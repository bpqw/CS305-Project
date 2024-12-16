"""
Simple util implementation for video conference
Including data capture, image compression and image overlap
Note that you can use your own implementation as well :)
"""

import zlib
import pyaudio
import cv2
import pyautogui
import numpy as np
from PIL import Image, ImageGrab
from config import *

cap = cv2.VideoCapture(0)
if cap.isOpened():
    can_capture_camera = True
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
else:
    can_capture_camera = False


def capture_camera():
    ret, frame = cap.read()
    if not ret:
        raise Exception("Fail to capture frame from camera")
    return frame


def compress_image(data):
    """
    Compress bytes using zlib.

    """
    try:
        compressed_data = zlib.compress(data)
        return compressed_data
    except Exception as e:
        print(f"[Error]: Compression error: {e}")
        return data


def decompress_image(compressed_data):
    """
    Decompress bytes using zlib.
    """
    try:
        decompressed_data = zlib.decompress(compressed_data)
        return decompressed_data
    except Exception as e:
        print(f"[Error]: Decompression error: {e}")
        return compressed_data


def stop_camera(self):
    """
    Stop the camera capture and release the resources.
    """
    if cap is not None:
        cap.release()
        cap = None
        print("[INFO]: Camera turned off.")


# audio setting
FORMAT = pyaudio.paInt16
audio = pyaudio.PyAudio()
# print("Default input device:", audio.get_default_input_device_info(), "\n")
# print("Default output device:", audio.get_default_output_device_info(), "\n")
# for i in range(audio.get_device_count()):
#     info = audio.get_device_info_by_index(i)
#     if info.get("maxOutputChannels") > 0:
#         print(
#             i,
#             info.get("name"),
#             info.get("maxInputChannels"),
#             info.get("maxOutputChannels"),
#         )
streamin = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)
# for i in range(audio.get_device_count()):
#     info = audio.get_device_info_by_index(i)
#     print(f"Device {i}: {info['name']} - Output Channels: {info['maxOutputChannels']}")
streamout = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    output=True,
    frames_per_buffer=CHUNK,
)






def capture_voice():
    try:
        return streamin.read(CHUNK, exception_on_overflow=False)
    except Exception as e:
        print(f"[Error]: Failed to capture audio: {e}")
        return None


# def compress_image(image, format="JPEG", quality=85):
#     """
#     compress image and output Bytes

#     :param image: PIL.Image, input image
#     :param format: str, output format ('JPEG', 'PNG', 'WEBP', ...)
#     :param quality: int, compress quality (0-100), 85 default
#     :return: bytes, compressed image data
#     """
#     img_byte_arr = BytesIO()
#     image.save(img_byte_arr, format=format, quality=quality)
#     img_byte_arr = img_byte_arr.getvalue()

#     return img_byte_arr


# def decompress_image(image_bytes):
#     """
#     Decompress image bytes and return them as raw JPEG bytes suitable for cv2.imdecode.
#     :param image_bytes: bytes representing compressed image data
#     :return: bytes representing a JPEG-encoded image
#     """
#     try:
#         # Load the image from bytes using PIL
#         img_byte_arr = io.BytesIO(image_bytes)
#         image = Image.open(img_byte_arr).convert("RGB")  # Ensure RGB format

#         # Re-encode the image as JPEG and return the raw bytes
#         out_byte_arr = io.BytesIO()
#         image.save(out_byte_arr, format="JPEG")
#         return out_byte_arr.getvalue()
#     except Exception as e:
#         print(f"[Error]: Decompression error: {e}")
#         return image_bytes


def capture_screen():
    """
    Capture the entire screen and return it as a NumPy array suitable for OpenCV.

    :return: np.ndarray representing the screen image.
    """
    try:
        img = ImageGrab.grab()
        img_np = np.array(img)
        # Convert RGB to BGR (OpenCV uses BGR)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return img_np
    except Exception as e:
        print(f"[Error]: Failed to capture screen: {e}")
        return None


# def capture_screen():
#     # capture screen with the resolution of display
#     # img = pyautogui.screenshot()
#     img = ImageGrab.grab()
#     return img


my_screen_size = pyautogui.size()


def resize_image_to_fit_screen(image, my_screen_size):
    screen_width, screen_height = my_screen_size

    original_width, original_height = image.size

    aspect_ratio = original_width / original_height

    if screen_width / screen_height > aspect_ratio:
        # resize according to height
        new_height = screen_height
        new_width = int(new_height * aspect_ratio)
    else:
        # resize according to width
        new_width = screen_width
        new_height = int(new_width / aspect_ratio)

    # resize the image
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    return resized_image


def overlay_camera_images(screen_image, camera_images):
    """
    screen_image: PIL.Image
    camera_images: list[PIL.Image]
    """
    if screen_image is None and camera_images is None:
        print("[Warn]: cannot display when screen and camera are both None")
        return None
    if screen_image is not None:
        screen_image = resize_image_to_fit_screen(screen_image, my_screen_size)

    if camera_images is not None:
        # make sure same camera images
        if not all(img.size == camera_images[0].size for img in camera_images):
            raise ValueError("All camera images must have the same size")

        screen_width, screen_height = (
            my_screen_size if screen_image is None else screen_image.size
        )
        camera_width, camera_height = camera_images[0].size

        # calculate num_cameras_per_row
        num_cameras_per_row = screen_width // camera_width

        # adjust camera_imgs
        if len(camera_images) > num_cameras_per_row:
            adjusted_camera_width = screen_width // len(camera_images)
            adjusted_camera_height = (
                adjusted_camera_width * camera_height
            ) // camera_width
            camera_images = [
                img.resize(
                    (adjusted_camera_width, adjusted_camera_height), Image.LANCZOS
                )
                for img in camera_images
            ]
            camera_width, camera_height = adjusted_camera_width, adjusted_camera_height
            num_cameras_per_row = len(camera_images)

        # if no screen_img, create a container
        if screen_image is None:
            display_image = Image.fromarray(
                np.zeros((camera_width, my_screen_size[1], 3), dtype=np.uint8)
            )
        else:
            display_image = screen_image
        # cover screen_img using camera_images
        for i, camera_image in enumerate(camera_images):
            row = i // num_cameras_per_row
            col = i % num_cameras_per_row
            x = col * camera_width
            y = row * camera_height
            display_image.paste(camera_image, (x, y))

        return display_image
    else:
        return screen_image
