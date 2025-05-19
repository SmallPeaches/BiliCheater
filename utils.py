from functools import reduce
from hashlib import md5
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import time
import httpx
import requests
import asyncio, aiohttp

HEADERS = {
    'referer': 'https://live.bilibili.com',
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54',
}

def getWebid(uid):
    dynamic_url = f"https://space.bilibili.com/{uid}/dynamic"
    text = httpx.get(dynamic_url, headers=HEADERS).text
    __RENDER_DATA__ = re.search(
        r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
        text,
        re.S,
    ).group(1)
    access_id = json.loads(urllib.parse.unquote(__RENDER_DATA__))["access_id"]
    return access_id

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys() -> tuple[str, str]:
    '获取最新的 img_key 和 sub_key'
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
            'Referer': 'https://www.bilibili.com/',
        })
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key


XOR_CODE = 23442827791579
MASK_CODE = 2251799813685247
MAX_AID = 1 << 51
ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6
DECODE_MAP = tuple(reversed(ENCODE_MAP))

BASE = len(ALPHABET)
PREFIX = "BV1"
PREFIX_LEN = len(PREFIX)
CODE_LEN = len(ENCODE_MAP)

def AVID2BVID(aid: int) -> str:
    bvid = [""] * 9
    tmp = (MAX_AID | aid) ^ XOR_CODE
    for i in range(CODE_LEN):
        bvid[ENCODE_MAP[i]] = ALPHABET[tmp % BASE]
        tmp //= BASE
    return PREFIX + "".join(bvid)

def BVID2AVID(bvid: str) -> int:
    assert bvid[:3] == PREFIX

    bvid = bvid[3:]
    tmp = 0
    for i in range(CODE_LEN):
        idx = ALPHABET.index(bvid[DECODE_MAP[i]])
        tmp = tmp * BASE + idx
    return (tmp & MASK_CODE) ^ XOR_CODE

import json
import re
import time
from typing import List, Union
import requests
import http.cookiejar as cookielib

class BaseAPI:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.30",
    }
    def __init__(self,timeout=(3.05,5)):
        self.timeout=timeout
        
    
    def set_default_timeout(self,timeout=(3.05,5)):
        self.timeout=timeout

class BiliLiveAPI(BaseAPI):
    def __init__(self,cookies:Union[List[str],str,dict],timeout=(3.05,5)):
        """B站直播相关API"""
        super().__init__(timeout)
        self.headers = dict(self.headers,
            Origin="https://live.bilibili.com",
            Referer="https://live.bilibili.com/")
        self.sessions = []
        self.csrfs = []
        self.rnd=int(time.time())
        if isinstance(cookies,str):    cookies=[cookies]
        if isinstance(cookies,list):
            for i in range(len(cookies)):
                self.sessions.append(requests.session())
                self.csrfs.append("")
                self.update_cookie(cookies[i],i)
        if isinstance(cookies,dict):
            self.sessions.append(requests.session())
            self.csrfs.append(cookies.get('bili_jct'))
            requests.utils.add_dict_to_cookiejar(self.sessions[0].cookies,cookies)
    
    def get_room_info(self,roomid,timeout=None) -> dict:
        """获取直播间标题、简介等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)

    def get_danmu_config(self,roomid,number=0,timeout=None) -> dict:
        """获取用户在直播间内的可用弹幕颜色、弹幕位置等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/dM/GetDMConfigByGroup"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_user_info(self,roomid,number=0,timeout=None) -> dict:
        """获取用户在直播间内的当前弹幕颜色、弹幕位置、发言字数限制等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByUser"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def set_danmu_config(self,roomid,color=None,mode=None,number=0,timeout=None) -> dict:
        """设置用户在直播间内的弹幕颜色或弹幕位置
        :（颜色参数为十六进制字符串，颜色和位置不能同时设置）"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/dM/AjaxSetConfig"
        data={
            "room_id": roomid,
            "color": color,
            "mode": mode,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def send_danmu(self,roomid,msg,mode=1,number=0,timeout=None,emoticon=0) -> dict:
        """向直播间发送弹幕"""
        url="https://api.live.bilibili.com/msg/send"
        data={
            "color": 16777215,
            "fontsize": 25,
            "mode": mode,
            "bubble": 0,
            "dm_type": emoticon,
            "msg": msg,
            "roomid": roomid,
            "rnd": self.rnd,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def get_slient_user_list(self,roomid,number=0,timeout=None):
        """获取房间被禁言用户列表"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/GetSilentUserList"
        params={
            "room_id": roomid,
            "ps": 1,
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def add_slient_user(self,roomid,uid,number=0,timeout=None):
        """禁言用户"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/AddSilentUser"
        data={
            "room_id": roomid,
            "tuid": uid,
            "mobile_app": "web",
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)

    def del_slient_user(self,roomid,silent_id,number=0,timeout=None):
        """解除用户禁言"""
        url="https://api.live.bilibili.com/banned_service/v1/Silent/del_room_block_user"
        data={
            "roomid": roomid,
            "id": silent_id,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def get_shield_keyword_list(self,roomid,number=0,timeout=None):
        """获取房间屏蔽词列表"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/GetShieldKeywordList"
        params={
            "room_id": roomid,
            "ps": 2,
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)

    def add_shield_keyword(self,roomid,keyword,number=0,timeout=None):
        """添加房间屏蔽词"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/AddShieldKeyword"
        data={
            "room_id": roomid,
            "keyword": keyword,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def del_shield_keyword(self,roomid,keyword,number=0,timeout=None):
        """删除房间屏蔽词"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/DelShieldKeyword"
        data={
            "room_id": roomid,
            "keyword": keyword,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def search_live_users(self,keyword,page_size=10,timeout=None) -> dict:
        """根据关键字搜索直播用户"""
        url="https://api.bilibili.com/x/web-interface/search/type"
        params={
            "keyword": keyword,
            "search_type": "live_user",
            "page_size": page_size,
        }
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_login_url(self,timeout=None):
        """获取登录链接"""
        url="https://passport.bilibili.com/qrcode/getLoginUrl"
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,timeout=timeout)
        return json.loads(res.text)
    
    def get_login_info(self,oauthKey,timeout=None):
        """检查登录链接状态，获取登录信息"""
        url="https://passport.bilibili.com/qrcode/getLoginInfo"
        data={
            "oauthKey": oauthKey,
        }
        if timeout is None: timeout=self.timeout
        res=requests.post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def update_cookie(self,cookie:str,number=0) -> str:
        """更新账号Cookie信息
        :返回cookie中buvid3,SESSDATA,bili_jct三项的合并内容"""
        cookie = re.sub(r"\s+", "", cookie)
        mo1 = re.search(r"buvid3=([^;]+)", cookie)
        mo2 = re.search(r"SESSDATA=([^;]+)", cookie)
        mo3 = re.search(r"bili_jct=([^;]+)", cookie)
        buvid3,sessdata,bili_jct=mo1.group(1) if mo1 else "",mo2.group(1) if mo2 else "",mo3.group(1) if mo3 else ""
        cookie="buvid3=%s;SESSDATA=%s;bili_jct=%s"%(buvid3,sessdata,bili_jct)
        requests.utils.add_dict_to_cookiejar(self.sessions[number].cookies,{"Cookie": cookie})
        self.csrfs[number]=bili_jct
        return cookie
    
    def onAir(self, rid):
        r_url = 'https://api.live.bilibili.com/room/v1/Room/room_init?id={}'.format(rid)
        res = requests.get(r_url,timeout=5,headers=HEADERS).json()
        code = res['code']
        if code == 0:
            live_status = res['data']['live_status']
            if live_status == 1:
                return True
        return False

    async def asyncOnAir(self, rid):
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f'https://api.live.bilibili.com/room/v1/Room/room_init?id={rid}',timeout=5,headers=HEADERS) as resp:
                res = await resp.json()
                code = res['code']
                if code == 0:
                    live_status = res['data']['live_status']
                    if live_status == 1:
                        return True
                    return False
                return None


