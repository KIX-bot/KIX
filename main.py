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

# ===== 都市 =====
CITY_MAP = {
    "HND": "東京（羽田）", "NRT": "東京（成田）", "ITM": "大阪（伊丹）",
    "CTS": "札幌（新千歳）", "FUK": "福岡", "OKA": "沖縄（那覇）",
    "MMY": "宮古", "ISG": "石垣", "SDJ": "仙台", "NGO": "名古屋（中部）",
    "HIJ": "広島", "KMI": "宮崎", "KOJ": "鹿児島",
    "ICN": "ソウル（仁川）", "GMP": "ソウル（金浦）", "PUS": "釜山",
    "PVG": "上海（浦東）", "SHA": "上海（虹橋）", "PEK": "北京（首都）",
    "PKX": "北京（大興）", "CAN": "広州", "SZX": "深圳",
    "TPE": "台北（桃園）", "TSA": "台北（松山）", "KHH": "高雄",
    "HKG": "香港", "MFM": "マカオ",
    "SIN": "シンガポール", "BKK": "バンコク（スワンナプーム）",
    "DMK": "バンコク（ドンムアン）", "KUL": "クアラルンプール",
    "MNL": "マニラ", "HAN": "ハノイ", "SGN": "ホーチミン",
    "CNS": "ケアンズ", "SYD": "シドニー", "MEL": "メルボルン",
    "BNE": "ブリスベン", "LAX": "ロサンゼルス", "SFO": "サンフランシスコ",
    "SEA": "シアトル", "YVR": "バンクーバー", "HNL": "ホノルル"
}

# ===== 航空会社 =====
AIRLINE_MAP = {
    "NH": "ANA", "JL": "JAL", "MM": "Peach", "GK": "Jetstar",
    "BC": "スカイマーク", "6J": "ソラシドエア", "7G": "スターフライヤー",
    "EH": "ANAウイングス",
    "KE": "大韓航空", "OZ": "アシアナ航空", "LJ": "ジンエアー",
    "TW": "ティーウェイ航空", "7C": "チェジュ航空",
    "BR": "エバー航空", "CI": "チャイナエアライン", "JX": "スターラックス航空",
    "MU": "中国東方航空", "CA": "中国国際航空", "CZ": "中国南方航空",
    "FM": "上海航空", "HO": "吉祥航空",
    "CX": "キャセイパシフィック", "HX": "香港航空",
    "SQ": "シンガポール航空", "TR": "スクート", "MH": "マレーシア航空",
    "AK": "エアアジア", "FD": "タイ・エアアジア", "TG": "タイ国際航空",
    "VN": "ベトナム航空", "VJ": "ベトジェットエア",
    "PR": "フィリピン航空", "5J": "セブパシフィック",
    "UA": "ユナイテッド航空", "DL": "デルタ航空", "AA": "アメリカン航空",
    "AF": "エールフランス", "LH": "ルフトハンザ", "BA": "ブリティッシュ・エアウェイズ",
    "QF": "カンタス航空", "JQ": "ジェットスター航空（豪州）",
    "VA": "ヴァージン・オーストラリア",
    "HA": "ハワイアン航空", "AS": "アラスカ航空"
}

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATION_API_KEY,
    "arr_iata": "KIX"
}

res = requests.get(url, params=params).json()

msg = "🛫関西国際空港 到着遅延便🛫\n\n（21:00〜翌2:00）\n\n"
found = False
seen = set()

for f in res.get("data", []):
    arr = f.get("arrival", {})
    dep = f.get("departure", {})
    flight = f.get("flight", {})
    airline = f.get("airline", {})

    scheduled = arr.get("scheduled")
    delay = arr.get("delay")
    estimated = arr.get("estimated")

    if not scheduled:
        continue

    try:
        sched_dt = datetime.fromisoformat(scheduled.replace("Z",""))
    except:
        continue

    if not is_target_arrival(sched_dt.time()):
        continue

    # 重複排除
    key = (scheduled, dep.get("iata"))
    if key in seen:
        continue
    seen.add(key)

    # ===== 時刻（最重要修正）=====
    try:
        if estimated:
            est_dt = datetime.fromisoformat(estimated.replace("Z",""))
        elif delay:
            est_dt = sched_dt + timedelta(minutes=delay)
        else:
            continue
    except:
        continue

    diff_min = int((est_dt - sched_dt).total_seconds() / 60)

    # 遅延のみ
    if diff_min <= 0:
        continue

    found = True

    scheduled_time = sched_dt.strftime("%H:%M")
    estimated_time = est_dt.strftime("%H:%M")

    # 都市
    city = CITY_MAP.get(dep.get("iata"), dep.get("iata") or "不明")

    # 航空会社
    airline_name = airline.get("name")
    if not airline_name:
        code = (flight.get("iata") or "")[:2]
        airline_name = AIRLINE_MAP.get(code, code)

    # 便名
    flight_no = flight.get("iata") or flight.get("number") or "不明"

    terminal = arr.get("terminal") or "1"

    msg += (
        f"🔵【{airline_name}】{flight_no} | {city}\n"
        f"到着ターミナル: T{terminal}\n"
        f"定刻: {scheduled_time} → {estimated_time}\n"
        f"{diff_min}分遅延\n\n"
    )

if found:
    send_line(msg)
else:
    send_line("対象時間帯（21:00〜翌2:00）の遅延便はありません。")
