import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import pprint
import base64
import binascii
from serializer import serialize, deserialize

active_transfers = {} # 用于存储当前正在接收的文件传输信息

def recv_msg(ssl_connect_sock):
    client_data_bytes = ssl_connect_sock.recv(4) # 先接收4个字节，表示数据长度
    if not client_data_bytes:
        print("客户端已断开连接。")
        return None

    datalength = int.from_bytes(client_data_bytes, byteorder='big')
    json_bytes = ssl_connect_sock.recv(datalength)
    if not json_bytes:
        return None

    # 解码并反序列化未dataclass对象
    msg_dict = json.loads(json_bytes.decode("UTF-8"))
    received_msg = deserialize(msg_dict)
    return received_msg

def recv_large_data(ssl_connect_sock, login_id): # 默认为写入通讯录
    # 这个函数现在只处理一个文件传输事务，完成后就返回。
    while True:
        # 等待 StartTransfer, DataChunk, 或 EndTransfer
        received_msg = recv_msg(ssl_connect_sock)
        if received_msg is None:
            print("[文件接收] 接收过程中连接中断。")
            return # 发生错误，返回

        # --- 新的分包处理逻辑 ---
        if received_msg.tag.name == "StartTransfer" and received_msg.transfer_id == login_id:
            transfer_id = received_msg.transfer_id
            print(f"\n[文件接收] 开始接收 '{received_msg.file_name}' ({received_msg.total_size} bytes)...")
            active_transfers[transfer_id] = {
                "file_name": received_msg.file_name,
                "total_chunks": received_msg.total_chunks,
                "data": bytearray(),
                "chunks_received": 0
            }

        elif received_msg.tag.name == "DataChunk":
            transfer_id = received_msg.transfer_id
            if transfer_id in active_transfers:
                transfer = active_transfers[transfer_id]

                # --- START OF MODIFICATION ---
                # Decode the Base64 string back to bytes
                try:
                    decoded_data = base64.b64decode(received_msg.data)
                    transfer["data"].extend(decoded_data)
                except (binascii.Error, TypeError) as e:
                    print(f"\n[文件接收] Base64解码失败: {e}")
                    # Decide how to handle this error, e.g., cancel the transfer
                    del active_transfers[transfer_id]
                    return # Exit the function
                # --- END OF MODIFICATION ---

                transfer["chunks_received"] += 1

        elif received_msg.tag.name == "EndTransfer":
            transfer_id = received_msg.transfer_id
            if transfer_id in active_transfers:
                print(f"\n[文件接收] '{active_transfers[transfer_id]['file_name']}' 接收完成!")
                
                full_data = active_transfers[transfer_id]["data"]
                
                # 检查文件名以确认是通讯录
                #if active_transfers[transfer_id]['file_name'] == 'directory.json':
                try:
                    # 增加一个防御性检查：如果数据为空，则视为空的JSON对象
                    if not full_data:
                        print("[客户端] 通讯录文件为空，初始化为空目录。")
                        directory_dict = {}
                    else:
                        directory_dict = json.loads(full_data.decode('utf-8'))
                    
                    # 写入本地文件 这里应该根据不同的文件类型进行选择
                    with open("data.json", 'w', encoding='utf-8') as f:
                            json.dump(directory_dict, f, indent=2, ensure_ascii=False)
                    print("[客户端] 通讯录已更新。")

                except json.JSONDecodeError as e:
                    print(f"[客户端] 处理通讯录数据失败：无效的JSON格式。 {e}")
                except Exception as e:
                    print(f"[客户端] 处理通讯录数据时发生未知错误: {e}")
                
                # 清理
                del active_transfers[transfer_id]
                return 

def save_msg():
    pass
        

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
        return True
    if received_msg.tag.name == "FailRegister" and received_msg.username == inp_username:
        print(f"注册失败: {received_msg}")
        return None

    return None


# User to Client to Server
def handle_login(ssl_connect_sock, my_p2p_port):
    inp_username = input("请输入用户名: ").strip()
    inp_secret = input("请输入密码: ").strip()
    login_msg = S.LoginMsg(username=inp_username, secret=inp_secret, port=my_p2p_port, time=int(time.time()))
    print(f"ready to send the message: {login_msg}")

    if not login_msg:
        return None

    ssl_connect_sock.sendall(serialize(login_msg))
    print("I'm in login")

    received_msg = recv_msg(ssl_connect_sock)
    if received_msg is None:
        print("客户端已断开连接。")
        return None

    if received_msg.tag.name == "SuccessLogin" and received_msg.username == inp_username:
        print(f"登录成功: {received_msg}")
        ''' 
        建立监听接口，等待联系人连接
        如果接收到到消息且接收者为本人
        则将消息根据发送id保存到历史记录，等ui显示    
        '''
        recv_large_data(ssl_connect_sock, received_msg.transfer_id)

        return received_msg.username
    
    if received_msg.tag.name == "FailLogin" and received_msg.username == inp_username:
        print(f"登录失败: {received_msg}")
        return None

    return None

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
def handle_get_directory(ssl_connect_sock):
    ''' 从服务器获取联系人列表 '''


    ''' 将服务器返回的联系人列表更新到本地 主要是离线时收到的消息'''

    print("I'm in get directory")

# User to Client to Server
def handle_get_history(ssl_connect_sock, current_user):
    print("I'm in get history")

# User to Client to Server 
def handle_get_public_key(ssl_connect_sock):
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
def handle_send_message(msg: S.MessageMsg):
    print("I'm in send message")

def handle_send_voice(msg: S.VoiceMsg):
    print("I'm in send voice")

def handle_send_file(msg: S.FileMsg):
    print("I'm in send file")

def handle_send_image(msg: S.ImageMsg):
    print("I'm in send image")

