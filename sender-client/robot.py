from WeChatPYAPI import WeChatPYApi
from datetime import datetime
from threading import Thread 
from queue import Queue
from time import sleep
import logging
import asyncio
import socket
import json
import time
import abc
import os


class Tweaker:
    def __init__(self):
        self.wechat = WeChatPYApi(
            msg_callback = self.on_message,
            exit_callback = self.on_exit,
            logger = logging
        )
        self.message_queue = Queue()

    def on_message(self, message):
        '''messages callback'''
        async def put_message():
            self.message_queue.put(message)
            logging.debug(f"Put {message} into queue.")
        asyncio.run(
            put_message()
        )

    def on_exit(self, event):
        '''exit event callback'''
        logging.info(f"{event['wx_id']} exit.")

    def start(self):
        '''start service'''
        try:
            self.wechat.start_wx()
        except Exception as e:
            logging.error(str(e))
        
        while not self.wechat.get_self_info():
            sleep(5)
        
        self.self_info = self.wechat.get_self_info()
        self.self_id = self.wechat.get_self_info()['wx_id']
        logging.info(f'Successfully logged in as {self.self_id}.')

class Client(Thread):
    def __init__(
        self,
        host: str,
        port: int,
        bufsize: int = 1024,
        name = 'Socket Thread'
    ):
        Thread.__init__(
            self,
            name = name
        )
        self.HOST = host
        self.PORT = port
        self.BUFSIZE = bufsize
        self.ADDRESS = (self.HOST, self.PORT)
        self.client_type = 'Sender'
        self.message_queue = Queue()
    
    def send_data(self, cmd, **kwargs):
        data = {}
        data['COMMAND'] = cmd
        data['client_type'] = self.client_type
        data['data'] = kwargs
        json_str = json.dumps(data)
        try:
            self.client.sendall(
                json_str.encode(
                    encoding = 'utf8'
                )
            )
            logging.debug(f'Sent: {json_str}')
        except Exception as e:
            logging.error(str(e))
    
    
    def run(self):
        self.client = socket.socket()
        self.client.connect(self.ADDRESS)
        logging.debug(f'Successfully connected to {self.ADDRESS}')
        logging.info(
            msg = self.client.recv(self.BUFSIZE).decode(
                encoding='utf8'
            )
        )
        self.send_data(cmd = 'CONNECT')
        
        last_time = time.time()
        while True:
            if int(time.time() - last_time) > 20:
                last_time = time.time()
                self.send_data(
                    cmd = 'HEART_BEAT',
                    data = 'I am ok yoo'
                )
            while self.message_queue.qsize() > 0:
                msg = self.message_queue.get()
                if msg == '/shutdown':
                    logging.info(msg = 'Socket service shutdown...')
                    self.client.close()
                    return
                self.send_data(
                    cmd = 'SEND_DATA',
                    data = msg
                )

class Command(metaclass = abc.ABCMeta):
    def __init__(
        self,
        tweaker: Tweaker,
        operation: str,
        target: str,
        args_len: int = 0
    ):
        self.tweaker = tweaker
        self.operation = operation
        self.target = target
        self.args_len = args_len
        self.warning_text = ''

    @abc.abstractclassmethod
    def execute(self, *args):
        pass
    
    def warning(self, *args):
        if len(args) > self.args_len:
            self.tweaker.wechat.send_text(
                self_wx = self.tweaker.self_id,
                to_wx = self.target,
                msg = f'请按 {self.warning_text} 格式输入！'
            )
            return

class ReplayCommand(Command):
    def __init__(self, tweaker, target):
        super(ReplayCommand, self).__init__(
            tweaker = tweaker,
            operation = '获取回放',
            target = target,
            args_len = 1
        )
        self.warning_text = '/获取回放 [篇回一/篇回二/...]'
    
    def execute(self, *args):
        self.warning(args)
        
        with open("./config.json", "r", encoding='utf8') as config:
            json_data = json.load(config)
        title = ''
        try:
            if not args:
                title = "回放频道"
            else:
                title = args[0]
                self.tweaker.wechat.send_text(
                    self_wx = self.tweaker.self_id,
                    to_wx = self.target,
                    msg = '''密码:%s''' % (json_data["replay"][title]["password"])
                )
            self.tweaker.wechat.send_text(
                    self_wx = self.tweaker.self_id,
                    to_wx = self.target,
                    msg = '''%s:%s''' % (title, json_data["replay"][title]["url"])
                )
        except KeyError as ie:
            logging.error(str(ie))
            self.tweaker.wechat.send_text(
                    self_wx = self.tweaker.self_id,
                    to_wx = self.target,
                    msg = ("暂时没有此篇回:(")
                )

class HelpCommand(Command):
    def __init__(self, tweaker, target):
        super(HelpCommand, self).__init__(
            tweaker = tweaker,
            operation = '帮助',
            target = target,
            args_len = 0
        )
    
    def execute(self, *args):
        self.tweaker.wechat.send_text(
            self_wx = self.tweaker.self_id,
            to_wx = self.target,
            msg = 
'''
1./帮助 获取所有指令

2./获取回放 [篇回一/篇回二/...] 获取回放链接和密码

3./上课提醒 [打开/关闭] 打开后上课前10分钟会提醒您

4./预习文档 [all/day1/day2/...] 会将课程文档私发给您

5./获取作业 [all/day1/day2/...] 会将作业文档私发给您
'''
        )

class ReminderCommand(Command):
    def __init__(self, tweaker, target):
        super(ReminderCommand, self).__init__(
            tweaker = tweaker,
            operation = '上课提醒',
            target = target,
            args_len = 2
        )
        self.warning_text = '/上课提醒 [打开/关闭]'

    def execute(self, *args):
        self.warning()
        
        with open("./config.json", "r", encoding='utf8') as configfile:
            config = json.load(configfile)
        on_enable = True if args[0] == '打开' else False
        sender = args[1]
        config['reminder'][sender] = on_enable
        
        with open("./config.json", "w", encoding='utf8') as configfile:
            json_str = json.dumps(config)
            configfile.write(json_str)

        try:
            self.tweaker.wechat.send_text(
                self_wx = self.tweaker.self_id,
                to_wx = sender,
                msg = f'已{args[0]}您的上课提醒。'
            )
        except Exception as e:
            logging.error(str(e))
        

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO)

def is_admin(cur_id, admin_id):
    return cur_id == admin_id

def is_that_group(cur_id, group_id):
    return cur_id == group_id

async def reminder(tweaker: Tweaker):
    now = datetime.now().strftime('%H:%M:%S')
    if now == '15:30:00':
        with open('./config.json', 'r', encoding='utf8') as configfile:
            namelist = json.load(configfile)['reminder']
        for name in namelist:
            if not namelist[name]:
                continue
            tweaker.wechat.send_text(
                self_wx = tweaker.self_id,
                to_wx = name,
                msg = '还有10分钟就要上课咯，请前往神秘组织等待直播吧'
            )
        await asyncio.sleep(1)

def main():
    with open('./config.json', 'r', encoding='utf8') as config_file:
        config = json.load(config_file)
    
    group_id = config['group_id']
    admin_id = config['admin_id']
    
    tweaker = Tweaker()
    tweaker.start()
    
    socket_thread = Client(
        host = config['server']['host'],
        port = config['server']['port']
    )
    socket_thread.start()
    
    commands = {
        '获取回放':ReplayCommand,
        '帮助':HelpCommand,
        '上课提醒':ReminderCommand
    }
    
    while True:
        asyncio.run(reminder(tweaker))
        while tweaker.message_queue.qsize() > 0:
            msg = tweaker.message_queue.get()
            msg_start_with = msg['content'][0]
            if is_that_group(msg['wx_id'], group_id) and msg['msg_type'] == 1:
                if msg_start_with == '问':
                    socket_thread.message_queue.put(
                        item = msg['content'][1:]
                    )

                if msg_start_with == '/':
                    cmd = msg['content'][1:].split()
                    operation = cmd[0]
                    args = ()
                    if len(cmd) > 1:
                        for i in range(1, len(cmd)):
                            args += (cmd[i],)
                    if operation == '上课提醒':
                        args += (msg['sender'],)
                    try:
                        commands[operation](
                            tweaker,
                            group_id
                        ).execute(*args)

                    except KeyError as ie:
                        logging.error(str(ie))
                        tweaker.wechat.send_text(
                            self_wx = tweaker.self_id,
                            to_wx = group_id,
                            msg = '未知指令，请输入 /帮助 获取帮助，或者联系我:)'
                        )

if '__main__' == __name__:
    main()
