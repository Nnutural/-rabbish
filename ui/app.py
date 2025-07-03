import sys
import os
from typing import Optional
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot
import message_storage
from backend import Backend
from audio import AudioRecorder  # 新增导入

class LoginBackend(QObject):
    """登录页面的后端处理类"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
    
    @pyqtSlot()
    def loginSuccess(self):
        """登录成功时调用，切换到主应用程序"""
        print("✅ 登录成功，切换到主应用程序")
        self.app_instance.switch_to_main()

class MainApp(QMainWindow):
    """主应用程序窗口，管理登录和主界面的切换"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("聊天应用程序")
        self.resize(900, 600)
        
        # 创建堆叠窗口部件来管理多个页面
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 创建登录页面
        self.create_login_page()
        
        # 创建主应用程序页面
        self.create_main_page()
        
        # 默认显示登录页面
        self.stacked_widget.setCurrentIndex(0)
    
    def create_login_page(self):
        """创建登录页面"""
        self.login_view = QWebEngineView()
        
        # 允许本地文件加载远程资源
        settings = self.login_view.settings()
        if settings:
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
            )
        
        # 设置WebChannel用于前后端通信
        self.login_channel = QWebChannel()
        self.login_backend = LoginBackend(self)
        self.login_channel.registerObject("backend", self.login_backend)
        page = self.login_view.page()
        if page:
            page.setWebChannel(self.login_channel)
        
        # 加载登录页面
        base_dir = os.path.dirname(os.path.abspath(__file__))
        login_html_path = os.path.join(base_dir, "login.html")
        self.login_view.load(QUrl.fromLocalFile(login_html_path))
        
        # 将登录页面添加到堆叠窗口
        self.stacked_widget.addWidget(self.login_view)
    
    def create_main_page(self):
        """创建主应用程序页面"""
        self.main_view = QWebEngineView()
        
        # 允许本地文件加载远程资源
        settings = self.main_view.settings()
        if settings:
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
            )
        
        # 设置WebChannel用于前后端通信
        self.main_channel = QWebChannel()
        self.main_backend = Backend()
        self.audio_recorder = AudioRecorder()  # 新增
        self.main_channel.registerObject("backend", self.main_backend)
        self.main_channel.registerObject("audioRecorder", self.audio_recorder)  # 新增
        page = self.main_view.page()
        if page:
            page.setWebChannel(self.main_channel)
        
        # 加载主应用程序页面
        base_dir = os.path.dirname(os.path.abspath(__file__))
        main_html_path = os.path.join(base_dir, "index.html")
        self.main_view.load(QUrl.fromLocalFile(main_html_path))
        
        # 将主应用程序页面添加到堆叠窗口
        self.stacked_widget.addWidget(self.main_view)
    
    def switch_to_main(self):
        """切换到主应用程序页面"""
        print("🔄 切换到主应用程序页面")
        self.stacked_widget.setCurrentIndex(1)
        self.setWindowTitle("聊天应用程序 - 主界面")
    
    def switch_to_login(self):
        """切换回登录页面"""
        print("🔄 切换回登录页面")
        self.stacked_widget.setCurrentIndex(0)
        self.setWindowTitle("聊天应用程序 - 登录")

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建主应用程序窗口
    main_window = MainApp()
    main_window.show()
    
    # 运行应用程序
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
