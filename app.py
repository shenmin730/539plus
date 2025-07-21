import streamlit as st
import main_module as core  # 請確定 main_module.py 跟 app.py 同目錄，且功能皆可正常呼叫

st.set_page_config(page_title="今彩539 ML 網頁介面", layout="centered")

st.title("🎯 今彩539 ML 網頁介面")

st.write("本介面可更新資料、分析號碼轉移、推薦號碼及產生圖表。")

# 按鈕：更新資料（歷史+今日）
if st.button("📥 更新歷史+今日資料"):
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
            st.error(f"更新資料失敗：{e}")

# 按鈕：執行號碼轉移分析
if st.button("🔁 進行號碼轉移分析"):
    with st.spinner("分析中，請稍候..."):
        try:
            core.analyze_transition_patterns()
            st.success("號碼轉移分析完成！")
        except Exception as e:
            st.error(f"分析失敗：{e}")

# 按鈕：推薦號碼
if st.button("🎯 顯示推薦號碼"):
    try:
        result = core.recommend_by_transition()
        if not result:
            st.warning("尚未有轉移分析結果，請先執行轉移分析。")
        else:
            last_nums, top10, top5 = result
            st.markdown(f"**📅 最近一期號碼：** {last_nums}")
            st.markdown(f"**🎯 推薦號碼（共 10 個）：** {top10}")
            st.markdown(f"**🏆 機率最高前 5 名：** {top5}")
    except Exception as e:
        st.error(f"推薦失敗：{e}")

# 按鈕：產生並顯示 3 的倍數圖表
if st.button("📈 產生並顯示 3 的倍數圖表"):
    with st.spinner("產生圖表中，請稍候..."):
        try:
            core.generate_multiples_of_3_chart()
            st.image(core.CHART_FILE, caption="3 的倍數號碼出現次數")
            st.success("圖表已產生並顯示。")
        except Exception as e:
            st.error(f"產生圖表失敗：{e}")
