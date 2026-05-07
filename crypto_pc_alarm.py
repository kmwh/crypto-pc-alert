import customtkinter as ctk
from tkinter import ttk, messagebox
import websocket
import json
import threading
import time
import urllib.request
import os
import wave
import struct
import math

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class BinanceModernAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Binance Pro Trading Alarm")
        self.root.geometry("900x700")
        self.root.minsize(850, 650)
        self.root.attributes('-topmost', True)

        # 👉 [여기 추가] 창 상단 및 작업 표시줄 아이콘 변경
        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            pass # 아이콘 파일이 없을 경우 프로그램이 튕기는 것을 방지
        
        self.root.grid_columnconfigure(0, weight=75, uniform="main") 
        self.root.grid_columnconfigure(1, weight=25, uniform="main") 
        self.root.grid_rowconfigure(0, weight=1)

        self.all_tickers = []
        self.alarms = {}
        self.alarm_counter = 0
        
        self.fav_file = "favorite_tickers.json"
        self.alarm_file = "saved_alarms.json"
        
        self.check_on = " [ ✔ ] "
        self.check_off = " [   ] "
        
        pygame.mixer.init()
        self.generate_default_sounds()

        self.favorites = self.load_json(self.fav_file, [])
        self.saved_alarms = self.load_json(self.alarm_file, {})

        if self.saved_alarms:
            self.alarm_counter = max([int(k) for k in self.saved_alarms.keys()] or [0])

        self.setup_ui()
        self.load_binance_tickers()

    def generate_default_sounds(self):
        sounds = {
            "기본 비프음": ("beep.wav", 1000, "beep"),
            "경고 사이렌": ("siren.wav", 1200, "siren"),
            "저음 알림": ("low.wav", 400, "low")
        }
        for name, (filename, freq, typ) in sounds.items():
            if not os.path.exists(filename):
                with wave.open(filename, 'w') as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(44100)
                    frames = []
                    for i in range(44100):
                        if typ == "beep":
                            val = int(32767.0 * math.sin(2.0 * math.pi * freq * i / 44100.0)) if (i // 4410) % 2 == 0 else 0
                        elif typ == "siren":
                            mod = math.sin(2.0 * math.pi * 4 * i / 44100.0) 
                            f_current = freq + mod * 300
                            val = int(32767.0 * math.sin(2.0 * math.pi * f_current * i / 44100.0))
                        else:
                            val = int(32767.0 * math.sin(2.0 * math.pi * freq * i / 44100.0))
                        frames.append(struct.pack('<h', val))
                    f.writeframesraw(b''.join(frames))

    def load_json(self, filepath, default_type):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except Exception:
                return default_type
        return default_type

    def save_json(self, filepath, data):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def load_binance_tickers(self):
        self.status_label.configure(text="바이낸스 마켓 데이터 동기화 중...", text_color="#3498db")
        self.root.update()
        
        def fetch():
            try:
                url = "https://api.binance.com/api/v3/exchangeInfo"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                tickers = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
                tickers.sort()
                self.all_tickers = tickers
                self.root.after(0, self.on_tickers_loaded)
            except Exception:
                self.root.after(0, lambda: self.status_label.configure(text="코인 목록 로드 실패", text_color="red"))

        threading.Thread(target=fetch, daemon=True).start()

    def on_tickers_loaded(self):
        self.status_label.configure(text="시스템 대기 중", text_color="gray")
        self.restore_alarms()

    def setup_ui(self):
        left_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        left_frame.grid_rowconfigure(0, weight=0)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        right_frame = ctk.CTkFrame(self.root, corner_radius=15)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        # --- 왼쪽: 알람 설정 패널 ---
        settings_frame = ctk.CTkFrame(left_frame, corner_radius=15)
        settings_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        settings_frame.grid_columnconfigure(1, weight=1) 
        
        ctk.CTkLabel(settings_frame, text="⚡ 새 알람 설정", font=("Roboto", 16, "bold")).grid(row=0, column=0, columnspan=3, pady=(15, 10), padx=20, sticky="w")

        ctk.CTkLabel(settings_frame, text="코인 검색:").grid(row=1, column=0, pady=8, padx=20, sticky="w")
        self.ticker_var = ctk.StringVar()
        self.ticker_entry = ctk.CTkEntry(settings_frame, textvariable=self.ticker_var, placeholder_text="예: BTCUSDT")
        self.ticker_entry.grid(row=1, column=1, pady=8, sticky="ew")
        self.ticker_entry.bind('<KeyRelease>', self.search_ticker)
        self.ticker_entry.bind('<FocusOut>', lambda e: self.root.after(200, self.hide_dropdown)) 

        ctk.CTkButton(settings_frame, text="⭐ 즐겨찾기 등록", width=120, fg_color="#f39c12", hover_color="#d68910", command=self.add_favorite).grid(row=1, column=2, padx=20)

        ctk.CTkLabel(settings_frame, text="목표 가격:").grid(row=2, column=0, pady=8, padx=20, sticky="w")
        self.price_var = ctk.DoubleVar(value=0.0)
        ctk.CTkEntry(settings_frame, textvariable=self.price_var).grid(row=2, column=1, pady=8, sticky="ew")

        ctk.CTkLabel(settings_frame, text="알림 조건:").grid(row=3, column=0, pady=8, padx=20, sticky="w")
        self.condition_var = ctk.StringVar(value="이상(>=)")
        ctk.CTkComboBox(settings_frame, variable=self.condition_var, values=["이상(>=)", "이하(<=)"]).grid(row=3, column=1, pady=8, sticky="ew")

        ctk.CTkLabel(settings_frame, text="소리 종류:").grid(row=4, column=0, pady=8, padx=20, sticky="w")
        self.sound_var = ctk.StringVar(value="경고 사이렌")
        ctk.CTkComboBox(settings_frame, variable=self.sound_var, values=["기본 비프음", "경고 사이렌", "저음 알림"]).grid(row=4, column=1, pady=8, sticky="ew")

        ctk.CTkLabel(settings_frame, text="소리 크기:").grid(row=5, column=0, pady=8, padx=20, sticky="w")
        vol_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        vol_frame.grid(row=5, column=1, columnspan=2, sticky="ew")
        self.volume_var = ctk.IntVar(value=50)
        ctk.CTkSlider(vol_frame, variable=self.volume_var, from_=0, to=100).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(vol_frame, text="🔊 듣기", width=60, fg_color="#34495e", hover_color="#2c3e50", command=self.preview_sound).pack(side="right", padx=(10, 20))

        ctk.CTkLabel(settings_frame, text="지속 시간(초):").grid(row=6, column=0, pady=8, padx=20, sticky="w")
        self.duration_var = ctk.IntVar(value=60)
        ctk.CTkEntry(settings_frame, textvariable=self.duration_var).grid(row=6, column=1, pady=8, sticky="ew")

        ctk.CTkButton(settings_frame, text="알람 리스트에 추가하기", height=40, font=("Roboto", 14, "bold"), command=self.add_alarm).grid(row=7, column=0, columnspan=3, pady=(15, 20), padx=20, sticky="ew")

        self.dropdown_frame = ctk.CTkScrollableFrame(self.root, width=160, height=180, corner_radius=5, fg_color="#1e272e", border_width=1, border_color="#3498db")

        # --- 왼쪽: 알람 리스트 패널 ---
        list_frame = ctk.CTkFrame(left_frame, corner_radius=15)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(list_frame, text="📋 감시 중인 타점 목록", font=("Roboto", 16, "bold")).grid(row=0, column=0, pady=15, padx=20, sticky="w")

        style = ttk.Style()
        style.theme_use("default")
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=30, borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#333333", foreground="white", relief="flat", font=("Roboto", 11, "bold"))
        style.map("Treeview.Heading", background=[('active', '#444444')])

        tree_scroll = ctk.CTkScrollbar(list_frame, command=self.tree_yview)
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 20), padx=(0, 15))

        columns = ("Select", "Ticker", "Price", "Cond", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", yscrollcommand=tree_scroll.set)
        
        self.tree.heading("Select", text=self.check_off)
        self.tree.heading("Ticker", text="Ticker")
        self.tree.heading("Price", text="Price")
        self.tree.heading("Cond", text="Cond")
        self.tree.heading("Status", text="Status")
        
        self.tree.column("Select", width=55, anchor="center")
        self.tree.column("Ticker", width=130, anchor="center")
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Cond", width=75, anchor="center")
        self.tree.column("Status", width=75, anchor="center")
        
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(20, 5), pady=(0, 20))
        self.tree.tag_configure('triggered', background='#5e2525')
        
        self.tree.bind('<ButtonRelease-1>', self.handle_tree_click)

        control_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20), padx=20, sticky="ew")
        
        ctk.CTkButton(control_frame, text="🗑️ 체크 항목 삭제", width=120, fg_color="#e74c3c", hover_color="#c0392b", command=self.remove_checked_alarms).pack(side="left", padx=(0, 10))
        ctk.CTkButton(control_frame, text="🚨 울리는 알람 지우기", width=140, fg_color="#d35400", hover_color="#a84300", command=self.clear_triggered_alarms).pack(side="left")
        
        self.status_label = ctk.CTkLabel(control_frame, text="상태: 대기 중", text_color="gray", width=200, anchor="e")
        self.status_label.pack(side="right")

        # --- 오른쪽: 즐겨찾기 패널 ---
        ctk.CTkLabel(right_frame, text="⭐ 즐겨찾기", font=("Roboto", 16, "bold")).grid(row=0, column=0, pady=(15, 10))
        self.fav_scroll_frame = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        self.fav_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.update_favorite_ui()

    def handle_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        col = self.tree.identify_column(event.x)

        if region == "heading" and col == "#1":
            self.toggle_all_checks()
            
        elif region == "cell" and col == "#1":
            item = self.tree.identify_row(event.y)
            if item:
                current_val = self.tree.set(item, "Select")
                new_val = self.check_on if current_val == self.check_off else self.check_off
                self.tree.set(item, "Select", new_val)
                self.update_header_checkbox_state() 

    def toggle_all_checks(self):
        items = self.tree.get_children()
        if not items: return
        
        current_header = self.tree.heading("Select")["text"]
        new_val = self.check_off if current_header == self.check_on else self.check_on
        
        self.tree.heading("Select", text=new_val)
        for item in items:
            self.tree.set(item, "Select", new_val)

    def update_header_checkbox_state(self):
        items = self.tree.get_children()
        if not items:
            self.tree.heading("Select", text=self.check_off)
            return

        all_checked = all(self.tree.set(item, "Select") == self.check_on for item in items)
        self.tree.heading("Select", text=self.check_on if all_checked else self.check_off)

    def remove_checked_alarms(self):
        items = self.tree.get_children()
        removed_count = 0
        
        for item in items:
            if self.tree.set(item, "Select") == self.check_on:
                aid = item
                if aid in self.alarms:
                    self.alarms[aid]["info"]["is_active"] = False
                    if self.alarms[aid]["ws"]:
                        self.alarms[aid]["ws"].close()
                    del self.alarms[aid] 
                self.tree.delete(aid)
                removed_count += 1
                
        if removed_count > 0:
            self.sync_alarms_to_file()
            self.status_label.configure(text=f"체크된 알람 {removed_count}개 삭제 완료", text_color="#3498db")
        else:
            messagebox.showinfo("알림", "삭제할 항목을 먼저 체크박스 표시에 선택해주세요.")
            
        self.update_header_checkbox_state() 

    def tree_yview(self, *args):
        self.tree.yview(*args)

    def search_ticker(self, event):
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return'): return
        typed_val = self.ticker_var.get().upper()

        for widget in self.dropdown_frame.winfo_children():
            widget.destroy()

        if typed_val == '' or not self.all_tickers:
            self.dropdown_frame.place_forget()
            return

        filtered = [t for t in self.all_tickers if typed_val in t]

        if not filtered:
            self.dropdown_frame.place_forget()
            return

        for ticker in filtered[:40]:
            btn = ctk.CTkButton(self.dropdown_frame, text=ticker, fg_color="transparent", 
                                hover_color="#34495e", anchor="w", text_color="white", height=28,
                                command=lambda t=ticker: self.select_ticker(t))
            btn.pack(fill="x", pady=1)

        self.root.update_idletasks()
        x = self.ticker_entry.winfo_rootx() - self.root.winfo_rootx()
        y = self.ticker_entry.winfo_rooty() - self.root.winfo_rooty() + self.ticker_entry.winfo_height() + 2
        
        self.dropdown_frame.configure(width=self.ticker_entry.winfo_width()) 
        self.dropdown_frame.place(x=x, y=y)
        self.dropdown_frame.lift() 

    def select_ticker(self, ticker):
        self.ticker_var.set(ticker)
        self.dropdown_frame.place_forget()
        self.ticker_entry.focus_set()
        self.ticker_entry.icursor("end")

    def hide_dropdown(self):
        self.dropdown_frame.place_forget()

    def update_favorite_ui(self):
        for widget in self.fav_scroll_frame.winfo_children():
            widget.destroy()
            
        for ticker in self.favorites:
            item_frame = ctk.CTkFrame(self.fav_scroll_frame, fg_color="#333333", corner_radius=8)
            item_frame.pack(fill="x", pady=2)
            
            btn = ctk.CTkButton(item_frame, text=ticker, fg_color="transparent", hover_color="#444444", anchor="w", command=lambda t=ticker: self.select_ticker(t))
            btn.pack(side="left", fill="x", expand=True, padx=5, pady=2)
            
            del_btn = ctk.CTkButton(item_frame, text="✕", width=30, fg_color="transparent", hover_color="#c0392b", command=lambda t=ticker: self.remove_favorite(t))
            del_btn.pack(side="right", padx=5, pady=2)

    def remove_favorite(self, ticker):
        if ticker in self.favorites:
            self.favorites.remove(ticker)
            self.save_json(self.fav_file, self.favorites)
            self.update_favorite_ui()

    def add_favorite(self):
        ticker = self.ticker_var.get().upper()
        if ticker and ticker in self.all_tickers and ticker not in self.favorites:
            self.favorites.append(ticker)
            self.favorites.sort()
            self.save_json(self.fav_file, self.favorites)
            self.update_favorite_ui()

    def preview_sound(self):
        file_map = {"기본 비프음": "beep.wav", "경고 사이렌": "siren.wav", "저음 알림": "low.wav"}
        sound_file = file_map.get(self.sound_var.get(), "beep.wav")
        sound = pygame.mixer.Sound(sound_file)
        sound.set_volume(self.volume_var.get() / 100.0)
        sound.play() 

    def sync_alarms_to_file(self):
        data_to_save = {aid: payload["info"] for aid, payload in self.alarms.items()}
        self.save_json(self.alarm_file, data_to_save)

    def restore_alarms(self):
        for aid, info in self.saved_alarms.items():
            status_text = "감시중" if info["is_active"] else "종료됨"
            # 👉 [변경됨] 복구 시 삽입 데이터에서 aid(ID) 변수 위치 제거
            self.tree.insert("", "end", iid=aid, values=(self.check_off, info["ticker"].upper(), info["target_price"], info["condition"], status_text))
            self.alarms[aid] = {"info": info, "ws": None}
            if info["is_active"]:
                threading.Thread(target=self.run_websocket, args=(aid,), daemon=True).start()
            else:
                self.tree.item(aid, tags=('triggered',))
        self.update_header_checkbox_state()

    def add_alarm(self):
        ticker = self.ticker_var.get().upper()
        if not ticker or ticker not in self.all_tickers: return messagebox.showwarning("경고", "올바른 코인을 선택하세요.")
            
        try:
            target_price = float(self.price_var.get())
            duration = int(self.duration_var.get())
            volume = int(self.volume_var.get())
        except ValueError: return messagebox.showwarning("경고", "숫자를 정확히 입력하세요.")

        condition = self.condition_var.get()
        self.alarm_counter += 1
        aid = str(self.alarm_counter)

        # 👉 [변경됨] 새 알람 추가 시 삽입 데이터에서 aid(ID) 변수 위치 제거
        self.tree.insert("", "end", iid=aid, values=(self.check_off, ticker, target_price, condition, "감시중"))

        alarm_info = {
            "ticker": ticker.lower(), "target_price": target_price, "condition": condition,
            "duration": duration, "sound_type": self.sound_var.get(), "volume": volume, "is_active": True
        }
        self.alarms[aid] = {"info": alarm_info, "ws": None}
        self.sync_alarms_to_file()
        threading.Thread(target=self.run_websocket, args=(aid,), daemon=True).start()
        self.status_label.configure(text=f"{ticker} 감시 시작", text_color="#2ecc71")
        self.update_header_checkbox_state()

    def clear_triggered_alarms(self):
        aids_to_remove = [aid for aid, payload in self.alarms.items() if not payload["info"]["is_active"]]
        if not aids_to_remove: return messagebox.showinfo("알림", "현재 타점에 도달하여 울리고 있는 알람이 없습니다.")
            
        for aid in aids_to_remove:
            del self.alarms[aid]
            try: self.tree.delete(aid)
            except: pass
                
        self.sync_alarms_to_file()
        self.status_label.configure(text=f"타점 도달 알람 {len(aids_to_remove)}개 일괄 삭제", text_color="#3498db")
        self.update_header_checkbox_state()

    def run_websocket(self, aid):
        info = self.alarms[aid]["info"]
        ticker = info["ticker"]
        socket = f"wss://stream.binance.com:9443/ws/{ticker}@trade"

        def on_message(ws, message):
            if not info.get("is_active"):
                ws.close()
                return
            data = json.loads(message)
            current_price = float(data['p'])
            triggered = False
            if info["condition"] == "이상(>=)" and current_price >= info["target_price"]: triggered = True
            elif info["condition"] == "이하(<=)" and current_price <= info["target_price"]: triggered = True

            if triggered:
                info["is_active"] = False 
                self.sync_alarms_to_file()
                ws.close() 
                self.trigger_alarm(aid, ticker, current_price, info)

        def on_error(ws, error): pass
        def on_close(ws, close_status_code, close_msg): pass

        ws_app = websocket.WebSocketApp(socket, on_message=on_message, on_error=on_error, on_close=on_close)
        self.alarms[aid]["ws"] = ws_app
        ws_app.run_forever()

    def trigger_alarm(self, aid, ticker, current_price, info):
        def update_ui():
            self.status_label.configure(text=f"🔥 타점 도달! {ticker.upper()} / 현재가: {current_price}", text_color="#e74c3c")
            try:
                self.tree.set(aid, "Status", "종료됨")
                self.tree.item(aid, tags=('triggered',))
            except: pass
        self.root.after(0, update_ui)
        threading.Thread(target=self.play_sound, args=(aid, info), daemon=True).start()

    def play_sound(self, aid, info):
        file_map = {"기본 비프음": "beep.wav", "경고 사이렌": "siren.wav", "저음 알림": "low.wav"}
        sound_file = file_map.get(info.get("sound_type", "경고 사이렌"), "siren.wav")
        try:
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(info.get("volume", 50) / 100.0)
            channel = sound.play(loops=-1) 
            end_time = time.time() + info.get("duration", 60)
            while time.time() < end_time:
                if aid not in self.alarms: break 
                time.sleep(0.1)
            channel.stop() 
        except: pass

if __name__ == "__main__":
    from sys import modules
    if 'wave' in modules:
        root = ctk.CTk()
        app = BinanceModernAlarmApp(root)
        root.mainloop()