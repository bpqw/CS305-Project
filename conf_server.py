import asyncio
from datetime import datetime
import json
import struct
from util import *


class ConferenceServer:
    def __init__(
        self,
    ):
        # async server
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = [
            "screen",
            "camera",
            "audio",
        ]  # example data types in a video conference
        self.clients_info = {}  # clients_info[user_id] = addr
        self.clients_conns = {}  #:dict[int,(reader,writer)
        self.mode = "Client-Server"  # or 'P2P' if you want to support peer-to-peer conference mode
        self.owner_id = 0  # 会议创建者的编号
        self.conf = None  # 异步服务器管理器，用来关闭会议

    async def handle_data(self, reader, writer, client_id):
        """
        Continuously receive data from a client and broadcast it to others.
        """
        try:
            while True:
                type_data = await reader.readexactly(1)
                if not type_data:
                    print(f"disconnect with {client_id}")
                    break
                data_type = type_data.decode("utf-8")
                if data_type == "T":
                    length_data = await reader.readexactly(4)
                    message_length = struct.unpack(">I", length_data)[0]
                    message_data = await reader.readexactly(message_length)
                    message = message_data.decode("utf-8")
                    print(f"Received text from client {client_id}: {message}")
                    message_dict = {
                        "client_id": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "message": message,
                    }
                    message_data = json.loads(message)
                    actual_message = message_data.get("message", "").strip()
                    if actual_message == "cancel":
                        await self.cancel_conference()
                        return
                    await self.broadcast("T", message_dict, writer, is_text=True)

                elif data_type in ("V", "A", "S"):
                    length_data = await reader.readexactly(4)
                    data_length = struct.unpack(">I", length_data)[0]

                    data = await reader.readexactly(data_length)
                    # print(
                    #     f"Received {data_type} data of length {data_length} from client {client_id}."
                    # )

                    await self.broadcast(data_type, data, writer, is_text=False)

                else:
                    print(f"Unsupported data type: {data_type}")
                    break
        except asyncio.IncompleteReadError:
            print(f"Client {client_id} disconnected during data transmission.")
        except Exception as e:
            print(f"Error handling data from client {client_id}: {e}")

    async def handle_client(self, reader, writer):  # 每一次客户端加入会议后调用本函数
        """
        running task: handle the in-meeting requests or messages from clients
        """
        addr = writer.get_extra_info("peername")  # 获取客户端地址
        user_id = await asyncio.wait_for(reader.read(1024), None)  # 接收客户端编号
        user_id = user_id.decode()
        if self.clients_info == {}:
            print(f"user{user_id}{addr} creates conference {self.conference_id}")
            self.clients_info[user_id] = addr
            self.clients_conns[user_id] = (reader, writer)
            self.owner_id = user_id
        else:
            print(f"user{user_id}{addr} joins conference {self.conference_id}")
        self.clients_info[user_id] = addr
        self.clients_conns[user_id] = (reader, writer)
        message_dict = {
            "client_id": 0,
            "timestamp": datetime.now().isoformat(),
            "message": f"Welcome to the conference server! User {user_id}",
        }
        await self.send_framed_message(writer, "T", message_dict)

        asyncio.create_task(self.handle_data(reader, writer, user_id))

    async def broadcast(self, data_type, payload, sender_writer, is_text=False):
        """
        Broadcast either text or binary data to all clients including the sender.
        'payload' is either a string (for text) or bytes (for binary data).
        'is_text' indicates whether payload should be treated as text (JSON) or raw bytes.
        """
        tasks = []
        for client in self.clients_conns:
            writer = self.clients_conns[client][1]
            if data_type == "A" and writer == sender_writer:
                continue
            task = asyncio.create_task(
                self.one_of_broadcast(writer, data_type, payload, is_text)
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def one_of_broadcast(self, writer, data_type, payload, is_text):
        try:
            if is_text:
                await self.send_framed_message(writer, data_type, payload)
            else:
                length = struct.pack(">I", len(payload))  # 4 bytes
                writer.write(data_type.encode("utf-8") + length + payload)
                await writer.drain()
            # print(f"Broadcasted {data_type} data to a client.")
        except Exception as e:
            print(f"Error broadcasting {data_type} data: {e}")

    async def send_framed_message(self, writer, data_type, message_dict):
        """
        Send a framed JSON message to a client.
        """
        try:
            json_message = json.dumps(message_dict)
            json_message_bytes = json_message.encode("utf-8")
            data_type_byte = data_type.encode("utf-8")  # 1 byte
            length = struct.pack(">I", len(json_message_bytes))  # 4 bytes
            writer.write(data_type_byte + length + json_message_bytes)
            await writer.drain()
            print(f"Sent {data_type} message to client.")
        except Exception as e:
            print(f"Error sending message: {e}")

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        if self.conf:
            print(f"[INFO]: Cancel the conference {self.conference_id}")
            self.conf.close()
            await self.conf.wait_closed()
            for user_id, (reader, writer) in list(self.clients_conns.items()):
                try:
                    writer.close()
                    await writer.wait_closed()
                    print(f"[INFO]: Disconnected client {user_id}")
                except Exception as e:
                    print(f"[ERROR]: Error disconnecting client {user_id}: {e}")
            self.clients_conns.clear()
            self.clients_info.clear()
            print("[INFO]: Conference shutdown complete")

    async def start(self):
        """
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        """
        self.conf = await asyncio.start_server(
            self.handle_client, SERVER_IP, self.conf_serve_ports
        )  # 以会议服务器的地址和端口创建并行服务器
        async with self.conf:
            await self.conf.serve_forever()


class MainServer:
    def __init__(self, server_ip, main_port):
        self.server_ip = server_ip
        self.server_port = main_port
        self.clients_counter = 1
        self.clients = {}  # 通过字典方式储存对应的连接的客户端的reader和writer
        self.conference_counter = 1
        self.conference_conns = None
        self.conference_servers = (
            {}
        )  # self.conference_servers[conference_id] = ConferenceManager
        self.main_server = None  # 目前看不出来有什么用

    async def handle_create_conference(self, writer):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        new_conference_server = ConferenceServer()  # 新建会议
        new_conference_server.conference_id = self.conference_counter
        self.conference_servers[new_conference_server.conference_id] = (
            new_conference_server  # 更新会议列表
        )
        new_conference_server.conf_serve_ports = 50000 + self.conference_counter
        conference_id = f"You create conference {self.conference_counter}"
        self.conference_counter += 1
        writer.write(
            conference_id.encode()
        )  # 将会议编号发回给创建者，使之与会议建立连接
        asyncio.create_task(
            new_conference_server.start()
        )  # 初始化会议，使之开始监听客户端加入申请，实现多个用户同时可以加入会议

    async def handle_join_conference(self, conference_id, writer):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        conference_id = int(conference_id)
        if conference_id in self.conference_servers:
            writer.write(f"Successfully join conference {conference_id}".encode())
        else:
            writer.write(f"There is no conference {conference_id}".encode())

    async def handle_quit_conference(self, writer):
        """
        quit conference (in-meeting request & or no need to request)
        """
        writer.write("You will quit the conference".encode())
        pass

    async def handle_cancel_conference(
        self, conference_id, writer
    ):  # 从会议列表去除取消的会议
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        conference_id = int(conference_id)
        try:
            self.conference_servers.pop(conference_id)
            print("[INFO]: Server shutdown complete.")
            writer.write("Cancel successfully".encode())
        except Exception as e:
            print(f"Fail to cancel because {e}")

    async def handle_list_conference(self, writer):
        a = "List: "
        for i in self.conference_servers:
            a += "conference " + str(i) + "\n"
        writer.write(a.encode())
        await writer.drain()

    async def start(self):
        """
        start MainServer
        """
        server = await asyncio.start_server(
            self.handle_client, self.server_ip, self.server_port
        )

        addr = server.sockets[0].getsockname()
        print(f"Server started on {addr}")

        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        # 每次有客户端申请连接服务器时进入该函数
        client_id = self.clients_counter
        self.clients_counter += 1
        addr = writer.get_extra_info("peername")
        self.clients[client_id] = (reader, writer)
        message = f"Your client ID is {client_id}"
        writer.write(message.encode())  # 发送用户编号
        await writer.drain()
        print(f"connect with user{client_id}{addr} ")
        while True:
            data = await asyncio.wait_for(reader.read(1024), None)
            if not data:
                print(f"disconnected with {addr}")
                self.clients.pop(client_id)
                writer.close()
                await writer.wait_closed()
                return
            if not writer:
                print("writer error")
            whole_message = data.decode()
            print(whole_message)
            command = whole_message.split("] ")[1]
            field = command.split()
            if len(field) == 1:
                if command == "create":
                    await self.handle_create_conference(writer)
                elif command == "quit":
                    await self.handle_quit_conference(writer)
                elif command == "list":
                    await self.handle_list_conference(writer)
                else:
                    writer.write("wrong command".encode())
            elif len(field) == 2:
                if field[0] == "join":
                    await self.handle_join_conference(field[1], writer)
                elif field[0] == "cancel":
                    await self.handle_cancel_conference(field[1], writer)
                else:
                    writer.write("wrong command".encode())
            else:
                print("error")


if __name__ == "__main__":
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    asyncio.run(server.start())
