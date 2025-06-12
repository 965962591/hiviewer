# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate, QStyleOptionButton, QStyle, QApplication
from PyQt5.QtCore import Qt, QSize, QAbstractListModel, QModelIndex, QVariant

# 导入颜色工具函数 & 颜色配置
from src.utils.color import rgb_str_to_qcolor
from src.common.settings_ColorAndExif import load_color_settings  


class CustomComboBox(QComboBox):
    """重写QComboBox类, 保证用户点击复选框时不立即收起"""

    def __init__(self, parent=None):
        super(CustomComboBox, self).__init__(parent)
        self.setEditable(True)  # 设置可编辑

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if self.view().isVisible() and self.view().underMouse():
            # 点击下拉框区域时，接受事件并保持展开
            event.accept()  
        else:
            # 调用父类的默认行为进行下拉框关闭
            super(CustomComboBox, self).mousePressEvent(event)  

    def hidePopup(self):
        """自定义 hidePopup 方法，控制下拉框隐藏"""
        if self.view().isVisible() and not self.view().underMouse():
            super(CustomComboBox, self).hidePopup()


class CheckBoxListModel(QAbstractListModel):
    """自定义数据模型，用于存储文件夹名和复选框的状态。"""

    def __init__(self, items):
        super(CheckBoxListModel, self).__init__()
        self.items = ["全选"] + sorted(items)  # 第一个项作为"全选"，其余按字母排序
        self.checked_states = [False] * len(self.items)  # 初始化所有项为未选中状态
        self.checked_order = []  # 新增：记录选中顺序的列表

    def rowCount(self, parent=QModelIndex()):
        """返回模型中的行数（文件夹项数）。"""
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        """根据索引和角色返回相应的数据。"""
        if not index.isValid():
            return QVariant()
        if role == Qt.DisplayRole:
            return self.items[index.row()]  # 返回项目名称
        if role == Qt.UserRole:
            return self.checked_states[index.row()]  # 返回选中状态
        return QVariant()

    def setChecked(self, index):
        if not index.isValid():
            return

        row = index.row()
        if row == 0:  # 全选逻辑保持不变
            all_checked = not self.checked_states[0]
            self.checked_states = [all_checked] * len(self.items)
            self.checked_order = self.items[1:] if all_checked else []
            self.dataChanged.emit(self.index(0), self.index(len(self.items) - 1))
        else:
            # 更新选中状态
            self.checked_states[row] = not self.checked_states[row]
            
            # 更新选中顺序
            item = self.items[row]
            if self.checked_states[row]:
                if item not in self.checked_order:
                    self.checked_order.append(item)
            else:
                if item in self.checked_order:
                    self.checked_order.remove(item)
            
            self.updateSelectAllState()

        self.dataChanged.emit(index, index)

    def updateSelectAllState(self):
        """检查是否所有项目都被选中，并更新"全选"的状态。"""
        all_selected = all(self.checked_states[1:])
        self.checked_states[0] = all_selected
        self.dataChanged.emit(self.index(0), self.index(0))  # 更新"全选"选项的显示

    def getCheckedItems(self):
        """获取当前被选中的文件夹列表（按点击顺序）"""
        # 直接返回记录顺序的列表
        return self.checked_order.copy()


class CheckBoxDelegate(QStyledItemDelegate):
    """自定义委托，用于在 ComboBox 中绘制复选框。"""

    def paint(self, painter, option, index):
        """绘制复选框和文本。"""
        # 获取当前选中状态
        checked = index.data(Qt.UserRole)
        # 检查鼠标是否悬停
        is_hovered = option.state & QStyle.State_MouseOver  
        # 如果鼠标悬停，则设置鼠标悬停的颜色为加载的配置文件中的背景颜色，字体颜色为黑色
        if is_hovered:
            # load_color_settings函数在src/common/SettingInit.py中定义
            basic_color_settings = load_color_settings().get('basic_color_settings')
            background_color = (
                basic_color_settings.get('background_color_default', "rgb(173, 216, 230)")
                if basic_color_settings else "rgb(173, 216, 230)"
            )
            # 将字符串转换为QColor, rgb_str_to_qcolor函数在src/utils/color.py中定义
            background_color = rgb_str_to_qcolor(background_color) 
            # 鼠标悬停时的颜色
            painter.fillRect(option.rect, background_color) 
            
        # 绘制复选框
        checkbox_style_option = QStyleOptionButton()
        checkbox_style_option.rect = option.rect.adjusted(0, 0, 0, 0)
        checkbox_style_option.state = QStyle.State_On if checked else QStyle.State_Off
        checkbox_style_option.state |= QStyle.State_Enabled

        QApplication.style().drawControl(QStyle.CE_CheckBox, checkbox_style_option, painter)
        # 绘制文本
        text_rect = option.rect
        text_rect.adjust(25, 0, 0, 0)  # 调整文本位置
        painter.drawText(text_rect, Qt.AlignVCenter, index.data(Qt.DisplayRole))

    def sizeHint(self, option, index):
        """返回项的大小，包括缩进和其他空间设置。"""
        size = super(CheckBoxDelegate, self).sizeHint(option, index)
        return QSize(size.width(), size.height())  # 设置项的大小