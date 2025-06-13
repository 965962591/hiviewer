# -*- coding: utf-8 -*-
import os
import sys
import json
from PyQt5.QtWidgets import (QApplication, QLabel, QDialogButtonBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt

# 新增运行模式判断，是单独调试该模块，还是被其它模块调用
is_standalone = os.path.basename(sys.argv[0]).lower() == "dialog_qualcom_aebox.py"
# 单独调试该模块,将项目根目录添加到sys.path
if is_standalone:
    # 添加项目根目录到系统路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


"""导入自定义的模块"""
from src.common.font_manager import SingleFontManager
from src.utils.aeboxlink import test_aebox_link,launch_aebox,urlencode_folder_path,get_api_data


"""设置本项目的入口路径,全局变量BasePath"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))    

class Qualcom_Dialog(QDialog):
    """自定义对话框类, 用于输入信息"""
    def __init__(self, images_path_list=None, parent=None):
        super().__init__(parent)

        # 初始化对话框UI
        self.init_ui()

        # 设置信号槽
        self.setShortcut()

        # 设置是否加载设置
        self.load_settings()

        # 高通工具、AEBOX工具、图片文件夹等初始化状态检查
        self.test_button1()
        self.test_button3()
        self.test_connection()

        # 根据传入的图片路径列表设置关联图片下拉框；
        if images_path_list and os.path.exists(images_path_list):
            # 优先选择传入的图片文件夹路径
            self.text_input3.setText(images_path_list)


    def setShortcut(self):
        "连接按钮信号"
        self.finished.connect(self.save_settings)           
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.load_button.clicked.connect(self.load_qualcom_path)         
        self.load_images_button.clicked.connect(self.load_image_path)
        self.load_aebox_button.clicked.connect(self.load_aebox_path)
        self.status_button1.clicked.connect(self.test_button1)
        self.text_input1.textChanged.connect(self.test_button1)   
        self.status_button2.clicked.connect(self.click_button2)
        self.text_input2.textChanged.connect(self.test_connection)
        self.status_button3.clicked.connect(self.test_button3)
        self.text_input3.textChanged.connect(self.test_button3)          
 

    def get_data(self):
        return {
            "Qualcom工具路径": self.text_input1.text(),
            "AEBOX工具路径": self.text_input2.text(),  # 新增数据项
            "Image文件夹路径": self.text_input3.text(),
        }

    def init_ui(self):
        """初始化对话框UI"""

        # 设置窗口标题
        self.setWindowTitle("Qualcom(AEC10)工具解析图片接口")
        # 设置窗口大小
        self.setFixedSize(1200, 300)  # 设置对话框大小
        
        # 设置保存的json路径
        self.json_path = os.path.join(BasePath, "cache", "Qualcom_exif_settings.json")

        # 初始化字体管理器
        self.font_path_jetbrains = os.path.join(BasePath, "resource", "fonts", "JetBrainsMapleMono_Regular.ttf")
        self.font_manager_jetbrains_big = SingleFontManager.get_font(size=12, font_path=self.font_path_jetbrains) 
        self.font_manager_jetbrains_small = SingleFontManager.get_font(size=10, font_path=self.font_path_jetbrains)

        self.setFont(self.font_manager_jetbrains_big)

        # 创建主布局
        self.layout = QVBoxLayout(self)

        # 统一的下拉框高度
        combo_box_height = 35

        
        # 第一行：标签 + 输入框 + 加载按钮 + 状态检查按钮 高通工具路径🚀
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
        self.status_button1 = QPushButton("🚀", self)
        self.status_button1.setFont(self.font_manager_jetbrains_big)
        self.status_button1.setFixedHeight(combo_box_height)  # 设置下拉框高度
        layout_one.addWidget(self.label1)
        layout_one.addWidget(self.text_input1)
        layout_one.addWidget(self.load_button)
        layout_one.addWidget(self.status_button1)
        # 设置比例
        layout_one.setStretch(0, 1)   # label1 的比例
        layout_one.setStretch(1, 10)  # combo_box1 的比例
        layout_one.setStretch(2, 1)   # load_button 的比例
        # layout_one.setStretch(3, 1)  
        self.layout.addLayout(layout_one)


        # 第二行：标签 + 输入框 + 加载按钮+状态检查按钮  AEBOX工具路径
        layout_two = QHBoxLayout()
        self.label2 = QLabel("AEBOX工具路径:", self)
        self.label2.setFont(self.font_manager_jetbrains_big)
        self.text_input2 = QLineEdit(self)
        self.text_input2.setFixedHeight(combo_box_height)
        self.text_input2.setFont(self.font_manager_jetbrains_small)
        self.text_input2.setPlaceholderText(r"如:D:\Image_process\aebox_utrl\aebox\aebox.exe")
        self.load_aebox_button = QPushButton("加载", self)
        self.load_aebox_button.setFont(self.font_manager_jetbrains_big)
        self.load_aebox_button.setFixedHeight(combo_box_height)
        self.status_button2 = QPushButton("🚀", self)
        self.status_button2.setFont(self.font_manager_jetbrains_big)
        self.status_button2.setFixedHeight(combo_box_height)
        
        layout_two.addWidget(self.label2)
        layout_two.addWidget(self.text_input2)
        layout_two.addWidget(self.load_aebox_button)
        layout_two.addWidget(self.status_button2)
        layout_two.setStretch(0, 1)
        layout_two.setStretch(1, 10)
        layout_two.setStretch(2, 1)
        # layout_two.setStretch(3, 1)
        self.layout.addLayout(layout_two)


        # 第三行：标签 + 输入框 + 加载按钮+状态检查按钮  图片文件夹
        layout_three = QHBoxLayout()
        self.label3 = QLabel("Image文件夹路径:", self)
        self.label3.setFont(self.font_manager_jetbrains_big)
        self.text_input3 = QLineEdit(self)
        self.text_input3.setFixedHeight(combo_box_height)  # 设置下拉框高度
        self.text_input3.setFont(self.font_manager_jetbrains_small)
        self.text_input3.setPlaceholderText("输入或加载待解析的图片文件夹...")  # 设置提示文本
        self.load_images_button = QPushButton("加载", self)
        self.load_images_button.setFont(self.font_manager_jetbrains_big)
        self.load_images_button.setFixedHeight(combo_box_height)  # 设置下拉框高度
        self.status_button3 = QPushButton("🚀", self)
        self.status_button3.setFont(self.font_manager_jetbrains_big)
        self.status_button3.setFixedHeight(combo_box_height)  # 设置下拉框高度
        layout_three.addWidget(self.label3)
        layout_three.addWidget(self.text_input3)
        layout_three.addWidget(self.load_images_button)
        layout_three.addWidget(self.status_button3)
        # 设置比例
        layout_three.setStretch(0, 1)   # label2 的比例
        layout_three.setStretch(1, 10)  # combo_box2 的比例
        layout_three.setStretch(2, 1)   # load_images_button 的比例
        # layout_three.setStretch(3, 1) 
        self.layout.addLayout(layout_three)

        # 添加确认和取消按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.setFont(self.font_manager_jetbrains_big)
        self.layout.addWidget(self.button_box)


    def test_button1(self):
        """测试高通工具路径"""
        tool_path = self.text_input1.text()
        if not tool_path:
            print("请先加载正确的高通工具路径")
            # 设置按钮文本信息
            self.status_button1.setText("❌")
            # 设置悬浮提示信息
            self.status_button1.setToolTip(f"请先加载正确的高通工具路径")
            
            return
            
        if not os.path.exists(tool_path):
            print(f"路径不存在: {tool_path}")
            self.status_button1.setText("❌")
            self.status_button1.setToolTip(f"❌当前路径不存在，请加载正确的高通工具路径")
            return
        
        self.status_button1.setText("✅")
        self.status_button1.setToolTip(f"✅当前路径检查通过")
            

    # 新增第二行AEBOX工具方法：连接测试
    def test_connection(self):
        """
        测试AEBOX工具连接
        
        功能说明：
            ❌ AEBOX路径不正确
            🚀 AEBOX程序未打开，没有与hiviewer通信
            ✅ AEBOX路径正确，且能够与hiviewer正常通信
        """
        tool_path = self.text_input2.text()
        if not tool_path or not os.path.exists(tool_path):
            print("请先选择AEBOX工具路径")
            self.status_button2.setText("❌")
            self.status_button2.setToolTip(f"❌当前AEBOX工具路径不存在，请加载正确的工具路径")
            return
        
        # 检查当前程序tool_path，是否在运行 test_aebox_link,launch_aebox
        list_url = self.get_url()
        if list_url and test_aebox_link(list_url):
            self.status_button2.setText("✅")
            self.status_button2.setToolTip(f"✅当前AEBOX工具路径有效，连接测试通过")
            return

        self.status_button2.setText("🚀")
        self.status_button2.setToolTip(f"🚀当前AEBOX工具路径有效，程序未启动，点击按钮启动AEBOX")


    def get_url(self):
        """获取高通工具路径和图片文件夹路径的编码url"""

        # 高通工具路径url
        qualcom_path = self.text_input1.text()
        if qualcom_path and os.path.exists(qualcom_path):
            # url编码
            qualcom_path_encoded = urlencode_folder_path(qualcom_path)
            qualcom_path_url = f"http://127.0.0.1:8000/set_c7_path/{qualcom_path_encoded}"
        else:
            return []

        # 图片文件夹路径url
        image_path = self.text_input3.text()
        if image_path and os.path.exists(image_path):
            # url编码
            image_path_encoded = urlencode_folder_path(image_path)
            image_path_url = f"http://127.0.0.1:8000/set_image_folder/{image_path_encoded}"
        else:
            return []
        
        # 返回编码后的url列表
        list_endpoints = [
            qualcom_path_url,
            image_path_url
        ]

        return list_endpoints


    def click_button2(self):
        """测试图片文件夹路径"""
        tool_path = self.text_input2.text()
        current_text = self.status_button2.text()
        try:
            # 这里可以添加实际的连接测试逻辑
            if current_text == "🚀" and tool_path and os.path.exists(tool_path):
                # 启动aebox工具
                launch_aebox(tool_path)
                # test
                self.test_connection()

            image_path = self.text_input3.text()
            image_path_url = ""
            if image_path and os.path.exists(image_path):
                # url编码
                image_path_encoded = urlencode_folder_path(image_path)
                image_path_url = f"http://127.0.0.1:8000/set_image_folder/{image_path_encoded}"
            if current_text == "✅" and image_path_url:
                # 发送文件夹到aebox
                response = get_api_data(url=image_path_url, timeout=3)
                if response:
                    print("click_button2():发送文件成功")
                else:
                    print("click_button2():发送文件失败")
        except Exception as e:
            print(f"click_button2()--发生错误: {e}")
                

    def test_button3(self):
        """测试图片文件夹路径"""
        image_path = self.text_input3.text()
        if not image_path:
            print("请先加载正确的图片文件夹路径")
            # 设置按钮文本信息
            self.status_button3.setText("❌")
            # 设置悬浮提示信息
            self.status_button3.setToolTip(f"请先加载正确的图片文件夹路径")
            return
            
        if not os.path.exists(image_path):
            print(f"路径不存在: {image_path}")
            self.status_button3.setText("❌")
            self.status_button3.setToolTip(f"❌当前图片文件夹路径不存在，请加载正确的图片文件夹路径")
            return
        
        self.status_button3.setText("✅")
        self.status_button3.setToolTip(f"✅当前路径检查通过")


    def load_qualcom_path(self):
        """加载Qualcom(AEC10)工具路径"""
        try:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(self, "选择Qualcom工具路径", "", "EXE Files (*.exe);;All Files (*)", options=options)
            if file_path:
                self.text_input1.setText(file_path)  # 显示选定的文件路径
        except Exception as e:
            print(f"选择Qualcom工具路径时发生错误: {e}")

    def load_aebox_path(self):
        """加载AEBOX工具路径"""
        try:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择AEBOX工具路径", "", 
                "EXE Files (*.exe);;All Files (*)", options=options)
            if file_path:
                self.text_input2.setText(file_path)
        except Exception as e:
            print(f"选择AEBOX工具路径时发生错误: {e}")

    def load_image_path(self):
        """加载文件夹路径"""
        try:
            options = QFileDialog.Options()
            folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", options=options)  # 获取文件夹路径
            if folder_path:
                self.text_input3.setText(folder_path)  # 显示选定的文件夹路径
        except Exception as e:
            print(f"加载文件夹时发生错误: {e}")


    def save_settings(self):
        """保存当前设置"""
        try:
            settings = {
                "Qualcom工具路径": self.text_input1.text(),
                "AEBOX工具路径": self.text_input2.text(),
                "Image文件夹路径": self.text_input3.text(),
            }
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

            print("Qualcom_Dialog类_配置已保存")
        except Exception as e:
            print(f"Qualcom_Dialog类_保存配置失败: {e}")
            

    def load_settings(self):
        """加载上次保存的设置"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

                # 恢复上一次打开的信息
                self.text_input1.setText(settings.get("Qualcom工具路径", ""))
                self.text_input2.setText(settings.get("AEBOX工具路径", ""))
                self.text_input3.setText(settings.get("Image文件夹路径", ""))
            print("Qualcom_Dialog类_配置已成功读取")
        except Exception as e:
            print(f"Qualcom_Dialog类_读取配置失败: {e}")

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
    dialog = Qualcom_Dialog()
    dialog.show()
    sys.exit(app.exec_())