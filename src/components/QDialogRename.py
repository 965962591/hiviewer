# -*- coding: utf-8 -*-
import os
from PyQt5.QtWidgets import QLabel, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QMessageBox, QCheckBox
from PyQt5.QtCore import Qt, QSettings, QTimer


class SingleFileRenameDialog(QDialog):
    """单文件重命名对话框类"""
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_dir = os.path.dirname(file_path)
        self.name_without_ext, self.ext = os.path.splitext(self.file_name)
        # 添加新文件路径属性
        self.new_file_path = None  
        # 添加设置对象用于保存复选框状态
        self.settings = QSettings('HiViewer', 'SingleFileRename')
        
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("重命名文件")
        self.setFixedSize(650, 180)
        
        # 主布局
        layout = QVBoxLayout()
        
        # 文件名显示
        self.file_label = QLabel(f"文件名：{self.file_name}")
        layout.addWidget(self.file_label)
        
        # 重命名输入区域
        name_layout = QHBoxLayout()
        name_label = QLabel("重命名为：")
        self.name_input = QLineEdit(self.name_without_ext)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # 显示扩展名选项 - 从设置中读取上次的状态
        show_ext_layout = QHBoxLayout()
        self.show_ext_checkbox = QCheckBox("显示扩展名")
        # 读取上次的选择,默认为False
        last_state = self.settings.value('show_extension', False, type=bool)
        self.show_ext_checkbox.setChecked(last_state)
        show_ext_layout.addWidget(self.show_ext_checkbox)
        show_ext_layout.addStretch()
        layout.addLayout(show_ext_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

        # 如果上次选择显示扩展名,则在输入框中显示完整文件名
        if last_state:
            self.name_input.setText(self.name_without_ext + self.ext)

    def setup_connections(self):
        """设置信号连接"""
        self.ok_button.clicked.connect(self.on_ok_clicked)
        self.cancel_button.clicked.connect(self.reject)
        self.show_ext_checkbox.stateChanged.connect(self.on_checkbox_changed)

    def on_checkbox_changed(self, state):
        """处理显示扩展名复选框状态改变"""
        # 保存当前选择到设置中
        self.settings.setValue('show_extension', state == Qt.Checked)
        
        if state == Qt.Checked:
            self.name_input.setText(self.name_without_ext + self.ext)
        else:
            self.name_input.setText(self.name_without_ext)

    def show_message_box(text, title="提示", timeout=None):
        """显示消息框，宽度自适应文本内容
        
        Args:
            text: 显示的文本内容
            title: 窗口标题，默认为"提示" 
            timeout: 自动关闭的超时时间(毫秒)，默认为None不自动关闭
        """
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(text)

        # 设置定时器自动关闭
        if timeout is not None:
            QTimer.singleShot(timeout, msg_box.close)

        # 使用 exec_ 显示模态对话框
        msg_box.exec_() 

    def on_ok_clicked(self):
        """处理确定按钮点击"""
        new_name = self.name_input.text()
        if not new_name:
            self.show_message_box("文件名不能为空！", "错误", 500)
            return
            
        # 构建新文件路径
        if not self.show_ext_checkbox.isChecked():
            new_name = new_name + self.ext
        new_path = os.path.join(self.file_dir, new_name)
        
        # 检查文件是否已存在
        if os.path.exists(new_path) and new_path != self.file_path:
            self.show_message_box("文件已存在！", "错误", 500)
            return
            
        try:
            os.rename(self.file_path, new_path)
            self.new_file_path = new_path  # 更新新文件路径
            self.accept()
        except Exception as e:
            self.show_message_box(f"重命名失败: {str(e)}", "错误", 1000)

    def get_new_file_path(self):
        """返回新的文件路径"""
        return self.new_file_path
    
    
