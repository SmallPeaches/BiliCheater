import glob
import subprocess
import requests
import os
import re
import time
import json
import m3u8
import base64
import functools
from os.path import *
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from urllib.parse import quote, unquote
from datetime import datetime


HEADERS = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'content-type': 'application/json',
    'origin': 'https://www.faceit.com',
    'priority': 'u=1, i',
    'referer': 'https://www.faceit.com/',
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0'
}

def download_ts(url, output, sess, retry=10):
    print(f"Downloading {output}")
    while retry >= 0:
        try:
            response = sess.get(url, timeout=10)
            if response.status_code == 403:
                print(f"403 Forbidden: {url}")
                return None
            response.raise_for_status()
            with open(output, "wb") as f:
                f.write(response.content)
            break
        except Exception as e:
            print(e)
            time.sleep(3)
            retry -= 1
    return None

def download_m3u8(url, output_name, headers=None, retry=3, max_workers=20):
    if not headers:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
            'Referer': 'https://www.faceit.com/',
        }
    m3u8_obj = m3u8.load(url, headers=headers)
    segments = m3u8_obj.segments
    sessions = [requests.Session() for _ in range(max_workers)]
    for sess in sessions:
        sess.headers.update(headers)
    ts_files = []
    tempdir = splitext(output_name)[0]
    os.makedirs(tempdir, exist_ok=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, seg in enumerate(segments):
            uri = seg.absolute_uri
            tsf = join(tempdir, f'{idx:06d}.ts')
            ts_files.append(tsf)
            if exists(tsf):
                continue
            executor.submit(download_ts, uri, tsf, sessions[idx % max_workers], retry)

    list_file = join(tempdir, 'list.txt')
    with open(list_file, 'w') as f:
        for tsf in ts_files:
            f.write(f"file '{abspath(tsf)}'\n")
    ret = subprocess.Popen([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_name
    ]).wait()
    if ret == 0:
        print(f"Merge success: {output_name}")
        os.remove(list_file)
        for tsf in ts_files:
            os.remove(tsf)
        os.rmdir(tempdir)
    else:
        print(f"Merge failed: {output_name}")

def download_m3u8_v2(stream_id, team, output_name, headers=None, retry=3, max_workers=20):
    for _ in range(5):
        uris = get_m3u8_uris(stream_id)[team]
        m3u8_file = video_file.replace('.ts', '.m3u8')
        if exists(video_file):
            return
        get_m3u8_file_v2(uris, m3u8_file)

        m3u8_obj = m3u8.load(m3u8_file, headers=headers)
        segments = m3u8_obj.segments
        sessions = [requests.Session() for _ in range(max_workers)]
        for sess in sessions:
            sess.headers.update(headers)
        ts_files = []
        tempdir = splitext(output_name)[0]
        os.makedirs(tempdir, exist_ok=True)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, seg in enumerate(segments):
                uri = seg.absolute_uri
                tsf = join(tempdir, f'{idx:06d}.ts')
                ts_files.append(tsf)
                if exists(tsf):
                    continue
                executor.submit(download_ts, uri, tsf, sessions[idx % max_workers], retry)

        # Check if all ts files exist
        if all([exists(tsf) for tsf in ts_files]):
            break

    list_file = join(tempdir, 'list.txt')
    with open(list_file, 'w') as f:
        for tsf in ts_files:
            f.write(f"file '{abspath(tsf)}'\n")
    ret = subprocess.Popen([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_name
    ]).wait()
    if ret == 0:
        print(f"Merge success: {output_name}")
        os.remove(list_file)
        for tsf in ts_files:
            os.remove(tsf)
        os.rmdir(tempdir)
    else:
        print(f"Merge failed: {output_name}")

def get_match_metadata(match_id:str):
    uri = f'https://www.faceit.com/api/watch-catalogue/v2/matches/{match_id}?v=1'
    metadata = requests.get(uri, headers=HEADERS).json()
    return metadata['payload']['match']

def get_vod_data(stream_id:str):
    stream_id = 'Match:'+stream_id.split(':')[-1]
    stream_id = base64.b64encode(stream_id.encode()).decode()
    uri = 'https://quarterback.znipe.tv/graphql?variables={%22id%22:%22'+stream_id+'%22,%22isVideo%22:false,%22isClip%22:false,%22withChannel%22:true}&extensions={%22persistedQuery%22:{%22version%22:1,%22sha256Hash%22:%2232147515%22}}'
    vod_data = requests.get(uri, headers=HEADERS).json()
    return vod_data['data']['match']

def get_m3u8_uris(stream_id:str):
    vod_data = get_vod_data(stream_id)
    ngames = len([1 for x in vod_data['games'] if x['status']=='vod'])

    all_streams = []
    url = 'https://quarterback.znipe.tv/v4/auth/tokens/akamai/streams'
    for idx in range(1, ngames+1):
        data = {
            "matches": [{"id": vod_data['id'], "gameNumber": idx}],
            "videos": [],
            "clips": []
        }
        stream_info = requests.post(url, headers=HEADERS, json=data).json()
        streams = stream_info['results']['matches'][0]['tokens']
        all_streams.append(streams)

    streamid2uri = {}
    for matchidx, streams in enumerate(all_streams):
        for stream in streams:
            streamid = stream['streamId']
            hls = stream['hls']
            streamid2uri[streamid] = hls

    teamsinfo = vod_data['teams']
    playerid2name = {}
    for team in teamsinfo:
        for player in team['players']:
            playerid2name[player['id']] = player['name']

    gamesinfo = vod_data['games']
    name2uri = {}
    for game in gamesinfo[:ngames]:
        for gstream in game['globalStreams']:
            streamid = gstream['streamId']
            uri = streamid2uri[streamid]
            name = gstream['name']
            uris = name2uri.get(name, [])
            uris.append(uri)
            name2uri[name] = uris
        for team in game['competitors']:
            for player in team['lineup']:
                streamid = player['streamId']
                uri = streamid2uri[streamid]
                playerid = player['playerId']
                name = playerid2name[playerid]
                pipeid = player['streamPipelineId']
                if len(pipeid) == 2:
                    pipeid = pipeid[0] + '0' + pipeid[1]
                name = f'{pipeid} {name}'
                uris = name2uri.get(name, [])
                uris.append(uri)
                name2uri[name] = uris

    return name2uri

def get_m3u8_file_v2(uris, output_file):
    combined_m3u8 = m3u8.M3U8()
    for idx, hls in enumerate(uris):
        mid_uri = hls.split('acl=/')[1].split('.m3u8')[0]
        parms_uri = quote(hls.split('hdnts=')[1], safe='')
        full_uri = f'https://media-vod-fa.znipe.tv/{mid_uri}.m3u8?hdnts={parms_uri}'
        # full_uri = f'https://media-live-fa-2.znipe.tv/{mid_uri}.m3u8?hdnts={parms_uri}'
        m3u8_obj = m3u8.load(full_uri, headers=HEADERS)
        best_uri = sorted(m3u8_obj.playlists, key=lambda x: x.stream_info.bandwidth)[-1].absolute_uri
        best_uri = best_uri + '?' + full_uri.split('?')[1]
        best_m3u8 = m3u8.load(best_uri, headers=HEADERS)
        for seg in best_m3u8.segments:
            seg.uri = seg.absolute_uri + '?' + full_uri.split('?')[1]
            combined_m3u8.segments.append(seg)
    combined_m3u8.dump(output_file)
    print(f'{output_file} done')
    return output_file

def download_one(stream_id, team, video_file):
    for _ in range(5):
        try:
            # uris = get_m3u8_uris(stream_id)[team]
            # output_file = video_file.replace('.ts', '.m3u8')
            # if exists(video_file):
            #     return
            # if datetime.now().timestamp() > T0.timestamp():
            #     return
            # get_m3u8_file_v2(uris, output_file)
            # download_m3u8(output_file, video_file, HEADERS, max_workers=max_workers)
            download_m3u8_v2(stream_id, team, video_file, HEADERS, max_workers=max_workers)
            return video_file
        except Exception as e:
            print(e)
            continue

class DownUpPool:
    def __init__(self, ndown, nup):
        self.down_pool = ThreadPoolExecutor(ndown)
        self.up_pool = ThreadPoolExecutor(nup)
        self.tasks = []

    def add(self, 
        down_func, down_args,
        up_func, up_args
    ):
        task = self.down_pool.submit(down_func, *down_args)
        def func(task):
            task.result()
            self.up_pool.submit(up_func, *up_args)
        task.add_done_callback(func)
        self.tasks.append(task)
        return task
    
    def wait(self):
        wait(self.tasks)
        self.down_pool.shutdown()
        self.up_pool.shutdown()


if __name__ == '__main__':
    MATCH2BVID = {
        '6809f1b6c8b5b82070b8811a': 'BV1pcVNzNEgr',
        # '6809f1b5c8b5b82070b88119': 'BV1wcVNzNEyp',

        # '6809f1b8d3bf442fc8734a40': 'BV1AfVPziEnE',
        # '6809f1bac8b5b82070b8811b': 'BV1pfVPziEQG',

        # '6809f1bbc8b5b82070b8811c': 'BV1RLVNz9E6h',
    }
    OUTPUTDIR = 'faceit-vods'
    T0 = datetime(2026, 2, 20, 9, 30)
    max_workers = 10

    
    from append_video import upload_one
    dpool = DownUpPool(3, 1)

    for matchid, bvid in MATCH2BVID.items():
        # matchid = '671a678515b3808df3dad4b1'
        # BVID = 'BV1LRFHe1EBf'
        meta_data = get_match_metadata(matchid)
        ngames = len(meta_data['maps'])
        stream_id = meta_data.get('streamId') or meta_data.get('stream_id')
        if meta_data['tournament'].get('stage'):
            fullname = f"{meta_data['tournament']['name']}-{meta_data['tournament']['stage']}-{meta_data['title']}-{matchid}"
        else:
            fullname = f"{meta_data['tournament']['name']}-{meta_data['title']}-{matchid}"
        output_dir = join(OUTPUTDIR, fullname)
        os.makedirs(output_dir, exist_ok=True)

        team_uris = get_m3u8_uris(stream_id)
        teams = list(team_uris.keys())
        teams = teams[6:]
        print(teams)
        time.sleep(5)
        for team in teams:
            if 'Audio' in team:
                continue
            if 'Event Stream' in team:
                output_file = join(output_dir, f'主视角 {team}.m3u8')
            elif 'Map Stream' in team:
                output_file = join(output_dir, f'地图 {team}.m3u8')
            else:
                output_file = join(output_dir, f'{team}.m3u8')
            video_file = output_file.replace('.m3u8', '.ts')
            # download_one(stream_id, team, video_file)
            dpool.add(
                download_one, (stream_id, team, video_file),
                upload_one, (video_file, bvid, 3, True)
            )
            time.sleep(60)
            
    dpool.wait()
