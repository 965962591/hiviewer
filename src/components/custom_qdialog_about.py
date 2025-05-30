# -*- coding: utf-8 -*-
import os
import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QHBoxLayout
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import QUrl, Qt

"""导入自定义模块,主函数调用"""
from src.common.font_manager import SingleFontManager
from src.utils.update import check_update
from src.common.version_Init import version_init

"""
在本项目结构中正确导入自定义模块的方法：

1. 使用相对路径, 符合Python模块导入规范:
from Custom_Font_class import SingleFontManager
from update import check_update

2. 添加项目根目录到系统路径:
import sys
# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.utils.Custom_Font_class import SingleFontManager
from src.utils.update import check_update

"""


"""设置本项目的入口路径"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))
    

class AboutDialog(QDialog):
    def __init__(self, md_path_user=None, md_path_version=None):
        super().__init__()

        # 设置使用说明markdown文件，备用文件
        if not md_path_user or not os.path.exists(md_path_user):
            md_path_user = os.path.join(BasePath, "resource", "docs", "User_Manual.md")
        self.User_Manual_Mdpath = md_path_user

        # 设置版本更新markdown文件
        if not md_path_version or not os.path.exists(md_path_version):
            md_path_version = os.path.join(BasePath, "resource", "docs", "Version_Updates.md")
        self.Version_Update_Mdpath = md_path_version
        
        # 设置默认版本号，并从version.ini配置文件中读取当前最新的版本号
        self.VERSION = version_init()

        # UI界面初始化
        self.ui_init()

        # 设置快捷键和槽函数
        self.set_shortcut()

        # 设置窗口标题组件和样式表
        self.set_stylesheet()


    def ui_init(self):
        """UI界面初始化"""

        """UI界面,整体是一个垂直layout"""
        self.main_layout = QVBoxLayout()
        
        # 创建一个垂直布局，用于放置图标和版本号
        self.icon_layout = QVBoxLayout()
        self.icon_label = QLabel() # 放置图标
        icon_path = os.path.join(BasePath, "resource", "icons", "viewer_3.ico")
        self.icon_label.setPixmap(QIcon(icon_path).pixmap(108, 108))
        self.icon_layout.addWidget(self.icon_label)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(self.icon_layout)

        # 创建一个水平布局，用于放置标题和版本号
        self.title_layout = QHBoxLayout()
        self.title_label = QLabel(f"HiViewer({self.VERSION})")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.title_label)
        self.main_layout.addLayout(self.title_layout)

        # 基础描述信息 and 作者描述信息
        self.basic_description_label = QLabel("HiViewer 看图工具，可支持多图片对比查看、多视频同步播放\n并集成有AI提示看图、批量重命名文件、压缩复制文件、局域网传输文件以及存储常见ADB脚本并一键运行等多种实用功能...")
        self.basic_description_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.basic_description_label)


        # 添加一个水平布局，用于放置作者描述信息按钮
        self.button_layout = QHBoxLayout()
        self.auther_1_button = QPushButton("diamond_cz@163.com")
        self.auther_2_button = QPushButton("barrymchen@gmail.com")
        self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.auther_1_button)
        self.button_layout.addWidget(self.auther_2_button)
        self.button_layout.addStretch(1)
        self.main_layout.addLayout(self.button_layout)
        
        # 设置四个功能按钮
        self.button_layout = QHBoxLayout()
        
        self.user_manual_button = QPushButton("使用说明")
        self.change_log_button = QPushButton("更新日志")
        self.feedback_button = QPushButton("建议反馈")
        self.check_update_button = QPushButton("检查更新")
        self.button_layout.addWidget(self.user_manual_button)
        self.button_layout.addWidget(self.change_log_button)
        self.button_layout.addWidget(self.feedback_button)
        self.button_layout.addWidget(self.check_update_button)
        self.main_layout.addLayout(self.button_layout)

        # 设置QTextBrowser组件，支持导入markdown文件显示
        self.changelog_browser = QTextBrowser()
        self.main_layout.addWidget(self.changelog_browser)

        # 设置主布局
        self.setLayout(self.main_layout)

    def set_shortcut(self):
        """设置快捷键和槽函数"""

        # 作者信息按钮槽函数
        self.auther_1_button.clicked.connect(self.open_auther1_url)
        self.auther_2_button.clicked.connect(self.open_auther2_url)

        # 设置按钮槽函数
        self.check_update_button.clicked.connect(self.release_updates)
        self.user_manual_button.clicked.connect(self.open_homepage_url)
        self.change_log_button.clicked.connect(self.open_faq_url)
        self.feedback_button.clicked.connect(self.open_feedback_url)
        

    def set_stylesheet(self):
        """设置窗口标题组件和样式表"""
        # 设置标题和图标
        self.setWindowTitle("关于")
        icon_path = os.path.join(BasePath, "resource", "icons", "about.ico")
        self.setWindowIcon(QIcon(icon_path))

        # 获取鼠标所在屏幕，并根据当前屏幕分辨率自适应界面大小
        screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        screen_geometry = QtWidgets.QApplication.desktop().screenGeometry(screen)
        self.width = int(screen_geometry.width() * 0.50)
        self.height = int(screen_geometry.height() * 0.80)
        self.resize(self.width, self.height)
        
        # 设置图标下的标题和描述信息的字体
        font_manager_10 = SingleFontManager.get_font(10)
        font_manager_12 = SingleFontManager.get_font(12)
        font_manager_20 = SingleFontManager.get_font(20)
        
        self.title_label.setFont(font_manager_20)
        self.basic_description_label.setFont(font_manager_10)

        # 设置样式表，去掉边框，悬停时添加下划线
        button_style = """
        QPushButton {
            border: none;                 /* 去掉边框 */
            text-decoration: none;        /* 默认无下划线 */
        }
        QPushButton:hover {
            text-decoration: underline;   /* 鼠标悬停时添加下划线 */
        }
        """
        self.auther_1_button.setStyleSheet(button_style)
        self.auther_2_button.setStyleSheet(button_style)
        # 设置按钮字体
        self.auther_1_button.setFont(font_manager_12)
        self.auther_2_button.setFont(font_manager_12)

        # 四个功能按钮
        self.check_update_button.setFont(font_manager_12)
        self.user_manual_button.setFont(font_manager_12)
        self.feedback_button.setFont(font_manager_12)
        self.change_log_button.setFont(font_manager_12)

        # 设置显示markdow文件的组件样式
        self.changelog_content = self.read_changelog(self.User_Manual_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)
        self.changelog_browser.setFont(font_manager_10)

    

    def read_changelog(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "# 更新日志\n无法找到更新日志文件。"

    def open_feedback_url(self):
        QDesktopServices.openUrl(QUrl("https://tally.so/r/wgJyJK"))

    def open_homepage_url(self):
        """打开使用说明md文件"""
        # QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz"))
        self.changelog_browser.clear()  # 清空内容
        self.changelog_content = self.read_changelog(self.User_Manual_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)

    def open_faq_url(self):
        """打开版本更新md文件"""
        # QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz/Hiviewer_releases/blob/main/README.md"))
        self.changelog_browser.clear()  # 清空内容
        self.changelog_content = self.read_changelog(self.Version_Update_Mdpath)
        self.changelog_browser.setMarkdown(self.changelog_content)

    def open_auther1_url(self): 
        # gitee
        # QDesktopServices.openUrl(QUrl("https://gitee.com/diamond-cz"))
        # github
        QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz"))

    def open_auther2_url(self):
        QDesktopServices.openUrl(QUrl("https://github.com/965962591"))


    
    def release_updates(self):
        """ 使用函数check_update自动检测更新"""
        try:
            # 初始化对话框并绑定销毁事件
            self.update_dialog = check_update()
            if self.update_dialog:
                print("更新成功")
                pass
            else:
                print("取消更新")
                pass
        except Exception as e:
            error_msg = f"检查更新报错:\n{str(e)}"
            print(error_msg)
    
