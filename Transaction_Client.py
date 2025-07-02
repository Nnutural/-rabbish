import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import pprint
from serializer import serialize, deserialize

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

'''
这里将调用客户端处理的事务，并返回结果给服务器
'''
# User to Client to Server
def handle_register(ssl_connect_sock):
    inp_username = input("请输入用户名: ").strip()
    inp_secret = input("请输入密码: ").strip()
    inp_email = input("请输入邮箱: ").strip()
    # login_msg = S.RegisterMsg(username="佀凯淇", secret="password123", email="1234567890@qq.com")
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
    if received_msg.tag.name == "SuccessRegister":
        print(f"注册成功: {received_msg}")
        return True
    if received_msg.tag.name == "FailRegister":
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

    if received_msg.tag.name == "SuccessLogin":
        print(f"登录成功: {received_msg}")
        return True

    if received_msg.tag.name == "FailLogin":
        print(f"登录失败: {received_msg}")
        return None

    return None

# User to Client to Server
def handle_logout(ssl_connect_sock):
    print("I'm in logout")

# User to Client to Server : when login success
def handle_get_directory(ssl_connect_sock):
    ''' 从服务器获取联系人列表 '''


    ''' 将服务器返回的联系人列表更新到本地 '''
    


    print("I'm in get directory")

# User to Client to Server
def handle_get_history(ssl_connect_sock):
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

