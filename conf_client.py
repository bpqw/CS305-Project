import asyncio
import datetime
import struct
import json
import cv2
import numpy as np
from util import *
from config import *


class ConferenceClient:
    def __init__(
        self,
    ):
        # Connection related
        self.server_addr = (SERVER_IP, MAIN_SERVER_PORT)
        self.client_id = None

        # Meeting related
        self.conference_id = 0
        self.is_owner = False
        self.on_meeting = False
        self.reader = None  # 对Main Server的接收端
        self.writer = None  # 对Main Server的发送端
        self.meet_reader = None  # 对会议室的接收端
        self.meet_writer = None  # 对会议室的发送端

        # Input related
        self.input = None

        # Message related
        self.message_queue = asyncio.Queue()

        # Video related
        self.cap = None
        self.camera_on = False
        self.frame = None
        self.video_task = None
        self.camera_stop_event = asyncio.Event()

        # Audio related

        # Screen related
        self.screen_on = False
        self.screen_frame = None
        self.screen_task = None
        self.screen_stop_event = asyncio.Event()

    async def start_conference(self):
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

    async def create_conference(self, conference_id):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        conference_port = int(conference_id) + 50000  # 服务器按50000+会议编号分配端口
        try:
            self.meet_reader, self.meet_writer = await asyncio.open_connection(
                self.server_addr[0], conference_port
            )
            print(
                f"Connected to conference {conference_id} at {self.server_addr[0]}:{conference_port}"
            )
            self.is_owner = True  # 是房间的创建者，用于判断有没有cancel的权力
            self.on_meeting = True
            self.meet_writer.write(str(self.client_id).encode())
            try:
                asyncio.create_task(self.keep_recv_meet(self.meet_reader))
            except Exception as e:
                print(f"Errors when starting keep_recv_meet: {e}")
        except Exception as e:
            print(f"Failed to connect to conference {conference_id}: {e}")
            return False
        return True

    async def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        conference_port = int(conference_id) + 50000
        try:
            self.meet_reader, self.meet_writer = await asyncio.open_connection(
                self.server_addr[0], conference_port
            )
            self.on_meeting = True
            self.meet_writer.write(str(self.client_id).encode())
            print(
                f"Connected to conference {conference_id} at {self.server_addr[0]}:{conference_port}"
            )
            try:
                asyncio.create_task(self.keep_recv_meet(self.meet_reader))
            except Exception as e:
                print(f"error when keep recv")
        except Exception as e:
            print(f"Failed to connect to conference {conference_id}: {e}")
            return False
        return True
        pass

    async def quit_conference(self):
        """
        quit your on-going conference
        """
        self.on_meeting = False
        self.conference_id = 0
        await self.disconnect_from_meeting()

    async def disconnect_from_meeting(self):
        if self.meet_writer:
            print("[INFO]: Closing connection to the conference")
            self.meet_writer.close()
            await self.meet_writer.wait_closed()
            self.meet_writer = None
            self.meet_reader = None

    async def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        try:
            await self.send_to_main(f"cancel {self.conference_id}")
            await self.send_to_meet("cancel")
        except Exception as e:
            print(f"Error on cancel")

    async def list_conference(self, conference):
        """list all the conferences"""
        print(conference)

    def capture_frame(self):
        """Capture a single frame from the camera."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
            else:
                print("[Error]: Failed to read frame from camera.")
                return None
        else:
            print("[Error]: Camera is not initialized or already closed.")
            return None

    async def start_video_share(self):
        """Start sharing video by initializing video capture and starting the keep_share coroutine."""
        if not self.camera_on:
            self.camera_on = True
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("[Error]: Unable to open the camera.")
                self.camera_on = False
                return
            self.camera_stop_event.clear()
            self.video_task = asyncio.create_task(
                self.keep_share(
                    data_type="video",
                    send_conn=self.meet_writer,
                    capture_function=self.capture_frame,
                    compress=compress_image,
                    fps_or_frequency=30,
                    stop_event=self.camera_stop_event,
                )
            )
            print("[INFO]: Video sharing started.")

    async def stop_video_share(self):
        """Stop sharing video by stopping the keep_share coroutine and releasing resources."""
        if self.camera_on:
            self.camera_on = False
            self.camera_stop_event.set()
            if self.video_task:
                self.video_task.cancel()
                try:
                    await self.video_task
                except asyncio.CancelledError:
                    print("[INFO]: Video sharing task cancelled successfully.")
                except Exception as e:
                    print(f"[Error]: Exception during video task cancellation: {e}")
            self.video_task = None
            if self.cap and self.cap.isOpened():
                self.cap.release()
                print("[INFO]: Camera released in stop_video_share.")
            self.cap = None
            self.frame = None
            print("[INFO]: Video sharing stopped and resources released.")

    async def start_screen_share(self):
        """Start sharing screen by starting the keep_share coroutine."""
        if not self.screen_on:
            self.screen_on = True
            self.screen_stop_event.clear()
            self.screen_task = asyncio.create_task(
                self.keep_share(
                    data_type="screen",
                    send_conn=self.meet_writer,
                    capture_function=capture_screen,
                    compress=compress_image,
                    fps_or_frequency=30,
                    stop_event=self.screen_stop_event,
                )
            )
            print("[INFO]: Screen sharing started.")

    async def stop_screen_share(self):
        """Stop sharing screen by stopping the keep_share coroutine."""
        if self.screen_on:
            self.screen_on = False
            self.screen_stop_event.set()
            if self.screen_task:
                self.screen_task.cancel()
                try:
                    await self.screen_task
                except asyncio.CancelledError:
                    print("[INFO]: Screen sharing task cancelled successfully.")
                except Exception as e:
                    print(f"[Error]: Exception during screen task cancellation: {e}")
            self.screen_task = None
            self.screen_frame = None
            print("[INFO]: Screen sharing stopped.")

    async def keep_share(
        self,
        data_type,
        send_conn,
        capture_function,
        compress=None,
        fps_or_frequency=30,
        stop_event=None,
    ):
        """
        Capture and send data based on the data type (video, audio).
        """
        try:
            if data_type == "video":
                while not stop_event.is_set():
                    print("[INFO]: Capturing video frame")
                    frame = capture_function()
                    if frame is None:
                        print("[Info]: No frame captured. Stopping video share.")
                        break

                    success, encoded_image = cv2.imencode(".jpg", frame)
                    if not success:
                        print("[Error]: Failed to encode frame.")
                        await asyncio.sleep(1 / fps_or_frequency)
                        continue

                    frame_bytes = encoded_image.tobytes()

                    if compress:
                        try:
                            frame_bytes = compress(frame_bytes)
                            if not isinstance(frame_bytes, bytes):
                                print(
                                    "[Error]: Compression function must return bytes."
                                )
                                await asyncio.sleep(1 / fps_or_frequency)
                                continue
                        except Exception as e:
                            print(f"[Error]: Compression failed: {e}")
                            await asyncio.sleep(1 / fps_or_frequency)
                            continue

                    data_type_byte = b"V"
                    client_id_packed = struct.pack(">I", int(self.client_id))
                    total_length = len(client_id_packed) + len(frame_bytes)
                    length_packed = struct.pack(">I", total_length)
                    send_conn.write(
                        data_type_byte + length_packed + client_id_packed + frame_bytes
                    )

                    await send_conn.drain()
                    await asyncio.sleep(1 / fps_or_frequency)

            elif data_type == "audio":
                while True:
                    audio_data = capture_function()
                    if audio_data is None:
                        print("[Info]: No audio captured. Stopping audio share.")
                        break

                    # Optional compression
                    if compress:
                        try:
                            audio_data = compress(audio_data)
                            if not isinstance(audio_data, bytes):
                                print(
                                    "[Error]: Compression function must return bytes."
                                )
                                await asyncio.sleep(1 / fps_or_frequency)
                                continue
                        except Exception as e:
                            print(f"[Error]: Compression failed: {e}")
                            await asyncio.sleep(1 / fps_or_frequency)
                            continue

                    data_type_byte = b"A"
                    client_id_packed = struct.pack(">I", int(self.client_id))
                    total_length = len(client_id_packed) + len(audio_data)
                    length_packed = struct.pack(">I", total_length)
                    send_conn.write(
                        data_type_byte + length_packed + client_id_packed + audio_data
                    )

                    await send_conn.drain()
                    await asyncio.sleep(1 / fps_or_frequency)

            elif data_type == "screen":
                while not stop_event.is_set():
                    print("[INFO]: Capturing screen")
                    screen = capture_function()
                    if screen is None:
                        print("[Info]: No screen captured. Stopping screen share.")
                        break

                    success, encoded_image = cv2.imencode(".jpg", screen)
                    if not success:
                        print("[Error]: Failed to encode screen.")
                        await asyncio.sleep(1 / fps_or_frequency)
                        continue

                    screen_bytes = encoded_image.tobytes()

                    if compress:
                        try:
                            screen_bytes = compress(screen_bytes)
                            if not isinstance(screen_bytes, bytes):
                                print(
                                    "[Error]: Compression function must return bytes."
                                )
                                await asyncio.sleep(1 / fps_or_frequency)
                                continue
                        except Exception as e:
                            print(f"[Error]: Compression failed: {e}")
                            await asyncio.sleep(1 / fps_or_frequency)
                            continue

                    data_type_byte = b"S"
                    client_id_packed = struct.pack(">I", int(self.client_id))
                    total_length = len(client_id_packed) + len(screen_bytes)
                    length_packed = struct.pack(">I", total_length)
                    send_conn.write(
                        data_type_byte + length_packed + client_id_packed + screen_bytes
                    )

                    await send_conn.drain()
                    await asyncio.sleep(1 / fps_or_frequency)

            else:
                print(f"[Error]: Unsupported data type {data_type}")
        except asyncio.CancelledError:
            print("[INFO]: keep_share task received cancellation.")
        except Exception as e:
            print(f"[Error]: Exception in keep_share: {e}")
        finally:
            print("[INFO]: keep_share task has exited.")
            if data_type == "video":
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                    print("[INFO]: Camera released in keep_share.")
                self.frame = None

    async def keep_recv_main(self):
        """Receive messages from the server."""
        if not self.reader:
            print("[Error]: Not connected to server!")
            return
        while True:
            data = await asyncio.wait_for(self.reader.read(1024), None)
            if data:
                print(f"[DEBUG]: Received from server: {data.decode()}")
                await self.message_queue.put(data.decode())
                # Extract the client ID from the welcome message
                if "Your client ID is" in data.decode():
                    # 连接到主服务器
                    self.client_id = (
                        data.decode().split("Your client ID is ")[1].strip()
                    )
                    print(f"[INFO]: Client ID set to {self.client_id}")
                elif "You create conference " in data.decode():
                    # create
                    self.conference_id = (
                        data.decode().split("You create conference ")[1].strip()
                    )
                    print(f"[INFO]: Create Conference {self.conference_id}")
                    asyncio.create_task(self.create_conference(self.conference_id))
                elif "Successfully join conference " in data.decode():
                    # join
                    self.conference_id = (
                        data.decode().split("Successfully join conference ")[1].strip()
                    )
                    print(f"[INFO]: Join Conference {self.conference_id}")
                    await self.join_conference(self.conference_id)
                elif "There is no conference " in data.decode():
                    # join fail
                    print("Please choose another conference")
                elif "List: " in data.decode():
                    conference = data.decode().split("List: ")[1].strip()
                    await self.list_conference(conference)
                elif "You will quit the conference" in data.decode():
                    await self.quit_conference()
                elif "Cancel successfully" in data.decode():
                    print("[INFO]: Cancel conference successfully")
                else:
                    print("Message error")
            else:
                print("[Error]: No response from server.")
                break
            await asyncio.sleep(0.1)

    async def keep_recv_meet(self, meet_reader, decompress=None):
        """
        Keep receiving data (text, video, audio, screen) from the (conference)server and process/display it accordingly.
        Assumes each message is prefixed with a 1-byte type identifier and a 4-byte big-endian length.
        Data Types:
            - 'T' : Text
            - 'V' : Video
            - 'A' : Audio
            - 'S' : Screen
        """
        try:
            while True:
                # Read the 1-byte type identifier
                type_data = await meet_reader.readexactly(1)
                if not type_data:
                    print("[Error]: No data received for type identifier.")
                    break
                data_type = type_data.decode("utf-8")

                # Read the 4-byte length header
                length_data = await meet_reader.readexactly(4)
                if not length_data:
                    print("[Error]: No data received for length header.")
                    break
                message_length = struct.unpack(">I", length_data)[0]

                # Read the actual message based on the length
                message_data = await meet_reader.readexactly(message_length)
                if not message_data:
                    print("[Error]: No data received for message payload.")
                    break

                # print(
                #     f"[DEBUG]: Received data type: {data_type}, Length: {message_length}"
                # )

                if data_type == "T":  # Text
                    try:
                        text_message = json.loads(message_data.decode("utf-8"))
                        client_id = text_message.get("client_id", "Unknown")
                        timestamp = text_message.get("timestamp", "Unknown")
                        message = text_message.get("message", "")
                        print(f"[{timestamp}] {client_id}: {message}")
                        await self.message_queue.put(
                            {
                                "client_id": client_id,
                                "timestamp": timestamp,
                                "message": message,
                            }
                        )

                    except json.JSONDecodeError:
                        print("[Error]: Failed to decode JSON message.")
                    except Exception as e:
                        print(f"[Error]: Exception while processing text message: {e}")

                elif data_type == "V":  # Video
                    client_id_packed = message_data[:4]
                    client_id = struct.unpack(">I", client_id_packed)[0]
                    message_data = message_data[4:]
                    decompress = decompress_image
                    if decompress:
                        try:
                            message_data = decompress(message_data)
                            if not isinstance(message_data, bytes):
                                print(
                                    "[Error]: Decompression function must return bytes."
                                )
                                continue
                        except Exception as e:
                            print(f"[Error]: Decompression failed: {e}")
                            continue

                    try:
                        frame_np = np.frombuffer(message_data, dtype=np.uint8)
                        frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

                        if frame is not None:
                            self.frame = frame
                            print(f"[INFO]: Received frame from Client {client_id}")
                        else:
                            print("[Error]: Failed to decode video frame.")
                    except Exception as e:
                        print(f"[Error]: Exception while decoding video frame: {e}")

                elif data_type == "A":  # Audio
                    client_id_packed = message_data[:4]
                    client_id = struct.unpack(">I", client_id_packed)[0]
                    message_data = message_data[4:]
                    if decompress:
                        try:
                            message_data = decompress(message_data)
                            if not isinstance(message_data, bytes):
                                print(
                                    "[Error]: Decompression function must return bytes."
                                )
                                continue
                        except Exception as e:
                            print(f"[Error]: Decompression failed: {e}")
                            continue
                    try:
                        # print(f"Received audio length: {len(message_data)}")
                        streamout.write(message_data)
                    except Exception as e:
                        print(f"[Error]: Exception while playing audio: {e}")

                elif data_type == "S":  # Screen
                    client_id_packed = message_data[:4]
                    client_id = struct.unpack(">I", client_id_packed)[0]
                    message_data = message_data[4:]
                    decompress = decompress_image
                    if decompress:
                        try:
                            message_data = decompress(message_data)
                            if not isinstance(message_data, bytes):
                                print(
                                    "[Error]: Decompression function must return bytes."
                                )
                                continue
                        except Exception as e:
                            print(f"[Error]: Decompression failed: {e}")
                            continue

                    try:
                        screen_np = np.frombuffer(message_data, dtype=np.uint8)
                        screen_frame = cv2.imdecode(screen_np, cv2.IMREAD_COLOR)

                        if screen_frame is not None:
                            self.screen_frame = screen_frame
                            print(
                                f"[INFO]: Received screen frame from Client {client_id}"
                            )
                        else:
                            print("[Error]: Failed to decode screen frame.")
                    except Exception as e:
                        print(f"[Error]: Exception while decoding screen frame: {e}")

                else:
                    print(f"[Error]: Unsupported data type {data_type}")
                await asyncio.sleep(0.01)
        except asyncio.IncompleteReadError:
            print("[Error]: Connection closed by the server.")
            self.on_meeting = False
            self.is_owner = False
            self.conference_id = 0
            if self.meet_writer:
                self.meet_writer.close()
                await self.meet_writer.wait_closed()
            self.meet_reader = None
        except Exception as e:
            print(f"[Error]: Exception in keep_recv: {e}")
        finally:
            streamout.stop_stream()
            streamout.close()
            print("[INFO]: Receiver connection closed.")

    async def send_to_main(self, message):
        if not self.writer:
            print("[Error]: Not connected to server!")
            return
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_with_metadata = f"[{self.client_id} | {timestamp}] {message}"
        self.writer.write(message_with_metadata.encode())

    async def send_to_meet(self, message):
        """
        Send a text message to the server, prefixed with a type identifier and length header.
        The message includes the client's ID and a timestamp.
        """
        if not self.meet_writer:
            print("[Error]: Not connected to server!")
            return
        data_type = "T".encode("utf-8")
        message_dict = {
            "client_id": self.client_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": message,
        }
        json_message = json.dumps(message_dict)
        message_bytes = json_message.encode("utf-8")
        total_length = len(message_bytes)
        self.meet_writer.write(
            data_type + struct.pack(">I", total_length) + message_bytes
        )
        await self.meet_writer.drain()
        print(
            f"[INFO]: Sent message from {self.client_id} at {message_dict['timestamp']}"
        )

    async def receive_command(self):
        while True:
            await asyncio.sleep(0.5)
            recognized = True
            if self.input is not None:
                fields = self.input.split(maxsplit=1)
                if len(fields) == 1:
                    if self.input in ("?", "？"):
                        print(HELP)
                    elif self.input == "create":
                        if not self.on_meeting:
                            await self.send_to_main("create")
                            pass
                        else:
                            print("You are already in a conference")
                    elif self.input == "quit":
                        if self.on_meeting:
                            await self.send_to_main("quit")
                        else:
                            print("You are not in any conference")
                    elif self.input == "cancel":
                        if self.is_owner:
                            await self.cancel_conference()
                        else:
                            print("You cannot cancel the conference")
                    elif self.input == "list":
                        await self.send_to_main("list")
                        pass
                    else:
                        recognized = False
                elif len(fields) == 2:
                    if fields[0] == "join":
                        if self.on_meeting:
                            print("You are already in a conference")
                        else:
                            input_conf_id = fields[1]
                            if input_conf_id.isdigit():
                                await self.send_to_main(f"join {input_conf_id}")
                            else:
                                print(
                                    "[Warn]: Input conference ID must be in digital form"
                                )
                    elif fields[0] == "send":
                        message = fields[1]
                        await self.send_to_meet(message)
                    elif fields[0] == "camera":
                        if fields[1] == "on":
                            await self.start_video_share()
                        elif fields[1] == "off":
                            await self.stop_video_share()
                    elif fields[0] == "audio":
                        if fields[1] == "on":
                            await self.keep_share(
                                "audio",
                                self.meet_writer,
                                capture_voice,
                                compress=None,
                                fps_or_frequency=120,
                            )
                        elif fields[1] == "off":
                            pass  ##
                    elif fields[0] == "screen":
                        if fields[1] == "on":
                            await self.start_screen_share()
                        elif fields[1] == "off":
                            await self.stop_screen_share()
                    else:
                        recognized = False
                else:
                    recognized = False

                self.input = None
                if not recognized:
                    print(f"[Warn]: Unrecognized input {self.input}")

                if not self.message_queue.empty():
                    await self.message_queue.get()
                    await asyncio.sleep(0.1)

    async def start(self):
        """
        Execute functions based on the command line input.
        """
        connected = await self.connect_to_server()
        if not connected:
            return

        await asyncio.gather(self.receive_command(), self.keep_recv_main())

    async def connect_to_server(self):
        """Connect to the server using asyncio."""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_addr[0], self.server_addr[1]
            )
            print(f"Connected to server at {self.server_addr[0]}:{self.server_addr[1]}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
        return True


if __name__ == "__main__":
    client1 = ConferenceClient()
    asyncio.run(client1.start())
