import json
import re
import csv
import os
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from urllib.parse import urlencode
from datetime import datetime
import requests
import base64
import string
from Crypto.Cipher import DES3
from Crypto.Util.Padding import unpad, pad
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置区 ====================
S45_KEYWORDS = [
    "非法占有", "故意犯", "自首", "罚金", "违法所得", "拘役",
    "减轻处罚", "共同犯罪", "管制", "扣押", "犯罪未遂", "没收",
    "从犯", "财产权", "返还", "行政拘留", "传唤", "羁押",
    "合法财产", "所有权", "偶犯", "没收财产", "着手", "鉴定",
    "保证金", "未成年人", "立功", "违法行为", "共同故意",
    "刑事责任能力", "赔偿损失", "公正审判", "取保候审", "财产刑", "变卖"
]

PROVINCE_LIST = [
    "北京市", "天津市", "河北省", "山西省", "内蒙古自治区",
    "辽宁省", "吉林省", "黑龙江省", "上海市", "江苏省",
    "浙江省", "安徽省",
    "福建省", "江西省", "山东省", "河南省", "湖北省",
    "湖南省", "广东省", "广西壮族自治区", "海南省", "重庆市",
    "四川省", "贵州省",
    "云南省", "西藏自治区", "陕西省", "甘肃省", "青海省",
    "宁夏回族自治区", "新疆维吾尔自治区",
    "新疆维吾尔自治区高级人民法院生产建设兵团分院"
]

COOKIES = {
    "wzws_reurl": "L3dlYnNpdGUvd2Vuc2h1L2ltYWdlcy9mYXZpY29uLmljbw==",
    "SESSION": ""  # 由用户在GUI中设置
}

# 固定 UA（与 ciphertext 绑定，不能随意更换）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://wenshu.court.gov.cn",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# ==================== 动态参数生成器 ====================
def random_salt(length: int = 24) -> str:
    """生成 24 位随机字符串（用于 salt 和 Token）"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def str_to_binary(s: str) -> str:
    """字符串每个字符转二进制，空格分隔（与 JS 完全一致）"""
    result = []
    for i, ch in enumerate(s):
        if i != 0:
            result.append(" ")
        result.append(bin(ord(ch))[2:])
    return "".join(result)


def generate_ciphertext(salt: str = None, timestamp: str = None) -> tuple:
    """
    生成与 JS cipher() 完全一致的 ciphertext
    返回 (ciphertext, salt, timestamp)
    """
    if timestamp is None:
        timestamp = str(int(time.time() * 1000))
    if salt is None:
        salt = random_salt(24)

    iv_str = datetime.now().strftime('%Y%m%d')
    key = salt.encode('utf-8')
    if len(key) != 24:
        raise ValueError(f"salt 长度必须是 24，当前 {len(key)}")
    iv = iv_str.encode('utf-8')
    if len(iv) != 8:
        raise ValueError(f"iv 长度必须是 8，当前 {len(iv)}")

    plaintext = timestamp.encode('utf-8')
    cipher = DES3.new(key, DES3.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(plaintext, DES3.block_size))
    enc = base64.b64encode(encrypted).decode('utf-8')
    combined = salt + iv_str + enc
    ciphertext = str_to_binary(combined)
    return ciphertext, salt, timestamp


def generate_token() -> str:
    """生成 __RequestVerificationToken（24位随机）"""
    return random_salt(24)


# ==================== 中文数字转阿拉伯数字 ====================
def chinese_to_arabic(ch):
    if not ch:
        return ''
    if ch.isdigit():
        return ch
    if '万' in ch:
        parts = ch.split('万')
        left = chinese_to_arabic(parts[0]) if parts[0] else '1'
        right = chinese_to_arabic(parts[1]) if len(parts) > 1 and parts[1] else '0'
        return str(int(left) * 10000 + int(right))
    if '千' in ch:
        parts = ch.split('千')
        left = chinese_to_arabic(parts[0]) if parts[0] else '1'
        right = chinese_to_arabic(parts[1]) if len(parts) > 1 and parts[1] else '0'
        return str(int(left) * 1000 + int(right))
    if '百' in ch:
        parts = ch.split('百')
        left = chinese_to_arabic(parts[0]) if parts[0] else '1'
        right = chinese_to_arabic(parts[1]) if len(parts) > 1 and parts[1] else '0'
        return str(int(left) * 100 + int(right))
    if '十' in ch:
        parts = ch.split('十')
        left = chinese_to_arabic(parts[0]) if parts[0] else '1'
        right = chinese_to_arabic(parts[1]) if len(parts) > 1 and parts[1] else '0'
        return str(int(left) * 10 + int(right))
    single = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
    return single.get(ch, '')


# ==================== 解密 ====================
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


# ==================== 数据解析 ====================
def parse_detail(data):
    s1 = data.get('s1', '')
    s2 = data.get('s2', '')
    s7 = data.get('s7', '')
    s9 = data.get('s9', '')
    s6 = data.get('s6', '')
    s31 = data.get('s31', '')
    s25 = data.get('s25', '')
    s26 = data.get('s26', '')
    s27 = data.get('s27', '')
    qwContent = data.get('qwContent', '')
    combined = f"{s25} {s26} {s27} {qwContent}"

    def bool_extract(text, pattern):
        return '是' if re.search(pattern, text, re.IGNORECASE) else '否'

    year = s31[:4] if s31 else ''
    province = ''
    patterns = [
        r'(北京市|天津市|上海市|重庆市)',
        r'(内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区)',
        r'([^省]+省)',
        r'([^市]+市)'
    ]
    for pat in patterns:
        m = re.search(pat, s2)
        if m:
            prov = m.group(1)
            if '区' not in prov or len(prov) > 4:
                province = prov
                break

    gender = ''
    m_gender = re.search(r'[男女]', qwContent) or re.search(r'[男女]', combined)
    if m_gender:
        gender = m_gender.group(0)

    birth_year = ''
    all_years = re.findall(r'\b(\d{4})\b', combined)
    valid_years = [y for y in all_years if 1900 <= int(y) <= 2004]
    if valid_years:
        birth_year = valid_years[0]

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

    is_house = bool_extract(combined, r'入户|入室')
    is_pick = bool_extract(combined, r'扒窃')
    is_weapon = bool_extract(combined, r'携带凶器|凶器')
    is_multi = bool_extract(combined, r'多次盗窃|多次实施')
    is_attempt = bool_extract(combined, r'未遂')
    is_recidivist = bool_extract(combined, r'累犯')

    has_other_priors = '否'
    if re.search(r'前科|曾因|判处过|受过刑事处罚', combined):
        if is_recidivist == '否':
            has_other_priors = '是'

    is_suspended1 = bool_extract(s27, r'缓刑')
    is_suspended2 = is_suspended1
    is_confess = bool_extract(combined, r'坦白|如实供述|供认不讳')
    is_plead = bool_extract(combined, r'认罪认罚')
    is_restore = bool_extract(combined, r'退赃|退赔|赔偿损失')
    is_forgive = bool_extract(combined, r'谅解|取得谅解|达成和解')
    is_multiple = bool_extract(combined, r'数罪并罚')

    prison_months = ''
    m = re.search(r'(?:判处)?\s*(拘役|有期徒刑)\s*([一二三四五六七八九十百千万]+|[0-9]+)\s*(个?月?|年)', s27)
    if not m:
        m = re.search(r'(?:判处)?\s*(拘役|有期徒刑)\s*([一二三四五六七八九十百千万]+|[0-9]+)\s*(个?月?|年)', s26)
    if m:
        unit = m.group(3)
        num_str = m.group(2)
        num_arabic = chinese_to_arabic(num_str)
        if num_arabic and num_arabic.isdigit():
            num = int(num_arabic)
            if '年' in unit:
                num *= 12
            prison_months = str(num)

    is_exempt = bool_extract(combined, r'免于刑事处罚|免除处罚')

    fine_amount = ''
    fine_text = ''
    if re.search(r'罚金', s27):
        fine_text = s27
    elif re.search(r'罚金', s26):
        fine_text = s26
    elif re.search(r'罚金', qwContent):
        fine_text = qwContent
    if fine_text:
        m = re.search(r'罚金\s*人民币?\s*([\d,]+\.?\d*)\s*元', fine_text)
        if m:
            fine_amount = m.group(1).replace(',', '')
        else:
            m = re.search(r'罚金\s*人民币?\s*([一二三四五六七八九十百千万]+)\s*元', fine_text)
            if m:
                fine_amount = chinese_to_arabic(m.group(1))

    full_text = qwContent
    return {
        '年份': year, '省份': province, '标题': s1, '案号': s7,
        '裁判法院': s2, '裁判日期': s31,
        '案由/罪名（盗窃罪）': '盗窃罪',
        '案件类型（一审）': s9,
        '文书类型（判决书）': '判决书' if s6 == '01' else s6,
        '被告人性别': gender, '被告人出生年份': birth_year,
        '盗窃金额': amount,
        '是否入户盗窃': is_house, '是否扒窃': is_pick,
        '是否携带凶器盗窃': is_weapon, '是否多次盗窃': is_multi,
        '是否未遂': is_attempt, '是否累犯': is_recidivist,
        '是否有非累犯前科（前罪缓刑、前罪发生在五年以前）': has_other_priors,
        '是否缓刑': is_suspended1,
        '是否坦白/如实供述': is_confess, '是否认罪认罚': is_plead,
        '是否退赃退赔': is_restore, '是否谅解': is_forgive,
        '是否数罪并罚': is_multiple, '刑期月数': prison_months,
        '是否缓刑（重复）': is_suspended2,
        '是否免于刑事处罚': is_exempt, '罚金金额': fine_amount,
        '全文': full_text
    }


def append_to_csv(parsed_list, filename='WENSHU.csv'):
    if not parsed_list:
        return
    fieldnames = [
        '序号', '年份', '省份', '标题', '案号', '裁判法院', '裁判日期',
        '案由/罪名（盗窃罪）', '案件类型（一审）', '文书类型（判决书）',
        '被告人性别', '被告人出生年份', '盗窃金额',
        '是否入户盗窃', '是否扒窃', '是否携带凶器盗窃', '是否多次盗窃',
        '是否未遂', '是否累犯',
        '是否有非累犯前科（前罪缓刑、前罪发生在五年以前）',
        '是否缓刑', '是否坦白/如实供述', '是否认罪认罚', '是否退赃退赔',
        '是否谅解', '是否数罪并罚', '刑期月数', '是否缓刑（重复）',
        '是否免于刑事处罚', '罚金金额', '全文'
    ]
    file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in parsed_list:
            writer.writerow(row)


# ==================== 进度管理 ====================
PROGRESS_FILE = "Deduckation.json"


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def get_page(key):
    data = load_progress()
    return data.get('pages', {}).get(key, 1)


def set_page(key, page):
    data = load_progress()
    if 'pages' not in data:
        data['pages'] = {}
    data['pages'][key] = page
    save_progress(data)


def load_crawled():
    data = load_progress()
    return set(data.get('crawled', []))


def save_crawled(crawled_set):
    data = load_progress()
    data['crawled'] = list(crawled_set)
    save_progress(data)


def is_crawled(doc_id):
    return doc_id in load_crawled()


# ==================== 网络请求（动态 ciphertext + Token） ====================
def search_docs(page, province, s45):
    url = "https://wenshu.court.gov.cn/website/parse/rest.q4w"
    headers = HEADERS.copy()
    conditions = [
        {"key": "s13", "value": "201"},
        {"key": "s9", "value": "0201"},
        {"key": "s6", "value": "01"},
        {"key": "s42", "value": "2026"},
    ]
    if s45:
        conditions.append({"key": "s45", "value": s45})
    if province:
        conditions.append({"key": "s33", "value": province})
    query_condition_str = json.dumps(conditions, ensure_ascii=False)

    # 动态生成 ciphertext 和 Token
    ciphertext, salt, timestamp = generate_ciphertext()
    token = generate_token()

    data = {
        "pageId": "55f13cfaa941bbdc9dc692ec7243e24a",
        "s16": "盗窃罪",
        "s13": "201",
        "s8": "02",
        "s9": "0201",
        "s6": "01",
        "sortFields": "s50:desc",
        "ciphertext": ciphertext,
        "pageNum": str(page),
        "pageSize": "15",
        "queryCondition": query_condition_str,
        "cfg": "com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@queryDoc",
        "__RequestVerificationToken": token,
        "wh": "828",
        "ww": "1536",
        "cs": "0",
    }
    payload = urlencode(data, encoding='utf-8')
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=payload, timeout=30, verify=False)
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json.get('code') != 1:
            desc = resp_json.get('description', '')
            if '登录' in desc or '认证' in desc or '失效' in desc or '没有权限' in desc:
                raise Exception("COOKIE_EXPIRED")
            print(f"搜索页错误: {desc}")
            return []
        secret_key = resp_json['secretKey']
        result_enc = resp_json['result']
        plaintext = decrypt_result(result_enc, secret_key)
        data_json = json.loads(plaintext)
        rel = data_json.get('relWenshu', {})
        doc_ids = list(rel.keys())
        return doc_ids
    except Exception as e:
        print(f"请求失败，完整响应: {resp.text}")
        if str(e) == "COOKIE_EXPIRED":
            raise
        print(f"搜索请求失败: {e}")
        return []


def fetch_detail(doc_id):
    url = "https://wenshu.court.gov.cn/website/parse/rest.q4w"
    headers = HEADERS.copy()
    headers["Referer"] = f"https://wenshu.court.gov.cn/website/wenshu/181107ANFZ0BXSK4/index.html?docId={doc_id}"

    ciphertext, salt, timestamp = generate_ciphertext()
    token = generate_token()

    data = {
        "docId": doc_id,
        "ciphertext": ciphertext,
        "cfg": "com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@docInfoSearch",
        "__RequestVerificationToken": token,
        "wh": "256",
        "ww": "1536",
        "cs": "0",
    }
    payload = urlencode(data, encoding='utf-8')
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=payload, timeout=30, verify=False)
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json.get('code') != 1:
            desc = resp_json.get('description', '')
            if '登录' in desc or '认证' in desc or '失效' in desc or '没有权限' in desc:
                raise Exception("COOKIE_EXPIRED")
            print(f"详情页错误: {desc}")
            return None
        secret_key = resp_json['secretKey']
        result_enc = resp_json['result']
        plaintext = decrypt_result(result_enc, secret_key)
        data_json = json.loads(plaintext)
        return data_json
    except Exception as e:
        if str(e) == "COOKIE_EXPIRED":
            raise
        print(f"详情请求失败: {e}")
        return None


# ==================== 模拟人类行为 ====================
class HumanSimulator:
    def __init__(self, status_callback=None):
        self.req_count = 0
        self.total = 0
        self.status_callback = status_callback
        self.work_start_hour = 6
        self.work_end_hour = 23

    def _is_active_hours(self):
        now = datetime.now().hour
        return self.work_start_hour <= now < self.work_end_hour

    def _exponential_delay(self, mean=2.0):
        delay = random.expovariate(1.0 / mean)
        return min(max(delay, 0.3), 10.0)

    def wait(self):
        base_mean = 1.5 + (self.req_count % 15) * 0.08
        delay = self._exponential_delay(base_mean)
        if random.random() < 0.15:
            delay += random.uniform(3.0, 12.0)
        if random.random() < 0.03:
            delay += random.uniform(10.0, 30.0)
        if not self._is_active_hours():
            delay *= 2.5
        time.sleep(delay)
        self.total += 1
        self.req_count += 1
        if self.req_count >= 30:
            rest = random.uniform(60, 300)
            self.req_count = 0
            if not self._is_active_hours():
                rest *= 1.8
            if self.status_callback:
                self.status_callback(f"💤 长休 {int(rest)} 秒")
            time.sleep(rest)
            if self.status_callback:
                self.status_callback("🔄 继续工作")
        else:
            if self.req_count % 10 == 0 and self.req_count > 0:
                short_rest = random.uniform(5, 20)
                if self.status_callback:
                    self.status_callback(f"💧 短休 {int(short_rest)} 秒")
                time.sleep(short_rest)
                if self.status_callback:
                    self.status_callback("🔄 继续工作")
            else:
                if self.status_callback:
                    self.status_callback(f"🔄 工作中 (已请求 {self.total} 次)")


# ==================== 主爬虫逻辑 ====================
def main_crawl(search_log_cb, detail_log_cb, status_cb, total_cb, task_cb):
    global COOKIES
    progress_data = load_progress()
    total_count = progress_data.get('total_count', 0)
    crawled_set = set(progress_data.get('crawled', []))
    human = HumanSimulator(status_cb)

    for s45 in S45_KEYWORDS:
        for province in PROVINCE_LIST:
            key = f"{s45}_{province}"
            page = get_page(key)
            search_log_cb(f"📂 组合: {s45} | {province} (从第{page}页)")
            task_cb(f"关键词: {s45} | 省份: {province} | 页码: {page}")

            while True:
                try:
                    doc_ids = search_docs(page, province, s45)
                    human.wait()
                except Exception as e:
                    if str(e) == "COOKIE_EXPIRED":
                        search_log_cb("⚠️ Cookie 失效，请在终端输入新 SESSION")
                        status_cb("⛔ Cookie 失效")
                        new_session = input("\n请输入新的 SESSION 值: ").strip()
                        if new_session:
                            COOKIES["SESSION"] = new_session
                            search_log_cb("✅ Cookie 已更新，继续...")
                            status_cb("🔄 继续")
                            continue
                        else:
                            search_log_cb("❌ 未输入，退出。")
                            return
                    else:
                        search_log_cb(f"❌ 搜索异常: {e}")
                        time.sleep(5)
                        continue

                if not doc_ids:
                    search_log_cb(f"  第{page}页无数据，组合结束")
                    break

                search_log_cb(f"  第{page}页获取 {len(doc_ids)} 个docid")

                for doc_id in doc_ids:
                    if doc_id in crawled_set:
                        continue
                    detail_data = fetch_detail(doc_id)
                    human.wait()
                    if detail_data is None:
                        detail_log_cb(f"  ⚠️ docid {doc_id[:20]}... 失败")
                        continue
                    parsed = parse_detail(detail_data)
                    total_count += 1
                    parsed['序号'] = total_count
                    append_to_csv([parsed])
                    crawled_set.add(doc_id)

                    progress_data = load_progress()
                    progress_data['crawled'] = list(crawled_set)
                    progress_data['total_count'] = total_count
                    save_progress(progress_data)

                    total_cb(str(total_count))
                    detail_log_cb(f"  ✅ 第{total_count}条: {parsed.get('标题', '')[:20]}...")
                    task_cb(f"📄 {parsed.get('标题', '')[:30]}...")
                    time.sleep(random.uniform(2, 5))

                set_page(key, page + 1)

                if len(doc_ids) < 15:
                    search_log_cb(f"  第{page}页为最后一页（少于15条）")
                    break

                page += 1
                task_cb(f"关键词: {s45} | 省份: {province} | 页码: {page}")
                time.sleep(random.uniform(1, 3))

            search_log_cb(f"✅ 组合 '{s45}_{province}' 完成，休息5秒...")
            status_cb("💤 组合间休息")
            time.sleep(5)

    search_log_cb("🏁 全部爬取完成！")
    status_cb("🎉 完成！")


# ==================== GUI ====================
def create_gui():
    root = tk.Tk()
    root.title("裁判文书网爬虫监控")
    root.geometry("850x720")
    root.resizable(False, False)

    tk.Label(root, text="📊 爬虫实时状态", font=("微软雅黑", 18, "bold")).pack(pady=5)

    cf = tk.Frame(root)
    cf.pack(pady=5, fill=tk.X, padx=10)
    tk.Label(cf, text="SESSION:", font=("微软雅黑", 10)).pack(side=tk.LEFT)
    session_entry = tk.Entry(cf, width=40)
    session_entry.pack(side=tk.LEFT, padx=5)
    session_entry.insert(0, COOKIES.get("SESSION", ""))

    def set_cookie():
        global COOKIES
        ns = session_entry.get().strip()
        if ns:
            COOKIES["SESSION"] = ns
            messagebox.showinfo("提示", "Cookie 设置成功！")
        else:
            messagebox.showwarning("警告", "请输入 SESSION 值")

    tk.Button(cf, text="设置 Cookie", command=set_cookie, font=("微软雅黑", 10), bg="lightyellow").pack(side=tk.LEFT, padx=5)

    status_var = tk.StringVar(value="等待设置 Cookie")
    total_var = tk.StringVar(value="0")
    task_var = tk.StringVar(value="等待启动...")

    f1 = tk.Frame(root); f1.pack(pady=5)
    tk.Label(f1, text="已爬取条数:", font=("微软雅黑", 12)).pack(side=tk.LEFT, padx=5)
    tk.Label(f1, textvariable=total_var, font=("微软雅黑", 14, "bold"), fg="blue").pack(side=tk.LEFT)

    f2 = tk.Frame(root); f2.pack(pady=5)
    tk.Label(f2, text="当前状态:", font=("微软雅黑", 12)).pack(side=tk.LEFT, padx=5)
    tk.Label(f2, textvariable=status_var, font=("微软雅黑", 12), fg="green").pack(side=tk.LEFT)

    f3 = tk.Frame(root); f3.pack(pady=5)
    tk.Label(f3, text="当前任务:", font=("微软雅黑", 12)).pack(side=tk.LEFT, padx=5)
    tk.Label(f3, textvariable=task_var, font=("微软雅黑", 11), wraplength=600, justify="left").pack(side=tk.LEFT)

    lf = tk.Frame(root); lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    sf = tk.LabelFrame(lf, text="📡 搜索日志", font=("微软雅黑", 10))
    sf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    s_text = scrolledtext.ScrolledText(sf, height=14, font=("宋体", 9), bg="#f0f8ff")
    s_text.pack(fill=tk.BOTH, expand=True)

    df = tk.LabelFrame(lf, text="📄 详情日志", font=("微软雅黑", 10))
    df.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
    d_text = scrolledtext.ScrolledText(df, height=14, font=("宋体", 9), bg="#f0fff0")
    d_text.pack(fill=tk.BOTH, expand=True)

    def s_log(msg):
        s_text.insert(tk.END, msg + "\n"); s_text.see(tk.END)

    def d_log(msg):
        d_text.insert(tk.END, msg + "\n"); d_text.see(tk.END)

    def status_update(msg):
        status_var.set(msg)

    def total_update(v):
        total_var.set(v)

    def task_update(msg):
        task_var.set(msg)

    pb = ttk.Progressbar(root, length=810, mode='indeterminate')
    pb.pack(pady=5)
    pb.start(10)

    bf = tk.Frame(root); bf.pack(pady=10)

    def start_crawl():
        if not COOKIES.get("SESSION"):
            messagebox.showwarning("提示", "请先设置 SESSION Cookie")
            return
        threading.Thread(target=lambda: main_crawl(s_log, d_log, status_update, total_update, task_update),
                         daemon=True).start()

    tk.Button(bf, text="🚀 启动爬虫", command=start_crawl, font=("微软雅黑", 12), bg="lightblue").pack(side=tk.LEFT, padx=20)
    tk.Button(bf, text="⏹ 停止", command=root.quit, font=("微软雅黑", 12), bg="lightcoral").pack(side=tk.LEFT, padx=20)

    root.mainloop()


if __name__ == "__main__":
    create_gui()