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
    "arr_iata": "KIX",
    "flight_status": "active"
}

res = requests.get(url, params=params).json()

msg = "✈️ 関西国際空港 到着遅延便（21:00〜翌2:00）\n\n"
found = False

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    delay = arr.get("delay")
    scheduled = arr.get("scheduled")
    estimated = arr.get("estimated")
    terminal = arr.get("terminal")
    status = f.get("flight_status")

    if not delay or not scheduled:
        continue

    try:
        t = datetime.fromisoformat(scheduled.replace("Z","")).time()
    except:
        continue

    if is_target_arrival(t):
        found = True

        # 出発地
        city = dep.get("airport") or dep.get("iata") or "不明"

        # ターミナル
        terminal_text = f"T{terminal}" if terminal else "-"

        # 遅延後時刻
        if estimated:
            try:
                est = datetime.fromisoformat(estimated.replace("Z","")).time()
                delay_time = est.strftime('%H:%M')
            except:
                delay_time = "不明"
        else:
            delay_time = "不明"

        msg += (
            f"✈️ {f.get('flight', {}).get('iata', '不明')}  | {city}\n"
            f"定刻: {t.strftime('%H:%M')} → 遅延: {delay_time}\n"
            f"遅延: {delay}分 / {status} / {terminal_text}\n\n"
        )

if found:
    send_line(msg)
else:
    send_line("対象時間帯の遅延便はありません。")
