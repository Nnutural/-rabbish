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

ip_port = ("", 47474)
# ip_port = ("10.122.192.1", 47474)

def msg_process(ssl_connect_sock):
    try:
        user_ip, user_port = ssl_connect_sock.getpeername()
        print("user_ip", user_ip)
        print("user_port", user_port)
        received_msg = T.recv_msg(ssl_connect_sock)
        if received_msg is None:
            print("客户端已断开连接。")
            return None

        if received_msg.tag.name == "Login":
            reply_msg = T.handle_login(received_msg, user_ip, user_port, ssl_connect_sock)        
        
        elif received_msg.tag.name == "Register":
            reply_msg = T.handle_register(received_msg)           
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "Logout":
            reply_msg = T.handle_logout(received_msg)   
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetDirectory":
            reply_msg = T.handle_send_directory(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetHistory":
            reply_msg = T.handle_get_history(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "GetPublicKey":
            reply_msg = T.handle_get_public_key(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

        elif received_msg.tag.name == "Alive":
            reply_msg = T.handle_alive(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))

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
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2

    context.load_cert_chain(certfile="server.crt", keyfile="server_rsa_private.pem.unsecure")
    context.load_verify_locations("ca.crt")
    context.verify_mode = ssl.CERT_REQUIRED

    with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as sk:
        sk.bind(ip_port)
        sk.listen(5)
        print('服务器已启动，等待客户端连接...')

        connect_sock, address = sk.accept()
        print(f"接受来自 {address} 的连接") # 得到了客户端socket的ip和port


        with context.wrap_socket(connect_sock, server_side=True) as ssl_connect_sock:
            while True:
                if msg_process(ssl_connect_sock) is None:
                    break

except FileNotFoundError:
    print("\n错误: 找不到证书文件 'server.crt' 或 'server.key'。")
except Exception as e:
    print(f"服务器启动失败: {e}")

print("服务器已关闭。")