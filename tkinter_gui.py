
import tkinter as tk
from tkinter import messagebox
import os
import sys
import main_module as core

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

def on_recommend():
    result = core.recommend_by_transition()
    if not result:
        messagebox.showwarning("尚未分析", "請先執行『轉移分析』功能")
        return
    last_nums, top10, top5 = result
    msg = f"📅 最近一期號碼：{last_nums}\n"
    msg += f"🎯 推薦號碼（共 10 個）：{top10}\n"
    msg += f"🏆 機率最高前 5 名：{top5}"
    messagebox.showinfo("推薦結果", msg)

def open_file(path):
    if os.path.exists(path):
        os.startfile(path)
    else:
        messagebox.showwarning("找不到檔案", f"無法找到檔案：{path}")

# === UI ===
root = tk.Tk()
root.title("今彩539 資料分析工具")
root.geometry("420x480")
root.resizable(False, False)

font_btn = ("Microsoft JhengHei", 11)

tk.Label(root, text="🎯 今彩539 資料分析工具", font=("Microsoft JhengHei", 15, "bold")).pack(pady=12)

frame = tk.Frame(root)
frame.pack()

buttons = [
    ("📥 一鍵更新資料（歷史+今日）", on_update_all),
    ("📊 建立統計頁面", on_generate_stats),
    ("📈 產生 3 的倍數圖表", on_generate_chart),
    ("🔁 建立號碼轉移分析", on_generate_transition),
    ("🎯 顯示推薦號碼", on_recommend),
]

for text, cmd in buttons:
    b = tk.Button(frame, text=text, font=font_btn, width=32, command=cmd)
    b.pack(pady=5)

file_buttons = [
    ("📂 開啟 Excel 檔", lambda: open_file(core.EXCEL_FILE)),
    ("🖼️ 查看圖表圖片", lambda: open_file(core.CHART_FILE)),
    ("📄 查看轉移分析檔", lambda: open_file(core.TRANSITION_FILE)),
]

tk.Label(root, text="").pack()
for text, cmd in file_buttons:
    tk.Button(root, text=text, font=font_btn, width=32, command=cmd).pack(pady=2)

tk.Label(root, text="版本 1.2", fg="gray").pack(pady=8)

root.mainloop()
