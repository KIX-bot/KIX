import requests
from datetime import datetime, time, timedelta, timezone
import json
import os

# 日本時間(JST)のタイムゾーン定義
JST = timezone(timedelta(hours=9))

# 環境変数（正しく設定されている必要があります）
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
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
    except Exception as e:
        print(f"LINE送信エラー: {e}")

def is_target_arrival(t):
    # 21:00以降、または 02:00以前
    return t >= time(21, 0) or t <= time(2, 0)

# ===== マッピングデータ（ここが抜けるとエラーになります） =====
CITY_MAP = {
    "HND": "東京（羽田）", "NRT": "東京（成田）", "ITM": "大阪（伊丹）",
    "CTS": "札幌（新千歳）", "FUK": "福岡", "OKA": "沖縄（那覇）",
    "MMY": "宮古", "ISG": "石垣", "SDJ": "仙台", "NGO": "名古屋",
    "HIJ": "広島", "KMI": "宮崎", "KOJ": "鹿児島",
    "ICN": "ソウル（仁川）", "GMP": "ソウル（金浦）", "PUS": "釜山",
    "PVG": "上海（浦東）", "SHA": "上海（虹橋）", "PEK": "北京（首都）",
    "PKX": "北京（大興）", "CAN": "広州", "SZX": "深圳",
    "TPE": "台北（桃園）", "TSA": "台北（松山）", "KHH": "高雄",
    "HKG": "香港", "MFM": "マカオ", "SIN": "シンガポール", 
    "BKK": "バンコク", "DMK": "バンコク", "KUL": "クアラルンプール",
    "MNL": "マニラ", "HAN": "ハノイ", "SGN": "ホーチミン",
    "CNS": "ケアンズ", "SYD": "シドニー", "MEL": "メルボルン",
    "BNE": "ブリスベン", "LAX": "ロサンゼルス", "SFO": "サンフランシスコ",
    "SEA": "シアトル", "YVR": "バンクーバー", "HNL": "ホノルル"
}

AIRLINE_MAP = {
    "NH": "ANA", "JL": "JAL", "MM": "Peach", "GK": "Jetstar",
    "BC": "スカイマーク", "6J": "ソラシドエア", "7G": "スターフライヤー",
    "KE": "大韓航空", "OZ": "アシアナ航空", "LJ": "ジンエアー",
    "TW": "ティーウェイ航空", "7C": "チェジュ航空",
    "BR": "エバー航空", "CI": "チャイナエアライン", "JX": "スターラックス",
    "MU": "中国東方航空", "CA": "中国国際航空", "CZ": "中国南方航空",
    "CX": "キャセイパシフィック", "SQ": "シンガポール航空", "TR": "スクート",
    "MH": "マレーシア航空", "TG": "タイ国際航空", "VN": "ベトナム航空",
    "UA": "ユナイテッド航空", "DL": "デルタ航空", "AA": "アメリカン航空",
    "HA": "ハワイアン航空"
}

STATUS_MAP = {
    "landed": "🛬 着陸済み",
    "active": "✈️ 運行中",
    "scheduled": "🕒 予定",
    "cancelled": "❌ 欠航",
    "incident": "⚠️ 異常あり"
}

# ===== メイン処理 =====
url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

try:
    res = requests.get(url, params=params).json()
except Exception as e:
    print(f"API取得エラー: {e}")
    res = {"data": []}

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
        # UTCをJSTに変換
        sched_utc = datetime.fromisoformat(scheduled_str.replace("Z", "+00:00"))
        sched_jst = sched_utc.astimezone(JST)
    except: continue

    # 日本時間で対象時間帯(21時〜2時)か判定
    if not is_target_arrival(sched_jst.time()):
        continue

    # 重複排除
    flight_iata = flight.get("iata") or "不明"
    key = (scheduled_str, dep.get("iata"), flight_iata)
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

    # 遅延計算
    diff_min = int((est_jst - sched_jst).total_seconds() / 60)
    if diff_min <= 0: continue

    found = True
    
    city = CITY_MAP.get(dep.get("iata"), dep.get("iata") or "不明")
    airline_name = AIRLINE_MAP.get((flight_iata)[:2], airline.get("name") or "不明")
    terminal = arr.get("terminal") or "1"
    status_text = STATUS_MAP.get(f.get("flight_status"), "不明")

    delay_badge = "🔴 大幅遅延" if diff_min >= 60 else "🟡 遅延"

    msg += (
        f"{delay_badge} (+{diff_min}分)\n"
        f"【{airline_name}】{flight_iata}\n"
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
