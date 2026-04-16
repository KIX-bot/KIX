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

# ===== マッピングデータ（省略せず保持） =====
CITY_MAP = {
    "HND": "東京(羽田)", "NRT": "東京(成田)", "ITM": "大阪(伊丹)",
    "CTS": "札幌(新千歳)", "FUK": "福岡", "OKA": "沖縄(那覇)",
    "MMY": "宮古", "ISG": "石垣", "SDJ": "仙台", "NGO": "名古屋",
    "ICN": "ソウル(仁川)", "GMP": "ソウル(金浦)", "TPE": "台北(桃園)",
    "HKG": "香港", "SIN": "シンガポール", "BKK": "バンコク",
    "LAX": "ロサンゼルス", "HNL": "ホノルル" # 必要に応じて追加してください
}

AIRLINE_MAP = {
    "NH": "ANA", "JL": "JAL", "MM": "Peach", "GK": "Jetstar",
    "BC": "スカイマーク", "7G": "スターフライヤー", "KE": "大韓航空",
    "OZ": "アシアナ航空", "CI": "チャイナエアライン", "SQ": "シンガポール航空"
}

# ステータスの日本語変換
STATUS_MAP = {
    "landed": "🛬 着陸済み",
    "active": "✈️ 運行中",
    "scheduled": "🕒 予定",
    "cancelled": "❌ 欠航",
    "incident": "⚠️ 異常あり"
}

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

# LINEメッセージのヘッダー
msg = "🛫 KIX 関西国際空港・到着遅延 🛫\n"
msg += f"📅 基準時刻: {datetime.now().strftime('%H:%M')}\n"
msg += "──────────────────\n\n"

found = False
seen = set()

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    flight = f.get("flight", {})
    airline = f.get("airline", {})
    f_status = f.get("flight_status")

    scheduled = arr.get("scheduled")
    if not scheduled: continue

    try:
        # タイムゾーンがUTCの場合、+9時間が必要なケースが多いです
        # もし時間がズレるならここを調整: + timedelta(hours=9)
        sched_dt = datetime.fromisoformat(scheduled.replace("Z",""))
    except: continue

    if not is_target_arrival(sched_dt.time()):
        continue

    # 重複排除
    key = (scheduled, dep.get("iata"), flight.get("iata"))
    if key in seen: continue
    seen.add(key)

    # 時刻・遅延計算
    estimated = arr.get("estimated")
    delay = arr.get("delay")
    
    try:
        if estimated:
            est_dt = datetime.fromisoformat(estimated.replace("Z",""))
        elif delay:
            est_dt = sched_dt + timedelta(minutes=delay)
        else:
            continue
    except: continue

    diff_min = int((est_dt - sched_dt).total_seconds() / 60)
    if diff_min <= 0: continue # 遅延のみ抽出

    found = True
    
    # 日本語名取得
    city = CITY_MAP.get(dep.get("iata"), dep.get("iata") or "不明")
    code = (flight.get("iata") or "")[:2]
    airline_name = AIRLINE_MAP.get(code, airline.get("name") or "不明")
    flight_no = flight.get("iata") or "不明"
    terminal = arr.get("terminal") or "1"
    status_text = STATUS_MAP.get(f_status, "不明")

    # 遅延レベルに応じたバッジ
    delay_badge = "🔴 大幅遅延" if diff_min >= 60 else "🟡 遅延"

    # 個別フライトのレイアウト
    msg += (
        f"{delay_badge} (+{diff_min}分)\n"
        f"【{airline_name}】{flight_no}\n"
        f"📍 {city} 発\n"
        f"📢 {status_text} (T{terminal})\n"
        f"定刻: {sched_dt.strftime('%H:%M')}\n"
        f"予想: {est_dt.strftime('%H:%M')}\n"
        f"──────────────────\n"
    )

if found:
    send_line(msg)
else:
    # 夜間なので、静かにしたい場合はここをpassにしてもOK
    send_line("✅ 対象時間帯に遅延便はありません。")
