import asyncio
from os import write

# from util import *
from config import *


class ConferenceServer:
    def __init__(self, ):
        # async server
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = {}#clients_info[user_id] = addr
        self.client_conns = {}#:dict[int,(reader,writer)]
        self.owner_id = 0# 会议创建者的编号
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.conf = None #异步服务器管理器，用来关闭会议

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """


    async def handle_client(self, reader, writer):#每一次客户端加入会议后调用本函数
        """
        running task: handle the in-meeting requests or messages from clients
        """
        addr = writer.get_extra_info('peername')#获取客户端地址
        user_id = await asyncio.wait_for(reader.read(1024), None)#接收客户端编号
        user_id = user_id.decode()
        if self.clients_info == {}:
            print(f'user{user_id}{addr} creates conference {self.conference_id}')
            self.clients_info[user_id] = addr
            self.client_conns[user_id] = (reader,writer)
            self.owner_id = user_id
        else:
            print(f'user{user_id}{addr} joins conference {self.conference_id}')
        self.clients_info[user_id] = addr
        self.client_conns[user_id] = (reader,writer)
        while True:
            try:
                data = await asyncio.wait_for(reader.read(1024), None)
                message = data.decode()
                if message == 'quit':
                    print('quit')
                    return
                elif message == 'ping': print('ok')
                elif message == 'cancel':
                    if user_id == self.owner_id:
                        await self.cancel_conference()
                    else:
                        writer.write('You cannot cancel the conference'.encode())

            except Exception:
                print('Error on Server')

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)


    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        for user_id,(reader,writer) in list(self.client_conns.items()):
            try:
                writer.close()
                await writer.wait_closed()
                reader.feed_eof()
            except Exception as e:
                print(f"Error closing connection for user {user_id}: {e}")
        self.conf.close()





    async def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''
        self.conf = await asyncio.start_server(self.handle_client, SERVER_IP,self.conf_serve_ports)#以会议服务器的地址和端口创建并行服务器
        async with self.conf:
            await self.conf.serve_forever()


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None
        self.conference_conns = None
        self.conference_servers:dict[int,ConferenceServer] = {}  # self.conference_servers[conference_id] = ConferenceServer
        self.users = {}#按连接顺序分配用户id user1， user2 ...

    async def handle_create_conference(self,writer):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        i = 1
        while i in self.conference_servers:#从1开始，查询未使用的编号
            i += 1
        new_conference_server = ConferenceServer()#新建会议
        self.conference_servers[i] = new_conference_server#更新会议列表
        new_conference_server.conference_id = i
        new_conference_server.conf_serve_ports = 50000+i
        id = str(i)
        writer.write(id.encode())#将会议编号发回给创建者，使之与会议建立连接
        await asyncio.create_task(new_conference_server.start())#初始化会议，使之开始监听客户端加入申请，实现多个用户同时可以创建会议

    async def handle_join_conference(self, conference_id,writer):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        conference_id = int(conference_id)
        if conference_id in self.conference_servers:
            writer.write('True'.encode())
        else : writer.write('False'.encode())


    async def handle_quit_conference(self,reader):
        """
        quit conference (in-meeting request & or no need to request)
        """
        #没用上，可能后续为提高安全性补全
        pass

    async def handle_cancel_conference(self,reader,writer):#从会议列表去除取消的会议
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        try:
            conference_id = await asyncio.wait_for(reader.read(1024), None)
            conference_id = conference_id.decode()
            self.conference_servers.pop(conference_id)
            writer.write('Cancel successfully'.encode())
        except Exception as e:
            print(f'Fail to cancel because {e}')
        pass

    async def list_conference(self,writer):
        for i in self.conference_servers:
            a = 'conference' + ' ' + str(i) + '\n'
            writer.write(a.encode())
        # await asyncio.sleep(0.01)#防止stop和会议同时被接受，造成误读
        writer.write('stop'.encode())
        pass

    async def request_handler(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        addr = writer.get_extra_info('peername')
        i = 1
        while i in self.users:
            i += 1
        self.users[i] = addr
        writer.write(str(i).encode())#发送用户编号
        print(f"connect with user{i}({addr}) ")
        while True:
            data = await asyncio.wait_for(reader.read(1024),None)
            if not data:
                print(f'disconnected with {addr}')
                self.users.pop(i)
                # writer.close()
                # await writer.wait_closed()
                return
            message = data.decode()
            field = message.split()
            if len(field) == 1:
                if message == 'create':
                    asyncio.create_task(self.handle_create_conference(writer))
                elif message == 'quit':
                    asyncio.create_task(self.handle_quit_conference(reader))
                elif message == 'cancel':
                    asyncio.create_task(self.handle_cancel_conference(reader,writer))
                elif message == 'list':
                    asyncio.create_task(self.list_conference(writer))
                else:
                    writer.write('wrong command'.encode())
            elif len(field) == 2:
                if field[0] == 'join':
                    asyncio.create_task(self.handle_join_conference(field[1],writer))
                elif field[0] == 'switch':
                    asyncio.create_task(self.handle_join_conference(field[1],writer))
                else:
                    writer.write('wrong command'.encode())
        pass

    async def start(self):
        """
        start MainServer
        """
        server = await asyncio.start_server(self.request_handler, SERVER_IP, MAIN_SERVER_PORT)#创建并行服务器
        addr = server.sockets[0].getsockname()
        print(f"Server started, listening {addr}")
        async with server:
            await server.serve_forever()#实现多个客户端同时操作
        pass


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    asyncio.run(server.start())
    #server.start()
