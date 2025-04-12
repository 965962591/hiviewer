from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QHBoxLayout
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import QUrl, Qt
import os
import sys

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

# 导入自定义模块
from src.utils.Custom_Font_class import SingleFontManager
from src.utils.update import check_update
    
# 字体管理器
font_manager = SingleFontManager()

# 设置本项目的入口路径
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))

# 使用src/__init__.py文件中设置的根目录
# from src import BASE_DIR
# BasePath = BASE_DIR


# 全局函数，版本号初始化
def version_init(VERSION=str):
    # 设置保存版本号的文件
    default_version_path = os.path.join(BasePath, "cache", "version.ini")
    try:
        # 检查文件是否存在，如果不存在则创建并写入默认版本号
        if not os.path.exists(default_version_path):
            # 确保cache目录存在
            os.makedirs(os.path.dirname(default_version_path), exist_ok=True)
            with open(default_version_path, 'w', encoding='utf-8') as f:
                f.write(VERSION)
            return VERSION
        else:
            with open(default_version_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception as e:
        print(f"版本号初始化失败: {str(e)}")
        return VERSION  # 返回默认版本号

class AboutDialog(QDialog):
    def __init__(self, markdown_path=None):
        super().__init__()

        if not markdown_path or not os.path.exists(markdown_path):
            # 直接获取markdown文件的路径
            markdown_path = os.path.join(BasePath, "docs", "update_main_logs.md")

        # 设置默认版本号，并从version.ini配置文件中读取当前最新的版本号
        self.VERSION = version_init(VERSION='release-v2.3.2')

        # 设置窗口属性
        self.setWindowTitle("关于")
        self.setFixedSize(1300, 1000)
        main_layout = QVBoxLayout()
        icon_path = os.path.join(BasePath, "icons", "about.ico")
        self.setWindowIcon(QIcon(icon_path))

        # 创建一个垂直布局，用于放置图标和版本号
        icon_layout = QVBoxLayout()
        icon_path = os.path.join(BasePath, "icons", "viewer_3.ico")
        icon_label = QLabel()
        icon_label.setPixmap(QIcon(icon_path).pixmap(108, 108))
        icon_layout.addWidget(icon_label)
        icon_label.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(icon_layout)

        # 创建一个水平布局，用于放置标题和版本号
        title_layout = QHBoxLayout()
        title_label = QLabel(f"HiViewer({self.VERSION})")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(font_manager.get_font(20))
        title_layout.addWidget(title_label)
        main_layout.addLayout(title_layout)

        # 基础描述信息 and 作者描述信息
        basic_description_label = QLabel("HiViewer 看图工具，可支持多图片对比查看、多视频同步播放\n并集成有AI提示看图、批量重命名文件、压缩复制文件、局域网传输文件以及存储常见ADB脚本并一键运行等多种实用功能...")
        basic_description_label.setAlignment(Qt.AlignCenter)
        basic_description_label.setFont(font_manager.get_font(10))
        main_layout.addWidget(basic_description_label)


        # 添加一个水平布局，用于放置作者描述信息按钮
        button_layout = QHBoxLayout()
        auther_1_button = QPushButton("diamond_cz@163.com")
        auther_1_button.clicked.connect(self.open_auther1_url)
        auther_2_button = QPushButton("barrymchen@gmail.com")
        auther_2_button.clicked.connect(self.open_auther2_url)

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
        auther_1_button.setStyleSheet(button_style)
        auther_2_button.setStyleSheet(button_style)
        # 设置按钮字体
        auther_1_button.setFont(font_manager.get_font(12))
        auther_2_button.setFont(font_manager.get_font(12))

        button_layout.addStretch(1)
        button_layout.addWidget(auther_1_button)
        button_layout.addWidget(auther_2_button)
        button_layout.addStretch(1)
        main_layout.addLayout(button_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        check_update_button = QPushButton("检查更新")
        check_update_button.clicked.connect(self.release_updates)
        homepage_button = QPushButton("github主页")
        homepage_button.clicked.connect(self.open_homepage_url)
        feedback_button = QPushButton("建议反馈")
        feedback_button.clicked.connect(self.open_feedback_url)
        faq_button = QPushButton("使用指南")
        faq_button.clicked.connect(self.open_faq_url)

        # 设置按钮为自定义字体并设置大小
        check_update_button.setFont(font_manager.get_font(12))
        homepage_button.setFont(font_manager.get_font(12))
        feedback_button.setFont(font_manager.get_font(12))
        faq_button.setFont(font_manager.get_font(12))
        button_layout.addWidget(check_update_button)
        button_layout.addWidget(homepage_button)
        button_layout.addWidget(feedback_button)
        button_layout.addWidget(faq_button)
        main_layout.addLayout(button_layout)

        # 更新日志，支持导入markdown文件
        changelog_browser = QTextBrowser()
        changelog_content = self.read_changelog(markdown_path)
        changelog_browser.setMarkdown(changelog_content)
        changelog_browser.setFont(font_manager.get_font(10))
        main_layout.addWidget(changelog_browser)

        # 设置主布局
        self.setLayout(main_layout)

    def read_changelog(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "# 更新日志\n无法找到更新日志文件。"

    def open_feedback_url(self):
        QDesktopServices.openUrl(QUrl("https://tally.so/r/wgJyJK"))

    def open_homepage_url(self):
        QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz"))

    def open_faq_url(self):
        QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz/Hiviewer_releases/blob/main/README.md"))

    def open_auther1_url(self):
        QDesktopServices.openUrl(QUrl("https://gitee.com/diamond-cz"))

    def open_auther2_url(self):
        QDesktopServices.openUrl(QUrl("https://github.com/965962591"))


    """ 移除该段逻辑，使用线程运行自动检测更新"""
    def release_updates(self):
        # check_update(self)  # self 是主窗口实例 # 调用自动检查更新模块update.py
        # QDesktopServices.openUrl(QUrl("https://github.com/diamond-cz/Hiviewer_releases/releases/"))
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
    


# 示例用法
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AboutDialog()
    dialog.show()
    sys.exit(app.exec_())