import asyncio, aiohttp
from functools import wraps
import uuid
import random
import base64
import json
import requests
import logging, logging.handlers
import sys, os

import asyncio
from hashlib import md5
import hashlib
import random
import time
import json
from typing import Union
from urllib.parse import urlencode
from datetime import datetime
from utils import *

class Crypto:
    APPKEY = '4409e2ce8ffd12b8'
    APPSECRET = '59b43e04ad6965f34319062b478f83dd'

    @staticmethod
    def md5(data: Union[str, bytes]) -> str:
        '''generates md5 hex dump of `str` or `bytes`'''
        if type(data) == str:
            return md5(data.encode()).hexdigest()
        return md5(data).hexdigest()

    @staticmethod
    def sign(data: Union[str, dict]) -> str:
        '''salted sign funtion for `dict`(converts to qs then parse) & `str`'''
        if isinstance(data, dict):
            _str = urlencode(data)
        elif type(data) != str:
            raise TypeError
        return Crypto.md5(_str + Crypto.APPSECRET)

class SingableDict(dict):
    @property
    def sorted(self):
        '''returns a alphabetically sorted version of `self`'''
        return dict(sorted(self.items()))

    @property
    def signed(self):
        '''returns our sorted self with calculated `sign` as a new key-value pair at the end'''
        _sorted = self.sorted
        return {**_sorted, 'sign': Crypto.sign(_sorted)}

def client_sign(data: dict):
    _str = json.dumps(data, separators=(',', ':'))
    for n in ["sha512", "sha3_512", "sha384", "sha3_384", "blake2b"]:
        _str = hashlib.new(n, _str.encode('utf-8')).hexdigest()
    return _str

class BiliApiError(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __str__(self):
        return self.msg

def randomString(length: int = 16) -> str:
    return ''.join(random.sample('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', length))

class BaseCheat():
    headers_pc = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.30",
        'Referer': "https://live.bilibili.com/",
    }
    headers_mobile = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36 Edg/109.0.1518.61",
    }

    def __init__(self, cookies=None, access_key=None) -> None:
        self.stoped = True
        self.cookies = cookies 
        self.uid = self.cookies.get('DedeUserID',0)
        self.access_key = access_key
        self.biliapi = BiliLiveAPI(cookies=self.cookies)

        if not self.cookies.get('buvid3'):
            resp = requests.get('https://data.bilibili.com/v/')
            self.cookies.update(resp.cookies) 
        if not self.cookies.get('LIVE_BUVID'):
            resp = requests.get('https://api.live.bilibili.com/activity/v1/Common/webBanner?platform=web')
            self.cookies.update(resp.cookies) 

    def _check_response(self, resp: dict) -> dict:
        if resp['code'] != 0 or ('mode_info' in resp['data'] and resp['message'] != ''):
            raise BiliApiError(resp['code'], resp['message'])
        return resp['data']

    async def _get(self, *args, **kwargs):
        async with self.sess.get(*args, **kwargs) as resp:
            return self._check_response(await resp.json())

    async def _post(self, *args, **kwargs):
        async with self.sess.post(*args, **kwargs) as resp:
            return self._check_response(await resp.json())
    
    @staticmethod
    def error_catcher(func):
        @wraps(func)
        async def warpper(*args,**kwargs):
            try:
                return await func(*args,**kwargs)
            except Exception as e:
                logging.exception(e)
        return warpper

    async def start(self):
        self.sess = aiohttp.ClientSession(cookies=self.cookies)
        self.stoped = False

        await asyncio.gather(
                self.statsRecord(),
                self.liveSign(),
                self.getOneBattery(),
            )
    
    async def statsRecord(self):
        cnt = 0
        while 1:
            logging.info(f'Watch {cnt} hours.')
            cnt += 1
            await asyncio.sleep(3600)
    
    async def liveSign(self):
        while 1:
            try:
                info = await self._get(
                    url='https://api.live.bilibili.com/xlive/web-ucenter/v1/sign/DoSign',
                    headers=self.headers_pc,
                )
                msg = info['text']
                logging.info(f'签到成功，得到{msg}')
            except Exception as e:
                logging.debug(e)
            await asyncio.sleep(43200)

    async def getOneBattery(self):
        while not self.stoped:
            url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/userTask/UserTaskReceiveRewards"
            data = {
                "access_key": self.access_key,
                "actionKey": "appkey",
                "appkey": Crypto.APPKEY,
                "ts": int(time.time()),
            }
            try:
                info = await self._post(url, data=SingableDict(data).signed, headers=self.headers_mobile)
            except Exception as e:
                logging.exception(e)
                await asyncio.sleep(60)
            await asyncio.sleep(3600)

    async def stop(self):
        self.stoped = True
        await self.sess.close()

class BiliCheat(BaseCheat):
    def __init__(self, rid, cookies=None, access_key=None) -> None:
        super().__init__(cookies=cookies, access_key=access_key)
        self.rid = rid

    async def start(self):
        self.sess = aiohttp.ClientSession(cookies=self.cookies)
        self.stoped = False

        try:
            info = await self._get(url=f'https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={self.rid}', headers=self.headers_pc, timeout=5)
            self.rid = info['room_info']['room_id']
            self.suid = info['room_info']['uid']
            self.suname = info['anchor_info']['base_info']['uname']
            logging.info(f'Add {self.suname}, uid:{self.suid}, rid:{self.rid}.')
        except Exception as e:
            logging.exception(e)

        await asyncio.gather(
                self.popularTickets(),
                self.heartbeat(),
                self.webHeartbeat(),
                self.mobileWatch(),
                self.likeInteractV3(),
                self.sendDanmaku(),
            )
    
    async def sendDanmaku(self):
        thisday = None
        while not self.stoped:
            if thisday == datetime.now().day or await self.biliapi.asyncOnAir(self.rid):
                await asyncio.sleep(300)
                continue
            try:
                info = self.biliapi.send_danmu(self.rid, 'official_147', emoticon=1)
                if info['code'] == 0:
                    thisday = datetime.now().day
            except Exception as e:
                logging.exception(e)
            await asyncio.sleep(300)

    async def heartbeat(self):
        url = 'https://api.live.bilibili.com/relation/v1/Feed/heartBeat'
        while not self.stoped:
            try:
                resp = await self.sess.get(url, headers=self.headers_pc)
                resp_json = await resp.json()
                if resp_json.get('code') == 0:
                    logging.debug(f'Heatbeat of {self.suname}.')
            except Exception as e:
                logging.exception(e)
            await asyncio.sleep(60)

    async def webHeartbeat(self):
        url = 'https://live-trace.bilibili.com/xlive/rdata-interface/v1/heartbeat/webHeartBeat'
        next_interval = random.randint(1,60)
        while not self.stoped:
            parms = {
                'hb': base64.b64encode(f'{next_interval}|{self.rid}|1|0'.encode()).decode(),
                'pf': 'web'
            }
            resp = await self.sess.get(url,params=parms,headers=self.headers_pc)
            resp_json = await resp.json()
            if resp_json.get('code') == 0:
                logging.debug(f'WebHeatbeat of {self.suname}.')
                next_interval = resp_json['data']['next_interval']
            await asyncio.sleep(next_interval)

    async def popularTickets(self):
        while not self.stoped:
            try:
                info = await self._get(
                    url=f'https://api.live.bilibili.com/xlive/general-interface/v1/rank/getUserPopularTicketsNum?ruid={self.suid}',
                    headers=self.headers_pc,
                    cookies=cookies
                )
                num = info['free_ticket']['num']
                if num > 0:
                    data = {
                        'ruid': self.suid,
                        'csrf': self.cookies.get('bili_jct'),
                        'csrf_token': self.cookies.get('bili_jct'),
                        'visit_id': randomString(12),
                    }
                    new_cookie = self.cookies.copy()
                    new_cookie.pop('buvid3')
                    new_cookie.pop('buvid2')
                    # new_cookie.update({
                    #     'fingerprint': '825bdeb3369fce730063309779a6798b', 
                    #     'buvid_fp': '825bdeb3369fce730063309779a6798b',
                    # })
                    info = await self._post(
                        url='https://api.live.bilibili.com/xlive/general-interface/v1/rank/popularRankFreeScoreIncr',
                        data=data,
                        headers=self.headers_pc,
                        cookies=new_cookie,
                    )
                    num = info['num']
                    logging.info(f'发送给 {self.suname} {num} 个人气票.')
            except Exception as e:
                logging.exception(e)
            await asyncio.sleep(900)

    async def likeInteractV3(self):
        """
        点赞直播间V3
        """
        thisday = None
        thisday_cnt = 0
        while not self.stoped:
            try:
                if not await self.biliapi.asyncOnAir(self.rid):
                    await asyncio.sleep(300)
                    continue

                url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
                data = {
                    'click_time': random.randint(1, 10),
                    'room_id': str(self.rid),
                    'uid': self.cookies['DedeUserID'],
                    'anchor_id': str(self.suid),
                    'csrf_token': self.cookies['bili_jct'],
                    'csrf': self.cookies['bili_jct'],
                    'visit_id': '',
                }
                res = await self._post(
                    url,
                    data = data,
                    headers = self.headers_pc,
                    cookies = self.cookies,
                )

                if datetime.now().day != thisday:
                    thisday = datetime.now().day
                    thisday_cnt = 1
                else:
                    thisday_cnt += 1
            except Exception as e:
                logging.exception(e)
            await asyncio.sleep(60)

    async def mobileHeartbeat(self):
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/heartbeat/mobileHeartBeat"
        data = {
            'platform': 'android',
            'uuid': self.uuids[0],
            'buvid': randomString(37).upper(),
            'seq_id': '1',
            'room_id': f'{self.rid}',
            'parent_id': '6',
            'area_id': '283',
            'timestamp': f'{int(time.time())-60}',
            'secret_key': 'axoaadsffcazxksectbbb',
            'watch_time': '60',
            'up_id': f'{self.suid}',
            'up_level': '40',
            'jump_from': '30000',
            'gu_id': randomString(43).lower(),
            'play_type': '0',
            'play_url': '',
            's_time': '0',
            'data_behavior_id': '',
            'data_source_id': '',
            'up_session': f'l:one:live:record:{self.rid}:{int(time.time())-88888}',
            'visit_id': randomString(32).lower(),
            'watch_status': '%7B%22pk_id%22%3A0%2C%22screen_status%22%3A1%7D',
            'click_id': self.uuids[1],
            'session_id': '',
            'player_type': '0',
            'client_ts': f'{int(time.time())}',
        }
        data.update(
            {
                'client_sign': client_sign(data),
                "access_key": self.access_key,
                "actionKey": "appkey",
                "appkey": Crypto.APPKEY,
                "ts": int(time.time()),
            }
        )
        return await self._post(
            url,
            data=SingableDict(data).signed,
            headers=self.headers_mobile.update(
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                }
            ),
        )

    async def mobileWatch(self):
        time_cnt = 0
        self.uuids = [str(uuid.uuid4()) for _ in range(2)]
        while not self.stoped:
            try:
                await self.mobileHeartbeat()
                logging.debug(f'Watch {self.suname} {time_cnt} minutes.')
                time_cnt += 1
            except Exception as e:
                logging.exception(e)
            await asyncio.sleep(60)

async def main(room_list):
    tasks = {}

    cheat = BaseCheat(cookies=cookies,access_key=access_key)
    basetask = asyncio.create_task(cheat.start())

    while 1:
        with open(room_list,'r') as f:
            rids = [x.strip() for x in f.readlines()]
            insert = set(rids) - set(tasks.keys())
            for rid in insert:
                worker = BiliCheat(rid,cookies=cookies,access_key=access_key)
                task = asyncio.create_task(worker.start())
                tasks[rid] = {
                    'class': worker,
                    'task': task,
                }
            
            delete = set(tasks) - set(rids)
            for rid in delete:
                worker = tasks[rid]['class']
                task = tasks[rid]['task']
                await worker.stop()
                task.cancel()
                logging.info(f'Delete task {worker.suname}.')
                tasks.pop(rid)

        await asyncio.sleep(60)

if __name__ == '__main__':
    with open('login_info/bili-main.json', encoding='utf8') as f:
        cookies = json.load(f)
        cookies = {it['name']:it['value'] for it in cookies['cookie_info']['cookies']}

    with open('login_info/login_info.txt','r') as f:
        access_key = f.read().strip()
    
    logging.getLogger().setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) 
    console_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s"))
    
    os.makedirs('logs',exist_ok=True)
    logname = f'logs/bilicheat-origin.log'
    file_handler = logging.handlers.TimedRotatingFileHandler(logname, when='D', interval=1, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s"))
    
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)

    login_info = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=BiliCheat.headers_pc, cookies=cookies).json()
    if login_info['code'] == 0:
        logging.info(f"Cookies值有效，{login_info['data']['uname']}，已登录！")
    else:
        logging.error('Cookies值已经失效，请重新扫码登录！')
        exit(0)
    url = "https://app.bilibili.com/x/v2/account/mine"
    params = {
        "access_key": access_key,
        "actionKey": "appkey",
        "appkey": Crypto.APPKEY,
        "ts": int(time.time()),
    }
    login_info = requests.get(url, params=SingableDict(params).signed, headers=BiliCheat.headers_mobile).json()
    if login_info['data']['mid'] == 0:
        logging.error('Access_key已经失效，请重新扫码登录！')
        exit(0)
    else:
        logging.info('Access_key有效！')

    asyncio.run(main('WATCH_LIVE_ORIGIN.txt'))