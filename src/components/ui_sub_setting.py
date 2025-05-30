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
                           QMessageBox, QLabel, QTableWidget, QHeaderView,
                           QMenu, QAction, QListWidgetItem)
from PyQt5.QtCore import Qt, QRectF, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter,QIcon
import os
from pathlib import Path
import xml.etree.ElementTree as ET



# 设置项目根路径
base_dir = Path(__file__).parent.parent.parent




class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene())
        # 设置渲染质量
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        # 设置场景自适应视图大小
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignCenter)
        # 设置调整大小策略
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        # logger.debug('CustomGraphicsView initialized')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 当视图大小改变时，调整图片大小
        if not self.scene().items():
            return
        try:
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
            # logger.debug(f'View resized to {event.size().width()}x{event.size().height()}')
        except Exception as e:
            # logger.error(f'Error in resizeEvent: {str(e)}')
            pass

    def showImage(self, image_path):
        """显示图片并保持宽高比"""
        if not os.path.exists(image_path):
            return False
            
        try:
            # 清除当前场景
            self.scene().clear()
            
            # 加载图片
            image = QImage(image_path)
            if image.isNull():
                return False
                
            
            # 创建像素图并添加到场景
            pixmap = QPixmap.fromImage(image)
            self.scene().addPixmap(pixmap)
            # 使用QRectF而不是QRect
            self.scene().setSceneRect(QRectF(pixmap.rect()))
            
            # 调整视图以适应图片
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
            return True
        except Exception as e:
            return False





class C7Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("设置")
        self.resize(1400, 1000)

        # 设置应用程序图标
        icon_path = base_dir / "resource" / "icons" / "setting.png"

        self.setWindowIcon(QIcon(icon_path.as_posix()))

        # 创建状态栏
        self.statusBar = self.statusBar()
        self.chromatix_label = QLabel("Chromatix路径未设置！")
        self.statusBar.addWidget(self.chromatix_label, 1)
        
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 添加按钮到工具栏
        btn_chromatix = QPushButton("Chromatix", self)
        btn_pic = QPushButton("pic", self)
        btn_meta = QPushButton("meta", self)  # 修改按钮名称
        btn_xml = QPushButton("xml", self)    # 新增XML按钮
        toolbar.addWidget(btn_chromatix)
        
        # 添加10像素的间隔
        spacer1 = QWidget()
        spacer1.setFixedWidth(10)
        toolbar.addWidget(spacer1)
        
        toolbar.addWidget(btn_pic)
        
        # 添加10像素的间隔
        spacer2 = QWidget()
        spacer2.setFixedWidth(10)
        toolbar.addWidget(spacer2)
        
        toolbar.addWidget(btn_meta)
        
        # 添加10像素的间隔
        spacer3 = QWidget()
        spacer3.setFixedWidth(10)
        toolbar.addWidget(spacer3)
        
        toolbar.addWidget(btn_xml)
        
        # 连接按钮信号
        btn_chromatix.clicked.connect(self.on_chromatix_clicked)
        btn_pic.clicked.connect(self.on_pic_clicked)
        btn_meta.clicked.connect(self.on_meta_clicked)  # 修改连接函数
        btn_xml.clicked.connect(self.on_xml_clicked)    # 新增连接函数
        
        # 创建下方的主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)  # 禁止完全折叠
        main_splitter.setHandleWidth(2)  # 设置分隔条宽度
        
        # 左侧图片列表
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_image_selected)
        self.image_list.setMinimumWidth(200)  # 设置最小宽度
        self.image_list.setContextMenuPolicy(Qt.CustomContextMenu)  # 设置自定义上下文菜单策略
        # self.image_list.customContextMenuRequested.connect(self.show_context_menu)  # 连接右键菜单信号
        main_splitter.addWidget(self.image_list)
        
        # 中间图片显示区域
        self.graphics_view = CustomGraphicsView()
        self.graphics_view.setMinimumWidth(400)  # 设置最小宽度
        main_splitter.addWidget(self.graphics_view)
        
        # 右侧分割器
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.setChildrenCollapsible(False)
        
        # 右侧上方面板 - 光照信息表格
        self.lux_table = QTableWidget()
        self.lux_table.setRowCount(1)
        self.lux_table.setColumnCount(12)
        self.lux_table.setHorizontalHeaderLabels([
            "Lux", "CCT", "BL", "AEC", "FPS", 
            "SG", "ShG", "ET",  # 简化显示名称
            "ISO", "EV", "Zoom", "HDR"
        ])
        self.lux_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lux_table.verticalHeader().setVisible(False)
        right_splitter.addWidget(self.lux_table)
        
        # 右侧中间面板 - 数据表格
        self.data_display = QWidget()
        right_splitter.addWidget(self.data_display)
        
        # 右侧下方面板 - SA步骤图
        # self.sa_steps_view = CustomSAStepsView()  # 使用自定义的视图类
        # self.sa_steps_view.setRenderHint(QPainter.Antialiasing)
        # right_splitter.addWidget(self.sa_steps_view)
        
        # 创建XML显示器实例
        # self.xml_show = C7XMLShow(self.lux_table, self.data_display, self.sa_steps_view)
        
        # 设置右侧分割器的初始大小比例
        right_splitter.setStretchFactor(0, 1)  # 上方面板
        right_splitter.setStretchFactor(1, 5)  # 中间面板
        right_splitter.setStretchFactor(2, 2)  # 下方面板
        
        main_splitter.addWidget(right_splitter)
        
        # 设置分割器的初始大小比例
        main_splitter.setStretchFactor(0, 1)  # 左侧列表
        main_splitter.setStretchFactor(1, 2)  # 中间显示区域
        main_splitter.setStretchFactor(2, 5)  # 右侧面板
        
        # 计算并设置初始大小
        total_width = 1200  # 假设初始总宽度
        sizes = [
            int(total_width * 0.2),  # 左侧列表 20%
            int(total_width * 0.4),  # 中间显示区域 40%
            int(total_width * 0.4)   # 右侧面板 40%
        ]
        # logger.debug(f"Setting initial splitter sizes to: {sizes}")
        main_splitter.setSizes(sizes)
        
        # 将分割器添加到主布局
        main_layout.addWidget(main_splitter)
        
        # 显示后再次设置大小
        QTimer.singleShot(100, lambda: self.updateSplitterSizes(main_splitter))



    def on_chromatix_clicked(self):
        """处理Chromatix按钮点击事件"""
        print("Chromatix按钮点击事件")
    
    def on_pic_clicked(self):
        """处理pic按钮点击事件"""
        print("pic按钮点击事件")
    
    
    def on_image_selected(self, item):
        """处理图片选择事件"""
        print("图片选择事件")
    
    def on_meta_clicked(self):
        """处理meta按钮点击事件"""
        print("meta按钮点击事件")

    def on_xml_clicked(self):
        """处理xml按钮点击事件"""
        print("xml按钮点击事件")

    
    def updateSplitterSizes(self, splitter):
        """更新分割器大小比例"""
        width = splitter.width()
        if width > 0:
            # 设置2:4:4的比例
            sizes = [
                int(width * 0.1),  # 左侧列表 20%
                int(width * 0.2),  # 中间显示区域 40%
                int(width * 0.5)   # 右侧面板 40%
            ]
            # logger.debug(f"Updated splitter sizes to: {sizes}")
            splitter.setSizes(sizes)

    def resizeEvent(self, event):
        """处理窗口大小改变事件"""
        super().resizeEvent(event)
        # 当窗口大小改变时，更新分割器比例
        for child in self.findChildren(QSplitter):
            if child.orientation() == Qt.Horizontal:
                self.updateSplitterSizes(child)
        # logger.debug(f"Window resized to: {event.size().width()}x{event.size().height()}")

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        try:
            # 确保资源正确释放
            if hasattr(self, 'image_processor'):
                # 停止所有可能正在运行的线程
                if self.image_processor.meta_thread is not None:
                    try:
                        self.image_processor.meta_thread.finished.disconnect()
                    except:
                        pass
                    self.image_processor.meta_thread = None
                
                if self.image_processor.xml_thread is not None:
                    try:
                        self.image_processor.xml_thread.finished.disconnect()
                    except:
                        pass
                    self.image_processor.xml_thread = None
            
            # 清理图形视图
            if hasattr(self, 'graphics_view') and self.graphics_view is not None:
                scene = self.graphics_view.scene()
                if scene is not None:
                    scene.clear()
            
            # 清理XML显示器
            if hasattr(self, 'xml_show'):
                self.xml_show = None
            
            # 清空图像列表
            if hasattr(self, 'image_list'):
                self.image_list.clear()
            
            print("窗口正常关闭，资源已清理")
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")
        
        # 接受关闭事件
        event.accept()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = C7Window()
    window.show()
    sys.exit(app.exec_()) 