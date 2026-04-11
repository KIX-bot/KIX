# ===== 時刻処理 =====
scheduled_time = sched_dt.strftime("%H:%M")

if estimated:
    try:
        est_dt = datetime.fromisoformat(estimated.replace("Z",""))
        estimated_time = est_dt.strftime("%H:%M")
    except:
        est_dt = sched_dt + timedelta(minutes=delay)
        estimated_time = est_dt.strftime("%H:%M")
else:
    est_dt = sched_dt + timedelta(minutes=delay)
    estimated_time = est_dt.strftime("%H:%M")

# ===== 差分計算（ここが重要）=====
diff_min = int((est_dt - sched_dt).total_seconds() / 60)

if diff_min > 0:
    delay_text = f"{diff_min}分遅延"
elif diff_min < 0:
    delay_text = f"{abs(diff_min)}分早着"
else:
    delay_text = "定刻"
