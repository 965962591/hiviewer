# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt

# 导入自定义库
from PIL import Image 
from src.view.sub_compare_image_view import pil_to_pixmap

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

            # 使用pil自动校准图像旋转信息
            with Image.open(path) as img:
                pixmap = pil_to_pixmap(img)
                if not pixmap: # 检查是否成功获取到pixmap
                    raise ValueError("无法加载图片")
                    
            # 设置图片pixmap_item,视图缩放比例自适应视图窗口大小
            self.pixmap_item.setPixmap(pixmap)
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)  
            if pixmap.size().width() > 512 or pixmap.size().height() > 512:
                self.scale(10, 10)  # 设置初始缩放比例为10倍
            else: 
                self.scale(8, 8)    # 如果图片尺寸小于视图窗口尺寸，则缩放比例为8倍
          
        except Exception as e:
            print(f"load_image()-error--从路径加载图片失败: {e}")
            return

    def scale_view(self, scale_factor):
        self.scale(scale_factor, scale_factor)

    def wheelEvent(self, event):
        # // 鼠标滚轮事件处理
        if event.angleDelta().y() > 0:
            self.scale_view(1.1)  # 向前滚动放大
        else:
            self.scale_view(0.9)  # 向后滚动缩小

    def resizeEvent(self, event):
        # 视图窗口大小改变事件处理
        if self.pixmap_item.pixmap().size().width() > 512 or self.pixmap_item.pixmap().size().height() > 512:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        super().resizeEvent(event)
