# -*- encoding: utf-8 -*-
'''
@File         :sub_setting_view.py
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
    2. 添加双击分割器切换导航区显示状态功能 add by diamond_cz@163.com 2025/06/30
    3. 添加具体分区内容，适配看图子界面 add by diamond_cz@163.com 2025/07/11
    

'''
import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QSplitter, QListWidget, QGraphicsView,
                           QGraphicsScene, QToolBar, QPushButton, QAbstractItemView,
                           QMessageBox, QLabel, QTableWidget, QScrollArea,
                           QMenu, QAction, QFrame, QListWidgetItem, QSizePolicy,
                           QComboBox, QCheckBox, QShortcut, QRadioButton, QButtonGroup,
                           QLineEdit,QGridLayout)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QMimeData, QTimer, QRectF, QPropertyAnimation, QObject, QEvent, QPoint
from PyQt5.QtGui import QKeySequence, QDrag, QPainter, QIcon, QMouseEvent, QCursor
from pathlib import Path
import xml.etree.ElementTree as ET



# 设置项目根路径
base_dir = Path(__file__).parent.parent.parent


class CustomSplitter(QSplitter):
    """自定义分割器，支持双击切换导航区显示状态"""
    doubleClicked = pyqtSignal()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """处理双击事件"""
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class DraggableCheckBox(QWidget):
    dragStarted = pyqtSignal(QWidget)
    dragMoved = pyqtSignal(QPoint)
    dragFinished = pyqtSignal(QWidget, QPoint)

    def __init__(self, text, checked=False, parent=None):
        super().__init__(parent)
        self.checkbox = QCheckBox(text)
        self.checkbox.setChecked(checked)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)
        self.setAcceptDrops(True)
        self._drag_start_pos = None
        self._dragging = False
        self.setMouseTracking(True)
        self.checkbox.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.checkbox:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._drag_start_pos = event.pos()
                    self._dragging = False
            elif event.type() == QEvent.MouseMove:
                if self._drag_start_pos is not None:
                    if (event.pos() - self._drag_start_pos).manhattanLength() > 5:
                        # 开始拖拽
                        if not self._dragging:
                            self._dragging = True
                            self.dragStarted.emit(self)
                        self.dragMoved.emit(self.mapToParent(event.pos()))
                        return True  # 阻止QCheckBox处理，防止勾选
            elif event.type() == QEvent.MouseButtonRelease:
                if self._dragging:
                    self.dragFinished.emit(self, self.mapToParent(event.pos()))
                    self._dragging = False
                    self._drag_start_pos = None
                    return True  # 阻止QCheckBox处理
                self._drag_start_pos = None
            elif event.type() == QEvent.Enter:
                self.setCursor(Qt.ArrowCursor)
            elif event.type() == QEvent.Leave:
                self.setCursor(Qt.OpenHandCursor)
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        if self._is_on_checkbox(self.mapFromGlobal(QCursor.pos())):
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_on_checkbox(event.pos()):
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        if self._drag_start_pos is not None and not self._dragging:
            if (event.pos() - self._drag_start_pos).manhattanLength() > 5 and not self._is_on_checkbox(self._drag_start_pos):
                self._dragging = True
                self.dragStarted.emit(self)
        if self._dragging:
            self.dragMoved.emit(self.mapToParent(event.pos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self.dragFinished.emit(self, self.mapToParent(event.pos()))
        self._drag_start_pos = None
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _is_on_checkbox(self, pos):
        return self.checkbox.geometry().contains(pos)

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)

    def isChecked(self):
        return self.checkbox.isChecked()

    def text(self):
        return self.checkbox.text()

class ExifGridWidget(QWidget):
    def __init__(self, exif_field_status, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.widgets = []
        self.placeholder = QWidget()
        self.placeholder.setFixedHeight(32)
        self.placeholder.setStyleSheet("background: #b3d8fd; border: 1px dashed #409eff; min-height: 28px; border-radius: 8px;")
        self.placeholder.hide()  # 初始隐藏
        for key, checked in exif_field_status.items():
            w = DraggableCheckBox(key, checked)
            w.dragStarted.connect(self.on_drag_started)
            w.dragMoved.connect(self.on_drag_moved)
            w.dragFinished.connect(self.on_drag_finished)
            self.main_layout.addWidget(w)
            self.widgets.append(w)
        self.dragging_widget = None
        self.dragging_index = None
        self.setMouseTracking(True)
        self._last_placeholder_index = None
        self._drag_offset = None
        self._dragging = False

    def on_drag_started(self, widget):
        self.dragging_index = self.widgets.index(widget)
        self.dragging_widget = widget
        self._dragging = True
        # 插入占位符并移除原控件
        self.main_layout.insertWidget(self.dragging_index, self.placeholder)
        self.placeholder.show()
        self.main_layout.removeWidget(widget)
        widget.setParent(self)
        widget.raise_()
        widget.show()
        # 计算拖拽偏移
        cursor_pos = QCursor.pos()
        widget_pos = widget.mapToGlobal(widget.rect().topLeft())
        self._drag_offset = cursor_pos - widget_pos
        self._last_placeholder_index = self.dragging_index
        # 拖拽时设置悬浮样式
        widget.setStyleSheet("background: rgba(102,177,255,0.18); border-radius: 8px;")

    def on_drag_moved(self, pos):
        if not self._dragging or not self.dragging_widget:
            return
        # 跟随鼠标移动
        global_pos = self.mapToGlobal(pos)
        widget_pos = self.mapFromGlobal(global_pos - self._drag_offset)
        self.dragging_widget.move(widget_pos)
        self.dragging_widget.raise_()
        
        # 计算插入点
        mouse_y = self.mapFromGlobal(global_pos).y()
        sticky_threshold = 24
        dead_zone = sticky_threshold // 2
        count = self.main_layout.count()
        min_dist = float('inf')
        best_idx = self._last_placeholder_index if self._last_placeholder_index is not None else len(self.widgets)

        # 边界处理：鼠标在控件区域上方，直接插入到最首位
        if mouse_y < 0:
            best_idx = 0
            if best_idx != self._last_placeholder_index:
                if self.main_layout.indexOf(self.placeholder) != -1:
                    self.main_layout.removeWidget(self.placeholder)
                self.main_layout.insertWidget(best_idx, self.placeholder)
                self._last_placeholder_index = best_idx
            return

        if count > 0:
            first_item = self.main_layout.itemAt(0)
            first_widget = first_item.widget()
            if first_widget and first_widget != self.placeholder:
                first_rect = first_widget.geometry()
                first_top = first_widget.mapTo(self, first_rect.topLeft()).y()
                first_bottom = first_widget.mapTo(self, first_rect.bottomLeft()).y()

                # 鼠标在第一个控件top之上，直接插入到0
                if mouse_y < first_top:
                    best_idx = 0
                    if best_idx != self._last_placeholder_index:
                        if self.main_layout.indexOf(self.placeholder) != -1:
                            self.main_layout.removeWidget(self.placeholder)
                        self.main_layout.insertWidget(best_idx, self.placeholder)
                        self._last_placeholder_index = best_idx
                    return
                
                # 鼠标在第一个控件范围内，但需要避免与拖拽控件冲突
                if first_top <= mouse_y < first_bottom:
                    # 如果拖拽的控件原本就在第一个位置，则插入到第二个位置
                    if self.dragging_index == 0:
                        best_idx = 1
                    else:
                        best_idx = 0
                    if best_idx != self._last_placeholder_index:
                        if self.main_layout.indexOf(self.placeholder) != -1:
                            self.main_layout.removeWidget(self.placeholder)
                        self.main_layout.insertWidget(best_idx, self.placeholder)
                        self._last_placeholder_index = best_idx
                    return
                
                # 鼠标在第一个控件bottom~bottom+dead_zone之间，插入到1
                if first_bottom <= mouse_y < first_bottom + dead_zone:
                    best_idx = 1
                    if best_idx != self._last_placeholder_index:
                        if self.main_layout.indexOf(self.placeholder) != -1:
                            self.main_layout.removeWidget(self.placeholder)
                        self.main_layout.insertWidget(best_idx, self.placeholder)
                        self._last_placeholder_index = best_idx
                    return

        # 其余控件正常判断
        for i in range(1, count):
            item = self.main_layout.itemAt(i)
            w = item.widget()
            if w == self.placeholder:
                continue
            center = w.mapTo(self, w.rect().center())
            dist = abs(mouse_y - center.y())
            if dist < min_dist:
                min_dist = dist
                best_idx = i if mouse_y < center.y() else i + 1

        # 边界保护：如果在首位或末位且占位符已在该位置，不再插入
        if (best_idx == count) and best_idx == self._last_placeholder_index:
            return
        
        # 只有当鼠标距离最近控件中心线超过粘滞区，且插入点变化时才移动占位符
        if min_dist > sticky_threshold and best_idx != self._last_placeholder_index:
            if self.main_layout.indexOf(self.placeholder) != -1:
                self.main_layout.removeWidget(self.placeholder)
            if best_idx > self.main_layout.count():
                best_idx = self.main_layout.count()
            self.main_layout.insertWidget(best_idx, self.placeholder)
            self._last_placeholder_index = best_idx

    def on_drag_finished(self, widget, pos):
        if not self._dragging:
            return
        idx = self.main_layout.indexOf(self.placeholder)
        # 彻底移除占位符
        if idx != -1:
            self.main_layout.removeWidget(self.placeholder)
            self.placeholder.hide()
            # 插入到目标位置
            self.main_layout.insertWidget(idx, widget)
            self.widgets.remove(widget)
            self.widgets.insert(idx, widget)
        widget.setParent(self)
        widget.move(0, 0)
        widget.show()
        # 恢复样式
        widget.setStyleSheet("")
        self.dragging_widget = None
        self.dragging_index = None
        self._last_placeholder_index = None
        self._drag_offset = None
        self._dragging = False

    def get_status_dict(self):
        result = {}
        for w in self.widgets:
            result[w.text()] = w.isChecked()
        return result

class setting_Window(QMainWindow):
    closed = pyqtSignal()  # 添加关闭信号
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("设置")
        self.resize(1400, 1000)
        
        # 初始化基础UI
        self.setup_ui()
        
        # 初始化导航和内容区
        self.init_sections()

        # 设置导航区和内容区的风格样式  
        self.set_stylesheet()

        # 设置槽函数和快捷键
        self.set_shortcut()

        # 显示设置界面
        # self.show_setting_ui()

    def setup_ui(self):
        """设置界面基础UI设计"""
        # 左侧导航区整体widget
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6) 
        # 创建导航区列表项,并设置图标尺寸为24x24
        self.nav_list = QListWidget()
        self.nav_list.setIconSize(QSize(24, 24))
        self.nav_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_layout.addWidget(self.nav_list)
        
        # 右侧内容区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.scroll_content)
        
        # 初始化自定义双击功能的分割器组件,并将左侧导航区和右侧内容区都添加到分割器中,禁止导航区和内容区折叠
        self.splitter = CustomSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.nav_widget)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setSizes([150, 850])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)


        # 创建中央主容器
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.splitter)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        

    def init_sections(self):
        """初始化导航分区和内容区"""
        # 定义分区
        self.sections = [
            {"name": "通用设置", "icon": "setting.png"},
            {"name": "颜色设置", "icon": "setting_color.png"},
            {"name": "显示设置", "icon": "setting_display.png"},
            {"name": "EXIF显示", "icon": "setting_h.png"},
            {"name": "色彩空间", "icon": "setting_rgb.png"},
            {"name": "关于", "icon": "setting_about.png"},
            # 可继续添加更多分区
        ]
        # 存储每个分区的标题控件，用于滚动时高亮导航项
        self.section_title_widgets = []
        # 根据自定义分区创建导航项和内容区
        for i, sec in enumerate(self.sections):
            # 左侧导航区添加: 名称+图标
            icon_path = base_dir / "resource" / "icons" / sec["icon"]
            item = QListWidgetItem(QIcon(icon_path.as_posix()), sec["name"])
            item.setData(Qt.UserRole, sec["name"])
            self.nav_list.addItem(item)
            
            # 右侧内容区设置: 分区标题，并设置对象名，便于识别
            title_label = QLabel(f"{sec['name']}")
            title_label.setObjectName(f"section_title_{i}")  
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 28px;    /* 设置字体大小为28像素 */
                    font-weight: bold;  /* 设置字体为粗体 */
                    color: #2a5caa;     /* 设置字体颜色 */
                    padding: 10px;      /* 设置内边距为10像素(文字与边框的距离) */
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DCE6F7, stop:1 #F0F0F4);
                    border-radius: 8px;  /* 圆角半径8像素,让标题有圆角效果 */
                    border-left: 4px solid #2a5caa;  /* 左边框: 4像素宽的蓝色实线 */
                    margin: 0px 5px 5px 0px;         /* 设置外边距:上右下左 */
                }
            """)

            # 右侧内容区添加: 标题组件
            self.content_layout.addWidget(title_label)
            
            # 右侧内容区添加: 具体内容组件,主要实现集中在这一部分;
            self.add_section_content(sec)

            # 右侧内容区添加: 分隔线（最后一个分区不添加横线）
            if i < len(self.sections) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("""
                    QFrame {
                        background: #cccccc;
                        margin: 0px 5px; /* 设置左右间距:左0右5 */
                    }
                """)
                # 添加分隔线到分区layout中
                self.content_layout.addWidget(separator)
            
            # 存储每个分区的标题控件，用于滚动时高亮导航项
            self.section_title_widgets.append(title_label)
        
        # 添加底部弹性空间（保存为实例变量，便于动态调整高度）
        self.bottom_spacer = QWidget()
        self.bottom_spacer.setFixedHeight(0)
        self.content_layout.addWidget(self.bottom_spacer)
        
        # 默认选中第一个分区
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)

    def add_section_content(self, section):
        """添加分区内容"""
        # 创建内容容器
        content_container = QWidget()

        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(10, 0, 10, 0)
        content_layout.setSpacing(0)
        
        # 根据分区名称添加特定内容
        if section["name"] == "通用设置":
            self.add_general_settings_content(content_layout)
        elif section["name"] == "颜色设置":
            self.add_color_settings_content(content_layout)
        elif section["name"] == "显示设置":
            self.add_display_settings_content(content_layout)
        elif section["name"] == "EXIF显示":
            self.add_exif_settings_content(content_layout)
        elif section["name"] == "色彩空间":
            self.add_color_space_settings_content(content_layout)
        else:# 其他分区的默认内容
            self.add_default_settings_content(content_layout, section["name"])
        
        self.content_layout.addWidget(content_container)


    def toggle_screen_display(self):
        """添加屏幕显示的槽函数"""
        if self.normal_radio.isChecked():
            print("切换到常规尺寸")
            if self.main_window and bool(self.main_window.toggle_screen_display):
                self.main_window.is_fullscreen = False      
                self.main_window.is_norscreen = True
                self.main_window.is_maxscreen = False
                self.main_window.toggle_screen_display()
            
        elif self.maxed_radio.isChecked():
            print("切换到最大化显示")
            if self.main_window and bool(self.main_window.toggle_screen_display):
                self.main_window.is_fullscreen = False      
                self.main_window.is_norscreen = False
                self.main_window.is_maxscreen = True
                self.main_window.toggle_screen_display()
        elif self.full_radio.isChecked():
            print("切换到全屏显示")
            if self.main_window and bool(self.main_window.toggle_screen_display):
                self.main_window.is_fullscreen = True   
                self.main_window.is_norscreen = False
                self.main_window.is_maxscreen = False   
                self.main_window.toggle_screen_display()


    def add_general_settings_content(self, layout):
        """添加通用设置内容"""
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)

        # 尺寸设置
        size_group = self.create_setting_group("尺寸设置", "选择看图子界面打开的尺寸")
        self.normal_radio = QRadioButton("常规尺寸显示")
        self.maxed_radio = QRadioButton("最大化显示")
        self.full_radio = QRadioButton("全屏显示")

        ## 创建互斥组
        radio_group = QButtonGroup(settings_container)
        radio_group.addButton(self.normal_radio)
        radio_group.addButton(self.maxed_radio)
        radio_group.addButton(self.full_radio)
        ## 添加到布局
        size_group.layout().addWidget(self.normal_radio)
        size_group.layout().addWidget(self.maxed_radio)
        size_group.layout().addWidget(self.full_radio)
        settings_layout.addWidget(size_group)

        # 设置圆形复选按钮的链接事件
        self.normal_radio.clicked.connect(self.toggle_screen_display)
        self.maxed_radio.clicked.connect(self.toggle_screen_display)
        self.full_radio.clicked.connect(self.toggle_screen_display)

        # 主题设置
        theme_group = self.create_setting_group("主题模式", "跟随系统勾选后，应用将跟随设备的系统设置切换主题模式，可选模式置灰处理")
        ## 跟随系统
        follow_system_checkbox = QCheckBox("跟随系统")
        follow_system_checkbox.setChecked(True)
        follow_system_checkbox.setStyleSheet("QCheckBox { font-size: 15px; margin-bottom: 2px; }")
        theme_group.layout().addWidget(follow_system_checkbox)

        ## 主题卡片区
        card_layout = QHBoxLayout()
        card_layout.setSpacing(24)
        card_layout.setAlignment(Qt.AlignLeft)
        ## 浅色卡片
        light_card = QFrame()
        light_card.setObjectName("light_card")
        light_card.setStyleSheet("""
            QFrame#light_card {
                border: 2px solid #409eff;
                border-radius: 14px;
                background: #fafbfc;
                min-width: 220px;
                max-width: 240px;
                min-height: 120px;
                margin: 0 0 0 0;
            }
        """)
        light_layout = QVBoxLayout(light_card)
        light_layout.setContentsMargins(18, 14, 18, 10)
        light_layout.setSpacing(8)
        # 预览
        light_preview = QLabel()
        light_preview.setFixedHeight(38)
        light_preview.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f5f6fa, stop:1 #e6eaf3); border-radius: 7px; margin-bottom: 2px;")
        light_layout.addWidget(light_preview)
        # 单选按钮
        light_radio = QRadioButton("浅色")
        light_radio.setChecked(True)
        light_radio.setStyleSheet("QRadioButton { font-size: 15px; margin-top: 2px; color: #000; }")
        light_layout.addWidget(light_radio)
        light_layout.setAlignment(light_radio, Qt.AlignLeft)

        # 深色卡片
        dark_card = QFrame()
        dark_card.setObjectName("dark_card")
        dark_card.setStyleSheet("""
            QFrame#dark_card {
                border: 2px solid #e0e0e0;
                border-radius: 14px;
                background: #23272e;
                min-width: 220px;
                max-width: 240px;
                min-height: 120px;
                margin: 0 0 0 0;
            }
        """)
        dark_layout = QVBoxLayout(dark_card)
        dark_layout.setContentsMargins(18, 14, 18, 10)
        dark_layout.setSpacing(8)
        # 预览
        dark_preview = QLabel()
        dark_preview.setFixedHeight(38)
        dark_preview.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #23272e, stop:1 #31343b); border-radius: 7px; margin-bottom: 2px;")
        dark_layout.addWidget(dark_preview)
        # 单选按钮
        dark_radio = QRadioButton("深色")
        dark_radio.setChecked(False)
        dark_radio.setStyleSheet("QRadioButton { font-size: 15px; margin-top: 2px; color: #000; }")
        dark_layout.addWidget(dark_radio)
        dark_layout.setAlignment(dark_radio, Qt.AlignLeft)

        # 单选互斥
        theme_radio_group = QButtonGroup(settings_container)
        theme_radio_group.addButton(light_radio)
        theme_radio_group.addButton(dark_radio)

        # 添加到主题组theme_group中
        card_layout.addWidget(light_card)
        card_layout.addWidget(dark_card)
        theme_group.layout().addLayout(card_layout)

        # 互斥逻辑
        def on_follow_system_changed():
            enabled = not follow_system_checkbox.isChecked()
            light_radio.setEnabled(enabled)
            dark_radio.setEnabled(enabled)
            light_card.setStyleSheet(f"""
                QFrame#light_card {{
                    border: 2px solid {'#e0e0e0' if not enabled else ('#409eff' if light_radio.isChecked() else '#e0e0e0')};
                    border-radius: 14px;
                    background: #fafbfc;
                    min-width: 220px;
                    max-width: 240px;
                    min-height: 120px;
                    margin: 0 0 0 0;
                }}
            """)
            dark_card.setStyleSheet(f"""
                QFrame#dark_card {{
                    border: 2px solid {'#e0e0e0' if not enabled else ('#409eff' if dark_radio.isChecked() else '#e0e0e0')};
                    border-radius: 14px;
                    background: #23272e;
                    min-width: 220px;
                    max-width: 240px;
                    min-height: 120px;
                    margin: 0 0 0 0;
                }}
            """)


        def update_card_styles():
            if light_radio.isChecked():
                light_card.setStyleSheet("""
                    QFrame#light_card {
                        border: 2px solid #409eff;
                        border-radius: 14px;
                        background: #fafbfc;
                        min-width: 220px;
                        max-width: 240px;
                        min-height: 120px;
                        margin: 0 0 0 0;
                    }
                """)
                dark_card.setStyleSheet("""
                    QFrame#dark_card {
                        border: 2px solid #e0e0e0;
                        border-radius: 14px;
                        background: #23272e;
                        min-width: 220px;
                        max-width: 240px;
                        min-height: 120px;
                        margin: 0 0 0 0;
                    }
                """)
            else:
                light_card.setStyleSheet("""
                    QFrame#light_card {
                        border: 2px solid #e0e0e0;
                        border-radius: 14px;
                        background: #fafbfc;
                        min-width: 220px;
                        max-width: 240px;
                        min-height: 120px;
                        margin: 0 0 0 0;
                    }
                """)
                dark_card.setStyleSheet("""
                    QFrame#dark_card {
                        border: 2px solid #409eff;
                        border-radius: 14px;
                        background: #23272e;
                        min-width: 220px;
                        max-width: 240px;
                        min-height: 120px;
                        margin: 0 0 0 0;
                    }
                """)

        # 设置主题模式的槽函数
        if follow_system_checkbox.isChecked:
            on_follow_system_changed()
        follow_system_checkbox.stateChanged.connect(on_follow_system_changed)
        light_radio.toggled.connect(update_card_styles)
        dark_radio.toggled.connect(update_card_styles)


        # 添加各个组件
        settings_layout.addWidget(theme_group)
        layout.addWidget(settings_container)

    def add_color_settings_content(self, layout):
        """添加颜色设置内容（配色盘风格）"""
        
        list_colors = [
            "rgb(127,127,127)",  # 18度灰
            "rgb(22, 24, 35)",  # 乌漆嘛黑
            "rgb(136,173,166)", # 水色
            "rgb(123,207,166)", # 石青
            "rgb(242,12,0)",    # 茶色
            "rgb(242,12,0)",    # 石榴红
            "rgb(240,240,244)", # 铅白
            "rgb(236,237,236)", # 天际
            "rgb(234,243,244)", # 晴空
            "rgb(220,230,247)", # 苍穹
            "rgb(74,116,171)",  # 湖光
            "rgb(84, 99,125)",  # 曜石
            "rgb(8,8,6)",       # 天际黑
            "rgb(45,53,60)",    # 晴空黑
            "rgb(47,51,68)",    # 苍穹黑
            "rgb(49,69,96)",    # 湖光黑
            "rgb(57,63,78)",    # 曜石黑
        ]

        # 配色主容器
        color_frame = QFrame()
        color_frame.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border-radius: 18px;
                padding: 12px 18px 12px 18px;
            }
        """)
        color_layout = QVBoxLayout(color_frame)
        color_layout.setSpacing(10)
        color_layout.setContentsMargins(16, 8, 16, 8)

        # 行生成函数
        def create_color_row(label_text, color_list):
            row = QHBoxLayout()
            row.setSpacing(16)
            # 标签
            label = QLabel(label_text)
            label.setStyleSheet("color: black; font-size: 15px; min-width: 36px;")
            row.addWidget(label)
            # 色块
            btn_group = []
            for color in color_list:
                btn = QPushButton()
                btn.setFixedSize(32, 32)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {color};
                        border-radius: 16px;
                        border: 2px solid transparent;
                    }}
                    QPushButton[selected='true'] {{
                        border: 3px solid #409eff;
                    }}
                """)
                btn.setProperty("selected", False)
                btn.setCursor(Qt.PointingHandCursor)
                btn_group.append(btn)
                row.addWidget(btn)
            row.addStretch(1)
            return btn_group, row

        # 自定义颜色选项行
        background_btns, back_row = create_color_row("背景颜色:", list_colors)
        fill_btns, fill_row = create_color_row("填充颜色:", list_colors)
        font_btns, font_row = create_color_row("字体颜色:", list_colors)
        exif_btns, exif_row = create_color_row("EXIF颜色:", list_colors)

        color_layout.addLayout(back_row)
        color_layout.addLayout(fill_row)
        color_layout.addLayout(font_row)
        color_layout.addLayout(exif_row)

        # 选中逻辑
        def select_color(btns, idx):
            for i, b in enumerate(btns):
                b.setProperty("selected", i == idx)
                b.setStyle(b.style())  # 强制刷新样式
        # 默认选中第一个
        select_color(background_btns, 0)
        select_color(fill_btns, 0)
        select_color(font_btns, 0)
        select_color(exif_btns, 0)
        
        # 点击事件
        for idx, btn in enumerate(background_btns):
            btn.clicked.connect(lambda _, i=idx: select_color(background_btns, i))
        for idx, btn in enumerate(fill_btns):
            btn.clicked.connect(lambda _, i=idx: select_color(fill_btns, i))
        for idx, btn in enumerate(font_btns):
            btn.clicked.connect(lambda _, i=idx: select_color(font_btns, i))
        for idx, btn in enumerate(exif_btns):
            btn.clicked.connect(lambda _, i=idx: select_color(exif_btns, i))

        """添加水平layout存放radio_layout等信息"""
        radio_layout = QHBoxLayout()
        radio_auto = QRadioButton("读取配置")
        radio_custom = QRadioButton("自定义颜色")
        # 设置默认选中读取配置项
        radio_auto.setChecked(True)
        # 添加到layout中
        radio_layout.addWidget(radio_auto)
        radio_layout.addWidget(radio_custom)

        """设置主题配色大框架""" 
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)
        # 设置颜色设置主布局layout
        color_group = self.create_setting_group("", "")
        # 标题和一键重置按钮按钮横向布局
        title_layout = QHBoxLayout()
        title_label = QLabel("颜色设置")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #22262A;")
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        save_button = QPushButton("一键重置")
        save_button.setMinimumSize(120, 50)
        save_button.setMaximumHeight(60)
        save_button.setStyleSheet("""
            QPushButton {
                font-size: 19px; 
                padding: 10px 36px; 
                border-radius: 8px; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #409eff, stop:1 #66b1ff); 
                color: white; 
                font-weight: bold; 
                letter-spacing: 2px; 
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66b1ff, stop:1 #85c1ff); 
                color: white;
            }     
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a8ee6, stop:1 #5a9ee6); 
                color: #e6f3ff;
                padding: 8px 34px;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #66b1ff;
            }                  
        """)

        def on_save():
            print("一键重置：")
            # 你可以emit信号或其它处理

        # 添加组件到主layout中
        title_layout.addWidget(save_button)
        color_group.layout().insertLayout(0, title_layout)
        # radio_layout中设置互斥分组
        radio_group = QButtonGroup(settings_container)
        radio_group.addButton(radio_custom)
        radio_group.addButton(radio_auto)        
        # 添加radio_layout和color_frame到设置组
        color_group.layout().addLayout(radio_layout)
        color_group.layout().addWidget(color_frame)
        
        # 添加槽函数
        save_button.clicked.connect(on_save)
        settings_layout.addWidget(color_group)
        layout.addWidget(settings_container)

    def add_display_settings_content(self, layout):
        """添加显示设置内容"""
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)

        # 显示选项复选框
        display_group = self.create_setting_group("显示设置",
                        "支持可选功能有: 直方图信息、EXIF信息、ROI信息以及AI提示看图功能")
        hisgram_checkbox = QCheckBox("显示直方图信息")
        exif_checkbox = QCheckBox("显示EXIF信息")
        roi_checkbox = QCheckBox("显示ROI信息")
        ai_checkbox = QCheckBox("启用AI提示看图功能")
        ## 默认选中显示ROI信息
        roi_checkbox.setChecked(True)
        display_group.layout().addWidget(hisgram_checkbox)
        display_group.layout().addWidget(exif_checkbox)
        display_group.layout().addWidget(roi_checkbox)
        display_group.layout().addWidget(ai_checkbox)

        # 标题显示开关
        title_group = self.create_setting_group("标题显示开关", "看图子界面的列名称设置，支持自定义和跟随文件夹两种可选")
        title_checkbox = QCheckBox("显示窗口标题")
        title_checkbox.setChecked(True)
        title_group.layout().addWidget(title_checkbox)
        ## 添加两个互斥的圆形单选项
        radio_layout = QHBoxLayout()
        radio_folder = QRadioButton("跟随文件夹")
        radio_custom = QRadioButton("名称文本自定义")
        radio_custom.setChecked(True)
        ## 互斥分组
        radio_group = QButtonGroup(settings_container)
        radio_group.addButton(radio_custom)
        radio_group.addButton(radio_folder)
        radio_layout.addWidget(radio_custom)
        radio_layout.addWidget(radio_folder)
        title_group.layout().addLayout(radio_layout)
        # 互斥逻辑：未勾选显示窗口标题时，单选按钮置灰
        def on_title_checkbox_changed(state):
            enabled = title_checkbox.isChecked()
            radio_custom.setEnabled(enabled)
            radio_folder.setEnabled(enabled)
        title_checkbox.stateChanged.connect(on_title_checkbox_changed)
        # 初始化一次
        on_title_checkbox_changed(title_checkbox.checkState())

        # 添加组件信息到主布局中
        settings_layout.addWidget(display_group)
        settings_layout.addWidget(title_group)
        layout.addWidget(settings_container)

    def add_exif_settings_content(self, layout):
        """添加EXIF显示设置内容，支持两列复选框拖动排序，保存时返回新顺序和勾选状态"""
        exif_field_status = {
            "图片名称": True, "品牌": False, "型号": True, "图片张数": True, "图片大小": True,
            "图片尺寸": True, "曝光时间": True, "光圈值": False, "ISO值": True, "原始时间": False,
            "测光模式": False, "HDR": True, "Zoom": True, "Lux": True, "CCT": True,
            "FaceSA": True, "DRCgain": True, "Awb_sa": False, "Triangle_index": False,
            "R_gain": False, "B_gain": False, "Safe_gain": False, "Short_gain": False, "Long_gain": False
        }

        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)
        exif_group = self.create_setting_group("", "")

        # 标题和保存按钮
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("EXIF信息显示->>支持拖拽调整顺序")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; background: #FFFFFF; color: #22262A;")
        save_button = QPushButton("保存")
        save_button.setMinimumSize(120, 44)
        save_button.setMaximumHeight(48)
        save_button.setStyleSheet("""
            QPushButton {
                font-size: 20px; 
                margin: 0px 0px 0px 0px; /* 设置外边距:上右下左 */
                border-radius: 8px; 
                border: none;
                background: #409eff;  
                color: white; 
                font-weight: bold; 
                letter-spacing: 2px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66b1ff, stop:1 #85c1ff); 
                color: white;
            }     
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a8ee6, stop:1 #5a9ee6); 
                color: #e6f3ff;
                padding: 8px 34px;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #66b1ff;
            }   
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(save_button)
        title_widget.setStyleSheet("""
            background: #ffffff;
            border-radius: 8px;
            padding: 0px 0px 0px 0px;
            border: 1px solid #b3d8fd;
        """)
        exif_group.layout().insertWidget(0, title_widget)

        # 拖拽排序的两列复选框
        exif_grid = ExifGridWidget(exif_field_status)
        exif_group.layout().addWidget(exif_grid)

        def on_save():
            result = exif_grid.get_status_dict()
            print("EXIF新顺序和勾选状态：", result)
            # 你可以emit信号或其它处理

        save_button.clicked.connect(on_save)
        settings_layout.addWidget(exif_group)
        layout.addWidget(settings_container)

    def add_color_space_settings_content(self, layout):
        """添加色彩空间设置内容"""
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)
        # 色彩空间选择
        cm_group = self.create_setting_group(
            "图像色彩空间管理",
            "设置色彩空间管理选项,默认自动读取ICC配置文件,支持可选强制转换色域(Gray、RGB和Display_P3)"
        )

        # 创建互斥的单选按钮
        auto_radio = QRadioButton("AUTO(自动读取ICC配置文件)")
        rgb_radio = QRadioButton("sRGB色域")
        gray_radio = QRadioButton("gray色域")
        p3_radio = QRadioButton("Display_P3色域")

        # 默认选中“自动读取ICC配置文件”
        auto_radio.setChecked(True)

        # 创建互斥组
        button_group = QButtonGroup(settings_container)
        button_group.addButton(auto_radio)
        button_group.addButton(rgb_radio)
        button_group.addButton(gray_radio)
        button_group.addButton(p3_radio)
        

        # 添加到布局
        cm_group.layout().addWidget(auto_radio)
        cm_group.layout().addWidget(rgb_radio)
        cm_group.layout().addWidget(gray_radio)
        cm_group.layout().addWidget(p3_radio)
        settings_layout.addWidget(cm_group)
        layout.addWidget(settings_container)

    def add_default_settings_content(self, layout, section_name):
        """添加默认设置内容"""
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)
        
        # 默认内容
        default_group = self.create_setting_group(f"{section_name}配置", f"{section_name}的详细配置选项")
        default_label = QLabel(f"{section_name}的具体设置选项将在这里显示。\n您可以在这里添加各种配置控件。")
        default_label.setWordWrap(True)
        default_label.setStyleSheet("color: #666; padding: 10px;")
        default_group.layout().addWidget(default_label)
        settings_layout.addWidget(default_group)
        
        layout.addWidget(settings_container)

    def create_setting_group(self, title, description):
        """创建设置组  margin: 0 0 0 0;"""
        # 定义并设置主布局QWidget和layout的样式
        main_group_widget = QWidget()
        main_group_widget.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 15px;
            }
        """) 
        # 添加垂直layout,layout内各个组件的间距设置为5个像素点
        main_group_layout = QVBoxLayout(main_group_widget) 
        main_group_layout.setSpacing(5) 
        # 外边距，参数顺序：左、上、右、下
        main_group_layout.setContentsMargins(10, 10, 10, 10)

        # 标题+描述容器
        title_desc_widget = QWidget()
        title_desc_layout = QVBoxLayout(title_desc_widget)
        title_desc_layout.setSpacing(0)
        title_desc_layout.setContentsMargins(0, 0, 0, 0)
        if title: # 标题
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: #22262A;
                    margin: 0;
                    padding: 4;
                    border: none;
                }
            """)
            title_desc_layout.addWidget(title_label)
        if description: # 描述
            desc_label = QLabel(description)
            desc_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            desc_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #959BA3;
                    margin: 1;
                    border: none; 
                }
            """)
            title_desc_layout.addWidget(desc_label)
        
        # 添加到主layout中
        if title or description:
            main_group_layout.addWidget(title_desc_widget)
        
        return main_group_widget

    def disable_wheel_event(self, widget):
        """禁止控件响应鼠标滚轮事件，只允许内容区滚动"""
        class NoWheelEventFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Wheel:
                    return True
                return False
        if not hasattr(self, '_no_wheel_filter'):
            self._no_wheel_filter = NoWheelEventFilter()
        widget.installEventFilter(self._no_wheel_filter)


    def set_stylesheet(self):
        """设置组件风格样式表"""
        # 设置应用程序图标
        icon_path = base_dir / "resource" / "icons" / "setting_basic.png"
        self.setWindowIcon(QIcon(icon_path.as_posix()))
        
        # 导航区显示状态：True为展开状态（显示图标和文字），False为折叠状态（只显示图标）
        self.nav_expanded = True
        self.nav_expanded_width = 220  # 展开时的宽度
        self.nav_collapsed_width = 60  # 折叠时的宽度
        

        # 分割器的样式设置
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #b3d8fd;  
                width: 6px;
                border-radius: 3px;
            }
            QSplitter::handle:hover {
                background: #6ca0dc;  
            }
        """)

        # 设置左侧导航区的最小宽度为60,确保折叠只显示图标
        self.nav_widget.setMinimumWidth(60)

        # 设置导航区列表的风格样式
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: #F5F6F5;
                border: none;
            }
            QListWidget::item {
                height: 40px;
                padding-left: 16px;
                padding-right: 8px;
                font-weight: normal;
                border: none;
                outline: none;
                margin: 0;
            }
            QListWidget::item:selected {
                background: #E4E6E5;
                color: #2a5caa;
                padding-left: 16px;
                padding-right: 8px;
                font-weight: normal;
                border: none;
                outline: none;
                margin: 0;
            }
            QListWidget::item:hover {
                background: #E4E6E5;
                color: #2a5caa;
                padding-left: 16px;
                padding-right: 8px;
                font-weight: normal;
                border: none;
                outline: none;
                margin: 0;
            }
        """)

        # 内容区的样式设置
        self.scroll_content.setStyleSheet("background: #F0F0F0;")
        self.bottom_spacer.setStyleSheet("background: #F0F0F0;")

        # 通用设置区域的相关初始化
        if self.main_window:
            if hasattr(self.main_window, 'is_maxscreen') and self.main_window.is_maxscreen:
                self.maxed_radio.setChecked(True)
            if hasattr(self.main_window, 'is_norscreen') and self.main_window.is_norscreen:
                self.normal_radio.setChecked(True)
            if hasattr(self.main_window, 'is_fullscreen') and self.main_window.is_fullscreen:
                self.full_radio.setChecked(True)
        else:
            # 设置默认设置项
            self.maxed_radio.setChecked(True)



    def set_shortcut(self):
        """设置界面的槽函数与快捷键连接函数"""
        # 导航区按钮槽函数
        self.nav_list.itemClicked.connect(self.on_nav_item_clicked) 

        # 设置分割器的槽函数，以及右侧内容区的槽函数
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        self.splitter.doubleClicked.connect(self.on_splitter_double_clicked)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll) 

        # 添加ESC键退出快捷键
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.close)

        self.shortcut_esc = QShortcut(QKeySequence('i'), self)
        self.shortcut_esc.activated.connect(self.close)
        

    def show_setting_ui(self):
        """显示设置界面"""
        # 获取主窗口的矩形区域
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        screen_geometry = QApplication.desktop().screenGeometry(screen)
        main_window_rect = (
            self.main_window.geometry() if self.main_window is not None
            else screen_geometry
        )
        x = main_window_rect.x() + (main_window_rect.width() - self.width()) // 2
        y = main_window_rect.y() + (main_window_rect.height() - self.height()) // 2
        w, h = main_window_rect.width(), main_window_rect.height()
        w, h = int(w * 0.55), int(h * 0.60)

        # 设置搜索界面位置和大小
        self.move(x, y)
        self.resize(w, h)
        self.show()


    def on_splitter_double_clicked(self):
        """处理分割器双击事件，切换导航区显示状态"""
        self.toggle_nav_display()
    
    def toggle_nav_display(self):
        """切换导航区显示状态"""
        self.nav_expanded = not self.nav_expanded
        
        if self.nav_expanded:
            # 展开状态：显示图标和文字
            target_width = self.nav_expanded_width
            self.update_nav_text_visibility(True)
        else:
            # 折叠状态：只显示图标
            target_width = self.nav_collapsed_width
            self.update_nav_text_visibility(False)
        
        # 设置分割器大小
        current_sizes = self.splitter.sizes()
        total_width = current_sizes[0] + current_sizes[1]
        self.splitter.setSizes([target_width, total_width - target_width])
    
    def update_nav_text_visibility(self, show_text):
        """更新导航项文字显示状态"""
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            if show_text:
                # 显示文字
                item.setText(self.sections[i]["name"])
            else:
                # 隐藏文字
                item.setText("")

    def on_nav_item_clicked(self, item):
        index = self.nav_list.row(item)
        self.scroll_to_section(index)

    def scroll_to_section(self, index):
        """平滑滚动到指定分区标题正好置顶（适配所有布局嵌套，支持最后一个标题置顶）"""
        if 0 <= index < len(self.section_title_widgets):
            self.is_scrolling = True
            target_widget = self.section_title_widgets[index]
            # 获取标题控件相对于scroll_content的y坐标（适配嵌套布局）
            target_pos = target_widget.mapTo(self.scroll_content, target_widget.rect().topLeft()).y()
            scrollbar = self.scroll_area.verticalScrollBar()
            start_value = scrollbar.value()
            end_value = target_pos

            # 计算内容区高度、视口高度、最后一个标题高度
            content_height = self.scroll_content.sizeHint().height()
            viewport_height = self.scroll_area.viewport().height()
            last_title = self.section_title_widgets[-1]
            last_title_pos = last_title.mapTo(self.scroll_content, last_title.rect().topLeft()).y()
            last_title_height = last_title.height()

            # 只在点击最后一个分区时动态调整底部spacer高度
            if index == len(self.section_title_widgets) - 1:
                need_spacer = viewport_height - (content_height - last_title_pos)
                self.bottom_spacer.setFixedHeight(max(0, need_spacer))
                # 重新计算end_value
                end_value = last_title_pos
            else:
                self.bottom_spacer.setFixedHeight(0)

            # 动画对象挂到self上，防止被回收
            if hasattr(self, '_scroll_anim') and self._scroll_anim:
                self._scroll_anim.stop()
            self._scroll_anim = QPropertyAnimation(scrollbar, b'value', self)
            self._scroll_anim.setDuration(300)  # 动画时长，毫秒
            self._scroll_anim.setStartValue(start_value)
            self._scroll_anim.setEndValue(end_value)
            self._scroll_anim.finished.connect(self.reset_scroll_state)
            self._scroll_anim.start()

    def reset_scroll_state(self):
        """重置滚动状态"""
        self.is_scrolling = False

    def show_section(self, index):
        """兼容旧版本的显示方法，现在调用滚动方法"""
        self.scroll_to_section(index)
    
    def on_splitter_moved(self, pos, index):
        """处理分割器移动事件"""
        if index == 1:  # 只处理导航区和内容区之间的分割器
            nav_width = self.splitter.sizes()[0]
            self.update_nav_view_by_width(nav_width)

    def update_nav_view_by_width(self, width):
        """根据宽度更新导航区显示状态"""
        # 计算阈值（展开宽度和折叠宽度的中间值）
        threshold = (self.nav_expanded_width + self.nav_collapsed_width) // 2
        
        # 根据宽度判断应该显示的状态
        should_expand = width > threshold
        
        # 如果状态需要改变，则更新
        if should_expand != self.nav_expanded:
            self.nav_expanded = should_expand
            self.update_nav_text_visibility(should_expand)


    def on_scroll(self, value):
        """内容区滚动事件处理"""
        scroll_pos = self.scroll_area.verticalScrollBar().value()
        current_section_index = self.find_visible_section(scroll_pos)
        if current_section_index != -1 and current_section_index != self.nav_list.currentRow():
            self.nav_list.setCurrentRow(current_section_index)

    def find_visible_section(self, scroll_pos):
        """根据滚动位置找到当前可见的分区"""
        if not self.section_title_widgets:
            return -1
        
        # 获取滚动区域的高度
        viewport_height = self.scroll_area.viewport().height()
        
        # 计算视口的可见区域
        viewport_top = scroll_pos
        viewport_bottom = scroll_pos + viewport_height
        
        # 遍历所有分区标题，找到当前可见的分区
        visible_sections = []
        
        for i, title_widget in enumerate(self.section_title_widgets):
            # 获取标题控件在滚动内容中的位置
            title_rect = title_widget.geometry()
            title_top = title_rect.y()
            title_bottom = title_rect.y() + title_rect.height()
            
            # 检查标题是否在视口中可见（至少有一部分可见）
            if (title_top < viewport_bottom and title_bottom > viewport_top):
                # 计算可见程度（标题在视口中的可见比例）
                visible_top = max(title_top, viewport_top)
                visible_bottom = min(title_bottom, viewport_bottom)
                visible_ratio = (visible_bottom - visible_top) / title_rect.height()
                
                visible_sections.append((i, visible_ratio, title_top))
        
        if not visible_sections:
            # 如果没有可见的分区，找到最接近视口顶部的分区
            closest_section = 0
            min_distance = float('inf')
            
            for i, title_widget in enumerate(self.section_title_widgets):
                title_rect = title_widget.geometry()
                distance = abs(title_rect.y() - viewport_top)
                if distance < min_distance:
                    min_distance = distance
                    closest_section = i
            
            return closest_section
        
        # 按可见程度排序，返回可见程度最高的分区
        visible_sections.sort(key=lambda x: (-x[1], x[2]))  # 按可见比例降序，然后按位置升序
        return visible_sections[0][0]


    def closeEvent(self, event):
        """重写设置子界面的关闭事件，发送关闭信号"""
        self.closed.emit()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = setting_Window()
    window.show()
    sys.exit(app.exec_()) 