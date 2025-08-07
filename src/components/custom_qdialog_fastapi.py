'''
@File         :custom_qdialog_fastapi.py
@Time         :2025/08/07 17:10:36
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :自定义Fastapi对话框
'''

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtGui import QIcon

class FastApiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 FastAPI 服务")
        if parent and parent.icon_path:
            self.setWindowIcon(QIcon(parent.icon_path))
        self.setFixedSize(400, 200)
        self.setStyleSheet("""
            QDialog { background: #23242a; color: #fff; }
            QLabel { font-size: 15px; }
            QLineEdit { background: #23242a; color: #00bfff; border: 1px solid #444; border-radius: 4px; padding: 2px 6px; }
            QPushButton { background: #23242a; color: #00bfff; border: 1px solid #00bfff; border-radius: 4px; min-width: 80px; min-height: 28px; }
            QPushButton:hover { background: #00bfff; color: #23242a; }
        """)
        layout = QVBoxLayout(self)
        # IP
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP地址：")
        ip_label.setStyleSheet("color: #fff; font-weight: bold;")
        self.ip_edit = QLineEdit("127.0.0.1")
        if parent and parent.fast_api_host:
            self.ip_edit.setText(parent.fast_api_host)
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_edit)
        layout.addLayout(ip_layout)
        # 端口
        port_layout = QHBoxLayout()
        port_label = QLabel("端 口 ：")
        port_label.setStyleSheet("color: #fff; font-weight: bold;")
        self.port_edit = QLineEdit("8000")
        if parent and parent.fast_api_port:
            self.port_edit.setText(parent.fast_api_port)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_edit)
        layout.addLayout(port_layout)
        # 按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        # 信号
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
    def get_result(self):
        return self.ip_edit.text(), self.port_edit.text()