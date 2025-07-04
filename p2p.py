# nnutural/-rabbish/-rabbish-ee4f00c467646964da558b8f7ce8d801ff83754b/p2p.py

import socket as skt
import ssl
import schema as S
import Transaction_Client as T
import json
import datetime as dt
from serializer import serialize, deserialize
import threading
import pprint
import time
import uuid
import os
import base64

contacts_map = {}
MY_USERNAME = "" 
CA_FILE = "ca.crt"
CLIENT_CERT_FILE = "client.crt"
PEER_HOSTNAME = 'CLIENT'
CLIENT_KEY_FILE = "client_rsa_private.pem.unsecure"

def save_received_file(transfer_info: dict, current_user: str):
    file_name = transfer_info['file_name']
    file_type = transfer_info['file_type']
    full_data = transfer_info['data']
    save_dir = ""
    try:
        if file_type == 'image': save_dir = os.path.join('user', current_user, 'image')
        elif file_type == 'audio': save_dir = os.path.join('user', current_user, 'audio')
        elif file_type == 'file': save_dir = os.path.join('user', current_user, 'file')
        else:
            print(f"[警告] 未知的文件类型 '{file_type}'，将保存到 'downloads' 目录。")
            save_dir = os.path.join('user', current_user, 'downloads')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, file_name)
        with open(save_path, 'wb') as f: f.write(full_data)
        print(f"\n[文件保存] 文件 '{file_name}' 已成功保存至: {save_path}")
    except Exception as e: print(f"\n[文件保存] 保存 '{file_name}' 时出错: {e}")

def handle_p2p_file_reception(p2p_sock: ssl.SSLSocket, start_msg: S.StartTransferMsg, current_user: str):
    transfer_id = start_msg.transfer_id
    file_name = start_msg.file_name
    print(f"\n[文件接收] 准备接收 '{file_name}' (ID: {transfer_id})...")
    received_data = bytearray()
    chunks_received = 0
    total_chunks = start_msg.total_chunks
    while chunks_received < total_chunks:
        msg = recv_p2p_msg(p2p_sock)
        if msg is None:
            print(f"\n[文件接收] 在接收 '{file_name}' 期间连接中断。传输失败。")
            return
        if not hasattr(msg, 'transfer_id') or msg.transfer_id != transfer_id:
            print(f"\n[文件接收] 错误: 在等待ID为'{transfer_id}'的数据块时，收到了一个无关的消息。")
            continue
        if isinstance(msg, S.DataChunkMsg):
            try:
                if msg.chunk_index != chunks_received:
                    print(f"\n[文件接收] 错误: 期望接收块 {chunks_received}，但收到了块 {msg.chunk_index}。")
                    return
                decoded_data = base64.b64decode(msg.data)
                received_data.extend(decoded_data)
                chunks_received += 1
                print(f"\r  > 正在接收 '{file_name}': {chunks_received}/{total_chunks} 块...", end="")
            except Exception as e:
                print(f"\n[文件接收] 处理数据块 {msg.chunk_index} 时失败: {e}")
                return
        elif isinstance(msg, S.EndTransferMsg):
            print(f"\n[文件接收] 错误: 在所有数据块接收完成前，过早地收到了结束信号。")
            return
    print()
    final_msg = recv_p2p_msg(p2p_sock)
    if isinstance(final_msg, S.EndTransferMsg) and final_msg.transfer_id == transfer_id:
        if final_msg.status == 'success':
            print(f"[文件接收] '{file_name}' 传输校验成功！")
            transfer_info = {'file_name': file_name, 'file_type': start_msg.file_type, 'data': received_data}
            save_received_file(transfer_info, current_user)
        else:
            print(f"[文件接收] 对端取消了 '{file_name}' 的传输 (状态: {final_msg.status})。")
    else: print(f"\n[文件接收] 错误: 未收到有效的结束信号。")

def create_secure_connection(server_ip_port, ca_file, cert_file, key_file, peer_hostname):
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(ca_file)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
        ssl_sock = context.wrap_socket(sock, server_hostname = peer_hostname)
        ssl_sock.connect(server_ip_port)
        print("--- 成功连接到服务器 ---")
        pprint.pprint(ssl_sock.getpeercert())
        print("------------------------\n")
        return ssl_sock
    except FileNotFoundError as e: print(f"\n错误: 找不到证书文件 '{e.filename}'。请确保文件存在于正确的位置。"); return None
    except ssl.SSLCertVerificationError as e: print(f"\n错误: 服务器证书验证失败! {e}"); return None
    except ConnectionRefusedError: print(f"错误: 连接被拒绝。服务器({server_ip_port})可能未运行或被防火墙阻止。"); return None
    except skt.gaierror: print(f"错误: 无法解析主机名 '{peer_hostname}' 或 IP '{server_ip_port[0]}'"); return None
    except ssl.SSLError as e: print(f"SSL握手失败: {e}"); return None
    except ConnectionResetError: print(f"连接已重置。"); return None
    except Exception as e: print(f"创建安全连接时发生未知错误: {e}"); return None

def recv_p2p_msg(ssl_connect_sock):
    try:
        len_bytes = ssl_connect_sock.recv(4)
        if not len_bytes: return None
        msg_len = int.from_bytes(len_bytes, byteorder='big')
        json_bytes = ssl_connect_sock.recv(msg_len)
        if not json_bytes: return None
        msg_dict = json.loads(json_bytes.decode("UTF-8"))
        return deserialize(msg_dict)
    except (ConnectionResetError, json.JSONDecodeError) as e: print(f"\n[Chat] Error receiving P2P message: {e}"); return None
    except UnicodeDecodeError as e: print(f"\n[Chat] CRITICAL: UnicodeDecodeError during P2P receive: {e}"); return None

def p2p_listener(p2p_server_sock, chat_queue):
    p2p_ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    p2p_ssl_context.verify_mode = ssl.CERT_REQUIRED
    p2p_ssl_context.load_verify_locations(CA_FILE)
    p2p_ssl_context.load_cert_chain(certfile=CLIENT_CERT_FILE, keyfile=CLIENT_KEY_FILE)
    if not p2p_ssl_context:
        print("[P2P Listener] SSL上下文创建失败，监听线程退出。")
        return

    print("[P2P Listener] 线程已启动，等待安全的P2P连接...")
    p2p_server_sock.listen()
    while True:
        try:
            conn, addr = p2p_server_sock.accept()
            # --- 修正处: 将之前导致语法错误的换行合并为一行 ---
            print(f"\n[P2P Listener] 接受到来自 {addr} 的TCP连接，正在进行SSL握手...")
            
            ssl_conn = p2p_ssl_context.wrap_socket(conn, server_side=True)
            print(f"[P2P Listener] 与 {addr} 的SSL握手成功！")
            chat_queue.put(ssl_conn)

        except ssl.SSLError as e:
            print(f"\n[P2P Listener] 来自 {addr} 的SSL握手失败: {e}")
        except Exception as e:
            print(f"\n[P2P Listener] 发生错误: {e}")

def run_p2p_chat_session(ssl_connect_sock, friend_name, current_user, user_id, first_message=None):
    global MY_USERNAME
    MY_USERNAME = current_user
    with ssl_connect_sock:
        print(f"--- 已连接! 您可以与 {friend_name} 开始聊天了。 ---")
        print("--- 输入 '/exit' 结束聊天。 ---")
        recv_thread = threading.Thread(target=receiver_thread_func, args=(ssl_connect_sock, friend_name, first_message), daemon=True)
        recv_thread.start()
        while True:
            msg_content = input("You: ")
            if not recv_thread.is_alive(): break
            if msg_content.strip().lower() == '/exit': break
            if msg_content.lower().startswith('/send '):
                parts = msg_content.split(' ', 2)
                if len(parts) < 3:
                    print("命令用法: /send <type> <filename>")
                    print("支持的类型: image, audio, file")
                    continue
                _, file_type, file_name = parts
                if file_type.lower() in ['image', 'audio', 'file']:
                    send_large_data_p2p(ssl_connect_sock, current_user, file_type.lower(), file_name)
                else:
                    print(f"不支持的文件类型: '{file_type}'。")
            else:
                msg_to_send = S.MessageMsg(
                    message_id=str(uuid.uuid4()), source_id=user_id,
                    sender_name=current_user, receiver_name=friend_name,
                    content=msg_content
                )
                if T.handle_send_message(ssl_connect_sock, msg_to_send):
                    now = dt.datetime.now()
                    friend_id = contacts_map.get(friend_name, {}).get("id")
                    if friend_id:
                        T.save_msg(
                            current_user=current_user, contact_id=friend_id, sender="user",
                            content=msg_content, time=now.strftime("%H:%M:%S"), date=now.strftime("%Y-%m-%d")
                        )
                else: break

def handle_incoming_chat_session(incoming_socket, current_user, user_id):
    first_msg = recv_p2p_msg(incoming_socket)
    if isinstance(first_msg, S.MessageMsg):
        friend_name = first_msg.sender_name
        run_p2p_chat_session(
            ssl_connect_sock=incoming_socket,
            friend_name=friend_name,
            current_user=current_user,
            user_id=user_id,
            first_message=first_msg
        )
    else:
        print("[!] 收到了无效的P2P初始消息，连接已关闭。")
        incoming_socket.close()

def receiver_thread_func(ssl_connect_sock, friend_name, first_message=None):
    if first_message and isinstance(first_message, S.MessageMsg):
        print(f"\r[{first_message.sender_name} 说]: {first_message.content}      ")
        now = dt.datetime.now()
        friend_id = contacts_map.get(friend_name, {}).get("id")
        if friend_id:
            T.save_msg(
                current_user=MY_USERNAME, contact_id=friend_id, sender="contact",
                content=first_message.content, time=now.strftime("%H:%M:%S"), date=now.strftime("%Y-%m-%d")
            )
        print("You: ", end="", flush=True)
    while True:
        msg = recv_p2p_msg(ssl_connect_sock)
        if msg is None:
            print(f"\n[聊天] {friend_name} 已断开连接。按回车键退出聊天。")
            break
        if isinstance(msg, S.MessageMsg) and msg.sender_name == friend_name:
            print(f"\r[{msg.sender_name} 说]: {msg.content}      ")
            now = dt.datetime.now()
            friend_id = contacts_map.get(friend_name, {}).get("id")
            if friend_id:
                T.save_msg(
                    current_user=MY_USERNAME, contact_id=friend_id, sender="contact",
                    content=msg.content, time=now.strftime("%H:%M:%S"), date=now.strftime("%Y-%m-%d")
                )
            print("You: ", end="", flush=True)
        elif isinstance(msg, S.StartTransferMsg):
            handle_p2p_file_reception(ssl_connect_sock, msg, MY_USERNAME)
            print("You: ", end="", flush=True)

def start_p2p_chat(friend_name, ip, port, current_user, user_id):
    print(f"--- 正在尝试连接到 {friend_name} at {ip}:{port} ---")
    ssl_connect_sock = create_secure_connection(
        server_ip_port=(ip, port), ca_file=CA_FILE,
        cert_file=CLIENT_CERT_FILE, key_file=CLIENT_KEY_FILE,
        peer_hostname=PEER_HOSTNAME
    )
    if not ssl_connect_sock:
        print(f"连接失败，请检查对方是否在线或网络设置。")
        return
    run_p2p_chat_session(ssl_connect_sock, friend_name, current_user, user_id)

def send_large_data_p2p(p2p_sock, current_user, file_type, file_name):
    filepath = ""
    try:
        base_dir = os.path.join('user', current_user)
        if file_type == 'image': filepath = os.path.join(base_dir, 'image', file_name)
        elif file_type == 'audio': filepath = os.path.join(base_dir, 'audio', file_name)
        elif file_type == 'file': filepath = os.path.join(base_dir, 'file', file_name)
        else: print(f"[P2P 发送错误] 不支持的文件类型: {file_type}"); return False
        with open(filepath, 'rb') as f: data_bytes = f.read()
    except FileNotFoundError: print(f"[P2P 发送错误] 文件未找到: {filepath}"); return False
    except Exception as e: print(f"[P2P 发送错误] 读取文件时出错: {e}"); return False
    transfer_id = str(uuid.uuid4())
    try:
        total_size = len(data_bytes)
        total_chunks = (total_size + 4096 - 1) // 4096
        start_msg = S.StartTransferMsg(
            transfer_id=transfer_id, file_type=file_type, file_name=file_name,
            total_size=total_size, total_chunks=total_chunks, chunk_size=4096
        )
        p2p_sock.sendall(serialize(start_msg))
        print(f"[P2P 发送] 开始传输 '{file_name}'...")
        for i in range(total_chunks):
            start, end = i * 4096, (i + 1) * 4096
            data_chunk = data_bytes[start:end]
            encoded_chunk_str = base64.b64encode(data_chunk).decode('ascii')
            chunk_msg = S.DataChunkMsg(transfer_id=transfer_id, chunk_index=i, data=encoded_chunk_str)
            p2p_sock.sendall(serialize(chunk_msg))
        end_msg = S.EndTransferMsg(transfer_id=transfer_id, status='success')
        p2p_sock.sendall(serialize(end_msg))
        print(f"[P2P 发送] 传输 '{file_name}' 完成。")
        return True
    except (BrokenPipeError, ConnectionResetError): print(f"\n[P2P 发送错误] 连接中断，传输 '{file_name}' 失败。"); return False
    except Exception as e: print(f"\n[P2P 发送错误] 传输 '{file_name}' 失败: {e}"); return False

def init_directory(current_user):
    global contacts_map
    try:
        with open(f"user/{current_user}/data.json", "r", encoding="UTF-8") as f:
            directory_data = json.load(f)
        contacts_map = {c["name"]: c for c in directory_data.get("contacts", [])}
        print("\n--- Your Contact List ---")
        if not contacts_map: print("Your contact list is empty.")
        else:
            for name, details in contacts_map.items():
                print(f"- {name} ({details.get('status', 'unknown')})")
        print("-------------------------\n")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[Error] Loading contact list failed: {e}")
        contacts_map = {}

def choose_friend(ssl_connect_sock, choice, current_user, user_id):
    if choice == "exit": return None
    if choice in contacts_map:
        friend_details = contacts_map[choice]
        if friend_details.get("status") == "online":
            print(f"======= {choice} is online. Trying to connect... =======")
            address_str = friend_details.get("address")
            if not address_str:
                print(f"[Error] {choice} is online but has no address information.")
                return True
            try:         
                ip, port_str = address_str.split(':')
                port = int(port_str)
                start_p2p_chat(choice, ip, port, current_user, user_id)
                return True
            except (ValueError, IndexError) as e:
                print(f"[Error] Invalid address format for {choice}: '{address_str}'. Error: {e}")
                return True
        else:
            print(f"======= {choice} is offline. You can leave an offline message. =======")
            return True
    else:
        print("======= The user is not in your contact list. =======")
        return True