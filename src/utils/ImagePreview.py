# -*- coding: utf-8 -*-
from pathlib import Path
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QColor, QPixmap, QPainter, QImageReader
from PyQt5.QtCore import Qt

# 导入自定义库
from PIL import Image 
from src.view.sub_compare_image_view import pil_to_pixmap

# 设置基础路径
BASEICONPATH = Path(__file__).parent.parent.parent

class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.setBackgroundBrush(QColor(127,127,127)) 

    def load_image(self, path):
        """从路径加载图片"""
        try:
            # 直接使用pyqt库中QPixmap读取，无法自动识别图像方向信息，移除该方法
            # pixmap = QPixmap(path)

            if False:
                # 方案一：使用QImageReader高效加载,设置自动转换（处理EXIF方向信息）,设置高质量缩放
                reader = QImageReader(path)
                reader.setAutoTransform(True) 
                reader.setQuality(100)           
                # 尝试读取图像
                if bool(img := reader.read()):
                    pixmap = QPixmap.fromImage(img)
            
            if True:
                # 使用PIL库处理图像，生成pixmap
                with Image.open(path) as img:
                    # 对png格式图片直接用QPixmap读取
                    if img.format in ["PNG"]:
                        pixmap = QPixmap(path)
                    else:
                        pixmap = pil_to_pixmap(img)

            # 确保生成的pixmap有效
            if not pixmap: 
                raise ValueError("无法加载图片")
            
            # 设置图片pixmap_item,视图缩放比例自适应视图窗口大小
            self.pixmap_item.setPixmap(pixmap)
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)  

            # 设置初始缩放比例为10倍，如果图片尺寸小于视图窗口尺寸，则缩放比例为8倍
            if pixmap.size().width() > 512 or pixmap.size().height() > 512:
                self.scale(10, 10)  
            else: 
                self.scale(8, 8)    

        except Exception as e:
            print(f"load_image()-error--从路径加载图片失败: {e}")
            return

    def scale_view(self, scale_factor):
        """
        该函数主要是实现了一个视图缩放功能.

        """
        self.scale(scale_factor, scale_factor)

    def wheelEvent(self, event):
        """
        该函数主要是实现了一个 鼠标滚轮事件处理，向前滚动放大，向后滚动缩小 功能.
        Args:
            event (type): Description of param1.

        """
        if event.angleDelta().y() > 0:
            self.scale_view(1.1)  
        else:
            self.scale_view(0.9)  

    def resizeEvent(self, event):
        """
        该函数主要是实现了一个 视图窗口大小改变事件处理 功能.
        Args:
            event (type): Description of param1.

        """
        if self.pixmap_item.pixmap().size().width() > 512 or self.pixmap_item.pixmap().size().height() > 512:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        super().resizeEvent(event)
