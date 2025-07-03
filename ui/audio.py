from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtMultimedia import QAudioSource, QAudioFormat, QMediaDevices
from PyQt6.QtCore import QBuffer, QIODevice
import wave
import time
import os

# 语音识别依赖
try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False

class AudioRecorder(QObject):
    # 录音完成后，发送音频文件名和识别文本
    recordingFinished = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.audio_source = None
        self.buffer = None
        self.file_path = None
        self.file_name = None

    @pyqtSlot()
    def startRecording(self):
        format = QAudioFormat()
        format.setSampleRate(16000)
        format.setChannelCount(1)
        format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        device = QMediaDevices.defaultAudioInput()
        self.audio_source = QAudioSource(device, format)
        self.buffer = QBuffer()
        self.buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        self.audio_source.start(self.buffer)
        # 确保audio目录存在
        base_dir = os.path.dirname(os.path.abspath(__file__))
        audio_dir = os.path.join(base_dir, 'audio')
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)
        self.file_name = f"{int(time.time())}.wav"

    @pyqtSlot()
    def stopRecording(self):
        if self.audio_source:
            self.audio_source.stop()
            self.saveWav()
            recognized_text = self.recognizeSpeech(self.file_name)
            self.recordingFinished.emit(self.file_name, recognized_text)

    def saveWav(self):
        self.buffer.seek(0)
        data = self.buffer.data()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_file_path = os.path.join(base_dir, 'audio', self.file_name)
        with wave.open(abs_file_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(16000)
            wf.writeframes(data)
        self.buffer.close()

    def recognizeSpeech(self, file_name):
        if not HAS_SR:
            return ''
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_file_path = os.path.join(base_dir, 'audio', file_name)
        r = sr.Recognizer()
        try:
            with sr.AudioFile(abs_file_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language='zh-CN')
            return text
        except Exception as e:
            print('语音识别失败:', e)
            return ''

    @pyqtSlot(str, result=str)
    def recognizeSpeechFromFile(self, file_name):
        if not HAS_SR:
            return ''
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_file_path = os.path.join(base_dir, 'audio', file_name)
        r = sr.Recognizer()
        try:
            with sr.AudioFile(abs_file_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language='zh-CN')
            return text
        except Exception as e:
            print('语音识别失败:', e)
            return ''
