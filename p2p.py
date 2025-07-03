# --- START OF MODIFIED p2p.py ---
import socket as skt
import ssl
import schema as S
import Transaction_Client as T
import json
from serializer import serialize, deserialize
import threading
import pprint
import time
import uuid
# --- MODIFICATION START ---
# contacts_map {"张三": {"id": 1, "name": "张三", ...}, "李四": {...}}
contacts_map = {}
# --- MODIFICATION END ---
# A global variable to hold the current user's name after login
MY_USERNAME = "" 
CA_FILE = "ca.crt"
CLIENT_CERT_FILE = "client.crt"
PEER_HOSTNAME = 'CLIENT'  # 可能生成时需要修改 !!!!!!!!
CLIENT_KEY_FILE = "client_rsa_private.pem.unsecure"

# --- NEW ENCAPSULATED FUNCTION ---

def create_secure_connection(server_ip_port, ca_file, cert_file, key_file, peer_hostname):
    """
    创建并返回一个到服务器的安全SSL/TLS连接。

    此函数封装了SSL上下文创建、证书加载、套接字包装和连接的所有步骤。

    Args:
        server_ip_port (tuple): 服务器的 (ip, port) 元组。
        ca_file (str): CA证书文件的路径。
        cert_file (str): 客户端证书文件的路径。
        key_file (str): 客户端私钥文件的路径。
        server_hostname (str): 用于证书验证和SNI的服务器主机名。

    Returns:
        ssl.SSLSocket: 如果连接成功，返回已连接的安全套接字。
        None: 如果发生任何错误（文件未找到、证书验证失败、连接被拒绝等）。
    """
    try:
        # 1. 创建SSL上下文
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_mode = ssl.CERT_REQUIRED

        # 2. 加载用于验证服务器的CA证书
        context.load_verify_locations(ca_file)

        # 3. 加载客户端自己的证书和私钥（用于服务器验证客户端）
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)

        # 4. 创建一个普通的TCP套接字
        sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)

        # 5. 将普通套接字包装成SSL套接字
        ssl_sock = context.wrap_socket(sock, server_hostname = peer_hostname)

        # 6. 连接到服务器
        ssl_sock.connect(server_ip_port)

        print("--- 成功连接到服务器 ---")
        print("服务器证书信息:")
        pprint.pprint(ssl_sock.getpeercert())
        print("------------------------\n")

        return ssl_sock # 返回一个普通的socket，而不是ssl_sock

# def create_connection(server_ip_port, ca_file, cert_file, key_file, server_hostname):
#     try:
#         # 4. 创建一个普通的TCP套接字
#         sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)

#         # 6. 连接到服务器
#         sock.connect(server_ip_port)

#         print("------------------------\n")

#         return sock # 返回一个普通的socket，而不是ssl_sock

    except FileNotFoundError as e:
        print(f"\n错误: 找不到证书文件 '{e.filename}'。请确保文件存在于正确的位置。")
        return None
    except ssl.SSLCertVerificationError as e:
        print(f"\n错误: 服务器证书验证失败! {e}")
        return None
    except ConnectionRefusedError:
        print(f"错误: 连接被拒绝。服务器({server_ip_port})可能未运行或被防火墙阻止。")
        return None
    except skt.gaierror:
        print(f"错误: 无法解析主机名 '{peer_hostname}' 或 IP '{server_ip_port[0]}'")
        return None
    except ssl.SSLError as e:
        print(f"SSL握手失败: {e}")
        return None
    except ConnectionResetError:
        print(f"连接已重置。")
        return None
    except Exception as e:
        print(f"创建安全连接时发生未知错误: {e}")
        return None

def recv_p2p_msg(ssl_connect_sock):
    """
    Receives and deserializes a P2P message object.
    This is used for P2P communication within this file.
    """
    try:
        len_bytes = ssl_connect_sock.recv(4)
        if not len_bytes:
            return None
        msg_len = int.from_bytes(len_bytes, byteorder='big')
        json_bytes = ssl_connect_sock.recv(msg_len)
        if not json_bytes:
            return None
            
        # The utf-8 decode error happened here because json_bytes
        # contained an extra, invalid length prefix.
        msg_dict = json.loads(json_bytes.decode("UTF-8"))
        return deserialize(msg_dict)
        
    except (ConnectionResetError, json.JSONDecodeError) as e:
        print(f"\n[Chat] Error receiving P2P message: {e}")
        return None
    except UnicodeDecodeError as e:
        # This is the error you were seeing. It's useful to log it if it happens again.
        print(f"\n[Chat] CRITICAL: UnicodeDecodeError during P2P receive: {e}")
        return None
# --- P2P LISTENER LOGIC (Runs in a separate thread) ---

def handle_incoming_chat(ssl_connect_sock, addr):
    """
    Handles a single, established P2P chat connection.
    This function is for the person RECEIVING the chat request.
    """
    print(f"\n[P2P] Incoming connection from {addr}. Starting chat session.")
    try:
        with ssl_connect_sock:
            while True:
                msg = recv_p2p_msg(ssl_connect_sock) # 接收到了发送给当前用户的消息
                if msg is None:
                    print(f"\n[Chat] Peer {addr} has disconnected.")
                    break
                if isinstance(msg, S.MessageMsg): # 应该保存到历史记录，等待查看


                    print(f"\r[{msg.sender_name} says]: {msg.content}      ")
                    print("You: ", end="", flush=True) # Re-print the input prompt
                else:
                    print(f"\n[Chat] Received unknown message type from {addr}.")
    except Exception as e:
        print(f"\n[Chat] Error with peer {addr}: {e}")
    finally:
         print(f"[P2P] Session with {addr} ended.")

# --- MODIFIED: P2P监听器，现在使用SSL ---
def p2p_listener(p2p_server_sock):

    p2p_ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    p2p_ssl_context.verify_mode = ssl.CERT_REQUIRED

    # 2. 加载用于验证服务器的CA证书
    p2p_ssl_context.load_verify_locations(CA_FILE)

    # 3. 加载客户端自己的证书和私钥（用于服务器验证客户端）
    p2p_ssl_context.load_cert_chain(certfile=CLIENT_CERT_FILE, keyfile=CLIENT_KEY_FILE)

    if not p2p_ssl_context:
        print("[P2P Listener] SSL上下文创建失败，监听线程退出。")
        return

    print("[P2P Listener] 线程已启动，等待安全的P2P连接...")
    p2p_server_sock.listen()
    while True:
        try:
            conn, addr = p2p_server_sock.accept()
            print(f"\n[P2P Listener] 接受到来自 {addr} 的TCP连接，正在进行SSL握手...")
            
            # 关键修复：使用SSL上下文包装接受的连接 !!!!!!
            ssl_conn = p2p_ssl_context.wrap_socket(conn, server_side=True)
            
            print(f"[P2P Listener] 与 {addr} 的SSL握手成功！")
            handler_thread = threading.Thread(target=handle_incoming_chat, args=(ssl_conn, addr), daemon=True)
            handler_thread.start()
        except ssl.SSLError as e:
            print(f"\n[P2P Listener] 来自 {addr} 的SSL握手失败: {e}")
        except Exception as e:
            print(f"\n[P2P Listener] 发生错误: {e}")

# --- P2P CHAT INITIATOR LOGIC ---

def receiver_thread_func(ssl_connect_sock, friend_name: str):
    """
    Dedicated thread to only receive messages from a friend.
    This is for the person who INITIATED the chat.
    """
    while True:
        msg = recv_p2p_msg(ssl_connect_sock)
        if msg is None:
            print(f"\n[Chat] {friend_name} has disconnected. Press Enter to exit chat.")
            break
        if isinstance(msg, S.MessageMsg)  and msg.sender_name == friend_name:
            # \r moves cursor to beginning of line, then we overwrite the "You: " prompt
            print(f"\r[{msg.sender_name} says]: {msg.content}      ")
            print("You: ", end="", flush=True) # Re-print the input prompt

def start_p2p_chat(friend_name, ip, port, current_user):
    """
    Initiates a P2P chat session with a friend.
    """
    print(f"--- Attempting to connect to {friend_name} at {ip}:{port} ---")
    try:
        ssl_connect_sock = create_secure_connection(
            server_ip_port = (ip, port),
            ca_file = CA_FILE,
            cert_file = CLIENT_CERT_FILE,
            key_file = CLIENT_KEY_FILE,
            peer_hostname = PEER_HOSTNAME
        )

        if not ssl_connect_sock:
            print(f"连接失败，请检查网络连接和证书文件。")
            return

        # with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as p2p_client_sock:
        #     p2p_client_sock.connect((ip, port))
        with ssl_connect_sock:
            print(f"--- Connection successful! You can now chat with {friend_name}. ---")
            print("--- Type '/exit' to end the chat. ---")
            
            # Start a thread to listen for incoming messages
            recv_thread = threading.Thread(target=receiver_thread_func, args=(ssl_connect_sock, friend_name), daemon=True)
            recv_thread.start()

            # Main thread loop for sending messages
            while True:
                msg_content = input("You: ")
                if not recv_thread.is_alive(): # Check if the friend disconnected
                    break
                if msg_content.strip().lower() == '/exit': # 退出当前聊天事件
                    break
                
                '''
                此处决定发送什么种类的消息
                '''
                if msg_content.startswith('/file'):
                    pass
                if msg_content.startswith('/voice'):
                    pass
                if msg_content.startswith('/image'):
                    pass
                

                # Create and send the message object
                msg_to_send = S.MessageMsg(
                    message_id = str(uuid.uuid4()),
                    sender_name = current_user, ## 用户名什么时候赋值？？
                    receiver_name = friend_name,
                    content = msg_content, 
                    time=int(time.time())
                )

                

                if not T.handle_send_message(ssl_connect_sock, msg_to_send):
                    break # Stop if sending fails

    except ConnectionRefusedError:
        print(f"\n[Connection Error] {friend_name} is not available or refused the connection.")
    except Exception as e:
        print(f"\n[Chat Error] An error occurred: {e}")
    finally:
        print(f"--- Chat with {friend_name} ended. Returning to main menu. ---")



def init_directory(ssl_connect_sock, current_user):
    # --- MODIFICATION START ---
    global contacts_map
    ''' 从本地 data.json 加载联系人列表到内存中 '''
    try:
        with open(f"user/{current_user}/data.json", "r", encoding = "UTF-8") as f:
            directory_data = json.load(f)

        # 使用字典推导式高效地创建 contacts_map
        # 键是联系人名字，值是联系人完整的字典信息
        contacts_map = {c["name"]: c for c in directory_data.get("contacts", [])}
        
        print("\n--- Your Contact List ---")
        if not contacts_map:
            print("Your contact list is empty.")
        else:
            # 打印每个联系人的名字和状态
            for name, details in contacts_map.items():
                status = details.get("status", "unknown")
                print(f"- {name} ({status})")
        print("-------------------------\n")

    except FileNotFoundError:
        print(f"[Error] {current_user}/data.json not found. Cannot load contact list.")
        contacts_map = {}
    except json.JSONDecodeError:
        print(f"[Error] Failed to parse {current_user}/data.json. Contact list might be corrupted.")
        contacts_map = {}
    # --- MODIFICATION END ---


def choose_friend(ssl_connect_sock, choice, current_user):
    if choice == "exit":
        return None # 返回 None 表示希望主程序退出

    # --- MODIFICATION START ---
    # 在 contacts_map 中查找用户选择的好友
    if choice in contacts_map:
        friend_details = contacts_map[choice]
        
        # 检查好友状态
        if friend_details.get("status") == "online":
            print(f"======= {choice} is online. Trying to connect... =======")
            
            # 获取地址字符串，例如 "127.0.0.1:10000"
            address_str = friend_details.get("address")
            print(address_str)
            
            if not address_str:
                print(f"[Error] {choice} is online but has no address information.")
                return True # 返回 True 表示继续循环，让用户重新选择

            # 解析 IP 和端口
            try:         
                ip, port_str = address_str.split(':')
                port = int(port_str)
                # HERE IS THE KEY CHANGE: We call the chat function
                start_p2p_chat(choice, ip, port, current_user)

                # !!! After chat ends, we return True to go back to the contact list
                return True

            except (ValueError, IndexError) as e:
                print(f"[Error] Invalid address format for {choice}: '{address_str}'. Error: {e}")
                return True # 地址格式错误，让用户重新选择

        else: # 好友离线
            '''
            1. 
            2. 向服务器发送离线消息
            3. 更新好友的通讯录
            4. 更新自己的通讯录
            5. 更新服务器上的通讯录
            6. 更新服务器上的历史记录
            7. 更新自己的历史记录
            8. 更新好友的历史记录
            '''
            print(f"======= {choice} is offline. You can leave an offline message. =======")
            return True # 返回 True 表示继续循环，让用户重新选择
    else:
        print("======= The user is not in your contact list. =======")
        return True # 返回 True 表示继续循环，让用户重新选择
    # --- MODIFICATION END ---

# --- END OF MODIFIED p2p.py ---