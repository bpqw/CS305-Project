import asyncio
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
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceServer
        self.conference_counter = 1
        self.clients = {} #用字典存方便移除
        self.clients_counter = 1

    async def handle_create_conference(self,writer):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        new_conference_server = ConferenceServer()#新建会议
        new_conference_server.conference_id = self.conference_counter
        self.conference_servers[new_conference_server.conference_id] = new_conference_server#更新会议列表

        new_conference_server.conf_serve_ports = 50000+self.conference_counter
        conference_id = f"Your conference ID is {self.conference_counter}"
        self.conference_counter += 1
        writer.write(conference_id.encode())  # 将会议编号发回给创建者，使之与会议建立连接
        asyncio.create_task(new_conference_server.start())#初始化会议，使之开始监听客户端加入申请，实现多个用户同时可以加入会议


    async def handle_join_conference(self, conference_id,writer):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        conference_id = int(conference_id)
        if conference_id in self.conference_servers:
            writer.write(f'Successfully join conference {conference_id}'.encode())
        else : writer.write(f'There is no conference {conference_id}'.encode())


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

    async def handle_list_conference(self,writer):
        a = 'List: '
        for i in self.conference_servers:
            a += 'conference ' + str(i) + '\n'
        writer.write(a.encode())
        await writer.drain()
        pass

    async def handle_client(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        client_id = self.clients_counter
        self.clients_counter += 1
        addr = writer.get_extra_info('peername')
        self.clients[client_id] = (reader,writer)
        message = f"Your client ID is {client_id}"
        writer.write(message.encode())#发送用户编号
        await writer.drain()
        print(f"connect with user{client_id}{addr} ")
        while True:
            data = await asyncio.wait_for(reader.read(1024),None)
            if not data:
                print(f'disconnected with {addr}')
                self.clients.pop(client_id)
                writer.close()
                await writer.wait_closed()
                return
            if not writer:
                print('writer error')
            whole_message = data.decode()
            print(whole_message)
            command = whole_message.split('] ')[1]
            field = command.split()
            if len(field) == 1:
                if command == 'create':
                    await self.handle_create_conference(writer)
                elif command == 'quit':
                    await self.handle_quit_conference(reader)
                elif command == 'cancel':
                    await self.handle_cancel_conference(reader, writer)
                elif command == 'list':
                    await self.handle_list_conference(writer)
                else:
                    writer.write('wrong command'.encode())
            elif len(field) == 2:
                if field[0] == 'join':
                    await self.handle_join_conference(field[1],writer)
                elif field[0] == 'switch':
                    await self.handle_join_conference(field[1],writer)
                else:
                    writer.write('wrong command'.encode())
            else: print('error')
        pass

    async def start(self):
        """
        start MainServer
        """
        self.server = await asyncio.start_server(self.handle_client, SERVER_IP, MAIN_SERVER_PORT)#创建并行服务器
        addr = self.server.sockets[0].getsockname()
        print(f"Server started, listening {addr}")
        async with self.server:
            await self.server.serve_forever()#实现多个客户端同时操作
        pass


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    asyncio.run(server.start())
    #server.start()
