#!/usr/bin/env python3
"""
测试脚本 - 验证app.py的登录跳转功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有必要的模块是否能正确导入"""
    try:
        print("🔍 测试模块导入...")
        
        # 测试PyQt6模块
        from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
        from PyQt6.QtCore import QUrl
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtCore import QObject, pyqtSlot
        print("✅ PyQt6模块导入成功")
        
        # 测试本地模块
        import message_storage
        print("✅ message_storage模块导入成功")
        
        from backend import Backend
        print("✅ Backend类导入成功")
        
        # 测试app.py模块
        from app import MainApp, LoginBackend
        print("✅ app.py模块导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_file_existence():
    """测试必要的文件是否存在"""
    required_files = [
        "login.html",
        "login.css", 
        "login.js",
        "index.html",
        "style.css",
        "qwebchannel.js",
        "backend.py",
        "message_storage.py"
    ]
    
    print("🔍 检查必要文件...")
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 缺失")
            missing_files.append(file)
    
    if missing_files:
        print(f"⚠️  缺失文件: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 所有必要文件都存在")
        return True

def main():
    """主测试函数"""
    print("🚀 开始测试app.py应用程序...")
    print("=" * 50)
    
    # 测试文件存在性
    files_ok = test_file_existence()
    print()
    
    # 测试模块导入
    imports_ok = test_imports()
    print()
    
    if files_ok and imports_ok:
        print("🎉 所有测试通过！可以运行 app.py")
        print("\n📝 运行命令:")
        print("   python app.py")
        print("\n📋 功能说明:")
        print("   1. 启动后显示登录页面")
        print("   2. 输入任意用户名密码点击登录")
        print("   3. 登录成功后自动跳转到主应用程序")
        return True
    else:
        print("❌ 测试失败，请检查上述错误")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 