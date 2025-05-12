from PyQt5.QtWidgets import QComboBox


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

