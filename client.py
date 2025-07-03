import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import pprint
import threading
import p2p as P
import Transaction_Client as T
from serializer import serialize, deserialize
CA_FILE = "ca.crt"
SERVER_HOSTNAME = 'SERVER' 
ip_port = ("127.0.0.1", 47474) # Server's ip and port
# ip_port = ("10.122.212.156", 47474) # Server's ip and port
CLIENT_CERT_FILE = "client.crt"
CLIENT_KEY_FILE = "client_rsa_private.pem.unsecure"
current_user = None

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

def User_evnets_process(ssl_connect_sock, current_user):
    T.handle_get_directory(ssl_connect_sock, current_user) # update the directory from server
    P.init_directory(ssl_connect_sock, current_user) # output the local directory
    while True:
        choice = input("which friend do you want to send message to: ").strip()
        if choice == "exit":
            print("客户端正在关闭...")
            return "exit"

        if choice == "logout":
            T.handle_logout(ssl_connect_sock, current_user)
            return "logout"
        
        if choice == "history":
            T.handle_get_history(ssl_connect_sock, current_user)
            continue

        if P.choose_friend(ssl_connect_sock, choice) is None: # 这一步会进入Chat
            return None

        P.init_directory(ssl_connect_sock, current_user) # output the local directory
        

def login_screen(ssl_connect_sock, my_p2p_port) -> bool:
    for _ in range(10):
        opt = input("plesse input login / register / exit: ")
        if opt == "login":  # 登录时需要发送自己的监听端口
            current_user = T.handle_login(ssl_connect_sock, my_p2p_port) # TO_DO 在boot()的端口和IP基础上，建立监听socket，等待联系人连接
            if current_user: 

                return current_user # 如果登录成功，则进入聊天界面，否则还处于for循环

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

def boot(): # TO_DO 客户端首先要确定自己的端口   

    # --- 使用 ---
    # 获取一个绑定好空闲端口的socket
    p2p_server_sock, my_p2p_port = bind_to_free_port() # 客户端的的监听端口，用于等待联系人连接
    global current_user

    if p2p_server_sock is None:
        print("无法绑定到空闲端口，请检查网络连接。")
        return

    try:
        # --- MODIFICATION START ---
        # 使用新函数建立连接
        ssl_connect_sock = P.create_secure_connection(
            server_ip_port = ip_port,
            ca_file = CA_FILE,
            cert_file = CLIENT_CERT_FILE,
            key_file = CLIENT_KEY_FILE,
            peer_hostname = SERVER_HOSTNAME
        )

        if not ssl_connect_sock:
            print("连接失败，请检查网络连接和证书文件。")
            return
        
        # 该主机上监听接口唯一，如果更换账号则在login时更换监听端口
        listening_thread = threading.Thread(target = P.p2p_listener, args=(p2p_server_sock, ), daemon=True) # 登录成功后就开始监听
        listening_thread.start()

        # with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as s:
        #     with context.wrap_socket(s, server_hostname=SERVER_HOSTNAME) as ssl_connect_sock:
        
        with ssl_connect_sock:
            login_result = login_screen(ssl_connect_sock, my_p2p_port)
            if login_result:
                current_user = login_result
                while True:
                    user_action = User_evnets_process(ssl_connect_sock, current_user)
                    if user_action == "exit": # 如果用户选择退出，则退出循环
                        break
                    else: # logout
                        login_result = login_screen(ssl_connect_sock, my_p2p_port)
                        if not login_result:
                            break
                        current_user = login_result  

    except (ConnectionResetError, BrokenPipeError) as e:
        print(f"\n错误: 与服务器的连接已意外断开。({e})")
    except KeyboardInterrupt:
        # 优雅地处理用户按 Ctrl+C 的情况
        print("\n检测到用户中断(Ctrl+C)，正在关闭客户端...")
    except Exception as e:
        # 捕获任何其他未预料到的错误，防止程序崩溃
        print(f"\n发生未知致命错误: {e}")
    finally:
        # 5. 清理资源
        #    这部分代码无论如何都会执行，是确保资源被释放的关键
        print("--- 开始清理和关闭客户端 ---")
        if p2p_server_sock:
            try:
                p2p_server_sock.close()
                print("P2P监听套接字已成功关闭。")
            except Exception as e:
                print(f"关闭P2P套接字时出错: {e}")
        
        # ssl_connect_sock 会被 'with' 语句自动关闭，所以这里无需手动关闭。
        # 这是 'with' 语句的强大之处。
        
        print("--- 客户端已关闭 ---")
    # --- MODIFICATION END ---

def main():
    boot()

main()