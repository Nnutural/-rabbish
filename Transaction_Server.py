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

class Contact:
    """
    管理单个用户的通讯录。
    每个用户都有一个独立的JSON文件来存储其联系人列表。
    """
    def __init__(self, username: str):
        self.username = username
        # 为每个用户创建一个独立的通讯录文件
        self.filepath = os.path.join('data', 'directory', f"{self.username}.json")
        self.contacts = self._load_contacts()

    def _load_contacts(self) -> List[Dict[str, Any]]:
        """从文件加载通讯录，如果文件不存在则返回空列表。"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("contacts", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_contacts(self):
        """
        保存通讯录到文件。
        在保存前，会根据最近通信时间戳对联系人进行排序，并重新生成ID。
        """
        # 1. 根据时间戳对联系人进行降序排序
        self.contacts.sort(key=lambda c: c.get('time', 0), reverse=True)
        
        # 2. 重新生成ID
        for i, contact in enumerate(self.contacts):
            contact['id'] = i + 1
            
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump({"contacts": self.contacts}, f, indent=4, ensure_ascii=False)

    def update_or_add_contact(self, name: str, address: str, preview: str):
        """
        更新或添加一个联系人。
        如果联系人已存在，则更新其信息和时间戳。
        如果不存在，则添加为新联系人。
        """
        found = False
        current_time = int(time.time())
        
        for contact in self.contacts:
            if contact.get("name") == name:
                # 更新现有联系人
                contact["address"] = address
                contact["preview"] = preview
                contact["time"] = current_time
                found = True
                break
        
        if not found:
            # 添加新联系人
            new_contact = {
                "id": -1, # id将在保存时重新计算
                "name": name,
                "status": "offline", # 初始状态为离线，将在获取时更新
                "preview": preview,
                "time": current_time,
                "address": address
            }
            self.contacts.append(new_contact)
            
        self._save_contacts()
        print(f"[通讯录日志] 用户 {self.username} 的通讯录已更新，联系人: {name}")

    def get_contacts_with_status(self, online_users_set: Set[str]) -> List[Dict[str, Any]]:
        """
        获取通讯录列表，并根据在线用户集合实时更新联系人状态。
        """
        for contact in self.contacts:
            if contact.get("name") in online_users_set:
                contact["status"] = "online"
            else:
                contact["status"] = "offline"
        return self.contacts

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

def send_large_data(ssl_connect_sock, data_bytes: bytes, file_name: str, id: str):
    """
    将大的二进制数据分块发送给指定的socket。
    这个函数会处理整个 Start -> Chunk -> End 的流程。
    """
    try:
        
        # 1. 准备元数据       
        total_size = len(data_bytes)
        total_chunks = math.ceil(total_size / CHUNK_SIZE)

        # 2. 发送 StartTransferMsg
        start_msg = S.StartTransferMsg(
            transfer_id = id,
            file_name = file_name,
            total_size = total_size,
            total_chunks = total_chunks,
            chunk_size = CHUNK_SIZE
        )
        ssl_connect_sock.sendall(serialize(start_msg))
        print(f"[服务器日志] 开始传输 '{file_name}' (ID: {id}), 共 {total_chunks} 块。")

        # 3. 循环发送 DataChunkMsg
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            data_chunk = data_bytes[start:end]

            # --- START OF MODIFICATION ---
            # Encode the binary chunk into a Base64 string
            encoded_chunk_str = base64.b64encode(data_chunk).decode('ascii')
            # --- END OF MODIFICATION ---
            
            
            chunk_msg = S.DataChunkMsg(
                transfer_id = id,
                chunk_index = i,
                data =  encoded_chunk_str
            )
            ssl_connect_sock.sendall(serialize(chunk_msg))
            # print(f"  > 已发送块 {i+1}/{total_chunks}") # 可选：用于调试
            # time.sleep(0.001) # 可选：防止网络拥塞，但TCP的流控通常能处理

        # 4. 发送 EndTransferMsg
        end_msg = S.EndTransferMsg(transfer_id = id, status='success')
        ssl_connect_sock.sendall(serialize(end_msg))
        print(f"[服务器日志] 传输 '{file_name}' (ID: {id}) 完成。")
        return True

    except Exception as e:
        print(f"[服务器错误] 传输 '{file_name}' 失败: {e}")
        # (可选) 可以尝试发送一个 'cancelled' 的 EndTransferMsg
        try:
            end_msg = S.EndTransferMsg(transfer_id = id, status='cancelled')
            ssl_connect_sock.sendall(serialize(end_msg))
        except Exception:
            pass # 如果发送也失败，就没办法了
        return False


'''
这里将处理服务器端的事务，并返回结果给客户端
'''
def handle_register(msg: S.RegisterMsg,):
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
    
    user_dic = Contact(msg.username)
    user_dic._save_contacts()
    
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

            port = msg.port
            user_record['address'] = f"{user_ip}:{port}"
            save_users_to_json("data/users.json", USER_LIST) 
            # 更新用户列表 这一步也应该更新该用户好友的通讯录
            '''
            1. 根据该用户通讯录中的好友，查找好友的通讯录（无则跳过）
            2. 在好友的通讯录中，更新当前用户的状态
            3. 调用通讯录更新函数，向好友发送当前用户的状态
            '''


            
            print(f"[服务器日志] 用户 '{found_username}' 验证成功。\n")
            transfer_id = str(uuid.uuid4()) # 生成一个唯一的传输ID
            response = S.SuccessLoginMsg(username = found_username,transfer_id = transfer_id, user_id=user_record['user_id'], directory="directory.json") # 需要传送通讯录数据
            ssl_connect_sock.sendall(serialize(response))
            try:
                with open('data/directory/'+found_username+'.json', 'rb') as f: # 以二进制模式读取 , 文件名！！！！
                    directory_bytes = f.read()
                
                # 调用分包发送函数
                send_large_data(ssl_connect_sock, directory_bytes, "directory.json", transfer_id)

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
    pass

def handle_send_directory(msg: S.GetDirectoryMsg):
    print("I'm in send directory")
    pass

def handle_get_history(msg: S.GetHistoryMsg):
    print("I'm in get history")
    pass

def handle_get_public_key(msg: S.GetPublicKeyMsg):
    print("I'm in get public key")
    pass

def handle_alive(msg: S.AliveMsg):
    print("I'm in update alive")
    pass

def handle_backup(msg: S.BackupMsg):
    print("I'm in backup history")
    pass


