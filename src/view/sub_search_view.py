# -*- encoding: utf-8 -*-
'''
@File         :sub_search_view.py
@Time         :2025/06/13 18:14:23
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :
'''


"""
1、支持在多维列表中进行模糊搜索
2、按下ctrl+f可以弹出一个搜索界面，输入后搜索框下面显示模糊匹配的项
3、支持模糊搜索，支持大小写，支持中文
4、支持按esc键关闭搜索界面
5、点击搜索到的项，可以返回该项在多维列表中的位置
"""
from PyQt5.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QShortcut, QMainWindow, QWidget, QApplication, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QPalette, QColor
import sys


class SearchOverlay(QMainWindow):
    # 修改信号，当项从搜索结果中被选中时发出，传递项的位置
    item_selected_from_search = pyqtSignal(tuple)
    def __init__(self, main_window, data_list):
        super().__init__()
        self.main_window = main_window
        self.data_list = data_list  # 保存多维列表数据
        
        # 初始化ui
        self.init_ui()


        # 连接信号和槽
        self.search_input.textChanged.connect(self.update_search_results)
        self.search_results_list.itemClicked.connect(self.select_item_from_search)
        
        # 添加Esc键快捷键
        self.shortcut_escape = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_escape.activated.connect(self.hide_search_overlay)

        # 设置窗口属性
        self.old_pos = None
        # self.resize(800, 400)

        # 显示窗口
        # self.show()

    def init_ui(self):
        """
        该函数主要是初始化ui.

        """
        # 创建中心部件和布局
        container_widget = QWidget()
        self.setCentralWidget(container_widget)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主布局
        main_layout = QVBoxLayout(container_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(2)

        # 创建QFrame作为容器，它包含搜索框和结果列表的主布局
        self.frame = QFrame()
        self.search_layout = QVBoxLayout(self.frame)
        self.search_layout.setContentsMargins(10, 10, 10, 10)
        self.search_layout.setSpacing(2)
        
        # 创建搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("在此处键入以搜索...")
        self.search_layout.addWidget(self.search_input)
        
        # 创建搜索结果列表
        self.search_results_list = QListWidget()
        self.search_layout.addWidget(self.search_results_list)

        """设置搜索框和结果列表的样式
        rgba(255, 255, 255, 0.85):
        调整透明度,0.85表示 85% 的不透明度, 0.0表示完全透明, 1.0表示完全不透明
        """
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(187,187,187, 0.55);
                border-radius: 5px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(240, 240, 240, 0.9);
                color: #333333;
                border: 1px solid rgba(78, 78, 78, 0.3);
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(78, 78, 78, 0.5);
            }
        """)
        self.search_results_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(240, 240, 240, 0.9);
                color: #333333;
                border: 1px solid rgba(187, 187, 187, 0.3);
                border-radius: 3px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }
            QListWidget::item:selected {
                background-color: rgba(187, 187, 187, 0.2);
                color: #000000;
            }
            QListWidget::item:hover {
                background-color: rgba(173,216,230, 0.5);
            }
        """)
        
        if self.main_window is not None and self.main_window.custom_font_jetbrains_medium:
            #设置字体
            self.search_input.setFont(self.main_window.custom_font_jetbrains_medium)
            self.search_results_list.setFont(self.main_window.custom_font_jetbrains_medium)

        # 将frame添加到主布局
        main_layout.addWidget(self.frame)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos is not None:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None
            
    def toggle_search_overlay(self):
        if self.isHidden():
            self.show_search_overlay()
        else:
            self.hide_search_overlay()
            
    def show_search_overlay(self):
        """显示搜索框和结果列表"""
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
        w, h = int(w * 0.40), int(h * 0.40)

        # 设置搜索界面位置和大小
        self.move(x, y)
        self.resize(w, h)
        self.show()
        self.search_input.setFocus()
        self.update_search_results(self.search_input.text())
        
    def hide_search_overlay(self):
        self.close()
        
    def update_search_results(self, query):
        """根据搜索查询更新结果列表"""
        self.search_results_list.clear()
        # 如果查询为空，显示所有项
        if not query:
            self._add_all_items_to_list()
            return
            
        # 执行模糊搜索
        self._search_items(query.lower())
        
    def _add_all_items_to_list(self):
        """添加所有项到结果列表"""
        for i, col in enumerate(self.data_list):
            for j, item in enumerate(col):
                list_item = QListWidgetItem(str(item))
                list_item.setData(Qt.UserRole, (j, i))  # 存储位置信息
                self.search_results_list.addItem(list_item)
                
    def _search_items(self, query):
        """搜索匹配的项"""
        for i, col in enumerate(self.data_list):
            for j, item in enumerate(col):
                if query in str(item).lower():
                    list_item = QListWidgetItem(str(item))
                    list_item.setData(Qt.UserRole, (j, i))  # 存储位置信息
                    self.search_results_list.addItem(list_item)
                    
    def select_item_from_search(self, item):
        """从搜索结果中选择项并发出位置信号"""
        # 直接从item的data中获取位置信息
        position = item.data(Qt.UserRole)
        self.item_selected_from_search.emit(position)
        self.hide_search_overlay()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 测试用的示例多维列表
    test_data = [
        ["苹果", "香蕉", "橙子"],
        ["猫", "狗", "兔子"],
        ["红色", "蓝色", "绿色"]
    ]
    main_window = SearchOverlay(None, test_data)
    main_window.show()
    sys.exit(app.exec_())