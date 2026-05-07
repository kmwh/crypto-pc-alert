import tkinter as tk
from tkinter import ttk, messagebox
import websocket
import json
import threading
import time
import urllib.request
import winsound
import os

class BinanceAdvancedAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("바이낸스 프로 트레이딩 알람")
        self.root.geometry("750x550")
        self.root.attributes('-topmost', True)

        self.all_tickers = []
        self.alarms = {}
        self.alarm_counter = 0
        
        self.fav_file = "favorite_tickers.json"
        self.alarm_file = "saved_alarms.json"
        
        self.favorites = self.load_json(self.fav_file, [])
        self.saved_alarms = self.load_json(self.alarm_file, {})

        if self.saved_alarms:
            self.alarm_counter = max([int(k) for k in self.saved_alarms.keys()])

        self.setup_ui()
        self.load_binance_tickers()

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
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(text="코인 목록 로드 실패 (네트워크 확인)"))

        threading.Thread(target=fetch, daemon=True).start()

    def on_tickers_loaded(self):
        self.ticker_combo['values'] = self.all_tickers
        self.status_label.config(text="시스템 대기 중")
        self.restore_alarms()

    def setup_ui(self):
        left_frame = tk.Frame(self.root)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        right_frame = tk.LabelFrame(self.root, text="⭐ 즐겨찾기 목록", width=200)
        right_frame.pack(side="right", fill="y", padx=10, pady=10)

        frame_settings = tk.LabelFrame(left_frame, text="새 알람 설정", padx=10, pady=10)
        frame_settings.pack(fill="x", pady=(0, 10))

        tk.Label(frame_settings, text="코인 검색:").grid(row=0, column=0, pady=5, sticky="w")
        
        self.ticker_var = tk.StringVar()
        self.ticker_combo = ttk.Combobox(frame_settings, textvariable=self.ticker_var, width=20)
        self.ticker_combo.grid(row=0, column=1, pady=5, sticky="w")
        self.ticker_combo.bind('<KeyRelease>', self.search_ticker) 

        tk.Button(frame_settings, text="즐겨찾기에 추가", command=self.add_favorite).grid(row=0, column=2, padx=10)

        tk.Label(frame_settings, text="목표 가격:").grid(row=1, column=0, pady=5, sticky="w")
        self.price_var = tk.DoubleVar(value=0.0)
        tk.Entry(frame_settings, textvariable=self.price_var, width=23).grid(row=1, column=1, pady=5, sticky="w")

        tk.Label(frame_settings, text="알림 조건:").grid(row=2, column=0, pady=5, sticky="w")
        self.condition_var = tk.StringVar(value="이상(>=)")
        ttk.Combobox(frame_settings, textvariable=self.condition_var, values=["이상(>=)", "이하(<=)"], state="readonly", width=20).grid(row=2, column=1, pady=5, sticky="w")

        tk.Label(frame_settings, text="지속 시간(초):").grid(row=3, column=0, pady=5, sticky="w")
        self.duration_var = tk.IntVar(value=60) 
        tk.Entry(frame_settings, textvariable=self.duration_var, width=23).grid(row=3, column=1, pady=5, sticky="w")

        tk.Button(frame_settings, text="알람 리스트에 추가", command=self.add_alarm, bg="lightblue").grid(row=4, column=0, columnspan=3, pady=10, ipadx=50)

        frame_list = tk.LabelFrame(left_frame, text="작동 중인 알람 목록", padx=10, pady=10)
        frame_list.pack(fill="both", expand=True)

        columns = ("ID", "Ticker", "Price", "Cond", "Sec", "Status")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=8)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Ticker", text="티커")
        self.tree.heading("Price", text="가격")
        self.tree.heading("Cond", text="조건")
        self.tree.heading("Sec", text="시간")
        self.tree.heading("Status", text="상태")
        
        self.tree.column("ID", width=30, anchor="center")
        self.tree.column("Ticker", width=80, anchor="center")
        self.tree.column("Price", width=80, anchor="e")
        self.tree.column("Cond", width=60, anchor="center")
        self.tree.column("Sec", width=40, anchor="center")
        self.tree.column("Status", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True)

        tk.Button(frame_list, text="선택한 알람 삭제", command=self.remove_alarm, bg="salmon").pack(pady=5)

        self.status_label = tk.Label(left_frame, text="상태: 초기화 중...", fg="blue")
        self.status_label.pack(pady=5)

        self.fav_listbox = tk.Listbox(right_frame, width=20, height=20)
        self.fav_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.fav_listbox.bind('<Double-1>', self.load_from_favorite) 
        
        tk.Button(right_frame, text="즐겨찾기에서 삭제", command=self.remove_favorite).pack(pady=5)
        self.update_favorite_listbox()

    # 👉 버그 수정된 함수: 타이핑 캔슬 현상 제거
    def search_ticker(self, event):
        # 방향키나 엔터 등 특정 키를 누를 때는 필터링 로직을 건너뜀 (포커스 유지용)
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return'):
            return

        typed_val = self.ticker_var.get().upper()
        
        if typed_val == '':
            self.ticker_combo['values'] = self.all_tickers
        else:
            filtered = [t for t in self.all_tickers if typed_val in t]
            self.ticker_combo['values'] = filtered
            
        # 기존 코드에서 드롭다운을 강제로 열던 event_generate('<Down>') 제거 완료

    def add_favorite(self):
        ticker = self.ticker_var.get().upper()
        if ticker and ticker in self.all_tickers and ticker not in self.favorites:
            self.favorites.append(ticker)
            self.favorites.sort()
            self.save_json(self.fav_file, self.favorites)
            self.update_favorite_listbox()
            messagebox.showinfo("추가 완료", f"{ticker} 즐겨찾기 등록됨")

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
            ticker = self.fav_listbox.get(selected[0])
            self.ticker_var.set(ticker)

    def sync_alarms_to_file(self):
        data_to_save = {aid: payload["info"] for aid, payload in self.alarms.items()}
        self.save_json(self.alarm_file, data_to_save)

    def restore_alarms(self):
        for aid, info in self.saved_alarms.items():
            status_text = "감시중" if info["is_active"] else "종료됨"
            self.tree.insert("", "end", iid=aid, values=(aid, info["ticker"].upper(), info["target_price"], info["condition"], info["duration"], status_text))
            
            self.alarms[aid] = {"info": info, "ws": None}
            
            if info["is_active"]:
                threading.Thread(target=self.run_websocket, args=(aid,), daemon=True).start()
                
            if not info["is_active"]:
                self.tree.item(aid, tags=('triggered',))
                self.tree.tag_configure('triggered', background='yellow')

    def add_alarm(self):
        ticker = self.ticker_var.get().upper()
        if not ticker or ticker not in self.all_tickers:
            messagebox.showwarning("경고", "올바른 바이낸스 티커를 입력/선택하세요.")
            return
            
        try:
            target_price = float(self.price_var.get())
            duration = int(self.duration_var.get())
        except ValueError:
             messagebox.showwarning("경고", "가격과 시간은 숫자로 입력해야 합니다.")
             return

        condition = self.condition_var.get()
        self.alarm_counter += 1
        aid = str(self.alarm_counter)

        self.tree.insert("", "end", iid=aid, values=(aid, ticker, target_price, condition, duration, "감시중"))

        alarm_info = {
            "ticker": ticker.lower(),
            "target_price": target_price,
            "condition": condition,
            "duration": duration,
            "is_active": True
        }
        self.alarms[aid] = {"info": alarm_info, "ws": None}
        self.sync_alarms_to_file()

        threading.Thread(target=self.run_websocket, args=(aid,), daemon=True).start()
        self.status_label.config(text=f"{ticker} 모니터링 추가됨", fg="green")

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
        self.status_label.config(text=f"알람 제거됨", fg="blue")

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
            if info["condition"] == "이상(>=)" and current_price >= info["target_price"]:
                triggered = True
            elif info["condition"] == "이하(<=)" and current_price <= info["target_price"]:
                triggered = True

            if triggered:
                info["is_active"] = False 
                self.sync_alarms_to_file()
                ws.close() 
                self.trigger_alarm(aid, ticker, current_price, info["duration"])

        def on_error(ws, error): pass
        def on_close(ws, close_status_code, close_msg): pass

        ws_app = websocket.WebSocketApp(socket, on_message=on_message, on_error=on_error, on_close=on_close)
        self.alarms[aid]["ws"] = ws_app
        ws_app.run_forever()

    def trigger_alarm(self, aid, ticker, current_price, duration):
        def update_ui():
            self.status_label.config(text=f"🔥 타점 도달! {ticker.upper()} / 현재가: {current_price}", fg="red")
            try:
                self.tree.set(aid, column="Status", value="종료됨")
                self.tree.item(aid, tags=('triggered',))
                self.tree.tag_configure('triggered', background='yellow')
            except tk.TclError:
                pass
            
        self.root.after(0, update_ui)
        self.play_sound(duration)

    def play_sound(self, duration_seconds):
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            winsound.Beep(2500, 500)
            time.sleep(0.05)

if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceAdvancedAlarmApp(root)
    root.mainloop()