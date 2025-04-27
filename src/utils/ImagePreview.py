from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt, QSize

class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.setBackgroundBrush(QColor(127,127,127)) 
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # 设置鼠标左键按住可以移动视图

    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            raise ValueError("无法加载图片")
        # 设置图片的初始缩放比例为原始大小的50%
        pixmap = pixmap.scaled(pixmap.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_item.setPixmap(pixmap)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)  # 视图缩放比例自适应视图窗口大小

        self.scale(15, 15)  # 设置初始缩放比例为15倍

    def load_image_from_qimage(self, q_img):
        """从QImage对象加载图片"""
        pixmap = QPixmap.fromImage(q_img)
        if pixmap.isNull():
            raise ValueError("无法加载图片")
        # 设置图片的初始缩放比例为原始大小的50%
        pixmap = pixmap.scaled(pixmap.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_item.setPixmap(pixmap)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)  # 视图缩放比例自适应视图窗口大小

        self.scale(15, 15)  # 设置初始缩放比例为15倍

    def scale_view(self, scale_factor):
        self.scale(scale_factor, scale_factor)

    def wheelEvent(self, event):
        # // 鼠标滚轮事件处理
        if event.angleDelta().y() > 0:
            self.scale_view(1.1)  # 向前滚动放大
        else:
            self.scale_view(0.9)  # 向后滚动缩小

    def mousePressEvent(self, event):
        # 鼠标左键按下事件处理
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 鼠标移动事件处理
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        # 视图窗口大小改变事件处理
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        super().resizeEvent(event)
