import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import pprint
import p2p as P
import Transaction_Client as T
from serializer import serialize, deserialize

CA_FILE = "ca.crt"
SERVER_HOSTNAME = 'SERVER' 
ip_port = ("127.0.0.1", 47474)

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

def msg_process(ssl_connect_sock):
    received_msg = recv_msg(ssl_connect_sock)
    if received_msg is None:
        print("客户端已断开连接。")
        return None

    print(f"服务器回复: {received_msg}")
    if received_msg.tag.name == "SuccessRegister":
        print(f"注册成功: {received_msg}")
        return True

    elif received_msg.tag.name == "FailRegister":
        print(f"注册失败: {received_msg}")

    elif received_msg.tag.name == "SuccessLogin":
        print(f"登录成功: {received_msg}")

    elif received_msg.tag.name == "FailLogin":
        print(f"登录失败: {received_msg}")

def User_evnets_process(ssl_connect_sock):
    T.handle_get_directory(ssl_connect_sock) # update the directory from server
    P.init_directory(ssl_connect_sock) # output the local directory
    while True:
        choice = input("which friend do you want to send message to: ").strip()
        if choice == "exit":
            print("客户端正在关闭...")
            return None

        if choice == "logout":
            T.handle_logout(ssl_connect_sock)
            return True
        
        if choice == "history":
            T.handle_get_history(ssl_connect_sock)
            return True

        if P.choose_friend(ssl_connect_sock, choice) is None:
            return None

def boot():
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        context.load_verify_locations(CA_FILE)
        context.load_cert_chain(certfile = "client.crt", keyfile = "client_rsa_private.pem.unsecure")
        context.verify_mode = ssl.CERT_REQUIRED

        with skt.socket(skt.AF_INET, skt.SOCK_STREAM) as s:
            with context.wrap_socket(s, server_hostname=SERVER_HOSTNAME) as ssl_connect_sock:
                ssl_connect_sock.connect(ip_port)

                print("--- 成功连接到服务器 ---")
                print("服务器证书信息:")
                pprint.pprint(ssl_connect_sock.getpeercert())
                print("------------------------\n")

                if login_screen(ssl_connect_sock):
                    while True:

                        if User_evnets_process(ssl_connect_sock) is None:
                            break
                        
                        if msg_process(ssl_connect_sock) is None:
                            break

    except FileNotFoundError:
        print(f"\n错误: 找不到CA证书文件 '{CA_FILE}'。")
    except ssl.SSLCertVerificationError as e:
        print(f"\n错误: 证书验证失败! {e}")
    except ConnectionRefusedError:
        print("错误: 连接被拒绝。服务器可能未运行或被防火墙阻止。")
    except Exception as e:
        print(f"发生未知错误: {e}")

    print("客户端已关闭。")

def login_screen(ssl_connect_sock) -> bool:
    for _ in range(5):
        opt = input("plesse inpu login / register: ")
        if opt == "login":          
            T.handle_login(ssl_connect_sock)
            return True
        elif opt == "register":
            T.handle_register(ssl_connect_sock)
            return True
        elif opt == "exit":
            return False
        else:
            print("invalid input")

    return False



def main():
    boot()

main()