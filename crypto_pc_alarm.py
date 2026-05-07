import tkinter as tk
from tkinter import ttk, messagebox
import websocket
import json
import threading
import time
import urllib.request
import winsound

class BinanceMultiAlarmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("바이낸스 다중 알람 시스템")
        self.root.geometry("450x550")
        self.root.attributes('-topmost', True)

        self.alarms = {}  # {알람ID: {"ws": websocket_객체, "info": 알람_정보_딕셔너리}}
        self.alarm_counter = 0

        self.setup_ui()
        self.load_binance_tickers() # 시작 시 티커 목록 로드

    def load_binance_tickers(self):
        self.status_label.config(text="바이낸스 코인 목록을 불러오는 중...")
        self.root.update()
        
        def fetch():
            try:
                # 바이낸스 Exchange Info API를 호출하여 활성화된 마켓 목록을 가져옴
                url = "https://api.binance.com/api/v3/exchangeInfo"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    
                # USDT 마켓이면서 현재 거래가 가능한(TRADING) 심볼만 필터링
                tickers = [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']
                tickers.sort() # 알파벳 순 정렬
                
                # 메인 스레드(UI)에서 콤보박스 업데이트
                self.root.after(0, lambda: self.update_ticker_combobox(tickers))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("오류", f"코인 목록 로드 실패: {e}"))
                self.root.after(0, lambda: self.status_label.config(text="코인 목록 로드 실패"))

        threading.Thread(target=fetch, daemon=True).start()

    def update_ticker_combobox(self, tickers):
        self.ticker_combo['values'] = tickers
        if tickers:
            self.ticker_combo.set("XRPUSDT") # 기본값
        self.status_label.config(text="대기 중")

    def setup_ui(self):
        # --- 설정 영역 ---
        frame_settings = tk.LabelFrame(self.root, text="알람 설정", padx=10, pady=10)
        frame_settings.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_settings, text="코인 선택:").grid(row=0, column=0, pady=5, sticky="w")
        self.ticker_combo = ttk.Combobox(frame_settings, state="readonly", width=15)
        self.ticker_combo.grid(row=0, column=1, pady=5, padx=5)

        tk.Label(frame_settings, text="목표 가격:").grid(row=1, column=0, pady=5, sticky="w")
        self.price_var = tk.DoubleVar(value=1.45)
        tk.Entry(frame_settings, textvariable=self.price_var, width=18).grid(row=1, column=1, pady=5, padx=5)

        tk.Label(frame_settings, text="알림 조건:").grid(row=2, column=0, pady=5, sticky="w")
        self.condition_var = tk.StringVar(value="이상(>=)")
        ttk.Combobox(frame_settings, textvariable=self.condition_var, values=["이상(>=)", "이하(<=)"], state="readonly", width=15).grid(row=2, column=1, pady=5, padx=5)

        tk.Label(frame_settings, text="지속 시간(초):").grid(row=3, column=0, pady=5, sticky="w")
        self.duration_var = tk.IntVar(value=10)
        tk.Entry(frame_settings, textvariable=self.duration_var, width=18).grid(row=3, column=1, pady=5, padx=5)

        tk.Button(frame_settings, text="알람 리스트에 추가", command=self.add_alarm, bg="lightblue").grid(row=4, column=0, columnspan=2, pady=10, ipadx=50)

        # --- 리스트 영역 ---
        frame_list = tk.LabelFrame(self.root, text="작동 중인 알람 목록", padx=10, pady=10)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)

        # Treeview (표 형태의 리스트) 설정
        columns = ("ID", "Ticker", "Price", "Cond", "Sec")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings", height=8)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Ticker", text="티커")
        self.tree.heading("Price", text="가격")
        self.tree.heading("Cond", text="조건")
        self.tree.heading("Sec", text="시간")
        
        self.tree.column("ID", width=30, anchor="center")
        self.tree.column("Ticker", width=90, anchor="center")
        self.tree.column("Price", width=80, anchor="e")
        self.tree.column("Cond", width=60, anchor="center")
        self.tree.column("Sec", width=40, anchor="center")
        self.tree.pack(fill="both", expand=True)

        tk.Button(frame_list, text="선택한 알람 삭제", command=self.remove_alarm, bg="salmon").pack(pady=5)

        # 상태 표시
        self.status_label = tk.Label(self.root, text="상태: 초기화 중...", fg="blue")
        self.status_label.pack(pady=5)

    def add_alarm(self):
        ticker = self.ticker_combo.get()
        if not ticker:
            messagebox.showwarning("경고", "코인을 선택하세요.")
            return
            
        try:
            target_price = float(self.price_var.get())
            duration = int(self.duration_var.get())
        except ValueError:
             messagebox.showwarning("경고", "가격과 시간은 숫자로 입력해야 합니다.")
             return

        condition = self.condition_var.get()
        
        self.alarm_counter += 1
        alarm_id = str(self.alarm_counter)

        # 리스트 뷰에 데이터 삽입
        self.tree.insert("", "end", iid=alarm_id, values=(alarm_id, ticker, target_price, condition, duration))

        # 알람 정보 저장
        alarm_info = {
            "ticker": ticker.lower(),
            "target_price": target_price,
            "condition": condition,
            "duration": duration,
            "is_active": True
        }
        self.alarms[alarm_id] = {"info": alarm_info, "ws": None}

        # 해당 알람을 위한 독립된 웹소켓 감시 스레드 시작
        threading.Thread(target=self.run_websocket, args=(alarm_id,), daemon=True).start()
        self.status_label.config(text=f"{ticker} 감시 시작됨 (ID: {alarm_id})", fg="green")

    def remove_alarm(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showinfo("알림", "삭제할 알람을 리스트에서 선택하세요.")
            return

        alarm_id = selected_item[0]
        
        # 1. 웹소켓 연결 강제 종료
        if alarm_id in self.alarms:
            self.alarms[alarm_id]["info"]["is_active"] = False
            ws_app = self.alarms[alarm_id]["ws"]
            if ws_app:
                ws_app.close()
            del self.alarms[alarm_id]

        # 2. UI 리스트에서 제거
        self.tree.delete(alarm_id)
        self.status_label.config(text=f"알람 ID {alarm_id} 삭제됨", fg="blue")

    def run_websocket(self, alarm_id):
        info = self.alarms[alarm_id]["info"]
        ticker = info["ticker"]
        socket = f"wss://stream.binance.com:9443/ws/{ticker}@trade"

        def on_message(ws, message):
            # 알람이 삭제되었거나 이미 울렸으면 무시
            if not info["is_active"]:
                ws.close()
                return

            data = json.loads(message)
            current_price = float(data['p'])
            
            # 조건 달성 여부 확인
            triggered = False
            if info["condition"] == "이상(>=)" and current_price >= info["target_price"]:
                triggered = True
            elif info["condition"] == "이하(<=)" and current_price <= info["target_price"]:
                triggered = True

            if triggered:
                info["is_active"] = False # 중복 알람 방지
                ws.close() # 목표 달성 시 해당 웹소켓 종료
                self.trigger_alarm(alarm_id, ticker, current_price, info["duration"])

        def on_error(ws, error):
            pass # 로그 생략
        def on_close(ws, close_status_code, close_msg):
            pass # 로그 생략

        ws_app = websocket.WebSocketApp(socket, on_message=on_message, on_error=on_error, on_close=on_close)
        self.alarms[alarm_id]["ws"] = ws_app
        ws_app.run_forever()

    def trigger_alarm(self, alarm_id, ticker, current_price, duration):
        # UI 업데이트는 메인 스레드에서 실행
        def update_ui():
            self.status_label.config(text=f"🔥 알람 발생! {ticker.upper()} 가격: {current_price}", fg="red")
            # 리스트에서 완료된 알람 강조 또는 삭제
            try:
                self.tree.item(alarm_id, tags=('triggered',))
                self.tree.tag_configure('triggered', background='yellow')
            except tk.TclError:
                pass # 이미 삭제된 경우 예외 처리
            
        self.root.after(0, update_ui)

        # 소리 재생
        self.play_sound(duration)

    def play_sound(self, duration_seconds):
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            winsound.Beep(2000, 300) # 주파수를 높이고 짧게 끊어서 긴박한 소리 연출
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceMultiAlarmApp(root)
    root.mainloop()