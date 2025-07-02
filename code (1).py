# sslclient.py
import socket
import ssl
import os
import sys
import struct
from enum import Enum
import time

# 1. 模拟C++的枚举 Msg_Tag (与服务器端相同)
class MsgTag(Enum):
    FILE_NAME = 1
    FILE_SIZE = 2
    READY_RECV = 3
    SEND_DATA = 4
    ALL_ACCPTED = 5
    GET_FILE_FAILED = 6
    FINISH = 7

# 定义与C++版本匹配的常量
PACKET_SIZE = 1012
HEADER_SIZE = 1024

# 全局变量，与C++版本保持一致
g_filebuff = None
g_filename = ""
g_filesize = 0
g_bytes_received = 0

# 2. 模拟C++的MsgHeader结构体 (与服务器端相同)
class MsgHeader:
    @staticmethod
    def pack(msg_tag, **kwargs):
        msg_id_bytes = struct.pack('!I', msg_tag.value)
        payload = b''
        
        if msg_tag == MsgTag.FILE_NAME:
            filename = kwargs.get('filename', '').encode('utf-8')
            payload = struct.pack('!256s', filename)
        
        # 其他消息类型由客户端打包
        
        full_message = msg_id_bytes + payload
        return full_message.ljust(HEADER_SIZE, b'\0')

    @staticmethod
    def unpack(data):
        msg_id_val = struct.unpack('!I', data[:4])[0]
        msg_tag = MsgTag(msg_id_val)
        payload = data[4:]
        
        info = {}
        if msg_tag == MsgTag.FILE_SIZE:
            filename_bytes, filesize = struct.unpack('!256sI', payload[:260])
            info['filename'] = filename_bytes.strip(b'\0').decode('utf-8')
            info['filesize'] = filesize
        elif msg_tag == MsgTag.SEND_DATA:
            packet_no, packet_size = struct.unpack('!II', payload[:8])
            info['packet_no'] = packet_no
            info['packet_size'] = packet_size
            info['data_buff'] = payload[8:8 + packet_size]
        
        return msg_tag, info

def error_handling(message):
    print(f"[error] {message} failed, line:{sys._getframe(1).f_lineno}", file=sys.stderr)

def init_ssl_context():
    """模拟C++的InitSSL函数，配置客户端SSL上下文"""
    # 对应 SSL_CTX_new(SSLv23_client_method())
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    
    # 客户端不需要设置TLS版本限制，通常会自动协商
    print("Initializing SSL Context...")
    try:
        # 对应 SSL_CTX_set_verify 和 SSL_CTX_load_verify_locations
        # 验证服务器证书
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile="ca.crt")
        
        # 对应 SSL_CTX_use_certificate_file 和 SSL_CTX_use_PrivateKey_file
        # 加载客户端证书以供服务器验证
        context.load_cert_chain(certfile="client.crt", keyfile="client_rsa_private.pem.unsecure")
        
        print("SSL Context initialized successfully.")
    except Exception as e:
        error_handling(f"InitSSL error: {e}")
        sys.exit(1)
        
    return context

def show_certs(ssl_socket):
    """模拟C++的ShowCerts函数"""
    print("\n--- Peer Certificate ---")
    cert = ssl_socket.getpeercert()
    if not cert:
        print("No peer certificate information!")
        return
        
    print("Certificate validation passed.")
    subject = dict(x[0] for x in cert['subject'])
    issuer = dict(x[0] for x in cert['issuer'])
    print(f"Certificate: /CN={subject.get('commonName')}")
    print(f"Issuer: /CN={issuer.get('commonName')}")
    print("----------------------\n")


def send_file_name(ssl_socket, filename):
    """模拟C++的sendFileName函数"""
    print(f"Requesting file: {filename}")
    msg = MsgHeader.pack(MsgTag.FILE_NAME, filename=filename)
    ssl_socket.sendall(msg)

def pls_send_data(ssl_socket, file_info):
    """模拟C++的plsSendData函数"""
    global g_filesize, g_filename, g_filebuff
    
    g_filesize = file_info['filesize']
    g_filename = file_info['filename']
    print(f"Server responded: File '{g_filename}' has size {g_filesize} bytes.")
    
    # 分配内存来接收文件，使用bytearray效率更高
    g_filebuff = bytearray(g_filesize)
    
    # 发送READY_RECV消息
    print("Now, please send data...")
    msg = MsgHeader.pack(MsgTag.READY_RECV)
    ssl_socket.sendall(msg)

def acpt_data(ssl_socket, data_info):
    """模拟C++的acptData函数"""
    global g_bytes_received, g_filebuff
    
    if g_filebuff is None:
        error_handling("g_filebuff is None, cannot accept data!")
        return

    p_no = data_info['packet_no']
    p_size = data_info['packet_size']
    data_chunk = data_info['data_buff']
    
    # 将数据块复制到缓冲区正确的位置
    g_filebuff[p_no : p_no + p_size] = data_chunk
    g_bytes_received += p_size
    
    # 检查是否已接收完所有数据
    if g_bytes_received >= g_filesize:
        print("\nAll data received. Begin writing to file...")
        
        try:
            with open(g_filename, "wb") as f:
                f.write(g_filebuff)
            print(f"Successfully wrote {g_bytes_received} bytes to '{g_filename}'.")
        except IOError as e:
            error_handling(f"File write error: {e}")
            
        # 发送ALL_ACCPTED消息
        msg = MsgHeader.pack(MsgTag.ALL_ACCPTED)
        ssl_socket.sendall(msg)
        
        # 清理缓冲区
        g_filebuff = None

def process_msg(ssl_socket):
    """模拟C++的ProcessMsg函数"""
    try:
        data = ssl_socket.recv(HEADER_SIZE)
        if not data:
            error_handling("Server closed connection unexpectedly.")
            return False

        msg_tag, info = MsgHeader.unpack(data)

        if msg_tag == MsgTag.GET_FILE_FAILED:
            print("Server failed to get the file. Please check the file path on the server.")
            return False
        elif msg_tag == MsgTag.FILE_SIZE:
            pls_send_data(ssl_socket, info)
        elif msg_tag == MsgTag.SEND_DATA:
            acpt_data(ssl_socket, info)
        elif msg_tag == MsgTag.FINISH:
            print(f"Transaction finished. The new file is '{g_filename}', total bytes received: {g_bytes_received}.")
            return False # 结束循环
        else:
            print(f"Received unknown message tag: {msg_tag}")
            return False

    except ssl.SSLError as e:
        error_handling(f"SSL_read error: {e}")
        return False
    except Exception as e:
        error_handling(f"ProcessMsg error: {e}")
        return False
        
    return True

def main():
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <IP> <Port> <FileName>")
        return

    serv_ip = sys.argv[1]
    serv_port = int(sys.argv[2])
    filename_to_get = sys.argv[3]

    # 1. 初始化SSL上下文 (InitSSL)
    ssl_context = init_ssl_context()
    
    raw_socket = None
    ssl_socket = None
    try:
        # 2. 创建并连接套接字 (CreateClntSocket, connect)
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.connect((serv_ip, serv_port))
        print(f"Connected to server at {serv_ip}:{serv_port}")

        # 禁用Nagle算法
        raw_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # 3. 包装套接字并进行SSL握手 (SSL_new, SSL_set_fd, SSL_connect)
        ssl_socket = ssl_context.wrap_socket(raw_socket, server_hostname=serv_ip)
        print(f"SSL connection established. Cipher is {ssl_socket.cipher()}")

        # 4. 显示服务器证书 (ShowCerts)
        show_certs(ssl_socket)
        
        # 5. 发送文件名开始流程
        send_file_name(ssl_socket, filename_to_get)
        
        # 开始计时，模拟RTT计算
        start_time = time.perf_counter()

        # 6. 循环处理消息
        while process_msg(ssl_socket):
            pass

        end_time = time.perf_counter()
        rtt = end_time - start_time
        print(f"The RTT (total transaction time) is {rtt:.6f} s")

    except ssl.SSLCertVerificationError as e:
        error_handling(f"Certificate verification failed: {e}")
    except ConnectionRefusedError:
        error_handling("Connection refused. Is the server running?")
    except Exception as e:
        error_handling(f"An unexpected error occurred: {e}")
    finally:
        # 7. 关闭连接 (SSL_shutdown, etc.)
        if ssl_socket:
            ssl_socket.close() # 在Python中，close()会处理unwrap和关闭底层套接字
        elif raw_socket:
            raw_socket.close()
        
        print("Socket has been closed.")

if __name__ == "__main__":
    main()