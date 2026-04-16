import requests
from datetime import datetime, time, timedelta, timezone
import json
import os

# 日本時間(JST)のタイムゾーン定義
JST = timezone(timedelta(hours=9))

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
    # 21:00以降、または 02:00以前
    return t >= time(21, 0) or t <= time(2, 0)

# (CITY_MAP, AIRLINE_MAP, STATUS_MAP は前回と同じため省略)

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

# 現在の日本時間を取得
now_jst = datetime.now(JST)
msg = "🛫 KIX 関西国際空港・到着遅延 🛫\n"
msg += f"📅 確認時刻: {now_jst.strftime('%H:%M')}\n"
msg += "──────────────────\n\n"

found = False
seen = set()

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    flight = f.get("flight", {})
    airline = f.get("airline", {})

    scheduled_str = arr.get("scheduled")
    if not scheduled_str: continue

    try:
        # 1. APIの時刻(UTC)を解析し、日本時間(JST)に変換
        # 文字列 "2024-04-16T12:30:00+00:00" のような形式を想定
        sched_utc = datetime.fromisoformat(scheduled_str.replace("Z", "+00:00"))
        sched_jst = sched_utc.astimezone(JST)
    except: continue

    # 2. 日本時間で対象時間帯(21時〜2時)か判定
    if not is_target_arrival(sched_jst.time()):
        continue

    key = (scheduled_str, dep.get("iata"), flight.get("iata"))
    if key in seen: continue
    seen.add(key)

    estimated_str = arr.get("estimated")
    delay = arr.get("delay")
    
    try:
        if estimated_str:
            est_jst = datetime.fromisoformat(estimated_str.replace("Z", "+00:00")).astimezone(JST)
        elif delay:
            est_jst = sched_jst + timedelta(minutes=delay)
        else:
            continue
    except: continue

    # 遅延分数を計算
    diff_min = int((est_jst - sched_jst).total_seconds() / 60)
    
    # 遅延が1分以上ある場合のみ抽出
    if diff_min <= 0: continue

    found = True
    
    # 表示用データの整理
    city = CITY_MAP.get(dep.get("iata"), dep.get("iata") or "不明")
    airline_name = AIRLINE_MAP.get((flight.get("iata") or "")[:2], airline.get("name") or "不明")
    flight_no = flight.get("iata") or "不明"
    terminal = arr.get("terminal") or "1"
    status_text = STATUS_MAP.get(f.get("flight_status"), "不明")

    delay_badge = "🔴 大幅遅延" if diff_min >= 60 else "🟡 遅延"

    msg += (
        f"{delay_badge} (+{diff_min}分)\n"
        f"【{airline_name}】{flight_no}\n"
        f"📍 {city} 発\n"
        f"📢 {status_text} (T{terminal})\n"
        f"定刻: {sched_jst.strftime('%H:%M')}\n"
        f"予想: {est_jst.strftime('%H:%M')}\n"
        f"──────────────────\n"
    )

if found:
    send_line(msg)
else:
    send_line("✅ 現在、対象時間帯(21:00-02:00)の遅延便はありません。")
