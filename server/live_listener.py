from bilibililive import BilibiliLive
from db_utils.MsgDb import MsgDb
import asyncio
import json
import os, sys, time, logging, traceback
from logging.handlers import RotatingFileHandler


# 日志
LOG_DIR = 'log/'

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s][%(name)s][%(levelname)s]%(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
file_handler = RotatingFileHandler(os.path.join(LOG_DIR, 'live.log'), maxBytes=1024*1024*10, backupCount=5, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


#ROOM_ID = [22608112, 22926711]
ROOM_ID = [22384516, 8792912]

MSG_BATCH_NUM = 50
MSG_BATCH_NUM_JSON = 500
JSON_MSG_DIR = 'raw/'
JSON_MSG_DAYS = 10


ALL_CMD = [
    'DANMU_MSG',
    'SEND_GIFT',
    'USER_TOAST_MSG',
    'SUPER_CHAT_MESSAGE',
    'VIEW',
    'WATCHED_CHANGE'
]
ADD_TIME_CMD = [
    'VIEW',
    'WATCHED_CHANGE'
]

class Room:
    def __init__(self, room_id):
        # 数据库和获取弹幕库
        self.id = room_id
        self.live_danmuku = BilibiliLive(self.id)
        self.db = MsgDb(str(self.id))
        # 状态和临时数据
        self.status = False
        self.msgs_to_db = []
        self.msgs_to_raw = []
        self.msgs_saved = 0
        self.commit_counter = 0
        # 注册handler
        self.live_danmuku.handle = self.append_msg

    async def auto_commit(self):
        '''
        30秒提交一次信息
        '''
        while True:
            # 超时提交信息
            self.commit_counter += 1
            if self.commit_counter >= 2:
                self.save_db_msgs()
            logger.info(f'[{self.id}]共已接收{self.msgs_saved}条信息 {len(self.msgs_to_db)}条信息尚未提交数据库')
            await asyncio.sleep(30)
    
    async def close_save_all(self):
        await self.live_danmuku.close()
        self.save_db_msgs()
        self.save_json_msgs()
        logger.info(f'[{self.id}]已保存数据并关闭连接.')

    
    def append_msg(self, msg):
        '''
        将获取到的信息存入列表
        若超过50条则写入数据库
        超过500条就写入json文本
        '''
        # 保存至数据库
        # 是否在需要保存的列表里
        if msg['cmd'].find('DANMU_MSG') > -1:
            msg['cmd'] = 'DANMU_MSG'
        if msg['cmd'] in ALL_CMD:
            self.msgs_to_db.append(msg)
            # VIEW和WATCHED_CHANGE类别需要加时间戳
            if msg['cmd'] in ADD_TIME_CMD:
                self.msgs_to_db[-1]['timestamp'] = int(time.time()*1000)
            self.msgs_saved += 1
        elif msg['cmd'] == 'LIVE':
            # 直播开始
            self.db.live_action(int(time.time()*1000), 'start')
        elif msg['cmd'] == 'PREPARING':
            # 直播结束
            self.db.live_action(int(time.time()*1000), 'end')
        
        # 保存至数据库
        if len(self.msgs_to_db)>=MSG_BATCH_NUM:
            self.save_db_msgs()
        
        # 保存raw文件
        self.msgs_to_raw.append(msg)
        if len(self.msgs_to_raw)>=MSG_BATCH_NUM_JSON:
            self.save_json_msgs()
    
    def save_db_msgs(self):
        try:
            self.db.commit_msgs(self.msgs_to_db)
            self.commit_counter = 0
            self.msgs_to_db = []
        except Exception as err:
            logger.error(f'[{self.id}]保存数据库时出现问题：{json.dumps(self.msgs_to_db, ensure_ascii=False)}')
            traceback.print_exc()
    
    def save_json_msgs(self):
        date_str = time.strftime("%Y%m%d")
        date_str_days_ago = time.strftime("%Y%m%d", time.localtime(time.time()-60*60*24*JSON_MSG_DAYS))
        o = ''
        for m in self.msgs_to_raw:
            o += json.dumps(m, ensure_ascii=False)
            o += ',\n'
        with open(os.path.join(JSON_MSG_DIR, f'{self.id}-{date_str}.json'), 'a', encoding='utf8') as f:
            f.write(o)
        self.msgs_to_raw = []
        # 检查是否存在N天前的 存在就删了
        fname = os.path.join(JSON_MSG_DIR, f'{self.id}-{date_str_days_ago}.json')
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
        tasks.append(asyncio.create_task(room.live_danmuku.keep_alive()))
        tasks.append(asyncio.create_task(room.auto_commit()))
    await asyncio.gather(*tasks)
    time.sleep(0.2)

rooms = []
for room_id in ROOM_ID:
    rooms.append(Room(room_id))


if __name__ == "__main__":
    asyncio.run(connect_all_rooms())
