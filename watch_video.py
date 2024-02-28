import re
import time
import sys
import json
import os
import random
import requests
import logging
import threading
from logging import handlers
from concurrent.futures import ProcessPoolExecutor, wait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import sys

sys.path.append('.')

class Watcher():
    def __init__(self, url, cookies=None, windows=3, **kwargs) -> None:
        self.url = url
        self.cookies = cookies
        self.windows = windows
        self.kwargs = kwargs
        self.stoped = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
        }
    
    def start(self):
        opt = webdriver.EdgeOptions()
        opt.add_argument('--headless')
        opt.add_argument('--mute-audio')
        opt.add_argument('--incognito')
        # opt.add_argument('--disable-gpu')

        self.driver = webdriver.Edge(options=opt)
        self.driver.set_window_size(1280, 720)
        self.driver.execute_script(r"Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver.get(self.url)
        if self.cookies:
            for c in self.cookies:
                self.driver.add_cookie(c)
        
        time_cnt = 1
        while not self.stoped: 
            logging.info(f'Watch {self.url} {time_cnt} times.')
            self.start_once()
            time_cnt += 1
            if not self.cookies:
                self.driver.delete_all_cookies()

    def start_once(self):
        try:
            bvid = re.search(r'(BV.*?).{10}', self.url)[0]
            resp = requests.get(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}', headers=self.headers).json()
            duration = float(resp['data']['duration'])
            watch_time = random.randint(int(duration*0.75), int(duration))
            views = int(resp['data']['stat']['view'])
            logging.info('Remote views: %s', views)
        except Exception as e:
            logging.exception(e)
            watch_time = 60
        
        try:
            self.driver.get(self.url)
            element = self.driver.find_element(By.ID, 'bilibili-player')
            # ActionChains(self.driver).move_to_element(element).click().perform()

            time.sleep(65)
            try:
                ActionChains(self.driver).\
                    move_to_element(self.driver.find_element(By.CLASS_NAME, 'bili-mini-close-icon'))\
                    .click().perform()
                time.sleep(1)
                ActionChains(self.driver)\
                    .move_to_element(self.driver.find_element(By.ID, 'bilibili-player'))\
                    .click().perform()
                time.sleep(1)
                self.driver.save_screenshot(f'logs/snapshot-{bvid}-1.png')
            except Exception as e:
                logging.error(e)
            
            time.sleep(max(watch_time-70,0))
            self.driver.save_screenshot(f'logs/snapshot-{bvid}-2.png')
        except Exception as e:
            logging.exception(e)
            self.driver.save_screenshot(f'logs/error-{bvid}.png')
            time.sleep(10)

    def stop(self):
        self.stoped = True
        self.driver.quit()

class Watch_Bili():
    def __init__(self, cookies='login_info/bili-main.json'):
        with open(cookies, encoding='utf8') as f:
            self.cookies = json.load(f)

        # opt = webdriver.EdgeOptions()
        # opt.add_argument('--headless')
        # opt.add_argument('--disable-gpu')

        # driver = webdriver.Edge(options=opt)
        
        # driver.get('https://www.bilibili.com')
        # for c in self.cookies:
        #     driver.add_cookie(c)
        # driver.refresh()
        # self.cookies = driver.get_cookies()

        # with open('cookies-bilimain.json', 'w', encoding='utf8') as f:
        #     json.dump(self.cookies, f)

        # self.pool = ProcessPoolExecutor(max_workers=5)
        self.tasks = {}

    def add(self, url, use_cookies=False):
        watcher = Watcher(url, self.cookies if use_cookies else None)
        threading.Thread(target=watcher.start, daemon=True).start()
        self.tasks[url] = watcher

    def delete(self, url):
        if url in self.tasks:
            self.tasks[url].stop()
            del self.tasks[url]
            return True
        return False

    def wait(self):
        pass

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) 
    console_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s"))
    
    os.makedirs('logs',exist_ok=True)
    logname = f'logs/bilicheat-watch.log'
    file_handler = handlers.TimedRotatingFileHandler(logname, when='D', interval=1, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s"))
    
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)

    afk = Watch_Bili()
    URL_LIST = []
    while 1:
        with open('WATCH_VIDEO.txt', 'r', encoding='utf8') as f:
            string = f.read().strip()
            urls = [uri for uri in string.split('\n') if uri.startswith('http')]

        need_add = set(urls) - set(URL_LIST)
        for url in need_add:
            logging.info(f'Add {url}.')
            afk.add(url)
            URL_LIST.append(url)

        need_delete = set(URL_LIST) - set(urls)
        for url in need_delete:
            logging.info(f'Delete {url}.')
            afk.delete(url)
            URL_LIST.pop(URL_LIST.index(url))
        
        time.sleep(60)
    