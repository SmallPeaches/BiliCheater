import logging
import random
import time
import requests
import traceback
from videoapi import BiliVideoAPI

COOKIES = r'login_info\bili-xiaohao.json'
FAV_MAPPING = {
    2935820373: ['apex'],
    2956820473: ['csgo', 'cs2'],
    2914806773: ['valorant', '瓦罗兰特', '无畏契约'],
    2875821773: ['原神', 'genshin'],
}


if __name__ == '__main__':
    vapi = BiliVideoAPI(COOKIES)
    num_videos = 0
    num_valid_videos = 0
    while num_videos < 10000:
        try:
            fvideos = vapi.get_feed_videos()
            # vapi.clean_cache()
            for video in fvideos['item']:
                bvid = video['bvid']
                uri = f'https://www.bilibili.com/video/{bvid}'
                if not bvid: continue
                video_info = vapi.get_video_info_v2(bvid)
                title = video_info['View']['title']
                desc = video_info['View']['desc']
                tags_str = ','.join(tag['tag_name']for tag in video_info['Tags'])

                total_str = f'{title} {desc} {tags_str}'.lower()
                valid = False
                fav_mlids = []
                domain = []
                num_videos += 1
                for mlid, keywords in FAV_MAPPING.items():
                    if any(kw in total_str for kw in keywords):
                        valid = True
                        fav_mlids.append(mlid)
                        domain.append(keywords[0])
                if not valid: 
                    print(f'[{num_videos:04d}] Video: {uri} {title} not match any keywords.')
                    time.sleep(1)
                    continue
                num_valid_videos += 1
                print(f'[{num_valid_videos:04d}/{num_videos:04d}] Found {domain} video: {uri} {title}.')
                try:
                    vapi.like_video(bvid)
                except Exception as e:
                    print(f'Failed to like video: {uri}: {e}')
                    time.sleep(5)
                time.sleep(1)
                try:
                    pass
                    # vapi.share_video(bvid)
                except Exception as e:
                    print(f'Failed to share video: {uri}: {e}')
                time.sleep(1)
                try:
                    vapi.fav_video(bvid, fav_mlids)
                except Exception as e:
                    print(f'Failed to favorite video: {uri}: {e}')
                time.sleep(10)
        except Exception as e:
            traceback.print_exc()
            time.sleep(random.randint(60,180))

    # bvid = 'BV1hF4m177DW'
    # vapi.like_video(bvid)
    # vapi.fav_video(bvid, FAV_MLID)
    # vapi.share_video(bvid)
    # print(f'Liked, favorited, and shared video: {bvid}')