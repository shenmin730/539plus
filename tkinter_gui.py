import tkinter as tk
from tkinter import messagebox, ttk
import datetime, os, csv, re, math
from bisect import bisect_right
import main_module as core

# === 路徑與檔名（固定寫在程式同一資料夾） ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "recommend_history.txt")   # 人類可讀
HISTORY_CSV  = os.path.join(BASE_DIR, "recommend_history.csv")   # 機器可讀（對獎用）


# =========================
# 工具與核心動作（函式）
# =========================

def run_and_alert(func, success_msg="✅ 完成", fail_msg="⚠️ 發生錯誤"):
    try:
        func()
        messagebox.showinfo("執行完成", success_msg)
    except Exception as e:
        messagebox.showerror("錯誤", f"{fail_msg}\n{e}")

def on_update_all():
    run_and_alert(core.update_history, "✅ 歷史資料已更新")
    ok = core.update_today()
    if ok:
        messagebox.showinfo("✅", "今天資料已更新")
    else:
        messagebox.showwarning("⚠️", "今天尚未開獎或無資料")

def on_generate_stats():
    run_and_alert(core.generate_stats, "✅ 統計已完成")

def on_generate_chart():
    run_and_alert(core.generate_multiples_of_3_chart, "✅ 圖表已產出")

def on_generate_transition():
    run_and_alert(core.analyze_transition_patterns, "✅ 轉移分析完成")


# ---------- 開獎資料讀取輔助 ----------

def _normalize_date(v):
    """把 Excel 讀到的日期單元轉成 datetime.date；字串也嘗試解析。"""
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
    """
    回傳依日期排序的開獎清單：
    [(date(YYYY-MM-DD), set{5個號碼}), ...]
    """
    wb = core.prepare_workbook()
    draws = []
    for sheet in sorted([s for s in wb.sheetnames if s.isdigit()]):
        ws = wb[sheet]
        for row in ws.iter_rows(min_row=2, values_only=True):
            dt = _normalize_date(row[0])  # 第一欄日期
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
    """回傳 (最新日期, 最新五號碼set)；若無資料回 (None, set())"""
    draws = _get_all_draws()
    return draws[-1] if draws else (None, set())

def _parse_csv_date(s: str):
    """允許 YYYY-MM-DD / YYYY/M/D / 含時間 的多種格式（CSV用）"""
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

def on_recommend():
    """
    顯示推薦號碼：使用 core.recommend_by_transition()
    並同時寫入：
      - recommend_history.txt（人類可讀）
      - recommend_history.csv（機器可讀，之後用來比對下一期是否中獎）
    """
    try:
        result = core.recommend_by_transition()
        if not result:
            messagebox.showwarning("尚未分析", "請先執行『轉移分析』功能")
            return

        last_nums, top10, top5 = result
        top3_m3 = [n for n in top10 if n % 3 == 0][:3]

        # 這次推薦的「基準日期」：目前 Excel 最新一期；之後用「下一期」來對獎
        base_date, _ = _get_latest_draw()   # datetime.date

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"🕒 {now_str}\n"
            f"📅 最近一期號碼：{tuple(last_nums)}\n"
            f"🎯 推薦號碼（10）：{top10}\n"
            f"🏆 機率最高前 5：{top5}\n"
            f"🔢 3 的倍數前三：{top3_m3}"
        )
        messagebox.showinfo("推薦結果", msg)

        # 人類可讀歷史
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(msg.replace("\n", " | ") + "\n")

        # 機器可讀歷史（用來對獎）：timestamp, base_date, top5
        if base_date:
            with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([now_str, base_date.strftime("%Y-%m-%d"),
                                 ",".join(map(str, top5))])

    except Exception as e:
        messagebox.showerror("on_recommend 發生例外", str(e))

def on_show_history_recommend():
    """顯示『人類可讀』推薦歷史（recommend_history.txt）"""
    if not os.path.exists(HISTORY_FILE):
        messagebox.showinfo("尚無紀錄", "目前沒有任何推薦歷史")
        return

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    hist_win = tk.Toplevel(root)
    hist_win.title("推薦歷史紀錄")
    hist_win.geometry("600x420")
    txt = tk.Text(hist_win, wrap="none")
    txt.pack(fill=tk.BOTH, expand=True)
    vsb = ttk.Scrollbar(hist_win, orient="vertical", command=txt.yview)
    hsb = ttk.Scrollbar(hist_win, orient="horizontal", command=txt.xview)
    txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)

    for line in reversed(lines):  # 最新在上
        txt.insert("end", line)

def on_clear_history():
    """清除兩種歷史：txt + csv"""
    removed = []
    for path in (HISTORY_FILE, HISTORY_CSV):
        if os.path.exists(path):
            try:
                os.remove(path)
                removed.append(path)
            except Exception as e:
                messagebox.showerror("清除失敗", f"{path}\n{e}")
                return
    if removed:
        messagebox.showinfo("清除完成", "已刪除：\n" + "\n".join(removed))
    else:
        messagebox.showinfo("無檔案", "目前沒有任何推薦歷史檔案")

def on_check_hits():
    """
    逐筆推薦對照『下一期』是否中獎（以 top5 為準）
    來源：recommend_history.csv 的 (timestamp, base_date, top5)
    """
    if not os.path.exists(HISTORY_CSV):
        messagebox.showinfo("尚無紀錄", "目前沒有任何推薦歷史（CSV）")
        return

    # 載入所有開獎
    draws = _get_all_draws()
    if not draws:
        messagebox.showwarning("沒有開獎資料", "請先更新 Excel 歷史資料")
        return
    dates = [d[0] for d in draws]  # 排序好的所有日期（datetime.date）

    rows = []
    with open(HISTORY_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for r in reader:
            if len(r) < 3:
                continue
            ts_str, base_str, top5_str = r[0], r[1], r[2]

            # 解析基準日期（相容 2025-08-08 / 2025/8/8 等）
            base_dt = _parse_csv_date(base_str)
            if not base_dt:
                rows.append((ts_str, base_str, "（日期格式錯誤）", "-", "-"))
                continue

            # 解析推薦 top5 集合
            try:
                rec_top5 = set(int(x) for x in top5_str.split(",") if x.strip().isdigit())
            except Exception:
                rec_top5 = set()

            # 找『下一期』：第一個日期 > base_dt
            idx = bisect_right(dates, base_dt)
            if idx >= len(dates):
                rows.append((ts_str, base_str, "（尚無下一期）", "-", "-"))
                continue

            target_dt, target_nums = draws[idx]
            hits = sorted(rec_top5.intersection(target_nums))
            rows.append((
                ts_str,
                base_dt.strftime("%Y-%m-%d"),
                target_dt.strftime("%Y-%m-%d"),
                f"{len(hits)}",
                str(hits)
            ))

    # 顯示檢查結果
    win = tk.Toplevel(root)
    win.title("推薦中獎檢查（對照下一期）")
    win.geometry("760x460")

    cols = ("推薦時間", "基準日期", "對獎日期", "中獎數", "中獎號")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=18)
    for c, w in zip(cols, (160, 100, 100, 80, 280)):
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor="center")
    tree.pack(fill=tk.BOTH, expand=True)

    for row in reversed(rows):  # 最新在上
        tree.insert("", "end", values=row)


# ---------- 新功能：組合與金額計算 ----------

def _parse_numbers(s: str):
    """把輸入字串轉成不重複、排序好的號碼清單（支援逗號/空白分隔）"""
    tokens = re.split(r"[,\s]+", (s or "").strip())
    nums = []
    for t in tokens:
        if not t:
            continue
        if not t.isdigit():
            raise ValueError("請只輸入數字（可用空白或逗號分隔）")
        v = int(t)
        if not (1 <= v <= 39):
            raise ValueError("號碼必須介於 1~39")
        nums.append(v)
    if len(nums) < 2:
        raise ValueError("請至少輸入 2 個號碼")
    return sorted(set(nums))

def on_calc_price():
    """開視窗計算 2星/3星/4星/5星 組合數與金額"""
    win = tk.Toplevel(root)
    win.title("組合與金額計算")
    win.geometry("560x430")

    tk.Label(win, text="輸入號碼（用空白或逗號分隔）").pack(anchor="w", padx=10, pady=(10, 0))
    ent_nums = tk.Entry(win)
    ent_nums.pack(fill="x", padx=10)

    # 單注金額設定
    frm_price = tk.Frame(win)
    frm_price.pack(fill="x", padx=10, pady=8)
    price_entries = {}
    defaults = {"2星": 50, "3星": 50, "4星": 50, "5星": 50}
    for col, star in enumerate(["2星", "3星", "4星", "5星"]):
        tk.Label(frm_price, text=f"{star} 單注").grid(row=0, column=col, padx=6)
        e = tk.Entry(frm_price, width=8, justify="center")
        e.insert(0, str(defaults[star]))
        e.grid(row=1, column=col, padx=6)
        price_entries[star] = e

    # 結果表
    cols = ("星別", "組合數", "單注金額", "小計")
    tree = ttk.Treeview(win, columns=cols, show="headings", height=6)
    for c, w in zip(cols, (80, 100, 100, 140)):
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor="center")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    total_var = tk.StringVar(value="總金額：0")
    tk.Label(win, textvariable=total_var, font=("Microsoft JhengHei", 12, "bold")).pack(pady=(0, 6))

    def do_calc():
        try:
            nums = _parse_numbers(ent_nums.get())
            n = len(nums)
            if n < 2:
                messagebox.showwarning("輸入不足", "至少輸入 2 個號碼")
                return

            # 清空表格
            for item in tree.get_children():
                tree.delete(item)

            total = 0
            for k, star in zip(range(2, 6), ["2星", "3星", "4星", "5星"]):
                count = math.comb(n, k) if n >= k else 0
                try:
                    price = float(price_entries[star].get() or 0)
                except Exception:
                    price = 0.0
                subtotal = int(round(count * price))
                tree.insert("", "end", values=(star, count, price, subtotal))
                total += subtotal

            total_var.set(f"總金額：{total}")

        except Exception as e:
            messagebox.showerror("格式錯誤", str(e))

    tk.Button(win, text="計算", command=do_calc).pack(pady=6)


# =========================
# UI
# =========================

root = tk.Tk()
root.title("今彩539 資料分析工具")
root.geometry("460x760")
root.resizable(False, False)

font_btn = ("Microsoft JhengHei", 11)

tk.Label(root,
         text="🎯 今彩539 資料分析工具",
         font=("Microsoft JhengHei", 16, "bold")
         ).pack(pady=12)

frame = tk.Frame(root)
frame.pack()

# 主功能按鈕
buttons = [
    ("📥 一鍵更新資料（歷史+今日）", on_update_all),
    ("🔁 建立號碼轉移分析", on_generate_transition),
    ("🎯 顯示推薦號碼", on_recommend),
    ("📚 顯示推薦歷史", on_show_history_recommend),
    ("🔎 檢查推薦是否中獎（對照下一期）", on_check_hits),
    ("💰 計算組合與金額", on_calc_price),       # ← 新增
    ("🗑️ 清除推薦歷史（TXT+CSV）", on_clear_history),
]
for text, cmd in buttons:
    tk.Button(frame, text=text, font=font_btn, width=36, command=cmd).pack(pady=5)

# 版本資訊
tk.Label(root, text="版本 1.5", fg="gray").pack(pady=10)

# 啟動
root.mainloop()
