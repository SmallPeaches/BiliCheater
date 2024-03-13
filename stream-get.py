import requests
import subprocess
import queue
import time
import m3u8
import socket
import random
import argparse
import ipaddress
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


def is_ipv6(address):
    try:
        ipaddress.IPv6Address(address)
        return True
    except ipaddress.AddressValueError:
        return False

HEADERS = {
    'referer': 'https://live.bilibili.com',
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.54',
}

class StreamGet():
    def __init__(self, nthreads=2, ipv6=False, limit=None, rids=None, ):
        self.count_q = queue.Queue()
        self.url_q = queue.Queue()
        self.nthreads = nthreads
        self.rids = rids or []
        self.ipv6 = ipv6
        self.limit = 2**64 if not limit else int(limit)
        self.sess = requests.Session()

    def download_one(self):
        while 1:
            url = self.url_q.get()
            print(f'\nDownloading {url}')
            try:
                if '.m3u8' not in url:
                    print(f'Not a m3u8 file: {url}.')
                    continue
                for _ in range(256):
                    index = self.sess.get(url, headers=HEADERS, timeout=5).text
                    m3u8_obj = m3u8.loads(index, uri=url)
                    while not m3u8_obj.segments:
                        if not m3u8_obj.playlists:
                            raise Exception('No segments found.')
                        index = self.sess.get(m3u8_obj.playlists[0].absolute_uri, headers=HEADERS, timeout=5).text
                        m3u8_obj = m3u8.loads(index, uri=url)
                    for seg in m3u8_obj.segments:
                        resp = self.sess.get(seg.absolute_uri, headers=HEADERS, timeout=5, stream=True)
                        if resp.status_code != 200:
                            print(f'Error: {resp.status_code}.')
                            break
                        while 1:
                            if self.total_this_second < self.limit*1024:
                                try:
                                    chunk = next(resp.iter_content(chunk_size=1024))
                                    self.total_this_second += len(chunk)
                                    self.count_q.put(len(chunk))
                                except StopIteration:
                                    break
                            else:
                                time.sleep(0.1)
                                continue
            except Exception as e:
                print(e)
    
    def get_urls(self):
        while 1:
            if self.url_q.qsize() > 32:
                time.sleep(10)
                continue
            try:
                rids = self.rids.copy()
                APEX_PAGE_URL = 'https://api.live.bilibili.com/xlive/web-interface/v1/second/getList'
                params = {
                    'platform': 'web',
                    'parent_area_id': 2,
                    'area_id': 240,
                    'sort_type': 'online',
                    'page': random.randint(1, 10),
                }
                page = self.sess.get(APEX_PAGE_URL, headers=HEADERS, params=params, timeout=5).json()
                for user in page['data']['list']:
                    rids.append(user['roomid'])

                for rid in rids:
                    resp = self.sess.get(f'https://api.live.bilibili.com/room/v1/Room/room_init?id={rid}',headers=HEADERS,timeout=5).json()
                    live_status = resp['data']['live_status']
                    if live_status == 1:
                        url = self.get_stream_url(rid)
                        if url: self.url_q.put_nowait(url)
            except Exception as e:
                print(e)
            
    def gather(self):
        t0 = datetime.now().timestamp()
        total = 0
        while 1:
            self.total_this_second = 0
            t2 = datetime.now().timestamp()
            time.sleep(1)
            cnt = 0
            for _ in range(self.count_q.qsize()):
                cnt += self.count_q.get()
            total += cnt
            t1 = datetime.now().timestamp()
            avg_speed = total/(t1-t0)
            speed = cnt/(t1-t2)
            print(f'\rDownload {total/1024/1024:.2f} MB, Speed {speed/1024/1024:.2f} MB/s, AvgSpeed {avg_speed/1024/1024:.2f} MB/s', end='')

    def start(self):
        with ThreadPoolExecutor(max_workers=self.nthreads+2) as pool:
            pool.submit(self.gather)
            pool.submit(self.get_urls)
            for i in range(self.nthreads):
                pool.submit(self.download_one)
            
    def get_stream_url(self, rid) -> str:
        real_url = ''
        r_url = 'https://api.live.bilibili.com/room/v1/Room/room_init?id={}'.format(rid)
        res = self.sess.get(r_url,timeout=5,headers=HEADERS).json()
        code = res['code']
        if code == 0:
            live_status = res['data']['live_status']
            if live_status == 1:
                room_id = res['data']['room_id']
                f_url = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo'
                params = {
                    'room_id': room_id,
                    'platform': 'html5',
                    'protocol': '1',
                    'format': '0,1,2',
                    'codec': '0',
                    'qn': 20000,
                    'ptype': 8,
                    'dolby': 5,
                    'panorama': 1
                }
                resp = self.sess.get(f_url, params=params, headers=HEADERS, timeout=5).json()
                stream = resp['data']['playurl_info']['playurl']['stream']
                real_urls = []
                for protocol_info in stream:
                    for format_info in protocol_info['format']:
                        format_name = format_info['format_name']
                        http_info = format_info['codec'][0]
                        base_url = http_info['base_url']
                        for info in http_info['url_info']:
                            host = info['host']
                            extra = info['extra']
                            url = host + base_url + extra
                            
                            if self.ipv6:
                                ip_address = socket.getaddrinfo(host.split('//')[1], None)[0][4][0]
                                if is_ipv6(ip_address): 
                                    real_urls.append(url)
                            else:
                                real_urls.append(url)
                if not real_urls:
                    return None
                real_url = random.choice(real_urls)
        return real_url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--nthreads', type=int, default=4, help='Number of threads.')
    parser.add_argument('-l', '--limit', type=int, default=0, help='Speed limit in KB/s.')
    parser.add_argument('-6', '--ipv6', action='store_true', help='Prefer IPv6.', default=False)
    args = parser.parse_args()
    sg = StreamGet(nthreads=args.nthreads, ipv6=args.ipv6, limit=args.limit)
    
    old_getaddrinfo = socket.getaddrinfo
    def getaddrinfo_v6(*args):
        responses = old_getaddrinfo(*args)
        sorted_responses = sorted(responses, key=lambda response: response[0] == socket.AF_INET6, reverse=True)
        return sorted_responses
    socket.getaddrinfo = getaddrinfo_v6

    try:
        sg.start()
    except KeyboardInterrupt:
        exit(0)