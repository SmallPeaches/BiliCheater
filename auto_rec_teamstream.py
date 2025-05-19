import os
import re
import requests
import time
import json
import threading
import logging

from glob import glob
from os.path import *
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)


url = "https://teamstream.gg/api/graphql"
headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Microsoft Edge\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


class AutoRecTeamStream:
    APACS_INFO = 'teams/APACS-{idx}.json'
    TEMPLATE = 'teams/teamstream-template.yml'
    OUTPUT = '/root/DMR-A/configs'

    def __init__(self):
        self.replays = {}
        self.end_events = {}
        self.end_players = {}
        
        self.START_INTERVAL = START_INTERVAL
        self.END_INTERVAL = END_INTERVAL
        self.REMOVE_INTERVAL = REMOVE_INTERVAL

    def _get_events(self, event_type):
        body = {
            "operationName": "EventsQuery",
            "variables": {
                "input": {
                    "type": event_type,
                    "sort": "START_DATE"
                }
            },
            "query": "query EventsQuery($input: EventsInput) {\n  events(input: $input) {\n    id\n    code\n    name\n    region\n    startDate\n    endDate\n    series {\n      id\n      code\n      __typename\n    }\n    logoUrl\n    __typename\n  }\n}"
        }
        resp = requests.post(url, headers=headers, json=body, timeout=5)
        return resp.json()['data']['events']

    def _get_event_info(self, event_code):
        event_query = {
            "operationName": "FindMultiviewEventQuery",
            "variables": {
                "eventCode": event_code
            },
            "query": "query FindMultiviewEventQuery($eventCode: String!) {\n  event: event(code: $eventCode) {\n    id\n    name\n    logoUrl\n    battlefyScoresUrl\n    startDate\n    region\n    organizer {\n      name\n      __typename\n    }\n    channel {\n      userId\n      isLive\n      displayName\n      loginName\n      profileImageUrl\n      __typename\n    }\n    teams {\n      id\n      name\n      logoUrl\n      players {\n        id\n        name\n        logoUrl\n        channel {\n          userId\n          isLive\n          displayName\n          loginName\n          profileImageUrl\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
        }
        resp = requests.post(url, headers=headers, json=event_query, timeout=5)
        return resp.json()['data']['event']

    def get_event_streams(self, event_code):
        event_info = self._get_event_info(event_code)
        event_name = event_info['name']
        teams = event_info['teams']
        region = event_info['region']

        replays = []

        for team in teams:
            team_name = team['name']
            if 'Watch Party' in team_name:
                team_name = '(解说团)'
            players = team['players']
            for player in players:
                if not player['channel']:
                    continue
                player_name = player['channel']['loginName']
                channel = f'https://www.twitch.tv/{player_name}'
                output = join(self.OUTPUT, f'DMR-{event_name}-{team_name}-{player_name}.yml')

                replays.append({
                    'player': player_name,
                    'uri': channel,
                    'team': team_name,
                    'event': event_name,
                    # 'start': event_start,
                    # 'end': event_end,
                })
        
        if event_channel := event_info['channel']:
            channel_name = event_channel['loginName']
            channel = f'https://www.twitch.tv/{channel_name}'
            output = join(self.OUTPUT, f'DMR-{event_name}-{team_name}-{channel_name}.yml')
            team_name = '(主机位)'

            replays.append({
                'player': channel_name,
                'uri': channel,
                'team': team_name,
                'event': event_name,
                # 'start': event_start,
                # 'end': event_end,
            })

        return replays

    def get_apacs_streams(self, group_id):
        player_info = json.load(open(self.APACS_INFO.format(idx=group_id), 'r'))
        replays = []
        for team, item in player_info.items():
            for name, uri in item.items():
                if not uri: continue
                replays.append({
                    'player': name,
                    'uri': uri,
                    'team': team,
                    'event': f'APACS-{group_id}',
                    'start': None,
                    'end':  None,
                })
        
        return replays

    def clean_replays(self):
        for conf, replay in list(self.replays.items()):
            end = replay['end']
            taskname = os.path.splitext(os.path.basename(conf))[0].split('-', 1)[-1]
            now = datetime.now().astimezone(tz=None)
            
            if self.replays[conf]['status'] == 'start'\
                and now - end > timedelta(minutes=self.END_INTERVAL):
                data = {
                    'source': 'web',
                    'target': 'downloader',
                    'event': 'stoptask',
                    'data': taskname,
                }
                resp = requests.post('http://127.0.0.1:5000/api/put_message', json={'data': data}, timeout=5)
                logging.info(f'{conf} stoped: {resp.status_code}')
                self.replays[conf]['status'] = 'end'
            
            if self.replays[conf]['status'] == 'end'\
                and now - end > timedelta(minutes=self.END_INTERVAL+self.REMOVE_INTERVAL):
                if exists(conf):
                    os.remove(conf)
                logging.info(f'{conf} removed')
                self.replays.pop(conf)

    def start_once(self):
        template = open(self.TEMPLATE, encoding='utf8').read()
        if not exists(self.OUTPUT):
            os.makedirs(self.OUTPUT)
            
        all_events = self._get_events('current') + self._get_events('upcoming')
        for event in all_events:
            event_code = event['code']
            event_start = datetime.fromisoformat(event['startDate'].replace("Z", "+00:00")).astimezone(tz=None)
            event_end = datetime.fromisoformat(event['endDate'].replace("Z", "+00:00")).astimezone(tz=None)
            now = datetime.now().astimezone(tz=None)
            if event_start - now > timedelta(minutes=self.START_INTERVAL):
                continue

            event_info = self._get_event_info(event_code)
            event_name = event_info['name']

            if not any(k in event_name.lower() for k in ['algs', 'emea', 'scrim', 'apac']):
                continue

            # hash = sum(ord(ch) for ch in event_name)
            # if hash % 2 == 1:
            #     continue

            if 'Open scrim Lobby' in event_name:
                now = datetime.now(timezone.utc)
                group_id = 'ALGS Open Scrims' + str(now.day)
                event_name = 'ALGS Open Scrims Part-2'
            else:
                group_id = event_name + r'{CTIME.DAY:02d}'

            streams = []
            if 'APAC-South' in event_name:
                group = re.findall(r'[A-C]v[A-C]', event_name)
                if group:
                    group = group[0]
                    g1 = group[0]
                    g2 = group[-1]
                    streams = self.get_apacs_streams(g1) + self.get_apacs_streams(g2)
            else:
                streams = self.get_event_streams(event_code)

            if len(streams) < 10:
                continue
            
            if 'ALGS' in event_name and 'scrim' not in event_name.lower():
                title = f'[APEX/ALGS] {event_name} ' + r'{CTIME.YEAR}-{CTIME.MONTH:02d}-{CTIME.DAY:02d}'
                desc = f'来自TeamStream的 {event_name} 多视角回放\\n\\n' + \
                    f'{event_start.isoformat()}'
            else:
                title = f'[APEX/ALGS训练赛] {event_name} ' + r'{CTIME.YEAR}-{CTIME.MONTH:02d}-{CTIME.DAY:02d}'
                desc = f'来自TeamStream的 {event_name} 训练赛多视角回放\\n\\n' + \
                    f'{event_start.isoformat()}'

            for stream in streams:
                player_name = stream['player']
                uri = stream['uri']
                team_name = stream['team']
                event_name = stream['event']
                output = join(self.OUTPUT, f'DMR-{event_name}-{team_name}-{player_name}.yml')

                if exists(output):
                    continue
                
                config = template.replace('{{URL}}', uri)\
                        .replace('{{TITLE}}', title)\
                        .replace('{{DESC}}', desc)\
                        .replace('{{TASKNAME}}', team_name+'-'+player_name)\
                        .replace('{{GROUPID}}', group_id)\
                        .replace('{{EVENT_URL}}', f'https://teamstream.gg/events/{event_code}')
                
                logging.info(f"Replay {output} is starting!")
                open(output, 'w', encoding='utf8').write(config)
                self.replays[output] = {
                    'start': event_start,
                    'end': event_end,
                    'status': 'start',
                    'stream': stream,
                }

        self.clean_replays()

    def run(self):
        while True:
            try:
                os.system('du -sh /root/DMR-A')
                self.start_once()
            except Exception as e:
                logging.exception(e)
            time.sleep(60)

if __name__ == '__main__':
    START_INTERVAL = 30
    END_INTERVAL = 60
    REMOVE_INTERVAL = 60
    auto_rec = AutoRecTeamStream()
    auto_rec.run()
