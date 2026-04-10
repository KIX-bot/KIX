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
    return t >= time(21, 0) or t <= time(2, 0)

# ===== 空港名 日本語変換 =====
airport_map = {
    "Tokyo Haneda International Airport": "東京（羽田）",
    "Tokyo Narita International Airport": "東京（成田）",
    "New Chitose Airport": "札幌（新千歳）",
    "Fukuoka Airport": "福岡",
    "Naha Airport": "沖縄（那覇）",
    "Seoul Incheon International Airport": "ソウル（仁川）",
    "Gimpo International Airport": "ソウル（金浦）",
    "Taiwan Taoyuan International Airport": "台北（桃園）",
    "Shanghai Pudong International Airport": "上海（浦東）",
    "Hong Kong International Airport": "香港",
    "Los Angeles International Airport": "ロサンゼルス",
    "Chicago O'Hare International Airport": "シカゴ（オヘア）",
    "San Francisco International Airport": "サンフランシスコ",
    "John F Kennedy International Airport": "ニューヨーク（JFK）"
}

# ===== ステータス日本語化 =====
status_map = {
    "active": "運行中",
    "landed": "到着済み",
    "scheduled": "出発前",
    "cancelled": "欠航"
}

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX",
    "flight_status": "active"
}

try:
    res = requests.get(url, params=params, timeout=10).json()
except:
    send_line("API取得エラー")
    exit()

msg = "✈️ 関西国際空港 到着遅延便（21:00〜翌2:00）\n\n"
found = False

# ===== 遅延順に並び替え =====
flights = sorted(
    res.get("data", []),
    key=lambda x: x.get("arrival", {}).get("delay") or 0,
    reverse=True
)

for f in flights:
    arr = f.get("arrival", {})
    dep = f.get("departure", {})

    delay = arr.get("delay")
    scheduled = arr.get("scheduled")
    estimated = arr.get("estimated")
    terminal = arr.get("terminal")
    status = f.get("flight_status")

    # ===== scheduledがないものは除外 =====
    if not scheduled:
        continue

    # ===== JSTに変換 =====
    try:
        t_utc = datetime.fromisoformat(scheduled.replace("Z", ""))
        t_jst = t_utc + timedelta(hours=9)
        t = t_jst.time()
    except:
        continue

    # ===== 時間帯チェック =====
    if not is_target_arrival(t):
        continue

    # ===== 遅延15分未満は除外（ノイズ削減） =====
    if not delay or delay < 15:
        continue

    found = True

    # ===== 出発地 =====
    airport_name = dep.get("airport")
    iata = dep.get("iata")

    city = airport_map.get(airport_name)
    if not city:
        city = iata if iata else "不明"

    # ===== ステータス =====
    status_jp = status_map.get(status, status)

    # ===== ターミナル =====
    terminal_text = f" / T{terminal}" if terminal else ""

    # ===== 遅延後時刻 =====
    if estimated:
        try:
            est = datetime.fromisoformat(estimated.replace("Z", "")) + timedelta(hours=9)
            delay_time = est.strftime('%H:%M')
        except:
            delay_time = "不明"
    else:
        delay_time = "不明"

    msg += (
        f"✈️ {f.get('flight', {}).get('iata', '不明')} | {city}\n"
        f"定刻: {t.strftime('%H:%M')} → {delay_time}\n"
        f"遅延: {delay}分 / {status_jp}{terminal_text}\n\n"
    )

# ===== 通知 =====
if found:
    send_line(msg)
else:
    send_line("対象時間帯（21:00〜翌2:00）の遅延便はありません。")
