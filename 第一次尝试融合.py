import asyncio
import io

import cv2

from conf_client import ConferenceClient
import struct
import sys

from PyQt5.QtCore import pyqtSignal, QThread, Qt, QDateTime
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QListWidget, \
    QMessageBox, QLineEdit, QTextEdit

#控制客户端线程
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

#用于控制台输出获取
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

#控制台信息输出线程
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

# 获取会议列表的接口
class MeetingAPI:
    @staticmethod
    def get_meeting_list():
        # 从服务器获取会议列表

        return ["会议1", "会议2", "会议3","新建会议"]

        # 模拟从服务器获取会议列表
        # 这里我们使用一个固定的URL来模拟服务器端点
        # url = "https://api.example.com/meetings"
        #
        # # 发送GET请求到服务器
        # try:
        #     response = requests.get(url)
        #     response.raise_for_status()  # 检查请求是否成功
        #     meetings = response.json()  # 假设服务器返回的是JSON数据
        #     return meetings
        # except requests.RequestException as e:
        #     print(f"请求失败：{e}")
        #     return []

# class ConsoleOutput:
#     def __init__(self, widget):
#         self.widget = widget
#
#     def write(self, message):
#         # 将输出写入到GUI组件中
#         self.widget.appendText(message)
#         # 确保输出也显示在控制台上
#         sys.__stdout__.write(message)

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
        self.setWindowTitle('视频会议系统')
        self.setGeometry(600, 300, 1000, 800)   # 正中间

        self.welcome_label = QLabel("欢迎使用本会议软件，请选择你需要的服务", self)
        self.welcome_label.move(500, 100)  # 设置标签的位置
        self.welcome_label.resize(400, 200)  # 设置标签的大小
        self.welcome_label.setStyleSheet("font-size: 25px;")  # 设置字体大小

        # 创建日期标签
        self.date_label = QLabel(self)
        self.date_label.move(550, 100)
        self.date_label.resize(700, 50)
        self.update_date()  # 更新日期
        self.date_label.setStyleSheet("font-size: 25px; color: blue; font-weight: bold;")

        # 创建图片标签
        self.image_label = QLabel(self)
        self.image_label.move(420, 200)  # 设置图片的位置
        self.image_label.resize(550, 650)  # 设置图片的大小
        pixmap = QPixmap("D:\PyCharm 2024.2.1\\pythonProject\\计算机网络\\GUI测试\\img.png")
        self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio))

        self.create_meeting_btn = QPushButton('创建会议', self)
        self.create_meeting_btn.move(200, 100)  # 设置按钮的位置
        self.create_meeting_btn.resize(200, 200)  # 设置按钮的大小
        self.create_meeting_btn.clicked.connect(self.onCreateMeeting)

        # 加入会议按钮
        self.join_meeting_btn = QPushButton('加入会议', self)
        self.join_meeting_btn.move(200, 400)
        self.join_meeting_btn.resize(200, 200)
        self.join_meeting_btn.clicked.connect(self.onJoinMeeting)

    def onCreateMeeting(self):
        self.client.input = "create"
        # 创建视频会议窗口
        self.create_meeting = MeetingRoom1(self.client)
        self.create_meeting.show()
        self.hide()


    def onJoinMeeting(self):
        # 创建加入会议列表窗口
        self.join_meeting_list = JoinMeetingList(self.client)  # 传递 self.client 给 JoinMeetingList
        self.join_meeting_list.show()
        self.hide()

    def update_date(self):
        current_date = QDateTime.currentDateTime().toString("yyyy 年 MM 月 dd 日")
        self.date_label.setText(current_date)

#输入创建会议的信息的窗口
class CreateMeetingDialog(QWidget):
    meeting_created = pyqtSignal(str)  # 创建会议的信号，传递会议名称

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('创建会议')
        self.setGeometry(700, 400, 300, 150)  # 正中间

        layout = QVBoxLayout()

        # 创建会议名称输入框
        self.meeting_name_edit = QLineEdit(self)
        layout.addWidget(self.meeting_name_edit)

        # 完成按钮
        finish_btn = QPushButton('完成')
        finish_btn.clicked.connect(self.onFinish)
        layout.addWidget(finish_btn)

        self.setLayout(layout)

    def onFinish(self):
        meeting_name = self.meeting_name_edit.text()
        if meeting_name:  # 检查是否输入了会议名称

            #填写对名称传输的逻辑

            self.meeting_room = MeetingRoom1()
            self.meeting_room.show()
            self.close()  # 关闭窗口
        else:
            QMessageBox.warning(self, '警告', '请输入会议名称')

#会议室（创建者版本）：可以结束会议
class MeetingRoom1(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.initUI()
        # self.client_thread = ClientThread(self.client)
        # self.client_thread.update_ui.connect(self.appendText)
        # self.client_thread.start()
        self.console_capture = ConsoleOutputCapture()  # 创建控制台输出捕获实例
        self.console_thread = ConsoleMonitorThread(self.console_capture)  # 创建监控线程
        self.console_thread.console_output.connect(self.appendText)  # 连接信号
        self.console_thread.start()  # 启动线程

    def initUI(self):
        self.setWindowTitle('视频会议房间')
        self.setGeometry(100, 100, 1280, 720)

        # 创建主布局
        main_layout = QVBoxLayout(self)  #QVBoxLayout作为主布局

        # 创建视频区域
        video_layout = QHBoxLayout()
        video_frame = QFrame()
        video_frame.setFrameShape(QFrame.StyledPanel)
        video_layout.addWidget(video_frame, 10)  # 用10作为拉伸因子，用来占据大部分空间
        self.video_area = video_frame  # 视频播放区域

        # 创建聊天框区域
        chat_layout = QVBoxLayout()
        chat_frame = QFrame()
        chat_frame.setFrameShape(QFrame.StyledPanel)
        chat_layout.addWidget(chat_frame)
        chat_layout.addStretch(1)  # 添加弹性空间
        self.chat_area = chat_frame  # 聊天框区域

        # 添加视频区域和聊天框到主布局
        main_layout.addLayout(video_layout)
        main_layout.addLayout(chat_layout, 1)  # 较小空间

        # 创建底部控制栏
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # 麦克风按钮
        self.mic_btn = QPushButton('开启麦克风')
        self.mic_btn.clicked.connect(self.onMicClick)
        bottom_layout.addWidget(self.mic_btn)

        # 摄像头按钮
        self.cam_btn = QPushButton('开启摄像头')
        self.cam_btn.clicked.connect(self.onCamClick)
        bottom_layout.addWidget(self.cam_btn)

        # 结束会议按钮
        self.end_meeting_btn = QPushButton('结束会议')
        self.end_meeting_btn.clicked.connect(self.onEndMeeting)
        bottom_layout.addWidget(self.end_meeting_btn)

        # 输入框
        self.input_edit = QLineEdit()
        bottom_layout.addWidget(self.input_edit)

        # 发送按钮
        self.send_btn = QPushButton('发送')
        self.send_btn.clicked.connect(self.Input)  # 点击时调用Input方法
        bottom_layout.addWidget(self.send_btn)

        # 将底部控制栏添加到主布局
        main_layout.addLayout(bottom_layout)

        # 设置布局的间距和对齐方式
        main_layout.setStretchFactor(video_layout, 10)
        main_layout.setStretchFactor(chat_layout, 2)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除默认的外边距
        bottom_layout.setContentsMargins(0, 0, 0, 0)  # 移除默认的外边距

        # 创建文本框用于输出信息
        self.info_text_edit = QTextEdit()
        self.info_text_edit.setReadOnly(True)
        main_layout.addWidget(self.info_text_edit)

        # self.client_thread = ClientThread(self.client)
        # self.client_thread.update_ui.connect(self.appendText)
        # self.client_thread.start()

        # self.video_label = QLabel(self.video_area)  # 创建用于显示视频的标签
        # self.video_area_layout = QVBoxLayout(self.video_area)
        # self.video_area_layout.addWidget(self.video_label)

    def onEndMeeting(self):
        self.client.input = "cancel"
        # 结束会议逻辑
        # self.close()
        # self.parent().show()  # 如果有父窗口，可以取消注释这行
        # QApplication.quit()

    def onMicClick(self):
        # 开启麦克风逻辑
        if self.mic_btn.text() == '开启麦克风':
            print("开启麦克风按钮被点击")
            self.client.input = "audio on"
            self.mic_btn.setText('关闭麦克风')
            self.appendText("麦克风已开启")         #仅用于证明文本框有效
        else:
            print("关闭麦克风按钮被点击")
            self.client.input = "audio off"
            self.mic_btn.setText('开启麦克风')
            self.appendText("麦克风已关闭")

    def onCamClick(self):
        # 开启摄像头逻辑
        if self.cam_btn.text() == '开启摄像头':
            print("开启摄像头按钮被点击")
            self.client.input = "camera on"
            self.cam_btn.setText('[关闭摄像头')
            self.appendText("[摄像头已开启")
        else:
            # 关闭摄像头逻辑
            print("关闭摄像头按钮被点击")
            self.client.input = "camera off"
            self.cam_btn.setText('[开启摄像头')
            self.appendText("[摄像头已关闭")
            self.appendText(self.client.input)


    def appendText(self, text):
        # self.info_text_edit.append(text)
        messages = text.split('\n')
        for message in messages:
            if  not message.startswith("[DEBUG]") and not message.startswith("[INFO]"):
                self.info_text_edit.append(message)

    # 处理输入的内容
    def Input(self):
        input_text = self.input_edit.text()
        if input_text:  # 空文本不做处理
            self.client.input = "send " + input_text
            # self.appendText(f"[{self.client.timestamp}] {self.client.client_id}: {self.client.message}")
            # self.appendText(input_text)  # 将输入的内容添加到文本框----------此行功能仅用于证明输入的文本有效
            self.input_edit.clear()  # 清空输入框

#会议室（加入者版本）：只能退出会议
class MeetingRoom2(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.initUI()
        self.console_capture = ConsoleOutputCapture()  # 创建控制台输出捕获实例
        self.console_thread = ConsoleMonitorThread(self.console_capture)  # 创建监控线程
        self.console_thread.console_output.connect(self.appendText)  # 连接信号
        self.console_thread.start()  # 启动线程

    def initUI(self):
        self.setWindowTitle('视频会议房间')
        self.setGeometry(100, 100, 1280, 720)  # 可以根据需要调整大小

        # 创建主布局
        main_layout = QVBoxLayout(self)  # 使用 QVBoxLayout 作为主布局

        # 创建视频区域
        video_layout = QHBoxLayout()
        video_frame = QFrame()
        video_frame.setFrameShape(QFrame.StyledPanel)
        video_layout.addWidget(video_frame, 10)  # 使用10作为拉伸因子，使其占据大部分空间
        self.video_area = video_frame  # 视频播放区域

        # 创建聊天框区域
        chat_layout = QVBoxLayout()
        chat_frame = QFrame()
        chat_frame.setFrameShape(QFrame.StyledPanel)
        chat_layout.addWidget(chat_frame)
        chat_layout.addStretch(1)  # 添加弹性空间，使其适应剩余空间
        self.chat_area = chat_frame  # 聊天框区域

        # 添加视频区域和聊天框到主布局
        main_layout.addLayout(video_layout)
        main_layout.addLayout(chat_layout, 1)  # 较小空间

        # 创建底部控制栏
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # 麦克风按钮
        self.mic_btn = QPushButton('开启麦克风')
        self.mic_btn.clicked.connect(self.onMicClick)
        bottom_layout.addWidget(self.mic_btn)

        # 摄像头按钮
        self.cam_btn = QPushButton('开启摄像头')
        self.cam_btn.clicked.connect(self.onCamClick)
        bottom_layout.addWidget(self.cam_btn)

        # 退出会议按钮
        self.end_meeting_btn = QPushButton('退出会议')
        self.end_meeting_btn.clicked.connect(self.onEndMeeting)
        bottom_layout.addWidget(self.end_meeting_btn)

        # 输入框
        self.input_edit = QLineEdit()
        bottom_layout.addWidget(self.input_edit)

        # 发送按钮
        self.send_btn = QPushButton('发送')
        self.send_btn.clicked.connect(self.Input)  # 点击时调用Input方法
        bottom_layout.addWidget(self.send_btn)

        # 将底部控制栏添加到主布局
        main_layout.addLayout(bottom_layout)

        # 设置布局的间距和对齐方式
        main_layout.setStretchFactor(video_layout, 10)
        main_layout.setStretchFactor(chat_layout, 2)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除默认的外边距
        bottom_layout.setContentsMargins(0, 0, 0, 0)  # 移除默认的外边距

        # 创建文本框用于输出信息
        self.info_text_edit = QTextEdit()
        self.info_text_edit.setReadOnly(True)
        main_layout.addWidget(self.info_text_edit)

    def onEndMeeting(self):
        self.client.input = "quit"
        # self.close()
        # self.parent().show()  # 如果有父窗口，可以取消注释这行
        # QApplication.quit()

    def onMicClick(self):
        # 开启麦克风逻辑
        if self.mic_btn.text() == '开启麦克风':
            print("开启麦克风按钮被点击")
            self.mic_btn.setText('关闭麦克风')
            self.appendText("麦克风已开启")  # 仅用于证明文本框有效
        else:
            print("关闭麦克风按钮被点击")
            self.mic_btn.setText('开启麦克风')
            self.appendText("麦克风已关闭")

    def onCamClick(self):
        # 开启摄像头逻辑
        if self.cam_btn.text() == '开启摄像头':
            print("开启摄像头按钮被点击")
            self.cam_btn.setText('关闭摄像头')
        else:
            # 关闭摄像头逻辑
            print("关闭摄像头按钮被点击")
            self.cam_btn.setText('开启摄像头')

    def appendText(self, text):
        # 预留方法，用于将接收到的信息添加到文本框中
        messages = text.split('\n')
        for message in messages:
            if not message.startswith("[DEBUG]") and not message.startswith("[INFO]"):
                self.info_text_edit.append(message)
    # 处理输入的内容
    def Input(self):
        input_text = self.input_edit.text()
        if input_text:  # 空文本不做处理
            self.client.input = "send " + input_text
            # self.appendText(f"[{self.client.timestamp}] {self.client.client_id}: {self.client.message}")
            # self.appendText(input_text)  # 将输入的内容添加到文本框----------此行功能仅用于证明输入的文本有效
            self.input_edit.clear()  # 清空输入框

# 加入会议列表界面(选择后进入加入者版会议室）
class JoinMeetingList(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client  # 保存 ConferenceClient 实例的引用
        self.initUI()

    def initUI(self):
        self.setWindowTitle('选择要加入的会议')
        self.setGeometry(700, 400, 300, 150)  # 正中间

        layout = QVBoxLayout()

        # 创建会议名称输入框
        self.meeting_name_edit = QLineEdit(self)
        layout.addWidget(self.meeting_name_edit)
        # 完成按钮
        finish_btn = QPushButton('完成')
        finish_btn.clicked.connect(self.onFinish)
        layout.addWidget(finish_btn)

        self.setLayout(layout)

    def onFinish(self):
        meeting_name = self.meeting_name_edit.text()
        if meeting_name:  # 检查是否输入了会议名称
            # 填写对名称传输的逻辑
            self.client.input = f"join {meeting_name}"  # 设置 self.client.input 的值
            self.meeting_room = MeetingRoom2(self.client)
            self.meeting_room.show()
            self.close()  # 关闭窗口
        else:
            QMessageBox.warning(self, '警告', '请输入会议名称')



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoConferenceApp()
    ex.show()
    sys.exit(app.exec_())