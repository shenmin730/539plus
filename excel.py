# excel.py

import pandas as pd
from config import EXCEL_FILE

def load_history_data(window=20):
    """
    讀取 EXCEL_FILE 中所有年度分頁，把開獎號碼攤平成 DataFrame，
    並計算各種統計特徵：
      - sum, span, odd_even_ratio, prime_count, high_low_ratio, consecutive_pairs, gap_mean
      - recent_count: 過去 window 期內該號碼出現次數
    最後回傳長格式（每一列是一個號碼 + 該行所有特徵）。
    """
    # 讀所有分頁
    all_sheets = pd.read_excel(EXCEL_FILE, sheet_name=None)
    history = []
    for name, df in all_sheets.items():
        if name.isdigit():
            # 假設第一欄是日期，其後 5 欄是號碼
            for _, row in df.iterrows():
                nums = list(row.iloc[1:6])
                history.append(nums)
    # 轉成 DataFrame
    df = pd.DataFrame(history, columns=['n1','n2','n3','n4','n5'])
    # 展平
    records = []
    prime_set = {2,3,5,7,11,13,17,19,23,29,31,37}
    for idx, row in df.iterrows():
        nums = row.values.tolist()
        s = sum(nums)
        sp = max(nums)-min(nums)
        odd = sum(n%2==1 for n in nums)
        even = 5-odd
        primes = sum(n in prime_set for n in nums)
        highs = sum(n>20 for n in nums)
        lows = 5-highs
        consec = sum(1 for i in range(4) if abs(nums[i+1]-nums[i])==1)
        gaps = [abs(nums[i+1]-nums[i]) for i in range(4)]
        gap_mean = sum(gaps)/len(gaps)
        # 過去 window 期 recent_count
        recent_slice = df.iloc[max(0, idx-window):idx]
        flat = recent_slice.values.flatten().tolist()
        for num in nums:
            records.append({
                'number': num,
                'sum': s,
                'span': sp,
                'odd_even_ratio': odd/(even or 1),
                'prime_count': primes,
                'high_low_ratio': highs/(lows or 1),
                'consecutive_pairs': consec,
                'gap_mean': gap_mean,
                'recent_count': flat.count(num)
            })
    return pd.DataFrame(records)
