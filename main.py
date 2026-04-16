import requests
from datetime import datetime, time
import json
import os

# ===== 環境変数から読み込み =====
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
    delay = arr.get("delay")
    scheduled = arr.get("scheduled")

    if not delay or not scheduled:
        continue

    t = datetime.fromisoformat(scheduled.replace("Z","")).time()

    if is_target_arrival(t):
        found = True
        mark = "⚠️ " if (t.hour >= 23 or t.hour < 2) else ""
        
        msg += (
            f"{mark}便名: {f['flight']['iata']}\n"
            f"到着予定: {t.strftime('%H:%M')}\n"
            f"遅延: {delay}分\n\n"
        )

if found:
    send_line(msg)
else:
    send_line("対象時間帯（21:00〜翌2:00）の遅延便はありません。")
