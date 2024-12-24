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
import noisereduce as nr
from PIL import Image, ImageGrab
from config import *


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


# audio setting
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
audio = pyaudio.PyAudio()
streamin = audio.open(
    format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK
)
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


def stop_voice():
    """
    Stop the voice capture and release the resources.
    """
    global streamin, streamout, audio

    try:
        if streamin.is_active():
            streamin.stop_stream()
        streamin.close()
    except Exception as e:
        print(f"[Error]: Failed to stop or close input stream: {e}")

    try:
        if streamout.is_active():
            streamout.stop_stream()
        streamout.close()
    except Exception as e:
        print(f"[Error]: Failed to stop or close output stream: {e}")

    try:
        audio.terminate()
    except Exception as e:
        print(f"[Error]: Failed to terminate PyAudio: {e}")

    print("Voice capture stopped and resources released.")


def compress_audio(data):

    return data


def decompress_audio(compressed_data):

    return compressed_data


def apply_noise_suppression(audio_data):
    """Apply noise suppression using the noisereduce package."""
    audio_np = np.frombuffer(audio_data, dtype=np.int16)
    audio_np = audio_np / 32768.0
    reduced_audio_np = nr.reduce_noise(y=audio_np, sr=RATE)
    reduced_audio_np = np.clip(reduced_audio_np, -1.0, 1.0)
    audio_data = (reduced_audio_np * 32768).astype(np.int16).tobytes()
    return audio_data


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


my_screen_size = pyautogui.size()
