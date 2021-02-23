import jieba
import jieba.analyse
import json
import time
import os
import re
from collections import Counter
from scipy.signal import savgol_filter
from scipy.signal import find_peaks
import numpy as np
from Msg_db import Msg_db

# 自定义词库，删除怪词
jieba.load_userdict('user_dict.txt')
jieba.del_word('哈哈哈哈')
jieba.del_word('哈哈')

# 正则表达式编译 匹配5位以上数字和5个以上连续字母
danmu_filter = re.compile(r'[0-9]{5,}|([a-zA-Z])\1{4,}')

class Danmu:
    def __init__(self, dm_list, sc_list, medal_name=None, keywords_re=None):
        self.medal_name = medal_name
        self.keywords_re = keywords_re
        self.sc_list = sc_list
        self.dm_list = dm_list
        self.dm_list.sort(key=lambda x:x['timestamp'])
        self.sc_list.sort(key=lambda x:x['timestamp'])

        self.total_danmu_number = len(self.dm_list)
        self.total_interact_number = 0
        self.total_interact_captain_number = 0
        self.interact_list = []

        # 分时段热词时间间隔（秒）
        self.HOTWORD_TIMESPAN = 10
        # 弹幕密度时间间隔（秒）
        self.DANMU_DENSITY_TIMESPAN = 5
        # 分时段热词数量
        self.SLICE_HOT_WORDS_NUMBER = 10
        # 总热词数量
        self.ALL_HOT_WORDS_NUMBER = 15
        # 识别峰值时的峰高下限
        self.PEAK_PROMINENCE = 20


    def split(self, time_span):
        '''
        对全部弹幕
        按time_span(秒)分片
        '''
        self.dm_slice = []
        a_list = []
        # 遍历弹幕列表
        t = self.dm_list[0]['timestamp']
        for dm in self.dm_list:
            while dm['timestamp'] >= t+time_span*1000:
                t += time_span*1000
                self.dm_slice.append(a_list)
                a_list = []
            a_list.append(dm)
        if a_list:
            self.dm_slice.append(a_list)

    def cal_density(self, time_span):
        '''
        计算分片弹幕密度
        和包含关键词弹幕密度
        '''
        self.split(time_span)
        y_axis = []
        keywords_y = []
        for dm_list in self.dm_slice:
            if dm_list:
                y_axis.append(len(dm_list))
                # 查找弹幕中是否含有关键词
                keywords_c = 0
                for d in dm_list:
                    if self.keywords_re.search(d['content']):
                        keywords_c+=1
                # 太小的直接过滤掉
                if keywords_c<=2:
                    keywords_c = 0
                keywords_y.append(keywords_c)
            else:
                y_axis.append(0)
                keywords_y.append(0)
        time_axis = self.time_axis(time_span)
        self.density = (time_axis, y_axis)
        self.keywords_density = (time_axis, keywords_y)
        return self.density


    def word_split(self, time_span):
        '''
        计算分时间段弹幕热词
        '''
        self.split(time_span)
        hot_words = []
        for dm_l in self.dm_slice:
            # 本时间分片，切词
            sentence = ' '.join(map(lambda x:x['content'], dm_l))
            words = jieba.analyse.extract_tags(sentence, topK=self.SLICE_HOT_WORDS_NUMBER)
            filterd = []
            for w in words:
                if not danmu_filter.search(w):
                    filterd.append(w)
            hot_words.append(filterd)
        self.hot_words = (self.time_axis(time_span), hot_words)
        return self.hot_words

    def all_hot_words(self, dm_list):
        '''
        计算弹幕热词
        '''
        sentence = ' '.join(map(lambda x:x['content'], dm_list))
        return jieba.analyse.extract_tags(sentence, topK=self.ALL_HOT_WORDS_NUMBER)
    
    def time_axis(self, time_span):
        '''
        根据time_span(秒)给出x时间轴
        '''
        start = self.dm_list[0]['timestamp']
        end = self.dm_list[-1]['timestamp']
        axis = list(range(start, end, time_span*1000))
        if axis[-1]+time_span*1000<=end:
            axis.append(axis[-1]+time_span*1000)
        return axis
    
    def captain_filter(self):
        '''
        过滤出舰长和单推人的弹幕
        '''
        self.captain_dm_list = []
        self.gachi_dm_list = []
        for dm in self.dm_list:
            if dm['medal_name'] == self.medal_name:
                self.gachi_dm_list.append(dm)
                if dm['captain'] > 0:
                    self.captain_dm_list.append(dm)

    def interact_analyse(self, dm_list):
        '''
        统计总发言人数
        统计发言量
        '''
        user_list = map(lambda x:x['username'], dm_list)
        in_c = Counter(user_list)
        interact_list = in_c.most_common()
        total_interact_number = len(interact_list)
        return (interact_list, total_interact_number)

    def find_peaks(self):
        '''
        查找弹幕峰值
        '''
        data = np.array(self.cal_density(5))
        # 平滑
        data[1] = savgol_filter(data[1],11,3)
        # 查找峰
        peaks, _ = find_peaks(data[1], prominence=self.PEAK_PROMINENCE)
        # 返回值
        return data[0][peaks].tolist()
    
    def output(self):
        '''
        生成网页可用的数据集
        1. 弹幕密度(5s)
        2. 分段弹幕热词(10s)
        3. sc列表
        4. 热词
            1. 全体观众
            2. 单推人（带牌子）
            3. 舰长
        5. 弹幕数
            1. 总体
            2. 单推人
            3. 舰长
        6. 互动人数
            1. 总体
            2. 单推人
            3. 舰长
        7. 发弹幕最多的前10人
        8. 弹幕峰值时间
        9. 关键词密度(5s)
        '''
        hw = self.word_split(self.HOTWORD_TIMESPAN)
        ds = self.cal_density(self.DANMU_DENSITY_TIMESPAN)
        self.captain_filter()
        all_intact = self.interact_analyse(self.dm_list)
        gachi_intact = self.interact_analyse(self.gachi_dm_list)
        captain_intact = self.interact_analyse(self.captain_dm_list)
        sc_list = []
        for sc in self.sc_list:
            sc_list.append({'u': sc['username'], 'c': sc['superchat_content'], 't': sc['timestamp'], 'p': sc['superchat_price']})
        output = {
            'density': list(zip(*ds)),
            'hot_words': list(zip(*hw)),
            'sc_list': sc_list,
            'all_hot_words': {
                'all': self.all_hot_words(self.dm_list), 
                'gachi': self.all_hot_words(self.gachi_dm_list), 
                'captain': self.all_hot_words(self.captain_dm_list)
            },
            'danmu_count':{
                'all': len(self.dm_list), 
                'gachi': len(self.gachi_dm_list), 
                'captain': len(self.captain_dm_list)
            },
            'interact_count':{
                'all': all_intact[1], 
                'gachi': gachi_intact[1], 
                'captain': captain_intact[1]
            },
            'most_interact': all_intact[0][0:10],
            'peaks': self.find_peaks(),
            'keywords_density': list(zip(*self.keywords_density))
        }
        return json.dumps(output, ensure_ascii = False)

def dir_update():
    '''
    扫描文件夹中今天对应的数据库
    连接检测然后更新
    更新原则：数据库没有表明结束时间，或者记录的文件没有表明结束时间
    '''
    # 读取已有文件
    with open(os.path.join(DANMU_SAVE_PATH, DANMU_LIST_NAME), 'r') as f:
        file_dict = json.loads(f.read())
    need_update = False
    # 读取文件结构
    for f in os.listdir(DANMU_ORG_PATH):
        # 跳过非数据库文件
        if f.split('.')[1] != 'db':
            continue
        vup_id = f.split('-')[0]
        date_n = f.split('-')[1].split('.')[0]
        # 跳过非今日日期
        today = time.strftime("%Y%m%d", time.localtime(time.time()-4*60*60))
        if date_n != today and FORCE_UPDATE == False:
            continue
        # 连接数据库
        db = Msg_db(vup_id, date_n)
        live_time = db.get_live_time()
        # 如果开播了
        if live_time[0] != None:
            # 新建vup
            if vup_id not in file_dict.keys():
                file_dict[vup_id] = [{'d': date_n, 's': None}]
            # 新建日期
            if date_n not in map(lambda x:x['d'], file_dict[vup_id]):
                file_dict[vup_id].append({'d': date_n, 's': None})
            # 查找对应时间
            for i in range(len(file_dict[vup_id])):
                if file_dict[vup_id][i]['d'] == date_n :
                    # 是否需要更新？
                    if live_time[1] == None or file_dict[vup_id][i]['s'] == None or FORCE_UPDATE == True:
                        # 更新网页所需文件
                        write_db(vup_id, date_n, db)
                        # 更新当前状态
                        file_dict[vup_id][i]['s'] = live_time[1]
                        need_update = True
                    else:
                        print('[{:s}] 无需更新 {:s}-{:s}, 直播结束'.format(time.strftime("%Y-%m-%d %H:%M:%S"), vup_id, date_n))
                    break
        else:
            print('[{:s}] 无需更新 {:s}-{:s}, 未开播'.format(time.strftime("%Y-%m-%d %H:%M:%S"), vup_id, date_n))
    if need_update:
        with open(os.path.join(DANMU_SAVE_PATH, DANMU_LIST_NAME), 'w') as f:
            # 倒序排序
            for key in file_dict.keys():
                file_dict[key].sort(key=lambda x:int(x['d']), reverse=True)
            f.write(json.dumps(file_dict))


def write_db(vup_id, date_n, db):
    tag = ''
    keywords_re = []
    for vup in VUP_LIST:
        if vup_id == vup['id']:
            tag = vup['tag']
            keywords_re = vup['keywords_re']
    fn = '{:s}-{:s}.json'.format(vup_id, date_n)
    print('[{:s}] 正在更新 {:s}'.format(time.strftime("%Y-%m-%d %H:%M:%S"), fn))
    # 收集弹幕数据
    dm_list = Danmu(*db.query_msg(), tag, keywords_re)
    # 写入文件
    with open(os.path.join(DANMU_SAVE_PATH,fn), 'w', encoding='utf-8') as f:
        f.write(dm_list.output())
    print('[{:s}] 更新完毕 {:s}'.format(time.strftime("%Y-%m-%d %H:%M:%S"), fn))
    

r'''
打call匹配文本
ღ: \u10e6
☀️: \u2600\ufe0f
☀: \u2600
\xxx/\xxx/: \\\\.+/
'''
DANMU_ORG_PATH = 'db/'
DANMU_SAVE_PATH = '../webpage/data'
DANMU_LIST_NAME = 'list.json'
SINGING_CALL_RE = re.compile('\u10e6|\u2600|\\\\.+/')
VUP_LIST = [{'id': '22384516', 'tag': '揪米', 'keywords_re': SINGING_CALL_RE}, {'id': '8792912', 'tag': '搞咩嘢', 'keywords_re': SINGING_CALL_RE}]
FORCE_UPDATE = True

if __name__ == "__main__":
    while True:
        dir_update()
        time.sleep(10*60)

