# sslserver.py
import socket
import ssl
import os
import sys
import struct
from enum import Enum

# 1. 模拟C++的枚举 Msg_Tag
class MsgTag(Enum):
    FILE_NAME = 1
    FILE_SIZE = 2
    READY_RECV = 3
    SEND_DATA = 4
    ALL_ACCPTED = 5
    GET_FILE_FAILED = 6
    FINISH = 7

# 定义与C++版本匹配的常量
# PACKET_SIZE = 1024 - sizeof(int)*3 = 1024 - 4*3 = 1012
PACKET_SIZE = 1012
# 总消息头大小为1024，与g_buff大小一致
HEADER_SIZE = 1024

# 全局变量，与C++版本保持一致
g_filebuff = None
g_filesize = 0
g_bytes_sent = 0

# 2. 模拟C++的MsgHeader结构体
# 我们创建一个类来处理打包和解包，以替代C++的struct和union
class MsgHeader:
    """
    处理与C++版本兼容的二进制消息。
    消息格式:
    - 4字节: msgID (int)
    - 1020字节: payload (union部分)
    总共 1024 字节
    """
    @staticmethod
    def pack(msg_tag, **kwargs):
        """打包消息，使其与C++的struct兼容"""
        msg_id_bytes = struct.pack('!I', msg_tag.value) # '!I' for network byte order unsigned int
        payload = b''

        if msg_tag == MsgTag.FILE_SIZE:
            # 模拟 FileInfo 结构
            filename = kwargs.get('filename', '').encode('utf-8')
            filesize = kwargs.get('filesize', 0)
            # 格式: 256s (文件名), I (文件大小)
            payload = struct.pack('!256sI', filename, filesize)
        elif msg_tag == MsgTag.SEND_DATA:
            # 模拟 FileData 结构
            packet_no = kwargs.get('packet_no', 0)
            packet_size = kwargs.get('packet_size', 0)
            data_buff = kwargs.get('data_buff', b'')
            # 格式: I (包序号), I (包大小), data
            payload = struct.pack('!II', packet_no, packet_size) + data_buff
        
        # 使用空字节填充payload，确保总长度为1024字节
        full_message = msg_id_bytes + payload
        return full_message.ljust(HEADER_SIZE, b'\0')

    @staticmethod
    def unpack(data):
        """解包从网络接收到的数据"""
        msg_id_val = struct.unpack('!I', data[:4])[0]
        msg_tag = MsgTag(msg_id_val)
        payload = data[4:]
        
        info = {}
        if msg_tag == MsgTag.FILE_NAME:
            # 模拟 FileInfo 结构
            filename_bytes = struct.unpack('!256s', payload[:256])[0]
            info['filename'] = filename_bytes.strip(b'\0').decode('utf-8')
        elif msg_tag == MsgTag.READY_RECV:
            # 这个消息没有payload
            pass
            
        return msg_tag, info

def error_handling(message):
    """模拟C++的ErrorHandling函数"""
    print(f"[error] {message} failed, line:{sys._getframe(1).f_lineno}", file=sys.stderr)

def init_ssl_context():
    """模拟C++的InitSSL函数，配置服务器端SSL上下文"""
    # 对应 SSL_CTX_new(SSLv23_server_method())
    # PROTOCOL_TLS 表示支持高版本TLS，由库自动协商
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # 对应 SSL_CTX_set_min/max_proto_version
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2

    print("Initializing SSL Context...")
    try:
        # 对应 SSL_CTX_set_verify 和 SSL_CTX_load_verify_locations
        # 要求客户端提供证书，并用ca.crt验证
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile="ca.crt")

        # 对应 SSL_CTX_use_certificate_file 和 SSL_CTX_use_PrivateKey_file
        context.load_cert_chain(certfile="server.crt", keyfile="server_rsa_private.pem.unsecure")
        
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
    
    # 打印证书验证结果
    # 在Python中，如果握手成功且verify_mode=CERT_REQUIRED，则表示验证已通过
    print("Certificate validation passed.")

    subject = dict(x[0] for x in cert['subject'])
    issuer = dict(x[0] for x in cert['issuer'])
    print(f"Certificate: /CN={subject.get('commonName')}")
    print(f"Issuer: /CN={issuer.get('commonName')}")
    print("----------------------\n")


def normalize_path(src_path):
    """模拟C++的normalize_path函数"""
    if not src_path:
        return None
    return src_path.replace('\\', '/')

def get_file(ssl_socket, file_info):
    """模拟C++的getFile函数"""
    global g_filebuff, g_filesize
    
    filename_req = normalize_path(file_info['filename'])
    print(f"Client requested file: {filename_req}")

    if not os.path.exists(filename_req):
        print(f"Cannot find file: {filename_req}")
        msg = MsgHeader.pack(MsgTag.GET_FILE_FAILED)
        ssl_socket.sendall(msg)
        return

    print(f"Found file: {filename_req}")
    
    # 获取文件大小并读入内存
    g_filesize = os.path.getsize(filename_req)
    with open(filename_req, "rb") as f:
        g_filebuff = f.read()

    # 准备并发送FILE_SIZE消息
    base_filename = os.path.basename(filename_req)
    msg = MsgHeader.pack(MsgTag.FILE_SIZE, filename=base_filename, filesize=g_filesize)
    
    print(f"Sending file info: name='{base_filename}', size={g_filesize} bytes")
    ssl_socket.sendall(msg)

def send_data(ssl_socket):
    """模拟C++的sendData函数"""
    global g_bytes_sent
    print("Client is ready. Starting file transfer...")
    
    offset = 0
    while offset < g_filesize:
        # 计算当前数据包的大小
        chunk_size = min(PACKET_SIZE, g_filesize - offset)
        
        # 从全局缓冲区中获取数据块
        data_chunk = g_filebuff[offset : offset + chunk_size]
        
        # 打包SEND_DATA消息
        msg = MsgHeader.pack(
            MsgTag.SEND_DATA,
            packet_no=offset,
            packet_size=chunk_size,
            data_buff=data_chunk
        )JJJ
        
        ssl_socket.sendall(msg)
        g_bytes_sent += chunk_size
        offset += chunk_size
        
    print(f"\nFinished sending file data. Total sent: {g_bytes_sent} bytes.")

def finish(ssl_socket):
    """模拟C++的finish函数"""
    global g_bytes_sent
    print(f"{g_bytes_sent} bytes were totally sent.")
    msg = MsgHeader.pack(MsgTag.FINISH)
    ssl_socket.sendall(msg)

def process_message(ssl_socket):
    """模拟C++的ProcessMessage函数"""
    try:
        # 对应 SSL_read
        data = ssl_socket.recv(HEADER_SIZE)
        if not data:
            print("Client has closed the connection.")
            return False
        
        # 解包消息
        msg_tag, info = MsgHeader.unpack(data)
        
        # 对应C++的switch语句
        if msg_tag == MsgTag.FILE_NAME:
            get_file(ssl_socket, info)
        elif msg_tag == MsgTag.READY_RECV:
            send_data(ssl_socket)
        elif msg_tag == MsgTag.ALL_ACCPTED:
            finish(ssl_socket)
            return False # 结束循环
        else:
            print(f"Received unknown message tag: {msg_tag}")
            return False

    except ssl.SSLError as e:
        error_handling(f"SSL_read error: {e}")
        return False
    except Exception as e:
        error_handling(f"ProcessMessage error: {e}")
        return False
        
    return True

def main():
    # if len(sys.argv) != 2:
    #     print(f"Usage: python {sys.argv[0]} <Port>")
    #     return

    # serv_port = int(sys.argv[1])
    serv_port = 47474


    # 1. 初始化SSL上下文 (InitSSL)
    ssl_context = init_ssl_context()
    
    # 2. 创建、绑定、监听套接字 (InitSocket, CreateServSocket)
    # Python的socket库不需要WSAStartup
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', serv_port))
    server_socket.listen(10)
    print(f"Server socket created. Waiting for client connection on port {serv_port}...")

    conn, addr = server_socket.accept()
    print(f"Accepted connection from {addr[0]}:{addr[1]}")

    # 禁用Nagle算法，与C++版本一致
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    ssl_socket = None
    try:
        # 3. 将套接字包装为SSL套接字并进行握手 (SSL_new, SSL_set_fd, SSL_accept)
        # wrap_socket会完成握手
        ssl_socket = ssl_context.wrap_socket(conn, server_side=True)
        
        # 4. 显示对端证书 (ShowCerts)
        show_certs(ssl_socket)
        
        # 5. 循环处理消息 (ProcessMessage)
        while process_message(ssl_socket):
            pass # 循环由process_message控制
            
    except ssl.SSLError as e:
        error_handling(f"SSL handshake (accept) error: {e}")
    except Exception as e:
        error_handling(f"An unexpected error occurred: {e}")
    finally:
        # 6. 关闭连接 (SSL_shutdown, SSL_free, CloseSocket, SSL_CTX_free)
        # Python的with语句或try/finally能更好地处理资源释放
        if ssl_socket:
            try:
                # SSL_shutdown
                ssl_socket.unwrap()
            except (ssl.SSLError, OSError) as e:
                # 可能会因为对方已关闭连接而出错，可以忽略
                pass
            # SSL_free, closesocket
            ssl_socket.close()
        
        server_socket.close()
        print("Sockets have been closed.")
        # SSL_CTX_free由Python垃圾回收器处理

if __name__ == "__main__":
    main()