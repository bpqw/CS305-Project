import asyncio
import datetime
import time
from util import *


class ConferenceClient:
    def __init__(
        self,
    ):
        # sync client
        self.is_working = True
        self.server_addr = SERVER_IP  # server addr
        self.server_port = MAIN_SERVER_PORT  # server port
        self.client_id = None  # client id
        self.on_meeting = False  # status
        self.conns = (
            None  # you may need to maintain multiple conns for a single conference
        )
        self.support_data_types = []  # for some types of data
        self.share_data = {}

        self.conference_info = (
            None  # you may need to save and update some conference_info regularly
        )

        self.recv_data = None  # you may need to save received streamd data from other clients in conference

        self.message_queue = asyncio.Queue()
        self.camera_on = False

    def start_conference(self):
        """
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        """

    def close_conference(self):
        """
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        """

    def create_conference(self):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        pass

    def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        pass

    def quit_conference(self):
        """
        quit your on-going conference
        """
        pass

    def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        pass

    async def keep_share(
        self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30
    ):
        """
        Capture and send data based on the data type (video, audio).
        """
        if data_type == "video":
            while True:
                frame = capture_function()
                if frame is None:
                    break

                if compress:
                    frame = compress(frame)

                send_conn.write(f"camera{frame}".encode("utf-8"))

                await send_conn.drain()
                await asyncio.sleep(1 / fps_or_frequency)

        elif data_type == "audio":
            while True:
                audio_data = capture_function()
                if audio_data is None:
                    break
                send_conn.write(f"audio{audio_data}".encode("utf-8"))
                await send_conn.drain()
                await asyncio.sleep(1 / fps_or_frequency)

        elif data_type == "screen":
            while True:
                screen_data = capture_function()
                if screen_data is None:
                    break

                if compress:
                    screen_data = compress(f"screen{screen_data}".encode("utf-8"))

                send_conn.write(screen_data)
                await send_conn.drain()
                await asyncio.sleep(1 / fps_or_frequency)

        else:
            print(f"[Error]: Unsupported data type {data_type}")

    async def share_switch(self, data_type):
        """
        switch for sharing certain type of data (screen, camera, audio, etc.)
        """
        if data_type == "video":
            if not self.camera_on:
                self.camera_on = True
                await self.keep_share(
                    "video",
                    self.send_conn,
                    capture_camera,
                    compress_image,
                    fps_or_frequency=30,
                )

        elif data_type == "audio":
            await self.keep_share(
                "audio", self.send_conn, capture_voice, fps_or_frequency=30
            )
        elif data_type == "screen":
            await self.keep_share(
                "screen", self.send_conn, capture_screen, fps_or_frequency=30
            )
        else:
            print("[Error]: Unsupported data type")

    async def keep_recv(self, recv_conn, data_type, decompress=None):
        """
        Keep receiving data (video, audio, screen) from the server and process/display it accordingly.
        """
        while True:
            data = await recv_conn.read(1024)
            if not data:
                break

            if decompress:
                data = decompress(data)

            if data_type == "video":
                frame = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                if frame is not None:
                    cv2.imshow("Received Video", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            elif data_type == "audio":
                streamout.write(data)
            else:
                print(f"[Error]: Unsupported data type {data_type}")

    def output_data(self):
        """
        running task: output received stream data
        """
        pass

    def stop_camera(self):
        """
        Stop the camera capture and release the resources.
        """
        if cap is not None:
            cap.release()
            cap = None
            print("[INFO]: Camera turned off.")
            self.camera_on = False

    async def send_message(self, message):
        """Send a message to the server."""
        if not self.writer:
            print("[Error]: Not connected to server!")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message_with_metadata = f"[{self.client_id} | {timestamp}] {message}"

        self.writer.write(message_with_metadata.encode())
        await self.writer.drain()

    async def receive_message(self):
        """Receive messages from the server."""
        if not self.reader:
            print("[Error]: Not connected to server!")
            return

        while True:
            data = await self.reader.read(1024)
            if data:
                print(f"[DEBUG]: Received from server: {data.decode()}")
                await self.message_queue.put(data.decode())

                # Extract the client ID from the welcome message
                if "Your client ID is" in data.decode():
                    self.client_id = (
                        data.decode().split("Your client ID is ")[1].strip()
                    )
                    print(f"[INFO]: Client ID set to {self.client_id}")
            else:
                print("[Error]: No response from server.")
                break

    async def connect_to_server(self):
        """Connect to the server using asyncio."""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_addr, self.server_port
            )
            self.send_conn = self.writer
            print(f"Connected to server at {self.server_addr}:{self.server_port}")
            await self.writer.drain()
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
        return True

    async def start(self):
        """
        Execute functions based on the command line input.
        """
        connected = await self.connect_to_server()
        if not connected:
            return

        asyncio.create_task(self.receive_message())

        while True:
            if not self.on_meeting:
                status = "Free"
            else:
                status = f"OnMeeting-{self.client_id}"

            recognized = True
            cmd_input = (
                input(f'({status}) Please enter a operation (enter "?" to help): ')
                .strip()
                .lower()
            )
            fields = cmd_input.split(maxsplit=1)

            if len(fields) == 1:
                if cmd_input in ("?", "？"):
                    print(HELP)
                elif cmd_input == "create":
                    self.create_conference()
                elif cmd_input == "quit":
                    self.quit_conference()
                elif cmd_input == "cancel":
                    self.cancel_conference()
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == "join":
                    input_conf_id = fields[1]
                    if input_conf_id.isdigit():
                        self.join_conference(input_conf_id)
                    else:
                        print("[Warn]: Input conference ID must be in numeric form")
                elif fields[0] == "send":
                    message = fields[1]
                    await self.send_message(message)
                elif fields[0] == "camera":
                    if fields[1] == "on":
                        await self.share_switch("video")
                    elif fields[1] == "off":
                        self.stop_camera()
                elif fields[0] == "audio":
                    if fields[1] == "on":
                        await self.share_switch("audio")
                    elif fields[1] == "off":
                        self.stop_camera()
                elif fields[0] == "screen":
                    if fields[1] == "on":
                        await self.share_switch("screen")
                    elif fields[1] == "off":
                        self.stop_camera()
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f"[Warn]: Unrecognized cmd_input {cmd_input}")

            if not self.message_queue.empty():
                msg = await self.message_queue.get()
            await asyncio.sleep(0.1)


if __name__ == "__main__":
    client1 = ConferenceClient()
    asyncio.run(client1.start())
