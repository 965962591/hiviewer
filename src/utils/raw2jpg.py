# -*- coding: utf-8 -*-
"""python标准库"""
import os
import sys
import json 

"""python三方模块"""
import cv2
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QWheelEvent, QPainter, QIcon, QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QGraphicsView, QMessageBox, 
                            QRadioButton, QButtonGroup, QSizePolicy, QGraphicsScene, QVBoxLayout, QMessageBox)
                            
"""导入自定义的模块"""
from src.utils.mipi2raw import convertMipi2Raw, bayer_order_maps

"""子界面，实现MIPI RAW文件转换为JPG文件"""

class ImageGraphicsView(QGraphicsView):
    """图像显示视图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # 隐藏水平和垂直滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def wheelEvent(self, event: QWheelEvent):
        # Zoom in or out
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

class Mipi2RawConverterApp(QMainWindow):
    """MIPI RAW文件转换为JPG文件"""
    # 添加一个信号用于通知主窗口子窗口已关闭
    closed = pyqtSignal()
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MIPI to RAW Converter")

        # self.setGeometry(100, 100, 1200, 900)  # 设置初始化大小为1200x900
        
        # 获取鼠标所在屏幕，并根据当前屏幕计算界面大小与居中位置，调整大小并移动到该位置
        screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        screen_geometry = QtWidgets.QApplication.desktop().screenGeometry(screen)
        width = int(screen_geometry.width() * 0.55)
        height = int(screen_geometry.height() * 0.55)
        self.resize(width, height)
        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        
        icon_path = r"D:\tuning\tools\AE\aebox_v3\icon\icon.ico"
        self.setWindowIcon(QIcon(icon_path))       

        # Main layout
        main_layout = QVBoxLayout()

        # Image display
        self.graphics_view = ImageGraphicsView()
        main_layout.addWidget(self.graphics_view)

        # Controls layout
        controls_layout = QHBoxLayout()

        # Width and Height
        controls_layout.addWidget(QLabel("宽:"))
        self.width_input = QLineEdit()
        self.width_input.setMaximumWidth(80)  # 设置最大宽度
        controls_layout.addWidget(self.width_input)

        controls_layout.addWidget(QLabel("高:"))
        self.height_input = QLineEdit()
        self.height_input.setMaximumWidth(80)  # 设置最大宽度
        controls_layout.addWidget(self.height_input)

        # Bit Depth Radio Buttons
        controls_layout.addWidget(QLabel("bit位:"))
        self.bit_depth_group = QButtonGroup(self)
        bit_depth_layout = QHBoxLayout()
        for bit in ["8", "10", "12", "14", "16"]:
            radio_button = QRadioButton(bit)
            self.bit_depth_group.addButton(radio_button)
            bit_depth_layout.addWidget(radio_button)
        controls_layout.addLayout(bit_depth_layout)

        # Bayer Pattern Radio Buttons
        controls_layout.addWidget(QLabel("Bayer:"))
        self.bayer_group = QButtonGroup(self)
        bayer_layout = QHBoxLayout()
        for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]:
            radio_button = QRadioButton(pattern)
            self.bayer_group.addButton(radio_button)
            bayer_layout.addWidget(radio_button)
        controls_layout.addLayout(bayer_layout)

        # Load, Convert, and Save buttons
        self.load_button = QPushButton("导入raw图")
        self.load_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.load_button.clicked.connect(self.load_mipi_raw_file)
        controls_layout.addWidget(self.load_button)

        self.convert_button = QPushButton("转换")
        self.convert_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.convert_button.clicked.connect(self.convert_image)
        controls_layout.addWidget(self.convert_button)

        self.save_button = QPushButton("保存图片")
        self.save_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.save_button.clicked.connect(self.save_image)
        controls_layout.addWidget(self.save_button)

        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)

        # Set main widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Placeholder for file path
        self.mipi_file_path = None

        # Initialize QSettings
        self.settings = QSettings("YourCompany", "Mipi2RawConverter")

        # Load previous settings from JSON
        self.load_settings()


    def load_settings(self):
        try:    
            # 从/cache/raw_settings.json中加载设置
            cache_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "cache")
            with open(os.path.join(cache_path, "raw_settings.json"), "r") as file:  
                settings = json.load(file)
                self.width_input.setText(settings.get("width", ""))
                self.height_input.setText(settings.get("height", ""))
                bit_depth = settings.get("bit_depth", "8")
                bayer_pattern = settings.get("bayer_pattern", "RGGB")
                for button in self.bit_depth_group.buttons():
                    if button.text() == bit_depth:
                        button.setChecked(True)
                for button in self.bayer_group.buttons():
                    if button.text() == bayer_pattern:
                        button.setChecked(True)
        except FileNotFoundError:
            self.width_input.setText("")
            self.height_input.setText("")
            self.bit_depth_group.buttons()[0].setChecked(True)
            self.bayer_group.buttons()[0].setChecked(True)
        
    def keyPressEvent(self, event):
        """处理键盘按键事件"""
        if event.key() == Qt.Key_Escape:
            self.close()  
            event.accept()

    def closeEvent(self, event):
        settings = {
            "width": self.width_input.text(),
            "height": self.height_input.text(),
            "bit_depth": self.get_checked_button_text(self.bit_depth_group),
            "bayer_pattern": self.get_checked_button_text(self.bayer_group),
        }
        # 保存设置到json文件,/cache/raw_settings.json
        cache_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "cache")
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        with open(os.path.join(cache_path, "raw_settings.json"), "w") as file:
            json.dump(settings, file, indent=4)
        
        # 发射关闭信号（新增），统一在这里发送信号
        self.closed.emit()

        # 接受关闭事件（重要！这会告诉Qt正常关闭窗口）
        event.accept()

    def get_checked_button_text(self, button_group):
        for button in button_group.buttons():
            if button.isChecked():
                return button.text()
        return ""

    def load_mipi_raw_file(self):
        # Open file dialog to select MIPI RAW file
        file_name, _ = QFileDialog.getOpenFileName(self, "Open MIPI RAW File", "", "MIPI RAW Files (*.raw);;All Files (*)")
        if file_name:
            self.mipi_file_path = file_name

    def convert_image(self):
        if not self.mipi_file_path:
            self.show_error_message("Please load a MIPI RAW file first.")
            return

        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.show_error_message("Please enter valid numbers for width and height.")
            return

        try:
            bit_depth = self.get_checked_button_text(self.bit_depth_group)
            bayer_pattern = self.get_checked_button_text(self.bayer_group)
            bayer_order = bayer_order_maps[bayer_pattern]

            convertMipi2Raw(self.mipi_file_path, width, height, int(bit_depth), bayer_order)

            jpg_file_path = self.mipi_file_path[:-4] + '_unpack.jpg'
            self.display_image(jpg_file_path)
        except Exception as e:
            self.show_error_message(f"An error occurred: {str(e)}")

    def display_image(self, image_path):
        # Load image using QImage
        image = QImage(image_path)
        if image.isNull():
            print("Failed to load image:", image_path)
            return

        # Convert QImage to QPixmap
        pixmap = QPixmap.fromImage(image)

        # Create a scene and add the pixmap
        scene = QGraphicsScene()
        scene.addPixmap(pixmap)

        # Set the scene to the graphics view
        self.graphics_view.setScene(scene)

    def show_error_message(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("Error")
        msg_box.exec_()

    def save_image(self):
        if not self.mipi_file_path:
            self.show_error_message("请先加载并转换MIPI RAW文件。")
            return

        jpg_file_path = self.mipi_file_path[:-4] + '_unpack.jpg'
        save_path, _ = QFileDialog.getSaveFileName(self, "保存图片", jpg_file_path, "JPEG Files (*.jpg);;All Files (*)")
        if save_path:
            try:
                # 使用OpenCV读取和保存图像
                image = cv2.imread(jpg_file_path)
                cv2.imwrite(save_path, image)
                QMessageBox.information(self, "保存成功", f"图片已保存到: {save_path}")
            except Exception as e:
                self.show_error_message(f"保存图片时出错: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Mipi2RawConverterApp()
    window.show()
    sys.exit(app.exec_())