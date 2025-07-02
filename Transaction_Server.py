import schema as S
import datetime as dt
import time
import socket as skt
import ssl
import json
import uuid
import pprint

'''
这里将处理服务器端的事务，并返回结果给客户端
'''
def handle_register(msg: S.RegisterMsg,):
    print("I'm in register")
    if 1 == 1:
        reply_msg = S.SuccessRegisterMsg(
            username = msg.username,
            user_id = str(uuid.uuid4()),
            time = int(time.time())
        )
        return reply_msg
    

def handle_login(msg: S.LoginMsg):
    print("I'm in login")
    if 1 == 1:
        reply_msg = S.SuccessLoginMsg(
            username = msg.username,
            user_id = str(uuid.uuid4()),
            time = int(time.time())
        )
        return reply_msg
    pass

def handle_logout(msg: S.LogoutMsg):
    print("I'm in logout")
    pass

def handle_get_directory(msg: S.GetDirectoryMsg):
    print("I'm in get directory")
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


