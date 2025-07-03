import os
import json
import base64
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSlot  # 导入 QObject 和 pyqtSlot

class Backend(QObject):  # 让 Backend 继承 QObject
    def __init__(self):
        super().__init__()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(self.base_dir, 'data.json')
        self.image_dir = os.path.join(self.base_dir, 'image')

        # 创建图片目录（如果不存在）
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    def save_message(self, contact_id, sender, content, time, date):
        print(f"保存消息: 联系人ID={contact_id}, 发送者={sender}, 内容={content}, 时间={time}, 日期={date}")

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"contacts": [], "messages": {}}

        messages = data.get('messages', {})
        contact_msgs = messages.get(str(contact_id), [])

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

        messages[str(contact_id)] = contact_msgs
        data['messages'] = messages

        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("消息已保存到 data.json")

    def save_image_message(self, contact_id, sender, base64_image, time, date):
        print(f"保存图片: 联系人ID={contact_id}, 发送者={sender}, 时间={time}, 日期={date}")

        # 将 base64 图片数据转换为字节
        image_data = base64_image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # 图片文件命名规则：联系人ID_时间戳.png
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_name = f"{contact_id}_{timestamp}.png"
        image_path = os.path.join(self.image_dir, image_name)

        # 如果文件已存在，添加(1), (2) 等后缀
        counter = 1
        while os.path.exists(image_path):
            image_name = f"{contact_id}_{timestamp}({counter}).png"
            image_path = os.path.join(self.image_dir, image_name)
            counter += 1

        # 保存图片
        with open(image_path, 'wb') as img_file:
            img_file.write(image_bytes)

        # 将图片路径添加到 data.json
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"contacts": [], "messages": {}}

        messages = data.get('messages', {})
        contact_msgs = messages.get(str(contact_id), [])

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
            "content": f"图片: {image_name}",  # 保存图片的路径
            "time": time
        })

        messages[str(contact_id)] = contact_msgs
        data['messages'] = messages

        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"图片已保存，路径为：{image_path}")

    @pyqtSlot(int, str, str, str, str)
    def saveMessage(self, contact_id, sender, content, time, date):
        self.save_message(contact_id, sender, content, time, date)

    @pyqtSlot(int, str, str, str, str)
    def saveImageMessage(self, contact_id, sender, base64_image, time, date):
        self.save_image_message(contact_id, sender, base64_image, time, date)
