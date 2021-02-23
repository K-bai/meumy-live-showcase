import json
import sqlite3
import time
import os

SQL_INSERT_DANMU_MSG = 'INSERT INTO DANMU_MSG VALUES(?, ?, ?, ?, ?, ?, ?);'
SQL_INSERT_SEND_GIFT = 'INSERT INTO SEND_GIFT VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'
SQL_INSERT_USER_TOAST_MSG = 'INSERT INTO USER_TOAST_MSG VALUES(?, ?, ?, ?, ?, ?);'
SQL_INSERT_SUPER_CHAT_MESSAGE = 'INSERT INTO SUPER_CHAT_MESSAGE VALUES(?, ?, ?, ?, ?, ?, ?, ?);'
SQL_INSERT_VIEW = 'INSERT INTO VIEW VALUES(?, ?);'
SQL_INSERT_LIVE = 'INSERT INTO LIVE VALUES(?, ?);'
SQL_CREATE_TABLE = ['''
    CREATE TABLE DANMU_MSG(
        uid INTEGER,
        username TEXT,
        timestamp INTEGER,
        medal_name TEXT,
        medal_level INTEGER,
        captain INTEGER,
        content TEXT
    );''',
    '''
    CREATE TABLE SEND_GIFT(
        uid INTEGER,
        username TEXT,
        timestamp INTEGER,
        medal_name TEXT,
        medal_level INTEGER,
        captain INTEGER,
        gift_name TEXT,
        gift_num INTEGER,
        gift_price INTEGER,
        gift_total_price INTEGER,
        gift_coin_type TEXT
    );''',
    '''
    CREATE TABLE USER_TOAST_MSG(
        uid INTEGER,
        username TEXT,
        timestamp INTEGER,
        captain INTEGER,
        captain_num INTEGER,
        captain_total_price INTEGER
    );''',
    '''
    CREATE TABLE SUPER_CHAT_MESSAGE(
        uid INTEGER,
        username TEXT,
        timestamp INTEGER,
        medal_name TEXT,
        medal_level INTEGER,
        captain INTEGER,
        superchat_content TEXT,
        superchat_price INTEGER
    );''',
    '''
    CREATE TABLE VIEW(
        timestamp INTEGER,
        view INTEGER
    );''',
    '''
    CREATE TABLE LIVE(
        timestamp INTEGER,
        action TEXT
    );
    '''
]

class Msg_db:
    def __init__(self, name, date = None, sql_dir = 'db/'):
        self.name = str(name)
        self.SQL_DIR = sql_dir
        self.conn = None
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
        if os.path.isfile(path):
            self.conn = sqlite3.connect(path)
        else:
            self.conn = sqlite3.connect(path)
            for command in SQL_CREATE_TABLE:
                self.conn.execute(command)
    
    def __fresh_connect(self):
        '''
        检测数据库是不是当天的
        若不是则关闭连接并新建连接
        时间为东四区，以免加班计算到后一天
        '''
        t = time.strftime("%Y%m%d", time.localtime(time.time()-4*60*60))
        if self.conn_t != t:
            self.conn.close()
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

    def __insert_msg(self, msg):
        '''
        向数据库插入一条信息
        识别并格式化
        '''
        if msg['type'] == 'DANMU_MSG':
            medal = self.__user_medal(msg)
            self.conn.execute(SQL_INSERT_DANMU_MSG, (
                msg['data']['info'][2][0], #用户id
                msg['data']['info'][2][1], #用户名
                msg['data']['info'][0][4], #时间戳
                medal['n'], #牌子名
                medal['l'], #牌子等级
                medal['c'], #舰长类别
                msg['data']['info'][1] #弹幕文本
            ))
        elif msg['type'] == 'SEND_GIFT':
            medal = self.__user_medal(msg)
            self.conn.execute(SQL_INSERT_SEND_GIFT, (
                msg['data']['data']['uid'], #用户id
                msg['data']['data']['uname'], #用户名
                msg['data']['data']['timestamp']*1000, #时间戳
                medal['n'], #牌子名
                medal['l'], #牌子等级
                medal['c'], #舰长类别
                msg['data']['data']['giftName'], #礼物名
                msg['data']['data']['num'], #礼物数量
                msg['data']['data']['price'], #礼物单价
                msg['data']['data']['total_coin'], #礼物总价
                msg['data']['data']['coin_type'] #货币类型
            ))
        elif msg['type'] == 'USER_TOAST_MSG':
            self.conn.execute(SQL_INSERT_USER_TOAST_MSG, (
                msg['data']['data']['uid'], #用户id
                msg['data']['data']['username'], #用户名
                msg['data']['data']['start_time']*1000, #时间戳
                msg['data']['data']['guard_level'], #大航海类别
                msg['data']['data']['num'], #数量
                msg['data']['data']['price'] #真实花费价格（RMB）
            ))
        elif msg['type'] == 'SUPER_CHAT_MESSAGE':
            medal = self.__user_medal(msg)
            self.conn.execute(SQL_INSERT_SUPER_CHAT_MESSAGE, (
                msg['data']['data']['uid'], #用户id
                msg['data']['data']['user_info']['uname'], #用户名
                msg['data']['data']['ts']*1000, #时间戳
                medal['n'], #牌子名
                medal['l'], #牌子等级
                medal['c'], #舰长类别
                msg['data']['data']['message'], #醒目留言文本
                msg['data']['data']['price'] #价格（RMB）
            ))
        elif msg['type'] == 'VIEW':
            self.conn.execute(SQL_INSERT_VIEW, (
                msg['timestamp'], #时间戳
                msg['data'] #人气值
            ))
        else:
            return None

    def __convert_dict(self, cur):
        '''
        把数据库返回的信息转化成字典
        '''
        keys = []
        for key in cur.description:
            keys.append(key[0])
        output = []
        for row in cur:
            output.append(dict(zip(keys, row)))
        return output

    def commit_msgs(self, msgs):
        '''
        向数据库提交信息列表
        '''
        self.__fresh_connect()
        for msg in msgs:
            self.__insert_msg(msg)
        self.conn.commit()

    def live_action(self, timestamp, action):
        '''
        向数据库提交直播状态（开始、结束）
        '''
        self.__fresh_connect()
        self.conn.execute(SQL_INSERT_LIVE, (
            timestamp, #时间戳
            action #开始/结束
        ))
        self.conn.commit()
    
    def get_live_time(self):
        '''
        获取直播开始和结束时间
        若不存在，则返回(None, None)
        '''
        if self.live_time == None:
            cur = self.conn.cursor()
            cur.execute('SELECT * FROM LIVE')
            live_list = cur.fetchall()
            if live_list == []:
                return (None, None)
            live_list.sort(key = lambda x:x[0])
            start_time = None
            end_time = None
            for t in live_list:
                if t[1] == 'start' and start_time == None:
                    start_time = t[0]
                    break
            if live_list[-1][1] == 'end':
                end_time = live_list[-1][0]
            self.live_time = (start_time, end_time)
        return self.live_time

    def query_table_on_live(self, table):
        '''
        取出本数据库在开播时间段内的一个表
        若没有结束时间就到最新的为止
        '''
        start, end = self.get_live_time()
        cur = self.conn.cursor()
        data = None
        if start:
            if end:
                cur.execute('SELECT * FROM {:s} WHERE timestamp BETWEEN {:d} AND {:d}'.format(table, start, end))
                data = self.__convert_dict(cur)
            else:
                cur.execute('SELECT * FROM {:s} WHERE timestamp >= {:d}'.format(table, start))
                data = self.__convert_dict(cur)
        return data

    def query_msg(self):
        '''
        取出本数据库在开播时间段内的所有弹幕和sc
        '''
        return (self.query_table_on_live('DANMU_MSG'), self.query_table_on_live('SUPER_CHAT_MESSAGE'))


