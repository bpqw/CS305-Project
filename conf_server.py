import asyncio
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

    async def handle_data(self, reader, writer, data_type):
        """
        Receive sharing stream data from a client and decide how to forward them to the rest of the clients.
        """
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break

                if data_type == "video":
                    print(
                        f"Received video data from {writer.get_extra_info('peername')}"
                    )
                    await self.broadcast_data(data, writer)
                elif data_type == "audio":
                    print(
                        f"Received audio data from {writer.get_extra_info('peername')}"
                    )
                    await self.broadcast_data(data, writer)
                elif data_type == "screen":
                    print(
                        f"Received screen data from {writer.get_extra_info('peername')}"
                    )
                    await self.broadcast_data(data, writer)
                else:
                    print("[Error]: Unsupported data type")
                    break
        except Exception as e:
            print(f"Error handling {data_type} data: {e}")

    async def broadcast_data(self, data, sender_writer):
        """
        Broadcast data to all clients except the sender.
        """
        for reader, writer in self.clients:
            if writer != sender_writer:
                try:
                    writer.write(data)
                    await writer.drain()
                except Exception as e:
                    print(f"Error broadcasting data: {e}")

    async def broadcast_message(self, message, sender_writer):
        """Send a message to all connected clients."""
        for reader, writer in self.clients:
            if writer != sender_writer:
                try:
                    writer.write(f"Broadcast: {message}".encode("utf-8"))
                    await writer.drain()
                except Exception as e:
                    print(f"Error broadcasting message: {e}")

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
        """Handle incoming client requests."""
        client_id = self.client_counter
        self.client_counter += 1
        addr = writer.get_extra_info("peername")
        print(f"New connection from {addr}")

        self.clients.append((reader, writer))

        writer.write(
            f"Welcome to the conference server! Your client ID is {client_id} ".encode()
        )
        await writer.drain()

        while True:
            data = await reader.read(1024)
            if not data:
                print(f"Client {client_id} disconnected.")
                break

            message = data.decode("utf-8")
            print(f"Received message from client {client_id}: {message}")
            # timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # message_with_metadata = f"[{client_id} | {timestamp}] {message}"

            if (
                message.startswith("camera")
                or message.startswith("audio")
                or message.startswith("screen")
            ):
                data_type = message.split()[0]
                await self.handle_data(reader, writer, data_type)
            else:
                await self.broadcast_message(message, writer)


if __name__ == "__main__":
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    asyncio.run(server.start())
