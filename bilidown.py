import math
import random
import subprocess
import os
import json
import requests
import re

from concurrent.futures import ThreadPoolExecutor
from videoapi import BiliVideoAPI
from utils import *

class BiliDown():
    def __init__(self, cookies_path:str=None) -> None:
        if cookies_path:
            with open(cookies_path, encoding='utf8') as f:
                cookies = json.load(f)
            self.cookies = {it['name']:it['value'] for it in cookies['cookie_info']['cookies']}
        else:
            self.cookies = {}
        self.vapi = BiliVideoAPI(cookies_path)
        self.img_key, self.sub_key = getWbiKeys()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
            'Referer': 'https://www.bilibili.com/',
        }

    def download_one(self, url, path, batch=True, danmaku=False, subtitle=False, extra_args:list=None):
        cmd = ['yutto', '-w']
        if self.cookies: cmd += ['-c', self.cookies['SESSDATA']]
        if path.endswith('}'):
            cmd += ['-tp', path]
        elif os.path.splitext(path)[1] == '':
            cmd += ['-d', path, '-tp', r'{name}']
        else:
            dirs, name = os.path.split(path)
            cmd += ['-d', dirs, '-tp', os.path.splitext(name)[0]]
        if batch: cmd += ['-b']
        if not danmaku: cmd += ['--no-danmaku']
        if not subtitle: cmd += ['--no-subtitle']
        # cmd += ['-q', 127]
        cmd += extra_args if extra_args is not None else []
        cmd += [url]
        cmd = [str(c) for c in cmd]

        # proc = subprocess.Popen(cmd,stderr=subprocess.PIPE)
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        proc.wait()

        err = proc.stderr.read().decode('utf8', errors='ignore')
        if err:
            print(err)
            return False
        return True
    
    def download_batch(self, url_list, max_workers=None, **kwargs):
        if max_workers is None: max_workers = len(url_list)
        def _download_one(url):
            print(f'Downloading {url}...')
            ret = self.download_one(url, **kwargs)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for url in url_list:
                pool.submit(_download_one, url)
        return

    def download_user(self, user, parallel=1, path=None):
        user_id = re.search(r'space.bilibili.com/\d+', user)[0].split('/')[-1]
        user_videos_info = self.vapi.get_user_videos(user_id)
        user_info = self.vapi.get_user_info(user_id)
        username = user_info['name']

        video_count = user_videos_info['page']['count']
        video_pages = math.ceil(video_count/30)
        for page_id in range(1, video_pages+1):
            this_videos = self.vapi.get_user_videos(user_id, page=page_id)['list']['vlist']
            bvid_list = [video_info['bvid'] for video_info in this_videos]
            output_path = f'./{username}/{{title}}/{{name}}' if path is None else path
            self.download_batch(bvid_list, max_workers=parallel, path=output_path)

if __name__ == '__main__':
    DL = BiliDown()
    DL.download_user('https://space.bilibili.com/2062760', 2)
    # DL.download_one('https://www.bilibili.com/video/BV1EN4y1v7ia', 'videos-1080P60', extra_args=['-q', 116])
    # DL.download_one('https://space.bilibili.com/58271553/?spm_id_from=333.999.0.0', 'videos')
