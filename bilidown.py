import math
import random
import subprocess
import os
import json
import requests
import re
import yutto

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

    def download_one(self, url, path=None, batch=True, danmaku=False, subtitle=False, timeout=None, extra_args:list=None):
        cmd = ['yutto', '-w', '--vip-strict']
        if self.cookies: cmd += ['-c', self.cookies['SESSDATA']]
        if not path:
            pass
        elif path.endswith('}'):
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
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f'Timeout for {url}')
            proc.kill()
            return False

        err = proc.stderr.read().decode('utf8', errors='ignore')
        if err:
            print(err)
            return False
        return True
    
    def download_one_v2(self, url, *args, **kwargs):
        ret = self.download_one(url, **kwargs)
        while not ret:
            print(f'Download {url} failed, retrying...')
            ret = self.download_one(url, **kwargs)
    
    def download_batch(self, url_list, max_workers=None, **kwargs):
        if max_workers is None: max_workers = len(url_list)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for url in url_list:
                pool.submit(self.download_one_v2, url, **kwargs)
        return
    
    def filter_videos(self, bvid, keywords=None):
        if not keywords:
            return True
        video_info = self.vapi.get_video_info_v2(bvid)
        title = video_info['View']['title']
        desc = video_info['View']['desc']
        tags_str = ','.join(tag['tag_name']for tag in video_info['Tags'])
        total_str = f'{title} {desc} {tags_str}'.lower()
        if keywords:
            keywords = keywords if isinstance(keywords, list) else [keywords]
            for keyword in keywords:
                if keyword in total_str:
                    return True
        return False

    def download_user(self, user, path=None, parallel=1, filter_args=None, **kwargs):
        user_id = re.search(r'space.bilibili.com/\d+', user)[0].split('/')[-1]
        user_videos_info = self.vapi.get_user_videos(user_id)
        user_info = self.vapi.get_user_info(user_id)
        username = user_info['name']

        video_count = user_videos_info['page']['count']
        video_pages = math.ceil(video_count/30)
        for page_id in range(1, video_pages+1):
            this_videos = self.vapi.get_user_videos(user_id, page=page_id)['list']['vlist']
            if filter_args is not None:
                bvid_list = []
                for video_info in this_videos:
                    bvid = video_info['bvid']
                    if self.filter_videos(bvid, **filter_args):
                        bvid_list.append(bvid)
                    else:
                        print(f'{video_info["title"]} not match {filter_args}, skip.')
            else:
                bvid_list = [video_info['bvid'] for video_info in this_videos]
            output_path = f'./{username}/{{title}}/{{name}}' if path is None else path.replace('{username}', username)
            self.download_batch(bvid_list, max_workers=parallel, path=output_path, **kwargs)

    def download_bangumi(self, ssid, path=None, parrallel=1, **kwargs):
        bangumi_info = self.vapi.get_bangumi_info(ssid)
        output_path = r'./videos/{title}/{name}' if path is None else path
        with ThreadPoolExecutorBlocking(max_workers=parrallel) as pool:
            total_ep = len(bangumi_info['episodes'])
            for idx, ep in enumerate(bangumi_info['episodes']):
                print(f'Downloading {idx+1}/{total_ep}:{ep["long_title"]}...')
                bvid = ep['bvid']
                pool.submit(self.download_one_v2, bvid, path=output_path, batch=False, **kwargs)

    def download_bangumi_allseason(self, ssid, path=None, parrallel=1, **kwargs):
        bangumi_info = self.vapi.get_bangumi_info(ssid)
        output_path = r'./videos/{title}/{name}' if path is None else path
        for season in bangumi_info['seasons']:
            self.download_bangumi(season['season_id'], output_path, parrallel, **kwargs)


if __name__ == '__main__':
    # DL = BiliDown()
    DL = BiliDown('login_info/bili-xiaohao.json')
    DL.download_one('https://www.bilibili.com/video/BV1ZwLVzpEky/')
    # DL.download_user('https://space.bilibili.com/272806101', r'D:\FileServer/{username}/{auto}', 
    #                  parallel=1, filter_args={'keywords': 'aimbot'})
    # DL.download_user('https://space.bilibili.com/1853214351/', r'D:\FileServer/{username}/{auto}', 
    #                  parallel=2)
    # DL.download_one('https://space.bilibili.com/75665203/channel/collectiondetail?sid=3058421', r'videos/{series_title}/{title}')
    # DL.download_bangumi_allseason('ss47625', r'D:\FileServer/{title}/{name}', parrallel=2)
    # for ssid in ['ss47625', 'ss45581', 'ss45582', 'ss41305', 'ss45579', 'ss45580']:
    #     DL.download_bangumi(ssid, r'D:\FileServer/{title}/{name}', parrallel=2, timeout=60000)
