# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal, QThread

class QualcomThread(QThread):
    """执行高通图片解析工具独立线程类"""
    finished = pyqtSignal(bool, str, str) 

    def __init__(self, qualcom_path, images_path):
        super().__init__()
        self.qualcom_path = qualcom_path
        self.images_path = images_path

    def run(self):
        try:
            # 使用高通工具解析图片
            from src.qpm.dump import process_images_in_folder
            process_images_in_folder(self.qualcom_path, self.images_path)
            
            # 解析xml文件
            from src.qpm.parse import parse_main
            parse_main(self.images_path)

            # 发射信号，传递结果
            self.finished.emit(True, "", self.images_path)
            
        except Exception as e:
            # 发射信号，传递错误信息
            self.finished.emit(False, str(e), self.images_path)  



if __name__ == "__main__":
    qualcom_path = r"C:\Qualcomm\Chromatix7\7.3.01.36\Chromatix.exe"
    images_path = r"D:\Tuning\O19\0_pic\02_IN_pic\2025.6.19-IN-一供验证 ISP\NOMAL\O19"
    qualcom_thread = QualcomThread(qualcom_path, images_path)
    qualcom_thread.start()
