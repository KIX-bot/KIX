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

# ===== IATAベース（これが重要）=====
CITY_MAP = {
    "HND": "東京（羽田）",
    "NRT": "東京（成田）",
    "OKA": "沖縄（那覇）",
    "MMY": "宮古",
    "ISG": "石垣",
    "CTS": "札幌（新千歳）",
    "ICN": "ソウル（仁川）",
    "GMP": "ソウル（金浦）",
    "TPE": "台北（桃園）",
    "PVG": "上海（浦東）",
    "SIN": "シンガポール"
}

STATUS_MAP = {
    "active": "運行中",
    "landed": "到着済み",
    "scheduled": "定刻"
}

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

msg = "✈️ 関西国際空港 到着遅延便（21:00〜翌2:00）\n\n"
found = False

# ===== 重複排除用（これ重要）=====
seen = set()

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    flight = f.get("flight", {})

    delay = arr.get("delay")
    scheduled = arr.get("scheduled")

    if not delay or not scheduled:
        continue

    t = datetime.fromisoformat(scheduled.replace("Z","")).time()

    if not is_target_arrival(t):
        continue

    # ===== 同一便の重複排除 =====
    key = (scheduled, dep.get("iata"))
    if key in seen:
        continue
    seen.add(key)

    found = True

    estimated = arr.get("estimated")
    terminal = arr.get("terminal") or "1"
    status = STATUS_MAP.get(f.get("flight_status"), "不明")

    # 時刻
    scheduled_time = datetime.fromisoformat(scheduled.replace("Z","")).strftime("%H:%M")

    if estimated:
        estimated_time = datetime.fromisoformat(estimated.replace("Z","")).strftime("%H:%M")
    else:
        # estimatedが無い場合 → delayで計算
        estimated_dt = datetime.fromisoformat(scheduled.replace("Z","")) + \
                       timedelta(minutes=delay)
        estimated_time = estimated_dt.strftime("%H:%M")

    # ===== 日本語都市（IATAで確実に変換）=====
    city = CITY_MAP.get(dep.get("iata"), dep.get("iata"))

    msg += (
        f"✈️ {flight.get('iata')} | {city}\n"
        f"定刻: {scheduled_time} → {estimated_time}\n"
        f"遅延: {delay}分 / {status} / T{terminal}\n\n"
    )

if found:
    send_line(msg)
else:
    send_line("対象時間帯（21:00〜翌2:00）の遅延便はありません。")
