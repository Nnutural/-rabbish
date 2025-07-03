import sys
import os
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
import message_storage  # 导入保存消息的 API
from backend import Backend
from audio import AudioRecorder  # 新增导入
from stego import StegoBackend  # 新增导入

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(900, 600)
        self.setWindowTitle("聊天示例")

        self.webview: QWebEngineView = QWebEngineView()
        self.setCentralWidget(self.webview)

        # 允许本地文件加载远程资源（如在线图标）
        self.webview.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)  # type: ignore

        self.channel = QWebChannel()
        self.backend = Backend()
        self.channel.registerObject("backend", self.backend)
        self.audio_recorder = AudioRecorder()  # 新增
        self.channel.registerObject("audioRecorder", self.audio_recorder)  # 新增
        self.stego_backend = StegoBackend()  # 新增
        self.channel.registerObject("stego", self.stego_backend)  # 新增
        self.webview.page().setWebChannel(self.channel)  # type: ignore

        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, 'index.html')
        self.webview.load(QUrl.fromLocalFile(html_path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())
