# -*- coding: utf-8 -*-
import os
import zipfile
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QLineEdit
from PyQt5.QtCore import QRunnable, Qt, QObject, pyqtSignal


class CompressWorker(QRunnable):
    """压缩工作线程类"""
    class Signals(QObject):
        """压缩工作线程信号"""
        progress = pyqtSignal(int, int)  # 当前进度,总数
        finished = pyqtSignal(str)  # 完成信号,返回压缩包路径
        error = pyqtSignal(str)  # 错误信号
        cancel = pyqtSignal()  # 取消信号
        
    def __init__(self, files_to_compress, zip_path):
        super().__init__()
        self.files = files_to_compress
        self.zip_path = zip_path
        self.signals = self.Signals()
        self._stop = False
        
    def run(self):
        try:
            with zipfile.ZipFile(self.zip_path, 'w') as zip_file:
                for i, file_item in enumerate(self.files):
                    if self._stop:
                        return
                    
                    try:
                        # 兼容两种输入格式：
                        # 1) (file_path, arcname) 元组
                        # 2) 仅 file_path 字符串
                        if isinstance(file_item, tuple) and len(file_item) == 2:
                            file_path, arcname = file_item
                        else:
                            file_path = file_item
                            arcname = os.path.basename(file_path)

                        zip_file.write(file_path, arcname)
                        self.signals.progress.emit(i + 1, len(self.files))
                    except Exception as e:
                        self.signals.error.emit(f"压缩文件失败: {file_path}, 错误: {e}")
                        continue
                    
            self.signals.finished.emit(self.zip_path)
            
        except Exception as e:
            self.signals.error.emit(f"创建压缩包失败: {e}")
        
    def cancel(self):
        """取消压缩任务"""
        self._stop = True  # 设置停止标志


# 更新 ProgressDialog 类以添加取消按钮
class ProgressDialog(QDialog):
    """压缩进度对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("压缩进度")
        self.setModal(True)

        # 使用无边框窗口风格
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.FramelessWindowHint)
        self.layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar(self)
        self.message_label = QLabel(self)

        # 按钮layout
        btn_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消", self)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.cancel_button)

        # 添加进度条、消息标签和取消按钮到布局
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.message_label)  
        self.layout.addLayout(btn_layout)

        # 设置窗口大小
        self.setFixedSize(400, 200)
        self.cancel_button.clicked.connect(self.cancel_compression)

        # 设置窗口位置为当前鼠标所在显示屏的中央
        self.center_on_current_screen()


    def center_on_current_screen(self):
        # 获取当前鼠标位置和显示屏
        cursor_pos = QCursor.pos()  
        screen = QApplication.desktop().screenNumber(cursor_pos)

        # 获取该显示屏的矩形区域
        screen_geometry = QApplication.desktop().screenGeometry(screen)

        # 计算中央位置
        center_x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        center_y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2

        # 设置窗口位置
        self.move(center_x, center_y)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def set_message(self, message):# 更新 QLabel 内容
        self.message_label.setText(message)  

    def cancel_compression(self):
        # 发送取消信号
        self.parent().cancel_compression()
        self.close()


class InputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 ZIP 名称")
        self.setFixedSize(400, 150)
        self.setStyleSheet("""
            QDialog { background: #23242a; color: #fff; }
            QLabel { font-size: 20px; }
            QLineEdit { font-size: 20px; background: #23242a; color: #00bfff; border: 1px solid #444; border-radius: 4px; padding: 2px 2px; }
            QPushButton { background: #23242a; color: #00bfff; border: 1px solid #00bfff; border-radius: 4px; min-width: 80px; min-height: 30px; }
            QPushButton:hover { background: #00bfff; color: #23242a; }
        """)
        # 整体垂直布局layout
        layout = QVBoxLayout(self)

        # 操作区layout,设置标签栏和编辑栏
        opera_layout = QVBoxLayout()
        self.label = QLabel("请输入压缩包名称(zip格式):")
        self.label.setStyleSheet("color: #fff; font-weight: bold;")
        self.edit = QLineEdit()
        opera_layout.addWidget(self.label)
        opera_layout.addWidget(self.edit)
        layout.addLayout(opera_layout)

        # 按钮区layout,设置确定和取消按钮
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # 信号链接
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_result(self):
        return self.edit.text()