from sys import setswitchinterval
import schema as S
import datetime as dt
import time
import socket as skt
import json
import ssl
import uuid
import Transaction_Server as T
from serializer import serialize, deserialize

ip_port = ("127.0.0.1", 47474)

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

def msg_process(ssl_connect_sock):
    try:
        received_msg = recv_msg(ssl_connect_sock)
        if received_msg is None:
            print("客户端已断开连接。")
            return None

        if received_msg.tag.name == "Login":
            reply_msg = T.handle_login(received_msg)
            
        
        elif received_msg.tag.name == "Register":
            reply_msg = T.handle_register(received_msg)
            

        elif received_msg.tag.name == "Logout":
            reply_msg = T.handle_logout(received_msg)

        elif received_msg.tag.name == "GetDirectory":
            reply_msg = T.handle_get_directory(received_msg)

        elif received_msg.tag.name == "GetHistory":
            reply_msg = T.handle_get_history(received_msg)
        
        elif received_msg.tag.name == "GetPublicKey":
            reply_msg = T.handle_get_public_key(received_msg)

        elif received_msg.tag.name == "Alive":
            reply_msg = T.handle_alive(received_msg)

        elif received_msg.tag.name == "BackUp":
            reply_msg = T.handle_backup(received_msg)
        
        ssl_connect_sock.sendall(serialize(reply_msg))
        return True

    except ConnectionResetError:
        print("客户端连接被重置。")
        return None
    except Exception as e:
        print(f"发生错误: {e}")
        return None                 

try:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.load_cert_chain(certfile="server.crt", keyfile="server_rsa_private.pem.unsecure")
    context.load_verify_locations("ca.crt")
    context.verify_mode = ssl.CERT_REQUIRED

    with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as sk:
        sk.bind(ip_port)
        sk.listen(5)
        print('服务器已启动，等待客户端连接...')

        connect_sock, address = sk.accept()
        print(f"接受来自 {address} 的连接")

        with context.wrap_socket(connect_sock, server_side=True) as ssl_connect_sock:
            while True:
                if msg_process(ssl_connect_sock) is None:
                    break

except FileNotFoundError:
    print("\n错误: 找不到证书文件 'server.crt' 或 'server.key'。")
except Exception as e:
    print(f"服务器启动失败: {e}")

print("服务器已关闭。")