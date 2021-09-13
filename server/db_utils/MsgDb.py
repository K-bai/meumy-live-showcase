import os, datetime, time

from peewee import SqliteDatabase
from .db_declaration import Danmu, Gift, SuperChat, Captain, View, LiveStatus
MODELS = [Danmu, Gift, SuperChat, Captain, View, LiveStatus]
MSG_TYPE = ['DANMU_MSG', 'SEND_GIFT', 'SUPER_CHAT_MESSAGE', 'USER_TOAST_MSG', 'VIEW', 'LIVE']


class MsgDb:
    def __init__(self, name, sql_dir = 'db/'):
        self.name = str(name)
        self.SQL_DIR = sql_dir

        # 连接数据库
        db_name = '{:s}.db'.format(self.name)
        path = os.path.join(self.SQL_DIR, db_name)
        self.db = SqliteDatabase(path, pragmas=(
            ('cache_size', -1024 * 64),  # 64MB page-cache.
            ('journal_mode', 'wal'))) # Use WAL-mode (you should always use this!).
        self.db.connect()
        self.db.bind(MODELS)

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
                'timestamp': msg['timestamp'], #时间戳
                'view': msg['data'], #人气值
            })
        else:
            return None

    def commit_msgs(self, msgs):
        '''
        向数据库提交信息列表
        '''
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
        # 绑定model
        self.db.bind(MODELS)
        # 插入数据
        LiveStatus.insert(timestamp=timestamp, action=action).execute()
    
    def get_live_time(self, date):
        '''
        date为datetime.date对象
        获取当天直播开始和结束时间列表
        将北京时间第一天4:00到第二天4:00作为分界线
        若不存在，则返回[[None, None]]
        '''
        t = datetime.time(4, 0, 0, 0)
        start_t = datetime.datetime.combine(date, t)
        dt = datetime.timedelta(days=1)
        time_range = [int(start_t.timestamp()*1000), int((start_t+dt).timestamp()*1000)]
        data = (LiveStatus
            .select()
            .where(LiveStatus.timestamp>=time_range[0], LiveStatus.timestamp<=time_range[1])
            .order_by(LiveStatus.timestamp))
        if len(data) == 0:
            return [[None, None]]
        # 核心逻辑：
        # 第一个判断是start还是end，end就把开头设为start
        # 最后一个判断是start还是end，是start且边界在当前时间之前（说明不是没播完）就把结尾设为end
        # 上一个是start，下一个就去找end，如果是start就无视掉，反之同理
        action_list = list(data.dicts())
        if action_list[0]["action"] == "end":
            action_list.insert(0, {"action": "start", "timestamp": time_range[0]})
        if action_list[-1]["action"] == "start" and time_range[1]<time.time()*1000:
            action_list.append({"action": "end", "timestamp": time_range[1]})
        rst = []
        last = "end"
        for d in action_list:
            if d["action"] == last:
                continue
            if d["action"] == "start":
                rst.append([d["timestamp"], None])
                last = "start"
            elif d["action"] == "end":
                rst[-1][1] = d["timestamp"]
                last = "end"
        # 筛选每个时间段 太短（小于1min）不要
        rst_filtered = []
        for x in rst:
            if x[-1] != None:
                if x[1]-x[0]<60*1000:
                    continue
            rst_filtered.append(x)
        return rst_filtered

    def query_table_on_live(self, model, date, idx):
        '''
        取出当天在开播时间段内的一个表格
        若没有结束时间就到最新的为止
        date为datetime.date对象
        idx为直播次序编号
        '''
        start, end = self.get_live_time(date)[idx]
        # 如果没有结束时间就持续到下一天4点
        if end == None:
            dt = datetime.timedelta(days=1)
            end = int(datetime.datetime.combine(date+dt, datetime.time(4, 0, 0, 0)).timestamp()*1000)
        # 绑定model
        self.db.bind(MODELS)
        data = None
        if start:
            if end:
                data = model.select().where(model.timestamp >= start, model.timestamp <= end).dicts()
            else:
                data = model.select().where(model.timestamp >= start).dicts()
        return list(data)

    def query_msg(self, date, idx):
        '''
        取出本数据库在开播时间段内的所有弹幕和sc
        date为datetime.date对象
        idx为今天直播次序编号 从0开始
        '''
        return (
            self.query_table_on_live(Danmu, date, idx), 
            self.query_table_on_live(SuperChat, date, idx)
        )
