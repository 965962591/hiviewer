import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QMenu, QAction

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        # 创建不可编辑的 QComboBox
        self.comboBox = QComboBox(self)
        self.comboBox.addItem("颜色设置")  # 添加初始提示文本
        
        # 设置 QComboBox 不可编辑
        self.comboBox.setEditable(False)

        # 添加 QComboBox 到布局
        layout.addWidget(self.comboBox)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MyWidget()
    widget.show()
    sys.exit(app.exec_())