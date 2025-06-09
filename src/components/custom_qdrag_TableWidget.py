# -*- coding: utf-8 -*-
from pathlib import Path
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QTableWidget)
from PyQt5.QtCore import (Qt, QTimer, QMimeData, QPoint, QUrl)
from PyQt5.QtGui import (QPixmap, QPainter, QDrag, QColor, QFont)


class DragTableWidget(QTableWidget):
    """重写QTableWidget类, 支持拖拽功能"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_start_position = None
        self.temp_files = set()
        
        # 添加主窗口引用
        self.main_window = parent  
        
        # 设置拖拽相关属性
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setAcceptDrops(False)
        
        # 设置清理临时文件的定时器
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.clean_temp_files)
        self.cleanup_timer.start(600000)

    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window

    def mousePressEvent(self, event):
        """重写鼠标按下事件，支持拖拽功能"""
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                self.drag_start_position = event.pos()
        # 调用父类方法
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """重写鼠标移动事件，支持拖拽功能切换"""
        try:
            # 提前检查是否按下左键，避免不必要的判断
            if not (event.buttons() & Qt.LeftButton):
                return
            # 确保有起始拖拽位置
            if not self.drag_start_position:
                return
              
            # 确保选中了 1 个或多个文件
            if not self.main_window or not self.main_window.RB_QTableWidget0.selectedItems():
                return

            # 计算拖拽距离，避免重复计算
            drag_distance = (event.pos() - self.drag_start_position).manhattanLength()
            # 如果拖拽距离小于最小拖拽距离，则不进行拖拽
            if drag_distance < QApplication.startDragDistance():
                return
            
            # 主函数中定义的拖拽模式切换标志位
            if self.main_window.drag_flag: 
                
                # 收集文件URL
                urls = self.main_window.get_selected_file_path()
                if not urls:
                    print("mouseMoveEvent()--拖拽操作失败: 无法获取文件路径")
                    return 

                # 处理表格拖拽功能
                self.handle_table_drag_function(urls)

            # 关闭拖拽模式后，处理多选功能        
            else:
                # 处理表格多选功能
                self.handle_table_multi_selection(event)

        except Exception as e:
            print(f"UiMain.DragTableWidget.mouseMoveEvent()--处理鼠标移动事件失败: {e}")


    def handle_table_drag_function(self, urls):
        """处理表格拖拽功能"""  
        try:
            # 创建拖拽对象和MIME数据
            drag = QDrag(self)
            mime_data = QMimeData()
            
            # 将文件路径转换为URL
            urls = [QUrl.fromLocalFile(file_path) for file_path in urls]

            # 设置MIME数据 & 拖拽对象
            mime_data.setUrls(urls)
            drag.setMimeData(mime_data)

            # 使用默认的纯色背景预览图
            preview = self.create_preview_image(f"{len(urls)}个")

            # 选择项数量为1时直接获取预览区域的pixmap
            if len(urls) == 1:
                # self.main_window.image_viewer.pixmap_item.pixmap()
                # self.main_window.image_viewer.scene.items()[0].pixmap()

                # 直接获取主界面预览区域的pixmap
                if self.main_window.image_viewer and self.main_window.image_viewer.pixmap_item:
                    _pixmap = self.main_window.image_viewer.pixmap_item.pixmap()
                    preview = _pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # 设置预览图
            drag.setPixmap(preview)
            drag.setHotSpot(QPoint(preview.width()//2, preview.height()//2))
            
            # 执行拖拽操作并清理临时文件
            drag_result = drag.exec_(Qt.CopyAction)
            if drag_result == Qt.IgnoreAction:
                self.clean_temp_files()  # 拖拽失败时清理
            elif drag_result == Qt.CopyAction:
                # 可选：拖拽成功后延迟清理临时文件
                QTimer.singleShot(1000, self.clean_temp_files)
                
        except Exception as e:
            self.clean_temp_files()
            print(f"handle_table_drag_function()--处理表格拖拽功能失败: {e}")

    def handle_table_multi_selection(self, event):
        """处理表格多选功能"""
        try:
            # 处理多选功能
            current_item = self.itemAt(event.pos())
            if not current_item:
                return
            
            start_item = self.itemAt(self.drag_start_position)
            if not start_item:
                return
                
            if event.buttons() & Qt.LeftButton:
                # 获取选择范围
                start_pos = (start_item.row(), start_item.column())
                current_pos = (current_item.row(), current_item.column())
                
                # 计算选择范围
                min_row, max_row = sorted([start_pos[0], current_pos[0]])
                min_col, max_col = sorted([start_pos[1], current_pos[1]])
                
                # 清除当前选择并选择新范围
                self.clearSelection()
                for row in range(min_row, max_row + 1):
                    for col in range(min_col, max_col + 1):
                        if item := self.item(row, col):
                            item.setSelected(True)
        except Exception as e:
            print(f"handle_table_multi_selection()--处理表格多选失败: {e}")
        
        
    def create_preview_image(self, file_extension):
        """创建预览图像"""
        try:
            preview = QPixmap(128, 128)
            preview.fill(Qt.transparent)

            with QPainter(preview) as painter:
                painter.setRenderHint(QPainter.Antialiasing)

                # 使用预定义的颜色和字体
                bg_color = QColor(88, 88, 88, 180)
                text_color = QColor(255, 255, 255)

                # 绘制背景
                painter.setBrush(bg_color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(0, 0, 128, 128, 8, 8)   

                # 设置文本样式
                font = QFont()
                font.setPointSize(12)
                font.setBold(True)
                painter.setFont(font)

                # 绘制文本
                painter.setPen(text_color)
                painter.drawText(preview.rect(), Qt.AlignCenter, f"{file_extension}文件")

            return preview

        except Exception as e:
            print(f"create_preview_image()--创建预览图像失败: {e}")
            return None
        
    def clean_temp_files(self):
        """清理临时文件"""
        for path in self.temp_files.copy():
            if Path(path).exists():
                try:
                    Path(path).unlink()
                    self.temp_files.remove(path)
                except Exception as e:
                    print(f"清理临时文件失败: {e}")

    def __del__(self):
        """析构函数中清理所有临时文件"""
        self.clean_temp_files()
