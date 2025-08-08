import streamlit as st
import main_module as core
import datetime
import os
import csv
import re
import math
from bisect import bisect_right

# === 路徑與檔名（固定寫在程式同一資料夾） ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "recommend_history.txt")   # 人類可讀
HISTORY_CSV  = os.path.join(BASE_DIR, "recommend_history.csv")   # 機器可讀（對獎用）

# ---------- 開獎資料讀取輔助 ----------

def _normalize_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str):
        s = v.strip()
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except Exception:
                pass
    return None

def _get_all_draws():
    wb = core.prepare_workbook()
    draws = []
    for sheet in sorted([s for s in wb.sheetnames if s.isdigit()]):
        ws = wb[sheet]
        for row in ws.iter_rows(min_row=2, values_only=True):
            dt = _normalize_date(row[0])
            if not dt:
                continue
            nums = []
            for val in row[1:6]:
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    nums.append(int(val))
            if len(nums) == 5:
                draws.append((dt, set(nums)))
    draws.sort(key=lambda x: x[0])
    return draws

def _get_latest_draw():
    draws = _get_all_draws()
    return draws[-1] if draws else (None, set())

def _parse_csv_date(s: str):
    s = (s or "").strip()
    fmts = (
        "%Y-%m-%d", "%Y/%m/%d",
        "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
    )
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    m = re.match(r"^\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        y, mth, d = map(int, m.groups())
        return datetime.date(y, mth, d)
    return None

# ---------- 推薦 / 歷史 / 檢查命中 ----------

def recommend():
    result = core.recommend_by_transition()
    if not result:
        st.warning("尚未分析轉移資料，請先執行『轉移分析』功能")
        return
    last_nums, top10, top5 = result
    top3_m3 = [n for n in top10 if n % 3 == 0][:3]
    base_date, _ = _get_latest_draw()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"🕒 {now_str}\n"
        f"📅 最近一期號碼：{tuple(last_nums)}\n"
        f"🎯 推薦號碼（10）：{top10}\n"
        f"🏆 機率最高前 5：{top5}\n"
        f"🔢 3 的倍數前三：{top3_m3}"
    )
    st.text_area("推薦結果", msg, height=130)

    # 寫入推薦歷史（可選擇按鈕啟動）
    if st.button("將本次推薦寫入歷史檔"):
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(msg.replace("\n", " | ") + "\n")
        if base_date:
            with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([now_str, base_date.strftime("%Y-%m-%d"),
                                 ",".join(map(str, top5))])
        st.success("推薦結果已寫入歷史檔")

def show_history_recommend():
    if not os.path.exists(HISTORY_FILE):
        st.info("尚無推薦歷史紀錄")
        return
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    st.text_area("推薦歷史紀錄 (最新在上)", "".join(reversed(lines)), height=300)

def clear_history():
    removed = []
    for path in (HISTORY_FILE, HISTORY_CSV):
        if os.path.exists(path):
            try:
                os.remove(path)
                removed.append(path)
            except Exception as e:
                st.error(f"清除失敗: {path}\n{e}")
                return
    if removed:
        st.success("已刪除：\n" + "\n".join(removed))
    else:
        st.info("沒有歷史檔案可刪除")

def check_hits():
    if not os.path.exists(HISTORY_CSV):
        st.info("尚無推薦歷史（CSV）")
        return
    draws = _get_all_draws()
    if not draws:
        st.warning("請先更新開獎歷史資料")
        return
    dates = [d[0] for d in draws]

    rows = []
    with open(HISTORY_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for r in reader:
            if len(r) < 3:
                continue
            ts_str, base_str, top5_str = r[0], r[1], r[2]
            base_dt = _parse_csv_date(base_str)
            if not base_dt:
                rows.append((ts_str, base_str, "日期格式錯誤", "-", "-"))
                continue
            try:
                rec_top5 = set(int(x) for x in top5_str.split(",") if x.strip().isdigit())
            except Exception:
                rec_top5 = set()
            idx = bisect_right(dates, base_dt)
            if idx >= len(dates):
                rows.append((ts_str, base_str, "尚無下一期", "-", "-"))
                continue
            target_dt, target_nums = draws[idx]
            hits = sorted(rec_top5.intersection(target_nums))
            rows.append((ts_str, base_dt.strftime("%Y-%m-%d"), target_dt.strftime("%Y-%m-%d"), str(len(hits)), str(hits)))

    import pandas as pd
    df = pd.DataFrame(rows, columns=["推薦時間", "基準日期", "對獎日期", "中獎數", "中獎號"])
    st.dataframe(df.style.set_properties(**{'text-align': 'center'}))

# ---------- 新功能：組合與金額計算 ----------

def parse_numbers(s: str):
    tokens = re.split(r"[,\s]+", (s or "").strip())
    nums = []
    for t in tokens:
        if not t:
            continue
        if not t.isdigit():
            st.error("請只輸入數字（用空白或逗號分隔）")
            return []
        v = int(t)
        if not (1 <= v <= 39):
            st.error("號碼必須介於 1~39")
            return []
        nums.append(v)
    if len(nums) < 2:
        st.error("請至少輸入 2 個號碼")
        return []
    return sorted(set(nums))

def calc_price():
    st.write("### 輸入號碼（用空白或逗號分隔）")
    nums_str = st.text_input("號碼", "")
    if not nums_str:
        return
    nums = parse_numbers(nums_str)
    if not nums:
        return
    n = len(nums)
    price_defaults = {"2星": 80, "3星": 80, "4星": 80, "5星": 80}
    st.write("### 單注金額設定")
    price_inputs = {}
    cols = st.columns(4)
    for i, star in enumerate(["2星", "3星", "4星", "5星"]):
        price_inputs[star] = cols[i].number_input(f"{star} 單注金額", min_value=0, value=price_defaults[star])

    total = 0
    rows = []
    for k, star in zip(range(2, 6), ["2星", "3星", "4星", "5星"]):
        count = math.comb(n, k) if n >= k else 0
        price = price_inputs[star]
        subtotal = count * price
        rows.append((star, count, price, subtotal))
        total += subtotal

    import pandas as pd
    df = pd.DataFrame(rows, columns=["星別", "組合數", "單注金額", "小計"])
    st.dataframe(df.style.format({"單注金額": "{:.0f}", "小計": "{:.0f}"}))
    st.markdown(f"**總金額：{total:.0f}**")

# =========================
# Streamlit UI
# =========================

st.title("🎯 今彩539 資料分析網頁版")
st.write("本介面可更新資料、分析號碼轉移、推薦號碼及產生圖表。")

if st.button("📥 一鍵更新資料（歷史+今日）"):
    with st.spinner("資料更新中，請稍候..."):
        try:
            core.update_history()
            updated = core.update_today()
            st.success("資料更新完成！")
            if updated:
                st.info("今天資料已更新。")
            else:
                st.info("今天尚未開獎或無資料。")
        except Exception as e:
            st.error(f"更新失敗：{e}")

if st.button("🔁 建立號碼轉移分析"):
    with st.spinner("分析中，請稍候..."):
        try:
            core.analyze_transition_patterns()
            st.success("轉移分析完成！")
        except Exception as e:
            st.error(f"分析失敗：{e}")

if st.button("🎯 顯示推薦號碼"):
    recommend()

if st.button("📚 顯示推薦歷史"):
    show_history_recommend()

if st.button("🔎 檢查推薦是否中獎（對照下一期）"):
    check_hits()

if st.button("💰 計算組合與金額"):
    calc_price()

if st.button("📈 產生並顯示 3 的倍數圖表"):
    try:
        core.generate_multiples_of_3_chart()
        st.image(core.CHART_FILE, caption="3 的倍數號碼出現次數")
        st.success("圖表已產生")
    except Exception as e:
        st.error(f"產生圖表失敗：{e}")
