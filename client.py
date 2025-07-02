import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import pprint
import p2p as P
import Transaction_Client as T
from serializer import serialize, deserialize
CA_FILE = "ca.crt"
SERVER_HOSTNAME = 'SERVER' 
ip_port = ("127.0.0.1", 47474) # Server's ip and port
# ip_port = ("10.122.212.156", 47474) # Server's ip and port

def bind_to_free_port():
    """
    创建一个socket并绑定到一个由操作系统自动分配的空闲端口。
    返回绑定好的socket和它实际使用的端口号。
    """
    try:
        # 1. 创建一个socket
        sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
        
        # 2. 调用bind，主机地址设为 "0.0.0.0" 或 "127.0.0.1"，端口号设为 0
        # "0.0.0.0" 表示监听所有可用的网络接口
        sock.bind(("0.0.0.0", 0)) 
        
        # 3. bind之后，通过getsockname()获取操作系统实际分配的端口号
        port = sock.getsockname()[1]
        
        print(f"操作系统已成功分配端口: {port}")
        
        return sock, port
        
    except Exception as e:
        print(f"无法绑定到空闲端口: {e}")
        return None, None
# --- 使用 ---
# 获取一个绑定好空闲端口的socket
p2p_server_sock, my_p2p_port = bind_to_free_port() # 客户端的的监听端口，用于等待联系人连接

def msg_process(ssl_connect_sock):
    received_msg = T.recv_msg(ssl_connect_sock)
    if received_msg is None:
        print("客户端已断开连接。")
        return None

    # # print(f"服务器回复: {received_msg}")
    # # if received_msg.tag.name == "SuccessRegister":
    # #     print(f"注册成功: {received_msg}")
    # #     return True

    # # elif received_msg.tag.name == "FailRegister":
    # #     print(f"注册失败: {received_msg}")

    # elif received_msg.tag.name == "SuccessLogin":
    #     print(f"登录成功: {received_msg}")

    # elif received_msg.tag.name == "FailLogin":
    #     print(f"登录失败: {received_msg}")

def User_evnets_process(ssl_connect_sock):
    T.handle_get_directory(ssl_connect_sock) # update the directory from server
    P.init_directory(ssl_connect_sock) # output the local directory
    while True:
        choice = input("which friend do you want to send message to: ").strip()
        if choice == "exit":
            print("客户端正在关闭...")
            return None

        if choice == "logout":
            T.handle_logout(ssl_connect_sock)
            return True
        
        if choice == "history":
            T.handle_get_history(ssl_connect_sock)
            return True

        if P.choose_friend(ssl_connect_sock, choice) is None: # 这一步会进入Chat
            return None

def boot(): # TO_DO 客户端首先要确定自己的端口
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        context.load_verify_locations(CA_FILE)
        context.load_cert_chain(certfile = "client.crt", keyfile = "client_rsa_private.pem.unsecure")
        context.verify_mode = ssl.CERT_REQUIRED

        with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as s:
            with context.wrap_socket(s, server_hostname=SERVER_HOSTNAME) as ssl_connect_sock:
                ssl_connect_sock.connect(ip_port)

                print("--- 成功连接到服务器 ---")
                print("服务器证书信息:")
                pprint.pprint(ssl_connect_sock.getpeercert())
                print("------------------------\n")

                if login_screen(ssl_connect_sock, my_p2p_port):
                    while True:

                        if User_evnets_process(ssl_connect_sock) is None:
                            break
                        
                        # if msg_process(ssl_connect_sock) is None:
                        #     break

    except FileNotFoundError:
        print(f"\n错误: 找不到CA证书文件 '{CA_FILE}'。")
    except ssl.SSLCertVerificationError as e:
        print(f"\n错误: 证书验证失败! {e}")
    except ConnectionRefusedError:
        print("错误: 连接被拒绝。服务器可能未运行或被防火墙阻止。")
    except Exception as e:
        print(f"发生未知错误: {e}")

    print("客户端已关闭。")

def login_screen(ssl_connect_sock, my_p2p_port) -> bool:
    for _ in range(10):
        opt = input("plesse input login / register / exit: ")
        if opt == "login":          
            if T.handle_login(ssl_connect_sock, my_p2p_port): # TO_DO 在boot()的端口和IP基础上，建立监听socket，等待联系人连接
                return True # 如果登录成功，则进入聊天界面，否则还处于for循环

        elif opt == "register":
            T.handle_register(ssl_connect_sock) 
            # 注册失败/成功，都继续for循环，等待下一步动作，直到达到10次循环/exit/成功login
        
        elif opt == "exit":
            return False
            # 输入exit，则直接退出

        else:
            print("invalid input")

    return False
    # 如果循环次数达到上限，则返回False

def main():
    boot()

main()