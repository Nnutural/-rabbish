#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2P聊天客户端GUI启动脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gui_client import main
    
    if __name__ == "__main__":
        print("正在启动P2P聊天客户端GUI...")
        main()
        
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有必要的模块都已安装")
    sys.exit(1)
except Exception as e:
    print(f"启动失败: {e}")
    sys.exit(1) 