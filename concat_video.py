import os
import subprocess
from os.path import *

def concat_video(video_dir, output):
    dir_list = os.listdir(video_dir)
    video_list = []
    for f in dir_list:
        if splitext(f)[1] in ['.mp4', '.flv', '.mkv', '.ts']:
            video_list.append(f'file \'{os.path.join(video_dir, f)}\'\n')
    video_list.sort()
    print(video_list)
    
    list_file = join(video_dir, 'list.txt')
    with open(list_file,'w',encoding='utf-8') as f:
        f.writelines(video_list)
    subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output]).wait()


if __name__ == '__main__':
    video_dir = r"D:\FileServer"
    output = 'output/1026dm.mp4'
    concat_video(video_dir, output)