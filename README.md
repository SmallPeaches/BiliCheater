# BiliCheater
个人常用的鼠鼠爬虫脚本，用vscode启动特别方便😋😋        

### 登录
所有的登录信息都使用biliup-rs格式的json文件。       

### 下载B站视频
**bilidown.py**       
实际上就是封装了yutto，不用填session-id。     

### 看直播
**bilicheat.py**
自动看直播，给主播点赞，发弹幕，拿来挂粉丝牌。      
需要一个txt文件，每一行代表一个直播间号。

### 看视频
**watch_video.py和watch_video_new.py**
一个是调用selenium，一个是直接访问api，现在已经没啥用了。

### 上传视频
**append_video.py和upload_video.py**        
实际上就是封装了biliup-rs，增加了重试功能和函数调用功能。       
需要一个这样的配置文件：

<details>
<summary>点击展开</summary>     

```yaml
# 视频目录或者路径
videos: videos

# 附加BVID
# 有就是追加，没有就是传新的
# 追加视频推荐直接 append_video.py
bvid: BVxxxx

# cookies
cookies: login_info/bili-xiaohao.json
# 上传线程数
limit: 10
# 是否为转载视频 1-自制 2-转载
copyright: 2
# 转载来源，转载视频必填
source: https://www.faceit.com/
# 分区号，分区参考 https://biliup.github.io/tid-ref.html
tid: 171
# 封面，指向本地文件地址
cover: ''
# 标题
title: '[APEX] ALGS Open 2025 总决赛 各战队第一视角 2025-05-05'
# 简介
desc: |
  Official Multiview of ALGS 2025: Open
  Grand Finals
# 动态内容
dynamic: ''
# 标签（一定要有！多个标签逗号分割）
tag: 'Apex英雄,ALGS'
# 延迟发布，单位秒，如果需要的话至少设置14400秒（4个小时）
# dtime: 172000
# 允许转载? 0-允许转载，1-禁止转载
no_reprint: 1
# 是否开启充电? 0-关闭 1-开启
open_elec: 1
```     
</details>

### 下载/上传Faceit的视频
**dl_faceit_vod.py**      
只要设置好常量`MATCH2BVID`就可以了，设置为`<faceit中的matchID>: <需要上传的BVID>`，程序就会自动下载上传了（matchid就是视频URL里面后面的那串代码，例如：`6809f1bed3bf442fc8734a41`）。还可以改`DownUpPool`的输入，设置不同的并行下载上传数。     
Faceit的登录限制是前端限制，后端不登录也可以直接用。上传的视频必须提前存在，不能传新视频！         
下载直播的API类似，但是直播的视频和音频是分离的不方便合并所以不推荐。

### 下载斗鱼的replay
**dl_douyu_replay.py**      
设置需要下载的主播的userID就可以了。      
如果下载单个录像，还要再指定videoID。     

### 合并/分割视频
***concat_video.py和split_video.py**      
可以合并某个文件夹下的所有视频到一个文件。      
分割视频可以将指定的视频内容移除，然后前后分割成多个视频。（有些时候视频有违规ID，这样移除违规时间段很方便）    

### 自动录制TeamStream直播
**auto_rec_teamstream.py**      
通过自动控制DanmakuRender的启动和停止，来自动录制带algs关键字的直播。可以调节一些超参数，来实现提前启动和延迟结束。使用此功能的DanmakuRender必须启用WebAPI。      
特别地，录制ALGS APAC-S时引入了手动设置的直播列表。       
<details>
<summary>展开录播模板示例</summary>     

```yaml
# 本文件一个代表一个录制任务，这里的设置基本上包含了所有可用的参数
# 配置文件编写请参考 https://github.com/SmallPeaches/DanmakuRender 
common_event_args:
  # 启动自动渲染
  auto_render: 0
  # 启动自动上传
  auto_upload: 1
  # 启动自动清理
  auto_clean: 1
  # 原视频自动转码
  auto_transcode: False

# 下载参数
download_args:
  dltype: live
  # 直播间链接
  url: {{URL}}
  # 录制输出文件夹，设置为空则使用主播名称作为文件夹
  output_dir: ./直播回放
  # 录制文件名称格式，可使用关键字替换，默认效果：飞天狙想要努力变胖-2023年3月1日20点30分，注意这里不能含有冒号，斜杠等非法字符！！
  output_name: '{{TASKNAME}}-{CTIME.YEAR}年{CTIME.MONTH:02d}月{CTIME.DAY:02d}日{CTIME.HOUR:02d}点{CTIME.MINUTE:02d}分-{TITLE}'
  # 录播分段时间（秒），默认一个小时
  segment: 28800
  # 录制程序引擎，可选ffmpeg或者streamgears
  # 在使用streamgears作为录制引擎时，录制视频格式可能会根据直播流的不同而不同
  engine: auto
  # 是否录制弹幕
  danmaku: 0
  # 是否录制直播流
  video: True
  # 延迟下播计时（分钟）
  # 使用这个功能可以把主播短暂下播又开播认定为同一场直播
  stop_wait_time: 12
  # 录制视频的格式，默认flv
  output_format: mkv
  
  advanced_video_args: 
    # 开播检测间隔，每隔这段时间检测一次是否开播
    start_check_interval: 60
    # 下播检测间隔，在主播下播但是未超过延迟下播时间时使用
    stop_check_interval: 60
    streamlink_extra_args: [
      "--twitch-disable-ads",     # 去广告，去掉、跳过嵌入的广告流
      "--twitch-disable-reruns",  # 如果该频道正在重放回放，不打开流
      "--twitch-proxy-playlist", "https://twitch.nadeko.net"    # 结合ttv-lol跳过广告
    ]
    group_id: '{{GROUPID}}'

# 上传参数，如果不需要上传就把下面的都删了
upload_args:
  # 原视频
  src_video+dm_video: 
    # 上传账号名称，程序依靠这个来识别不同的账号，如果打算传不同账号就要设置不同的名称
    account: bili-xiaohao
    # 上传cookies路径，如果设置为空将会保存到./login_info/{ACCOUNT}.json
    cookies: ~
    # 重试次数，如果上传遇到错误将会重试，设置为0表示不重试
    # 注意：重试会整个视频重传，并且阻塞后面视频的上传，不应该设置太大
    retry: 3
    # 实时上传（边录边传），每录制一个分段上传一次，同一场直播的不同分P仍然会在一个视频下，默认开启
    realtime: 0
    # 上传的视频最短长度，小于此长度的视频会被自动过滤，默认120s
    min_length: 240
    # 上传线程数
    limit: 20
    # 是否为转载视频 1-自制 2-转载
    copyright: 2
    # 转载来源，转载视频必填
    source: {{EVENT_URL}}
    # 分区号，分区参考 https://biliup.github.io/tid-ref.html
    tid: 171
    # 封面，指向本地文件地址
    cover: ''
    # 标题，可以使用关键字替换
    # 默认的例子：[飞天狙想要努力变胖/直播回放] 晚上七点半比赛 2023年2月24日 （带弹幕版）
    title: '{{TITLE}}'
    # 简介，可以使用关键字替换
    desc: "{{DESC}}"
    # 动态内容，可以使用关键字替换
    dynamic: ''
    # 标签（一定要有！多个标签逗号分割）
    tag: 'Apex英雄,ALGS'

clean_args:
  all:
    # 清理方法，可选copy（复制），move（移动），delete（删除）
    method: delete
    # 目标文件夹，文件夹不存在会自动创建，可以使用关键字替换
    dest: ~
    # 清理延迟（秒）
    delay: 600
    # 清理弹幕视频时同时清理原文件，默认false
    # 请注意，此功能应该只在不上传原文件的情况下使用，否则会导致上传失败
    w_srcfile: False
    # 清理源文件时同时清理转码前文件（如果有的话），默认true
    w_srcpre: True
```     
</details>