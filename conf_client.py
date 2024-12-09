# from util import *
from socket import *
from config import *
import asyncio
import datetime
import aioconsole
import time

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
        self.conference_id = 0 #所在会议的编号
        self.client_id = 0 #用于在服务器中确定用户，由服务器从1开始分配
        # self.conference_socket = None
        self.is_owner = False #是否是会议创建者
        self.message_queue = asyncio.Queue()
        self.reader = None #对Main Server的接收端
        self.writer = None #对Main Server的发送端
        self.meet_reader = None
        self.meet_writer = None



    async def create_conference(self,conference_id):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        conference_port = int(conference_id) + 50000
        try:
            self.meet_reader, self.meet_writer = await asyncio.open_connection(self.server_addr[0], conference_port)
            print(f"Connected to conference {conference_id} at {self.server_addr[0]}:{conference_port}")
            self.is_owner = True  # 是房间的创建者，用于判断有没有cancel的权力
            self.on_meeting = True
            # await self.writer.drain()
        except Exception as e:
            print(f"Failed to connect to conference {conference_id}: {e}")
            return False
        return True
        pass

    async def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        conference_port = int(conference_id) + 50000
        try:
            self.meet_reader, self.meet_writer = await asyncio.open_connection(self.server_addr[0], conference_port)
            print(f"Connected to conference {conference_id} at {self.server_addr[0]}:{conference_port}")
            self.on_meeting = True
        except Exception as e:
            print(f"Failed to connect to conference {conference_id}: {e}")
            return False
        return True
        pass

    async def quit_conference(self):
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

    async def cancel_conference(self):
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

    async def send_message(self, message):
        """Send a message to the server."""
        if not self.writer:
            print("[Error]: Not connected to server!")
            return
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_with_metadata = f"[{self.client_id} | {timestamp}] {message}"
        self.writer.write(message_with_metadata.encode())
        # await self.writer.drain()

    async def receive_message(self):
        """Receive messages from the server."""
        if not self.reader:
            print("[Error]: Not connected to server!")
            return
        while True:
            data = await asyncio.wait_for(self.reader.read(1024), None)
            if data:
                # print(f"[DEBUG]: Received from server: {data.decode()}")
                await self.message_queue.put(data.decode())
                # Extract the client ID from the welcome message
                if "Your client ID is" in data.decode():
                    #连接到主服务器
                    self.client_id = (
                        data.decode().split("Your client ID is ")[1].strip()
                    )
                    print(f"[INFO]: Client ID set to {self.client_id}")
                elif "Your conference ID is" in data.decode():
                    #create
                    self.conference_id = (
                        data.decode().split("Your conference ID is ")[1].strip()
                    )
                    print(f"[INFO]: Create Conference {self.client_id}")
                    await self.create_conference(self.conference_id)
                elif "Successfully join conference " in data.decode():
                    #join
                    self.conference_id = (
                        data.decode().split('Successfully join conference ')[1].strip()
                    )
                    print(f"[INFO]: Join Conference {self.client_id}")
                    await self.join_conference(self.conference_id)
                elif 'There is no conference ' in data.decode():
                    #join fail
                    print('Please choose another conference')
                elif 'List: ' in data.decode():
                    conference = (
                        data.decode().split('List: ')[1].strip()
                    )
                    await self.list_conference(conference)
                else: print('Message error')
            else:
                print("[Error]: No response from server.")
                break
            await asyncio.sleep(0.1)

    async def send_to_conference(self, message):
        """Send a message to the server."""
        if not self.meet_writer:
            print("[Error]: Not connected to conference!")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message_with_metadata = f"[{self.client_id} | {timestamp}] {message}"

        self.writer.write(message_with_metadata.encode())
        await self.writer.drain()

    async def list_conference(self,conference):
        """list all the conferences"""
        print(conference)
        # stop = False
        # while not stop:
            # conference = self.client_socket.recv(1024).decode()
        #     if conference.endswith("stop"):
        #         stop = True
        #         conference = conference.replace("stop", '')
        #     print(conference,end='')

    async def connect_to_server(self):
        """Connect to the server using asyncio."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.server_addr[0],self.server_addr[1])
            print(f"Connected to server at {self.server_addr[0]}:{self.server_addr[1]}")
            await self.writer.drain()
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
        return True

    async def receive_command(self):
        while True:
            await asyncio.sleep(0.3)
            if not self.on_meeting:
                status = 'Free'
            else:
                status = f'OnMeeting-{self.conference_id}'
            recognized = True
            cmd_input = await aioconsole.ainput(f'({status}) Please enter a operation (enter "?" to help): ')
            cmd_input = cmd_input.strip().lower()
            fields = cmd_input.split(maxsplit=1)
            if len(fields) == 1:
                if cmd_input in ('?', '？'):
                    print(HELP)
                elif cmd_input == 'create':
                    if not self.on_meeting:
                        await self.send_message('create')
                    else:
                        print('You are in a conference')
                elif cmd_input == 'quit':
                    if self.on_meeting:
                        self.quit_conference()
                    else:
                        print('You are not in any conference')
                elif cmd_input == 'cancel':
                    if self.is_owner:
                        self.cancel_conference()
                    else:
                        print("You cannot cancel the conference")
                elif cmd_input == 'list':
                    await self.send_message('list')
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == 'join':
                    if self.on_meeting:
                        print('You are already in a conference')
                    else:
                        input_conf_id = fields[1]
                        if input_conf_id.isdigit():
                            await self.send_message(f'join {input_conf_id}')
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


    async def start(self):
        """
        execute functions based on the command line input
        """
        connected = await self.connect_to_server()
        if not connected:
            return
        await asyncio.gather(self.receive_message(),self.receive_command())



if __name__ == '__main__':
    client1 = ConferenceClient()
    asyncio.run(client1.start())

