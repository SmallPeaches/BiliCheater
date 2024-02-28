import subprocess
import time
import yaml

def append(video, bvid):
    upload_args = BASE_ARGS + ['append', '--vid', bvid, '--limit', '5']
    if isinstance(video, str):
        upload_args += [video]
    elif isinstance(video, list):
        upload_args += video
    print(f'biliuprs: {upload_args}')
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
        line:str='kodo',
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
            '--line', line,
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

if __name__ == '__main__':
    COOKIES = ''
    with open('UPLOAD_VIDEO.yml','r',encoding='utf-8') as f:
        config = yaml.safe_load(f)
        if config.get('cookies'):   
            COOKIES = config['cookies']
    BASE_ARGS = ['login_info/biliup.exe', '-u', COOKIES]
    VIDEO = config['videos']
    if isinstance(VIDEO, str):
        VIDEO = [VIDEO]
    VIDEO = [x for x in VIDEO if x]
    if len(VIDEO) > 0:
        bvid = config.get('bvid')
        if bvid:
            ret_msg = append(VIDEO, bvid)
        else:
            ret_msg = upload(video=VIDEO, **config)

    # VIDEO = r"D:\Videos\Kovaaks\2024.02.15.mp4"

    # ret_msg = upload(video=VIDEO, **config)   #custom
    # ret_msg = append(VIDEO, 'BV1HK421y7WY')   # kvk
    # ret_msg = append(VIDEO, 'BV152421F72E')   # firing range

    exit(ret_msg)