def _execute_login(client_address: str, message: LoginMsg) -> None:
    print(f"[服务器日志] 收到来自 {client_address} 的登录请求。\n")
    user_data = None
    login_username = message.username

    #  根据提供的标识符查找用户
    if message.username:
        user_data = USER_DATABASE.get(message.username)
    elif message.userID:
        for uname, udata in USER_DATABASE.items():
            if udata['userID'] == message.userID:
                user_data = udata
                login_username = uname
                break
    
    if not user_data:
        print(f"[服务器日志] 校验失败: 提供的标识符未找到对应用户。\n")
        response = FailLoginMsg(username=login_username, errortype=FailType.USER_NOT_FOUND.value)
        send_to_client(client_address, response)
        return

    # 验证密码哈希值是否匹配
    provided_secret_hash = _hash_secret(message.secret)
    
    if provided_secret_hash == user_data['secret']:
        # 验证成功
        print(f"[服务器日志] 用户 '{login_username}' 验证成功。\n")
        response = SuccessLoginMsg(username=login_username, userID=user_data['userID'])
        send_to_client(client_address, response)
    else:
        # 验证失败
        print(f"[服务器日志] 校验失败: 用户 '{login_username}' 的密码不正确。\n")
        response = FailLoginMsg(username=login_username, errortype=FailType.INCORRECT_SECRET.value)
        send_to_client(client_address, response)