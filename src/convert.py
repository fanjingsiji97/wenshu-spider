import requests

url = "https://wenshu.court.gov.cn/website/parse/rest.q4w"

headers = {
    "Host": "wenshu.court.gov.cn",
    "Connection": "keep-alive",
    "sec-ch-ua-platform": '"Windows"',
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua-mobile": "?0",
    "Origin": "https://wenshu.court.gov.cn",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://wenshu.court.gov.cn/website/wenshu/181217BMTKHNT2W0/index.html?s8=02&pageId=0.6754662636100317",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

cookies = {
    "SESSION": "<YOUR_SESSION_HERE>",
    "wzws_cid": "c3b60862d419d4acff901a8a076e415d91e7933e22ad1499d899ee98afcafa5d4d5869424bd20aaa00e20277103104253ea743d57df7c6b0006075a08f6ac49964ee44375595bc11e58393d545f4882de6027e74bde85a2e76cd657ffce04c41",
    "wzws_reurl": "L2FwaS9mcC9haGltZz9yYW5kb209T09VOVNKNU54YUpvaE9zYk1OZTNsQjhWRFNzWDExWFMra1FRdVZvZWszQT0mZGF0ZT0xNzgzNTEwMjY1MzE1",
}

data = {
    "s8": "02",
    "pageId": "0.6754662636100317",
    "sortFields": "s50:desc",
    "ciphertext": "1010000+1001100+110001+110011+1000111+110001+1101111+1110100+1000110+1110101+1110011+1001000+1110000+110100+1110110+1000110+1101111+1110100+110010+110100+110100+1010111+1010000+1010011+110010+110000+110010+110110+110000+110111+110000+111000+1011000+1001111+111000+1001011+1000011+1100100+1000010+1100010+1010001+1011000+1010011+1000101+110100+1001101+1101001+1110000+1100111+110100+1100001+1111010+111000+1000001+111101+111101",
    "pageNum": "3",
    "pageSize": "15",
    "queryCondition": '[{"key":"s8","value":"02"},{"key":"s13","value":"201"},{"key":"s9","value":"0201"},{"key":"s6","value":"01"},{"key":"cprq","value":"2026-01-01+TO+2026-07-09"}]',
    "cfg": "com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@queryDoc",
    "__RequestVerificationToken": "GZKhsDLiQaBMcfxodUfQl15h",
    "wh": "825",
    "ww": "1536",
    "cs": "0",
}

response = requests.post(url, headers=headers, cookies=cookies, data=data)

print(response.text)
print(response.status_code)