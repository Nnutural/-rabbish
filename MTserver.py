# --- START OF FILE server.py (Modified for Multithreading) ---
from sys import setswitchinterval
import schema as S
import datetime as dt
import time
import socket as skt
import json
import ssl
import uuid
import Transaction_Server as T
from serializer import serialize, deserialize
import threading

# 服务器IP和端口保持不变
ip_port = ("", 47474)

def msg_process(ssl_connect_sock):
    """
    处理来自单个客户端的一条消息。
    这个函数保持完全不变。
    """
    try:
        user_ip, user_port = ssl_connect_sock.getpeername()
        print("user_ip", user_ip)
        print("user_port", user_port)
        received_msg = T.recv_msg(ssl_connect_sock)
        if received_msg is None:
            print("客户端已断开连接。")
            return None


        # --- 登录请求是特例，因为它需要发送分包数据，在处理函数内部发送 ---
        if received_msg.tag.name == "LoginMsg": # 注意：你的schema里是LoginMsg
            # handle_login 会自己处理发送逻辑，因为它包含大文件传输
            T.handle_login(received_msg, user_ip, user_port, ssl_connect_sock)
            return True # 即使登录失败，连接也保持

        # --- 其他请求，服务器处理后统一返回响应 ---
        reply_msg = None
        if received_msg.tag.name == "RegisterMsg": # 注意：你的schema里是RegisterMsg
            reply_msg = T.handle_register(received_msg)
        elif received_msg.tag.name == "LogoutMsg":
            reply_msg = T.handle_logout(received_msg)
        elif received_msg.tag.name == "GetDirectory":
            reply_msg = T.handle_send_directory(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetHistory":
            reply_msg = T.handle_get_history(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetPublicKey":
            reply_msg = T.handle_get_public_key(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "Alive":
            reply_msg = T.handle_alive(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "BackUp":
            reply_msg = T.handle_backup(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        # 如果生成了回复消息，就发送它
        if reply_msg:
            ssl_connect_sock.sendall(serialize(reply_msg))

        return True # 表示连接应保持

    except ConnectionResetError:
        # 这是客户端强制关闭连接的正常情况
        return None
    except Exception as e:
        print(f"处理消息时发生错误: {e}")
        return None

def client_handler(connect_sock, address, context):
    """
    2. 新建的客户端处理函数，每个线程运行此函数。
    它负责处理一个客户端的完整生命周期。
    """
    print(f"线程 {threading.get_ident()}: 开始处理来自 {address} 的新连接。")
    try:
        # 使用 'with' 语句进行SSL握手并自动管理资源
        with context.wrap_socket(connect_sock, server_side=True) as ssl_connect_sock:
            print(f"线程 {threading.get_ident()}: 与 {address} 的SSL握手成功。")
            
            # 循环处理来自这个特定客户端的消息
            while True:
                if msg_process(ssl_connect_sock) is None:
                    break  # 客户端断开连接或发生错误，退出循环

    except ssl.SSLError as e:
        print(f"线程 {threading.get_ident()}: 来自 {address} 的SSL错误: {e}")
    except Exception as e:
        print(f"线程 {threading.get_ident()}: 处理客户端 {address} 时发生意外错误: {e}")
    finally:
        print(f"线程 {threading.get_ident()}: 与 {address} 的连接已关闭。")


def main():
    """
    服务器主函数
    """
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile="server.crt", keyfile="server_rsa_private.pem.unsecure")
        context.load_verify_locations("ca.crt")
        context.verify_mode = ssl.CERT_REQUIRED

        with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as sk:
            sk.bind(ip_port)
            sk.listen(10)  # 增加监听队列大小
            print(f'服务器已在 {ip_port} 启动，等待客户端连接...')

            # 3. 主线程的无限循环，只负责接受连接并创建新线程
            while True:
                # 阻塞等待新连接
                connect_sock, address = sk.accept()
                
                # 创建一个新的线程来处理客户端连接
                client_thread = threading.Thread(
                    target=client_handler,
                    args=(connect_sock, address, context) # 将需要的参数传给线程
                )
                # 设置为守护线程，这样主程序退出时子线程也会被强制退出
                client_thread.daemon = True 
                client_thread.start() # 启动线程

    except FileNotFoundError as e:
        print(f"\n错误: 找不到证书文件 '{e.filename}'。")
    except KeyboardInterrupt:
        print("\n检测到用户中断(Ctrl+C)，正在关闭服务器...")
    except Exception as e:
        print(f"服务器启动失败或运行时发生致命错误: {e}")
    finally:
        print("服务器已关闭。")

# --- 程序入口 ---
if __name__ == "__main__":
    main()

# --- END OF FILE server.py ---