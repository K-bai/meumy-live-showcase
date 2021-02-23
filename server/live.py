from bilibili_api import live
from Msg_db import Msg_db
import asyncio
import json
import time

rooms_id = [22384516,8792912]
ALL_CMD = [
    'DANMU_MSG',
    'SEND_GIFT',
    'USER_TOAST_MSG',
    'SUPER_CHAT_MESSAGE',
    'VIEW'
]

async def listen_room(room):
    '''
    检测一个房间是否在直播
    输出数据信息
    30秒检测一次
    '''
    while True:
        status = (live.get_room_play_info(room['id'])['live_status'] == 1)
        if status == True and room['status'] == False:
            # 开始直播
            room['status'] = True
            room['db'].live_action(int(time.time()*1000), 'start')
            print('[{:d}][{:s}] 直播已开始.'.format(room['id'], time.strftime("%Y-%m-%d %H:%M:%S")))
        elif status == False and room['status'] == True:
            # 结束直播
            room['status'] = False
            room['db'].live_action(int(time.time()*1000), 'end')
            print('[{:d}][{:s}] 直播已结束.'.format(room['id'], time.strftime("%Y-%m-%d %H:%M:%S")))
        # 长时间未增加新信息则保存
        room['commit_timer'] += 1
        if room['commit_timer']>2 and room['msgs'] != None:
            room['db'].commit_msgs(room['msgs'])
            room['commit_timer'] = 0
            c = len(room['msgs'])
            room['msgs'] = None
            print('[{:d}][{:s}] 超时，自动提交{:d}条信息.'.format(room['id'], time.strftime("%Y-%m-%d %H:%M:%S"), c))
        print('[{:d}][{:s}] 已记录{:d}条信息.'.format(room['id'], time.strftime("%Y-%m-%d %H:%M:%S"), room['msg_n']))
        await asyncio.sleep(30)

async def connect_all_rooms(rooms):
    '''
    连接所有直播间
    '''
    tasks = []
    for room in rooms:
        tasks.append(asyncio.create_task(room['obj'].connect(True)))
        tasks.append(asyncio.create_task(listen_room(room)))
    await asyncio.gather(*tasks)

def append_msg(room, msg):
    '''
    将获取到的信息存入列表
    若超过10条则写入数据库
    '''
    if room['msgs'] == None:
        room['msgs'] = []
    # 是否在需要保存的列表里
    if msg['type'] in ALL_CMD:
        # VIEW类别需要加时间戳
        room['msgs'].append(msg)
        if msg['type'] == 'VIEW':
            room['msgs'][-1]['timestamp'] = int(time.time()*1000)
        room['msg_n'] += 1
    if len(room['msgs'])>=10:
        room['db'].commit_msgs(room['msgs'])
        room['commit_timer'] = 0
        room['msgs'] = None



# 实例化直播间websocket
rooms = []
for room_id in rooms_id:
    rooms.append({
        'id':room_id,
        'status': False,
        'msgs': None,
        'msg_n': 0,
        'commit_timer': 0,
        'obj': live.LiveDanmaku(room_display_id=room_id,debug=False),
        'db': Msg_db(str(room_id))
    })


# 定义handler
room = rooms[0]['obj']
@room.on("ALL")
async def on_all0(msg):
    append_msg(rooms[0], msg)

room = rooms[1]['obj']
@room.on("ALL")
async def on_all1(msg):
    append_msg(rooms[1], msg)

if __name__ == "__main__":
    asyncio.run(connect_all_rooms(rooms))