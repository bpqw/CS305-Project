import asyncio
from datetime import datetime
from util import *
import struct
import json
import cv2
import numpy as np


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
                "screen",
                self.send_conn,
                capture_screen,
                compress_image,
                fps_or_frequency=30,
            )
        else:
            print("[Error]: Unsupported data type")

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
                            print("[Error]: Compression function must return bytes.")
                            await asyncio.sleep(1 / fps_or_frequency)
                            continue
                    except Exception as e:
                        print(f"[Error]: Compression failed: {e}")
                        await asyncio.sleep(1 / fps_or_frequency)
                        continue

                data_type_byte = b"V"
                length = struct.pack(">I", len(frame_bytes))

                send_conn.write(data_type_byte + length + frame_bytes)

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
                            print("[Error]: Compression function must return bytes.")
                            await asyncio.sleep(1 / fps_or_frequency)
                            continue
                    except Exception as e:
                        print(f"[Error]: Compression failed: {e}")
                        await asyncio.sleep(1 / fps_or_frequency)
                        continue

                data_type_byte = b"A"
                length = struct.pack(">I", len(audio_data))

                send_conn.write(data_type_byte + length + audio_data)

                await send_conn.drain()
                await asyncio.sleep(1 / fps_or_frequency)

        elif data_type == "screen":
            while True:
                screen_frame = capture_function()
                if screen_frame is None:
                    print("[Info]: No screen captured. Stopping screen share.")
                    break

                success, encoded_image = cv2.imencode(".jpg", screen_frame)
                if not success:
                    print("[Error]: Failed to encode screen frame.")
                    await asyncio.sleep(1 / fps_or_frequency)
                    continue

                screen_bytes = encoded_image.tobytes()

                if compress:
                    try:
                        screen_bytes = compress(screen_bytes)
                        if not isinstance(screen_bytes, bytes):
                            print("[Error]: Compression function must return bytes.")
                            await asyncio.sleep(1 / fps_or_frequency)
                            continue
                    except Exception as e:
                        print(f"[Error]: Compression failed: {e}")
                        await asyncio.sleep(1 / fps_or_frequency)
                        continue

                data_type_byte = b"S"
                length = struct.pack(">I", len(screen_bytes))

                send_conn.write(data_type_byte + length + screen_bytes)

                await send_conn.drain()
                await asyncio.sleep(1 / fps_or_frequency)

        else:
            print(f"[Error]: Unsupported data type {data_type}")

    async def keep_recv(self, recv_conn, decompress=None):
        """
        Keep receiving data (text, video, audio, screen) from the server and process/display it accordingly.
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
                type_data = await recv_conn.readexactly(1)
                if not type_data:
                    print("[Error]: No data received for type identifier.")
                    break
                data_type = type_data.decode("utf-8")

                # Read the 4-byte length header
                length_data = await recv_conn.readexactly(4)
                if not length_data:
                    print("[Error]: No data received for length header.")
                    break
                message_length = struct.unpack(">I", length_data)[0]

                # Read the actual message based on the length
                message_data = await recv_conn.readexactly(message_length)
                if not message_data:
                    print("[Error]: No data received for message payload.")
                    break

                print(
                    f"[DEBUG]: Received data type: {data_type}, Length: {message_length}"
                )

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

                        if "Your client ID is" in message:
                            self.client_id = message.split("Your client ID is ")[
                                1
                            ].strip()
                            print(f"[INFO]: Client ID set to {self.client_id}")

                    except json.JSONDecodeError:
                        print("[Error]: Failed to decode JSON message.")
                    except Exception as e:
                        print(f"[Error]: Exception while processing text message: {e}")

                elif data_type == "V":  # Video
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
                            cv2.imshow("Received Video", frame)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                print("[INFO]: Quitting video display.")
                                break
                        else:
                            print("[Error]: Failed to decode video frame.")
                    except Exception as e:
                        print(f"[Error]: Exception while decoding video frame: {e}")

                elif data_type == "A":  # Audio
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
                            streamout.write(message_data)
                        except Exception as e:
                            print(f"[Error]: Exception while playing audio: {e}")

                elif data_type == "S":  # Screen
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
                            cv2.imshow("Received Screen", screen_frame)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                print("[INFO]: Quitting screen display.")
                                break
                        else:
                            print("[Error]: Failed to decode screen frame.")
                    except Exception as e:
                        print(f"[Error]: Exception while decoding screen frame: {e}")

                else:
                    print(f"[Error]: Unsupported data type {data_type}")

        except asyncio.IncompleteReadError:
            print("[Error]: Connection closed by the server.")
        except Exception as e:
            print(f"[Error]: Exception in keep_recv: {e}")
        finally:
            # Cleanup resources
            cv2.destroyAllWindows()
            streamout.stop_stream()
            streamout.close()
            print("[INFO]: Receiver connection closed.")

    def output_data(self):
        """
        running task: output received stream data
        """
        pass

    async def send_message(self, message):
        """
        Send a text message to the server, prefixed with a type identifier and length header.
        The message includes the client's ID and a timestamp.
        """
        if not self.writer:
            print("[Error]: Not connected to server!")
            return

        data_type = "T".encode("utf-8")

        message_dict = {
            "client_id": self.client_id,
            "timestamp": datetime.now().isoformat(),
            "message": message,
        }

        json_message = json.dumps(message_dict)
        message_bytes = json_message.encode("utf-8")
        length = struct.pack(">I", len(message_bytes))
        self.writer.write(data_type + length + message_bytes)

        await self.writer.drain()

        print(
            f"[INFO]: Sent message from {self.client_id} at {message_dict['timestamp']}"
        )

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

        asyncio.create_task(self.keep_recv(self.reader))

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
                        stop_camera
                        self.camera_on = False
                elif fields[0] == "audio":
                    if fields[1] == "on":
                        await self.share_switch("audio")
                    elif fields[1] == "off":
                        pass
                elif fields[0] == "screen":
                    if fields[1] == "on":
                        await self.share_switch("screen")
                    elif fields[1] == "off":
                        pass
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f"[Warn]: Unrecognized cmd_input {cmd_input}")

            if not self.message_queue.empty():
                await self.message_queue.get()
            await asyncio.sleep(0.1)


if __name__ == "__main__":
    client1 = ConferenceClient()
    asyncio.run(client1.start())
