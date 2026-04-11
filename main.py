import requests
from datetime import datetime, time, timedelta
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
    return t >= time(22, 0) or t <= time(2, 0)

# ===== 都市（日本語）=====
CITY_MAP = {
    "HND": "東京（羽田）",
    "NRT": "東京（成田）",
    "OKA": "沖縄（那覇）",
    "MMY": "宮古",
    "ISG": "石垣",
    "CTS": "札幌（新千歳）",
    "ICN": "ソウル（仁川）",
    "TPE": "台北（桃園）",
    "PVG": "上海（浦東）",
    "SIN": "シンガポール",
    "LAX": "ロサンゼルス",
    "CNS": "ケアンズ",
    "SYD": "シドニー",
    "BKK": "バンコク",
    "HKG": "香港",
    "DXB": "ドバイ",
    "CDG": "パリ",
    "LHR": "ロンドン"
}

# ===== ステータス =====
STATUS_MAP = {
    "active": "運行中",
    "landed": "到着済み",
    "scheduled": "定刻"
}

# ===== 航空会社（重要）=====
AIRLINE_MAP = {
    "NH": ("ANA", "🟦"),
    "JL": ("JAL", "🔴"),
    "NU": ("JTA", "🔴"),
    "GK": ("Jetstar", "🟧"),
    "MM": ("Peach", "🟪"),
    "APJ": ("Peach", "🟪"),
    "OZ": ("Asiana", "🟥"),
    "SQ": ("Singapore", "🟨"),
    "CI": ("China Airlines", "🟩"),
    "BR": ("EVA", "🟩")
}

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

msg = "✈️ 関西国際空港 到着遅延便（22:00〜翌2:00）\n\n"
found = False
seen = set()

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    flight = f.get("flight", {})

    delay = arr.get("delay")
    scheduled = arr.get("scheduled")

    if not delay or not scheduled:
        continue

    try:
        sched_dt = datetime.fromisoformat(scheduled.replace("Z",""))
    except:
        continue

    if not is_target_arrival(sched_dt.time()):
        continue

    # ===== 重複排除 =====
    key = (scheduled, dep.get("iata"))
    if key in seen:
        continue
    seen.add(key)

    found = True

    estimated = arr.get("estimated")
    terminal = arr.get("terminal") or "1"
    status = STATUS_MAP.get(f.get("flight_status"), "不明")

    scheduled_time = sched_dt.strftime("%H:%M")

    if estimated:
        try:
            estimated_time = datetime.fromisoformat(
                estimated.replace("Z","")
            ).strftime("%H:%M")
        except:
            estimated_time = "??:??"
    else:
        estimated_time = (sched_dt + timedelta(minutes=delay)).strftime("%H:%M")

    # ===== 都市 =====
    city = CITY_MAP.get(dep.get("iata"), dep.get("iata") or "不明")

    # ===== 便名 =====
    flight_no = flight.get("iata") or flight.get("number") or "不明"

    # ===== 航空会社判定 =====
    prefix = flight_no[:2]
    airline_name, airline_icon = AIRLINE_MAP.get(prefix, ("その他", "✈️"))

    # ===== 遅延アイコン =====
    delay_icon = "⚠️" if delay >= 20 else ""

    msg += (
        f"{delay_icon} {airline_icon} {airline_name} {flight_no}　{city}\n"
        f"{scheduled_time} → {estimated_time}（+{delay}分）\n"
        f"{status}｜T{terminal}\n\n"
    )

if found:
    send_line(msg.strip())
else:
    send_line("対象時間帯（22:00〜翌2:00）の遅延便はありません。")
