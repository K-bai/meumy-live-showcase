import json, datetime, time, os, re, jieba, jieba.analyse
from collections import Counter
from functools import cmp_to_key
from scipy.signal import savgol_filter
from scipy.signal import find_peaks
import numpy as np
from db_utils.MsgDb import MsgDb


# 自定义词库，删除怪词
jieba.load_userdict('user_dict.txt')
jieba.del_word('哈哈哈哈')
jieba.del_word('哈哈')

# 两个idf词库
IDF_GENERAL = 'idf/idf_general.txt'
IDF_LIVE = 'idf/idf_live.txt'

# 正则表达式编译
# 匹配5位以上数字和5个以上连续字母
danmu_filter = re.compile(r'[0-9]{5,}|([a-zA-Z])\1{4,}')
# 匹配哈
haha_filter = re.compile(r'哈')
# 匹配草
fuck_filter = re.compile(r'草')
# 匹配问号
problem_filter = re.compile(r'[?？]')

# 一些预定义的参数
SLICE_HOT_WORDS_NUMBER = 10 # 分片热词数量
ALL_HOT_WORDS_NUMBER = 15 # 总热词数量
DENSITY_TIME_INTERVAL = 5 # 弹幕密度计算时间间隔（秒）
HOT_WORDS_TIME_INTERVAL = 10 # 热词计算时间间隔（秒）

PEAK_PROMINENCE = 20 # 峰识别峰高阈值

# 一些用来给日期字符串排序的垃圾函数
def date_text_split(t):
    split = t['d'].split('-')
    d = int(split[0])
    n = 0
    if len(split) > 1:
        n = int(split[1])
    return d, n
def date_text_compare(a, b):
    a_split = date_text_split(a)
    b_split = date_text_split(b)
    if a_split[0]>b_split[0]:
        return 1
    elif a_split[0]<b_split[0]:
        return -1
    else:
        return a_split[1]-b_split[1]

class Danmu:
    def __init__(self, dm_list, sc_list, medal_name=None, keywords_re=None):
        self.medal_name = medal_name
        self.sc_list = sc_list
        self.dm_list = dm_list
        self.dm_list.sort(key=lambda x:x['timestamp'])
        self.sc_list.sort(key=lambda x:x['timestamp'])
        time_list = [dm['timestamp'] for dm in self.dm_list]
        self.time_range = [min(time_list), max(time_list)]
        self.captain_dm_list = [
            dm for dm in self.dm_list 
            if dm['medal_name'] in self.medal_name and dm['captain'] > 0
        ]
        self.gachi_dm_list = [
            dm for dm in self.dm_list 
            if dm['medal_name'] in self.medal_name
        ]
        self.singing_dm_list = [
            dm for dm in self.dm_list 
            if keywords_re.search(dm['content'])
        ]
        self.haha_dm_list = [
            dm for dm in self.dm_list 
            if haha_filter.search(dm['content'])
        ]
        self.fuck_dm_list = [
            dm for dm in self.dm_list 
            if fuck_filter.search(dm['content'])
        ]
        self.problem_dm_list = [
            dm for dm in self.dm_list 
            if problem_filter.search(dm['content'])
        ]

    def time_axis(self, time_interval=5):
        '''
        根据time_interval(秒)给出x时间轴
        '''
        time_ms = time_interval*1000
        start = self.time_range[0]
        end = self.time_range[1]
        axis = list(range(start, end, time_ms))
        if axis[-1]+time_ms<=end:
            axis.append(axis[-1]+time_ms)
        return axis

    def time_slicing(self, dm_list=(), time_axis=()):
        '''
        将传入的列表按时间间隔分开
        time_axis是一个列表 表示需要分开的时间段
        '''
        # 遍历时间轴
        rst = []
        for t in range(len(time_axis)-1):
            rst.append([])
            # 遍历弹幕列表
            for dm in dm_list:
                if dm["timestamp"]>time_axis[t] and dm["timestamp"]<=time_axis[t+1]:
                    rst[-1].append(dm)
                elif dm["timestamp"]>time_axis[t+1]:
                    break
        return rst
    
    def hot_words(self, dm_list=(), num=10):
        '''
        根据传入的列表计算热词
        字典content字段为需要计算的词
        num为输出的词的数量
        '''
        if len(dm_list) == 0:
            return []
        sentence = ' '.join([
            dm['content'] for dm in dm_list
            if not danmu_filter.search(dm['content'])
        ])
        return jieba.analyse.extract_tags(sentence, topK=num)
    
    def key_words(self, dm_list=(), num=10):
        '''
        根据传入的列表计算关键词 根据新的idf词典
        字典content字段为需要计算的词
        num为输出的词的数量
        只能在hot_words之后调用
        '''
        jieba.analyse.set_idf_path("./idf/idf_live.txt")
        rst = self.hot_words(dm_list=dm_list, num=num)
        jieba.analyse.set_idf_path("./idf/idf_general.txt")
        return rst

    def interact_analyse(self, dm_list=()):
        '''
        统计总发言人数
        统计发言量
        '''
        user_list = [x['username'] for x in dm_list]
        in_c = Counter(user_list)
        interact_list = in_c.most_common()
        total_interact_number = len(interact_list)
        return (interact_list, total_interact_number)

    def find_peaks(self, dm_list=()):
        '''
        查找弹幕峰值
        '''
        x = np.array(self.time_axis(DENSITY_TIME_INTERVAL))
        y = np.array([
            len(x) 
            for x in self.time_slicing(dm_list=dm_list, time_axis=self.time_axis(DENSITY_TIME_INTERVAL))
        ])
        # 数据量太少就返回空
        if len(y)<30:
            return []
        # 平滑
        y = savgol_filter(y,11,3)
        # 查找峰
        peaks, _ = find_peaks(y, prominence=PEAK_PROMINENCE)
        # 返回值
        return x[peaks].tolist()
    
    def output(self):
        '''
        生成网页可用的数据集
        1. 弹幕密度 包括总弹幕 打call 哈 草 问号(5s)
        2. 分段弹幕热词(10s)
        3. sc列表
        4. 热词(数量最多)
            1. 全体观众
            2. 单推人（带牌子）
            3. 舰长
        5. 推测可能的关键词(按直播的idf给出)
            1. 全体观众
        6. 弹幕数
            1. 总体
            2. 单推人
            3. 舰长
        7. 互动人数
            1. 总体
            2. 单推人
            3. 舰长
        8. 发弹幕最多的前10人
        9. 弹幕峰值时间
        '''
        # 1. 弹幕密度(5s)
        density_time_axis = self.time_axis(DENSITY_TIME_INTERVAL)
        total_density = {
            'x': density_time_axis,
            'total': [
                len(x) 
                for x in self.time_slicing(dm_list=self.dm_list, time_axis=density_time_axis)
            ],
            'call': [
                len(x) 
                for x in self.time_slicing(dm_list=self.singing_dm_list, time_axis=density_time_axis)
            ],
            'haha': [
                len(x) 
                for x in self.time_slicing(dm_list=self.haha_dm_list, time_axis=density_time_axis)
            ],
            'fuck': [
                len(x) 
                for x in self.time_slicing(dm_list=self.fuck_dm_list, time_axis=density_time_axis)
            ],
            'problem': [
                len(x) 
                for x in self.time_slicing(dm_list=self.problem_dm_list, time_axis=density_time_axis)
            ]
        }
        # 2. 分段弹幕热词(10s)
        hot_words_time_axis = self.time_axis(HOT_WORDS_TIME_INTERVAL)
        time_slice_hot_words = list(zip(
            hot_words_time_axis,
            [
                self.hot_words(dm_list=x, num=SLICE_HOT_WORDS_NUMBER) 
                for x in self.time_slicing(dm_list=self.dm_list, time_axis=hot_words_time_axis)
            ]
        ))
        # 3. sc列表
        sc_list = []
        for sc in self.sc_list:
            sc_list.append({'u': sc['username'], 'c': sc['superchat_content'], 't': sc['timestamp'], 'p': sc['superchat_price']})
        output = {
            'density': total_density,
            'hot_words': time_slice_hot_words,
            'sc_list': sc_list,
            'all_hot_words': {
                'all': self.hot_words(self.dm_list), 
                'gachi': self.hot_words(self.gachi_dm_list), 
                'captain': self.hot_words(self.captain_dm_list)
            },
            'all_key_words': {
                'all': self.key_words(self.dm_list), 
            },
            'danmu_count':{
                'all': len(self.dm_list), 
                'gachi': len(self.gachi_dm_list), 
                'captain': len(self.captain_dm_list)
            },
            'interact_count':{
                'all': self.interact_analyse(dm_list=self.dm_list)[1], 
                'gachi': self.interact_analyse(dm_list=self.gachi_dm_list)[1], 
                'captain': self.interact_analyse(dm_list=self.captain_dm_list)[1]
            },
            'most_interact': self.interact_analyse(dm_list=self.dm_list)[0][0:10],
            'peaks': self.find_peaks(self.dm_list),
        }
        return json.dumps(output, ensure_ascii = False)

def dir_update():
    '''
    扫描文件夹中今天对应的数据库
    连接检测然后更新
    更新原则：数据库没有表明结束时间，或者记录的文件没有表明结束时间
    如何判定今天两场直播？
    '''
    # 读取已有文件
    with open(os.path.join(DANMU_SAVE_PATH, DANMU_LIST_NAME), 'r') as f:
        file_dict = json.loads(f.read())
    need_update = False
    if DATE_LIST:
        date_list = DATE_LIST
    else:
        date_list = [datetime.date.today()]
    for vup in VUP_LIST:
        # 遍历每个vup
        db = MsgDb(vup["id"])
        for date in date_list:
            # 遍历全部日期
            live_list = db.get_live_time(date)
            date_n = date.strftime("%Y%m%d")
            if live_list[0][0] != None:
                # 如果开播了
                for idx in range(len(live_list)):
                    # 遍历日期内每场直播
                    live_time = live_list[idx]
                    if idx > 0:
                        date_n = "{:s}-{:d}".format(date.strftime("%Y%m%d"), idx+1)
                    # 文件里添加信息
                    # 添加vup
                    if vup["id"] not in file_dict.keys():
                        file_dict[vup["id"]] = [{"d": date_n, "s": None}]
                    # 添加日期
                    if date_n not in map(lambda x:x["d"], file_dict[vup["id"]]):
                        file_dict[vup["id"]].append({"d": date_n, "s": None})
                    # 查找对应时间
                    for i in range(len(file_dict[vup["id"]])):
                        if file_dict[vup["id"]][i]['d'] == date_n :
                            # 是否需要更新？
                            # 直播未结束，即没有结束时间需要更新
                            # 文件里没记录直播结束，需要更新
                            # FORCE_UPDATE标志为真 需要更新
                            if live_time[1] == None or file_dict[vup["id"]][i]['s'] == None or FORCE_UPDATE == True:
                                # 更新网页所需文件
                                write_json(vup["id"], date, idx, db)
                                # 更新当前状态
                                file_dict[vup["id"]][i]['s'] = live_time[1]
                                need_update = True
                            else:
                                print('[{:s}] 无需更新 {:s}-{:s}, 直播结束'.format(time.strftime("%Y-%m-%d %H:%M:%S"), vup["id"], date_n))
                            break
            else:
                print('[{:s}] 无需更新 {:s}-{:s}, 未开播'.format(time.strftime("%Y-%m-%d %H:%M:%S"), vup["id"], date_n))
    if need_update:
        with open(os.path.join(DANMU_SAVE_PATH, DANMU_LIST_NAME), 'w') as f:
            # 倒序排序
            for key in file_dict.keys():
                file_dict[key].sort(key=cmp_to_key(date_text_compare), reverse=True)
            f.write(json.dumps(file_dict))


def write_json(vup_id, date, idx, db):
    '''
    从数据库获取数据并写入json文件
    vup_id: string
    date: datetime.date对象 日期
    idx: 当天直播次序编号 从0开始
    db: 数据库对象
    '''
    date_n = date.strftime("%Y%m%d")
    if idx > 0:
        date_n = "{:s}-{:d}".format(date_n, idx+1)
    for vup in VUP_LIST:
        if vup_id == vup['id']:
            tag = vup['tag']
            keywords_re = vup['keywords_re']
    fn = '{:s}-{:s}.json'.format(vup_id, date_n)
    print('[{:s}] 正在更新 {:s}'.format(time.strftime("%Y-%m-%d %H:%M:%S"), fn))
    # 收集弹幕数据
    dm_list = Danmu(*db.query_msg(date, idx), tag, keywords_re)
    # 写入文件
    with open(os.path.join(DANMU_SAVE_PATH,fn), 'w', encoding='utf-8') as f:
        f.write(dm_list.output())
    print('[{:s}] 更新完毕 {:s}'.format(time.strftime("%Y-%m-%d %H:%M:%S"), fn))
    

r'''
打call匹配文本
ღ: \u10e6
☀️: \u2600\ufe0f
☀: \u2600
⛈️: \u26c8\ufe0f
⛈: \u26c8
⛅: \u26c5
\xxx/\xxx/: \\\\.+/
'''
DANMU_ORG_PATH = 'db/'
#DANMU_SAVE_PATH = 'output/'
DANMU_SAVE_PATH = '/data/meumy_web/data'
DANMU_LIST_NAME = 'list.json'
SINGING_CALL_RE = re.compile('\u10e6|\u2600|\u26c8|\u26c5|\\\\.+/')
VUP_LIST = [
    {'id': '22384516', 'tag': ['揪米', '小米星'], 'keywords_re': SINGING_CALL_RE},
    {'id': '8792912', 'tag': ['搞咩嘢', '小綿花'], 'keywords_re': SINGING_CALL_RE}
]
FORCE_UPDATE = True
DATE_LIST = None
'''
DATE_LIST = []
date_range = (datetime.date(2020, 9, 12), datetime.date(2021, 8, 27))
cur = date_range[0]
one_day = datetime.timedelta(days=1)
while cur<=date_range[1]:
    DATE_LIST.append(cur)
    cur += one_day
'''



if __name__ == "__main__":
    while True:
        dir_update()
        time.sleep(10*60)

