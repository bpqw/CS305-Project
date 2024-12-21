from PyQt5.QtCore import pyqtSignal, QThread, Qt
from PyQt5.QtGui import QImage
import cv2


class ScreenThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    error_signal = pyqtSignal(str)

    def __init__(self, frame_provider):
        super().__init__()
        self.frame_provider = frame_provider
        self.running = True

    def run(self):
        while self.running:
            if (
                hasattr(self.frame_provider, "screen_frame")
                and self.frame_provider.screen_frame is not None
            ):
                frame = self.frame_provider.screen_frame
                image = self.convert_cv_qt(frame)
                self.change_pixmap_signal.emit(image)
                self.frame_provider.screen_frame = None
            else:
                blank_image = QImage(640, 480, QImage.Format_RGB888)
                blank_image.fill(Qt.black)
                self.change_pixmap_signal.emit(blank_image)
            self.msleep(10)  # Sleep for 10ms to prevent high CPU usage

    def stop(self):
        self.running = False
        self.wait()

    def convert_cv_qt(self, cv_img):
        """Convert from an OpenCV image to QImage."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(
            rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
        )
        p = convert_to_Qt_format.scaled(640, 480, Qt.KeepAspectRatio)
        return p
