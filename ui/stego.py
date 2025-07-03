from PyQt6.QtCore import QObject, pyqtSlot
import base64
from PIL import Image
import io
import os
import time

class StegoBackend(QObject):
    @pyqtSlot(str, str, str, result='QString')
    def encodeStegoImage(self, sender_id, base64img, text):
        # 解码base64图片
        header, b64data = base64img.split(',', 1)
        img_bytes = base64.b64decode(b64data)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
        pixels = img.load()
        if pixels is None:
            return ''
        # 用UTF-8编码支持中文
        text_bytes = text.encode('utf-8')
        bin_text = ''.join([format(b, '08b') for b in text_bytes]) + '00000000'  # 结尾0字节
        w, h = img.size
        idx = 0
        for y in range(h):
            for x in range(w):
                if idx < len(bin_text):
                    px = pixels[x, y]
                    if not isinstance(px, tuple) or len(px) < 4:
                        continue
                    r, g, b, a = px
                    r = (r & ~1) | int(bin_text[idx])
                    pixels[x, y] = (r, g, b, a)
                    idx += 1
        # 保存图片，文件名格式：发送人序号_时间戳_stego.png
        save_dir = os.path.join(os.path.dirname(__file__), 'Image')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        filename = f'{sender_id}_{int(time.time())}_stego.png'
        save_path = os.path.join(save_dir, filename)
        img.save(save_path)
        return filename

    @pyqtSlot(str, result='QString')
    def decodeStegoImage(self, img_name):
        # 解析图片最低位隐写明文
        img_path = os.path.join(os.path.dirname(__file__), 'Image', img_name)
        if not os.path.exists(img_path):
            return ''
        img = Image.open(img_path).convert('RGBA')
        pixels = img.load()
        if pixels is None:
            return ''
        w, h = img.size
        bits = ''
        for y in range(h):
            for x in range(w):
                px = pixels[x, y]
                if not isinstance(px, tuple) or len(px) < 4:
                    continue
                r = px[0]
                bits += str(r & 1)
        # 每8位转字节，遇到全0字节停止
        bytes_list = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            if byte == '00000000' or len(byte) < 8:
                break
            bytes_list.append(int(byte, 2))
        try:
            return bytes(bytes_list).decode('utf-8')
        except Exception:
            return ''
