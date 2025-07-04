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
    try:
        user_ip, user_port = ssl_connect_sock.getpeername()
        print("user_ip", user_ip)
        print("user_port", user_port)
        received_msg = T.recv_msg(ssl_connect_sock)
        if received_msg is None:
            print("客户端已断开连接。")
            return None

        if received_msg.tag.name == "Login":
            T.handle_login(received_msg, user_ip, user_port, ssl_connect_sock)        
        
        elif received_msg.tag.name == "Register":
            reply_msg = T.handle_register(received_msg, ssl_connect_sock)           
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "Logout":
            reply_msg = T.handle_logout(received_msg)   
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetDirectory":
            T.handle_send_directory(received_msg, ssl_connect_sock)

        # elif received_msg.tag.name == "GetHistory":
        #     reply_msg = T.handle_get_history(received_msg)
        #     ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetPublicKey":
            T.handle_get_public_key(received_msg, ssl_connect_sock)

        # elif received_msg.tag.name == "Alive":
        #     reply_msg = T.handle_alive(received_msg)
        #     ssl_connect_sock.sendall(serialize(reply_msg))

        # elif received_msg.tag.name == "BackUp":
        #     reply_msg = T.handle_backup(received_msg)
        #     ssl_connect_sock.sendall(serialize(reply_msg))

        return True

    except ConnectionResetError:
        print("客户端连接被重置。")
        return None
    except Exception as e:
        print(f"发生错误: {e}")
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