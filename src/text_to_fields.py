import pandas as pd
import re
import os
from pathlib import Path

# ==================== 提取函数 ====================
def extract_birth_year(text):
    if pd.isna(text):
        return None
    text = str(text)
    patterns = [
        r'出生于\s*(\d{4})',
        r'出生\s*[：:]\s*(\d{4})',
        r'[（(](\d{4})年\d{1,2}月',
        r'(\d{4})年\d{1,2}月\d{1,2}日',
        r'男,\s*(\d{4})',
        r'女,\s*(\d{4})',
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return int(match.group(1))
    return None

def extract_theft_amount(text):
    if pd.isna(text):
        return None
    text = str(text)
    patterns = [
        r'现金共(\d+)\s*元',
        r'盗窃[^，。]*?(\d+)\s*元',   # 较宽松的匹配
        r'窃取.*?(\d+)\s*元',
        r'涉案金额.*?(\d+)\s*元',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if match:
            amount = int(match.group(1))
            # 过滤异常金额（例如小于10元可能不是盗窃数额）
            if amount >= 10:
                return amount
    return None

# ==================== 处理单个文件 ====================
def process_file(file_path, columns_map=None):
    """
    读取一个Excel文件，提取出生年份和盗窃金额，返回DataFrame。
    columns_map: 可选，指定'全文'列名、'出生年份'列名、'盗窃金额'列名
    """
    df = pd.read_excel(file_path, engine='openpyxl')
    # 如果文件中没有'全文'列，跳过
    if '全文' not in df.columns:
        print(f"警告：文件 {file_path} 没有'全文'列，跳过")
        return None

    # 确定目标列名（如果不存在则创建）
    birth_col = columns_map.get('birth', '出生年份') if columns_map else '出生年份'
    amount_col = columns_map.get('amount', '盗窃金额') if columns_map else '盗窃金额'

    if birth_col not in df.columns:
        df[birth_col] = None
    if amount_col not in df.columns:
        df[amount_col] = None

    # 逐行提取
    for idx, row in df.iterrows():
        full = row.get('全文')
        if pd.isna(full):
            continue
        # 出生年份
        if pd.isna(row.get(birth_col)):
            year = extract_birth_year(full)
            if year:
                df.at[idx, birth_col] = year
        # 盗窃金额
        if pd.isna(row.get(amount_col)):
            amount = extract_theft_amount(full)
            if amount:
                df.at[idx, amount_col] = amount

    return df

# ==================== 批量处理与追加合并 ====================
def merge_extracted_data(input_files, output_file, columns_map=None):
    """
    输入文件列表，合并提取后的数据到 output_file。
    columns_map: 指定列名映射，例如 {'full':'全文', 'birth':'出生年份', 'amount':'盗窃金额'}
    """
    all_dfs = []
    for f in input_files:
        if not os.path.exists(f):
            print(f"文件不存在：{f}")
            continue
        print(f"正在处理：{f}")
        df = process_file(f, columns_map)
        if df is not None and not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        print("没有有效数据可合并。")
        return

    # 合并所有DataFrame（按行拼接）
    merged = pd.concat(all_dfs, ignore_index=True)

    # 如果输出文件已存在，可选择追加（保留原有数据，仅追加新行）
    # 但这里直接覆盖写（或另存为新文件），若需追加可先读取原文件再合并
    if os.path.exists(output_file):
        # 追加模式：读取原文件，与新数据合并去重（可自行决定是否去重）
        existing = pd.read_excel(output_file, engine='openpyxl')
        merged = pd.concat([existing, merged], ignore_index=True).drop_duplicates()
        print(f"已存在 {output_file}，将追加新数据（自动去重）")

    merged.to_excel(output_file, index=False, engine='openpyxl')
    print(f"合并完成，结果保存至：{output_file}，共 {len(merged)} 行")

# ==================== 主程序 ====================
if __name__ == "__main__":
    # 请修改为您的三个文件路径
    files_to_process = [
        r"C:\Users\繁\OneDrive\文档\xwechat_files\wxid_ectzkf8isdsh22_2a63\msg\file\2026-07\盗窃罪_结构化数据_clean_美化版_part001_已填充.xlsx",
        r"C:\Users\繁\OneDrive\文档\xwechat_files\wxid_ectzkf8isdsh22_2a63\msg\file\2026-07\盗窃罪_结构化数据_clean_美化版_part002_已填充.xlsx",
        r"C:\Users\繁\OneDrive\文档\xwechat_files\wxid_ectzkf8isdsh22_2a63\msg\file\2026-07\盗窃罪_结构化数据_clean_美化版_part003_已填充.xlsx",
    ]

    # 输出汇总文件
    output_filename = 'merged_data.xlsx'

    # 如果列名不同，可在此映射（比如有些文件列名为‘出生年’）
    col_mapping = {
        'full': '全文',
        'birth': '出生年份',
        'amount': '盗窃金额'
    }

    merge_extracted_data(files_to_process, output_filename, col_mapping)