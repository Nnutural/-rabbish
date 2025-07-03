import os
import json
from datetime import datetime

# 获取当前脚本的目录并构建 data.json 路径
def get_data_file_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本目录
    return os.path.join(base_dir, 'data.json')

# 保存消息
def save_message(contactId, sender, content, time, date):
    data_file = get_data_file_path()
    print(f"保存消息: 联系人ID={contactId}, 发送者={sender}, 内容={content}, 时间={time}, 日期={date}")

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"contacts": [], "messages": {}}

    messages = data.get('messages', {})
    contact_msgs = messages.get(str(contactId), [])

    day_entry = None
    for day in contact_msgs:
        if day['date'] == date:
            day_entry = day
            break
    if not day_entry:
        day_entry = {"date": date, "messages": []}
        contact_msgs.append(day_entry)

    day_entry['messages'].append({
        "sender": sender,
        "content": content,
        "time": time
    })

    messages[str(contactId)] = contact_msgs
    data['messages'] = messages

    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"消息已保存到 {data_file}")
