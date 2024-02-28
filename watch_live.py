import time
import sys
import json
import os
import http.cookiejar as cookielib
import requests
import logging
import threading
from logging import handlers
from concurrent.futures import ProcessPoolExecutor, wait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from liveapi import bilibili, split_url

sys.path.append('.')

class Watcher():
    def __init__(self, url, cookies, **kwargs) -> None:
        self.url = url
        self.cookies = cookies
        self.kwargs = kwargs
        self.stoped = False
        self.liveapi = bilibili(split_url(self.url)[1])

    def start(self):
        opt = webdriver.EdgeOptions()
        opt.add_argument('--headless')
        opt.add_argument('--mute-audio')
        # opt.add_argument('--disable-gpu')

        self.driver = webdriver.Edge(options=opt)
        self.driver.set_window_size(1280, 720)
        self.driver.execute_script(r"Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        # 发送请求
        self.driver.get(self.url)
        for c in self.cookies:
            self.driver.add_cookie(c)
        self.driver.get(self.url)
        
        logging.info(f'Watching {self.url}')
        roomid = split_url(self.url)[1]
        self.driver.save_screenshot(f'logs/snapshot-{roomid}.png')

        time_cnt = 0
        old_status = self.liveapi.onair()
        time.sleep(60)
        while not self.stoped:
            try:
                new_status = self.liveapi.onair()
                if old_status != new_status:
                    logging.info(f'Live status: {new_status}, refresh.')
                    self.driver.refresh()
                    old_status = new_status
                elif time_cnt % 3 == 0:
                    ActionChains(self.driver)\
                        .move_by_offset(100, 100)\
                        .move_by_offset(-100, -100)\
                        .perform()
                    # self.driver.execute_script('window.scrollBy(0, -100)')
                    self.driver.save_screenshot(f'logs/snapshot-{roomid}.png')
            except Exception as e:
                self.driver.save_screenshot(f'logs/exception-{roomid}.png')
                logging.exception(e)
            time.sleep(60)

    def stop(self):
        self.stoped = True
        self.driver.close()

class Watch_Bili():
    def __init__(self, cookies='login_info/bili-main.json'):
        with open(cookies, encoding='utf8') as f:
            self.cookies = json.load(f)

        # opt = webdriver.EdgeOptions()
        # opt.add_argument('--headless')
        # opt.add_argument('--disable-gpu')

        # driver = webdriver.Edge(options=opt)
        
        # driver.get('https://live.bilibili.com')
        # for c in self.cookies:
        #     driver.add_cookie(c)
        # driver.refresh()
        # self.cookies = driver.get_cookies()

        # with open('cookies.json', 'w', encoding='utf8') as f:
        #     json.dump(self.cookies, f)

        # self.pool = ProcessPoolExecutor(max_workers=5)
        self.tasks = {}

    def add(self, url):
        watcher = Watcher(url, self.cookies)
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
    logname = f'logs/bilicheat-live.log'
    file_handler = handlers.TimedRotatingFileHandler(logname, when='D', interval=1, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s"))
    
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)

    afk = Watch_Bili()
    URL_LIST = []
    while 1:
        with open('WATCH_LIVE.txt', 'r', encoding='utf8') as f:
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
    