from PyQt5.QtCore import pyqtSignal, QThread, Qt
from PyQt5.QtGui import QImage
import cv2


# 视频流获取线程（用Video_play)改造的，赞！
class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    error_signal = pyqtSignal(str)

    def __init__(self, frame_provider):
        super().__init__()
        self.frame_provider = frame_provider  # 用于提供视频帧的对象
        self.running = True

    def run(self):
        while self.running:
            if (
                hasattr(self.frame_provider, "frame")
                and self.frame_provider.frame is not None
            ):
                frame = self.frame_provider.frame
                image = self.convert_cv_qt(frame)
                self.change_pixmap_signal.emit(image)
                self.frame_provider.frame = None  # 重置frame
            self.msleep(10)  # Sleep for 10ms to prevent high CPU usage

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
