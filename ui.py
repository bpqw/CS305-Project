import io
import sys
import asyncio
from conf_client import ConferenceClient
from video_thread import VideoThread
from screen_thread import ScreenThread

from PyQt5.QtCore import pyqtSignal, QThread, Qt, QDateTime
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QListWidget,
    QMessageBox,
    QLineEdit,
    QTextEdit,
)


# 控制客户端线程
class ClientThread(QThread):
    # 定义信号，用于在需要时更新 UI
    update_ui = pyqtSignal(str)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def run(self):
        # 在新线程中运行异步客户端
        asyncio.set_event_loop(asyncio.new_event_loop())
        asyncio.get_event_loop().run_until_complete(self.client.start())


# 用于控制台输出获取
class ConsoleOutputCapture:
    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.console_output = io.StringIO()
        sys.stdout = self.console_output
        sys.stderr = self.console_output

    def get_output(self):
        # 获取当前缓存的输出
        output = self.console_output.getvalue()
        self.console_output.truncate(0)
        self.console_output.seek(0)
        return output

    def reset_capture(self):
        # 重置输出缓存
        self.console_output.truncate(0)
        self.console_output.seek(0)

    def restore_original(self):
        # 恢复原始的stdout和stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


# 控制台信息输出线程
class ConsoleMonitorThread(QThread):
    console_output = pyqtSignal(str)

    def __init__(self, capture):
        super().__init__()
        self.capture = capture

    def run(self):
        while True:
            output = self.capture.get_output()
            if output:
                self.console_output.emit(output)
            self.msleep(1)  # 每100毫秒检查一次


class VideoConferenceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.client = ConferenceClient()
        # self.client.message_received.connect(MeetingRoom1.appendText)
        # self.client.message_received.connect(self.appendText)
        self.client_thread = ClientThread(self.client)
        self.client_thread.start()

    def initUI(self):
        self.setWindowTitle("视频会议系统")
        self.setGeometry(600, 150, 700, 700)  # Left, Top, Height, Width
        self.setStyleSheet("background-color: #f0f0f0; font-family: Arial, sans-serif;")

        self.welcome_label = QLabel("欢迎使用本会议软件，请选择你需要的服务", self)
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.welcome_label.setStyleSheet(
            "font-size: 32px; color: #333333; margin-bottom: 20px;"
        )

        # 创建日期标签
        self.date_label = QLabel(self)
        self.update_date()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet(
            "font-size: 24px; color: blue; font-weight: bold; margin-bottom: 40px;"
        )

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.welcome_label)
        main_layout.addWidget(self.date_label)

        # 创建图片标签
        self.image_label = QLabel(self)
        self.image_label.setPixmap(
            QPixmap("path_to_your_image.png").scaled(550, 650, Qt.KeepAspectRatio)
        )
        self.image_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.image_label)

        button_layout = QHBoxLayout()

        self.create_meeting_btn = QPushButton("创建会议", self)
        self.create_meeting_btn.setStyleSheet(self.button_style())
        self.create_meeting_btn.clicked.connect(self.onCreateMeeting)
        button_layout.addWidget(self.create_meeting_btn)

        self.join_meeting_btn = QPushButton("加入会议", self)
        self.join_meeting_btn.setStyleSheet(self.button_style())
        self.join_meeting_btn.clicked.connect(self.onJoinMeeting)
        button_layout.addWidget(self.join_meeting_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def button_style(self):
        return """
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 10px;
                font-size: 20px;
                padding: 15px;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #003d80;
            }
        """

    def onCreateMeeting(self):
        self.client.input = "create"
        # 创建视频会议窗口
        self.create_meeting = MeetingRoom1(self.client)
        self.create_meeting.show()
        self.hide()

    def onJoinMeeting(self):
        # 创建加入会议列表窗口
        self.join_meeting_list = JoinMeetingList(
            self.client
        )  # 传递 self.client 给 JoinMeetingList
        self.join_meeting_list.show()
        self.hide()

    def update_date(self):
        current_date = QDateTime.currentDateTime().toString("yyyy 年 MM 月 dd 日")
        self.date_label.setText(current_date)


# 输入创建会议的信息的窗口
class CreateMeetingDialog(QWidget):
    meeting_created = pyqtSignal(str)  # 创建会议的信号，传递会议名称

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("创建会议")
        self.setGeometry(700, 400, 300, 150)  # 正中间

        layout = QVBoxLayout()

        # 创建会议名称输入框
        self.meeting_name_edit = QLineEdit(self)
        layout.addWidget(self.meeting_name_edit)

        # 完成按钮
        finish_btn = QPushButton("完成")
        finish_btn.clicked.connect(self.onFinish)
        layout.addWidget(finish_btn)

        self.setLayout(layout)

    def onFinish(self):
        meeting_name = self.meeting_name_edit.text()
        if meeting_name:  # 检查是否输入了会议名称

            # 填写对名称传输的逻辑

            self.meeting_room = MeetingRoom1()
            self.meeting_room.show()
            self.close()  # 关闭窗口
        else:
            QMessageBox.warning(self, "警告", "请输入会议名称")


class BaseMeetingRoom(QWidget):
    def __init__(self, client, room_type):
        super().__init__()
        self.client = client
        self.room_type = room_type
        self.initUI()
        self.console_capture = ConsoleOutputCapture()  # 创建控制台输出捕获实例
        self.console_thread = ConsoleMonitorThread(self.console_capture)  # 创建监控线程
        self.console_thread.console_output.connect(self.appendText)  # 连接信号
        self.console_thread.start()  # 启动线程

        self.video_thread = VideoThread(self.client)  # 使用 client 作为 frame_provider
        self.video_thread.change_pixmap_signal.connect(self.update_video)
        self.video_thread.start()
        # self.screen_thread = ScreenThread(self.client)
        # self.screen_thread.change_pixmap_signal.connect(self.update_video)
        # self.screen_thread.start()

    def initUI(self):
        self.setWindowTitle(self.get_window_title())
        self.setGeometry(200, 100, 1280, 720)  # 可以根据需要调整大小

        # 创建主布局
        main_layout = QVBoxLayout(self)  # 使用 QVBoxLayout 作为主布局

        # 创建视频区域
        video_layout = self.create_video_area()
        main_layout.addLayout(video_layout)

        # 创建聊天框区域
        chat_layout = self.create_chat_area()
        main_layout.addLayout(chat_layout, 1)  # 较小空间

        # 创建底部控制栏
        bottom_layout = self.create_bottom_controls()
        main_layout.addLayout(bottom_layout)

        # 设置布局的间距和对齐方式
        main_layout.setStretchFactor(video_layout, 10)
        main_layout.setStretchFactor(chat_layout, 2)
        main_layout.setContentsMargins(20, 20, 20, 20)  # 移除默认的外边距
        bottom_layout.setContentsMargins(20, 20, 20, 20)  # 移除默认的外边距

        # 创建文本框用于输出信息
        self.info_text_edit = QTextEdit()
        self.info_text_edit.setReadOnly(True)
        main_layout.addWidget(self.info_text_edit)

        self.video_label = QLabel(self.video_area)  # 创建用于显示视频的标签
        video_layout.addWidget(self.video_label)

    def get_window_title(self):
        """Return the window title based on room type."""
        if self.room_type == "creator":
            return "用户" + self.client.client_id + "的视频会议房间(房主)"
        else:
            return "用户" + self.client.client_id + "的视频会议房间（成员）"

    def create_video_area(self):
        """Create and return the video area layout."""
        video_layout = QHBoxLayout()
        video_frame = QFrame()
        video_frame.setFrameShape(QFrame.StyledPanel)
        video_layout.addWidget(
            video_frame, 10
        )  # 使用10作为拉伸因子，使其占据大部分空间
        self.video_area = video_frame  # 视频播放区域
        return video_layout

    def create_chat_area(self):
        """Create and return the chat area layout."""
        chat_layout = QVBoxLayout()
        chat_frame = QFrame()
        chat_frame.setFrameShape(QFrame.StyledPanel)
        chat_layout.addWidget(chat_frame)
        chat_layout.addStretch(1)  # 添加弹性空间，使其适应剩余空间
        self.chat_area = chat_frame  # 聊天框区域
        return chat_layout

    def create_bottom_controls(self):
        """Create and return the bottom control layout."""
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)

        # 麦克风按钮
        self.mic_btn = QPushButton("开启麦克风")
        self.mic_btn.clicked.connect(self.onMicClick)
        bottom_layout.addWidget(self.mic_btn)

        # 摄像头按钮
        self.cam_btn = QPushButton("开启摄像头")
        self.cam_btn.clicked.connect(self.onCamClick)
        bottom_layout.addWidget(self.cam_btn)

        # 共享屏幕按钮
        self.screen_btn = QPushButton("共享屏幕")
        self.screen_btn.clicked.connect(self.onScreenClick)
        bottom_layout.addWidget(self.screen_btn)

        # 结束/退出会议按钮
        self.end_meeting_btn = QPushButton(self.get_end_button_text())
        self.end_meeting_btn.clicked.connect(self.onEndMeeting)
        bottom_layout.addWidget(self.end_meeting_btn)

        # 输入框
        self.input_edit = QLineEdit()
        bottom_layout.addWidget(self.input_edit)

        # 发送按钮
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.Input)  # 点击时调用Input方法
        bottom_layout.addWidget(self.send_btn)

        return bottom_layout

    def get_stylesheet(self):
        """Return the style sheet for the widget."""
        return """
        QWidget {
            font-family: Arial, sans-serif;
            font-size: 16px;
            color: #333;
            background-color: #f4f4f4;
        }
        QPushButton {
            padding: 8px 16px;
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            border: none;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 5px;
            background-color: white;
        }
        QTextEdit {
            background-color: #ffffff;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        QFrame {
            border-radius: 5px;
            border: 1px solid #ddd;
            background-color: #fff;
        }
        QLabel {
            max-width: 100%;
            max-height: 100%;
        }
        """

    def get_end_button_text(self):
        """Return the text for the end button based on room type."""
        if self.room_type == "creator":
            return "结束会议"
        else:
            return "退出会议"

    def update_video(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def onEndMeeting(self):
        if self.room_type == "creator":
            self.client.input = "cancel"
        else:
            self.client.input = "quit"
        # 结束或退出会议逻辑
        # self.close()
        # self.parent().show()  # 如果有父窗口，可以取消注释这行
        # QApplication.quit()

    def onMicClick(self):
        # 开启麦克风逻辑
        if self.mic_btn.text() == "开启麦克风":
            print("开启麦克风按钮被点击")
            self.client.input = "audio on"
            self.mic_btn.setText("关闭麦克风")
        else:
            print("关闭麦克风按钮被点击")
            self.client.input = "audio off"
            self.mic_btn.setText("开启麦克风")

    def onCamClick(self):
        if self.cam_btn.text() == "开启摄像头":
            print("开启摄像头按钮被点击")
            self.client.input = "camera on"
            self.cam_btn.setText("关闭摄像头")
        else:
            print("关闭摄像头按钮被点击")
            self.client.input = "camera off"
            self.cam_btn.setText("开启摄像头")

    def onScreenClick(self):
        if self.screen_btn.text() == "共享屏幕":
            print("共享屏幕按钮被点击")
            self.client.input = "screen on"
            self.screen_btn.setText("停止共享")
        else:
            print("停止共享按钮被点击")
            self.client.input = "screen off"
            self.screen_btn.setText("共享屏幕")

    def appendText(self, text):
        # 预留方法，用于将接收到的信息添加到文本框中
        messages = text.split("\n")
        for message in messages:
            if not message.startswith("[DEBUG]") and not message.startswith("[INFO]"):
                self.info_text_edit.append(message)

    # 处理输入的内容
    def Input(self):
        input_text = self.input_edit.text()
        if input_text:  # 空文本不做处理
            self.client.input = "send " + input_text
            self.input_edit.clear()  # 清空输入框


# 会议室（创建者版本）
class MeetingRoom1(BaseMeetingRoom):
    def __init__(self, client):
        super().__init__(client, room_type="creator")


# 会议室（加入者版本）
class MeetingRoom2(BaseMeetingRoom):
    def __init__(self, client):
        super().__init__(client, room_type="member")


# 加入会议列表界面(选择后进入加入者版会议室）
class JoinMeetingList(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client  # 保存 ConferenceClient 实例的引用
        self.initUI()

    def initUI(self):
        self.setWindowTitle("选择要加入的会议")
        self.setGeometry(700, 400, 400, 250)  # 正中间
        self.setStyleSheet("background-color: #f0f0f0; font-family: Arial, sans-serif;")

        layout = QVBoxLayout()

        # Create meeting name input field
        self.meeting_name_edit = QLineEdit(self)
        self.meeting_name_edit.setPlaceholderText("请输入会议名称")
        self.meeting_name_edit.setAlignment(Qt.AlignCenter)
        self.meeting_name_edit.setStyleSheet(self.input_style())
        layout.addWidget(self.meeting_name_edit)

        # Complete button
        finish_btn = QPushButton("完成", self)
        finish_btn.setStyleSheet(self.button_style())
        finish_btn.clicked.connect(self.onFinish)
        layout.addWidget(finish_btn)

        self.setLayout(layout)

    def input_style(self):
        return """
            QLineEdit {
                border: 2px solid #007BFF;
                border-radius: 10px;
                padding: 10px;
                font-size: 18px;
                color: #333;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #0056b3;
                background-color: #f0faff;
            }
        """

    def button_style(self):
        return """
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 10px;
                font-size: 18px;
                padding: 12px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #003d80;
            }
        """

    def onFinish(self):
        meeting_name = self.meeting_name_edit.text()
        if meeting_name:  # 检查是否输入了会议名称
            # 填写对名称传输的逻辑
            self.client.input = f"join {meeting_name}"  # 设置 self.client.input 的值
            self.meeting_room = MeetingRoom2(self.client)
            self.meeting_room.show()
            self.close()  # 关闭窗口
        else:
            QMessageBox.warning(self, "警告", "请输入会议名称")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = VideoConferenceApp()
    ex.show()
    sys.exit(app.exec_())
