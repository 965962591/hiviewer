import os
import sys
import json
from PyQt5.QtWidgets import (QApplication, QLabel, QDialogButtonBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt

# 导入自定义的模块
from src.utils.Custom_Font_class import SingleFontManager

class Qualcom_Dialog(QDialog):
    """自定义对话框类, 用于输入信息"""
    def __init__(self, images_path_list=None, parent=None):
        super().__init__(parent)

        # 初始化对话框UI
        self.init_ui()

        # 设置是否加载设置
        self.load_settings()

        # 根据传入的图片路径列表设置关联图片下拉框；
        if images_path_list and os.path.exists(images_path_list):
            # 优先选择传入的图片文件夹路径
            self.text_input2.setText(images_path_list)


        # 连接按钮信号
        self.finished.connect(self.save_settings)           
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.load_button.clicked.connect(self.load_qualcom_path)         
        self.load_images_button.clicked.connect(self.load_image_path)          
 

    def get_data(self):
        return {
            "Qualcom工具路径": self.text_input1.text(),
            "Image文件夹路径": self.text_input2.text(),
        }

    def init_ui(self):
        """初始化对话框UI"""

        # 设置窗口标题
        self.setWindowTitle("Qualcom(AEC10)工具解析图片接口")
        # 设置窗口大小
        self.setFixedSize(1200, 300)  # 设置对话框大小
        
        # 设置根路径以及保存的json路径
        self.root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.json_path = os.path.join(self.root_path, "cache", "Qualcom_exif_settings.json")

        # 初始化字体管理器，标签组件使用 D:\Image_process\hiviewer-master\fonts\JetBrainsMapleMono_Regular.ttf
        self.font_path_jetbrains = os.path.join(self.root_path, "fonts", "JetBrainsMapleMono_Regular.ttf")
        self.font_manager_jetbrains_big = SingleFontManager.get_font(size=12, font_path=self.font_path_jetbrains) 
        self.font_manager_jetbrains_small = SingleFontManager.get_font(size=10, font_path=self.font_path_jetbrains)

        self.setFont(self.font_manager_jetbrains_big)

        # 创建主布局
        self.layout = QVBoxLayout(self)

        # 统一的下拉框高度
        combo_box_height = 35

        
        # 第一行：标签 + 输入框 + 加载按钮 + 写入按钮
        layout_one = QHBoxLayout()
        self.label1 = QLabel("Qualcom工具路径:", self)
        self.label1.setFont(self.font_manager_jetbrains_big)
        self.text_input1 = QLineEdit(self)
        self.text_input1.setFixedHeight(combo_box_height)  # 设置下拉框高度
        self.text_input1.setFont(self.font_manager_jetbrains_small)
        self.text_input1.setPlaceholderText(r"如:C:\Qualcomm\Chromatix7\7.3.01.36\Chromatix.exe")  # 设置提示文本
        self.load_button = QPushButton("加载", self)
        self.load_button.setFont(self.font_manager_jetbrains_big)
        self.load_button.setFixedHeight(combo_box_height)  # 设置下拉框高度
        layout_one.addWidget(self.label1)
        layout_one.addWidget(self.text_input1)
        layout_one.addWidget(self.load_button)
        # 设置比例
        layout_one.setStretch(0, 1)   # label1 的比例
        layout_one.setStretch(1, 10)  # combo_box1 的比例
        layout_one.setStretch(2, 1)   # load_button 的比例
        self.layout.addLayout(layout_one)

        # 第二行：标签 + 输入框 + 汇总按钮 + 保存按钮
        layout_two = QHBoxLayout()
        self.label2 = QLabel("Image文件夹路径:", self)
        self.label2.setFont(self.font_manager_jetbrains_big)
        self.text_input2 = QLineEdit(self)
        self.text_input2.setFixedHeight(combo_box_height)  # 设置下拉框高度
        self.text_input2.setFont(self.font_manager_jetbrains_small)
        self.text_input2.setPlaceholderText("输入或加载待解析的图片文件夹...")  # 设置提示文本
        self.load_images_button = QPushButton("加载", self)
        self.load_images_button.setFont(self.font_manager_jetbrains_big)
        self.load_images_button.setFixedHeight(combo_box_height)  # 设置下拉框高度
        layout_two.addWidget(self.label2)
        layout_two.addWidget(self.text_input2)
        layout_two.addWidget(self.load_images_button)
        # 设置比例
        layout_two.setStretch(0, 1)   # label2 的比例
        layout_two.setStretch(1, 10)  # combo_box2 的比例
        layout_two.setStretch(2, 1)   # load_images_button 的比例
        self.layout.addLayout(layout_two)


        # 添加确认和取消按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.setFont(self.font_manager_jetbrains_big)
        self.layout.addWidget(self.button_box)



    def load_qualcom_path(self):
        """加载Qualcom(AEC10)工具路径"""
        try:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(self, "选择Qualcom工具路径", "", "EXE Files (*.exe);;All Files (*)", options=options)
            if file_path:
                self.text_input1.setText(file_path)  # 显示选定的文件路径
        except Exception as e:
            print(f"选择Qualcom工具路径时发生错误: {e}")

    def load_image_path(self):
        """加载文件夹路径"""
        try:
            options = QFileDialog.Options()
            folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", options=options)  # 获取文件夹路径
            if folder_path:
                self.text_input2.setText(folder_path)  # 显示选定的文件夹路径
        except Exception as e:
            print(f"加载文件夹时发生错误: {e}")


    # 新增方法：保存设置
    def save_settings(self):
        """保存当前设置"""
        try:
            settings = {
                "Qualcom工具路径": self.text_input1.text(),
                "Image文件夹路径": self.text_input2.text(),
            }
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

            print("Qualcom_Dialog类_配置已保存")
        except Exception as e:
            print(f"Qualcom_Dialog类_保存配置失败: {e}")
            

    # 新增方法：加载设置
    def load_settings(self):
        """加载上次保存的设置"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

                # 恢复上一次打开的信息
                self.text_input1.setText(settings.get("Qualcom工具路径", ""))
                self.text_input2.setText(settings.get("Image文件夹路径", ""))
            print("Qualcom_Dialog类_配置已成功读取")
        except Exception as e:
            print(f"Qualcom_Dialog类_读取配置失败: {e}")

    # 重写按键事件
    def keyPressEvent(self, event):
        """重写键盘按下事件，防止在输入框或下拉框中按下回车时关闭对话框"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 如果当前焦点在输入框或下拉框中，阻止默认行为
            if self.focusWidget() in [self.text_input1, self.text_input2]:
                event.ignore()  # 忽略事件
            else:
                super().keyPressEvent(event)  # 处理其他情况
        else:
            super().keyPressEvent(event)  # 处理其他按键事件


# 示例用法
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # dialog = Qualcom_Dialog("D:/Tuning/O19/0_pic")
    dialog = Qualcom_Dialog()
    dialog.show()
    sys.exit(app.exec_())