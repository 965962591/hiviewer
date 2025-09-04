'''
@File         :custom_qdialog_fastapi.py
@Time         :2025/08/07 17:10:36
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :自定义Fastapi对话框
'''

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class FastApiDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置 FastAPI 服务")
        self.setFixedSize(400, 200)
        self.setStyleSheet("""
            QDialog { background: #23242a; color: #fff; }
            QLabel { font-size: 15px; }
            QLineEdit { background: #23242a; color: #00bfff; border: 1px solid #444; border-radius: 4px; padding: 2px 6px; }
            QPushButton { background: #23242a; color: #00bfff; border: 1px solid #00bfff; border-radius: 4px; min-width: 80px; min-height: 28px; }
            QPushButton:hover { background: #00bfff; color: #23242a; }
        """)
        layout = QVBoxLayout(self)
        # IP编辑栏设置
        ip_layout = QHBoxLayout()
        self.ip_label = QLabel("IP地址：")
        self.ip_label.setStyleSheet("color: #fff; font-weight: bold;")
        self.ip_edit = QLineEdit("127.0.0.1")
        ip_layout.addWidget(self.ip_label)
        ip_layout.addWidget(self.ip_edit)
        layout.addLayout(ip_layout)
        # 端口编辑栏设置
        port_layout = QHBoxLayout()
        self.port_label = QLabel("端 口 ：")
        self.port_label.setStyleSheet("color: #fff; font-weight: bold;")
        self.port_edit = QLineEdit("8000")
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_edit)
        layout.addLayout(port_layout)
        # 按钮设置
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        # 信号链接
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def get_result(self):
        return self.ip_edit.text(), self.port_edit.text()