# -*- encoding: utf-8 -*-
'''
@File         :sub_setting_view.py
@Time         :2025/05/30 10:16:24
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :relize setting ui design

使用pathlib获取图片路径notes:
    ICONDIR = Path(__file__).parent.parent.parent
    icon_path = ICONDIR / "setting.png"
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
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QSplitter, QListWidget, QTextBrowser,
                           QGraphicsScene, QToolBar, QPushButton, QAbstractItemView,
                           QMessageBox, QLabel, QTableWidget, QScrollArea,
                           QMenu, QAction, QFrame, QListWidgetItem, QSizePolicy,
                           QComboBox, QCheckBox, QShortcut, QRadioButton, QButtonGroup,
                           QLineEdit,QGridLayout)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QUrl, QTimer, QRectF, QPropertyAnimation, QObject, QEvent, QPoint
from PyQt5.QtGui import QKeySequence, QDrag, QDesktopServices, QIcon, QMouseEvent, QCursor
from pathlib import Path

# 设置项目根路径
BASEPATH = Path(__file__).parent.parent.parent
ICONDIR = BASEPATH / "resource" / "icons" 

# 设置md文件路径
USERPATH = BASEPATH / "resource" / "docs" / "User_Manual.md"
VWESIONPATH = BASEPATH / "resource" / "docs" / "Version_Updates.md"

# 设置图标路径
ICONLABELPATH = Path(BASEPATH, "resource", "icons", "viewer_3.ico").as_posix()

# 设置配置文件路基
BASICSET = BASEPATH / "config" / "basic_settings.json"
EXIFSET = BASEPATH / "config" / "exif_setting.json"

def version_init(VERSION="release-v2.3.2"):
    """从配置文件中读取当前软件版本号"""
    default_version_path = BASEPATH / "config" / "version.ini"
    try:
        # 检查文件是否存在，如果不存在则创建并写入默认版本号
        if not default_version_path.exists():
            # 确保cache目录存在
            default_version_path.parent.mkdir(parents=True, exist_ok=True)
            with open(default_version_path, 'w', encoding='utf-8') as f:
                f.write(VERSION)
            print(f"[version_init]-->找不到文件{default_version_path}，写入版本号{VERSION}")
            return VERSION
        else:
            with open(default_version_path, 'r', encoding='utf-8') as f:
                VERSION = f.read().strip()
                return VERSION
    except Exception as e:
        print(f"[version_init]-->读取版本号失败: {str(e)}\n使用默认版本号{VERSION}")
        return VERSION

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
        
        # 设置窗口标志，确保设置窗口显示在最顶层
        self.setWindowFlags(
            Qt.Window |                   # 独立窗口
            Qt.WindowStaysOnTopHint |     # 保持在最顶层
            Qt.WindowCloseButtonHint |    # 显示关闭按钮
            Qt.WindowMinimizeButtonHint | # 显示最小化按钮
            Qt.WindowMaximizeButtonHint   # 显示最大化按钮
        )
        
        # 初始化基础UI
        self.setup_ui()
        
        # 初始化导航和内容区
        self.init_sections()

        # 设置槽函数和快捷键
        self.set_shortcut()

        # 设置导航区和内容区的风格样式  
        self.set_stylesheet()
        

        # 显示设置界面
        # self.show_setting_ui()

    def setup_ui(self):
        """设置界面基础UI设计"""
        # 创建左侧导航区整体widget
        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6) 
        # 创建左侧导航区列表项,并设置图标尺寸为24x24
        self.nav_list = QListWidget()
        self.nav_list.setIconSize(QSize(24, 24))
        self.nav_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_layout.addWidget(self.nav_list)
        
        # 创建右侧内容区
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
        # 设置列表存储每个分区的标题控件，用于滚动时高亮导航项
        self.section_title_widgets = []
        self.sections = [
            {"name": "通用设置", "icon": "setting.png"},
            {"name": "颜色设置", "icon": "setting_color.png"},
            {"name": "显示设置", "icon": "setting_display.png"},
            {"name": "EXIF显示", "icon": "setting_h.png"},
            {"name": "色彩空间", "icon": "setting_rgb.png"},
            {"name": "关于", "icon": "setting_about.png"},
            # 自定义添加导航分区和内容区，可继续添加更多分区
        ]

        # 根据自定义分区创建导航项和内容区
        for i, sec in enumerate(self.sections):
            # 左侧导航区添加: 名称+图标
            icon_path = ICONDIR / sec["icon"]
            item = QListWidgetItem(QIcon(icon_path.as_posix()), sec["name"])
            item.setData(Qt.UserRole, sec["name"])
            self.nav_list.addItem(item)
            
            """右侧内容区添加: 分区标题; 存储到对应列表中便于滚动高亮显示"""
            title_label = self.set_title_label(sec, i)
            self.content_layout.addWidget(title_label)
            self.section_title_widgets.append(title_label)
            
            """🔺右侧内容区添加: 具体内容组件,主要实现集中在这一部分🔺""" 
            self.add_section_content(sec)

            """右侧内容区添加: 分隔线（最后一个分区不添加横线）"""
            if i < len(self.sections) - 1:
                self.content_layout.addWidget(self.set_title_separator())
            
        # 添加底部弹性空间（保存为实例变量，便于动态调整高度）
        self.bottom_spacer = QWidget()
        self.bottom_spacer.setFixedHeight(0)
        self.content_layout.addWidget(self.bottom_spacer)
        


    def set_title_separator(self):
        """设置分隔横线"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("""
            QFrame {
                background: #cccccc;
                margin: 0px 5px; /* 设置左右间距:左0右5 */
            }
        """)
        return separator

    def set_title_label(self, sec, i):
        """设置内容区的标题"""
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
        return title_label


    def add_section_content(self, section):
        """添加内容区各个分区的具体内容"""
        # 首先，创建内容区容器
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
        elif section["name"] == "关于":
            self.add_about_settings_content(content_layout)
        else:
            self.add_default_settings_content(content_layout, section["name"])
        
        # 添加
        self.content_layout.addWidget(content_container)

    
    """
    内容区设置槽函数
    ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    toggle_screen_display: 通用设置--尺寸设置--相关函数

    toggle_hisgram_info/toggle_exif_info/toggle_roi_info/toggle_ai_info: 显示设置--相关函数

    on_title_checkbox_changed/toggle_radio_title: 显示设置--标题显示开关--相关函数

    toggle_checkbox_exif: EXIF显示--相关函数

    toggle_radio_colorspace: 色彩空间--相关函数
    """
    def toggle_screen_display(self):
        """通用设置-->尺寸设置的槽函数"""
        try:
            if self.normal_radio.isChecked():
                print("[toggle_screen_display]-->切换到常规尺寸")
                self.exif_setting["label_visable_settings"]["is_fullscreen"] = False
                self.exif_setting["label_visable_settings"]["is_norscreen"] = True
                self.exif_setting["label_visable_settings"]["is_maxscreen"] = False
                # 在看图界面打开，直接调用函数切换
                if self.main_window and hasattr(self.main_window,'toggle_screen_display'): 
                    self.main_window.is_fullscreen = False      
                    self.main_window.is_norscreen = True
                    self.main_window.is_maxscreen = False
                    self.main_window.toggle_screen_display()
                # 在主界面打开，写入json文件中
                if (self.main_window and hasattr(self.main_window,'compare_window') 
                and hasattr(self.main_window.compare_window,'is_fullscreen')):
                    self.main_window.compare_window.is_fullscreen = False   
                    self.main_window.compare_window.is_norscreen =  True
                    self.main_window.compare_window.is_maxscreen = False

            elif self.maxed_radio.isChecked():
                print("[toggle_screen_display]-->切换到最大化显示")
                self.exif_setting["label_visable_settings"]["is_fullscreen"] = False
                self.exif_setting["label_visable_settings"]["is_norscreen"] = False
                self.exif_setting["label_visable_settings"]["is_maxscreen"] = True
                # 在看图界面打开，直接调用函数切换
                if self.main_window and hasattr(self.main_window,'toggle_screen_display'):
                    self.main_window.is_fullscreen = False      
                    self.main_window.is_norscreen = False
                    self.main_window.is_maxscreen = True
                    self.main_window.toggle_screen_display()
                # 在主界面打开，写入json文件中
                if (self.main_window and hasattr(self.main_window,'compare_window') 
                and hasattr(self.main_window.compare_window,'is_fullscreen')):
                    self.main_window.compare_window.is_fullscreen = False   
                    self.main_window.compare_window.is_norscreen = False
                    self.main_window.compare_window.is_maxscreen = True   

            elif self.full_radio.isChecked():
                print("[toggle_screen_display]-->切换到全屏显示")
                self.exif_setting["label_visable_settings"]["is_fullscreen"] = True
                self.exif_setting["label_visable_settings"]["is_norscreen"] = False
                self.exif_setting["label_visable_settings"]["is_maxscreen"] = False
                # 在看图界面打开，直接调用函数切换
                if self.main_window and hasattr(self.main_window,'toggle_screen_display'):
                    self.main_window.is_fullscreen = True   
                    self.main_window.is_norscreen = False
                    self.main_window.is_maxscreen = False   
                    self.main_window.toggle_screen_display()
                # 在主界面打开，写入json文件中
                if (self.main_window and hasattr(self.main_window,'compare_window') 
                and hasattr(self.main_window.compare_window,'toggle_screen_display')):
                    self.main_window.compare_window.is_fullscreen = True   
                    self.main_window.compare_window.is_norscreen = False
                    self.main_window.compare_window.is_maxscreen = False   
                    
            # 保存设置
            if EXIFSET.exists():
                with open(EXIFSET, "w", encoding="utf-8") as f:
                    json.dump(self.exif_setting, f, ensure_ascii=False, indent=4)
                print("[toggle_screen_display]-->已写回原json文件!")

        except Exception as e:
            print(f"[toggle_screen_display]-->设置界面-->通用设置—-尺寸设置发生错误: {e}")


    def toggle_player(self):
        """通用设置-->播放器设置的槽函数"""
        if not self.opencv_player.isChecked() and not self.vlc_player.isChecked():
            print("[toggle_player]-->无法切换播放器核心，无效的点击事件!!!")
            return 
        elif self.opencv_player.isChecked():
            print("[toggle_player]-->切换播放器核心为CV")
            if self.basic_settings:
                self.basic_settings["player_key"] = True
        elif self.vlc_player.isChecked():
            print("[toggle_player]-->切换播放器核心为VLC")
            if self.basic_settings:
                self.basic_settings["player_key"] = False
        # 保存设置
        if BASICSET.exists():
            with open(BASICSET, "w", encoding="utf-8") as f:
                json.dump(self.basic_settings, f, ensure_ascii=False, indent=4)
            print("[toggle_player]-->已写回原json文件!")

    # 互斥逻辑
    def on_follow_system_changed(self):
        """通用设置-->主题模式--跟随系统复选框的槽函数"""
        try:
            enabled = not self.follow_system_checkbox.isChecked()
            print("通用设置-主题模式-->跟随系统主题" if not enabled else "通用设置-主题模式-->不跟随系统主题")

            self.light_radio.setEnabled(enabled)
            self.dark_radio.setEnabled(enabled)
            self.light_card.setStyleSheet(f"""
                QFrame#light_card {{
                    border: 2px solid {'#e0e0e0' if not enabled else ('#409eff' if self.light_radio.isChecked() else '#e0e0e0')};
                    border-radius: 14px;
                    background: #fafbfc;
                    min-width: 220px;
                    max-width: 240px;
                    min-height: 120px;
                    margin: 0 0 0 0;
                }}
            """)
            self.dark_card.setStyleSheet(f"""
                QFrame#dark_card {{
                    border: 2px solid {'#e0e0e0' if not enabled else ('#409eff' if self.dark_radio.isChecked() else '#e0e0e0')};
                    border-radius: 14px;
                    background: #23272e;
                    min-width: 220px;
                    max-width: 240px;
                    min-height: 120px;
                    margin: 0 0 0 0;
                }}
            """)
        except Exception as e:
            print(f"[on_follow_system_changed]-->设置界面-->通用设置—-主题模式跟随系统发生错误: {e}")


    def update_card_styles(self):
        """通用设置-->主题模式--深浅色主题选择的槽函数"""
        try:
            qss_dark = f"""
                /* 主窗口样式 */
                QMainWindow {{
                    background-color: black;
                    color: #F0F0F0;
                }}
                QMainWindow QCheckBox{{
                    color: #FFFFFF;
                    background-color: #2D353C;
                    border:none;
                    border-radius:5px;
                    margin: 0 0 0 0; /* 外边距 上右下左 */
                    padding:0 0 0 5; /* 外边距 上右下左 */                  
                }}
                QMainWindow QComboBox{{
                    background-color: #2D353C;
                }}
            """
            qss_light = f"""
                /* 主窗口样式 */
                QMainWindow {{background-color: #F0F0F0;color: black;}}    
            """

            if self.light_radio.isChecked():
                print("通用设置-->主题模式--选择浅色主题")
                self.set_light()   

                if self.main_window:
                    # 主界面打开设置界面
                    if hasattr(self.main_window, 'compare_window') and hasattr(self.main_window, 'current_theme'):
                        self.main_window.current_theme = "默认主题"
                        self.main_window.apply_theme()
                        if (hasattr(self.main_window.compare_window, 'label_0')
                        and hasattr(self.main_window.compare_window, 'statusbar')):
                            self.main_window.compare_window.setStyleSheet(qss_light) 
                            self.main_window.compare_window.statusbar.setStyleSheet(f"background-color: {self.main_window.background_color_default};")
                            self.main_window.compare_window.label_0.setStyleSheet(f"background-color: {self.main_window.background_color_default};")
                    # 看图界面打开设置界面
                    if hasattr(self.main_window, 'toggle_fullscreen'):
                        self.main_window.setStyleSheet(qss_light) 
                        self.main_window.statusbar.setStyleSheet(f"background-color: {self.main_window.background_color_default};")
                        self.main_window.label_0.setStyleSheet(f"background-color: {self.main_window.background_color_default};")
                        if hasattr(self.main_window, 'parent_window') and hasattr(self.main_window.parent_window, 'current_theme'):
                            self.main_window.parent_window.current_theme = "默认主题"
                            self.main_window.parent_window.apply_theme()

            else:
                print("通用设置-->主题模式--选择深色主题")
                self.set_dark()

                # 主界面打开设置界面
                if hasattr(self.main_window, 'compare_window') and hasattr(self.main_window, 'current_theme'):
                    self.main_window.current_theme = "暗黑主题"
                    self.main_window.apply_theme()
                    if (hasattr(self.main_window.compare_window, 'label_0')
                    and hasattr(self.main_window.compare_window, 'statusbar')):
                        self.main_window.compare_window.setStyleSheet(qss_dark) 
                        self.main_window.compare_window.statusbar.setStyleSheet("background-color: #2D353C;")
                        self.main_window.compare_window.label_0.setStyleSheet("background-color: #2D353C;")
                # 看图界面打开设置界面
                if hasattr(self.main_window, 'toggle_fullscreen'):
                    self.main_window.setStyleSheet(qss_light) 
                    self.main_window.statusbar.setStyleSheet("background-color: #2D353C;")
                    self.main_window.label_0.setStyleSheet("background-color: #2D353C;")
                    if hasattr(self.main_window, 'parent_window') and hasattr(self.main_window.parent_window, 'current_theme'):
                        self.main_window.parent_window.current_theme = "暗黑主题"
                        self.main_window.parent_window.apply_theme()
        except Exception as e:
            print(f"[update_card_styles]-->通用设置-->主题模式--深浅色主题选择发生错误: {e}")

    def set_light(self):
        self.light_card.setStyleSheet("""
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
        self.dark_card.setStyleSheet("""
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

    def set_dark(self):
        self.light_card.setStyleSheet("""
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
        self.dark_card.setStyleSheet("""
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



    def reset_colorsetting(self):
        """颜色设置-->一键重置"""
        try:
            print("设置界面->颜色设置-->一键重置")
            if self.main_window and hasattr(self.main_window, "show_menu_combox1"):
                self.main_window.show_menu_combox1(index=1)
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
            and hasattr(self.main_window.compare_window, 'show_menu_combox1')):
                self.main_window.compare_window.show_menu_combox1(index=1)
        except Exception as e:
            print(f"[reset_colorsetting]-->颜色设置-->一键重置时发生错误: {e}")

    def read_colorsetting(self):
        """颜色设置-->读取配置文件"""
        try:
            print("设置界面->颜色设置-->读取配置文件")
            if self.main_window and hasattr(self.main_window, "show_menu_combox1"):
                if self.checkbox_checkbox.isChecked():
                    self.main_window.show_menu_combox1(index=0)
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
            and hasattr(self.main_window.compare_window, 'show_menu_combox1')):
                if self.checkbox_checkbox.isChecked():
                    self.main_window.compare_window.show_menu_combox1(index=0)       
        except Exception as e:
            print(f"[read_colorsetting]-->颜色设置-->读取配置文件时发生错误: {e}")


    def create_color_row(self, label_text, color_list):
        """颜色设置-->行生成函数"""
        try:
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
        except Exception as e:
            print(f"[create_color_row]-->颜色设置-->行生成函数时发生错误: {e}")


    def select_color(self, btns, idx, color_type):
        """颜色设置-->槽函数--选中颜色并打印RGB值
        Args:
            btns: 按钮组列表
            idx: 选中的索引
            color_type: 颜色类型(背景颜色、填充颜色、字体颜色、EXIF颜色)
        """
        try:
            for i, b in enumerate(btns):
                if i == idx:
                    # 更新按钮选中状态并强制刷新样式
                    # print(f"🎨 颜色设置 -> {color_type} -> 选中: {self.color_names[idx]} RGB: {self.list_colors[idx]}")
                    b.setProperty("selected", True)
                    b.setStyle(b.style())  
                    # 更新看图界面上的显示
                    if self.main_window and hasattr(self.main_window, 'update_ui_styles'):
                        if hasattr(self.main_window, 'background_color_default'):
                            if color_type == "背景颜色":
                                self.main_window.background_color_default = self.list_colors[idx]
                            if color_type == "填充颜色":
                                self.main_window.background_color_table = self.list_colors[idx]
                            if color_type == "字体颜色":
                                self.main_window.font_color_default = self.list_colors[idx]
                            if color_type == "EXIF颜色":
                                self.main_window.font_color_exif = self.list_colors[idx]
                        # 更新样式表
                        self.main_window.update_ui_styles()
                    # 更新看图界面上的显示
                    if (self.main_window and hasattr(self.main_window, 'compare_window')
                    and hasattr(self.main_window.compare_window, 'update_ui_styles')):
                        if hasattr(self.main_window.compare_window, 'background_color_default'):
                            if color_type == "背景颜色":
                                self.main_window.compare_window.background_color_default = self.list_colors[idx]
                            if color_type == "填充颜色":
                                self.main_window.compare_window.background_color_table = self.list_colors[idx]
                            if color_type == "字体颜色":
                                self.main_window.compare_window.font_color_default = self.list_colors[idx]
                            if color_type == "EXIF颜色":
                                self.main_window.compare_window.font_color_exif = self.list_colors[idx]
                        # 更新样式表
                        self.main_window.compare_window.update_ui_styles()
                else:
                    b.setProperty("selected", False)
                    b.setStyle(b.style())  
        except Exception as e:
            print(f"[select_color]-->颜色设置-->选中颜色并打印RGB值时发生错误: {e}")

    def color_setting_clicked(self):
        """颜色设置-->点击颜色设置按钮"""
        try:
            # 点击事件槽函数
            for idx, btn in enumerate(self.background_btns):
                btn.clicked.connect(lambda _, i=idx: self.select_color(self.background_btns, i, "背景颜色"))
            for idx, btn in enumerate(self.fill_btns):
                btn.clicked.connect(lambda _, i=idx: self.select_color(self.fill_btns, i, "填充颜色"))
            for idx, btn in enumerate(self.font_btns):
                btn.clicked.connect(lambda _, i=idx: self.select_color(self.font_btns, i, "字体颜色"))
            for idx, btn in enumerate(self.exif_btns):
                btn.clicked.connect(lambda _, i=idx: self.select_color(self.exif_btns, i, "EXIF颜色"))
        except Exception as e:
            print(f"[color_setting_clicked]-->颜色设置-->点击颜色设置按钮时发生错误: {e}")

    def toggle_hisgram_info(self):
        """显示设置-->显示直方图信息的槽函数"""
        try:
            print("设置界面->通用设置->打开->显示直方图信息" if self.hisgram_checkbox.isChecked() else "设置界面->通用设置->关闭->显示直方图信息")
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
                and hasattr(self.main_window.compare_window, 'checkBox_1')):            
                self.main_window.compare_window.checkBox_1.setChecked(self.hisgram_checkbox.isChecked())
        except Exception as e:
            print(f"[toggle_hisgram_info]-->设置界面--显示设置-显示直方图信息时发生错误: {e}")

    def toggle_exif_info(self):
        """显示设置-->显示exif复选框的槽函数"""
        try:
            print("设置界面->通用设置->打开->显示EXIF图信息" if self.exif_checkbox.isChecked() else "设置界面->通用设置->关闭->显示EXIF图信息")
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
                and hasattr(self.main_window.compare_window, 'checkBox_2')):           
                self.main_window.compare_window.checkBox_2.setChecked(self.exif_checkbox.isChecked())
            
        except Exception as e:
            print(f"[toggle_exif_info]-->设置界面--显示设置-显示exif复选框时发生错误: {e}")

    def toggle_roi_info(self):
        """显示设置-->roi复选框的槽函数"""
        try:
            print("设置界面->通用设置->打开->显示ROI信息" if self.roi_checkbox.isChecked() else "设置界面->通用设置->关闭->显示ROI信息")
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
                and hasattr(self.main_window.compare_window, 'checkBox_3')):          
                self.main_window.compare_window.checkBox_3.setChecked(self.roi_checkbox.isChecked())
                
        except Exception as e:
            print(f"[toggle_roi_info]-->设置界面--显示设置-显示ROI信息时发生错误: {e}")

    def toggle_ai_info(self):
        """显示设置-->ai复选框的槽函数"""
        try:
            print("设置界面->通用设置->打开->启用AI提示看图功能" if self.ai_checkbox.isChecked() else "设置界面->通用设置->关闭->启用AI提示看图功能")
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
                and hasattr(self.main_window.compare_window, 'checkBox_4')):           
                self.main_window.compare_window.checkBox_4.setChecked(self.ai_checkbox.isChecked())
                
        except Exception as e:
            print(f"[toggle_ai_info]-->设置界面--显示设置-启用AI提示看图功能时发生错误: {e}")

    def on_title_checkbox_changed(self, state):
        """显示设置-->标题显示开关; 添加互斥逻辑：未勾选显示窗口标题时，单选按钮置灰"""
        try:
            # 互斥逻辑功能
            print("打开--显示看图界面窗口标题" if (enabled := bool(state == Qt.Checked)) else "关闭--显示看图界面窗口标题")
            self.radio_custom.setEnabled(enabled)
            self.radio_folder.setEnabled(enabled)

            # 看图界面显示隐藏标题逻辑
            if (self.main_window and hasattr(self.main_window, 'compare_window') 
                and hasattr(self.main_window.compare_window, 'toggle_title_display')):   
                self.main_window.compare_window.toggle_title_display(enabled)

        except Exception as e:
            print(f"[on_title_checkbox_changed]-->设置界面--点击显示设置相关按钮时发生错误: {e}")

    def toggle_radio_title(self):
        """显示设置-->表头设置; 跟随文件夹、名称文本自定义"""
        try:
            if self.radio_folder.isChecked():
                print("显示看图界面窗口标题，选择跟随文件夹")
            if self.radio_custom.isChecked():
                print("显示看图界面窗口标题，选择名称文本自定义")

        except Exception as e:
            print(f"[toggle_radio_title]-->设置界面--点击显示设置相关按钮时发生错误: {e}")

    def toggle_checkbox_exif(self):
        """EXIF显示-->保存按钮链接函数"""
        print("保存并更新EXIF显示!!!")
        try:
            # 获取设置界面上最新的EXIF显示结果
            result = self.exif_grid.get_status_dict()

            # 同步更新看图界面上的显示
            if self.main_window:
                if (hasattr(self.main_window, 'dict_exif_info_visibility')
                and hasattr(self.main_window, "update_exif_show")):
                    self.main_window.dict_exif_info_visibility = result
                    self.main_window.update_exif_show()

                if (hasattr(self.main_window, 'compare_window') 
                and hasattr(self.main_window.compare_window, 'dict_exif_info_visibility')
                and hasattr(self.main_window.compare_window, 'update_exif_show')):   
                    self.main_window.compare_window.dict_exif_info_visibility = result
                    self.main_window.compare_window.update_exif_show()

        except Exception as e:
            print(f"[toggle_checkbox_exif]-->设置界面--更新EXIF显示时发生错误: {e}")

    def toggle_radio_colorspace(self):
        """色彩空间-->图像色彩空间管理"""
        try:
            if self.auto_radio.isChecked():
                print("图像色彩空间管理, 选择AUTO(自动读取并加载图片ICC配置文件)")
                if self.main_window:
                    if hasattr(self.main_window, "on_comboBox_2_changed"):
                        self.main_window.on_comboBox_2_changed(index=0)  
                        self.main_window.comboBox_2.setCurrentIndex(0)  
                    if (hasattr(self.main_window, 'compare_window') 
                    and hasattr(self.main_window.compare_window, 'on_comboBox_2_changed')):   
                        self.main_window.compare_window.on_comboBox_2_changed(index=0)  
                        self.main_window.compare_window.comboBox_2.setCurrentIndex(0) 

            if self.rgb_radio.isChecked():
                print("图像色彩空间管理, 选择sRGB色域")
                if self.main_window:
                    if hasattr(self.main_window, "on_comboBox_2_changed"):
                        self.main_window.on_comboBox_2_changed(index=1)  
                        self.main_window.comboBox_2.setCurrentIndex(1)  
                    if (hasattr(self.main_window, 'compare_window') 
                    and hasattr(self.main_window.compare_window, 'on_comboBox_2_changed')):   
                        self.main_window.compare_window.on_comboBox_2_changed(index=1)  
                        self.main_window.compare_window.comboBox_2.setCurrentIndex(1) 

            if self.gray_radio.isChecked():
                print("图像色彩空间管理, 选择gray灰度空间")     
                if self.main_window:
                    if hasattr(self.main_window, "on_comboBox_2_changed"):
                        self.main_window.on_comboBox_2_changed(index=2)  
                        self.main_window.comboBox_2.setCurrentIndex(2)  
                    if (hasattr(self.main_window, 'compare_window') 
                    and hasattr(self.main_window.compare_window, 'on_comboBox_2_changed')):   
                        self.main_window.compare_window.on_comboBox_2_changed(index=2)  
                        self.main_window.compare_window.comboBox_2.setCurrentIndex(2) 

            if self.p3_radio.isChecked():
                print("图像色彩空间管理, 选择Display-P3色域")
                if self.main_window:
                    if hasattr(self.main_window, "on_comboBox_2_changed"):
                        self.main_window.on_comboBox_2_changed(index=3)  
                        self.main_window.comboBox_2.setCurrentIndex(3)  
                    if (hasattr(self.main_window, 'compare_window') 
                    and hasattr(self.main_window.compare_window, 'on_comboBox_2_changed')):   
                        self.main_window.compare_window.on_comboBox_2_changed(index=3)  
                        self.main_window.compare_window.comboBox_2.setCurrentIndex(3) 
        except Exception as e:
            print(f"[toggle_radio_colorspace]-->设置界面--选择图像色彩空间时发生错误: {e}")

    """
    内容区设置槽函数
    ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    """
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

        # 尺寸设置
        player_group = self.create_setting_group("播放器设置", "选择视频播放子界面的播放器内核\n1.推荐使用vlc对性能较差电脑友好,需要安装VLC播放器; 2.电脑性能较好使用cv内核无需额外安装播放器")
        self.opencv_player = QRadioButton("CV-播放器内核")
        self.vlc_player = QRadioButton("VLC-播放器内核")
        ## 创建互斥组并添加到布局
        player_radio_group = QButtonGroup(settings_container)
        player_radio_group.addButton(self.opencv_player)
        player_radio_group.addButton(self.vlc_player)
        player_group.layout().addWidget(self.opencv_player)
        player_group.layout().addWidget(self.vlc_player)
        settings_layout.addWidget(player_group)

        # 主题设置
        theme_group = self.create_setting_group("主题模式", "跟随系统勾选后，应用将跟随设备的系统设置切换主题模式，可选模式置灰处理")
        # 跟随系统复选框设置
        self.follow_system_checkbox = QCheckBox("跟随系统")
        self.follow_system_checkbox.setStyleSheet("QCheckBox { font-size: 15px; margin-bottom: 2px; }")
        theme_group.layout().addWidget(self.follow_system_checkbox)
        # 主题卡片区
        card_layout = QHBoxLayout()
        card_layout.setSpacing(24)
        card_layout.setAlignment(Qt.AlignLeft)

        # 浅色卡片
        self.light_card = QFrame()
        self.light_card.setObjectName("light_card")
        self.light_card.setStyleSheet("""
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
        light_layout = QVBoxLayout(self.light_card)
        light_layout.setContentsMargins(18, 14, 18, 10)
        light_layout.setSpacing(8)
        # 预览
        light_preview = QLabel()
        light_preview.setFixedHeight(38)
        light_preview.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f5f6fa, stop:1 #e6eaf3); 
            border-radius: 7px; 
            margin-bottom: 2px;
        """)
        light_layout.addWidget(light_preview)
        # 浅色-->单选圆形按钮
        self.light_radio = QRadioButton("浅色")
        # self.light_radio.setChecked(True)
        self.light_radio.setStyleSheet("""
            QRadioButton { font-size: 15px;
                margin-top: 2px; 
                color: #000; 
            }
        """)
        light_layout.addWidget(self.light_radio)
        light_layout.setAlignment(self.light_radio, Qt.AlignLeft)


        # 深色卡片
        self.dark_card = QFrame()
        self.dark_card.setObjectName("dark_card")
        self.dark_card.setStyleSheet("""
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
        dark_layout = QVBoxLayout(self.dark_card)
        dark_layout.setContentsMargins(18, 14, 18, 10)
        dark_layout.setSpacing(8)
        # 预览
        dark_preview = QLabel()
        dark_preview.setFixedHeight(38)
        dark_preview.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #23272e, stop:1 #31343b); 
            border-radius: 7px;
            margin-bottom: 2px;
        """)
        dark_layout.addWidget(dark_preview)
        # 深色-->单选圆形按钮
        self.dark_radio = QRadioButton("深色")
        self.dark_radio.setStyleSheet("""
            QRadioButton { 
                font-size: 15px;
                margin-top: 2px;
                color: #000; 
            }
        """)
        dark_layout.addWidget(self.dark_radio)
        dark_layout.setAlignment(self.dark_radio, Qt.AlignLeft)

        # 单选互斥
        theme_radio_group = QButtonGroup(settings_container)
        theme_radio_group.addButton(self.light_radio)
        theme_radio_group.addButton(self.dark_radio)
        # 添加各个组件
        card_layout.addWidget(self.light_card)
        card_layout.addWidget(self.dark_card)
        theme_group.layout().addLayout(card_layout)    
        settings_layout.addWidget(theme_group)
        layout.addWidget(settings_container)

    def add_color_settings_content(self, layout):
        """添加颜色设置内容（配色盘风格）"""
        # 颜色列表
        self.list_colors = [
            "rgb(127,127,127)", # 18度灰
            "rgb(0,0,0)",       # 乌漆嘛黑
            "rgb(173,216,230)", # 好蓝
            "rgb(123,207,166)", # 石青
            "rgb(242,12,0)",    # 茶色
            "rgb(242,12,0)",    # 石榴红
            "rgb(255,255,255)", # 纯白
            "rgb(236,237,236)", # 天际
            "rgb(234,243,244)", # 晴空
            "rgb(220,230,247)", # 苍穹
            "rgb(74,116,171)",  # 湖光
            "rgb(84,99,125)",  # 曜石
            "rgb(8,8,6)",       # 天际黑
            "rgb(45,53,60)",    # 晴空黑
            "rgb(47,51,68)",    # 苍穹黑
            "rgb(49,69,96)",    # 湖光黑
            "rgb(57,63,78)",    # 曜石黑
        ]
        # 颜色名称映射
        self.color_names = [
            "18度灰", "乌漆嘛黑", "好蓝", "石青", "茶色", "石榴红", "纯白", "天际", 
            "晴空", "苍穹", "湖光", "曜石", "天际黑", "晴空黑", "苍穹黑", "湖光黑", "曜石黑"
        ]

        
        # 配色主容器初始化
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

        # 自定义颜色选项行
        self.background_btns, back_row_layout = self.create_color_row("背景颜色:", self.list_colors)
        self.fill_btns, fill_row_layout = self.create_color_row("填充颜色:", self.list_colors)
        self.font_btns, font_row_layout = self.create_color_row("字体颜色:", self.list_colors)
        self.exif_btns, exif_row_layout = self.create_color_row("EXIF颜色:", self.list_colors)

        color_layout.addLayout(back_row_layout)
        color_layout.addLayout(fill_row_layout)
        color_layout.addLayout(font_row_layout)
        color_layout.addLayout(exif_row_layout)

        # 默认选中第一个
        # self.select_color(self.background_btns, 0, "背景颜色")
        # self.select_color(self.fill_btns, 0, "填充颜色")
        # self.select_color(self.font_btns, 0, "字体颜色")
        # self.select_color(self.exif_btns, 0, "EXIF颜色")
        

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
        self.save_button_colorsetting = QPushButton("一键重置")
        self.save_button_colorsetting.setMinimumSize(120, 50)
        self.save_button_colorsetting.setMaximumHeight(60)
        self.save_button_colorsetting.setStyleSheet("""
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

        self.checkbox_checkbox = QCheckBox("读取配置文件")

        # 添加组件到主layout中
        title_layout.addWidget(self.save_button_colorsetting)
        color_group.layout().insertLayout(0, title_layout)
        color_group.layout().addWidget(self.checkbox_checkbox)
        color_group.layout().addWidget(color_frame)
        

        settings_layout.addWidget(color_group)
        layout.addWidget(settings_container)

    def add_display_settings_content(self, layout):
        """添加显示设置内容"""
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)

        """显示设置的复选框相关设置"""
        display_group = self.create_setting_group("显示设置",
                        "支持可选功能有: 直方图信息、EXIF信息、ROI信息以及AI提示看图功能")
        self.hisgram_checkbox = QCheckBox("显示直方图信息")
        self.exif_checkbox = QCheckBox("显示EXIF信息")
        self.roi_checkbox = QCheckBox("显示ROI信息")
        self.ai_checkbox = QCheckBox("启用AI提示看图功能")
        display_group.layout().addWidget(self.hisgram_checkbox)
        display_group.layout().addWidget(self.exif_checkbox)
        display_group.layout().addWidget(self.roi_checkbox)
        display_group.layout().addWidget(self.ai_checkbox)


        """标题显示开关的相关设置"""
        title_group = self.create_setting_group("标题显示开关", "看图子界面的列名称设置，支持自定义和跟随文件夹两种可选")
        self.title_checkbox = QCheckBox("显示看图界面窗口标题")
        title_group.layout().addWidget(self.title_checkbox)
        ## 添加两个互斥的圆形单选项
        radio_layout = QHBoxLayout()
        self.radio_folder = QRadioButton("跟随文件夹")
        self.radio_custom = QRadioButton("名称文本自定义")
        ## 设置互斥分组
        radio_group = QButtonGroup(settings_container)
        radio_group.addButton(self.radio_folder)
        radio_group.addButton(self.radio_custom)
        radio_layout.addWidget(self.radio_folder)
        radio_layout.addWidget(self.radio_custom)
        title_group.layout().addLayout(radio_layout)

        # 添加组件信息到主布局中
        settings_layout.addWidget(display_group)
        settings_layout.addWidget(title_group)
        layout.addWidget(settings_container)

    def set_exif_setting_ui(self):
        """exif显示设置界面UI"""
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

        return title_widget, save_button

    def add_exif_settings_content(self, layout):
        """添加EXIF显示设置内容，支持两列复选框拖动排序，保存时返回新顺序和勾选状态"""
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)
        exif_group = self.create_setting_group("", "")

        # 初始化exif基础信息
        exif_field_status = {
            "图片名称": True, "品牌": False, "型号": True, "图片张数": True, "图片大小": True,
            "图片尺寸": True, "曝光时间": True, "光圈值": False, "ISO值": True, "原始时间": False,
            "测光模式": False, "HDR": True, "Zoom": True, "Lux": True, "CCT": True,
            "FaceSA": True, "DRCgain": True, "Awb_sa": False, "Triangle_index": False,
            "R_gain": False, "B_gain": False, "Safe_gain": False, "Short_gain": False, "Long_gain": False
        }
        if self.main_window and hasattr(self.main_window, 'dict_exif_info_visibility'):
            exif_field_status = self.main_window.dict_exif_info_visibility

        # 设置EXIF显示主要UI
        title_widget, save_button = self.set_exif_setting_ui()
        self.save_button = save_button

        # 设置自定义类，支持拖拽调整复选框顺序
        self.exif_grid = ExifGridWidget(exif_field_status)

        exif_group.layout().insertWidget(0, title_widget)
        exif_group.layout().addWidget(self.exif_grid)
        settings_layout.addWidget(exif_group)
        layout.addWidget(settings_container)

    def add_color_space_settings_content(self, layout):
        """添加色彩空间设置内容"""
        # 主内容layout
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(15)
        cm_group = self.create_setting_group(
            "图像色彩空间管理",
            "设置色彩空间管理选项,默认自动读取ICC配置文件,支持可选强制转换色域(Gray、RGB和Display_P3)"
        )

        # 创建互斥的单选按钮
        self.auto_radio = QRadioButton("AUTO(自动读取ICC配置文件)")
        self.rgb_radio = QRadioButton("sRGB色域")
        self.gray_radio = QRadioButton("gray色域")
        self.p3_radio = QRadioButton("Display_P3色域")

        # 创建互斥组
        button_group = QButtonGroup(settings_container)
        button_group.addButton(self.auto_radio)
        button_group.addButton(self.rgb_radio)
        button_group.addButton(self.gray_radio)
        button_group.addButton(self.p3_radio)
        
        # 添加到布局
        cm_group.layout().addWidget(self.auto_radio)
        cm_group.layout().addWidget(self.rgb_radio)
        cm_group.layout().addWidget(self.gray_radio)
        cm_group.layout().addWidget(self.p3_radio)
        settings_layout.addWidget(cm_group)
        layout.addWidget(settings_container)

    def add_about_settings_content(self, layout):
        # 设置使用说明markdown文件，备用文件
        self.User_Manual_Mdpath = USERPATH.as_posix() if USERPATH.exists() else ""
        # 设置版本更新markdown文件
        self.Version_Update_Mdpath = VWESIONPATH.as_posix() if VWESIONPATH.exists() else ""
        # 设置默认版本号，并从version.ini配置文件中读取当前最新的版本号
        self.VERSION = version_init()

        # 初始化UI
        main_layout = QVBoxLayout()
        # 创建一个垂直布局，用于放置图标和版本号
        self.icon_layout = QVBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setPixmap(QIcon(ICONLABELPATH).pixmap(108, 108))
        self.icon_layout.addWidget(self.icon_label)
        self.icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(self.icon_layout)

        # 创建一个水平布局，用于放置标题和版本号
        self.title_layout = QHBoxLayout()
        self.title_label = QLabel(f"HiViewer({self.VERSION})")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.title_label)
        main_layout.addLayout(self.title_layout)

        # 基础描述信息 and 作者描述信息
        self.basic_description_label = QLabel("HiViewer 看图工具，可支持多图片对比查看、多视频同步播放\n并集成有AI提示看图、批量重命名文件、压缩复制文件、局域网传输文件以及存储常见ADB脚本并一键运行等多种实用功能...")
        self.basic_description_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.basic_description_label)

        # 添加一个水平布局，用于放置作者描述信息按钮
        self.button_layout = QHBoxLayout()
        self.auther_1_button = QPushButton("diamond_cz@163.com")
        self.auther_2_button = QPushButton("barrymchen@gmail.com")
        self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.auther_1_button)
        self.button_layout.addWidget(self.auther_2_button)
        self.button_layout.addStretch(1)
        main_layout.addLayout(self.button_layout)
        
        # 设置四个功能按钮
        self.button_layout = QHBoxLayout()
        self.user_manual_button = QPushButton("使用说明")
        self.change_log_button = QPushButton("更新日志")
        self.button_layout.addWidget(self.user_manual_button)
        self.button_layout.addWidget(self.change_log_button)
        main_layout.addLayout(self.button_layout)

        # 设置QTextBrowser组件，支持导入markdown文件显示
        self.browser_layout = QVBoxLayout()
        self.changelog_browser = QTextBrowser()
        self.changelog_content = self.read_changelog(self.User_Manual_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)
        self.changelog_browser.setMinimumHeight(6000)
        self.browser_layout.addWidget(self.changelog_browser)

        # 添加到整体布局中
        main_layout.addLayout(self.browser_layout)
        layout.addLayout(main_layout)
    

    def ui_init(self):
        """UI界面初始化"""

        """UI界面,整体是一个垂直layout"""
        main_layout = QVBoxLayout()
        
        # 创建一个垂直布局，用于放置图标和版本号
        self.icon_layout = QVBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setPixmap(QIcon(ICONLABELPATH).pixmap(108, 108))
        self.icon_layout.addWidget(self.icon_label)
        self.icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(self.icon_layout)

        # 创建一个水平布局，用于放置标题和版本号
        self.title_layout = QHBoxLayout()
        self.title_label = QLabel(f"HiViewer({self.VERSION})")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.title_label)
        main_layout.addLayout(self.title_layout)

        # 基础描述信息 and 作者描述信息
        self.basic_description_label = QLabel("HiViewer 看图工具，可支持多图片对比查看、多视频同步播放\n并集成有AI提示看图、批量重命名文件、压缩复制文件、局域网传输文件以及存储常见ADB脚本并一键运行等多种实用功能...")
        self.basic_description_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.basic_description_label)

        # 添加一个水平布局，用于放置作者描述信息按钮
        self.button_layout = QHBoxLayout()
        self.auther_1_button = QPushButton("diamond_cz@163.com")
        self.auther_2_button = QPushButton("barrymchen@gmail.com")
        self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.auther_1_button)
        self.button_layout.addWidget(self.auther_2_button)
        self.button_layout.addStretch(1)
        main_layout.addLayout(self.button_layout)
        
        # 设置四个功能按钮
        self.button_layout = QHBoxLayout()
        self.user_manual_button = QPushButton("使用说明")
        self.change_log_button = QPushButton("更新日志")
        self.button_layout.addWidget(self.user_manual_button)
        self.button_layout.addWidget(self.change_log_button)
        main_layout.addLayout(self.button_layout)

        # 设置QTextBrowser组件，支持导入markdown文件显示
        self.changelog_browser = QTextBrowser()
        self.changelog_content = self.read_changelog(self.User_Manual_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)
        self.changelog_browser.setMinimumHeight(1000)
        main_layout.addWidget(self.changelog_browser)

        # 返回主布局
        return main_layout
    

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
        """
        设置界面-->应用程序图标
        -----------------------------------------------------------------------------------------------------------
        """
        icon_path = ICONDIR / "setting_basic.png"
        self.setWindowIcon(QIcon(icon_path.as_posix()))
        
        """
        设置界面-->左侧导航区样式设计
        -----------------------------------------------------------------------------------------------------------
        """
        # 导航区显示状态：True为展开状态（显示图标和文字），False为折叠状态（只显示图标）
        self.nav_expanded = True
        self.nav_expanded_width = 220  # 展开时的宽度
        self.nav_collapsed_width = 60  # 折叠时的宽度
        
        # 设置左侧导航区的最小宽度为60,确保折叠只显示图标
        self.nav_widget.setMinimumWidth(60)

        # 导航区默认选中第一个分区
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)

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

        """
        设置界面-->分割器的样式设置
        -----------------------------------------------------------------------------------------------------------
        """
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
        """
        设置界面-->右侧内容区的样式设置
        -----------------------------------------------------------------------------------------------------------
        """
        self.scroll_content.setStyleSheet("background: #F0F0F0;")
        self.bottom_spacer.setStyleSheet("background: #F0F0F0;")
        """
        设置界面-->右侧内容区--关于页--的样式设置
        -----------------------------------------------------------------------------------------------------------
        """



        """内容取组件初始化"""
        # 设置界面相关按钮复选框初始化
        self.basic_settings = []
        if BASICSET.exists():
            with open(BASICSET, "r", encoding='utf-8', errors='ignore') as f:
                self.basic_settings = json.load(f)

                # 初始化播放器设置
                player = self.basic_settings.get("player_key", True)
                self.opencv_player.setChecked(True) if player else self.vlc_player.setChecked(True)
        # 初始化exif相关标签信息
        self.exif_setting = []
        if EXIFSET.exists():
            with open(EXIFSET, "r", encoding='utf-8', errors='ignore') as f:
                self.exif_setting = json.load(f)
                label_setting = self.exif_setting.get("label_visable_settings",{})

                # 初始化--尺寸设置
                self.full_radio.setChecked(True) if label_setting.get("is_fullscreen", False) else ...
                self.normal_radio.setChecked(True) if label_setting.get("is_norscreen", False) else ...
                self.maxed_radio.setChecked(True) if label_setting.get("is_maxscreen", False) else ...

                # 初始化--显示设置
                self.hisgram_checkbox.setChecked(label_setting.get("histogram_info", False))
                self.exif_checkbox.setChecked(label_setting.get("exif_info", False))
                self.roi_checkbox.setChecked(label_setting.get("roi_info", False))
                self.ai_checkbox.setChecked(label_setting.get("ai_tips", False))

                # 初始化--标题开关显示
                self.radio_folder.setChecked(True)
                self.radio_custom.setChecked(False)
                self.title_checkbox.setChecked(label_setting.get("is_title_on", False))


                # 初始化--色彩空间
                self.auto_radio.setChecked(True) if label_setting.get("auto_color_space", False) else ...
                self.rgb_radio.setChecked(True) if label_setting.get("srgb_color_space", False) else ...
                self.p3_radio.setChecked(True) if label_setting.get("p3_color_space", False) else ...
                self.gray_radio.setChecked(True) if label_setting.get("gray_color_space", False) else ...


        # 主题模式初始化
        self.follow_system_checkbox.setChecked(True)
        # self.light_radio.clicked.setChecked(True)
        # self.dark_radio.clicked.setChecked(True)


        # 显示设置区域
        self.roi_checkbox.setChecked(True)

        # EXIF显示


        # 色彩空间区域
        self.auto_radio.setChecked(True)




    def set_shortcut(self):
        """设置界面的槽函数与快捷键连接函数"""
        # 导航区按钮槽函数
        self.nav_list.itemClicked.connect(self.on_nav_item_clicked) 

        # 设置分割器的槽函数，以及右侧内容区的槽函数
        self.splitter.splitterMoved.connect(self.on_splitter_moved)
        self.splitter.doubleClicked.connect(self.on_splitter_double_clicked)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll) 

        """内容区组件的槽函数"""
        # 通用设置区域；设置圆形选择按钮的链接事件
        self.opencv_player.clicked.connect(self.toggle_player)
        self.vlc_player.clicked.connect(self.toggle_player)
        self.normal_radio.clicked.connect(self.toggle_screen_display)
        self.maxed_radio.clicked.connect(self.toggle_screen_display)
        self.full_radio.clicked.connect(self.toggle_screen_display)
        # 通用设置区域；主题模式的槽函数
        self.follow_system_checkbox.stateChanged.connect(self.on_follow_system_changed)
        self.light_radio.clicked.connect(self.update_card_styles)
        self.dark_radio.clicked.connect(self.update_card_styles)

        # 颜色设置区域；一键重置按钮链接事件
        self.save_button_colorsetting.clicked.connect(self.reset_colorsetting)
        self.checkbox_checkbox.clicked.connect(self.read_colorsetting)
        self.color_setting_clicked()

        # 显示设置区域；设置方形复选框的链接事件
        self.hisgram_checkbox.stateChanged.connect(self.toggle_hisgram_info)
        self.exif_checkbox.stateChanged.connect(self.toggle_exif_info)
        self.roi_checkbox.stateChanged.connect(self.toggle_roi_info)
        self.ai_checkbox.stateChanged.connect(self.toggle_ai_info)

        # 显示设置区域；
        # checbox: 显示窗口标题;radiobutton: 跟随文件夹,名称文本自定义
        self.title_checkbox.stateChanged.connect(self.on_title_checkbox_changed)
        self.radio_folder.clicked.connect(self.toggle_radio_title)
        self.radio_custom.clicked.connect(self.toggle_radio_title)

        # EXIF显示区域
        self.save_button.clicked.connect(self.toggle_checkbox_exif)
        
        # 色彩空间区域
        self.auto_radio.clicked.connect(self.toggle_radio_colorspace)
        self.rgb_radio.clicked.connect(self.toggle_radio_colorspace)
        self.p3_radio.clicked.connect(self.toggle_radio_colorspace)
        self.gray_radio.clicked.connect(self.toggle_radio_colorspace)

        # 关于区域；作者信息按钮槽函数，按钮槽函数
        self.auther_1_button.clicked.connect(self.open_auther1_url)
        self.auther_2_button.clicked.connect(self.open_auther2_url)
        self.user_manual_button.clicked.connect(self.open_homepage_url)
        self.change_log_button.clicked.connect(self.open_faq_url)
        


        """全局快键键设置"""
        # 添加ESC键退出快捷键
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.close)

        # 添加i键退出快捷键
        # self.shortcut_esc = QShortcut(QKeySequence('i'), self)
        # self.shortcut_esc.activated.connect(self.close)
        

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

        w = 1400 if w < 1400 else w
        h = 900 if h < 900 else h

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


    def read_changelog(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "# 更新日志\n无法找到更新日志文件。"

    def open_homepage_url(self):
        """打开使用说明md文件"""
        self.changelog_browser.clear()  # 清空内容
        self.changelog_content = self.read_changelog(self.User_Manual_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)

    def open_faq_url(self):
        """打开版本更新md文件"""
        self.changelog_browser.clear()  # 清空内容
        self.changelog_content = self.read_changelog(self.Version_Update_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)

    def open_auther1_url(self): 
        QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz"))

    def open_auther2_url(self):
        QDesktopServices.openUrl(QUrl("https://github.com/965962591"))

    
    def closeEvent(self, event):
        """重写设置子界面的关闭事件，发送关闭信号"""
        self.closed.emit()
        event.accept()

    

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = setting_Window()
    window.show()
    sys.exit(app.exec_()) 
