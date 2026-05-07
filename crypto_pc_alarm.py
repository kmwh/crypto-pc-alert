import tkinter as tk
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

class BinanceAdvancedAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("바이낸스 프로 트레이딩 알람 (사운드 제어판)")
        self.root.geometry("750x620")
        self.root.attributes('-topmost', True)

        self.all_tickers = []
        self.alarms = {}
        self.alarm_counter = 0
        
        self.fav_file = "favorite_tickers.json"
        self.alarm_file = "saved_alarms.json"
        
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
        self.status_label.config(text="바이낸스 마켓 데이터 동기화 중...")
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
                self.root.after(0, lambda: self.status_label.config(text="코인 목록 로드 실패"))

        threading.Thread(target=fetch, daemon=True).start()

    def on_tickers_loaded(self):
        self.ticker_combo['values'] = self.all_tickers
        self.status_label.config(text="시스템 대기 중")
        self.restore_alarms()

    def setup_ui(self):
        left_frame = tk.Frame(self.root)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        right_frame = tk.LabelFrame(self.root, text="⭐ 즐겨찾기", width=180)
        right_frame.pack(side="right", fill="y", padx=10, pady=10)

        frame_settings = tk.LabelFrame(left_frame, text="알람 상세 설정", padx=10, pady=10)
        frame_settings.pack(fill="x", pady=(0, 10))

        tk.Label(frame_settings, text="코인 검색:").grid(row=0, column=0, pady=5, sticky="w")
        self.ticker_var = tk.StringVar()
        self.ticker_combo = ttk.Combobox(frame_settings, textvariable=self.ticker_var, width=15)
        self.ticker_combo.grid(row=0, column=1, pady=5, sticky="w")
        self.ticker_combo.bind('<KeyRelease>', self.search_ticker) 
        tk.Button(frame_settings, text="⭐ 즐겨찾기 추가", command=self.add_favorite).grid(row=0, column=2, padx=10)

        tk.Label(frame_settings, text="목표 가격:").grid(row=1, column=0, pady=5, sticky="w")
        self.price_var = tk.DoubleVar(value=0.0)
        tk.Entry(frame_settings, textvariable=self.price_var, width=18).grid(row=1, column=1, pady=5, sticky="w")

        tk.Label(frame_settings, text="알림 조건:").grid(row=2, column=0, pady=5, sticky="w")
        self.condition_var = tk.StringVar(value="이상(>=)")
        ttk.Combobox(frame_settings, textvariable=self.condition_var, values=["이상(>=)", "이하(<=)"], state="readonly", width=15).grid(row=2, column=1, pady=5, sticky="w")

        tk.Label(frame_settings, text="소리 종류:").grid(row=3, column=0, pady=5, sticky="w")
        self.sound_var = tk.StringVar(value="경고 사이렌")
        ttk.Combobox(frame_settings, textvariable=self.sound_var, values=["기본 비프음", "경고 사이렌", "저음 알림"], state="readonly", width=15).grid(row=3, column=1, pady=5, sticky="w")

        tk.Label(frame_settings, text="소리 크기:").grid(row=4, column=0, pady=5, sticky="w")
        self.volume_var = tk.IntVar(value=50)
        
        vol_frame = tk.Frame(frame_settings)
        vol_frame.grid(row=4, column=1, columnspan=2, sticky="w")
        tk.Scale(vol_frame, variable=self.volume_var, from_=0, to=100, orient="horizontal", length=120).pack(side="left")
        tk.Button(vol_frame, text="🔊 미리듣기", command=self.preview_sound, bg="lightyellow").pack(side="left", padx=10)

        tk.Label(frame_settings, text="지속 시간(초):").grid(row=5, column=0, pady=5, sticky="w")
        self.duration_var = tk.IntVar(value=60) 
        tk.Entry(frame_settings, textvariable=self.duration_var, width=18).grid(row=5, column=1, pady=5, sticky="w")

        tk.Button(frame_settings, text="알람 리스트에 등록", command=self.add_alarm, bg="lightblue").grid(row=6, column=0, columnspan=3, pady=10, ipadx=50)

        frame_list = tk.LabelFrame(left_frame, text="작동 중인 알람 목록", padx=10, pady=10)
        frame_list.pack(fill="both", expand=True)

        columns = ("ID", "Ticker", "Price", "Cond", "Status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=6)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Ticker", text="티커")
        self.tree.heading("Price", text="가격")
        self.tree.heading("Cond", text="조건")
        self.tree.heading("Status", text="상태")
        
        self.tree.column("ID", width=30, anchor="center")
        self.tree.column("Ticker", width=90, anchor="center")
        self.tree.column("Price", width=80, anchor="e")
        self.tree.column("Cond", width=60, anchor="center")
        self.tree.column("Status", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # 👉 버튼 패널 구성 (개별 삭제 / 일괄 삭제)
        btn_frame = tk.Frame(frame_list)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="선택한 알람 1개 삭제", command=self.remove_alarm, bg="salmon", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="울리는 알람 모두 지우기 🔇", command=self.clear_triggered_alarms, bg="orange", fg="white", font=("", 9, "bold")).pack(side="left", padx=5)

        self.status_label = tk.Label(left_frame, text="상태: 초기화 중...", fg="blue")
        self.status_label.pack(pady=5)

        self.fav_listbox = tk.Listbox(right_frame, width=18, height=20)
        self.fav_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.fav_listbox.bind('<Double-1>', self.load_from_favorite) 
        tk.Button(right_frame, text="즐겨찾기 삭제", command=self.remove_favorite).pack(pady=5)
        self.update_favorite_listbox()

    def preview_sound(self):
        file_map = {"기본 비프음": "beep.wav", "경고 사이렌": "siren.wav", "저음 알림": "low.wav"}
        sound_file = file_map.get(self.sound_var.get(), "beep.wav")
        volume = self.volume_var.get() / 100.0 
        sound = pygame.mixer.Sound(sound_file)
        sound.set_volume(volume)
        sound.play() 

    def search_ticker(self, event):
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return'):
            return
        typed_val = self.ticker_var.get().upper()
        if typed_val == '':
            self.ticker_combo['values'] = self.all_tickers
        else:
            filtered = [t for t in self.all_tickers if typed_val in t]
            self.ticker_combo['values'] = filtered

    def add_favorite(self):
        ticker = self.ticker_var.get().upper()
        if ticker and ticker in self.all_tickers and ticker not in self.favorites:
            self.favorites.append(ticker)
            self.favorites.sort()
            self.save_json(self.fav_file, self.favorites)
            self.update_favorite_listbox()

    def remove_favorite(self):
        selected = self.fav_listbox.curselection()
        if selected:
            ticker = self.fav_listbox.get(selected[0])
            self.favorites.remove(ticker)
            self.save_json(self.fav_file, self.favorites)
            self.update_favorite_listbox()

    def update_favorite_listbox(self):
        self.fav_listbox.delete(0, tk.END)
        for f in self.favorites:
            self.fav_listbox.insert(tk.END, f)

    def load_from_favorite(self, event):
        selected = self.fav_listbox.curselection()
        if selected:
            self.ticker_var.set(self.fav_listbox.get(selected[0]))

    def sync_alarms_to_file(self):
        data_to_save = {aid: payload["info"] for aid, payload in self.alarms.items()}
        self.save_json(self.alarm_file, data_to_save)

    def restore_alarms(self):
        for aid, info in self.saved_alarms.items():
            status_text = "감시중" if info["is_active"] else "종료됨"
            self.tree.insert("", "end", iid=aid, values=(aid, info["ticker"].upper(), info["target_price"], info["condition"], status_text))
            self.alarms[aid] = {"info": info, "ws": None}
            
            if info["is_active"]:
                threading.Thread(target=self.run_websocket, args=(aid,), daemon=True).start()
            if not info["is_active"]:
                self.tree.item(aid, tags=('triggered',))
                self.tree.tag_configure('triggered', background='yellow')

    def add_alarm(self):
        ticker = self.ticker_var.get().upper()
        if not ticker or ticker not in self.all_tickers:
            return messagebox.showwarning("경고", "올바른 코인을 선택하세요.")
            
        try:
            target_price = float(self.price_var.get())
            duration = int(self.duration_var.get())
            volume = int(self.volume_var.get())
        except ValueError:
             return messagebox.showwarning("경고", "숫자를 정확히 입력하세요.")

        condition = self.condition_var.get()
        sound_type = self.sound_var.get()
        
        self.alarm_counter += 1
        aid = str(self.alarm_counter)

        self.tree.insert("", "end", iid=aid, values=(aid, ticker, target_price, condition, "감시중"))

        alarm_info = {
            "ticker": ticker.lower(),
            "target_price": target_price,
            "condition": condition,
            "duration": duration,
            "sound_type": sound_type,
            "volume": volume,
            "is_active": True
        }
        self.alarms[aid] = {"info": alarm_info, "ws": None}
        self.sync_alarms_to_file()

        threading.Thread(target=self.run_websocket, args=(aid,), daemon=True).start()
        self.status_label.config(text=f"{ticker} 감시 시작", fg="green")

    def remove_alarm(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        aid = selected_item[0]
        
        if aid in self.alarms:
            self.alarms[aid]["info"]["is_active"] = False
            if self.alarms[aid]["ws"]:
                self.alarms[aid]["ws"].close()
            del self.alarms[aid] 
            
        self.sync_alarms_to_file()
        self.tree.delete(aid)
        self.status_label.config(text=f"알람 제거 완료 (알람음 정지됨)", fg="blue")

    # 👉 신규 추가된 함수: 트리거된 알람(소리가 나는 중인 알람) 모두 지우기
    def clear_triggered_alarms(self):
        aids_to_remove = []
        
        # is_active가 False인(이미 가격 도달을 달성한) 모든 알람의 ID를 수집합니다.
        for aid, payload in self.alarms.items():
            if not payload["info"]["is_active"]:
                aids_to_remove.append(aid)
                
        if not aids_to_remove:
            return messagebox.showinfo("알림", "현재 타점에 도달하여 울리고 있는 알람이 없습니다.")
            
        # 수집된 ID들을 딕셔너리와 UI 리스트에서 순차적으로 제거합니다.
        for aid in aids_to_remove:
            del self.alarms[aid] # 이 순간 스레드에서 돌고 있던 각각의 사운드 루프가 즉각 차단됩니다.
            try:
                self.tree.delete(aid)
            except tk.TclError:
                pass
                
        self.sync_alarms_to_file()
        self.status_label.config(text=f"타점 도달 알람 {len(aids_to_remove)}개 일괄 삭제 (소리 강제 종료)", fg="blue")

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
            self.status_label.config(text=f"🔥 타점 도달! {ticker.upper()} / 현재가: {current_price}", fg="red")
            try:
                self.tree.set(aid, column="Status", value="종료됨")
                self.tree.item(aid, tags=('triggered',))
                self.tree.tag_configure('triggered', background='yellow')
            except tk.TclError:
                pass
            
        self.root.after(0, update_ui)
        threading.Thread(target=self.play_sound, args=(aid, info), daemon=True).start()

    def play_sound(self, aid, info):
        file_map = {"기본 비프음": "beep.wav", "경고 사이렌": "siren.wav", "저음 알림": "low.wav"}
        sound_file = file_map.get(info.get("sound_type", "경고 사이렌"), "siren.wav")
        volume = info.get("volume", 50) / 100.0

        try:
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(volume)
            channel = sound.play(loops=-1) 
            
            end_time = time.time() + info.get("duration", 60)
            while time.time() < end_time:
                if aid not in self.alarms:
                    break 
                time.sleep(0.1)
                
            channel.stop() 
        except Exception as e:
            print(f"사운드 재생 오류: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceAdvancedAlarmApp(root)
    root.mainloop()