import json
import random
import requests
from functools import reduce
from hashlib import md5
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import time
from utils import *


class BiliVideoAPI:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'Referer': 'https://www.bilibili.com/',
    }
    def __init__(self, cookies=None) -> None:
        self.sess = requests.Session()
        if cookies is None:
            self.cookies = {}
        else:
            with open(cookies, encoding='utf8') as f:
                cookies = json.load(f)
                cookies = {it['name']:it['value'] for it in cookies['cookie_info']['cookies']}
            self.cookies = cookies
        resp = self.sess.get('https://api.bilibili.com/x/frontend/finger/spi', headers=self.headers, cookies=self.cookies).json()
        self.cookies['buvid3'] = resp['data']['b_3']
        self.cookies['buvid4'] = resp['data']['b_4']
        self.img_key, self.sub_key = getWbiKeys()
        self.cache = {}

    def clean_cache(self):
        self.cache = {}

    def get_video_info(self, bvid):
        resp = self.sess.get(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}', headers=self.headers).json()
        if resp['code'] == 0:
            return resp['data']
        raise RuntimeError(resp['message'])
    
    def get_video_info_v2(self, bvid):
        params = {'bvid': bvid}
        # resp = self.sess.get(
        #     f'https://api.bilibili.com/x/web-interface/wbi/view/detail',
        #     headers=self.headers, 
        #     params=encWbi(params, img_key=self.img_key, sub_key=self.sub_key),
        # ).json()
        resp = self.sess.get(
            f'https://api.bilibili.com/x/web-interface/view/detail',
            headers=self.headers, 
            params=params,
        ).json()
        if resp['code'] == 0:
            return resp['data']
        raise RuntimeError(resp['message'])

    def like_video(self, bvid):
        url = f'https://api.bilibili.com/x/web-interface/archive/like'
        data = {
            'bvid': bvid,
            'like': 1,
            'eab_x': 1,
            'ramval': 2,
            'source': 'web_normal',
            'ga': 1,
            'csrf': self.cookies['bili_jct'],
        }
        resp = self.sess.post(url, headers=self.headers, cookies=self.cookies, data=data).json()
        if resp['code'] == 0:
            return 0
        raise RuntimeError(resp['message'])
    
    def fav_video(self, bvid, mlid):
        url = f'https://api.bilibili.com/x/v3/fav/resource/deal'
        if not isinstance(mlid, list):
            mlid = [mlid]
        mlid = [str(i) for i in mlid]
        data = {
            'rid': BVID2AVID(bvid),
            'type': 2,
            'add_media_ids': ','.join(mlid),
            'csrf': self.cookies['bili_jct'],
        }
        resp = self.sess.post(url, headers=self.headers, cookies=self.cookies, data=data).json()
        if resp['code'] == 0:
            return 0
        raise RuntimeError(resp['message'])
    
    def share_video(self, bvid):
        url = f'https://api.bilibili.com/x/web-interface/share/add'
        data = {
            'bvid': bvid,
            'csrf': self.cookies['bili_jct'],
        }
        resp = self.sess.post(url, headers=self.headers, cookies=self.cookies, data=data).json()
        if resp['code'] == 0:
            return 0
        raise RuntimeError(resp['message'])
    
    def get_feed_videos(self, size=10):
        url = f'https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd'
        if self.cache.get('uniq_id') is None:
            self.cache['uniq_id'] = random.randint(10**13, 2*10**13)
        params = {
            'web_location': 1430650,
            'y_num': 8,
            'fresh_type': 3,
            'feed_version': 'V8',
            'fresh_idx_1h': 1,
            'fetch_row': 1,
            'fresh_idx': 1,
            'brush': 1,
            'homepage_ver': 1,
            'ps': size,
            'last_y_num': 8,
            'screen': '1920-1080',
            'seo_info': '',
            'last_showlist': self.cache.get('last_showlist', 'av_712909579'), 
            'uniq_id': self.cache['uniq_id'],
        }
        params = encWbi(params, img_key=self.img_key, sub_key=self.sub_key)
        resp = self.sess.get(url, headers=self.headers, cookies=self.cookies, params=params).json()
        if resp['code'] == 0:
            avids = ['av_'+str(x['id']) for x in resp['data']['item'] if x['id']]
            self.cache['last_showlist'] = self.cache.get('last_showlist','') + ','.join(avids) + ';'
            return resp['data']
        raise RuntimeError(resp['message'])
    
    def get_user_videos(self, user_id, page=1, page_size=30):
        header = {
            'accept-language': 'en,zh-CN;q=0.9,zh;q=0.8',
            'User-Agent': 'Mozilla/5.0',
        }
        cookie = self.cookies.copy()
        cookie['SESSDATA'] = ''
        dm_rand = 'ABCDEFGHIJK'
        dm_img_list = '[]'
        dm_img_str = ''.join(random.sample(dm_rand, 2))
        dm_cover_img_str = ''.join(random.sample(dm_rand, 2))
        dm_img_inter = '{"ds":[],"wh":[0,0,0],"of":[0,0,0]}'
        encoded_parms = encWbi(
            {
                'mid': user_id,
                'pn': page,
                'ps': page_size,
                'order': 'pubdate',
                "platform": "web",
                "web_location": "1550101",
                "order_avoided": "true",
                "dm_img_list": dm_img_list,
                "dm_img_str": dm_img_str,
                "dm_cover_img_str": dm_cover_img_str,
                "dm_img_inter": dm_img_inter,
            },
            img_key=self.img_key,
            sub_key=self.sub_key,
        )
        resp = self.sess.get(
            url='https://api.bilibili.com/x/space/wbi/arc/search',
            params=encoded_parms,
            headers=header,
            cookies=cookie,
        ).json()
        return resp['data']
    
    def get_user_info(self, user_id):
        params = encWbi({
            'mid': user_id,
            },
            img_key=self.img_key, sub_key=self.sub_key,
        )
        resp = self.sess.get('https://api.bilibili.com/x/space/wbi/acc/info', params=params).json()
        return resp['data']
    