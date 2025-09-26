# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from pathlib import Path

"""设置本项目的入口路径,全局变量BasePath,设置图标路径ICONPATH"""
BASEPATH = Path(__file__).parent.parent.parent
ICONPATH = Path(BASEPATH, "resource", "icons", "viewer_3.ico").as_posix()


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
    
    # 设置消息框主图标,获取项目根目录并拼接图标路径
    msg_box.setWindowIcon(QIcon(ICONPATH))

    # 设置定时器自动关闭
    if timeout is not None:
        QTimer.singleShot(timeout, msg_box.close)

    # 使用 exec_ 显示模态对话框
    msg_box.exec_() 

