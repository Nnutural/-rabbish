import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import uuid
import os
import pprint
import math
import base64
from serializer import serialize, deserialize
from dataclasses import asdict
from typing import Any, Dict, List, Set
import hashlib
import Contacts as C

# In Transaction_Server.py

# ... existing imports ...
import ssl # 确保导入 ssl 模块
import os  # 确保导入 os 模块

# --- START OF NEW FUNCTION ---

def save_client_certificate(ssl_connect_sock: ssl.SSLSocket, username: str):
    """
    从 SSL/TLS 连接中获取客户端证书，并以 PEM 格式保存到指定目录。

    Args:
        ssl_connect_sock: 已建立的 SSL socket 连接。
        username (str): 与该证书关联的用户名。
    """
    if not username:
        print("[证书保存] 错误: 未提供用户名，无法保存证书。")
        return

    print(f"[证书保存] 尝试为用户 '{username}' 保存证书...")
    try:
        # 1. 获取二进制格式 (DER) 的客户端证书
        # a. 你的 server.py 中设置了 context.verify_mode = ssl.CERT_REQUIRED
        # b. 这意味着如果客户端没有提供证书，TLS 握手会失败，连接根本无法建立
        # c. 因此，在这里我们总能获取到证书
        der_cert = ssl_connect_sock.getpeercert(binary_form=True)
        if der_cert is None:
            # 理论上在 CERT_REQUIRED 模式下不应该发生，但作为健壮性检查
            print(f"[证书保存] 警告: 未能从用户 '{username}' 的连接中获取证书。")
            return

        # 2. 将 DER 格式转换为人类可读的 PEM 格式
        pem_cert = ssl.DER_cert_to_PEM_cert(der_cert)

        # 3. 定义保存路径
        # 我们将所有用户数据统一放在 'data/users' 目录下，更整洁
        save_dir = os.path.join('data', 'publickey', username)
        os.makedirs(save_dir, exist_ok=True) # 如果目录不存在，则创建它

        # 4. 写入文件
        file_path = os.path.join(save_dir, f"{username}_cert.pem")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(pem_cert)
        
        print(f"[证书保存] 成功! 用户 '{username}' 的证书已保存到: {file_path}")

    except Exception as e:
        print(f"[证书保存] 严重错误: 为用户 '{username}' 保存证书时失败: {e}")

# --- END OF NEW FUNCTION ---

def hash_password(password: str) -> str:
    """使用SHA-256对密码进行哈希处理。"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(provided_password: str, stored_hash: str) -> bool:
    """验证提供的密码是否与存储的哈希值匹配。"""
    return hash_password(provided_password) == stored_hash

def load_users_from_json(filename: str) -> List[Dict[str, Any]]:
    """
    从JSON文件加载用户列表。
    如果文件不存在，则返回一个空列表。
    """
    try:
        # 确保目录存在
        db_dir = os.path.dirname(filename)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 更新：如果文件不存在或为空返回空列表
        print(f"[服务器日志] 未找到或无法解析 {filename}。将使用空的用户列表启动。")
        return []

def save_users_to_json(filename: str, users: List[Dict[str, Any]]) -> None:
    """将用户列表保存到JSON文件。"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    print(f"[服务器日志] 用户数据已保存到 {filename}。")

def recv_msg(ssl_connect_sock):
    try:
        header_bytes = ssl_connect_sock.recv(4) # 先接收4个字节，表示数据长度
        if not header_bytes:
            print("客户端可能已断开连接 (header is empty)。")
            return None

        datalength = int.from_bytes(header_bytes, byteorder='big')
        
        # 分块接收数据，确保接收完整
        json_bytes_list = []
        bytes_received = 0
        while bytes_received < datalength:
            chunk = ssl_connect_sock.recv(min(datalength - bytes_received, 4096))
            if not chunk:
                raise ConnectionError("客户端在传输数据时断开连接。")
            json_bytes_list.append(chunk)
            bytes_received += len(chunk)
        
        json_bytes = b''.join(json_bytes_list)

        # 解码并反序列化为 dataclass 对象
        msg_dict = json.loads(json_bytes.decode("UTF-8"))
        received_msg = deserialize(msg_dict)
        return received_msg
    except (ConnectionError, ConnectionResetError):
        print("客户端连接中断。")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 解码错误: {e}")
        return None

# subpackage
# 定义一个常量
CHUNK_SIZE = 4096 # 每次发送 4KB，这是一个常用的大小

def send_large_data(ssl_connect_sock, username: str, file_type: str, file_name: str, id: str):
    """
    将大的二进制数据分块发送给指定的socket。
    这个函数会处理整个 Start -> Chunk -> End 的流程，并根据 file_type 决定文件路径 -> data_bytes。 

    Args:
        ssl_connect_sock: 目标socket连接。
        username (str): 用于构建文件路径的用户名。
        file_type (str): 文件类型 ('directory', 'image', 'audio', 'file')。
        file_name (str): 要传输的文件名。
        transfer_id (str): 本次传输的唯一ID。
    """
    filepath = ""
    # 1. 根据文件类型确定文件路径
    # 注意：这里的路径是服务器端的存储结构
    if file_type == 'directory':
        # 通讯录文件直接在 'data/directory' 目录下，以用户名命名
        filepath = f'data/directory/{username}.json'
    elif file_type == 'publickey':
        filepath = f'data/publickey/{username}/{username}_cert.pem'
    elif file_type == 'image':
        filepath = os.path.join('data', 'user_data', username, 'image', file_name)
    elif file_type == 'audio':
        filepath = os.path.join('data', 'user_data', username, 'audio', file_name)
    elif file_type == 'file':
        filepath = os.path.join('data', 'user_data', username, 'file', file_name)
    else:
        print(f"[服务器错误] 不支持的文件类型: {file_type}")
        return False

    # 2. 读取文件内容
    try:
        # 确保目录存在（对于未来可能的上传功能有好处）
        server_storage_dir = os.path.dirname(filepath)
        if not os.path.exists(server_storage_dir):
            os.makedirs(server_storage_dir)

        with open(filepath, 'rb') as f:
            data_bytes = f.read()
    except FileNotFoundError:
        print(f"[服务器错误] 传输失败: 文件 '{filepath}' 未找到。")
        # （可选）可以发送一个 'cancelled' 状态的 EndTransferMsg
        try:
            end_msg = S.EndTransferMsg(transfer_id = id, status='cancelled_not_found')
            ssl_connect_sock.sendall(serialize(end_msg))
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"[服务器错误] 读取文件 '{filepath}' 时出错: {e}")
        return False  
    
    # 3. 开始传输流程
    try:
        # 3.1 准备元数据
        total_size = len(data_bytes)
        total_chunks = math.ceil(total_size / CHUNK_SIZE)

        # 3.2 发送 StartTransferMsg (包含新的 file_type 字段)
        start_msg = S.StartTransferMsg(
            transfer_id = id,
            file_type = file_type,
            file_name = file_name,
            total_size = total_size,
            total_chunks = total_chunks,
            chunk_size = CHUNK_SIZE
        )
        ssl_connect_sock.sendall(serialize(start_msg))
        print(f"[服务器日志] 开始传输 '{file_name}' (类型: {file_type}, ID: {id}), 共 {total_chunks} 块。")

        # 3.3 循环发送 DataChunkMsg
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            data_chunk = data_bytes[start:end]
            encoded_chunk_str = base64.b64encode(data_chunk).decode('ascii')
            
            chunk_msg = S.DataChunkMsg(
                transfer_id = id,
                chunk_index = i,
                data = encoded_chunk_str
            )
            ssl_connect_sock.sendall(serialize(chunk_msg))

        # 3.4 发送 EndTransferMsg
        end_msg = S.EndTransferMsg(transfer_id = id, status = 'success')
        ssl_connect_sock.sendall(serialize(end_msg))
        print(f"[服务器日志] 传输 '{file_name}' (ID: {id}) 完成。")
        return True

    except Exception as e:
        print(f"[服务器错误] 传输 '{file_name}' 失败: {e}")
        try:
            end_msg = S.EndTransferMsg(transfer_id = id, status = 'cancelled')
            ssl_connect_sock.sendall(serialize(end_msg))
        except Exception:
            pass
        return False

# --- END OF MODIFICATION ---

def update_friends_contact_status(username, status):
    directory_path = 'data/directory'
    for user_file in os.listdir(directory_path):
        if not user_file.endswith('.json'):
            continue
        filepath = os.path.join(directory_path, user_file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            contacts = data.get('contacts', [])
            updated = False
            for contact in contacts:
                if contact.get('name') == username:
                    contact['status'] = status
                    updated = True
            if updated:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump({'contacts': contacts}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[通讯录同步错误] 更新 {filepath} 时出错: {e}")

'''
这里将处理服务器端的事务，并返回结果给客户端
'''
def handle_register(msg: S.RegisterMsg, ssl_connect_sock: ssl.SSLSocket):
    print("I'm in register")         
    # 启动时加载用户数据
    USER_LIST = load_users_from_json("data/users.json")

    if any(user.get('username') == msg.username for user in USER_LIST):
        response = S.FailRegisterMsg(error_type="username_exists", username=msg.username)
        return response

    # 2. 更新：使用uuid生成唯一的字符串ID
    new_user_id = str(uuid.uuid4())
    pass_hash = hash_password(msg.secret)

    # 创建新的用户记录，使用 user_id
    new_user_record = {
        "user_id"    : new_user_id,
        "username"   : msg.username,
        "email"      : msg.email,
        "pass_hash"  : pass_hash,
        "created_at" : int(time.time()),
        "address"    : None
    }
    USER_LIST.append(new_user_record)
    
    # 将更新后的用户列表保存到文件
    save_users_to_json("data/users.json", USER_LIST)
    
    user_dic = C.ContactManager(msg.username)
    user_dic._save_data()

    save_client_certificate(ssl_connect_sock, msg.username)
    
    print(f"[服务器日志] 用户 '{msg.username}' 创建成功, user_id: {new_user_id}。\n") # 应该查看使用否有对应的通讯录文件
    response = S.SuccessRegisterMsg(
        username = msg.username, 
        user_id=new_user_id,
        time = int(time.time()))

    return response 
    

def handle_login(msg: S.LoginMsg, user_ip, user_port, ssl_connect_sock):
    print("I'm in login, the listening port is {}".format(msg.port))
    '''读取json
    6. 更新用户在线状态，保存监听端口信息
    '''
    USER_LIST = load_users_from_json("data/users.json")

    user_record = None
    login_identifier = msg.username # or msg.user_id

    for record in USER_LIST:
        if (msg.username and record.get('username') == msg.username):
            user_record = record
            break
    
    if not user_record:
        print(f"[服务器日志] 校验失败: 提供的标识符 '{login_identifier}' 未找到对应用户。\n")
        response = S.FailLoginMsg(error_type="user_not_found", username=msg.username, time=int(time.time()))
        return response

    found_username = user_record.get('username')
    if found_username is None:
        return None

    if verify_password(msg.secret, user_record.get('pass_hash', '')):
        # 更新：检查 user_id
        if found_username and 'user_id' in user_record:

            save_client_certificate(ssl_connect_sock, found_username)

            port = msg.port
            user_record['address'] = f"{user_ip}:{port}"
            save_users_to_json("data/users.json", USER_LIST) 
            # 更新用户列表 这一步也应该更新该用户好友的通讯录
            '''
            1. 根据该用户通讯录中的好友，查找好友的通讯录（无则跳过）
            2. 在好友的通讯录中，更新当前用户的状态
            3. 调用通讯录更新函数，向好友发送当前用户的状态
            '''
            update_friends_contact_status(found_username, 'online')
            
            print(f"[服务器日志] 用户 '{found_username}' 验证成功。\n")

            transfer_id = str(uuid.uuid4()) # 生成一个唯一的传输ID
            response = S.SuccessLoginMsg(
                username = found_username,
                transfer_id = transfer_id, 
                user_id = user_record['user_id'], 
                directory = "directory.json") 
            # 需要传送通讯录数据

            ssl_connect_sock.sendall(serialize(response))
            
            try:
                # with open('data/directory/'+found_username+'.json', 'rb') as f: # 以二进制模式读取 , 文件名！！！！
                #     directory_bytes = f.read()
                
                # 调用分包发送函数
                send_large_data(
                    ssl_connect_sock = ssl_connect_sock,
                    username = found_username,
                    file_type = "directory",
                    file_name = f"{found_username}.json",
                    id = transfer_id
                )

            except FileNotFoundError:
                print(f"[服务器错误] 未找到通讯录文件。")
                # 可以发送一个失败的信令，或者直接不回复
                # 为了简单，这里我们只打印日志
            except Exception as e:
                print(f"[服务器错误] 处理发送通讯录时出错: {e}")

        else:
            print(f"[服务器错误] 数据库记录不完整，无法为用户 '{login_identifier}' 创建成功登录响应。\n")
            response = S.FailLoginMsg(username = found_username, error_type="server_error", time=int(time.time()))
            ssl_connect_sock.sendall(serialize(response))

    else:
        print(f"[服务器日志] 校验失败: 用户 '{found_username or login_identifier}' 的密码不正确。\n")
        response = S.FailLoginMsg( username=found_username, error_type="incorrect_secret", time=int(time.time()))
        ssl_connect_sock.sendall(serialize(response))

def handle_logout(msg: S.LogoutMsg):
    print("I'm in logout")
    USER_LIST = load_users_from_json("data/users.json")
    user_record = None
    for record in USER_LIST:
        if record.get('username') == msg.username:
            user_record = record
            break
    if not user_record:
        print(f"[服务器日志] 注销失败: 用户 '{msg.username}' 未找到。\n")
        return None
    user_record['address'] = ""
    save_users_to_json("data/users.json", USER_LIST)
    update_friends_contact_status(msg.username, 'offline')

    print(f"[服务器日志] 用户 '{msg.username}' 注销成功。\n")
    response = S.SuccessLogoutMsg(username=msg.username, user_id=user_record['user_id'], time=int(time.time()))
    return response

def handle_send_directory(msg: S.GetDirectoryMsg, ssl_connect_sock):
    """
    处理获取通讯录的请求。
    直接启动一个大文件传输流程来发送通讯录文件。
    """
    username = msg.username
    print(f"[服务器日志] 用户 '{username}' 请求通讯录。")
    
    try:
        transfer_id = str(uuid.uuid4())
        directory_filename = f"{username}.json"

        # 直接调用 send_large_data 发送通讯录
        success = send_large_data(
            ssl_connect_sock = ssl_connect_sock,
            username = msg.username,
            file_type = "directory",
            file_name = directory_filename,
            id = transfer_id
        )
        print("I'm in send directory")
        if success:
            print(f"[服务器日志] 已为 '{username}' 启动通讯录传输。")
        else:
            print(f"[服务器错误] 启动通讯录传输失败。")
        
        # 此函数自己处理发送，返回 None
        return None

    except Exception as e:
        print(f"[服务器错误] 处理 'GetDirectory' 请求时出错: {e}")
        return None
# def handle_get_history(msg: S.GetHistoryMsg):
#     print("I'm in get history")
#     pass
def handle_get_public_key(msg: S.GetPublicKeyMsg, ssl_connect_sock: ssl.SSLSocket):
    # *** 修正 #4: 此函数不应发送一个 PublicKeyMsg，它应该只启动文件传输 ***
    # 服务器的职责是响应 GetPublicKeyMsg，然后直接开始发送文件。
    # 客户端的后台线程或特定函数会接收这个文件流。
    
    requester_name = msg.request_name
    target_name = msg.target_name
    print(f"[服务器日志] 用户 '{requester_name}' 请求 '{target_name}' 的公钥。")
    
    try: 
        transfer_id = str(uuid.uuid4())
        cert_filename = f"{target_name}_cert.pem"
        
        # 直接调用 send_large_data 开始传输
        success = send_large_data(
            ssl_connect_sock = ssl_connect_sock,
            username = target_name, # 公钥属于 target_name
            file_type = "publickey",
            file_name = cert_filename,
            id = transfer_id
        )
        if success:
            print(f"[服务器日志] 已成功为 '{requester_name}' 启动 '{target_name}' 的公钥传输。")
        else:
            print(f"[服务器错误] 为 '{requester_name}' 启动公钥传输失败。")
            
    except Exception as e:
        print(f"[服务器错误] 处理发送公钥时出错: {e}")
    
    # 该函数自己处理发送，返回 None
    return None

