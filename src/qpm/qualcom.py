# -*- coding: utf-8 -*-
import subprocess
from PyQt5.QtCore import pyqtSignal, QThread

class CommandThread(QThread):
    """执行高通图片解析工具独立线程类"""
    finished = pyqtSignal(bool, str, str)  # 添加 images_path 参数

    def __init__(self, command, images_path):
        super().__init__()
        self.command = command
        self.images_path = images_path

    def run(self):
        try:
            if False:
                result = subprocess.run(
                    self.command, 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    encoding='utf-8')
                self.finished.emit(result.returncode == 0, result.stderr, self.images_path)  # 发射信号，传递结果
            
            # 使用 /c 参数，命令执行完成后关闭窗口，直接独立线程
            result = subprocess.run(
                f'start /wait cmd /c {self.command}',  # /wait 等待新窗口关闭
                shell=True,
                stdout=subprocess.PIPE,  # 捕获标准输出
                stderr=subprocess.PIPE,  # 捕获标准错误
                text=True  # 将输出解码为字符串
            )
            
            # 发射信号，传递结果
            self.finished.emit(result.returncode == 0, result.stderr, self.images_path)
            
        except Exception as e:
            self.finished.emit(False, str(e), self.images_path)  # 发射信号，传递错误信息