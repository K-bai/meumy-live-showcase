import time
import os

from peewee import SqliteDatabase
from db_declaration import Danmu, Live, Gift, SuperChat, Captain, View
MODELS = [Danmu, Gift, SuperChat, Captain, View, Live]
MSG_TYPE = ['DANMU_MSG', 'SEND_GIFT', 'SUPER_CHAT_MESSAGE', 'USER_TOAST_MSG', 'VIEW', 'LIVE']
MODELS_DICT = {
    'DANMU_MSG': Danmu,
    'SEND_GIFT': Gift,
    'SUPER_CHAT_MESSAGE': SuperChat,
    'USER_TOAST_MSG': Captain,
    'VIEW': View,
    'LIVE': Live,
}

class Msg_db:
    def __init__(self, name, date = None, sql_dir = 'db/'):
        self.name = str(name)
        self.SQL_DIR = sql_dir
        self.db = SqliteDatabase(None)
        if date:
            self.conn_t = str(date)
        else:
            self.conn_t = time.strftime("%Y%m%d", time.localtime(time.time()-4*60*60))
        self.__connect()
        self.live_time = None


    def __connect(self):
        '''
        连接数据库，不存在就新建
        '''
        db_name = '{:s}-{:s}.db'.format(self.name, self.conn_t)
        path = os.path.join(self.SQL_DIR, db_name)
        is_new = True
        if os.path.isfile(path):
            is_new = False
        self.db.init(path)
        self.db.connect()
        if is_new:
            self.db.bind(MODELS)
            self.db.create_tables(MODELS)

    def __fresh_connect(self):
        '''
        检测数据库是不是当天的
        若不是则关闭连接并新建连接
        时间为东四区，以免加班计算到后一天
        '''
        t = time.strftime("%Y%m%d", time.localtime(time.time()-4*60*60))
        if self.conn_t != t:
            self.db.close()
            self.conn_t = t
            self.__connect()

    def __user_medal(self, msg):
        '''
        格式化信息中的牌子
        '''
        if msg['type'] == 'DANMU_MSG':
            if msg['data']['info'][3]: 
                if msg['data']['info'][3][11] == 1:
                    return {
                        'n': msg['data']['info'][3][1], #牌子名
                        'l': msg['data']['info'][3][0], #牌子等级
                        'c': msg['data']['info'][3][10], #舰长类别
                    }
        else:
            if msg['data']['data']['medal_info']:
                if msg['data']['data']['medal_info']['is_lighted'] == 1:
                    return {
                        'n': msg['data']['data']['medal_info']['medal_name'], #牌子名
                        'l': msg['data']['data']['medal_info']['medal_level'], #牌子等级
                        'c': msg['data']['data']['medal_info']['guard_level'], #舰长类别
                    }
        return {
            'n': None, #牌子名
            'l': None, #牌子等级
            'c': None #舰长类别
        }

    def __insert_msg(self, msg, insert_list):
        '''
        向列表插入一条信息
        识别并格式化
        '''
        if msg['type'] == 'DANMU_MSG':
            medal = self.__user_medal(msg)
            insert_list[msg['type']].append({
                'captain': medal['c'], #舰长类别
                'content': msg['data']['info'][1], #弹幕文本
                'medal_level': medal['l'], #牌子等级
                'medal_name': medal['n'], #牌子名
                'timestamp': msg['data']['info'][0][4], #时间戳
                'uid': msg['data']['info'][2][0], #用户id
                'username': msg['data']['info'][2][1], #用户名
            })
        elif msg['type'] == 'SEND_GIFT':
            medal = self.__user_medal(msg)
            insert_list[msg['type']].append({
                'captain': medal['c'], #舰长类别
                'gift_coin_type': msg['data']['data']['coin_type'], #货币类型
                'gift_name': msg['data']['data']['giftName'], #礼物名
                'gift_num': msg['data']['data']['num'], #礼物数量
                'gift_price': msg['data']['data']['price'], #礼物单价
                'gift_total_price': msg['data']['data']['total_coin'], #礼物总价
                'medal_level': medal['l'], #牌子等级
                'medal_name': medal['n'], #牌子名
                'timestamp': msg['data']['data']['timestamp']*1000, #时间戳
                'uid': msg['data']['data']['uid'], #用户id
                'username': msg['data']['data']['uname'], #用户名
            })
        elif msg['type'] == 'USER_TOAST_MSG':
            insert_list[msg['type']].append({
                'captain': msg['data']['data']['guard_level'], #大航海类别
                'captain_num': msg['data']['data']['num'], #数量
                'captain_total_price': msg['data']['data']['price'], #真实花费价格（RMB）
                'timestamp': msg['data']['data']['start_time']*1000, #时间戳
                'uid': msg['data']['data']['uid'], #用户id
                'username': msg['data']['data']['username'], #用户名
            })
        elif msg['type'] == 'SUPER_CHAT_MESSAGE':
            medal = self.__user_medal(msg)
            insert_list[msg['type']].append({
                'captain': medal['c'], #舰长类别
                'medal_level': medal['l'], #牌子等级
                'medal_name': medal['n'], #牌子名
                'superchat_content': msg['data']['data']['message'], #醒目留言文本
                'superchat_price': msg['data']['data']['price'], #价格（RMB）
                'timestamp': msg['data']['data']['ts']*1000, #时间戳
                'uid': msg['data']['data']['uid'], #用户id
                'username': msg['data']['data']['user_info']['uname'], #用户名
            })
        elif msg['type'] == 'VIEW':
            insert_list[msg['type']].append({
                #'timestamp': msg['timestamp'], #时间戳
                'timestamp': 0, #时间戳
                'view': msg['data'], #人气值
            })
        else:
            return None

    def __convert_dict(self, data):
        '''
        把数据库返回的信息转化成字典
        '''
        output = []
        for row in data:
            output.append(row)
        return output

    def commit_msgs(self, msgs):
        '''
        向数据库提交信息列表
        '''
        # 刷新数据库
        self.__fresh_connect()
        # 绑定model
        self.db.bind(MODELS)
        # 列表分类
        insert_list = {}
        for t in MSG_TYPE:
            insert_list[t] = []
        # 创建插入列表
        for msg in msgs:
            self.__insert_msg(msg, insert_list)
        # 插入数据
        with self.db.atomic():
            Danmu.insert_many(insert_list['DANMU_MSG']).execute()
            Gift.insert_many(insert_list['SEND_GIFT']).execute()
            Captain.insert_many(insert_list['USER_TOAST_MSG']).execute()
            SuperChat.insert_many(insert_list['SUPER_CHAT_MESSAGE']).execute()
            View.insert_many(insert_list['VIEW']).execute()

    def live_action(self, timestamp, action):
        '''
        向数据库提交直播状态（开始、结束）
        '''
        # 刷新数据库
        self.__fresh_connect()
        # 绑定model
        self.db.bind(MODELS)
        # 插入数据
        Live.insert(timestamp=timestamp, action=action).execute()
    
    def get_live_time(self):
        '''
        获取直播开始和结束时间
        若不存在，则返回(None, None)
        '''
        if self.live_time == None:
            # 绑定model
            self.db.bind(MODELS)
            live_list = Live.select().order_by(Live.timestamp)
            if len(live_list) == 0:
                return (None, None)
            start_time = None
            end_time = None
            for t in live_list:
                if t.action == 'start' and start_time == None:
                    start_time = t.timestamp
                    break
            if live_list[-1].action == 'end':
                end_time = live_list[-1].timestamp
            self.live_time = (start_time, end_time)
        return self.live_time

    def query_table_on_live(self, model):
        '''
        取出本数据库在开播时间段内的一个表格
        若没有结束时间就到最新的为止
        '''
        start, end = self.get_live_time()
        # 绑定model
        self.db.bind(MODELS)
        data = None
        if start:
            if end:
                data = model.select().where(model.timestamp >= start, model.timestamp <= end).dicts()
            else:
                data = model.select().where(model.timestamp >= start).dicts()
        return data

    def query_msg(self):
        '''
        取出本数据库在开播时间段内的所有弹幕和sc
        '''
        return (self.__convert_dict(self.query_table_on_live(Danmu)), self.__convert_dict(self.query_table_on_live(SuperChat)))




if __name__ == "__main__":
    db = Msg_db(22384516, 20210227)
    print(db.query_table_on_live(Danmu))
    
