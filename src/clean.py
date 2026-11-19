import csv
import os

INPUT_FILE = r"D:\mycraft\pycharmProjects\test\开始接单!\74\盗窃罪_结构化数据.csv"
OUTPUT_FILE = r"D:\mycraft\pycharmProjects\test\开始接单!\74\盗窃罪_结构化数据_clean_title.csv"

def clean_by_title():
    if not os.path.exists(INPUT_FILE):
        print("❌ 输入文件不存在。")
        return

    seen_titles = set()
    total = 0
    kept = 0
    gender_removed = 0
    duplicate_removed = 0

    with open(INPUT_FILE, 'r', encoding='utf-8-sig') as f_in, \
         open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        header = next(reader, None)
        if not header:
            print("文件为空或缺少表头。")
            return
        writer.writerow(header)

        # 找列索引
        try:
            title_idx = header.index('标题')
        except ValueError:
            print("❌ 未找到'标题'列，无法按标题去重。")
            return
        try:
            gender_idx = header.index('被告人性别')
        except ValueError:
            print("❌ 未找到'被告人性别'列，无法过滤。")
            gender_idx = None

        for row in reader:
            total += 1
            # 过滤性别为空的行
            if gender_idx is not None and (len(row) <= gender_idx or row[gender_idx].strip() == ''):
                gender_removed += 1
                continue

            title = row[title_idx].strip() if len(row) > title_idx else ''
            # 按标题去重
            if title in seen_titles:
                duplicate_removed += 1
                continue
            seen_titles.add(title)
            writer.writerow(row)
            kept += 1

    print(f"✅ 清洗完成！")
    print(f"   总行数: {total}")
    print(f"   因性别为空删除: {gender_removed}")
    print(f"   因标题重复删除: {duplicate_removed}")
    print(f"   保留行数: {kept}")
    print(f"   输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    clean_by_title()