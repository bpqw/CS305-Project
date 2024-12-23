from threading import Lock

import cv2
import time
from PyQt5.QtCore import pyqtSignal, QThread, Qt
from PyQt5.QtGui import QImage, QPainter, QFont


class VideoThread(QThread):
    change_pixmap_signal_1 = pyqtSignal(QImage)
    change_pixmap_signal_2 = pyqtSignal(QImage)
    change_pixmap_signal_3 = pyqtSignal(QImage)
    error_signal = pyqtSignal(str)


    def __init__(self, frame_provider):
        super().__init__()
        self.frame_provider = frame_provider  # 用于提供视频帧的对象
        self.running = True
        self.last_frame_time = time.time()
        self.lock = Lock()  # 添加线程锁

    def run(self):
        while self.running:
            self.process_frame("frame_1", self.change_pixmap_signal_1)
            self.process_frame("frame_2", self.change_pixmap_signal_2)
            self.process_frame("frame_3", self.change_pixmap_signal_3)
            self.msleep(10)  # Sleep for 10ms to prevent high CPU usage


    def process_frame(self, frame_attr, signal):
        current_time = time.time()
        with self.lock:  # 确保对共享资源的访问是线程安全的
            frame = getattr(self.frame_provider, frame_attr, None)
            if frame is not None:
                image = self.convert_cv_qt(frame)
                signal.emit(image)
                setattr(self.frame_provider, frame_attr, None)  # 重置 frame
                self.last_frame_time = current_time  # 更新最后处理时间
            elif current_time - self.last_frame_time > 0.1:  # 超过 100ms 没有帧
                placeholder_image = self.create_placeholder_image(640, 480, "No Video")
                signal.emit(placeholder_image)

    def stop(self):
        self.running = False
        self.wait()

    def convert_cv_qt(self, cv_img):
        # 将cv图像转换为QImage
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(
            rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
        )
        p = convert_to_Qt_format.scaled(640, 480, Qt.KeepAspectRatio)
        return p

    def create_placeholder_image(self, width=640, height=480, message="No Video"):
        placeholder = QImage(width, height, QImage.Format_RGB888)
        placeholder.fill(Qt.black)  # Fill with black color

        # Add text overlay
        painter = QPainter(placeholder)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 20))
        painter.drawText(placeholder.rect(), Qt.AlignCenter, message)
        painter.end()

        return placeholder