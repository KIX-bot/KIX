import requests
from datetime import datetime, time
import json
import os

AVIATION_API_KEY = os.environ.get("AVIATION_API_KEY")
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

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

def is_target_arrival(t):
    return t >= time(21, 0) or t <= time(2, 0)

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

msg = "✈️ 関西国際空港 到着遅延便（21:00〜翌2:00）\n\n"
found = False

for f in res.get("data", []):
    arr = f.get("arrival", {})
    flight = f.get("flight", {})
    dep = f.get("departure", {})

    delay = arr.get("delay")
    scheduled = arr.get("scheduled")
    estimated = arr.get("estimated")
    terminal = arr.get("terminal") or "?"
    status = f.get("flight_status", "不明")

    if not delay or not scheduled:
        continue

    t = datetime.fromisoformat(scheduled.replace("Z","")).time()

    if is_target_arrival(t):
        found = True

        # 時刻整形
        scheduled_time = datetime.fromisoformat(scheduled.replace("Z","")).strftime("%H:%M")
        estimated_time = (
            datetime.fromisoformat(estimated.replace("Z","")).strftime("%H:%M")
            if estimated else "??:??"
        )

        # 出発地（都市名）
        city = dep.get("airport") or dep.get("iata") or "不明"

        msg += (
            f"✈️ {flight.get('iata')} | {city}\n"
            f"定刻: {scheduled_time} → {estimated_time}\n"
            f"遅延: {delay}分 / {status} / T{terminal}\n\n"
        )

if found:
    send_line(msg)
else:
    send_line("対象時間帯（21:00〜翌2:00）の遅延便はありません。")
