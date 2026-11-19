import requests
import time
import os
import requests
import base64
import json
import csv
import re
import random
from urllib.parse import urlencode
from datetime import datetime
from Crypto.Cipher import DES3
from Crypto.Util.Padding import unpad
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def decrypt_result(result_b64, secret_key):
    try:
        key = secret_key.encode('utf-8')
        if len(key) < 24:
            key = key.ljust(24, b'\x00')
        elif len(key) > 24:
            key = key[:24]

        iv_str = datetime.now().strftime('%Y%m%d')
        iv = iv_str.encode('utf-8')
        if len(iv) < 8:
            iv = iv.ljust(8, b'\x00')
        elif len(iv) > 8:
            iv = iv[:8]

        cipher = DES3.new(key, DES3.MODE_CBC, iv)
        encrypted = base64.b64decode(result_b64)
        decrypted = cipher.decrypt(encrypted)
        plaintext = unpad(decrypted, DES3.block_size).decode('utf-8')
        return plaintext
    except Exception as e:
        raise Exception(f"解密失败: {e}")

url = "https://wenshu.court.gov.cn/website/parse/rest.q4w"

# ---------- 替换后的 headers（与最新 curl 完全一致） ----------
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://wenshu.court.gov.cn",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Referer": "https://wenshu.court.gov.cn/website/wenshu/181107ANFZ0BXSK4/index.html?docId=TEBb1cfvywxQ0h+BrotfiXks/Uyyj0lLBhyrr1bFbx9Y+8AlzKmTHZ/dgBYosE2goOpT8rwbImZv03bv5YpFWg0D6tE/O7l4xv8KWwSDUA5/erBPRZ4M47F3PFwyvqcF",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# ---------- 替换后的 cookies（仅 SESSION） ----------
cookies = {
    "SESSION": "<YOUR_SESSION_HERE>",
}

# ---------- 替换后的 data（参数取自最新 curl 的 --data-raw） ----------
data = {
    "docId": "TEBb1cfvywxQ0h+BrotfiXks/Uyyj0lLBhyrr1bFbx9Y+8AlzKmTHZ/dgBYosE2goOpT8rwbImZv03bv5YpFWg0D6tE/O7l4xv8KWwSDUA5/erBPRZ4M47F3PFwyvqcF",
    "ciphertext": "110010+1001111+1110110+1001101+1000101+1010000+1000100+1101001+1000010+1111010+1101110+1100010+1010011+1101111+1110000+1101011+1110110+1001010+1101100+110011+1001110+110011+1111001+1000101+110010+110000+110010+110110+110000+110111+110000+111001+1101100+1010001+1000100+1101001+1110001+110010+1001101+1010110+1001011+1110101+101011+1010010+1000111+1100100+1011000+1001101+1010110+110000+1001001+1000001+1000101+1000001+111101+111101",
    "cfg": "com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@docInfoSearch",
    "__RequestVerificationToken": "i5ksVYGgZIMwLljzzGFgC14Y",
    "wh": "256",
    "ww": "1536",
    "cs": "0",
}

# ---------- 发送请求（其余逻辑不变） ----------
resp = requests.post(url, headers=headers, cookies=cookies, data=data, timeout=30, verify=False)
resp.raise_for_status()
resp_json = resp.json()
if resp_json.get('code') != 1:
    description = resp_json.get('description', '')
    if '登录' in description or '认证' in description or '失效' in description:
        raise Exception("COOKIE_EXPIRED")
    else:
        print(f"服务端错误: {description}")

secret_key = resp_json['secretKey']
result_enc = resp_json['result']
plaintext = decrypt_result(result_enc, secret_key)
data_json = json.loads(plaintext)
import json
import re
import csv
import os

def parse_detail(plaintext):
    """
    从裁判文书网详情页的 plaintext（解密后的 JSON 字符串）中提取 19 个字段。
    返回一个字典。
    """
    data = json.loads(plaintext)

    # 提取关键文本字段
    s26 = data.get('s26', '')      # 本院认为
    s27 = data.get('s27', '')      # 判决结果
    s25 = data.get('s25', '')      # 事实部分
    s22 = data.get('s22', '')      # 案号等
    combined = f"{s26} {s27} {s25} {s22}"

    # 辅助函数：根据关键词判断是否
    def bool_extract(text, pattern):
        return '是' if re.search(pattern, text, re.IGNORECASE) else '否'

    # 1. 盗窃金额（从事实或判决中找“价值X元”或“涉案X元”）
    amount = ''
    amount_patterns = [
        r'(?:价值|涉案|盗窃|金额|赃物)?\s*[（(]?人民币?[）)]?\s*([\d,]+\.?\d*)\s*元',
        r'(?:共计|合计)\s*([\d,]+\.?\d*)\s*元',
    ]
    for pat in amount_patterns:
        m = re.search(pat, s25) or re.search(pat, s26)
        if m:
            amount = m.group(1).replace(',', '')
            break

    # 2-6. 犯罪情节
    is_house = bool_extract(combined, r'入户|入室')
    is_pick = bool_extract(combined, r'扒窃')
    is_weapon = bool_extract(combined, r'携带凶器|凶器')
    is_multi = bool_extract(combined, r'多次盗窃|多次实施')
    is_attempt = bool_extract(combined, r'未遂')

    # 7. 累犯
    is_recidivist = bool_extract(combined, r'累犯')

    # 8. 非累犯前科（有前科且不是累犯）
    has_other_priors = '否'
    if re.search(r'前科|曾因|判处过|受过刑事处罚', combined):
        if is_recidivist == '否':
            has_other_priors = '是'

    # 9. 缓刑（判决结果中是否宣告缓刑）
    is_suspended1 = bool_extract(s27, r'缓刑')

    # 10. 坦白/如实供述
    is_confess = bool_extract(combined, r'坦白|如实供述|供认不讳')

    # 11. 认罪认罚
    is_plead = bool_extract(combined, r'认罪认罚')

    # 12. 退赃退赔
    is_restore = bool_extract(combined, r'退赃|退赔|赔偿损失')

    # 13. 谅解
    is_forgive = bool_extract(combined, r'谅解|取得谅解|达成和解')

    # 14. 数罪并罚
    is_multiple = bool_extract(combined, r'数罪并罚')

    # 15. 刑期月数
    prison_months = ''
    m = re.search(r'(?:判处)?\s*(拘役|有期徒刑)\s*([一二三四五六七八九十]+|[0-9]+)\s*(个?月?|年)', s27)
    if not m:
        m = re.search(r'(?:判处)?\s*(拘役|有期徒刑)\s*([一二三四五六七八九十]+|[0-9]+)\s*(个?月?|年)', s26)
    if m:
        unit = m.group(3)
        num_str = m.group(2)
        chinese_num = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
        if num_str in chinese_num:
            num = chinese_num[num_str]
        else:
            num = int(num_str)
        if '年' in unit:
            num = num * 12
        prison_months = str(num)

    # 16. 缓刑（第二个，内容与第一个相同，保留以符合字段要求）
    is_suspended2 = is_suspended1

    # 17. 免于刑事处罚
    is_exempt = bool_extract(combined, r'免于刑事处罚|免除处罚')

    # 18. 罚金金额
    fine_amount = ''
    m = re.search(r'罚金\s*人民币?\s*([\d,]+\.?\d*)\s*元', s27)
    if not m:
        m = re.search(r'罚金\s*人民币?\s*([\d,]+\.?\d*)\s*元', s26)
    if m:
        fine_amount = m.group(1).replace(',', '')

    # 19. 全文
    full_text = data.get('qwContent', '')

    # 组装结果
    result = {
        '盗窃金额': amount,
        '是否入户盗窃': is_house,
        '是否扒窃': is_pick,
        '是否携带凶器盗窃': is_weapon,
        '是否多次盗窃': is_multi,
        '是否未遂': is_attempt,
        '是否累犯': is_recidivist,
        '是否有非累犯前科': has_other_priors,
        '是否缓刑_判决': is_suspended1,
        '是否坦白/如实供述': is_confess,
        '是否认罪认罚': is_plead,
        '是否退赃退赔': is_restore,
        '是否谅解': is_forgive,
        '是否数罪并罚': is_multiple,
        '刑期月数': prison_months,
        '是否缓刑_适用': is_suspended2,   # 第二个缓刑字段
        '是否免于刑事处罚': is_exempt,
        '罚金金额': fine_amount,
        '全文': full_text
    }
    return result


def append_to_csv(parsed_list, filename='output.csv'):
    """
    将解析结果列表追加写入 CSV，自动添加表头。
    """
    if not parsed_list:
        return
    fieldnames = [
        '盗窃金额', '是否入户盗窃', '是否扒窃', '是否携带凶器盗窃',
        '是否多次盗窃', '是否未遂', '是否累犯',
        '是否有非累犯前科', '是否缓刑_判决', '是否坦白/如实供述',
        '是否认罪认罚', '是否退赃退赔', '是否谅解', '是否数罪并罚',
        '刑期月数', '是否缓刑_适用', '是否免于刑事处罚', '罚金金额', '全文'
    ]
    file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in parsed_list:
            writer.writerow(row)


# ==================== 使用示例 ====================
if __name__ == '__main__':
    # 假设 plaintext 是你解密后的 JSON 字符串
    plaintext = plaintext  # 替换为实际数据

    # 解析单条
    parsed = parse_detail(plaintext)
    print(parsed)

    # 如果需要写入 CSV，可以这样：
    append_to_csv([parsed])