import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import uuid
import pprint
from serializer import serialize, deserialize

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
    '''读取json
    1. 检查用户名是否已存在
    2. 如果存在，则返回失败
    3. 如果不存在，则将用户名、密码、邮箱写入data.json
    4. 返回成功
    '''
    if 1 == 1:
        reply_msg = S.SuccessRegisterMsg(
            username = msg.username,
            user_id = str(uuid.uuid4()),
            time = int(time.time())
        )
        return reply_msg
    

def handle_login(msg: S.LoginMsg):
    print("I'm in login, the listening port is {}".format(msg.port))
    '''读取json
    1. 检查用户名是否已存在
    2. 如果不存在，则返回失败
    3. 如果存在，则检查密码是否正确
    4. 如果密码正确，则返回成功
    5. 如果密码不正确，则返回失败
    6. 更新用户在线状态，保存监听端口信息
    '''
    if 1 == 1:
        reply_msg = S.SuccessLoginMsg( # 在登录成功的消息中加入通讯录数据
            username = msg.username,
            user_id = str(uuid.uuid4()),
            directory = "data.json",  # 通讯录数据，json格式？？可以么？？
            time = int(time.time())
        )
        return reply_msg
    pass

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


