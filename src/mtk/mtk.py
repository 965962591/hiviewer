# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal, QThread

class MTKThread(QThread):
    """执行高通图片解析工具独立线程类"""
    finished = pyqtSignal(bool, str, str) 

    def __init__(self, mtk_dptool_path, images_path):
        super().__init__()
        self.mtk_dptool_path = mtk_dptool_path
        self.images_path = images_path

    def run(self):
        try:
            # 使用高通工具解析图片
            from src.mtk.dump import process_images_in_folder
            process_images_in_folder(self.mtk_dptool_path, self.images_path)
            
            # 解析.txt文件为,toml文件，暂时停用，使用aebox工具解析
            # from src.mtk.parse import parse_main
            # parse_main(self.images_path)

            # 发射信号，传递结果
            self.finished.emit(True, "", self.images_path)
            
        except Exception as e:
            # 发射信号，传递错误信息
            self.finished.emit(False, str(e), self.images_path)  



if __name__ == "__main__":
    mtk_dptool_path = r"D:\Tool_ml\DebugParserV4\DebugParserV4\DebugParser.exe"
    images_path = r"D:\Tuning\M5151\0_picture\0_tuning_para\空景"
    qualcom_thread = MTKThread(mtk_dptool_path, images_path)
    qualcom_thread.start()
