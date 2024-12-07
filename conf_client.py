# from util import *
from socket import *

from pyexpat.errors import messages

from config import *

class ConferenceClient:
    def __init__(self,):
        # sync client
        self.is_working = True
        self.server_addr = (SERVER_IP,MAIN_SERVER_PORT)  # server addr ，在config.py里设置服务器IP
        self.on_meeting = False  # status
        self.conns = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}
        self.conference_info = None  # you may need to save and update some conference_info regularly
        self.recv_data = None  # you may need to save received streamd data from other clients in conference
        self.conference_id = 0
        self.user_id = 0 #用于在服务器中确定用户，由服务器从1开始分配
        self.conference_socket = None
        #与Main Server建立TCP连接
        self.client_socket = socket(AF_INET, SOCK_STREAM) #创建基于网络（ipv4)的TCP套接字
        self.client_socket.connect(self.server_addr) #用该套接字与服务器地址连接
        self.user_id = self.client_socket.recv(1024).decode()
        self.is_owner = False
        print(f'You are user {self.user_id}')
        # self.client_socket.send("connect successfully".encode())
        # print(self.client_socket.recv(1024).decode())
    def create_conference(self):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        #可能需要加一个if条件（是否要求Free状态才能创建）
        self.client_socket.send('create'.encode())#发送请求
        data = self.client_socket.recv(1024).decode()#得到编号，端口号为50000+data
        print(f'Your conference id is {data}')
        self.conference_id = data
        self.conference_socket = socket(AF_INET,SOCK_STREAM)#与会议服务器建立TCP
        port = 50000+int(data)
        self.conference_socket.connect((SERVER_IP,port))
        self.conference_socket.send(str(self.user_id).encode())#向会议室发送自己的编号
        self.is_owner = True # 是房间的创建者，用于判断有没有cancel的权力
        self.on_meeting = True

        pass

    def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        data_send = 'join'+' '+ conference_id
        self.client_socket.send(data_send.encode())
        data = self.client_socket.recv(1024).decode()
        if data == 'True':
            self.conference_id = conference_id
            self.conference_socket = socket(AF_INET, SOCK_STREAM)  # 与会议服务器建立TCP
            port = 50000 + int(conference_id)
            self.conference_socket.connect((SERVER_IP, port))
            self.conference_socket.send(str(self.user_id).encode())
            self.on_meeting = True
            print(f'Join conference {conference_id} successfully')
        else:
            print(f"There is no conference {conference_id}")
        pass

    def quit_conference(self):
        """
        quit your on-going conference
        """
        self.client_socket.send('quit'.encode())#告知主服务器要退出
        # self.client_socket.send(str(self.conference_id).encode())
        self.conference_socket.send('quit'.encode())
        self.conference_socket.send(str(self.conference_id).encode())
        self.conference_socket.close()
        self.conference_id = 0
        self.on_meeting = False
        print('quit')
        pass

    def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        self.client_socket.send('cancel'.encode())
        self.client_socket.send(str(self.conference_id).encode())# 发送会议编号给主服务器，使其释放端口
        self.conference_socket.send('cancel'.encode())
        self.is_owner = False
        try:
            data = self.conference_socket.recv(1024)
            message = data.decode()
            print(message)
        except Exception:
            print('Error')
        pass

    def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        pass

    def share_switch(self, data_type):
        '''
        switch for sharing certain type of data (screen, camera, audio, etc.)
        '''
        pass

    def keep_recv(self, recv_conn, data_type, decompress=None):
        '''
        running task: keep receiving certain type of data (save or output)
        you can create other functions for receiving various kinds of data
        '''

    def output_data(self):
        '''
        running task: output received stream data
        '''

    def start_conference(self):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''

    def close_conference(self):
        '''
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        '''

    def list_conference(self):
        self.client_socket.send('list'.encode())
        stop = False
        while not stop:
            conference = self.client_socket.recv(1024).decode()
            if conference.endswith("stop"):
                stop = True
                conference = conference.replace("stop", '')
            print(conference,end='')

    def start(self):
        """
        execute functions based on the command line input
        """
        while True:
            if not self.on_meeting:
                status = 'Free'
            else:
                status = f'OnMeeting-{self.conference_id}'
            recognized = True
            cmd_input = input(f'({status}) Please enter a operation (enter "?" to help): ').strip().lower()
            fields = cmd_input.split(maxsplit=1)
            if len(fields) == 1:
                if cmd_input in ('?', '？'):
                    print(HELP)
                elif cmd_input == 'create':
                    if not self.on_meeting:
                        self.create_conference()
                    else : print('You are in a conference')
                elif cmd_input == 'quit':
                    if self.on_meeting:
                        self.quit_conference()
                    else: print('You are not in any conference')
                elif cmd_input == 'cancel':
                    if self.is_owner:
                        self.cancel_conference()
                    else: print("You cannot cancel the conference")
                elif cmd_input == 'list':
                    self.list_conference()
                elif cmd_input == 'ping':#测试连接
                    self.conference_socket.send('ping'.encode())
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == 'join':
                    if self.on_meeting:
                        print('You are in a conference')
                    else:
                        input_conf_id = fields[1]
                        if input_conf_id.isdigit():
                            self.join_conference(input_conf_id)
                        else:
                            print('[Warn]: Input conference ID must be in digital form')
                elif fields[0] == 'switch':
                    data_type = fields[1]
                    if data_type in self.share_data.keys():
                        self.share_switch(data_type)
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f'[Warn]: Unrecognized cmd_input {cmd_input}')


if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.start()

