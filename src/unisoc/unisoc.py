# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal, QThread

class UnisocThread(QThread):
    """执行展锐图片解析工具独立线程类"""
    finished = pyqtSignal(bool, str, str) 

    def __init__(self, unisoc_path, images_path):
        super().__init__()
        self.unisoc_path = unisoc_path
        self.images_path = images_path

    def run(self):
        try:
            # 使用展锐工具解析图片
            from src.unisoc.dump import run_iqttool
            run_iqttool(self.unisoc_path, self.images_path)
            
            # 解析.txt文件为,toml文件，暂时停用，使用aebox工具解析
            # from src.unisoc.parse import parse_main
            # parse_main(self.images_path)

            # 发射信号，传递结果
            self.finished.emit(True, "", self.images_path)
            
        except Exception as e:
            # 发射信号，传递错误信息
            self.finished.emit(False, str(e), self.images_path)  



if __name__ == "__main__":
    qualcom_path = r"D:/Tuning/01_Unisoc/ViviMagic_TOOL_V1.5_R1.W25.2502/plugins/3aTool/IQT.exe"
    images_path = r"D:\Tuning\C3Z\03_pic\20250819_20.18.11"
    unisoc_thread = UnisocThread(qualcom_path, images_path)
    unisoc_thread.start()
