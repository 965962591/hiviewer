#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File         :test_munch.py
@Time         :2025/05/28 11:39:18
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :圆形进度条

文件头注释关键字: cc
函数头注释关键字: func
'''
import sys
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5 import QtGui,QtCore
 
class RoundProgress(QWidget):
 
    def __init__(self, parent=None, total_time=5000, interval=50):
        super(RoundProgress, self).__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)  # 添加Tool标志
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景透明
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 显示时不获取焦点
        self.persent = 0
        self.is_completed = False  # 添加完成状态标志
        self.is_quick_complete = False  # 添加快速完成标志
        
        # 设置窗口大小
        self.setFixedSize(106, 106)  # 设置固定大小
        
        # 设置定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        
        # 设置总时长（毫秒）和时间间隔
        self.total_time = total_time
        self.interval = interval
        self.step = 100 / (self.total_time / self.interval)  # 每次更新的进度值
        
        # 启动定时器
        self.timer.start(self.interval)

    def center_on_mouse(self):
        """将窗口居中显示在鼠标位置"""
        # 获取鼠标位置
        cursor_pos = QCursor.pos()
        # 获取鼠标所在的屏幕
        screen = QApplication.screenAt(cursor_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        
        # 计算窗口位置
        screen_geometry = screen.geometry()
        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        
        # 移动窗口到计算出的位置
        self.move(x, y)

    @staticmethod
    def show_progress(parent=None, total_time=5000, interval=50):
        """静态方法用于创建和显示进度条"""
        progress = RoundProgress(parent, total_time, interval)
        progress.center_on_mouse()  # 居中显示
        progress.show()
        progress.raise_()  # 确保窗口在最顶层
        progress.activateWindow()  # 激活窗口
        return progress

    def complete_progress(self):
        """快速完成进度条"""
        self.is_quick_complete = True
        # 加快更新速度
        self.timer.setInterval(10)  # 设置为10毫秒的更新间隔
        self.step = 2  # 每次更新增加2%的进度

    def update_progress(self):
        if self.is_completed:
            return
            
        if self.persent < 100:
            self.persent += self.step
            if self.persent >= 100:
                self.persent = 100
                self.update()  # 确保更新显示100%
                if self.is_quick_complete:
                    self.is_completed = True
                    self.timer.stop()
                    # 添加延时后关闭窗口
                    QTimer.singleShot(100, self.close)
                return
        else:
            self.persent = 100
            self.update()
            self.timer.stop()
            # 添加延时后关闭窗口
            QTimer.singleShot(100, self.close)
        
        self.update()

    def keyPressEvent(self, event):
        # 添加退出键检测
        if event.key() == Qt.Key_Escape:
            self.close_window()
        # 添加空格键检测
        elif event.key() == Qt.Key_Space:  
            self.complete_progress()

    def close_window(self):
        """关闭窗口的方法"""
        self.timer.stop()
        self.close()
        QApplication.quit()

    def mousePressEvent(self, event):
        """添加鼠标点击事件，点击窗口任意位置可关闭"""
        if event.button() == Qt.LeftButton:
            self.close_window()

    def paintEvent(self, event):
        rotateAngle = 360 * self.persent / 100
        # 绘制准备工作，启用反锯齿
        painter = QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
 
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QBrush(QColor("#5F89FF")))
        painter.drawEllipse(3, 3, 100, 100)  # 画外圆
 
        painter.setBrush(QBrush(QColor("#e3ebff")))
        painter.drawEllipse(5, 5, 96, 96)  # 画内圆
 
        gradient = QConicalGradient(50, 50, 91)
        gradient.setColorAt(0, QColor("#95BBFF"))
        gradient.setColorAt(1, QColor("#5C86FF"))
        self.pen = QPen()
        self.pen.setBrush(gradient)  # 设置画刷渐变效果
        self.pen.setWidth(8)
        self.pen.setCapStyle(Qt.RoundCap)
        painter.setPen(self.pen)
        painter.drawArc(QtCore.QRectF(4, 4, 98, 98), int((90 - 0) * 16), int(-rotateAngle * 16))  # 画圆环
 
        font = QtGui.QFont()
        font.setFamily("微软雅黑")
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QColor("#5481FF"))
        painter.drawText(QtCore.QRectF(4, 4, 98, 98), Qt.AlignCenter, "%d%%" % int(self.persent))  # 显示进度条当前进度

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 在这里设置总时长和时间间隔
    total_time = 3000  # 总时长3秒
    interval = 5       # 更新间隔30毫秒
    
    # 使用静态方法创建进度条
    progress = RoundProgress.show_progress(total_time=total_time, interval=interval)

    # 添加1.5秒延时后触发快速完成
    QTimer.singleShot(500, progress.complete_progress)



    sys.exit(app.exec_())