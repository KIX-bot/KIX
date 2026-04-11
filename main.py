import requests
from datetime import datetime, time
import json
import os

# ===== 環境変数 =====
AVIATION_API_KEY = os.environ.get("AVIATION_API_KEY")
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

# ===== 日本語変換マップ =====
STATUS_MAP = {
    "active": "運行中",
    "landed": "到着済み",
    "scheduled": "定刻",
    "cancelled": "欠航",
    "incident": "トラブル",
    "diverted": "目的地変更"
}

CITY_MAP = {
    "Tokyo Haneda International Airport": "東京（羽田）",
    "Tokyo International Airport": "東京（羽田）",
    "Narita International Airport": "東京（成田）",
    "Naha Airport": "沖縄（那覇）",
    "New Ishigaki Airport": "石垣",
    "Miyako Airport": "宮古島",
    "Sendai Airport": "仙台",
    "Taiwan Taoyuan International Airport": "台北（桃園）",
    "Incheon International Airport": "ソウル（仁川）",
    "Singapore Changi Airport": "シンガポール"
}

# ===== LINE送信 =====
def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    requests.post(url, headers=headers, data=json.dumps(data))

# ===== 対象時間判定 =====
def is_target_arrival(t):
    return t >= time(21, 0) or t <= time(2, 0)

# ===== API取得 =====
url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

# ===== メッセージ生成 =====
msg = "✈️ 関西国際空港 到着遅延便（21:00〜翌2:00）\n\n"
found = False

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    flight = f.get("flight", {})

    delay = arr.get("delay")
    scheduled = arr.get("scheduled")
    estimated = arr.get("estimated")
    terminal = arr.get("terminal") or "?"

    if not delay or not scheduled:
        continue

    # 時刻変換
    t = datetime.fromisoformat(scheduled.replace("Z", "")).time()

    if is_target_arrival(t):
        found = True

        scheduled_time = datetime.fromisoformat(
            scheduled.replace("Z", "")
        ).strftime("%H:%M")

        estimated_time = (
            datetime.fromisoformat(
                estimated.replace("Z", "")
            ).strftime("%H:%M")
            if estimated else "??:??"
        )

        # ===== 日本語化 =====
        dep_airport = dep.get("airport")
        city = CITY_MAP.get(dep_airport, dep_airport or "不明")

        status_raw = f.get("flight_status")
        status = STATUS_MAP.get(status_raw, "不明")

        # ===== 表示 =====
        msg += (
            f"✈️ {flight.get('iata')} | {city}\n"
            f"定刻: {scheduled_time} → {estimated_time}\n"
            f"遅延: {delay}分 / {status} / T{terminal}\n\n"
        )

# ===== 送信 =====
if found:
    send_line(msg)
else:
    send_line("対象時間帯（21:00〜翌2:00）の遅延便はありません。")
