import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QMenu, QAction, QWidgetAction, QLabel, QHBoxLayout
from PyQt5.QtWidgets import QProxyStyle, QStyle
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt, QObject, QEvent

class ColorMenuEventFilter(QObject):
    """事件过滤器类，用于处理颜色菜单的悬停事件"""
    def eventFilter(self, watched, event):
        if event.type() == QEvent.HoverMove and isinstance(watched, QMenu):
            action = watched.actionAt(event.pos())
            if action and (color_data := action.data()):
                try:
                    r, g, b = map(int, color_data.split(','))
                    color = QColor(r, g, b)
                    watched.palette().setColor(QPalette.Highlight, color)
                    QApplication.processEvents()  # 立即处理所有待处理的事件
                except Exception as e:
                    print(f"颜色解析错误: {color_data} - {str(e)}")
        return super().eventFilter(watched, event)

class ColorComboBoxManager:
    """颜色设置下拉菜单管理类"""
    def __init__(self, combo_box, color_settings, callback):
        """
        参数说明:
        - combo_box: 要管理的QComboBox组件
        - color_settings: 颜色配置字典 {显示名称: RGB值}
        - index_map: 索引映射字典 {主选项索引: 对应的属性名}
        - callback: 颜色改变时的回调函数
        """
        self.combo_box = combo_box
        self.color_settings = color_settings
        self.callback = callback
        
        # 初始化下拉框
        self.combo_box.currentIndexChanged.connect(self.show_menu)
        self._setup_combo_box()

    def _setup_combo_box(self):
        """初始化下拉框选项"""
        self.combo_box.clear()
        self.combo_box.addItems(["✅颜色设置", "⭕一键重置", "🔽背景颜色>>", "🔽表格填充颜色>>", "🔽字体颜色>>", "🔽exif字体颜色>>"])
        self.combo_box.setCurrentIndex(0)

    def show_menu(self, index):
        """显示多级菜单"""
        if index == 1:  # 一键重置
            self._handle_reset()
        elif index >= 2:  # 颜色选项
            self._create_color_menu(index)
        elif not index:
            print("按下了颜色设置")

    def _handle_reset(self):
        """处理一键重置"""
        self.combo_box.setCurrentIndex(0)
        print("按下了一键重置")

    def _create_color_menu(self, index):
        """创建颜色选择菜单（修正方案）"""
        menu = QMenu(self.combo_box)
        event_filter = ColorMenuEventFilter(menu)  # 创建事件过滤器
        menu.installEventFilter(event_filter)  # 安装事件过滤器
        
        for sub_index, (color_name, rgb) in enumerate(self.color_settings.items()):
            action = QAction(color_name, menu)
            # 存储颜色数据
            action.setData(rgb.replace('rgb', '').strip('()'))
            action.triggered.connect(
                lambda _, cn=color_name, idx=index, si=sub_index:
                    self._on_color_selected(cn, idx, si))
            menu.addAction(action)
        
        # 显示菜单
        rect = self.combo_box.rect()
        global_pos = self.combo_box.mapToGlobal(rect.bottomLeft())
        menu.exec_(global_pos)

    def _on_color_selected(self, color_name, main_index, sub_index):
        """颜色选择处理"""
        print(f"Selected color: {color_name}, main_Index: {main_index},sub_Index: {sub_index}")


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.color_rgb_settings = {
            "18度灰": "rgb(127,127,127)",
            "石榴红": "rgb(242,12,0)",
            "乌漆嘛黑": "rgb(22, 24, 35)",
            "铅白": "rgb(240,240,244)", 
            "水色": "rgb(136,173,166)",   
            "石青": "rgb(123,207,166)",           
            "茶色": "rgb(242,12,0)",
            "天际": "rgb(236,237,236)",   
            "晴空": "rgb(234,243,244)",  
            "苍穹": "rgb(220,230,247)", 
            "湖光": "rgb(74,116,171)", 
            "曜石": "rgb(84, 99,125)", 
            "天际黑": "rgb(8,8,6)",   
            "晴空黑": "rgb(45,53,60)",  
            "苍穹黑": "rgb(47,51,68)", 
            "湖光黑": "rgb(49,69,96)", 
            "曜石黑": "rgb(57,63,78)", 
        }
        self.color_combo_mgr = ColorComboBoxManager(
            combo_box=self.comboBox1,
            color_settings=self.color_rgb_settings,
            callback=self.handle_color_change
        )

    def handle_color_change(self):
        print("按下了")
        pass


    def initUI(self):
        layout = QVBoxLayout()
        
        # 创建不可编辑的 QComboBox
        self.comboBox = QComboBox(self)
        self.comboBox.addItem("颜色设置")  # 添加初始提示文本
        self.comboBox.setEditable(False)   # 设置 QComboBox 不可编辑

        self.comboBox1 = QComboBox(self)
        self.comboBox1.addItem("颜色设置1")  # 添加初始提示文本
        self.comboBox1.setEditable(False)   # 设置 QComboBox 不可编辑

        layout.addWidget(self.comboBox)    # 添加 QComboBox 到布局
        layout.addWidget(self.comboBox1)    # 添加 QComboBox 到布局



        # 连接 QComboBox 的点击事件到显示菜单
        self.comboBox.activated.connect(self.show_menu)

        # 创建菜单
        self.menu = QMenu(self)
        # 定义颜色选项和菜单名称
        color_options = ["水色", "漆黑", "石榴红", "茶色", "石青", "18度灰", "铅白", "月白"]
        menu_names = ["背景颜色", "表格填充颜色", "字体颜色", "EXIF字体颜色"]
        # 添加主选项和对应的二级菜单
        for menu_name in menu_names:
            submenu = QMenu(menu_name, self)
            for color in color_options:
                action = QAction(color, self)
                action.triggered.connect(lambda checked, color=color: self.select_color(color))
                submenu.addAction(action)
            self.menu.addMenu(submenu)


        self.setLayout(layout)
        self.setWindowTitle("颜色选择器示例")

    def show_menu(self):
        # 获取 QComboBox 顶部的矩形区域
        rect = self.comboBox.rect()
        global_pos = self.comboBox.mapToGlobal(rect.bottomLeft())
        
        # 弹出 QMenu
        self.menu.exec_(global_pos)

    def select_color(self, color):
        # 处理选择的颜色
        self.comboBox.setCurrentText(color)  # 更新 QComboBox 显示为选中的颜色
        print(f"选中的颜色: {color}")  # 打印选中的颜色或进行其他处理


# 程序入口路径
if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MyWidget()
    widget.show()
    sys.exit(app.exec_())