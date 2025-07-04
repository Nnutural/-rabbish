import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import os
import pprint
import threading
import base64
import binascii
from serializer import serialize, deserialize
import Contacts as C
from typing import Dict, Any, Union
import Transaction_Server as T
import uuid
CHUNK_SIZE = 4096
active_transfers = {} # 用于存储当前正在接收的文件传输信息


def send_large_data_p2p(p2p_sock: ssl.SSLSocket, current_user: str, file_type: str, file_name: str):
    """
    (客户端P2P版本) 将本地文件分块发送给对端客户端。
    """
    filepath = ""
    try:
        base_dir = os.path.join('user', current_user)
        if file_type == 'image':
            filepath = os.path.join(base_dir, 'image', file_name)
        elif file_type == 'audio':
            filepath = os.path.join(base_dir, 'audio', file_name)
        elif file_type == 'file':
            filepath = os.path.join(base_dir, 'file', file_name)
        else:
            print(f"[P2P 发送错误] 不支持的文件类型: {file_type}")
            return False

        with open(filepath, 'rb') as f:
            data_bytes = f.read()

    except FileNotFoundError:
        print(f"[P2P 发送错误] 文件未找到: {filepath}")
        return False
    except Exception as e:
        print(f"[P2P 发送错误] 读取文件时出错: {e}")
        return False

    transfer_id = str(uuid.uuid4())
    try:
        total_size = len(data_bytes)
        total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE

        start_msg = S.StartTransferMsg(
            transfer_id=transfer_id, file_type=file_type, file_name=file_name,
            total_size=total_size, total_chunks=total_chunks, chunk_size=CHUNK_SIZE
        )
        p2p_sock.sendall(serialize(start_msg))
        print(f"[P2P 发送] 开始传输 '{file_name}'...")

        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            data_chunk = data_bytes[start:end]
            encoded_chunk_str = base64.b64encode(data_chunk).decode('ascii')
            
            chunk_msg = S.DataChunkMsg(
                transfer_id=transfer_id, chunk_index=i, data=encoded_chunk_str
            )
            p2p_sock.sendall(serialize(chunk_msg))
        
        end_msg = S.EndTransferMsg(transfer_id=transfer_id, status='success')
        p2p_sock.sendall(serialize(end_msg))
        print(f"[P2P 发送] 传输 '{file_name}' 完成。")
        return True

    except (BrokenPipeError, ConnectionResetError):
        print(f"\n[P2P 发送错误] 连接中断，传输 '{file_name}' 失败。")
        return False
    except Exception as e:
        print(f"\n[P2P 发送错误] 传输 '{file_name}' 失败: {e}")
        return False

# --- P2P Message Sending Handlers ---

def recv_msg(ssl_connect_sock):
    try:
        client_data_bytes = ssl_connect_sock.recv(4)
        if not client_data_bytes:
            return None

        datalength = int.from_bytes(client_data_bytes, byteorder='big')
        json_bytes = ssl_connect_sock.recv(datalength)
        if not json_bytes:
            return None

        msg_dict = json.loads(json_bytes.decode("UTF-8"))
        received_msg = deserialize(msg_dict)
        return received_msg
    except (ConnectionResetError, BrokenPipeError):
        print("与服务器的连接已断开。")
        return None
    except Exception as e:
        print(f"接收服务器消息时出错: {e}")
        return None

def recv_large_data(ssl_connect_sock, id, current_user):
    """
    循环接收一个完整的文件传输事务（Start -> Chunks -> End）。
    根据 StartTransferMsg 中的 file_type 决定保存路径。
    """
    while True:
        received_msg = recv_msg(ssl_connect_sock)
        if received_msg is None:
            print("[文件接收] 接收过程中连接中断。")
            # 如果有进行中的传输，标记为失败
            if id in active_transfers:
                del active_transfers[id]
            return

        tag_name = received_msg.tag.name
        
        # 1. 处理 StartTransfer 消息
        if tag_name == "StartTransfer" and received_msg.transfer_id == id:
            transfer_id = received_msg.transfer_id
            print(f"\n[文件接收] 开始接收 '{received_msg.file_name}' (类型: {received_msg.file_type}, 大小: {received_msg.total_size} bytes)...")
            active_transfers[transfer_id] = {
                "file_name": received_msg.file_name,
                "file_type": received_msg.file_type, # 存储文件类型
                "total_chunks": received_msg.total_chunks,
                "data": bytearray(),
                "chunks_received": 0
            }

        # 2. 处理 DataChunk 消息
        elif tag_name == "DataChunk":
            transfer_id = received_msg.transfer_id
            if transfer_id in active_transfers:
                transfer = active_transfers[transfer_id]
                try:
                    decoded_data = base64.b64decode(received_msg.data)
                    transfer["data"].extend(decoded_data)
                except (binascii.Error, TypeError) as e:
                    print(f"\n[文件接收] Base64解码失败: {e}")
                    del active_transfers[transfer_id]
                    return
                transfer["chunks_received"] += 1

        # 3. 处理 EndTransfer 消息
        elif tag_name == "EndTransfer":
            transfer_id = received_msg.transfer_id
            if transfer_id in active_transfers:
                transfer_info = active_transfers[transfer_id]
                file_name = transfer_info['file_name']
                file_type = transfer_info['file_type']
                full_data = transfer_info["data"]

                print(f"\n[文件接收] '{file_name}' 接收完成!")
                
                # 根据 file_type 确定保存路径和处理方式
                try:
                    save_dir = ""
                    if file_type == 'directory':
                        # 通讯录直接保存为 data.json
                        save_path = os.path.join('user', current_user, 'data.json')
                        
                        # 确保目录存在
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        
                        # 解码为JSON字典并保存
                        if not full_data:
                            directory_dict = {"contacts": [], "messages": {}}
                        else:
                            directory_dict = json.loads(full_data.decode('utf-8'))
                        
                        with open(save_path, 'w', encoding='utf-8') as f:
                            json.dump(directory_dict, f, indent=4, ensure_ascii=False)
                        print(f"[客户端] 通讯录已更新并保存至: {save_path}")

                    else:
                        # 处理图片、语音和通用文件
                        if file_type == 'image':
                            save_dir = os.path.join('user', current_user, 'image')
                        elif file_type == 'audio':
                            save_dir = os.path.join('user', current_user, 'audio')
                        elif file_type == 'file':
                            save_dir = os.path.join('user', current_user, 'file')
                        elif file_type == 'publickey':
                            save_dir = os.path.join('user', current_user, 'publickey')
                            os.makedirs(save_dir, exist_ok=True)
                            save_path = os.path.join(save_dir, file_name)

                            with open(save_path, 'wb') as f:
                                f.write(full_data)
                            print(f"[客户端] 公钥已保存至: {save_path}")

                        else:
                            print(f"[客户端] 未知的 file_type '{file_type}'，将保存到 'downloads' 目录。")
                            save_dir = os.path.join('user', current_user, 'downloads')

                        # 创建目标目录
                        os.makedirs(save_dir, exist_ok=True)
                        save_path = os.path.join(save_dir, file_name)
                        
                        # 以二进制模式写入文件
                        with open(save_path, 'wb') as f:
                            f.write(full_data)
                        print(f"[客户端] 文件 '{file_name}' 已保存至: {save_path}")
                
                except json.JSONDecodeError as e:
                    print(f"[客户端] 处理通讯录数据失败：无效的JSON格式。 {e}")
                except Exception as e:
                    print(f"[客户端] 保存文件时发生错误: {e}")
                
                # 清理并结束函数
                del active_transfers[transfer_id]
                return
            
        elif received_msg.transfer_id == id:
            print(f"[文件接收] 收到意外消息 {tag_name}，传输ID为 {id}。")

# --- END OF MODIFICATION ---

# 线程锁，用于防止多个线程同时写入同一个文件导致数据损坏
# 在P2P聊天中，主线程（发送）和监听线程（接收）可能都会调用保存消息的函数

file_write_lock = threading.Lock()
def save_msg(current_user: str, contact_id: Union[str, int], sender: str, content: str, time: str, date: str):
    """
    将一条消息保存到指定用户的本地 JSON 文件中。

    该函数是线程安全的，会根据用户名动态定位到 'user/{username}/data.json' 文件，
    并按照指定的结构（按联系人ID和日期分组）来存储消息。

    Args:
        current_user (str): 当前登录的用户名，用于确定文件路径。
        contact_id (int): 消息所属的联系人ID。
        sender (str): 消息的发送者名称。                                             # 为user / contact !!!
        content (str): 消息内容。
        time (str): 消息的时间戳 (e.g., "14:30:05")。
        date (str): 消息的日期 (e.g., "2023-10-27")。
    """
    if not current_user:
        print("[保存消息错误] 未提供当前用户名，无法保存消息。")
        return

    # 1. 构造文件路径
    filepath = os.path.join('user', current_user, 'data.json')
    
    # 使用锁来确保文件操作的原子性，防止数据竞争
    with file_write_lock:
        try:
            # 2. 读取现有的数据
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data: Dict[str, Any] = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # 如果文件不存在或是空的/无效的JSON，则初始化一个新结构
                data = {"contacts": [], "messages": {}}

            # 3. 更新数据结构
            # 获取所有消息记录，如果不存在则为空字典
            all_messages = data.get('messages', {})
            
            # 获取特定联系人的消息列表，如果不存在则为空列表
            # 注意：JSON的键必须是字符串，所以要转换 contact_id
            contact_id_str = str(contact_id)
            contact_msgs_list = all_messages.get(contact_id_str, [])

            # 寻找当天的消息记录
            day_entry = None
            for day in contact_msgs_list:
                if day.get('date') == date:
                    day_entry = day
                    break
            
            # 如果没有找到当天的记录，就创建一个新的
            if day_entry is None:
                day_entry = {"date": date, "messages": []}
                contact_msgs_list.append(day_entry)

            # 将新消息追加到当天的消息列表中
            day_entry['messages'].append({
                "sender": sender,
                "content": content,
                "time": time
            })

            # 将更新后的联系人消息列表写回主数据结构
            all_messages[contact_id_str] = contact_msgs_list
            data['messages'] = all_messages

            # 4. 将更新后的完整数据写回文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # print(f"[消息已保存] 到 {filepath}") # 可选的调试信息

        except Exception as e:
            print(f"[保存消息时发生严重错误] 文件: {filepath}, 错误: {e}")

# --- END OF NEW/MODIFIED CODE FOR Transaction_Client.py ---

'''
这里将调用客户端处理的事务，并返回结果给服务器
'''
# User to Client to Server
def handle_register(ssl_connect_sock):
    inp_username = input("请输入用户名: ").strip()
    inp_secret = input("请输入密码: ").strip()
    inp_email = input("请输入邮箱: ").strip()
    register_msg = S.RegisterMsg(username=inp_username, secret=inp_secret, email=inp_email, time=int(time.time()))

    print(f"ready to send the message: {register_msg}")  
    if not register_msg:
        return None

    ssl_connect_sock.sendall(serialize(register_msg))
    print("I'm in register")
    # 等待服务器回复
    received_msg = recv_msg(ssl_connect_sock)
    if received_msg is None:
        print("客户端已断开连接。")
        return None

    print(f"服务器回复: {received_msg}")
    if received_msg.tag.name == "SuccessRegister" and received_msg.username == inp_username:
        print(f"注册成功: {received_msg}")

        directory_path = os.path.join('user', inp_username) # 用户注册时就应该创建
        os.makedirs(directory_path, exist_ok=True) # user/{username}

        directory = {"contacts": [], "messages": {}}
        with open(f"user/{inp_username}/data.json", 'w', encoding='utf-8') as f:
            json.dump(directory, f, indent=2, ensure_ascii=False)

        return True
    if received_msg.tag.name == "FailRegister" and received_msg.username == inp_username:
        print(f"注册失败: {received_msg}")
        return None

    return None


# User to Client to Server
def handle_login(ssl_connect_sock, my_p2p_port):
    inp_username = input("请输入用户名: ").strip()
    inp_secret = input("请输入密码: ").strip()
    login_msg = S.LoginMsg(
        username=inp_username, 
        secret=inp_secret, 
        port=my_p2p_port, 
        time=int(time.time()))
    
    print(f"ready to send the message: {login_msg}")

    if not login_msg:
        return None, None

    ssl_connect_sock.sendall(serialize(login_msg))
    print("I'm in login")

    received_msg = recv_msg(ssl_connect_sock)
    if received_msg is None:
        print("客户端已断开连接。")
        return None, None

    if received_msg.tag.name == "SuccessLogin" and received_msg.username == inp_username:
        print(f"登录成功: {received_msg}")
        ''' 
        建立监听接口，等待联系人连接
        如果接收到到消息且接收者为本人
        则将消息根据发送id保存到历史记录，等ui显示  
        '''
        recv_large_data(ssl_connect_sock, received_msg.transfer_id, inp_username)

        return received_msg.username, received_msg.user_id
    
    if received_msg.tag.name == "FailLogin" and received_msg.username == inp_username:
        print(f"登录失败: {received_msg}")
        return None, None

    return None, None

# User to Client to Server
def handle_logout(ssl_connect_sock, current_user):
    logout_msg = S.LogoutMsg(username=current_user, time=int(time.time()))
    ssl_connect_sock.sendall(serialize(logout_msg))
    print("I'm in logout")
    received_msg = recv_msg(ssl_connect_sock)
    if received_msg is None:
        print("服务器端已断开连接。")
        return None
    for _ in range(10):
        if received_msg.tag.name == "SuccessLogout" and received_msg.username == current_user:
            print(f"注销成功: {received_msg}")
            return True
    return None

# User to Client to Server : when login success
def handle_get_directory(ssl_connect_sock, current_user):
    """(前台手动调用) 向服务器请求并接收最新的通讯录。"""
    if not current_user:
        print("[错误] 未登录，无法获取通讯录。")
        return False
        
    try:
        # 1. 发送请求
        get_dir_msg = S.GetDirectoryMsg(username=current_user)
        ssl_connect_sock.sendall(serialize(get_dir_msg))
        
        # 2. 等待服务器的 StartTransferMsg
        response = recv_msg(ssl_connect_sock)
        if isinstance(response, S.StartTransferMsg) and response.file_type == 'directory':
            # 3. 如果是正确的开始信号，调用 recv_large_data 处理后续传输
            recv_large_data(ssl_connect_sock, response.transfer_id, current_user)
            return True
        else:
            print(f"[错误] 请求通讯录后收到意外的服务器响应: {type(response)}")
            return False
            
    except Exception as e:
        print(f"获取通讯录时出错: {e}")
        return False
    # get_directory_msg = S.GetDirectoryMsg(
    #     username = current_user, 
    #     time = int(time.time()))

    # ssl_connect_sock.sendall(serialize(get_directory_msg))

    # received_msg = recv_msg(ssl_connect_sock)
    # if received_msg is None:
    #     print("服务器端已断开连接。")
    #     return None

    # if received_msg.tag.name == "Directory" and received_msg.username == current_user:
    #     transfer_id = received_msg.transfer_id
    #     recv_large_data(ssl_connect_sock, transfer_id, current_user)

    #     return True ## 去实现一个计时器，如果收到消息，则返回True，否则返回False

    # return None


# User to Client to Server
# def handle_get_history(ssl_connect_sock, current_user):
#     print("I'm in get history")

# User to Client to Server 
def handle_get_public_key(ssl_connect_sock, current_user_id, current_username):
    """
    向服务器请求指定用户的公钥证书。
    """
    if not current_user_id or not current_username:
        print("[错误] 您必须先登录才能请求公钥。")
        return

    dest_username = input("请输入您想获取其公钥证书的用户名: ").strip()
    if not dest_username:
        print("用户名不能为空。")
        return
        
    print(f"正在为用户 '{dest_username}' 请求公钥证书...")
    
    # 创建请求消息
    request_msg = S.GetPublicKeyMsg(
        request_name=current_username,
        target_name=dest_username,
        time=int(time.time())
    )
    
    # 发送请求
    # 注意：响应将作为文件传输异步到达，并由主监听循环处理，
    # 而不是作为此函数的直接返回值。
    try:
        ssl_connect_sock.sendall(serialize(request_msg))
        print("请求已发送。证书将在片刻后接收并自动保存。")
    except Exception as e:
        print(f"发送请求失败: {e}")    

    print("I'm in get public key")

# User to Client to Server: when the user is online and is leisure
def handle_alive(ssl_connect_sock):
    print("I'm in send alive")

# User to Client to Server: when close the chat window
def handle_backup(ssl_connect_sock):
    print("I'm in backup history")

'''
这里将调用客户端处理的事务，并返回结果给客户端(对端)
'''
def handle_send_message(ssl_connect_sock, msg: S.MessageMsg):
    try:
        # The `serialize` function already creates the full payload with the length prefix.
        # We just need to send its output directly. This fixes the "double prefix" bug.
        payload = serialize(msg)
        ssl_connect_sock.sendall(payload)
        print("==== I'm in send message ====")
        return True
    except (BrokenPipeError, ConnectionResetError):
        print("\n[Chat] Connection lost while trying to send.")
        return False

# *** 修正 #6: 重写P2P文件发送处理函数，使其正确且独立 ***
def handle_send_voice(p2p_sock, current_user, file_name):
    """(P2P) 处理发送语音文件的请求，使用分块传输协议。"""
    if not file_name:
        print("文件名不能为空。")
        return False
    print("==== 准备发送语音... ====")
    # 调用新的P2P专用发送函数
    return send_large_data_p2p(p2p_sock, current_user, 'audio', file_name)

def handle_send_file(p2p_sock, current_user, file_name):
    """(P2P) 处理发送通用文件的请求。"""
    if not file_name:
        print("文件名不能为空。")
        return False
    print("==== 准备发送文件... ====")
    return send_large_data_p2p(p2p_sock, current_user, 'file', file_name)

def handle_send_image(p2p_sock, current_user, file_name):
    """(P2P) 处理发送图片文件的请求。"""
    if not file_name:
        print("文件名不能为空。")
        return False
    print("==== 准备发送图片... ====")
    return send_large_data_p2p(p2p_sock, current_user, 'image', file_name)