import requests
import math
import yt_dlp
from datetime import datetime
from ytdlp import ytdlp


def time_str_to_seconds(time_str):
    parts = time_str.split(":")
    if len(parts) == 3:
        # 时间格式为 HH:MM:SS
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    elif len(parts) == 2:
        # 时间格式为 MM:SS
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    else:
        raise ValueError("Invalid time format")
    

from yt_dlp.extractor.douyutv import *
def _real_extract(self, url):
    url = url.replace('vmobile.', 'v.')
    video_id = self._match_id(url)

    webpage = self._download_webpage(url, video_id)

    video_info = self._search_json(
        r'<script>\s*window\.\$DATA\s*=', webpage,
        'video info', video_id, transform_source=js_to_json)

    js_sign_func = self._search_js_sign_func(webpage)
    form_data = {
        'vid': video_id,
        **self._calc_sign(js_sign_func, video_id, video_info['ROOM']['point_id']),
    }
    url_info = self._download_json(
        'https://v.douyu.com/wgapi/vodnc/front/stream/getStreamUrlWeb', video_id,
        data=urlencode_postdata(form_data), note="Downloading video formats")

    formats = []
    for name, url in traverse_obj(url_info, ('data', 'thumb_video', {dict.items}, ...)):
        video_url = traverse_obj(url, ('url', {url_or_none}))
        if video_url:
            ext = determine_ext(video_url)
            formats.append({
                'format': self._FORMATS.get(name),
                'format_id': name,
                'url': video_url,
                'quality': self._QUALITIES.get(name),
                'ext': 'mp4' if ext == 'm3u8' else ext,
                'protocol': 'm3u8_native' if ext == 'm3u8' else 'https',
                **parse_resolution(self._RESOLUTIONS.get(name))
            })
        else:
            self.to_screen(
                f'"{self._FORMATS.get(name, name)}" format may require logging in. {self._login_hint()}')

    return {
        'id': video_id,
        'formats': formats,
        **traverse_obj(video_info, ('DATA', {
            'title': ('content', 'title', {str}),
            'uploader': ('content', 'author', {str}),
            'uploader_id': ('content', 'up_id', {str_or_none}),
            'duration': ('content', 'video_duration', {int_or_none}),
            'thumbnail': ('content', 'video_pic', {url_or_none}),
            'timestamp': ('content', 'create_time', {int_or_none}),
            'view_count': ('content', 'view_num', {int_or_none}),
            'tags': ('videoTag', ..., 'tagName', {str}),
        }))
    }
DouyuShowIE._real_extract = _real_extract


class DouyuLiveReplay:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }
    def __init__(self, uid):
        self.uid = uid
        self.sess = requests.Session()

    def __del__(self):
        self.sess.close()

    def sess_get(self, url, params=None, **kwargs):
        resp = self.sess.get(url, headers=self.headers, params=params, **kwargs).json()
        if resp['error'] != 0:
            raise Exception(resp['msg'])
        return resp['data']

    def video_list(self, start_time=None, end_time=None, reverse=False):
        url = f'https://v.douyu.com/wgapi/vod/center/authorShowVideoList'
        LIMIT = 5
        params = {
            'page': 1,
            'limit': LIMIT,
            'up_id': self.uid,
        }
        if start_time: params['start_time'] = start_time
        if end_time: params['end_time'] = end_time
        resp = self.sess_get(url, params=params)
        page_nums = math.ceil(resp['count'] / LIMIT)
        if reverse:
            page_range = range(page_nums, 0, -1)
        else:
            page_range = range(1, page_nums + 1)
        for page in page_range:
            params['page'] = page
            resp = self.sess_get(url, params=params)
            if reverse:
                replay_list = reversed(resp['list'])
            else: 
                replay_list = resp['list']
            for replay_info in replay_list:
                video = replay_info['video_list'][0]
                video_info = {
                    'vid': video['hash_id'],
                    'time': datetime.fromtimestamp(video['start_time']),
                    'duration': video['video_duration'],
                    'title': video['title'],
                    'cover': video['video_pic'],
                    'author': video['author'],
                    'uid': self.uid,
                }
                yield video_info

    def get_video_segments(self, vid, uid=None):
        url = f'https://v.douyu.com/wgapi/vod/center/getShowReplayList'
        params = {
            'vid': vid,
            'up_id': uid or self.uid,
        }
        resp = self.sess_get(url, params=params)
        videos = resp['list']
        if not videos:
            return None
        segments = []
        for video in videos:
            segments.append({
                'vid': video['hash_id'],
                'duration': time_str_to_seconds(video['video_duration']),
                'title': video['title'],
                'segment_title': video['show_remark'],
            })
        return segments
    
    def download_one(self, vid, output_file):
        extra_args = {
            'concurrent_fragment_downloads': 3,
        }
        return ytdlp.download_func(f'https://v.douyu.com/show/{vid}', output_file, extra_args=extra_args)
    
    def download_all(self, output_dir='.', start_time=None, end_time=None, reverse=False, num_workers=1):
        for video_info in self.video_list(start_time, end_time, reverse=reverse):
            segments = self.get_video_segments(video_info['vid'])
            if not segments:
                print(f"Video {video_info['vid']} has no segments")
                continue

            for i, segment in enumerate(segments):
                output_file = f"{output_dir}/[{video_info['time'].strftime('%Y-%m-%d')}]{video_info['title']}/{segment['segment_title']}.mp4"
                print(f"Downloading {output_file}...")
                self.download_one(segment['vid'], output_file)
            
            print(f"Downloaded all segments of {video_info['title']}")
    
    def download_batch(self, vid, output_dir):
        segments = self.get_video_segments(vid)
        if not segments:
            raise RuntimeError(f"Video {vid} has no segments")

        for i, segment in enumerate(segments):
            output_file = f"{output_dir}/{segment['segment_title']}.mp4"
            print(f"Downloading {output_file}...")
            self.download_one(segment['vid'], output_file)
        
        print(f"Downloaded all segments of {vid}")


if __name__ == '__main__':
    dl = DouyuLiveReplay('JGdyYY0XadXy')
    # dl.download_all('videos', reverse=0)
    dl.download_batch('Bjq4MexZERg75Ea8', 'videos')
