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
        self.clients_info = None
        self.client_conns = None
        self.mode = "Client-Server"  # or 'P2P' if you want to support peer-to-peer conference mode

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """

    async def log(self):
        while self.running:
            print("Something about server status")
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """

    def start(self):
        """
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        """


class MainServer:
    def __init__(self, server_ip, main_port):
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None
        self.client_counter = 1

        self.clients = []

        self.conference_conns = None
        self.conference_servers = (
            {}
        )  # self.conference_servers[conference_id] = ConferenceManager

    def handle_creat_conference(
        self,
    ):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """

    def handle_join_conference(self, conference_id):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """

    def handle_quit_conference(self):
        """
        quit conference (in-meeting request & or no need to request)
        """
        pass

    def handle_cancel_conference(self):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        pass

    async def request_handler(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        pass

    async def handle_data(self, reader, writer, data_type, client_id):
        """
        Continuously receive data from a client and broadcast it to others.
        """
        try:
            while True:
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

                    await self.broadcast("T", message_dict, writer, is_text=True)

                elif data_type in ("V", "A", "S"):
                    length_data = await reader.readexactly(4)
                    data_length = struct.unpack(">I", length_data)[0]

                    data = await reader.readexactly(data_length)
                    print(
                        f"Received {data_type} data of length {data_length} from client {client_id}."
                    )

                    await self.broadcast(data_type, data, writer, is_text=False)

                else:
                    print(f"Unsupported data type: {data_type}")
                    break
        except asyncio.IncompleteReadError:
            print(f"Client {client_id} disconnected during data transmission.")
        except Exception as e:
            print(f"Error handling data from client {client_id}: {e}")

    async def broadcast(self, data_type, payload, sender_writer, is_text=False):
        """
        Broadcast either text or binary data to all clients including the sender.
        'payload' is either a string (for text) or bytes (for binary data).
        'is_text' indicates whether payload should be treated as text (JSON) or raw bytes.
        """
        for reader, writer in self.clients:
            try:
                if is_text:
                    await self.send_framed_message(writer, data_type, payload)
                else:
                    length = struct.pack(">I", len(payload))  # 4 bytes
                    writer.write(data_type.encode("utf-8") + length + payload)
                    await writer.drain()
                print(f"Broadcasted {data_type} data to a client. ")
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
        client_id = self.client_counter
        self.client_counter += 1
        addr = writer.get_extra_info("peername")
        print(f"New connection from {addr}")

        self.clients.append((reader, writer))

        message_dict = {
            "client_id": 0,
            "timestamp": datetime.now().isoformat(),
            "message": f"Welcome to the conference server! Your client ID is {client_id}",
        }

        await self.send_framed_message(writer, "T", message_dict)

        while True:
            try:
                type_data = await reader.readexactly(1)
                data_type = type_data.decode("utf-8")
                print(f"Received data type: {data_type} from client {client_id}")

                await self.handle_data(reader, writer, data_type, client_id)
            except asyncio.IncompleteReadError:
                print(f"Client {client_id} disconnected.")
                break
            except Exception as e:
                print(f"Error with client {client_id}: {e}")
                break

        self.clients.remove((reader, writer))
        writer.close()
        await writer.wait_closed()
        print(f"Connection with client {client_id} closed.")


if __name__ == "__main__":
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    asyncio.run(server.start())
