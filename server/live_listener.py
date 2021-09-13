from bilibili_api import live
from db_utils.MsgDb import MsgDb
import asyncio, aiofiles
import json
import os, sys, time

ALL_CMD = [
    'DANMU_MSG',
    'SEND_GIFT',
    'USER_TOAST_MSG',
    'SUPER_CHAT_MESSAGE',
    'VIEW'
]


#ROOM_ID = [1569975]
ROOM_ID = [22384516, 8792912]


MSG_BATCH_NUM = 50
MSG_BATCH_NUM_JSON = 500
JSON_MSG_DIR = 'raw/'
JSON_MSG_DAYS = 10

class Room:
    def __init__(self, room_id):
        # 数据库和获取弹幕库
        self.id = room_id
        self.live_danmuku = live.LiveDanmaku(room_display_id=self.id, max_retry=99, retry_after=2, debug=False)
        self.live_room = live.LiveRoom(room_display_id=self.id)
        self.db = MsgDb(str(self.id))
        # 状态和临时数据
        self.status = False
        self.msgs_to_db = []
        self.msgs_to_raw = []
        self.msgs_saved = 0
        self.commit_counter = 0
        # 注册handler
        self.live_danmuku.add_event_listener("ALL", self.append_msg)

    async def listen(self):
        '''
        检测一个房间是否在直播
        输出数据信息
        45秒检测一次
        '''
        while True:
            # 获取直播间直播状态
            try:
                status = await self.live_room.get_room_play_info()
                status = status['live_status'] == 1
            except Exception as err:
                print('[{:d}][{:s}][ERROR] 获取直播状态时出现问题：{}'.format(self.id, time.strftime("%Y-%m-%d %H:%M:%S"), err))
                status = self.status
            # 修改直播状态
            if status == True and self.status == False:
                self.status = True
                self.db.live_action(int(time.time()*1000), 'start')
                print('[{:d}][{:s}] 直播已开始.'.format(self.id, time.strftime("%Y-%m-%d %H:%M:%S")))
            elif status == False and self.status == True:
                # 结束直播
                self.status = False
                self.db.live_action(int(time.time()*1000), 'end')
                print('[{:d}][{:s}] 直播已结束.'.format(self.id, time.strftime("%Y-%m-%d %H:%M:%S")))
            # 超时提交信息
            self.commit_counter += 1
            if self.commit_counter >= 2:
                self.save_db_msgs()
            print('[{:d}][{:s}] 共已接收{:d}条信息 {:d}条信息尚未提交数据库'.format(self.id, time.strftime("%Y-%m-%d %H:%M:%S"), self.msgs_saved, len(self.msgs_to_db)))
            await asyncio.sleep(45)
    
    async def close_save_all(self):
        await self.live_danmuku.disconnect()
        self.save_db_msgs()
        await self.save_json_msgs()
        print('[{:d}][{:s}] 已保存数据并关闭连接.'.format(self.id, time.strftime("%Y-%m-%d %H:%M:%S")))

    
    async def append_msg(self, msg):
        '''
        将获取到的信息存入列表
        若超过50条则写入数据库
        超过500条就写入json文本
        '''
        # 保存至数据库
        # 是否在需要保存的列表里
        if msg['type'].find('DANMU_MSG') > -1:
            msg['type'] = 'DANMU_MSG'
        if msg['type'] in ALL_CMD:
            # VIEW类别需要加时间戳
            self.msgs_to_db.append(msg)
            if msg['type'] == 'VIEW':
                self.msgs_to_db[-1]['timestamp'] = int(time.time()*1000)
            self.msgs_saved += 1
        if len(self.msgs_to_db)>=MSG_BATCH_NUM:
            self.save_db_msgs()
        
        # 保存raw文件
        self.msgs_to_raw.append(msg)
        if len(self.msgs_to_raw)>=MSG_BATCH_NUM_JSON:
            await self.save_json_msgs()
            
    
    def save_db_msgs(self):
        try:
            self.db.commit_msgs(self.msgs_to_db)
            self.commit_counter = 0
            self.msgs_to_db = []
        except Exception as err:
            print('[{:d}][{:s}][ERROR] 保存数据库时出现问题：{}'.format(self.id, time.strftime("%Y-%m-%d %H:%M:%S"), err))
    
    async def save_json_msgs(self):
        date_str = time.strftime("%Y%m%d")
        date_str_days_ago = time.strftime("%Y%m%d", time.localtime(time.time()-60*60*24*JSON_MSG_DAYS))
        o = ''
        for m in self.msgs_to_raw:
            o += json.dumps(m)
            o += ','
        async with aiofiles.open('{}{}-{}.json'.format(JSON_MSG_DIR, self.id, date_str), 'a') as f:
            await f.write(o)
        self.msgs_to_raw = []
        # 检查是否存在N天前的 存在就删了
        fname = '{}{}-{}.json'.format(JSON_MSG_DIR, self.id, date_str_days_ago)
        if os.path.isfile(fname):
            os.remove(fname)
    




async def quit_signal():
    while True:
        t = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if t.strip() == 'q':
            for room in rooms:
                await room.close_save_all()
            return
        else:
            print('wrong command.')

async def connect_all_rooms():
    '''
    连接所有直播间
    '''
    tasks = []
    tasks.append(asyncio.create_task(quit_signal()))
    for room in rooms:
        tasks.append(asyncio.create_task(room.live_danmuku.connect()))
        tasks.append(asyncio.create_task(room.listen()))
    await asyncio.gather(*tasks)


rooms = []
for room_id in ROOM_ID:
    rooms.append(Room(room_id))

if __name__ == "__main__":
    asyncio.run(connect_all_rooms())
