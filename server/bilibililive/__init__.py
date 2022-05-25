import aiohttp, asyncio, requests, struct, json, brotli, traceback, logging

logger = logging.getLogger(__name__)


class BilibiliLive():
    def __init__(self, rid):
        self.id = rid
        self.ws = None
        self.handle = None
        self.reconnect_sec = 5

        self.__heartbeat_task = None
        self.__heartbeat_timer = 0
        self.__keep_alive_flag = True
    
    def __get_live_info(self):
        url = 'https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo'
        params = {
            'id': self.id,
            'type': 0
        }
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
        except Exception as e:
            logger.error(f'[{self.id}]获取直播间信息时发生网络错误')
            raise e
        res_obj = res.json()
        conf = {
            'urls': [
                'wss://{}:{}/sub'.format(host['host'], host['wss_port'])
                for host in res_obj['data']['host_list']
            ],
            'token': res_obj['data']['token']
        }
        logger.info(f'[{self.id}]已获取服务器地址{conf!r}')
        return conf

    async def connect(self):
        '''
        连接弹幕服务器，心跳包维持
        '''
        # 获取服务器地址
        try:
            conf = self.__get_live_info()
        except:
            logger.error(f'[{self.id}]获取直播间信息错误，退出连接')
            return
        # 建立连接
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(conf['urls'][0]) as ws:
                    self.ws = ws
                    await self.__send_verify(conf['token'])
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            pass
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            raw_data = self.__unpack(msg.data)
                            for d in raw_data:
                                self.__process_data(d)
                        elif msg.type == aiohttp.WSMsgType.PING:
                            pass
                        elif msg.type == aiohttp.WSMsgType.PONG:
                            pass
                        elif msg.type == aiohttp.WSMsgType.CLOSE:
                            logger.info(f'[{self.id}]ws连接返回了关闭')
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f'[{self.id}]ws连接返回了错误')
                            break
        except Exception as e:
            logger.error(f'[{self.id}]直播间连接中出现了错误')
            traceback.print_exc()
        # 退出ws连接 取消心跳包活动
        if self.__heartbeat_task != None:
            self.__heartbeat_task.cancel()
        logger.info(f'[{self.id}]ws连接已完全断开')
    
    async def keep_alive(self):
        self.__keep_alive_flag = True
        while True:
            await self.connect()
            if self.__keep_alive_flag:
                for i in range(self.reconnect_sec, 0, -1):
                    logger.error(f'[{self.id}]意外断开连接，{i}秒后重连')
                    await asyncio.sleep(1)
            else:
                break
    
    def __process_data(self, raw_data):
        '''
        处理接收到的数据
        '''
        if raw_data['type'] == 'welcome':
            # 认证成功注册心跳任务
            self.__heartbeat_timer = 0
            self.__heartbeat_task = asyncio.create_task(self.__heartbeat())
            logger.info(f'[{self.id}]认证成功')
        elif raw_data['type'] == 'heartbeat':
            # 心跳包返回 重置计时器 返回人气值
            logger.debug(f'[{self.id}]收到心跳包')
            self.__heartbeat_timer = 30
            self.handle({
                'cmd': 'VIEW',
                'data': raw_data['data']
            })
        elif raw_data['type'] == 'data':
            data = raw_data['data']
            logger.debug(f'[{self.id}]收到数据')
            self.handle(data)
        else:
            data = raw_data['data']
            logger.warning(f'[{self.id}]收到未知版本消息, {data}')
    


    async def __heartbeat(self):
        '''
        定时30s发送心跳包
        发送后10s没收到回应则超时
        '''
        while True:
            if self.__heartbeat_timer == 0:
                await self.send(b'', 'heartbeat')
                logger.debug(f'[{self.id}]已发送心跳包')
            elif self.__heartbeat_timer <= -10:
                logger.error(f'[{self.id}]心跳包连接超时')
                await self.ws.close()
                break
            await asyncio.sleep(1)
            self.__heartbeat_timer -= 1

    async def __send_verify(self, token):
        '''
        发送认证包
        '''
        await self.send(json.dumps({
            "uid": 0,
            "roomid": self.id,
            "protover": 3,
            "platform": "web",
            "type": 2,
            "key": token
        }).encode(), 'verify')
        logger.debug(f'[{self.id}]已发送认证包')
    
    async def send(self, data, data_type):
        await self.ws.send_bytes(self.__pack(data, data_type))
    
    async def close(self):
        self.__keep_alive_flag = False
        await self.ws.close()
        logger.info(f'[{self.id}]已手动断开连接')

    @staticmethod
    def __pack(data, data_type):
        '''
        打包数据
        '''
        PACK_TYPE = {
            'heartbeat': 2,
            'verify': 7
        }
        send_data = bytearray()
        send_data += struct.pack(">H", 16) # 固定字段
        send_data += struct.pack(">H", 1) # 数据包类别 心跳包
        send_data += struct.pack(">I", PACK_TYPE[data_type]) # 数据包类别 分心跳包和验证
        send_data += struct.pack(">I", 1) # 固定字段
        send_data += data # 数据段
        send_data = struct.pack(">I", len(send_data) + 4) + send_data # 第一个字段是长度
        return bytes(send_data)

    @staticmethod
    def __unpack(data):
        '''
        解包数据
        '''
        PROTOCOL_VERSION = {
            'raw': 0,
            'heartbeat': 1,
            'brotli': 3
        }
        MSG_TYPE = {
            'heartbeat': 3,
            'message': 5,
            'welcome': 8
        }
        # 先看是不是压缩的
        header = struct.unpack(">IHHII", data[:16])
        if header[2] == PROTOCOL_VERSION['brotli']:
            real_data = brotli.decompress(data[16:])
        else:
            real_data = data
        # 按长度分割数据包并逐个解析
        rst = []
        offset = 0
        while offset < len(real_data):
            header = struct.unpack(">IHHII", real_data[offset:offset + 16]) # 解包每个分片的包头
            length = header[0]
            data_part = real_data[offset + 16:offset +length]
            # 消息类别判定
            if header[2] == PROTOCOL_VERSION['heartbeat']:
                if header[3] == MSG_TYPE['heartbeat']:
                    msg = {
                        'type': 'heartbeat',
                        'data': struct.unpack(">I", data_part)[0]
                    }
                elif header[3] == MSG_TYPE['welcome']:
                    msg = {
                        'type': 'welcome',
                        'data': json.loads(data_part.decode())
                    }
            elif header[2] == PROTOCOL_VERSION['raw']:
                msg = {
                    'type': 'data',
                    'data': json.loads(data_part.decode())
                }
            else:
                msg = {
                    'type': 'unknown',
                    'data': real_data
                }
            rst.append(msg)
            offset = offset + length # 获取下一个的起始位置
        return rst


