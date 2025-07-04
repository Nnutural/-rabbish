# nnutural/-rabbish/-rabbish-ee4f00c467646964da558b8f7ce8d801ff83754b/client.py

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
import queue
import sys
# --- 修改处: 增加 os 模块用于判断操作系统 ---
import os

# --- 修改处: 根据操作系统选择不同的模块导入 ---
IS_WINDOWS = os.name == 'nt'
if not IS_WINDOWS:
    import select

CA_FILE = "ca.crt"
SERVER_HOSTNAME = 'SERVER' 
ip_port = ("10.122.233.244", 47474)
CLIENT_CERT_FILE = "client.crt"
CLIENT_KEY_FILE = "client_rsa_private.pem.unsecure"
current_user = None
user_id = None
directory_update_event = threading.Event()
DIRECTORY_UPDATE_INTERVAL = 30
server_socket_lock = threading.Lock()

# --- 修改处: 重写此函数以兼容 Windows ---
def get_user_input(prompt):
    """
    获取用户输入。在非Windows系统上使用select实现非阻塞效果，
    在Windows上使用标准input()来避免兼容性问题。
    """
    if IS_WINDOWS:
        # 在Windows上，select不能用于sys.stdin，所以我们使用标准的阻塞式input。
        # 这意味着需要按回车才能检查收到的消息。
        return input(prompt)
    else:
        # 在Linux/macOS上，使用select可以实现带超时的非阻塞输入。
        sys.stdout.write(prompt)
        sys.stdout.flush()
        # 等待1秒，看sys.stdin是否可读
        ready, _, _ = select.select([sys.stdin], [], [], 1.0)
        if ready:
            return sys.stdin.readline().strip()
        return "" # 超时则返回空字符串

def bind_to_free_port():
    try:
        sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
        sock.bind(("0.0.0.0", 0)) 
        port = sock.getsockname()[1]
        print(f"操作系统已成功分配端口: {port}")
        return sock, port
    except Exception as e:
        print(f"无法绑定到空闲端口: {e}")
        return None, None

def periodic_directory_updater(ssl_sock, stop_event: threading.Event):
    global current_user
    print(f"[后台同步] 通讯录自动更新线程已启动 (每 {DIRECTORY_UPDATE_INTERVAL} 秒一次)。")
    while not stop_event.is_set():
        if stop_event.wait(DIRECTORY_UPDATE_INTERVAL):
            break 
        try:
            if current_user:
                with server_socket_lock:
                    print(f"\n[后台同步] 正在为 '{current_user}' 请求通讯录更新...")
                    success = T.handle_get_directory(ssl_sock, current_user)
                    if success:
                        print(f"[后台同步] 通讯录更新完成。请按回车查看更新后的提示。")
                    else:
                        print(f"[后台同步] 通讯录更新失败。")
                print("\rwhich friend do you want to send message to: ", end="")
        except (ConnectionResetError, BrokenPipeError):
            print("[后台同步] 连接断开，更新线程退出。")
            break
        except Exception as e:
            print(f"[后台同步] 线程发生错误: {e}")
    print("[后台同步] 通讯录自动更新线程已停止。")

def User_evnets_process(ssl_connect_sock, current_user, user_id, chat_queue):
    P.init_directory(current_user)
    prompt_text = "which friend do you want to send message to: "
    while True:
        try:
            incoming_socket = chat_queue.get_nowait()
            print(f"\n[!] 检测到新的P2P连接，正在建立会话...")
            P.handle_incoming_chat_session(incoming_socket, current_user, user_id)
            P.init_directory(current_user)
            continue
        except queue.Empty:
            # --- 修改处: 调用新的 get_user_input 函数 ---
            choice = get_user_input(prompt_text)
            
            if choice:
                if choice == "exit":
                    print("客户端正在关闭...")
                    return "exit"

                if choice == "logout":
                    with server_socket_lock:
                        T.handle_logout(ssl_connect_sock, current_user)
                    return "logout"

                if choice == "refresh":
                    print("正在手动刷新好友列表...")
                    with server_socket_lock:
                        T.handle_get_directory(ssl_connect_sock, current_user)
                    P.init_directory(current_user)
                    continue

                if P.choose_friend(ssl_connect_sock, choice, current_user, user_id) is None:
                    return None
                P.init_directory(current_user)

def login_screen(ssl_connect_sock, my_p2p_port):
    for _ in range(10):
        opt = input("plesse input login / register / exit: ")
        if opt == "login":
            with server_socket_lock:
                current_user, user_id = T.handle_login(ssl_connect_sock, my_p2p_port)
            if current_user and user_id: 
                return current_user, user_id
        elif opt == "register":
            with server_socket_lock:
                T.handle_register(ssl_connect_sock) 
        elif opt == "exit":
            return None, None
        else:
            print("invalid input")
    return None, None
    
def boot(): 
    p2p_server_sock, my_p2p_port = bind_to_free_port()
    global current_user 
    global user_id
    if p2p_server_sock is None: return

    incoming_chat_queue = queue.Queue()
    updater_thread = None
    stop_updater_event = threading.Event()
    try:
        ssl_connect_sock = P.create_secure_connection(
            server_ip_port=ip_port,
            ca_file=CA_FILE,
            cert_file=CLIENT_CERT_FILE,
            key_file=CLIENT_KEY_FILE,
            peer_hostname=SERVER_HOSTNAME
        )
        if not ssl_connect_sock: return
        
        listening_thread = threading.Thread(target=P.p2p_listener, args=(p2p_server_sock, incoming_chat_queue), daemon=True)
        listening_thread.start()

        with ssl_connect_sock:
            while True: 
                login_name, login_id = login_screen(ssl_connect_sock, my_p2p_port)
                if login_name and login_id:
                    current_user = login_name
                    user_id = login_id
                    P.MY_USERNAME = current_user
                    
                    print("登录成功，正在启动后台服务...")
                    stop_updater_event.clear()
                    updater_thread = threading.Thread(
                        target=periodic_directory_updater,
                        args=(ssl_connect_sock, stop_updater_event),
                        daemon=True
                    )
                    updater_thread.start()

                    user_action = User_evnets_process(ssl_connect_sock, current_user, user_id, incoming_chat_queue)
                    
                    print("正在停止后台同步线程...")
                    stop_updater_event.set()
                    if updater_thread: updater_thread.join(timeout=1)
                    
                    if user_action == "exit": break 
                    elif user_action == "logout":
                        print("您已注销，返回登录界面。")
                        current_user, user_id = None, None
                        continue 
                else: break

    except (ConnectionResetError, BrokenPipeError) as e: print(f"\n错误: 与服务器的连接已意外断开。({e})")
    except KeyboardInterrupt: print("\n检测到用户中断(Ctrl+C)，正在关闭客户端...")
    except Exception as e:
        # --- 修改处: 打印更详细的错误信息 ---
        import traceback
        print(f"\n发生未知致命错误: {e}")
        traceback.print_exc()

    finally:
        print("--- 开始清理和关闭客户端 ---")
        if stop_updater_event: stop_updater_event.set()
        if updater_thread and updater_thread.is_alive(): updater_thread.join(timeout=1)
        if p2p_server_sock:
            try:
                p2p_server_sock.close()
                print("P2P监听套接字已成功关闭。")
            except Exception as e: print(f"关闭P2P套接字时出错: {e}")
        print("--- 客户端已关闭 ---")

if __name__ == "__main__":
    boot()