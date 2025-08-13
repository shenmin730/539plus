import os
import io
import csv
import re
import math
import tempfile
import datetime
from bisect import bisect_right
from collections import Counter

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

import main_module as core

# ========== 全域設定 ==========
APP_VERSION = "v2.1 (Streamlit optimized)"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 在雲端環境避免寫入倉庫目錄，統一用可寫目錄
SAFE_DIR = os.environ.get("STREAMLIT_DATA_DIR") or tempfile.gettempdir()

HISTORY_FILE = os.path.join(SAFE_DIR, "recommend_history.txt")
HISTORY_CSV  = os.path.join(SAFE_DIR, "recommend_history.csv")

# 來自 core 的路徑（讀取時仍在專案目錄）
EXCEL_FILE = core.EXCEL_FILE
TRANSITION_FILE = core.TRANSITION_FILE
CHART_FILE = core.CHART_FILE  # 產圖片仍用 core 既有路徑

# ========== 共用工具 ==========
def _normalize_date(v):
    if isinstance(v, datetime.datetime): return v.date()
    if isinstance(v, datetime.date): return v
    if isinstance(v, str):
        s = v.strip()
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try: return datetime.datetime.strptime(s, fmt).date()
            except: pass
    return None

@st.cache_data(show_spinner=False, ttl=300)
def _load_all_draws():
    """載入全部開獎紀錄（快取 5 分鐘）"""
    wb = core.prepare_workbook()
    draws = []
    for sheet in sorted([s for s in wb.sheetnames if s.isdigit()]):
        ws = wb[sheet]
        for row in ws.iter_rows(min_row=2, values_only=True):
            dt = _normalize_date(row[0])
            if not dt: continue
            nums = [int(v) for v in row[1:6] if isinstance(v, (int, float))]
            if len(nums) == 5:
                draws.append((dt, set(nums)))
    draws.sort(key=lambda x: x[0])
    return draws

def _get_latest_draw():
    d = _load_all_draws()
    return d[-1] if d else (None, set())

def _parse_csv_date(s: str):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%Y-%m-%d %H:%M","%Y/%m/%d %H:%M","%Y-%m-%d %H:%M:%S","%Y/%m/%d %H:%M:%S"):
        try: return datetime.datetime.strptime(s, fmt).date()
        except: pass
    m = re.match(r"^\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        y, mth, d = map(int, m.groups())
        return datetime.date(y, mth, d)
    return None

def _download_bytes(name: str, data: bytes, label: str):
    st.download_button(label, data=data, file_name=name)

# ========== UI：側欄 ==========
st.sidebar.title("⚙️ 設定 / 工具")
with st.sidebar.expander("覆寫 config（選填）"):
    override_year_start = st.number_input("start_year", min_value=2004, max_value=2100, value=core.START_YEAR)
    override_year_end   = st.number_input("end_year",   min_value=2004, max_value=2100, value=core.END_YEAR)
    months_str = st.text_input("months（以逗號分隔 1~12）", ",".join(map(str, core.MONTHS)))
    apply_override = st.checkbox("使用以上覆寫參數", value=False, help="只影響本次更新資料")

st.sidebar.markdown("---")
if st.sidebar.button("🧹 清除快取（cache_data）"):
    st.cache_data.clear()
    st.sidebar.success("已清除快取")

if st.sidebar.button("🗑 清空推薦歷史檔(TXT/CSV)"):
    removed = []
    for p in (HISTORY_FILE, HISTORY_CSV):
        if os.path.exists(p):
            try:
                os.remove(p); removed.append(p)
            except Exception as e:
                st.sidebar.error(f"刪除失敗: {p}\n{e}")
    if removed:
        st.sidebar.success("已刪除：\n" + "\n".join(removed))
    else:
        st.sidebar.info("沒有可刪檔案")

st.sidebar.markdown("---")
st.sidebar.caption(f"{APP_VERSION}")

# ========== 主標題 ==========
st.title("🎯 今彩539 資料分析網頁版（優化）")
st.write("更新資料、建立號碼轉移分析、推薦號碼、對獎檢查與組合金額試算。")

# ========== 功能：更新資料 ==========
col1, col2 = st.columns(2)
with col1:
    if st.button("📥 一鍵更新資料（歷史+今日）"):
        try:
            if apply_override:
                # 動態覆寫 core 的設定（僅此行程有效，不改檔案）
                try:
                    core.START_YEAR = int(override_year_start)
                    core.END_YEAR   = int(override_year_end)
                    ms = [int(x) for x in re.split(r"[,\s]+", months_str) if x.strip()]
                    core.MONTHS = [m for m in ms if 1 <= m <= 12] or list(range(1,13))
                except Exception as e:
                    st.warning(f"覆寫參數解析失敗，使用預設設定。{e}")

            with st.spinner("更新歷史資料中…"):
                core.update_history()
            with st.spinner("更新今日資料中…"):
                updated_today = core.update_today()

            st.success("✅ 資料更新完成！")
            if updated_today:
                st.info("今天資料已更新。")
            else:
                st.info("今天尚未開獎或無資料。")

            st.cache_data.clear()  # 更新後刷新快取
        except Exception as e:
            st.error(f"更新失敗：{e}")

# ========== 功能：建立轉移分析 ==========
with col2:
    if st.button("🔁 建立號碼轉移分析"):
        try:
            with st.spinner("建立中…"):
                core.analyze_transition_patterns()
            st.success("✅ 轉移分析完成！")
        except Exception as e:
            st.error(f"分析失敗：{e}")

# ========== 功能：顯示推薦 ==========
st.markdown("### 🎯 顯示推薦號碼")
if st.button("產生推薦"):
    try:
        result = core.recommend_by_transition()
        if not result:
            st.warning("尚未有轉移分析結果，請先點『建立號碼轉移分析』")
        else:
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

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("寫入推薦歷史檔"):
                    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                        f.write(msg.replace("\n", " | ") + "\n")
                    if base_date:
                        with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
                            csv.writer(f).writerow([now_str, base_date.strftime("%Y-%m-%d"), ",".join(map(str, top5))])
                    st.success("已寫入歷史檔")
            with c2:
                if os.path.exists(HISTORY_FILE):
                    _download_bytes("recommend_history.txt",
                                    open(HISTORY_FILE, "rb").read(),
                                    "下載 TXT 歷史")
            with c3:
                if os.path.exists(HISTORY_CSV):
                    _download_bytes("recommend_history.csv",
                                    open(HISTORY_CSV, "rb").read(),
                                    "下載 CSV 歷史")
    except Exception as e:
        st.error(f"推薦失敗：{e}")

# ========== 功能：顯示推薦歷史 ==========
st.markdown("### 📚 推薦歷史")
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    st.text_area("（最新在上）", "".join(reversed(lines)), height=220)
else:
    st.caption("尚無推薦歷史紀錄")

# ========== 功能：檢查是否中獎 ==========
st.markdown("### 🔎 檢查推薦是否中獎（對照下一期）")
def _check_hits_df():
    if not os.path.exists(HISTORY_CSV):
        return pd.DataFrame(columns=["推薦時間","基準日期","對獎日期","中獎數","中獎號"])

    draws = _load_all_draws()
    if not draws:
        return pd.DataFrame(columns=["推薦時間","基準日期","對獎日期","中獎數","中獎號"])
    dates = [d[0] for d in draws]

    rows = []
    with open(HISTORY_CSV, "r", encoding="utf-8") as f:
        for ts_str, base_str, top5_str in csv.reader(f):
            base_dt = _parse_csv_date(base_str)
            if not base_dt:
                rows.append((ts_str, base_str, "日期格式錯誤", "-", "-")); continue
            try:
                rec_top5 = set(int(x) for x in top5_str.split(",") if x.strip().isdigit())
            except:
                rec_top5 = set()
            idx = bisect_right(dates, base_dt)
            if idx >= len(dates):
                rows.append((ts_str, base_str, "尚無下一期", "-", "-")); continue
            target_dt, target_nums = draws[idx]
            hits = sorted(rec_top5 & target_nums)
            rows.append((ts_str, base_dt.strftime("%Y-%m-%d"), target_dt.strftime("%Y-%m-%d"), len(hits), hits))
    df = pd.DataFrame(rows, columns=["推薦時間","基準日期","對獎日期","中獎數","中獎號"])
    return df

if st.button("開始檢查"):
    df_hits = _check_hits_df()
    st.dataframe(df_hits, use_container_width=True)
    if not df_hits.empty:
        csv_buf = io.StringIO()
        df_hits.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        _download_bytes("hits_check.csv", csv_buf.getvalue().encode("utf-8-sig"), "下載對獎結果")

# ========== 功能：組合與金額試算 ==========
st.markdown("### 💰 組合與金額試算")
with st.form("price_form"):
    nums_str = st.text_input("輸入號碼（用空白或逗號分隔，1~39）", "")
    c21, c22, c23, c24 = st.columns(4)
    p2 = c21.number_input("2星單注", min_value=0, value=50)
    p3 = c22.number_input("3星單注", min_value=0, value=50)
    p4 = c23.number_input("4星單注", min_value=0, value=50)
    p5 = c24.number_input("5星單注", min_value=0, value=50)
    calc = st.form_submit_button("計算組合與金額")

if calc:
    tokens = re.split(r"[,\s]+", nums_str.strip())
    ok, nums = True, []
    for t in tokens:
        if not t: continue
        if not t.isdigit(): ok=False; break
        v = int(t); 
        if not (1 <= v <= 39): ok=False; break
        nums.append(v)
    if not ok or len(nums)<2:
        st.error("請輸入 2 個以上介於 1~39 的整數（用空白或逗號分隔）")
    else:
        nums = sorted(set(nums)); n=len(nums)
        rows = []
        def comb(n,k): return math.comb(n,k) if n>=k else 0
        data = [("2星", comb(n,2), p2), ("3星", comb(n,3), p3),
                ("4星", comb(n,4), p4), ("5星", comb(n,5), p5)]
        total=0
        for star, cnt, price in data:
            sub = cnt*price; total += sub
            rows.append((star, cnt, price, sub))
        df_price = pd.DataFrame(rows, columns=["星別","組合數","單注金額","小計"])
        st.dataframe(df_price.style.format({"單注金額":"{:.0f}","小計":"{:.0f}"}), use_container_width=True)
        st.markdown(f"**總金額：{total:.0f}**")
        # 下載
        csv_buf = io.StringIO(); df_price.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        _download_bytes("price_calc.csv", csv_buf.getvalue().encode("utf-8-sig"), "下載試算表")

# ========== 功能：3 的倍數圖表 ==========
st.markdown("### 📈 產生並顯示 3 的倍數圖表")
if st.button("產生圖表"):
    try:
        core.generate_multiples_of_3_chart()
        if os.path.exists(core.CHART_FILE):
            st.image(core.CHART_FILE, caption="3 的倍數號碼出現次數")
        else:
            # 兼容雲端無法寫檔時，直接畫一次
            draws = _load_all_draws()
            counter = Counter()
            for _, nums in draws: counter.update(nums)
            x = list(range(3,40,3)); y=[counter.get(i,0) for i in x]
            plt.figure(figsize=(10,5))
            bars = plt.bar([str(i) for i in x], y)
            for b in bars:
                h=b.get_height(); plt.text(b.get_x()+b.get_width()/2,h+0.5,str(int(h)),ha="center",va="bottom",fontsize=9)
            plt.title("今彩539 - 3 的倍數號碼出現次數"); plt.xlabel("號碼"); plt.ylabel("出現次數")
            st.pyplot(plt.gcf())
        st.success("圖表完成")
    except Exception as e:
        st.error(f"產生圖表失敗：{e}")
