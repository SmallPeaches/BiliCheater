import subprocess


def split_video(video:str, excepts, output=None):
    ss = '00:00:00'
    for i, (s, e) in enumerate(excepts):
        output = VIDEO.split('.')[0] + f'{i+1}.mp4'
        cmds = ['ffmpeg', '-i', video, '-ss', ss, '-to', s, '-c', 'copy', output]
        print(cmds)
        subprocess.Popen(cmds).wait()
        ss = e
    output = VIDEO.split('.')[0] + f'{len(excepts)+1}.mp4'
    cmds = ['ffmpeg', '-i', video, '-ss', ss, '-c', 'copy', output]
    print(cmds)
    subprocess.Popen(cmds).wait()


if __name__ == '__main__':
    VIDEO = r"D:\Download\Code\DanmakuRender-5\直播回放（弹幕版）\（弹幕版）一口三明治3Mz-2024年12月29日20点32分.mp4"
    EXCEPTS = [
        ('12:48', '12:52'),
        ('20:56', '21:21')
    ]

    split_video(VIDEO, EXCEPTS)

