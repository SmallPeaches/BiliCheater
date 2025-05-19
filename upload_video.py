import os
import subprocess
import time
import yaml

def append(video, bvid, timeout=None, extra_args=None):
    upload_args = BASE_ARGS + ['append', '--vid', bvid, '--limit', '20']
    if extra_args:  upload_args += extra_args
    if isinstance(video, str):
        upload_args += [video]
    elif isinstance(video, list):
        upload_args += video
    print(f'biliuprs: {upload_args}')
    if timeout:
        return subprocess.Popen(upload_args).wait(timeout=timeout)
    else:
        return subprocess.Popen(upload_args).wait()

def upload(
        video:str,
        copyright:int=1,
        cover:str='',
        desc:str='',
        dolby:int=0,
        dtime:int=0,
        dynamic:str='',
        interactive:int=0,
        limit:int=3,
        no_reprint:int=1,
        open_elec:int=1,
        source:str='',
        tag:str='',
        tid:int=65,
        title:str='',
        **kwargs
    ):
        upload_args = BASE_ARGS + ['upload']
        dtime = dtime + int(time.time()) if dtime else 0
        if isinstance(tag, list):
            tag = ','.join(tag)
        upload_args += [
            '--copyright', copyright,
            '--cover', cover,
            '--desc', desc,
            '--dolby', dolby,
            '--dtime', dtime,
            '--dynamic', dynamic,
            '--interactive', interactive,
            '--limit', limit,
            '--no-reprint', no_reprint,
            '--open-elec', open_elec,
            '--source', source,
            '--tag', tag,
            '--tid', tid,
            '--title', title,
        ]
        if isinstance(video, str):
            upload_args += [video]
        elif isinstance(video, list):
            upload_args += video

        upload_args = [str(x) for x in upload_args]
        print(f'biliuprs: {upload_args}')

        return subprocess.Popen(upload_args).wait()

with open(os.path.join(os.path.split(__file__)[0],'UPLOAD_VIDEO.yml'),'r',encoding='utf-8') as f:
    config = yaml.safe_load(f)
    if config.get('cookies'):   
        COOKIES = config['cookies']

BASE_ARGS = ['login_info/biliup.exe', '-u', COOKIES]

if __name__ == '__main__':
    VIDEO = config['videos']
    if isinstance(VIDEO, str):
        if os.path.isfile(VIDEO):
            VIDEO = [VIDEO]
        elif os.path.isdir(VIDEO):
            VIDEO = [os.path.join(VIDEO, x) for x in os.listdir(VIDEO)]
            VIDEO = sorted(VIDEO)
        else:
            raise ValueError('Invalid video path.')
    VIDEO = [x for x in VIDEO if x]

    if len(VIDEO) > 0:
        bvid = config.get('bvid')
        if bvid:
            for video in VIDEO:
                try:
                    ret_msg = append(video, bvid)
                except Exception as e:
                    print(e)
                    ret_msg = 1
            # ret_msg = append(VIDEO, bvid)
        else:
            ret_msg = upload(video=VIDEO, **config)

    exit(ret_msg)