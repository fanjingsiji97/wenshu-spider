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
    "Referer": "https://wenshu.court.gov.cn/website/wenshu/181217BMTKHNT2W0/index.html?s8=03",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# ---------- 替换后的 cookies（包含 SESSION 和 wzws_reurl） ----------
cookies = {
    "SESSION": "<YOUR_SESSION_HERE>",
    "wzws_reurl": "L3dlYnNpdGUvd2Vuc2h1L2ltYWdlcy9iZWlqaW5nLnBuZw==",
}

# ---------- 替换后的 data（参数取自最新 curl 的 --data-raw） ----------
data = {
    "s8": "03",
    "sortFields": "s50:desc",
    "ciphertext": "1010110+1001001+1110110+1110111+1001101+111001+1100110+1101000+1010101+1010001+1101010+110000+1111010+1010101+1000011+1001111+1001011+1000111+1001010+1001000+1010111+1001011+1100010+1110101+110010+110000+110010+110110+110000+110111+110000+111001+1110101+1100011+1111000+1010011+1110110+1001110+1100111+111001+1101001+1101001+1010011+1101010+1111010+110100+1111001+1001101+1010010+111001+110100+1000110+1100110+1110111+111101+111101",
    "pageNum": "2",
    "pageSize": "5",
    "queryCondition": '[{"key":"s8","value":"03"}]',
    "cfg": "com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@queryDoc",
    "__RequestVerificationToken": "T39hV14cdHDaDXTmoARnrW3R",
    "wh": "828",
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
print(plaintext)