import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import uuid
import os
import pprint
from serializer import serialize, deserialize
from dataclasses import asdict
from typing import Any, Dict, List
import hashlib

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
        "user_id": new_user_id,
        "username": msg.username,
        "email": msg.email,
        "pass_hash": pass_hash,
        "created_at": int(time.time())
    }
    USER_LIST.append(new_user_record)
    
    # 将更新后的用户列表保存到文件
    save_users_to_json("data/users.json", USER_LIST)
    
    print(f"[服务器日志] 用户 '{msg.username}' 创建成功, user_id: {new_user_id}。\n")
    response = S.SuccessRegisterMsg(
        username = msg.username, 
        user_id=new_user_id,
        time = int(time.time()))

    return response 
    

def handle_login(msg: S.LoginMsg, user_ip, user_port):
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

            
            print(f"[服务器日志] 用户 '{found_username}' 验证成功。\n")
            response = S.SuccessLoginMsg(username = found_username, user_id=user_record['user_id'], directory="directory.json") # 需要传送通讯录数据
            return response
        else:
            print(f"[服务器错误] 数据库记录不完整，无法为用户 '{login_identifier}' 创建成功登录响应。\n")
            response = S.FailLoginMsg(username = found_username, error_type="server_error", time=int(time.time()))
            return response
    else:
        print(f"[服务器日志] 校验失败: 用户 '{found_username or login_identifier}' 的密码不正确。\n")
        response = S.FailLoginMsg( username=found_username, error_type="incorrect_secret", time=int(time.time()))
        return response

    # if 1 == 1:
    #     reply_msg = S.SuccessLoginMsg( # 在登录成功的消息中加入通讯录数据
    #         username = msg.username,
    #         user_id = str(uuid.uuid4()),
    #         directory = "data.json",  # 通讯录数据，json格式？？可以么？？
    #         time = int(time.time())
    #     )
    #     return reply_msg
    # pass

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


