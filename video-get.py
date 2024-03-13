import argparse
import shutil
import time
import os
import subprocess
import random
import glob
import sys

from concurrent.futures import ThreadPoolExecutor
from bilidown import BiliDown


def download_one(url, path):
    uuid = random.randint(0, 100000)
    cmd = ['yutto', '-w', '-b', '--no-danmaku', '--no-subtitle']
    cmd += ['-d', path, '-tp', r'{name}-'+str(uuid)]
    cmd += ['--no-color', '--no-progress']
    cmd += [url]
    print(f'Downloading {url}...')
    try:
        with open(os.path.join(path,f'yutto-{uuid}.log'), 'w') as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, encoding='utf8')
            proc.wait(timeout=3600)
    except subprocess.TimeoutExpired:
        print(f'Download {url} timeout, kill.')
        proc.kill()
    files = glob.glob(os.path.join(path, f'*-{uuid}.*'))
    filesize = sum([os.path.getsize(f) for f in files])/1024/1024
    global total_size
    total_size += filesize
    print(f'Download {url} finished. Filesize: {filesize:.2f} MB, Total {total_size:.2f} MB. Delete.')
    for f in files:
        os.remove(f)

def download_batch(urls, path, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for url in urls:
            pool.submit(download_one, url, path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Infinite download bilibili videos.')
    parser.add_argument('-u', '--uid', type=str, default='275729731', help='The user id to download from.')
    parser.add_argument('-n', '--nthreads', type=int, default=4, help='The number of parallel downloads.')
    parser.add_argument('-b', '--batchsize', type=int, default=30, help='The number of videos to download in one batch.')
    parser.add_argument('-r', '--reverse', action='store_true', help='Reverse the download order.')
    parser.add_argument('--tempfile', type=str, help='The tempfile path to save the videos.')
    args = parser.parse_args()

    if args.tempfile is None:
        tempfile = f'./tempfile'
    else:
        tempfile = args.tempfile
    if os.path.exists(tempfile):
        shutil.rmtree(tempfile)
    os.makedirs(tempfile, exist_ok=True)
    total_size = 0
    
    while 1:
        try:
            DL = BiliDown()
            user_id = args.uid
            user_videos_info = DL.vapi.get_user_videos(user_id)

            video_count = user_videos_info['page']['count']
            video_pages = video_count//30
            if args.reverse:
                iter_range = range(video_pages, 0, -1)
            else:
                iter_range = range(1, video_pages+1)
            
            for page_id in iter_range:
                this_videos = DL.vapi.get_user_videos(user_id, page=page_id)['list']['vlist']
                bvid_list = [video_info['bvid'] for video_info in this_videos]
                download_batch(bvid_list, max_workers=args.nthreads, path=tempfile)
        except KeyboardInterrupt:
            exit(0)
        except Exception as e:
            print(e)
        finally:
            if os.path.exists(tempfile):
                shutil.rmtree(tempfile)
        time.sleep(60)