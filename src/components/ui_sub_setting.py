# -*- encoding: utf-8 -*-
'''
@File         :ui_sub_setting.py
@Time         :2025/05/30 10:16:24
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :relize setting ui design

使用pathlib获取图片路径notes:
    base_dir = Path(__file__).parent.parent.parent
    icon_path = base_dir / "resource" / "icons" / "setting.png"
str风格图片路径:
    icon_path.as_posix()    # POSIX风格 'd:/Image_process/hiviewer/resource/icons/setting.png'
    icon_path._str          # 原始字符串 'd:\\Image_process\\hiviewer\\resource\\icons\\setting.png'
实现进展：
    1. 初步实现设置界面ui设计,待完善 add by diamond_cz@163.com 2025/05/30
    

'''

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QSplitter, QListWidget, QGraphicsView,
                           QGraphicsScene, QToolBar, QPushButton, QFileDialog,
                           QMessageBox, QLabel, QTableWidget, QScrollArea,
                           QMenu, QAction, QFrame, QListWidgetItem, QSizePolicy)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QUrl, QTimer,Qt, QRectF
from PyQt5.QtGui import QImage, QPixmap, QPainter,QIcon
import os
from pathlib import Path
import xml.etree.ElementTree as ET



# 设置项目根路径
base_dir = Path(__file__).parent.parent.parent


class setting_Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("设置")
        self.resize(1400, 1000)
        self.is_nav_collapsed = False  # 修复未初始化问题
        # 设置应用程序图标
        icon_path = base_dir / "resource" / "icons" / "setting.png"
        self.setWindowIcon(QIcon(icon_path.as_posix()))
        
        # 创建状态栏
        self.statusBar = self.statusBar()
        self.chromatix_label = QLabel("Chromatix路径未设置！")
        self.statusBar.addWidget(self.chromatix_label, 1)
        
        # 初始化基础UI
        self.setup_ui()
        
        # 初始化导航和内容区
        self.init_sections()  
        

    def setup_ui(self):
        # 初始化主窗口布局
        self.splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.splitter)

        # 左侧导航区整体widget
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6)
        
        # 右侧内容区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)

        # 添加到分割器
        self.splitter.addWidget(self.nav_widget)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setSizes([180, 850])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #cccccc;
                width: 6px;
            }
            QSplitter::handle:hover {
                background: #888888;
            }
        """)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # 创建中央主容器
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def init_sections(self):
        # 定义分区
        self.sections = [
            {"name": "按钮组件通用设置", "icon": "setting.png"},
            {"name": "颜色设置", "icon": "color.png"},
            # 可继续添加更多分区
        ]
        # 创建导航项和内容区
        self.nav_list = QListWidget()
        self.nav_list.setIconSize(QSize(24, 24))
        # self.nav_list.setFixedWidth(180)  # 删除或注释此行
        self.nav_list.setMinimumWidth(140)
        self.nav_list.setMaximumWidth(300)
        self.nav_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav_list.itemClicked.connect(self.on_nav_item_clicked)
        self.section_widgets = []
        for sec in self.sections:
            icon_path = base_dir / "resource" / "icons" / sec["icon"]
            item = QListWidgetItem(QIcon(icon_path.as_posix()), sec["name"])
            item.setData(Qt.UserRole, sec["name"])
            self.nav_list.addItem(item)
            # 创建内容区
            section_widget = QWidget()
            layout = QVBoxLayout(section_widget)
            layout.addWidget(QLabel(f"{sec['name']}内容区"))
            if sec["name"] == "按钮组件通用设置":
                layout.addWidget(QLabel("这里是按钮通用设置内容"))
            elif sec["name"] == "颜色设置":
                layout.addWidget(QLabel("这里是颜色设置内容"))
            layout.addStretch(1)
            self.section_widgets.append(section_widget)
        # 导航区添加到布局（放在按钮下方）
        self.nav_layout.addWidget(self.nav_list, 1)
        # 默认选中第一个
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)
            self.show_section(0)

    def on_nav_item_clicked(self, item):
        index = self.nav_list.row(item)
        self.show_section(index)

    def show_section(self, index):
        # 清空右侧内容区
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # 添加当前分区内容
        self.content_layout.addWidget(self.section_widgets[index])

    def on_splitter_moved(self, pos, index):
        if index == 1:
            nav_width = self.splitter.sizes()[0]
            self.update_nav_view(nav_width)

    def on_scroll(self, value):
        # The connect/disconnect for itemClicked is not needed here because
        # setCurrentRow does not emit the itemClicked signal.
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        # If scrolled to the bottom, highlight the last item.
        if scroll_pos == scroll_bar.maximum():
            if self.nav_list.count() > 0:
                self.nav_list.setCurrentRow(self.nav_list.count() - 1)
        else:
            # Find which section is most visible
            current_row = -1
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                widget = getattr(item, 'section_widget', None)
                if widget:
                    # The active section is the last one whose top is at or above the viewport's top.
                    if widget.y() - 20 <= scroll_pos:
                        current_row = i
            
            if current_row != -1:
                self.nav_list.setCurrentRow(current_row)

    def update_nav_view(self, width):
        collapse_threshold = 100
        if width < collapse_threshold:
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                item.setText("")  # 隐藏文字
        else:
            for i, sec in enumerate(self.sections):
                item = self.nav_list.item(i)
                item.setText(sec["name"])  # 恢复文字

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = setting_Window()
    window.show()
    sys.exit(app.exec_()) 