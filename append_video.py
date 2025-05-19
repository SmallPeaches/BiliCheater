import os
import subprocess
import json
import time
from datetime import datetime
from os.path import *

from upload_video import append

def upload_one(file, bvid, retry=3, auto_clean=False, **kwargs):
    for _ in range(retry):
        try:
            ret = append(file, bvid, **kwargs)
            if ret == 0:
                if auto_clean:
                    os.remove(file)
                return ret
        except Exception as e:
            print(e)
            continue
    open(file+'ERROR', 'w').close()


if __name__ == '__main__':
    VIDEO = 'output'
    BVID = 'BV1xKJTzcEbC'
    if isinstance(VIDEO, str):
        if os.path.isfile(VIDEO):
            VIDEO = [VIDEO]
        elif os.path.isdir(VIDEO):
            VIDEO = [os.path.join(VIDEO, x) for x in os.listdir(VIDEO)]
            VIDEO = sorted(VIDEO)
        else:
            raise ValueError('Invalid video path.')

    for idx, vid in enumerate(VIDEO.copy()):
        vname = splitext(basename(vid))[0]
        if len(vname) > 80:
            new_name = vname[:80]
            new_vid = vid.replace(vname, new_name)
            print(f'Rename {vid} -> {new_vid}')
            os.rename(vid, new_vid)
            VIDEO[idx] = new_vid

    print(VIDEO)

    # ret = upload_one(VIDEO, BVID, extra_args=['--line', 'txa'])
    # if ret != 0:
    #     open(VIDEO[0]+'ERROR', 'w').close()
    # exit(0)


    for video in VIDEO:
        ret = upload_one(video, BVID, extra_args=['--line', 'txa'])
        if ret != 0:
            open(video+'ERROR', 'w').close()