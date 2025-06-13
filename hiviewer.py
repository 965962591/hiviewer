#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File         :hiviewer.py
@Time         :2025/06/04
@Author       :diamond_cz@163.com
@Version      :release-v3.5.1
@Description  :hiviewer看图工具主界面

python项目多文件夹路径说明:
(1)获取当前py文件的路径: 
os.path.abspath(__file__)
(2)获取当前py文件的父文件夹路径: 
os.path.dirname(os.path.abspath(__file__))
BASEICONPATH = Path(__file__).parent
(1)获取主函数py文件的路径: 
os.path.abspath(sys.argv[0])
(2)获取主函数py文件的父文件夹路径: 
os.path.dirname(os.path.abspath(sys.argv[0]))
BASEICONPATH = Path(sys.argv[0]).parent
'''

"""导入python内置模块"""
import gc
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from itertools import zip_longest

"""导入python第三方模块"""
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QFileSystemModel, QAbstractItemView, QTableWidgetItem, 
    QHeaderView, QShortcut, QSplashScreen, QMainWindow, 
    QSizePolicy, QApplication, QMenu, QInputDialog, 
    QProgressDialog, QDialog, QLabel)
from PyQt5.QtCore import (
    Qt, QDir, QSize, QTimer, QThreadPool, QUrl, QSize, 
    QMimeData, QPropertyAnimation, QItemSelection, QItemSelectionModel)

"""导入用户自定义的模块"""
from src.components.ui_main import Ui_MainWindow                            # 假设你的主窗口类名为Ui_MainWindow
from src.view.sub_compare_image_view import SubMainWindow                   # 假设这是你的子窗口类名
from src.view.sub_compare_video_view import VideoWall                       # 假设这是你的子窗口类名 
from src.view.sub_rename_view import FileOrganizer                          # 添加这行以导入批量重名名类名
from src.view.sub_image_process_view import SubCompare                      # 确保导入 SubCompare 类
from src.view.sub_bat_view import LogVerboseMaskApp                         # 导入批量执行命令的类
from src.components.custom_qMbox_showinfo import show_message_box           # 导入消息框类
from src.components.custom_qdialog_about import AboutDialog                 # 导入关于对话框类,显示帮助信息
from src.components.custom_qdialog_LinkQualcomAebox import Qualcom_Dialog   # 导入自定义对话框的类
from src.components.custom_qCombox_spinner import (CheckBoxListModel,       # 导入自定义下拉框类中的数据模型和委托代理类
    CheckBoxDelegate)        
from src.components.custom_qdialog_rename import SingleFileRenameDialog     # 导入自定义重命名对话框类
from src.components.custom_qdialog_progress import (ProgressDialog,         # 导入自定义压缩进度对话框类
    CompressWorker)         
from src.common.font_manager import MultiFontManager                        # 字体管理器
from src.common.version_Init import version_init                            # 版本号初始化
from src.common.settings_ColorAndExif import load_color_settings            # 导入自定义json配置文件
from src.common.log_files import setup_logging                              # 导入日志文件初始化
from src.qpm.qualcom import CommandThread                                   # 导入高通图片解析工具独立线程类
from src.utils.raw2jpg import Mipi2RawConverterApp                          # 导入MIPI RAW文件转换为JPG文件的类
from src.utils.update import check_update, pre_check_update                 # 导入自动更新检查程序
from src.utils.hisnot import WScreenshot                                    # 导入截图工具类
from src.utils.ImagePreview import ImageViewer                              # 导入自定义图片预览组件
from src.utils.xml import save_excel_data                                   # 导入xml文件解析工具类
from src.utils.delete import force_delete_folder                            # 导入强制删除文件夹的功能函数
from src.utils.Icon import IconCache, ImagePreloader                        # 导入文件Icon图标加载类
from src.utils.heic import extract_jpg_from_heic                            # 导入heic文件解析工具类
from src.utils.video import extract_video_first_frame                       # 导入视频预览工具类
from src.utils.image import ImageProcessor                                  # 导入图片处理工具类
from src.utils.sort import sort_by_custom                                   # 导入文件排序工具类
from src.view.sub_search_view import SearchOverlay                                  # 导入图片搜索工具类(ctrl+f)
from src.utils.decorator import CC_TimeDec                                  # 导入自定义装饰器
from src.utils.aeboxlink import (check_process_running,                     # 导入自定义装饰器
    urlencode_folder_path, get_api_data)


"""
设置主界面类区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
class HiviewerMainwindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(HiviewerMainwindow, self).__init__(parent)
        
        # 记录程序启动时间；设置图标路径；读取本地版本信息，并初始化新版本信息
        self.start_time = time.time()        
        self.base_icon_path = Path(__file__).parent / "resource" / "icons"
        self.version_info, self.new_version_info = version_init(), False     
        
        # 创建启动画面,启动画面以及相关初始化在self.update_splash_message()函数中
        self.create_splash_screen()


    @CC_TimeDec(tips="所有组件初始化完成")
    def initialize_components(self):
        """初始化所有组件"""
        # 初始化相关变量及配置文件
        self.init_variable()

        # 设置主界面相关组件
        self.set_stylesheet()

        # 加载之前的设置    
        self.load_settings()  

        # 设置快捷键
        self.set_shortcut()

        # 设置右侧表格区域的右键菜单
        self.setup_context_menu()  

        # 设置左侧文件浏览器的右键菜单
        self.setup_treeview_context_menu()

        # 模仿按下回车
        self.input_enter_action()  

        # 迁移到函数update_splash_message()中，modify by diamond_cz
        # 显示主窗口
        # self.show()


    def init_variable(self):
        """初始化整个主界面类所需的变量"""

        # 设置图片&视频文件格式
        self.IMAGE_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.webp', '.ico', '.heic') 
        self.VIDEO_FORMATS = ('.mp4', '.avi', '.mov', '.wmv', '.mpeg', '.mpg', '.mkv')

        # 初始化属性
        self.files_list = []                    # 文件名及基本信息列表
        self.paths_list = []                    # 文件路径列表
        self.dirnames_list = []                 # 选中的同级文件夹列表
        self.image_index_max = []               # 存储当前选中及复选框选中的，所有图片列有效行最大值
        self.preloading_file_name_paths = []    # 预加载图标前的文件路径列表
        self.compare_window = None              # 添加子窗口引用
        self.last_key_press = False             # 记录第一次按下键盘空格键或B键
        self.left_tree_file_display = False     # 设置左侧文件浏览器初始化标志位，只显示文件夹
        self.simple_mode = True                 # 设置默认模式为简单模式，同EXIF信息功能
        self.current_theme = "默认主题"          # 设置初始主题为默认主题

        # 添加预加载相关的属性初始化
        self.current_preloader = None 
        self.preloading = False        

        # 初始化线程池
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(max(4, os.cpu_count()))  

        # 初始化压缩工作线程,压缩包路径
        self.zip_path = None  
        self.compress_worker = None

        """加载颜色相关设置""" # 设置背景色和字体颜色，使用保存的设置或默认值
        basic_color_settings = load_color_settings().get('basic_color_settings',{})
        self.background_color_default = basic_color_settings.get("background_color_default", "rgb(173,216,230)")  # 深色背景色_好蓝
        self.background_color_table = basic_color_settings.get("background_color_table", "rgb(127, 127, 127)")    # 表格背景色_18度灰
        self.font_color_default = basic_color_settings.get("font_color_default", "rgb(0, 0, 0)")                  # 默认字体颜色_纯黑色
        self.font_color_exif = basic_color_settings.get("font_color_exif", "rgb(255, 255, 255)")                  # Exif字体颜色_纯白色

        """加载字体相关设置""" # 初始化字体管理器,并获取字体，设置默认字体 self.custom_font
        font_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "fonts", "JetBrainsMapleMono_Regular.ttf"), # JetBrains Maple Mono
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "fonts", "xialu_wenkai.ttf"),               # LXGW WenKai
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource", "fonts", "MapleMonoNormal_Regular.ttf")     # Maple Mono Normal
        ]
        MultiFontManager.initialize(font_paths=font_paths)
        self.custom_font = MultiFontManager.get_font(font_family="LXGW WenKai", size=12)
        self.custom_font_jetbrains = MultiFontManager.get_font(font_family="JetBrains Maple Mono", size=12)
        self.custom_font_jetbrains_medium = MultiFontManager.get_font(font_family="JetBrains Maple Mono", size=11)
        self.custom_font_jetbrains_small = MultiFontManager.get_font(font_family="JetBrains Maple Mono", size=10)
        self.custom_font = self.custom_font_jetbrains


    """
    设置动画显示区域开始线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """
    @CC_TimeDec(tips="创建hiviewer的启动画面")
    def create_splash_screen(self):
        """创建带渐入渐出效果的启动画面"""
        # 加载启动画面图片
        splash_path = (self.base_icon_path / "viewer_0.png").as_posix()
        splash_pixmap = QPixmap(splash_path)
        
        # 如果启动画面图片为空，则创建一个空白图片
        if splash_pixmap.isNull():
            splash_pixmap = QPixmap(400, 200)
            splash_pixmap.fill(Qt.white)
            
        # 创建启动画面
        self.splash = QSplashScreen(splash_pixmap)
        
        # 获取当前屏幕并计算居中位置, 移动到该位置
        x, y, _, _ = self.__get_screen_geometry()
        self.splash.move(x, y)
        
        # 设置半透明效果
        self.splash.setWindowOpacity(0)
        
        # 创建渐入动画
        self.fade_anim = QPropertyAnimation(self.splash, b"windowOpacity")
        self.fade_anim.setDuration(1000)  # 1000ms的渐入动画
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()
        
        # 设置启动画面的样式
        self.splash.setStyleSheet("""
            QSplashScreen {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                border-radius: 10px;
            }
        """)
        
        # 显示启动画面
        self.splash.show()
        
        # 设置进度更新定时器
        self.fla = 0         # 记录启动画面更新次数
        self.dots_count = 0  # 记录启动画面更新点
        self.splash_progress_timer = QTimer()  # 启动进度更新定时器
        self.splash_progress_timer.timeout.connect(self.update_splash_message)  # 连接定时器到更新函数,相关函数变量的初始化
        self.splash_progress_timer.start(10)   # 每10ms更新一次


    def update_splash_message(self):
        """更新启动画面的加载消息,并在这部分初始化UI界面以及相关变量"""
        # 更新进度点
        self.dots_count = (self.dots_count + 1) % 4
        dots = "." * self.dots_count
        
        # 使用HTML标签设置文字颜色为红色，并调整显示内容，文字颜色为配置文件（color_setting.json）中的背景颜色
        message = f'<div style="color: {"rgb(173,216,230)"};">HiViewer</div>' \
                  f'<div style="color: {"rgb(173,216,230)"};">正在启动...{dots}</div>'

        # 显示启动消息
        self.splash.showMessage(
            message, 
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )

        # 更新启动画面更新次数
        self.fla += 1
        print(f"----------[第 {self.fla} 次 进入函数update_splash_message], 当前运行时间: {(time.time()-self.start_time):.2f} 秒----------")
              

        # 检查是否完成初始化, 第三次进入
        if not hasattr(self, 'initialize_three') and hasattr(self, 'initialize_two'):
            # 初始化完成标志位
            self.initialize_three = True
            
            # 创建渐出动画
            self.fade_out = QPropertyAnimation(self.splash, b"windowOpacity")
            self.fade_out.setDuration(1000)  # 1000ms的渐出动画
            self.fade_out.setStartValue(1)
            self.fade_out.setEndValue(0)
            self.fade_out.finished.connect(self.splash.close)
            self.fade_out.start()

            # 停止定时器
            self.splash_progress_timer.stop()

            # 获取当前屏幕并计算居中位置，移动到该位置
            x, y, _, _ = self.__get_screen_geometry()
            self.move(x, y)

            # 预先检查更新  
            self.pre_update()

            # 记录结束时间并计算耗时
            self.preview_label.setText(f"⏰启动耗时: {(time.time()-self.start_time):.2f} 秒")
            print(f"----------[hiviewer主界面启动成功], 共耗时: {(time.time()-self.start_time):.2f} 秒----------")

            # 延时显示主窗口,方便启动画面渐出
            QTimer.singleShot(800, self.show)

            # 延时检查更新
            # QTimer.singleShot(3000, self.pre_update)


        # 初始化其余相关变量, 第二次进入
        if not hasattr(self, 'initialize_two') and hasattr(self, 'drag_flag'):
            self.initialize_two = True
            self.initialize_components()


        # 初始化界面UI, 第一次进入
        if not hasattr(self, 'drag_flag'):
            self.drag_flag = True  # 默认设置是图片拖拽模式, self.setupUi(self) 中需要调用
            self.setupUi(self)



    """
    设置hiviewer类中的可重复使用的common私有方法开始线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """
    def __get_screen_geometry(self)->tuple:
        """
        该函数主要是实现了获取当前鼠标所在屏幕的几何信息的功能.
        Args:
            self (object): 当前对象
        Returns:
            x (int): 当前屏幕中心的x坐标
            y (int): 当前屏幕中心的y坐标
            w (int): 当前屏幕的宽度
            h (int): 当前屏幕的高度
        Raises:
            列出函数可能抛出的所有异常，并描述每个异常的触发条件
        Example:
            提供一个或多个使用函数的示例，展示如何调用函数及其预期输出
        Note:
            注意事项，列出任何重要的假设、限制或前置条件.
        """
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        screen_geometry = QApplication.desktop().screenGeometry(screen)
        x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
        w = screen_geometry.width()
        h = screen_geometry.height()
        return x, y, w, h




    """
    设置右键菜单函数区域开始线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """

    def setup_context_menu(self):
        """设置右键菜单"""
        self.context_menu = QMenu(self)
    
        # 设置菜单样式 modify by diamond_cz 20250217 优化右键菜单栏的显示
        self.context_menu.setStyleSheet(f"""
            QMenu {{
                /*background-color: #F0F0F0;   背景色 */

                font-family: "{self.custom_font_jetbrains_small.family()}";
                font-size: {self.custom_font_jetbrains_small.pointSize()}pt;    
            }}
            QMenu::item:selected {{
                background-color: {self.background_color_default};   /* 选中项背景色 */
                color: #000000;               /* 选中项字体颜色 */
            }}
        """)

        # 添加主菜单项并设置图标
        icon_path = (self.base_icon_path / "delete_ico_96x96.ico").as_posix()
        delete_icon = QIcon(icon_path) 
        icon_path = (self.base_icon_path / "paste_ico_96x96.ico").as_posix()
        paste_icon = QIcon(icon_path) 
        icon_path = (self.base_icon_path / "update_ico_96x96.ico").as_posix()
        refresh_icon = QIcon(icon_path) 
        icon_path = (self.base_icon_path / "theme_ico_96x96.ico").as_posix()
        theme_icon = QIcon(icon_path) 
        icon_path = (self.base_icon_path / "image_size_reduce_ico_96x96.ico").as_posix()
        image_size_reduce_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "ps_ico_96x96.ico").as_posix()
        ps_icon = QIcon(icon_path) 
        icon_path = (self.base_icon_path / "cmd_ico_96x96.ico").as_posix()
        command_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "exif_ico_96x96.ico").as_posix()
        exif_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "raw_ico_96x96.ico").as_posix()
        raw_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "rename_ico_96x96.ico").as_posix()
        rename_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "about.ico").as_posix()
        help_icon = QIcon(icon_path) 
        icon_path = (self.base_icon_path / "file_zip_ico_96x96.ico").as_posix()
        zip_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "TCP_ico_96x96.ico").as_posix()
        tcp_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "rorator_plus_ico_96x96.ico").as_posix()
        rotator_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "line_filtrate_ico_96x96.ico").as_posix()
        filtrate_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "win_folder_ico_96x96.ico").as_posix()
        win_folder_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "restart_ico_96x96.ico").as_posix()
        restart_icon = QIcon(icon_path)


        # 创建二级菜单-删除选项
        sub_menu = QMenu("删除选项", self.context_menu) 
        sub_menu.setIcon(delete_icon)  
        sub_menu.addAction("从列表中删除(D)", self.delete_from_list)  
        sub_menu.addAction("从原文件删除(Ctrl+D)", self.delete_from_file)  

        # 创建二级菜单-复制选项
        sub_menu2 = QMenu("复制选项", self.context_menu)  
        sub_menu2.setIcon(paste_icon)  
        sub_menu2.addAction("复制文件路径(C)", self.copy_selected_file_path)  
        sub_menu2.addAction("复制文件(Ctrl+C)", self.copy_selected_files)  

        # 创建二级菜单-无损旋转
        sub_menu3 = QMenu("无损旋转", self.context_menu)  
        sub_menu3.setIcon(rotator_icon)  
        sub_menu3.addAction("逆时针旋转", lambda: self.jpg_lossless_rotator('l'))  
        sub_menu3.addAction("顺时针旋转", lambda: self.jpg_lossless_rotator('r'))  
        sub_menu3.addAction("旋转180度", lambda: self.jpg_lossless_rotator('u'))  
        sub_menu3.addAction("水平翻转", lambda: self.jpg_lossless_rotator('h'))  
        sub_menu3.addAction("垂直翻转", lambda: self.jpg_lossless_rotator('v'))  
        sub_menu3.addAction("自动校准EXIF旋转信息", lambda: self.jpg_lossless_rotator('auto'))  

        # 创建二级菜单-按行筛选
        sub_menu4 = QMenu("按行筛选", self.context_menu)  
        sub_menu4.setIcon(filtrate_icon)  
        sub_menu4.addAction("奇数行", lambda: self.show_filter_rows('odd'))  
        sub_menu4.addAction("偶数行", lambda: self.show_filter_rows('even'))  
        sub_menu4.addAction("3选1", lambda: self.show_filter_rows('three_1'))  
        sub_menu4.addAction("3选2", lambda: self.show_filter_rows('three_2'))  
        sub_menu4.addAction("5选1", lambda: self.show_filter_rows('five_1'))  

        # 将二级菜单添加到主菜单
        self.context_menu.addMenu(sub_menu)   
        self.context_menu.addMenu(sub_menu2)  
        self.context_menu.addMenu(sub_menu4)  
        self.context_menu.addMenu(sub_menu3)  
        
        # 设置右键菜单槽函数
        self.context_menu.addAction(exif_icon, "高通AEC10解析图片(I)", self.on_i_pressed)
        self.context_menu.addAction(zip_icon, "压缩文件(Z)", self.compress_selected_files)
        self.context_menu.addAction(theme_icon, "切换主题(P)", self.on_p_pressed)
        self.context_menu.addAction(image_size_reduce_icon, "图片瘦身(X)", self.jpgc_tool) 
        self.context_menu.addAction(ps_icon, "图片调整(L)", self.on_l_pressed)
        self.context_menu.addAction(tcp_icon, "截图功能(T)", self.screen_shot_tool)
        self.context_menu.addAction(command_icon, "批量执行命令工具(M)", self.execute_command)
        self.context_menu.addAction(rename_icon, "批量重命名工具(F4)", self.on_f4_pressed)
        self.context_menu.addAction(raw_icon, "RAW转JPG工具(F1)", self.on_f1_pressed)
        self.context_menu.addAction(win_folder_icon, "打开资源管理器(W)", self.reveal_in_explorer)
        self.context_menu.addAction(refresh_icon, "刷新(F5)", self.on_f5_pressed)
        self.context_menu.addAction(restart_icon, "重启程序", self.on_f12_pressed)
        self.context_menu.addAction(help_icon, "关于(Ctrl+H)", self.on_ctrl_h_pressed)

        # 连接右键菜单到表格
        self.RB_QTableWidget0.setContextMenuPolicy(Qt.CustomContextMenu)
        self.RB_QTableWidget0.customContextMenuRequested.connect(self.show_context_menu)


    def show_context_menu(self, pos):
        """显示右键菜单"""
        self.context_menu.exec_(self.RB_QTableWidget0.mapToGlobal(pos))



    def setup_treeview_context_menu(self):
        """设置左侧文件浏览器右键菜单"""

        # 添加右键菜单功能,连接到文件浏览树self.Left_QTreeView上
        self.Left_QTreeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.Left_QTreeView.customContextMenuRequested.connect(self.show_treeview_context_menu)



    def show_treeview_context_menu(self, pos):
        """显示文件树右键菜单"""

        # 设置左侧文件浏览器的右键菜单栏
        self.treeview_context_menu = QMenu(self)
    
        # 设置右键菜单样式
        self.treeview_context_menu.setStyleSheet(f"""
            QMenu {{
                /*background-color: #F0F0F0;   背景色 */

                font-family: "{self.custom_font_jetbrains_small.family()}";
                font-size: {self.custom_font_jetbrains_small.pointSize()}pt;    
            }}
            QMenu::item:selected {{
                background-color: {self.background_color_default};   /* 选中项背景色 */
                color: #000000;               /* 选中项字体颜色 */
            }}
        """)

        # 添加常用操作
        show_file_action = self.treeview_context_menu.addAction(
            "显示所有文件" if not self.left_tree_file_display else "隐藏所有文件")
        open_action = self.treeview_context_menu.addAction("打开所在位置")
        open_aebox = self.treeview_context_menu.addAction("打开aebox")
        send_path_to_aebox = self.treeview_context_menu.addAction("发送到aebox")
        copy_path_action = self.treeview_context_menu.addAction("复制路径")
        rename_action = self.treeview_context_menu.addAction("重命名")  
        
        # 获取选中的文件信息
        index = self.Left_QTreeView.indexAt(pos)
        if index.isValid():
            file_path = self.file_system_model.filePath(index)

            # 连接想信号槽函数
            open_action.triggered.connect(lambda: self.open_file_location(file_path))  
            copy_path_action.triggered.connect(lambda: self.copy_file_path(file_path))
            send_path_to_aebox.triggered.connect(lambda: self.send_file_path_to_aebox(file_path))
            rename_action.triggered.connect(lambda: self.rename_file(file_path))
            show_file_action.triggered.connect(self.show_file_visibility)
            open_aebox.triggered.connect(lambda: self.open_aebox(file_path))


            # 设置右键菜单绑定左侧文件浏览器
            self.treeview_context_menu.exec_(self.Left_QTreeView.viewport().mapToGlobal(pos))


    
    """
    设置右键菜单函数区域结束线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """

    @CC_TimeDec(tips="设置主界面图标以及标题")
    def set_stylesheet(self):
        """设置主界面图标以及标题"""
        # print("[set_stylesheet]-->设置主界面相关组件")

        icon_path = os.path.join(self.base_icon_path, "viewer_3.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(f"HiViewer")

        # 根据鼠标的位置返回当前光标所在屏幕的几何信息
        _, _, w, h = self.__get_screen_geometry()
        width, height = int(w * 0.65), int(h * 0.65)
        self.resize(width, height)

        # 启用拖放功能
        self.setAcceptDrops(True)

        """界面底部状态栏设置"""
        # self.statusbar --> self.statusbar_widget --> self.statusbar_QHBoxLayout --> self.statusbar_button1 self.statusbar_button2
        # 设置按钮无边框
        self.statusbar_button1.setFlat(True)
        self.statusbar_button2.setFlat(True)

        # 初始化版本更新按钮文本
        self.statusbar_button2.setText(f"🚀版本({self.version_info})")            

        # 初始化标签文本
        self.statusbar_label1.setText(f"🔉: 进度提示标签🍃")
        self.statusbar_label0.setText(f"📢:选中或筛选的文件夹中包含{self.image_index_max}张图")
        self.statusbar_label.setText(f"[0]已选择")

        
        """ 左侧组件
        设置左侧组件显示风格，背景颜色为淡蓝色，四角为圆形; 下面显示左侧组件name 
        self.Left_QTreeView | self.Left_QFrame
        self.verticalLayout_left_2
        modify by diamond_cz 20250403 移除self.L_radioButton1 | self.L_radioButton2 | self.L_pushButton1 | self.L_pushButton2
        """  


        # self.Left_QTreeView
        self.file_system_model = QFileSystemModel(self)
        self.file_system_model.setRootPath('')  # 设置根路径为空，表示显示所有磁盘和文件夹
        self.Left_QTreeView.setModel(self.file_system_model)

        # 隐藏不需要的列，只显示名称列
        self.Left_QTreeView.header().hide()  # 隐藏列标题
        self.Left_QTreeView.setColumnWidth(0, 650)  # 设置名称列宽度，以显示横向滚动条
        self.Left_QTreeView.setColumnHidden(1, True)  # 隐藏大小列
        self.Left_QTreeView.setColumnHidden(2, True)  # 隐藏类型列
        self.Left_QTreeView.setColumnHidden(3, True)  # 隐藏修改日期列 

        # 设置QDir的过滤器默认只显示文件夹
        self.file_system_model.setFilter(QDir.NoDot | QDir.NoDotDot | QDir.AllDirs)    # 使用QDir的过滤器,只显示文件夹

        """ 右侧组件
        设置右侧组件显示风格（列出了右侧第一行第二行第三行的组件名称）
        self.RT_QComboBox | self.RT_QPushButton2 | self.RT_QPushButton3
        self.RT_QComboBox0 | self.RT_QComboBox1 | self.RT_QComboBox2 | self.RT_QComboBox3 | self.RT_QPushButton5 | self.RT_QPushbutton6
        self.RB_QTableWidget0 
        """

        self.RT_QPushButton3.setText("清除")
        self.RT_QPushButton5.setText("对比")

        # 设置当前目录到地址栏，并将地址栏的文件夹定位到左侧文件浏览器中
        current_directory = os.path.dirname(os.path.abspath(__file__).capitalize())
        self.RT_QComboBox.addItem(current_directory)
        self.RT_QComboBox.lineEdit().setPlaceholderText("请在地址栏输入一个有效的路径")  # 设置提示文本
        
        # RB_QTableWidget0表格设置
        self.RB_QTableWidget0.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # 设置表格列宽自适应
   
        # RT_QComboBox0 添加下拉框选项
        self.RT_QComboBox0.addItem("显示图片文件")
        self.RT_QComboBox0.addItem("显示视频文件")
        self.RT_QComboBox0.addItem("显示所有文件")

        # RT_QComboBox2 添加下拉框选项
        self.RT_QComboBox2.addItem("按文件名称排序")
        self.RT_QComboBox2.addItem("按创建时间排序")
        self.RT_QComboBox2.addItem("按修改时间排序")
        self.RT_QComboBox2.addItem("按文件大小排序")
        self.RT_QComboBox2.addItem("按曝光时间排序")
        self.RT_QComboBox2.addItem("按ISO排序")
        self.RT_QComboBox2.addItem("按文件名称逆序排序")
        self.RT_QComboBox2.addItem("按创建时间逆序排序")
        self.RT_QComboBox2.addItem("按修改时间逆序排序")
        self.RT_QComboBox2.addItem("按文件大小逆序排序")
        self.RT_QComboBox2.addItem("按曝光时间逆序排序")
        self.RT_QComboBox2.addItem("按ISO逆序排序")

        # RT_QComboBox3 添加下拉框选项
        self.RT_QComboBox3.addItem("默认主题")
        self.RT_QComboBox3.addItem("暗黑主题")

        """RT_QComboBox1待完善功能: 在下拉框中多次选择复选框后再收起下拉框; modify by 2025-01-21, 在main_ui.py中使用自定义的 ComboBox已解决"""
        self.RT_QComboBox1.setEditable(True)  # 设置可编辑
        self.RT_QComboBox1.lineEdit().setReadOnly(True)  # 设置不可编辑
        self.RT_QComboBox1.lineEdit().setPlaceholderText("请选择")  # 设置提示文本
        

    def set_shortcut(self):
        """快捷键和槽函数连接事件"""

        """1.快捷键设置"""
        # 添加快捷键 切换主题
        self.p_shortcut = QShortcut(QKeySequence('p'), self)
        self.p_shortcut.activated.connect(self.on_p_pressed)
        # 添加快捷键，打开命令工具
        self.m_shortcut = QShortcut(QKeySequence('M'), self)
        self.m_shortcut.activated.connect(self.open_bat_tool)
        # 添加快捷键，切换上一组图片/视频
        self.b_shortcut = QShortcut(QKeySequence('b'), self)
        self.b_shortcut.activated.connect(self.on_b_pressed)
        # 添加快捷键，切换下一组图片/视频
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.space_shortcut.activated.connect(self.on_space_pressed)
        # 退出界面使用ALT+Q替换原来的ESC（Qt.Key_Escape），防误触
        self.esc_shortcut = QShortcut(QKeySequence(Qt.AltModifier + Qt.Key_Q), self)
        self.esc_shortcut.activated.connect(self.on_escape_pressed)
        # 拖拽模式使用ALT快捷键
        self.esc_shortcut = QShortcut(QKeySequence(Qt.AltModifier + Qt.Key_A), self)
        self.esc_shortcut.activated.connect(self.on_alt_pressed)
        # 极简模式和EXIF信息切换使用ALT+I快捷键
        self.esc_shortcut = QShortcut(QKeySequence(Qt.AltModifier + Qt.Key_I), self)
        self.esc_shortcut.activated.connect(self.show_exif)
        # 添加快捷键 F1，打开MIPI RAW文件转换为JPG文件工具
        self.f1_shortcut = QShortcut(QKeySequence(Qt.Key_F1), self)
        self.f1_shortcut.activated.connect(self.on_f1_pressed)
        # 添加快捷键，打开批量执行命令工具
        self.f2_shortcut = QShortcut(QKeySequence(Qt.Key_F2), self)
        self.f2_shortcut.activated.connect(self.on_f2_pressed)
        # 添加快捷键，打开批量重命名工具
        self.f4_shortcut = QShortcut(QKeySequence(Qt.Key_F4), self)
        self.f4_shortcut.activated.connect(self.on_f4_pressed)
        # 添加快捷键 F5,刷新表格
        self.f5_shortcut = QShortcut(QKeySequence(Qt.Key_F5), self)
        self.f5_shortcut.activated.connect(self.on_f5_pressed)
        # 添加快捷键 i 切换极简模式
        self.p_shortcut = QShortcut(QKeySequence('i'), self)
        self.p_shortcut.activated.connect(self.on_i_pressed)
        # 添加快捷键 Ctrl+i 打开图片处理窗口
        self.i_shortcut = QShortcut(QKeySequence('l'), self)
        self.i_shortcut.activated.connect(self.on_l_pressed)
        # 添加快捷键 Ctrl+h 打开帮助信息显示
        self.h_shortcut = QShortcut(QKeySequence(Qt.ControlModifier + Qt.Key_H), self)
        self.h_shortcut.activated.connect(self.on_ctrl_h_pressed)
        # 添加快捷键 Ctrl+f 打开图片搜索工具
        self.f_shortcut = QShortcut(QKeySequence(Qt.ControlModifier + Qt.Key_F), self)
        self.f_shortcut.activated.connect(self.on_ctrl_f_pressed)
        # 添加快捷键 C,复制选中的文件路径
        self.c_shortcut = QShortcut(QKeySequence('c'), self)
        self.c_shortcut.activated.connect(self.copy_selected_file_path)
        # 添加快捷键 Ctrl+c 复制选中的文件
        self.c_shortcut = QShortcut(QKeySequence(Qt.ControlModifier + Qt.Key_C), self)
        self.c_shortcut.activated.connect(self.copy_selected_files)
        # 添加快捷键 D 从列表中删除选中的文件
        self.d_shortcut = QShortcut(QKeySequence('d'), self)
        self.d_shortcut.activated.connect(self.delete_from_list)
        # 添加快捷键 Ctrl+d 从原文件删除选中的文件
        self.d_shortcut = QShortcut(QKeySequence(Qt.ControlModifier + Qt.Key_D), self)
        self.d_shortcut.activated.connect(self.delete_from_file)
        # 添加快捷键 Z 压缩选中的文件
        self.z_shortcut = QShortcut(QKeySequence('z'), self)
        self.z_shortcut.activated.connect(self.compress_selected_files)
        # 添加快捷键 T 打开--局域网传输工具--，改为截图功能
        self.z_shortcut = QShortcut(QKeySequence('t'), self)
        self.z_shortcut.activated.connect(self.screen_shot_tool)
        # 添加快捷键 X 打开图片体积压缩工具
        self.z_shortcut = QShortcut(QKeySequence('x'), self)
        self.z_shortcut.activated.connect(self.jpgc_tool) 
        # 添加快捷键 W 打开资源管理器
        self.z_shortcut = QShortcut(QKeySequence('w'), self)
        self.z_shortcut.activated.connect(self.reveal_in_explorer) 

        """2. 槽函数连接事件"""
        # 连接左侧按钮槽函数
        self.Left_QTreeView.clicked.connect(self.update_combobox)        # 点击左侧文件浏览器时的连接事件
        
        # 连接右侧按钮槽函数
        self.RT_QComboBox.lineEdit().returnPressed.connect(self.input_enter_action) # 用户在地址栏输入文件路径后按下回车的动作反馈
        self.RT_QComboBox0.activated.connect(self.handleComboBox0Pressed)           # 点击（显示图片视频所有文件）下拉框选项时的处理事件
        self.RT_QComboBox1.view().pressed.connect(self.handleComboBoxPressed)       # 处理复选框选项被按下时的事件
        self.RT_QComboBox1.activated.connect(self.updateComboBox1Text)              # 更新显示文本
        self.RT_QComboBox2.activated.connect(self.handle_sort_option)               # 点击下拉框选项时，更新右侧表格
        self.RT_QComboBox3.activated.connect(self.handle_theme_selection)           # 点击下拉框选项时，更新主题
        self.RT_QPushButton3.clicked.connect(self.clear_combox)                     # 清除地址栏
        self.RT_QPushButton5.clicked.connect(self.compare)                          # 打开看图工具

        # 表格选择变化时，更新状态栏和预览区域显示
        self.RB_QTableWidget0.itemSelectionChanged.connect(self.handle_table_selection)
        
        # 底部状态栏按钮连接函数
        self.statusbar_button1.clicked.connect(self.setting)   # 🔆设置按钮槽函数
        self.statusbar_button2.clicked.connect(self.update)    # 🚀版本按钮槽函数
        

    """
    左侧信号槽函数
    """
    def show_file_visibility(self):
        """设置左侧文件浏览器的显示"""
        self.left_tree_file_display = not self.left_tree_file_display

        if not self.left_tree_file_display:
            self.file_system_model.setFilter(QDir.NoDot | QDir.NoDotDot | QDir.AllDirs)    # 使用QDir的过滤器,只显示文件夹  
        else:
            self.file_system_model.setFilter(QDir.NoDot | QDir.NoDotDot |QDir.AllEntries)  # 显示所有文件和文件夹


    def open_aebox(self,selected_option):
        # 创建并显示自定义对话框,传入图片列表
        try:
            # 初始化自定义的对话框
            dialog = Qualcom_Dialog(selected_option)

            # 设置窗口标题
            dialog.setWindowTitle("打开AEBOX工具")
            # 设置窗口大小
            dialog.setFixedSize(1200, 100)
            # 隐藏对话框的按钮
            dialog.button_box.setVisible(False)
            dialog.label1.setVisible(False)
            dialog.text_input1.setVisible(False)
            dialog.load_button.setVisible(False)
            dialog.status_button1.setVisible(False)
            dialog.label3.setVisible(False)
            dialog.text_input3.setVisible(False)
            dialog.load_images_button.setVisible(False)
            dialog.status_button3.setVisible(False)
            
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:

                # 执行命名
                dict_info = dialog.get_data()
                # print(f"用户加载的路径信息: {dict_info}")

                qualcom_path = dict_info.get("Qualcom工具路径","")
                images_path = dict_info.get("Image文件夹路径","")
                metadata_path = os.path.join(os.path.dirname(__file__), "resource", "tools", "metadata.exe")

                # 拼接参数命令字符串
                if qualcom_path and images_path and os.path.exists(metadata_path) and os.path.exists(images_path) and os.path.exists(qualcom_path):
                    command = f"{metadata_path} --chromatix \"{qualcom_path}\" --folder \"{images_path}\""

                    """
                    # 添加检查 图片文件夹目录下是否已存在xml文件，不存在则启动线程解析图片
                    # xml_exists = [f for f in os.listdir(images_path) if f.endswith('_new.xml')]

                    针对上面的代码，优化了检查'_new.xml'文件的逻辑:
                    1. os.listdir(images_path) 列出文件夹中的所有文件
                    2. os.path.exists(os.path.join(images_path, f)) 检查文件是否存在
                    3. any() 函数会在找到第一个符合条件的文件时立即返回 True, 避免不必要的遍历
                    """
                    # 检查图片文件夹目录下是否存在xml文件，不存在则启动线程解析图片
                    xml_exists = any(f for f in os.listdir(images_path) if f.endswith('_new.xml'))

                    # 创建线程，必须在主线程中连接信号
                    self.command_thread = CommandThread(command, images_path)
                    self.command_thread.finished.connect(self.on_command_finished)  # 连接信号
                    # self.command_thread.finished.connect(self.cleanup_thread)  # 连接清理槽

                    if not xml_exists:
                        self.command_thread.start()  # 启动线程
                        show_message_box("正在使用高通工具后台解析图片Exif信息...", "提示", 1000)
                    else:
                        show_message_box("已有xml文件, 无须解析图片", "提示", 1000)

                        # 解析xml文件将其保存到excel中去
                        save_excel_data(images_path)

            # 无论对话框是接受还是取消，都手动销毁对话框
            dialog.deleteLater()
            dialog = None

        except Exception as e:
            print(f"on_i_pressed()-error--处理i键按下事件失败: {e}")
            return


    def open_file_location(self, path):
        """在资源管理器中打开路径(适用于window系统)"""
        try:
            # 跨平台处理优化
            if sys.platform == 'win32':
                # 转换为Windows风格路径并处理特殊字符
                win_path = str(path).replace('/', '\\')
                # 自动添加双引号
                if ' ' in win_path:  
                    win_path = f'"{win_path}"'
                # 使用start命令更可靠
                command = f'start explorer /select,{win_path}'
                # 移除check=True参数避免误报
                subprocess.run(command, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                ...
        except Exception as e:
            show_message_box(f"[open_file_location]-->定位文件失败: {str(e)}", "错误", 2000)


    def copy_file_path(self, path): 
        """复制文件路径到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(path)

    def send_file_path_to_aebox(self, path): 
        """将文件夹路径发送到aebox"""
        try:

            if not check_process_running("aebox.exe"):
                show_message_box(f"未检测到aebox进程，请先手动打开aebox软件", "错误", 1000)

            # url编码
            image_path_url = urlencode_folder_path(path)
            if image_path_url:
                # 拼接文件夹
                image_path_url = f"http://127.0.0.1:8000/set_image_folder/{image_path_url}"
                # 发送请求通信到aebox
                response = get_api_data(url=image_path_url, timeout=3)
                if response:
                    print(f"[send_file_path_to_aebox]-->发送文件夹成功")
                else:
                    print(f"[send_file_path_to_aebox]-->发送文件夹失败")
            
        except Exception as e:
            show_message_box(f"[send_file_path_to_aebox]-->将文件夹路径发送到aebox失败: {str(e)}", "错误", 1000)


    def rename_file(self, path):
        """重命名文件/文件夹"""
        old_name = os.path.basename(path)
        dialog = QInputDialog(self)  # 创建自定义对话框实例
        dialog.setWindowTitle("重命名")
        dialog.setLabelText("请输入新名称:")
        dialog.setTextValue(old_name)
        
        # 设置对话框尺寸
        dialog.setMinimumSize(100, 100)  # 最小尺寸
        dialog.setFixedSize(500, 150)    # 固定尺寸（宽400px，高150px）
        
        # 设置输入框样式
        dialog.setStyleSheet("""
            QInputDialog {
                font-family: "JetBrains Mono";
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.textValue()
            if new_name and new_name != old_name:
                try:
                    new_path = os.path.join(os.path.dirname(path), new_name)
                    
                    # 检查新路径是否已存在
                    if os.path.exists(new_path):
                        show_message_box("名称已存在！", "错误", 500)
                        return
                    
                    # 执行重命名
                    os.rename(path, new_path)
                    
                    # 更新文件系统模型
                    self.file_system_model.setRootPath('')
                    self.Left_QTreeView.viewport().update()
                    
                except Exception as e:
                    show_message_box(f"重命名失败: {str(e)}", "错误", 1000)

    """
    右侧信号槽函数
    """
    def input_enter_action(self):
        # 地址栏输入后按下回车的反馈
        print("[input_enter_action]-->在地址栏按下回车/拖拽了文件进来,开始在左侧文浏览器中定位")  # 打印输入内容
        self.locate_in_tree_view()
        # 初始化同级文件夹下拉框选项
        self.RT_QComboBox1_init()
        # 更新右侧表格
        self.update_RB_QTableWidget0()

    def clear_combox(self):
        print("clear_combox()--清除按钮被点击")
        # 清空地址栏
        self.RT_QComboBox.clear()
        # 刷新右侧表格
        self.update_RB_QTableWidget0()
        # 手动清除图标缓存
        IconCache.clear_cache() 
        # 释放内存
        self.cleanup() 
        
    
    def execute_command(self):
        print("execute_command()--命令按钮被点击")
        try:    
            self.open_bat_tool()
        except Exception as e:
            print(f"execute_command()-error--打开批量执行命令工具失败: {e}")
            return

    def compare(self):
        print("compare()-对比按钮被点击--调用on_space_pressed()")
        self.on_space_pressed()


    def setting(self):
        print("setting()-设置按钮被点击--setting()")
        # 暂时调用关于信息，后续添加设置界面
        self.on_ctrl_h_pressed()
    

    def update(self):
        print("setting()-版本按钮被点击")
        check_update()

    @CC_TimeDec(tips="预更新版本")
    def pre_update(self):
        """预更新版本函数
        检查更新版本信息，并更新状态栏按钮，如果耗时超过2秒，则提示用户更新失败
        """
        try:
            # 预检查更新
            self.new_version_info = pre_check_update()
            
            if self.new_version_info:
                self.statusbar_button2.setText(f"🚀有新版本可用")  
                self.statusbar_button2.setToolTip(f"🚀新版本: {self.version_info}-->{self.new_version_info}")
                self.apply_theme() 
            else:
                self.statusbar_button2.setToolTip("已是最新版本")

        except Exception as e:
            print(f"pre_update()-error--预更新版本失败: {e}")
            return
        
    def show_exif(self):
        """打开Exif信息显示，类似快捷键CTRL+P功能  """
        print("show_exif()--打开Exif信息显示")

        try:
            # 获取当前选中的文件类型
            selected_option = self.RT_QComboBox0.currentText()
            if selected_option == "显示所有文件":
                show_message_box("该功能只在显示图片文件时有效！", "提示", 500)
                return
            elif selected_option == "显示视频文件":
                show_message_box("该功能只在显示图片文件时有效！", "提示", 500)
                return
            elif selected_option == "显示图片文件":
                self.simple_mode = not self.simple_mode 

            if self.simple_mode:
                show_message_box("关闭Exif信息显示", "提示", 500)
            else:
                show_message_box("打开Exif信息显示", "提示", 500)
        except Exception as e:
            print(f"show_exif()-error--打开Exif信息显示失败: {e}")
        finally:
            # 更新 RB_QTableWidget0 中的内容    
            self.update_RB_QTableWidget0() 

    
    def show_filter_rows(self, row_type):
        """显示筛选行"""
        print(f"show_filter_rows()--显示筛选行")
        try:
            # 按照传入的行类型，筛选行，显示需要的行
            if row_type == 'odd': # 传入奇数行，需要先选中偶数行，然后从列表中删除偶数行，最后显示奇数行
                self.filter_rows('even')
                self.delete_from_list()
            elif row_type == 'even': # 传入偶数行，需要先选中奇数行，然后从列表中删除奇数行，最后显示偶数行
                self.filter_rows('odd')
                self.delete_from_list()
            elif row_type == 'three_1': # 传入3选1，需要先选中3选2，然后从列表中删除3选2，最后显示3选1
                self.filter_rows('three_2')
                self.delete_from_list()
            elif row_type == 'three_2': # 传入3选2，需要先选中3选1，然后从列表中删除3选1，最后显示3选2
                self.filter_rows('three_1')
                self.delete_from_list()
            elif row_type == 'five_1': # 传入5选1，需要先选中5选4，然后从列表中删除5选4，最后显示5选1
                self.filter_rows('five_4')
                self.delete_from_list()
            else:
                show_message_box(f"未知筛选模式: {row_type}", "错误", 1000)
        except Exception as e:
            print(f"show_filter_rows()-error--显示筛选行失败: {e}")
            return

    def filter_rows(self, row_type):
        """批量选中指定模式行（使用类switch结构优化）"""
        
        # 清空选中状态
        self.RB_QTableWidget0.clearSelection()
        # 获取总行数
        total_rows = self.RB_QTableWidget0.rowCount()
        # 获取选中状态
        selection = self.RB_QTableWidget0.selectionModel()
        # 定义选择范围
        selection_range = QItemSelection()

        # 定义条件映射字典（实际行号从1开始计算）
        condition_map = {
            'odd': lambda r: (r + 1) % 2 == 1,  # 奇数行（1,3,5...）
            'even': lambda r: (r + 1) % 2 == 0,  # 偶数行（2,4,6...）
            'three_1': lambda r: (r + 1) % 3 == 1,  # 3选1（1,4,7...）
            'three_2': lambda r: (r + 1) % 3 != 0,  # 3选2（1,2,4,5...）
            'five_1': lambda r: (r + 1) % 5 == 1,  # 5选1（1,6,11...）
            'five_4': lambda r: (r + 1) % 5 != 1  # 5选4（2,3,4,5...）
        }

        # 获取判断条件
        condition = condition_map.get(row_type)
        if not condition:
            show_message_box(f"未知筛选模式: {row_type}", "错误", 1000)
            return

        try:
            # 批量选择符合条件的行
            for row in range(total_rows):
                if condition(row):
                    row_selection = QItemSelection(
                        self.RB_QTableWidget0.model().index(row, 0),
                        self.RB_QTableWidget0.model().index(row, self.RB_QTableWidget0.columnCount()-1)
                    )
                    selection_range.merge(row_selection, QItemSelectionModel.Select)

            # 应用选择并滚动定位
            if not selection_range.isEmpty():
                selection.select(selection_range, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                first_row = selection_range[0].top()
                self.RB_QTableWidget0.scrollTo(
                    self.RB_QTableWidget0.model().index(first_row, 0),
                    QAbstractItemView.PositionAtTop
                )

        except Exception as e:
            print(f"filter_rows()-error--批量选中指定模式行失败: {e}")
            return

    def jpg_lossless_rotator(self, para=''):
        """无损旋转图片"""
        print(f"jpg_lossless_rotator()-启动无损旋转图片任务:")
        try:
            # 取消当前的预加载任务
            self.cancel_preloading()

            # 构建jpegoptim的完整路径
            jpegr_path = os.path.join(os.path.dirname(__file__), "resource", 'tools', 'jpegr_lossless_rotator', 'jpegr.exe')
            if not os.path.exists(jpegr_path):
                show_message_box(f"jpegr.exe 不存在，请检查/tools/jpegr_lossless_rotator/", "提示", 1500)
                return
            
            # 获取选中的单元格中的路径
            files = self.copy_selected_file_path(0)
            # 获取选中的文件夹
            target_dir_paths = {os.path.dirname(file) for file in files}
            
            # 创建进度条
            if para == 'auto':
                progress_dialog = QProgressDialog("正在无损旋转图片...", "取消", 0, len(target_dir_paths), self)
            else:
                progress_dialog = QProgressDialog("正在无损旋转图片...", "取消", 0, len(files), self)
            progress_dialog.setWindowTitle("无损旋转进度")
            progress_dialog.setModal(True)
            progress_dialog.setFixedSize(450, 150)
            progress_dialog.setStyleSheet("QProgressDialog { border: none; }")
            progress_dialog.setVisible(False)

            if para == 'auto' and target_dir_paths:
                # 显示进度条,及时响应
                progress_dialog.setVisible(True)
                progress_dialog.setValue(0)
                QApplication.processEvents()
                
                for index_, dir_path in enumerate(target_dir_paths):

                    # 拼接参数命令字符串
                    command = f"{jpegr_path} -{para} -s \"{dir_path}\""

                    # 调用jpegoptim命令并捕获返回值
                    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    # 检查返回码
                    if result.returncode == 0:
                        progress_dialog.setValue(index_ + 1)
                        if progress_dialog.wasCanceled():
                            show_message_box(f"用户手动自动校准EXIF旋转信息操作, \n已自动校准前{index_+1}个文件夹,共{len(target_dir_paths)}张", "提示", 3000)
                            break  # 如果用户取消了操作，则退出循环
                    else:
                        print("自动校准EXIF旋转信息命令执行失败, 返回码:", result.returncode)
                        print("错误信息:", result.stderr)
                        return
                    
                # 添加进度条完成后的销毁逻辑
                progress_dialog.finished.connect(progress_dialog.deleteLater)  # 进度条完成时销毁    

                show_message_box("自动校准EXIF旋转信息成功!", "提示", 1500) 

                # 清图标缓存，刷新表格
                IconCache.clear_cache()

                # 更新表格
                self.update_RB_QTableWidget0() 

                # 退出当前函数
                return
                    
            # 进行无损旋转相关的调用
            if files:
                # 显示进度条,及时响应
                progress_dialog.setVisible(True)
                progress_dialog.setValue(0)
                QApplication.processEvents()

                for index, file in enumerate(files):
                    if not file.lower().endswith(self.IMAGE_FORMATS):
                        # show_message_box("文件格式错误，仅支持对图片文件进行无损旋转", "提示", 500)
                        # progress_dialog.setVisible(False)
                        print(f"函数jpg_lossless_rotator:{os.path.basename(file)}文件格式错误，仅支持对图片文件进行无损旋转")
                        progress_dialog.setValue(index + 1)
                        continue                    

                    # 拼接参数命令字符串
                    command = f"{jpegr_path} -{para} -s \"{file}\""

                    # 调用jpegoptim命令并捕获返回值
                    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    # 检查返回码
                    if result.returncode == 0:
                        # 更新进度条
                        progress_dialog.setValue(index + 1)
                        if progress_dialog.wasCanceled():
                            show_message_box(f"用户手动取消无损旋转操作，\n已无损旋转前{index+1}张图,共{len(files)}张", "提示", 3000)
                            break  # 如果用户取消了操作，则退出循环
                    else:
                        print("命令执行失败，返回码:", result.returncode)
                        print("错误信息:", result.stderr)
                        return
                
                # 添加进度条完成后的销毁逻辑
                progress_dialog.finished.connect(progress_dialog.deleteLater)  # 进度条完成时销毁                

                # 提示信息
                show_message_box(f"选中的{len(files)}张图片已完成无损旋转", "提示", 1000)

                # 清图标缓存，刷新表格
                IconCache.clear_cache()

                # 更新表格
                self.update_RB_QTableWidget0() 

        except subprocess.CalledProcessError as e:
            print(f"jpg_lossless_rotator()-error--无损旋转图片失败: {e}")
            return


    def get_selected_file_path(self):
            """或取所有选中的单元格的文件路径"""
            # 获取选中的项
            selected_items = self.RB_QTableWidget0.selectedItems() 
            if not selected_items:
                print("[get_selected_file_path]-->warning: 没有选中的项")
                return []
            
            # 用于存储所有选中的文件路径
            file_paths = []  
            try:
                for item in selected_items:
                    row = item.row()
                    col = item.column()

                    # 构建文件完整路径
                    file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0]      # 获取文件名
                    column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()        # 获取列名
                    current_directory = self.RT_QComboBox.currentText()                         # 获取当前选中的目录
                    full_path = str(Path(current_directory).parent / column_name / file_name)   # 构建文件完整路径

                    # 判断文件是否存在，存在则添加到列表
                    if os.path.isfile(full_path):
                        file_paths.append(full_path)  
                
                return file_paths

            except Exception as e:
                print(f"[get_selected_file_path]-->error: 获取文件路径失败: {e}")
                return []


    def copy_selected_file_path(self,flag=1):
        """复制所有选中的单元格的文件路径到系统粘贴板"""
        selected_items = self.RB_QTableWidget0.selectedItems()  # 获取选中的项
        if not selected_items:
            show_message_box("没有选中的项！", "提示", 500)
            return
        
        # 用于存储所有选中的文件路径
        file_paths = []  
        try:
            for item in selected_items:
                row = item.row()
                col = item.column()

                # 构建文件完整路径
                file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0]  # 获取文件名
                column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()  # 获取列名
                current_directory = self.RT_QComboBox.currentText()  # 获取当前选中的目录
                # 移除传统构建路径方法
                # full_path = os.path.join(os.path.dirname(current_directory), column_name, file_name)
                # 使用 Path 构建路径，自动处理跨平台的路径问题
                full_path = str(Path(current_directory).parent / column_name / file_name)

                if os.path.isfile(full_path):
                    file_paths.append(full_path)  # 添加有效文件路径到列表

            if file_paths:
                # 将文件路径复制到剪贴板，使用换行符分隔
                clipboard_text = "\n".join(file_paths)
                clipboard = QApplication.clipboard()
                clipboard.setText(clipboard_text)

                if flag:
                    show_message_box(f"{len(file_paths)} 个文件的路径已复制到剪贴板", "提示", 2000)
                else:
                    return file_paths
            else:
                show_message_box("没有有效的文件路径", "提示", 2000)

        except Exception as e:
            print(f"copy_selected_file_path()-error--复制文件路径失败: {e}")
            return


    def copy_selected_files(self):
        """复制选中的单元格对应的所有文件到系统剪贴板"""
        selected_items = self.RB_QTableWidget0.selectedItems()  # 获取选中的项
        if not selected_items:
            show_message_box("没有选中的项！", "提示", 500)
            return

        # 用于存储所有选中的文件路径
        file_paths = []  
        try:
            for item in selected_items:
                row = item.row()
                col = item.column()

                # 构建文件完整路径
                file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0]  # 获取文件名
                column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()  # 获取列名
                current_directory = self.RT_QComboBox.currentText()  # 获取当前选中的目录
                full_path = str(Path(current_directory).parent / column_name / file_name)

                if os.path.isfile(full_path):
                    file_paths.append(full_path)  # 添加有效文件路径到列表

            if file_paths:
                # 创建QMimeData对象
                mime_data = QMimeData()
                mime_data.setUrls([QUrl.fromLocalFile(path) for path in file_paths])  # 设置文件路径

                # 将QMimeData放入剪贴板
                clipboard = QApplication.clipboard()
                clipboard.setMimeData(mime_data)

                show_message_box(f"{len(file_paths)} 个文件已复制到剪贴板", "提示", 2000)
            else:
                show_message_box("没有有效的文件路径", "提示", 2000)

        except Exception as e:
            print(f"copy_selected_files()-error--复制文件失败: {e}")
            return


    def delete_from_list(self):
        """从列表中删除选中的单元格"""
        print(f"delete_from_list()-从列表中删除选中的单元格")

        selected_items = self.RB_QTableWidget0.selectedItems()
        if not selected_items:
            show_message_box("没有选中的项！", "提示", 500)
            return
        
        # 收集要删除的项目信息
        items_to_delete = []
        try:
            for item in selected_items:
                col = item.column()
                row = item.row()
                file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0].strip()
                
                # 获取对应列的文件夹名称
                column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()
                
                # 在paths_list中查找对应的索引
                col_idx = self.dirnames_list.index(column_name) if column_name in self.dirnames_list else -1
                
                if col_idx != -1 and row < len(self.paths_list[col_idx]):
                    # 验证文件名是否完全匹配
                    path_file_name = os.path.basename(self.paths_list[col_idx][row])
                    if file_name == path_file_name:
                        items_to_delete.append((col_idx, row))
            
            # 按列和行的逆序排序，确保删除时不会影响其他项的索引
            items_to_delete.sort(reverse=True)
            
            # 执行删除操作
            for col_idx, row in items_to_delete:
                if col_idx < len(self.files_list) and row < len(self.files_list[col_idx]):
                    del self.files_list[col_idx][row]
                    del self.paths_list[col_idx][row]
            
            # 更新表格显示
            self.update_RB_QTableWidget0_from_list(self.files_list, self.paths_list, self.dirnames_list)
    
        except Exception as e:
            print(f"delete_from_list()-error--删除失败: {e}")
            return

    def delete_from_file(self):
        """从源文件删除选中的单元格并删除原文件"""
        print(f"delete_from_file()-从原文件删除选中的单元格并删除原文件")

        selected_items = self.RB_QTableWidget0.selectedItems()  # 获取选中的项
        if not selected_items:
            show_message_box("没有选中的项！", "提示", 500)
            return
        # 收集要删除的文件路径
        file_paths_to_delete = []
        try:
            for item in selected_items:
                row = item.row()
                col = item.column()
                file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0]  # 获取文件名
                column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()  # 获取列名
                current_directory = self.RT_QComboBox.currentText()  # 获取当前选中的目录
                full_path = str(Path(current_directory).parent / column_name / file_name)

                if os.path.isfile(full_path):
                    file_paths_to_delete.append(full_path)  # 添加有效文件路径到列表

            # 删除文件
            for file_path in file_paths_to_delete:
                try:
                    os.remove(file_path)  # 删除文件
                except Exception as e:
                    show_message_box(f"删除文件失败: {file_path}, 错误: {e}", "提示", 500)

            # 删除表格中的行，可以直接更新表格
            self.update_RB_QTableWidget0()
            show_message_box(f"{len(file_paths_to_delete)} 个文件已从列表中删除并删除原文件", "提示", 1000)

        except Exception as e:
            print(f"delete_from_file()-error--删除失败: {e}")
            return


    def compress_selected_files(self):
        """压缩选中的文件并复制压缩包文件到剪贴板"""
        print("compress_selected_files()-启动压缩文件任务")
        try:
            selected_items = self.RB_QTableWidget0.selectedItems()
            if not selected_items:
                show_message_box("没有选中的项！", "提示", 500)
                return

            # 获取压缩包名称
            zip_name, ok = QInputDialog.getText(self, "输入压缩包名称", "请输入压缩包名称（不带扩展名）:")
            if not ok or not zip_name:
                show_message_box("未输入有效的名称！", "提示", 500)
                return

            # 准备要压缩的文件列表
            files_to_compress = []
            current_directory = self.RT_QComboBox.currentText()
        
            for item in selected_items:
                row = item.row()
                col = item.column()
                file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0]
                column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()
                full_path = str(Path(current_directory).parent / column_name / file_name)
                
                if os.path.isfile(full_path):
                    files_to_compress.append((full_path, file_name))

            if not files_to_compress:
                show_message_box("没有有效的文件可压缩", "提示", 500)
                return

            # 设置压缩包路径
            cache_dir = os.path.join(os.path.dirname(__file__), "cache")
            os.makedirs(cache_dir, exist_ok=True)
            self.zip_path = os.path.join(cache_dir, f"{zip_name}.zip")

            # 创建并启动压缩工作线程
            self.compress_worker = CompressWorker(files_to_compress, self.zip_path)
            
            # 连接信号
            self.compress_worker.signals.progress.connect(self.on_compress_progress)
            self.compress_worker.signals.finished.connect(self.on_compress_finished)
            self.compress_worker.signals.error.connect(self.on_compress_error)
            self.compress_worker.signals.cancel.connect(self.cancel_compression)

            # 显示进度窗口
            self.progress_dialog = ProgressDialog(self)
            self.progress_dialog.show()

            # 启动压缩任务
            self.threadpool.start(self.compress_worker)

        except Exception as e:
            print(f"compress_selected_files()-error--压缩失败: {e}")
            return  

    def screen_shot_tool(self):
        """截图功能"""
        try:
            WScreenshot.run() # 调用截图工具
        except Exception as e:
            show_message_box(f"启动截图功能失败: {str(e)}", "错误", 2000)

    def jpgc_tool(self):
        """打开图片体积压缩工具_升级版"""
        try:
            tools_dir = os.path.join(os.path.dirname(__file__), "resource", "tools")
            tcp_path = os.path.join(tools_dir, "JPGC.exe")
            
            if not os.path.isfile(tcp_path):
                show_message_box(f"未找到JPGC工具: {tcp_path}", "错误", 1500)
                return
                
            # 使用startfile保持窗口可见（适用于GUI程序）
            # 该方法只适用于window系统，其余系统（mac,linux）需要通过subprocess实现
            os.startfile(tcp_path)
            
        except Exception as e:
            show_message_box(f"启动JPGC工具失败: {str(e)}", "错误", 2000)


    def reveal_in_explorer(self):
        """在资源管理器中高亮定位选中的文件(适用于window系统)"""
        try:
            # 获取首个选中项（优化性能，避免处理多选）
            if not (selected := self.RB_QTableWidget0.selectedItems()):
                show_message_box("请先选择要定位的文件", "提示", 1000)
                return

            # 缓存路径对象避免重复计算
            current_dir = Path(self.RT_QComboBox.currentText()).resolve()
            item = selected[0]
            
            # 直接获取列名（避免多次调用horizontalHeaderItem）
            if not (col_name := self.RB_QTableWidget0.horizontalHeaderItem(item.column()).text()):
                raise ValueError("无效的列名")
            col_name = self.RB_QTableWidget0.horizontalHeaderItem(item.column()).text()

            # 强化路径处理，移除前后空格
            file_name = item.text().split('\n', 1)[0].strip() 
            full_path = (current_dir.parent / col_name / file_name).resolve()

            if not full_path.exists():
                show_message_box(f"文件不存在: {full_path.name}", "错误", 1500)
                return

            # 跨平台处理优化
            if sys.platform == 'win32':
                # 转换为Windows风格路径并处理特殊字符
                win_path = str(full_path).replace('/', '\\')
                if ' ' in win_path:  # 自动添加双引号
                    win_path = f'"{win_path}"'
                # 使用start命令更可靠
                command = f'start explorer /select,{win_path}'
                # 移除check=True参数避免误报
                subprocess.run(command, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

            else: # ... 可代替 pass ，是一个单例，也是numpy的语法糖
                ...
        except Exception as e:
            show_message_box(f"定位文件失败: {str(e)}", "错误", 2000)


    def on_compress_progress(self, current, total):
        """处理压缩进度"""
        progress_value = int((current / total) * 100)  # 计算进度百分比
        self.progress_dialog.update_progress(progress_value)
        self.progress_dialog.set_message(f"显示详情：正在压缩文件... {current}/{total}")

    def cancel_compression(self):
        """取消压缩任务"""
        if self.compress_worker:
            self.compress_worker.cancel()  
        self.progress_dialog.close()  
        show_message_box("压缩已取消", "提示", 500)

        # 若是压缩取消，则删除缓存文件中的zip文件
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        if os.path.exists(cache_dir):
            # 强制删除缓存文件中的zip文件
            force_delete_folder(cache_dir, '.zip')

    def on_compress_finished(self, zip_path):
        """处理压缩完成"""
        self.progress_dialog.close()
        # 将压缩包复制到剪贴板
        mime_data = QMimeData()
        url = QUrl.fromLocalFile(zip_path)
        mime_data.setUrls([url])
        QApplication.clipboard().setMimeData(mime_data)
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"🔉: 压缩完成🍃")
        show_message_box(f"文件已压缩为: {zip_path} 并复制到剪贴板", "提示", 500)

    def on_compress_error(self, error_msg):
        """处理压缩错误"""
        self.progress_dialog.close()  
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"🔉: 压缩出错🍃")
        show_message_box(error_msg, "错误", 2000)


    """
    自定义功能函数区域：
    拖拽功能函数 self.dragEnterEvent(), self.dropEvent()
    左侧文件浏览器与地址栏联动功能函数 self.locate_in_tree_view, selfupdate_combobox
    右侧表格显示功能函数 self.update_RB_QTableWidget0()
    """


    def dragEnterEvent(self, event):
        # 如果拖入的是文件夹，则接受拖拽
        if event.mimeData().hasUrls():

            event.accept()

    def dropEvent(self, event):
        # 获取拖放的文件夹路径,并插入在首行，方便地查看最近添加的文件夹路径
        for url in event.mimeData().urls():
            folder_path = url.toLocalFile()
            if os.path.isdir(folder_path):  
                self.RT_QComboBox.insertItem(0, folder_path)
                self.RT_QComboBox.setCurrentText(folder_path)
                # 定位到左侧文件浏览器中
                self.locate_in_tree_view()
                # 将同级文件夹添加到 RT_QComboBox1 中
                self.RT_QComboBox1_init() 
                # 更新右侧RB_QTableWidget0表格
                self.update_RB_QTableWidget0() 
                break  
        
    # 点击左侧文件浏览器时的功能函数
    def update_combobox(self, index):
        """左侧文件浏览器点击定位更新右侧combobox函数"""
        print("update_combobox函数: ")

        # 清空历史的已选择
        self.statusbar_label.setText(f"[0]已选择")

        # 更新左侧文件浏览器中的预览区域显示
        if True:
            # 清空旧预览内容
            self.clear_preview_layout()
            # 显示预览信息
            self.show_preview_error("预览区域")

        # 获取左侧文件浏览器中当前点击的文件夹路径，并显示在地址栏
        current_path = self.file_system_model.filePath(index)
        if os.path.isdir(current_path):
            if self.RT_QComboBox.findText(current_path) == -1:
                self.RT_QComboBox.addItem(current_path)
            self.RT_QComboBox.setCurrentText(current_path)
            print(f"点击了左侧文件，该文件夹已更新到地址栏中: {current_path}")

        # 禁用左侧文件浏览器中的滚动条自动滚动
        self.Left_QTreeView.setAutoScroll(False)

        # 将同级文件夹添加到 RT_QComboBox1 中
        self.RT_QComboBox1_init()      
        # 更新右侧RB_QTableWidget0表格
        self.update_RB_QTableWidget0() 
        
    # 在左侧文件浏览器中定位地址栏(RT_QComboBox)中当前显示的目录
    def locate_in_tree_view(self):
        """左侧文件浏览器点击定位函数"""
        print("[locate_in_tree_view]-->在左侧文件浏览器中定位地址栏路径")
        try:
            current_directory = self.RT_QComboBox.currentText()
            # 检查路径是否有效
            if not os.path.exists(current_directory): 
                print("[locate_in_tree_view]-->地址栏路径不存在")
                return  
            # 获取当前目录的索引
            index = self.file_system_model.index(current_directory)  
            # 检查索引是否有效
            if index.isValid():
                # 设置当前索引
                self.Left_QTreeView.setCurrentIndex(index)    
                # 展开该目录
                self.Left_QTreeView.setExpanded(index, True)  
                # 滚动到该项，确保垂直方向居中
                self.Left_QTreeView.scrollTo(index, QAbstractItemView.PositionAtCenter)
                
                # 手动设置水平方向进度条
                self.Left_QTreeView.horizontalScrollBar().setValue(0)
            
            else:
                print("[locate_in_tree_view]-->索引无效-无法定位")

        except Exception as e:
            print(f"[locate_in_tree_view]-->定位失败: {e}")
            return


    def update_RB_QTableWidget0_from_list(self, file_infos_list, file_paths, dir_name_list):
        """从当前列表中更新表格，适配从当前列表删除文件功能"""
        print(f"[update_RB_QTableWidget0_from_list]-->从当前列表中更新表格")
        try:    
            # 取消当前的预加载任务
            self.cancel_preloading()
            # 清空表格和缓存
            self.RB_QTableWidget0.clear()
            self.RB_QTableWidget0.setRowCount(0)
            self.RB_QTableWidget0.setColumnCount(0)
            self.image_index_max = [] # 清空图片列有效行最大值 

            # 先初始化表格结构和内容，不加载图标,并获取图片列有效行最大值
            self.image_index_max = self.init_table_structure(file_infos_list, dir_name_list)

            # 对file_paths进行转置,实现加载图标按行加载,使用列表推导式
            file_name_paths = [path for column in zip_longest(*file_paths, fillvalue=None) for path in column if path is not None]

            if file_name_paths:  # 确保有文件路径才开始预加载
                self.start_image_preloading(file_name_paths)

        except Exception as e:
            print(f"[update_RB_QTableWidget0_from_list]-->error--从当前列表中更新表格任务失败: {e}")


    @CC_TimeDec(tips="更新右侧表格功能函数",show_time=False)
    def update_RB_QTableWidget0(self):
        """更新右侧表格功能函数"""
        
        # 取消当前的预加载任务
        self.cancel_preloading()

        # 清空表格和缓存
        self.RB_QTableWidget0.clear()
        self.RB_QTableWidget0.setRowCount(0)
        self.RB_QTableWidget0.setColumnCount(0)
        self.image_index_max = [] # 清空图片列有效行最大值  
        
        # 收集文件名基本信息以及文件路径，并将相关信息初始化为类中全局变量
        file_infos_list, file_paths, dir_name_list = self.collect_file_paths()
        self.files_list = file_infos_list      # 初始化文件名及基本信息列表
        self.paths_list = file_paths           # 初始化文件路径列表
        self.dirnames_list = dir_name_list     # 初始化选中的同级文件夹列表

        # 先初始化表格结构和内容，不加载图标,并获取图片列有效行最大值
        self.image_index_max = self.init_table_structure(file_infos_list, dir_name_list)       

        # 对file_paths进行转置,实现加载图标按行加载，并初始化预加载图标线程前的问价排列列表
        file_name_paths = [path for column in zip_longest(*file_paths, fillvalue=None) for path in column if path is not None]
        self.preloading_file_name_paths = file_name_paths 

        # 开始预加载图标    
        if file_name_paths:  # 确保有文件路径才开始预加载
            self.start_image_preloading(file_name_paths)


    def init_table_structure(self, file_name_list, dir_name_list):
        """初始化表格结构和内容，不包含图标"""
        try:
            # 设置表格的列数
            self.RB_QTableWidget0.setColumnCount(len(file_name_list))
            # 设置列标题为当前选中的文件夹名，设置列名为文件夹名
            self.RB_QTableWidget0.setHorizontalHeaderLabels(dir_name_list)  

            # 判断是否存在文件
            if not file_name_list or not file_name_list[0]:
                return []  
            
            # 设置表格的行数
            max_cols = max(len(row) for row in file_name_list) 
            self.RB_QTableWidget0.setRowCount(max_cols)  
            self.RB_QTableWidget0.setIconSize(QSize(48, 48))  

            pic_num_list = [] # 用于记录每列的图片数量
            flag_ = 0 # 用于记录是否需要设置固定行高
            # 填充 QTableWidget,先填充文件名称，后填充图标(用多线程的方式后加载图标)
            for col_index, row in enumerate(file_name_list):
                pic_num_list.append(len(row))
                for row_index, value in enumerate(row):
                    if value[4][0] is None and value[4][1] is None:
                        resolution = " "
                    else:
                        resolution = f"{value[4][0]}x{value[4][1]}"
                    if value[5] is None:
                        exposure_time = " "
                    else:
                        exposure_time = value[5]
                    if value[6] is None:
                        iso = " "
                    else: 
                        iso = value[6]
                    # 文件名称、分辨率、曝光时间、ISO
                    if resolution == " " and exposure_time == " " and iso == " ": 
                        item_text = value[0]
                        flag_ = 0 
                    else:
                        item_text = value[0] + "\n" + f"{resolution} {exposure_time} {iso}"
                        flag_ = 1 # 设置flag_为1，设置行高
                    item = QTableWidgetItem(item_text)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                    self.RB_QTableWidget0.setItem(row_index, col_index, item)  # 设置单元格项
                ###############################    列  ,     行   ，内容    ######################

            # 设置单元格行高固定为60,如果flag_为0，则不设置行高
            if flag_:
                for row in range(self.RB_QTableWidget0.rowCount()):
                    self.RB_QTableWidget0.setRowHeight(row, 60)
            else:
                for row in range(self.RB_QTableWidget0.rowCount()):
                    self.RB_QTableWidget0.setRowHeight(row, 52)

            # # 更新标签显示  
            self.statusbar_label0.setText(f"📢:当前选中的文件夹中包含 {pic_num_list} 张图")  

            return pic_num_list
        except Exception as e:
            print(f"[init_table_structure]-->初始化表格结构和内容失败: {e}")
            return []

        
    def collect_file_paths(self):
        """收集需要显示的文件路径"""
        # 初始化列表
        file_infos = []  # 文件名列表
        file_paths = []  # 文件路径列表
        dir_name_list = [] # 文件夹名列表

        try:
            # 获取复选框中选择的文件夹路径列表
            selected_folders = self.model.getCheckedItems()  # 获取选中的文件夹
            current_directory = self.RT_QComboBox.currentText() # 当前选中的文件夹目录 
            parent_directory = os.path.dirname(current_directory)  # 获取父目录
            
            # 构建所有需要显示的文件夹路径
            selected_folders_path = [os.path.join(parent_directory, path) for path in selected_folders]
            selected_folders_path.insert(0, current_directory)  # 将当前选中的文件夹路径插入到列表的最前面
            
            # 检测当前文件夹路径是否包含文件，没有则剔除该文件夹，修复多级空文件夹显示错乱的bug
            selected_option = self.RT_QComboBox0.currentText()
            if selected_option == "显示图片文件":
                selected_folders_path = [folder for folder in selected_folders_path 
                                    if os.path.exists(folder) and any(
                                        entry.name.lower().endswith(self.IMAGE_FORMATS) 
                                        for entry in os.scandir(folder) if entry.is_file()
                                    )]
            elif selected_option == "显示视频文件":
                selected_folders_path = [folder for folder in selected_folders_path 
                                    if os.path.exists(folder) and any(
                                        entry.name.lower().endswith(self.VIDEO_FORMATS) 
                                        for entry in os.scandir(folder) if entry.is_file()
                                    )]
            else: # 显示所有文件
                selected_folders_path = [folder for folder in selected_folders_path 
                                    if os.path.exists(folder) and any(os.scandir(folder))]

            # 获取文件夹名列表
            dir_name_list = [os.path.basename(dir_name) for dir_name in selected_folders_path]
            
            # 处理每个文件夹
            for folder in selected_folders_path:
                if not os.path.exists(folder):
                    continue
                    
                file_name_list, file_path_list = self.filter_files(folder)
                if file_name_list:  # 只添加非空列表
                    file_infos.append(file_name_list)
                    file_paths.append(file_path_list)
                
            return file_infos, file_paths, dir_name_list
            
        except Exception as e:
            print(f"collect_file_paths函数_收集文件路径失败: {e}")
            return [], [], []
        
    def filter_files(self, folder):
        """根据选项过滤文件"""
        files_and_dirs_with_mtime = [] 
        selected_option = self.RT_QComboBox0.currentText()
        sort_option = self.RT_QComboBox2.currentText()

        # 使用 os.scandir() 获取文件夹中的条目
        with os.scandir(folder) as entries:
            # 使用列表推导式和 DirEntry 对象的 stat() 方法获取文件元组，比os.listdir()更高效,性能更高
            for entry in entries:
                if entry.is_file():
                    if selected_option == "显示图片文件":
                        if entry.name.lower().endswith(self.IMAGE_FORMATS):
                            # 非极简模式下通过PIL获取图片的宽度、高度、曝光时间、ISO
                            if not self.simple_mode: 
                                with ImageProcessor(entry.path) as img:
                                    width, height, exposure_time, iso = img.width, img.height, img.exposure_time, img.iso
                            # 获取图片的分辨率，极简模式下不获取图片的宽度、高度、曝光时间、ISO
                            else:   
                                width, height, exposure_time, iso = None, None, None, None
                            # 文件名称、创建时间、修改时间、文件大小、分辨率、曝光时间、ISO、文件路径
                            files_and_dirs_with_mtime.append((entry.name, entry.stat().st_ctime, entry.stat().st_mtime, entry.stat().st_size,
                                                           (width, height), exposure_time, iso, entry.path))
                    elif selected_option == "显示视频文件":
                        if entry.name.lower().endswith(self.VIDEO_FORMATS):     
                            # 文件名称、创建时间、修改时间、文件大小、分辨率、曝光时间、ISO、文件路径
                            files_and_dirs_with_mtime.append((entry.name, entry.stat().st_ctime, entry.stat().st_mtime, entry.stat().st_size,
                                                           (None, None), None, None, entry.path))
                    elif selected_option == "显示所有文件":
                            # 文件名称、创建时间、修改时间、文件大小、分辨率、曝光时间、ISO、文件路径
                            files_and_dirs_with_mtime.append((entry.name, entry.stat().st_ctime, entry.stat().st_mtime, entry.stat().st_size,
                                                           (None, None), None, None, entry.path))
                    else: # 没有选择任何选项就跳过
                        print("filter_files函数:selected_option没有选择任何选项,跳过")
                        continue

        # 使用sort_by_custom函数进行排序
        files_and_dirs_with_mtime = sort_by_custom(sort_option, files_and_dirs_with_mtime, self.simple_mode, selected_option)

        # 获取文件路径列表，files_and_dirs_with_mtime的最后一列
        file_paths = [item[-1] for item in files_and_dirs_with_mtime]

        return files_and_dirs_with_mtime, file_paths

        
    def start_image_preloading(self, file_paths):
        """开始预加载图片"""
        if self.preloading:
            print("[start_image_preloading]-->预加载已启动, 跳过")
            return
        
        # 设置预加载状态
        self.preloading = True
        print("[start_image_preloading]-->开始预加载图标, 启动预加载线程")

        self.start_time_image_preloading = time.time()
        
        try:
            # 创建新的预加载器
            self.current_preloader = ImagePreloader(file_paths)
            self.current_preloader.signals.progress.connect(self.update_preload_progress)
            self.current_preloader.signals.batch_loaded.connect(self.on_batch_loaded)
            self.current_preloader.signals.finished.connect(self.on_preload_finished)
            self.current_preloader.signals.error.connect(self.on_preload_error)
            
            # 启动预加载
            self.threadpool.start(self.current_preloader)
        except Exception as e:
            print(f"[start_image_preloading]-->开始预加载图标, 启动预加载线程失败: {e}")

    @CC_TimeDec(tips="取消当前预加载任务", show_time=False)
    def cancel_preloading(self):
        """取消当前预加载任务"""
        try:
            if self.current_preloader and self.preloading:
                self.current_preloader._stop = True  # 使用 _stop 属性而不是 stop() 方法
                self.preloading = False
                self.current_preloader = None
                
        except Exception as e:
            print(f"取消预加载任务失败: {e}")

    def on_batch_loaded(self, batch):
        """处理批量加载完成的图标"""
        for path, icon in batch:
            # 更新表格中对应的图标
            self.update_table_icon(path, icon)
            
    def update_table_icon(self, file_path, icon):
        """更新表格中的指定图标
        通过先查找行来优化图标更新效率
        """
        filename = os.path.basename(file_path)
        folder = os.path.basename(os.path.dirname(file_path))
        
        # 先在每一行中查找文件名
        for row in range(self.RB_QTableWidget0.rowCount()):
            # 遍历每一列查找匹配的文件夹
            for col in range(self.RB_QTableWidget0.columnCount()):
                header = self.RB_QTableWidget0.horizontalHeaderItem(col)
                item = self.RB_QTableWidget0.item(row, col)
                
                if (header and header.text() == folder and 
                    item and item.text().split('\n')[0] == filename):
                    if bool(icon):
                        item.setIcon(icon)
                    return  # 找到并更新后直接返回

    def update_preload_progress(self, current, total):
        """处理预加载进度"""
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"🔉: 图标加载进度...{current}/{total}🍃")
        
    def on_preload_finished(self):
        """处理预加载完成"""
        # 打印提示信息
        print(f"[on_preload_finished]-->所有图标预加载完成,耗时：{time.time()-self.start_time_image_preloading:.2f}秒")
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"🔉: 图标已全部加载-^-耗时：{time.time()-self.start_time_image_preloading:.2f}秒🍃")
        gc.collect()
        
    def on_preload_error(self, error):
        """处理预加载错误"""
        print(f"[on_preload_error]-->图标预加载错误: {error}")

    def RT_QComboBox1_init(self):
        """自定义RT_QComboBox1, 添加复选框选项"""
        print("[RT_QComboBox1_init]-->开始添加地址栏文件夹的同级文件夹到下拉复选框中")
        try:
            # 获取地址栏当前路径    
            current_directory = self.RT_QComboBox.currentText()
            # 检查路径是否有效
            if not os.path.exists(current_directory): 
                print("[RT_QComboBox1_init]-->地址栏路径不存在")
                return  
            # 获取父目录中的文件夹列表
            sibling_folders = self.getSiblingFolders(current_directory)  
            # 使用文件夹列表和父目录初始化模型
            self.model = CheckBoxListModel(sibling_folders)  
            # 绑定模型到 QComboBox
            self.RT_QComboBox1.setModel(self.model)  
            # 设置自定义委托
            self.RT_QComboBox1.setItemDelegate(CheckBoxDelegate())  
            # 禁用右键菜单
            self.RT_QComboBox1.setContextMenuPolicy(Qt.NoContextMenu)  
        except Exception as e:
            print(f"[RT_QComboBox1_init]-->初始化失败: {e}")

    def handleComboBoxPressed(self, index):
        """处理复选框选项被按下时的事件。"""
        print("[handleComboBoxPressed]-->更新复选框状态")
        try:
            if not index.isValid():
                print("[handleComboBoxPressed]-->下拉复选框点击无效")
                return
            self.model.setChecked(index)  # 更新复选框的状态
        except Exception as e:
            print(f"[handleComboBoxPressed]-->更新复选框状态失败: {e}")

    def handleComboBox0Pressed(self):
        """处理（显示图片视频所有文件）下拉框选项被按下时的事件。"""
        print("[handleComboBox0Pressed]-->更新（显示图片视频所有文件）下拉框状态")
        self.update_RB_QTableWidget0() # 更新右侧RB_QTableWidget0表格

    def updateComboBox1Text(self):
        """更新 RT_QComboBox1 的显示文本。"""    
        print("[updateComboBox1Text]-->更新显示文本")
        try:
            selected_folders = self.model.getCheckedItems()  # 获取选中的文件夹
            current_text = '; '.join(selected_folders) if selected_folders else "(请选择)"
            self.RT_QComboBox1.setCurrentText(current_text)  # 更新 ComboBox 中的内容
            # 更新表格内容
            self.update_RB_QTableWidget0()  
        except Exception as e:
            print(f"[updateComboBox1Text]-->更新显示文本失败: {e}")

    def getSiblingFolders(self, folder_path):
        """获取指定文件夹的同级文件夹列表。"""
        print(f"[getSiblingFolders]-->获取{folder_path}的同级文件夹列表")
        try:
            parent_folder = os.path.dirname(folder_path)  # 获取父文件夹路径
            return [
                name for name in os.listdir(parent_folder)
                    if os.path.isdir(os.path.join(parent_folder, name)) and name != os.path.basename(folder_path)  # 过滤出同级文件夹，不包括当前选择的文件夹
                ]
        except Exception as e:
            print(f"[getSiblingFolders]-->获取同级文件夹列表失败: {e}")
            return []

    # @CC_TimeDec(tips="suc")
    def handle_table_selection(self):
        """处理表格选中事件（新增预览功能）"""
        try:
            # 看图子界面更新图片时忽略表格选中事件
            if self.compare_window and self.compare_window.is_updating:
                # 若预览区域显示的是ImageViewer，清空旧预览内容, 显示label
                if (self.verticalLayout_left_2.itemAt(0) and self.verticalLayout_left_2.itemAt(0).widget() 
                    and type(self.verticalLayout_left_2.itemAt(0).widget()).__name__ == "ImageViewer"):
                    self.clear_preview_layout()
                    self.show_preview_error("预览区域")
                return
            
            # 获取选中的文件路径列表并检查是否有效
            if not (file_paths := self.get_selected_file_path()):
                print("[handle_table_selection]-->warning: 没有获取到文件路径")
                return
            
            # 清空旧预览内容，只需要第一个选中文件的路径
            self.clear_preview_layout() 
            preview_path = file_paths[0]

            # 根据文件类型创建预览
            if preview_path.lower().endswith(tuple(self.IMAGE_FORMATS)):
                # 处理HEIC格式图片
                if preview_path.lower().endswith(tuple(".heic")):
                    if (new_path := extract_jpg_from_heic(preview_path)):
                        # 创建图片预览
                        self.create_image_preview(new_path)
                    else:
                        # 显示错误信息
                        self.show_preview_error("提取HEIC图片失败")
                # 处理其他格式图片
                else:
                    # 创建图片预览
                    self.create_image_preview(preview_path)

            elif preview_path.lower().endswith(tuple(self.VIDEO_FORMATS)):
                # 提取视频文件首帧图，并且创建预览图
                if video_path := extract_video_first_frame(preview_path):
                    # 创建图片预览   
                    self.create_image_preview(video_path)     
                else:
                    # 显示错误信息
                    self.show_preview_error("视频文件预览失败")

            else:
                # 显示错误信息
                self.show_preview_error("不支持预览的文件类型")
                
            # 更新状态栏显示选中数量
            self.statusbar_label.setText(f"[{len(file_paths)}]已选择")

        except Exception as e:
            print(f"[handle_table_selection]-->处理表格选中事件失败: {e}")


    def clear_preview_layout(self):
        """清空预览区域"""
        try:
            while self.verticalLayout_left_2.count():
                item = self.verticalLayout_left_2.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        except Exception as e:
            print(f"[clear_preview_layout]-->清空预览区域失败: {e}")

    # @CC_TimeDec(tips="suc")
    def create_image_preview(self, path):
        """创建图片预览"""
        try:
            # 清空旧预览内容
            self.clear_preview_layout()
            # 创建 ImageViewer 实例
            self.image_viewer = ImageViewer(self.Left_QFrame)
            # 加载图片
            self.image_viewer.load_image(path)
            # 添加 ImageViewer 到 layout
            self.verticalLayout_left_2.addWidget(self.image_viewer)
            # 调整 self.Left_QFrame 的尺寸策略
            self.Left_QFrame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        except Exception as e:
            print(f"[create_image_preview]-->图片预览失败: {e}")
            self.show_preview_error("图片预览不可用")


    def show_preview_error(self, message):
        """显示预览错误信息"""
        # 显示错误信息
        error_label = QLabel(message)
        error_label.setStyleSheet("color: white;")
        error_label.setFont(self.custom_font_jetbrains)
        error_label.setAlignment(Qt.AlignCenter)
        self.verticalLayout_left_2.addWidget(error_label)

    def handle_sort_option(self):
        """处理排序选项"""
        print("[handle_sort_option]-->处理排序选项")
        try:
            sort_option = self.RT_QComboBox2.currentText()
            if self.simple_mode:
                if sort_option == "按曝光时间排序" or sort_option == "按曝光时间逆序排序":
                    # 弹出提示框
                    show_message_box("极简模式下不使能曝光时间排序，\nALT+I快捷键可切换进入极简模式", "提示", 1000)
                    # 设置排序选项为默认排序
                    self.RT_QComboBox2.setCurrentText("按文件名称排序")
                    
                elif sort_option == "按ISO排序" or sort_option == "按ISO逆序排序":
                    # 弹出提示框    
                    show_message_box("极简模式下不使能ISO排序，\nALT+I快捷键可切换进入极简模式", "提示", 1000)
                    # 设置排序选项为默认排序
                    self.RT_QComboBox2.setCurrentText("按文件名称排序")
            # 更新右侧表格
            self.update_RB_QTableWidget0()  
        except Exception as e:
            print(f"[handle_sort_option]-->处理排序选项失败: {e}")

    def handle_theme_selection(self):
        """处理下拉框选择"""
        # 获取下拉框的当前选择
        print("[handle_theme_selection]-->处理下拉框选择")
        try:
            selected_theme = self.RT_QComboBox3.currentText()
            if selected_theme == "默认主题":
                self.current_theme = "默认主题"
            elif selected_theme == "暗黑主题":  # 修改为 "暗黑主题"
                self.current_theme = "暗黑主题"
            
            # 更新主题
            self.apply_theme()
        except Exception as e:
            print(f"[handle_theme_selection]-->处理下拉框选择失败: {e}")

    def toggle_theme(self):
        """切换主题"""
        print("[toggle_theme]-->切换主题")
        try:
            if self.current_theme == "默认主题":
                self.current_theme = "暗黑主题"
            else:
                self.current_theme = "默认主题"

            # 更新主题
            self.apply_theme()
        except Exception as e:
            print(f"[toggle_theme]-->切换主题失败: {e}")

    def apply_theme(self):
        """初始化主题"""
        print("[apply_theme]-->更新当前主题")
        try:
            if self.current_theme == "暗黑主题":
                self.setStyleSheet(self.dark_style())     # 暗黑主题
            else:
                self.setStyleSheet(self.default_style())  # 默认主题
        except Exception as e:
            print(f"[apply_theme]-->应用当前主题失败: {e}")


    def default_style(self):
        """返回默认模式的样式表"""

        # 定义通用颜色变量
        BACKCOLOR = self.background_color_default  # 浅蓝色背景
        FONTCOLOR = self.font_color_default        # 默认字体颜色
        GRAY = "rgb(127, 127, 127)"                # 灰色
        WHITE = "rgb(238,238,238)"                 # 白色
        QCOMBox_BACKCOLOR = "rgb(255,242,223)"     # 下拉框背景色

        
        table_style = f"""
            QTableWidget#RB_QTableWidget0 {{
                /* 表格整体样式 */
                background-color: {GRAY};
                color: {FONTCOLOR};
            }}
            
            QTableWidget#RB_QTableWidget0::item {{
                /* 单元格样式 */
                background-color: {GRAY};
                color: {FONTCOLOR};
            }}
            
            QTableWidget#RB_QTableWidget0::item:selected {{
                /* 选中单元格样式 */
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
            }}
            
            /* 添加表头样式 */
            QHeaderView::section {{
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
                text-align: center;
                padding: 3px;
                margin: 1px;
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}
            
            /* 修改左上角区域样式 */
            QTableWidget#RB_QTableWidget0::corner {{
                background-color: {BACKCOLOR};  /* 设置左上角背景色 */
                color: {FONTCOLOR};
            }}
        """
        left_qframe_style = f"""
            QFrame#Left_QFrame {{ 
                background-color: {GRAY};
                color: {FONTCOLOR};
                border-radius: 10px;
                border: 1px solid {GRAY};
            }}
        """

        # 按钮组件和复选框组件样式
        button_style = f"""
            QPushButton {{
                background-color: {WHITE};
                color: {FONTCOLOR};
                text-align: center;
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}
            QPushButton:hover {{
                border: 1px solid {BACKCOLOR};
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
            }}
        """

        # 左侧文件浏览区域样式 使用 QFrame 包裹 QTreeView,可以不破坏圆角
        left_area_style = f"""
            QTreeView#Left_QTreeView {{
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
                border-radius: 10px;
                padding: 5px;  /* 添加内边距 */
            }}
            QScrollBar:vertical {{
                background: {GRAY};       /* 纵向滚动条背景色 */
                width: 5px;               /* 设置滚动条高度 */
            }}

            QScrollBar:horizontal {{
                background: {GRAY};        /* 横向滚动条背景色 */
                height: 5px;               /* 设置滚动条高度 */
            }}
            QScrollBar::handle {{
                background: {GRAY};       /* 滚动条的颜色 */
                border-radius: 10px;      /* 设置滚动条的圆角 */
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                background: none; /* 隐藏箭头 */
            }}
        """
        
        # 下拉框通用样式模板
        combobox_style = f"""
            QComboBox {{
                /* 下拉框本体样式 */
                background-color: {QCOMBox_BACKCOLOR};
                color: {FONTCOLOR};
                selection-background-color: {BACKCOLOR};
                selection-color: {FONTCOLOR};
                min-height: 30px;
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}
            
            QComboBox QAbstractItemView {{
                /* 下拉列表样式 */
                background-color: {QCOMBox_BACKCOLOR};
                color: {FONTCOLOR};
                selection-background-color: {BACKCOLOR};
                selection-color: {FONTCOLOR};
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}
            
            QComboBox QAbstractItemView::item {{
                /* 下拉项样式 */
                min-height: 25px;
                padding: 5px;
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}

            QComboBox::hover {{
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
            }}  

        """

        # 下拉框通用样式模板2
        combobox_style2 = f"""
            QComboBox {{
                /* 下拉框本体样式 */
                background-color: {QCOMBox_BACKCOLOR};
                color: {FONTCOLOR};
                selection-background-color: {BACKCOLOR};
                selection-color: {FONTCOLOR};
                min-height: 30px;
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}
            
            QComboBox QAbstractItemView {{
                /* 下拉列表样式 */
                background-color: {QCOMBox_BACKCOLOR};
                color: {FONTCOLOR};
                selection-background-color: {BACKCOLOR};
                selection-color: {FONTCOLOR};
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}
            
            QComboBox QAbstractItemView::item {{
                /* 下拉项样式 */
                min-height: 25px;
                padding: 5px;
                font-family: "{self.custom_font.family()}";
                font-size: {self.custom_font.pointSize()}pt;
            }}

        """

        # 标签的样式表
        statusbar_label_style = f"""
            QLabel {{
                border: none;
                color: {"rgb(255,255,255)"};
                text-align: center;
                font-family: "{self.custom_font_jetbrains_small.family()}";
                font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
            }}
            /* 添加悬浮效果 
            QLabel:hover {{
                border: 1px solid {BACKCOLOR};
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
            }}*/
        """

        # 普通按钮样式表
        statusbar_button_style = f"""
            QPushButton {{
                border: none;
                color: {"rgb(255,255,255)"};
                text-align: center;
                font-family: "{self.custom_font_jetbrains_small.family()}";
                font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
            }}
            QPushButton:hover {{
                border: 1px solid {BACKCOLOR};
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
            }}
        """

        # 检查到新版本的按钮样式表
        statusbar_button_style_version = f"""
            QPushButton {{
                border: none;
                color: {"rgb(255,0,0)"};/* 检测到新版本设置字体颜色为红色 */
                text-align: center;
                background-color: {BACKCOLOR};
                font-family: "{self.custom_font_jetbrains_small.family()}";
                font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
            }}
            QPushButton:hover {{
                border: 1px solid {BACKCOLOR};
                background-color: {BACKCOLOR};
                color: {FONTCOLOR};
            }}
        """        

        # self.custom_font_jetbrains_small   "rgb(234, 211, 32)"
        statusbar_style = f"""
            border: none;
            background-color: {GRAY};
            color: {FONTCOLOR};
            font-family: {self.custom_font_jetbrains_small.family()};
            font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
            
        """

        # 设置左上侧文件浏览区域样式
        self.Left_QTreeView.setStyleSheet(left_area_style)
        # 设置左下角侧框架样式
        self.Left_QFrame.setStyleSheet(left_qframe_style)

        # 设置右侧顶部按钮下拉框样式
        self.RT_QPushButton3.setStyleSheet(button_style)
        self.RT_QPushButton5.setStyleSheet(button_style)
        self.RT_QComboBox.setStyleSheet(combobox_style2)
        self.RT_QComboBox1.setStyleSheet(combobox_style2)
        self.RT_QComboBox0.setStyleSheet(combobox_style)
        self.RT_QComboBox2.setStyleSheet(combobox_style)
        self.RT_QComboBox3.setStyleSheet(combobox_style)
        # 设置右侧中间表格区域样式
        self.RB_QTableWidget0.setStyleSheet(table_style)

        # 设置底部状态栏区域样式 self.statusbar --> self.statusbar_widget --> self.statusbar_QHBoxLayout --> self.statusbar_button1 self.statusbar_button2
        self.statusbar.setStyleSheet(statusbar_style)
        self.statusbar_button1.setStyleSheet(statusbar_button_style)
        # 设置版本按钮更新样式
        if self.new_version_info:
            self.statusbar_button2.setStyleSheet(statusbar_button_style_version)
        else:
            self.statusbar_button2.setStyleSheet(statusbar_button_style)
        self.statusbar_label.setStyleSheet(statusbar_label_style)
        self.statusbar_label0.setStyleSheet(statusbar_label_style)
        self.statusbar_label1.setStyleSheet(statusbar_label_style)


        # 返回主窗口样式
        return f""" 
                /* 浅色模式 */
            """

    def dark_style(self):
            """返回暗黑模式的样式表"""

            BACKCOLOR_ = self.background_color_default  # 配置中的背景色
            # 定义通用颜色变量
            BACKCOLOR = "rgb( 15, 17, 30)"   # 浅蓝色背景
            GRAY = "rgb(127, 127, 127)"      # 灰色
            WHITE = "rgb(238,238,238)"       # 白色
            BLACK = "rgb( 34, 40, 49)"       # 黑色

            
            table_style = f"""
                QTableWidget#RB_QTableWidget0 {{
                    /* 表格整体样式 */
                    background-color: {BLACK};
                    color: {WHITE};
                }}
                
                QTableWidget#RB_QTableWidget0::item {{
                    /* 单元格样式 */
                    background-color: {GRAY};
                    color: {BLACK};
                }}
                
                QTableWidget#RB_QTableWidget0::item:selected {{
                    /* 选中单元格样式 */
                    background-color: {BLACK};
                    color: {WHITE};
                }}
                
                /* 添加表头样式 */
                QHeaderView::section {{
                    background-color: {BLACK};
                    color: {WHITE};
                    text-align: center;
                    padding: 3px;
                    margin: 1px;
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}
              
                /* 设置空列头的背景色 */
                QTableWidget::verticalHeader {{
                    background-color: {BACKCOLOR}; /* 空列头背景色 */
                }}                
                
                /* 修改滚动条样式 */
                QScrollBar:vertical {{
                    background: {BLACK}; /* 滚动条背景 */
                    width: 10px; /* 滚动条宽度 */
                    margin: 22px 0 22px 0; /* 上下边距 */
                }}
                QScrollBar::handle:vertical {{
                    background: {GRAY}; /* 滚动条滑块颜色 */
                    min-height: 20px; /* 滚动条滑块最小高度 */
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    background: none; /* 隐藏上下箭头 */
                }}
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                    background: none; /* 隐藏箭头 */
                }}
                QScrollBar:horizontal {{
                    background: {BLACK}; /* 滚动条背景 */
                    height: 10px; /* 滚动条高度 */
                    margin: 0 22px 0 22px; /* 左右边距 */
                }}
                QScrollBar::handle:horizontal {{
                    background: {GRAY}; /* 滚动条滑块颜色 */
                    min-width: 20px; /* 滚动条滑块最小宽度 */
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    background: none; /* 隐藏左右箭头 */
                }}
                QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
                    background: none; /* 隐藏箭头 */
                }}
                
            """
            left_qframe_style = f"""
                QFrame#Left_QFrame {{ 
                    background-color: {BLACK};
                    color: {WHITE};
                    border-radius: 10px;
                    border: 1px solid {GRAY};
                }}
            """

            # 按钮组件和复选框组件样式
            button_style = f"""
                QPushButton {{
                    background-color: rgb( 58, 71, 80);
                    color: {WHITE};
                    text-align: center;
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}
                QPushButton:hover {{
                    border: 1px solid {BACKCOLOR};
                    background-color: {BACKCOLOR};
                }}
            """


            # 左侧文件浏览区域样式
            left_area_style = f"""
                QTreeView#Left_QTreeView {{
                    background-color: {BLACK};
                    color: {WHITE};
                    border-radius: 10px;
                }}

                /* 修改滚动条样式 */
                QScrollBar:vertical {{
                    background: {BLACK}; /* 滚动条背景 */
                    width: 10px; /* 滚动条宽度 */
                    margin: 22px 0 22px 0; /* 上下边距 */
                }}
                QScrollBar::handle:vertical {{
                    background: {GRAY}; /* 滚动条滑块颜色 */
                    min-height: 20px; /* 滚动条滑块最小高度 */
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    background: none; /* 隐藏上下箭头 */
                }}
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                    background: none; /* 隐藏箭头 */
                }}
                QScrollBar:horizontal {{
                    background: {BLACK}; /* 滚动条背景 */
                    height: 10px; /* 滚动条高度 */
                    margin: 0 22px 0 22px; /* 左右边距 */
                }}
                QScrollBar::handle:horizontal {{
                    background: {GRAY}; /* 滚动条滑块颜色 */
                    min-width: 20px; /* 滚动条滑块最小宽度 */
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    background: none; /* 隐藏左右箭头 */
                }}
                QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
                    background: none; /* 隐藏箭头 */
                }}

            """
            
            # 下拉框通用样式模板
            combobox_style = f"""
                QComboBox {{
                    /* 下拉框本体样式 */
                    background-color: {BLACK};
                    color: {WHITE};
                    selection-background-color: {BACKCOLOR};
                    selection-color: {WHITE};
                    min-height: 30px;
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}
                
                QComboBox QAbstractItemView {{
                    /* 下拉列表样式 */
                    background-color: {BLACK};
                    color: {WHITE};
                    selection-background-color: {WHITE};
                    selection-color: {BLACK};
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}
                
                QComboBox QAbstractItemView::item {{
                    /* 下拉项样式 */
                    min-height: 25px;
                    padding: 5px;
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}

                QComboBox::hover {{
                    background-color: {BACKCOLOR};
                    color: {WHITE};
                }}  

            """

            # 下拉框通用样式模板2
            combobox_style2 = f"""
                QComboBox {{
                    /* 下拉框本体样式 */
                    background-color: {BLACK};
                    color: {WHITE};
                    selection-background-color: {BACKCOLOR};
                    selection-color: {WHITE};
                    min-height: 30px;
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}
                
                QComboBox QAbstractItemView {{
                    /* 下拉列表样式 */
                    background-color: {WHITE};
                    color: {BLACK};
                    selection-background-color: {BACKCOLOR_};
                    selection-color: {WHITE};
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}
                
                QComboBox QAbstractItemView::item {{
                    /* 下拉项样式 */
                    min-height: 25px;
                    padding: 5px;
                    font-family: "{self.custom_font.family()}";
                    font-size: {self.custom_font.pointSize()}pt;
                }}

            """
    
    
            statusbar_label_style = f"""
                border: none;
                color: {WHITE};
                font-family: {self.custom_font_jetbrains_small.family()};
                font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
                
            """

            statusbar_button_style = f"""
                QPushButton {{
                    background-color: {BLACK};
                    color: {WHITE};
                    text-align: center;
                    font-family: "{self.custom_font_jetbrains_small.family()}";
                    font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
                }}
                QPushButton:hover {{
                    border: 1px solid {BACKCOLOR};
                    background-color: {BACKCOLOR};
                    color: {WHITE};
                }}
            """

            statusbar_button_style_version = f"""
                QPushButton {{
                    background-color: {"rgb(245,108,108)"};
                    color: {WHITE};
                    text-align: center;
                    font-family: "{self.custom_font_jetbrains_small.family()}";
                    font-size: {self.custom_font_jetbrains_small.pointSize()}pt;
                }}
                QPushButton:hover {{
                    border: 1px solid {BACKCOLOR};
                    background-color: {"rgb(245,108,108)"};
                    color: {WHITE};
                }}
            """  

            statusbar_style = f"""
                border: none;
                background-color: {BLACK};
                color: {WHITE};
            """


            # 设置左上侧文件浏览区域样式
            self.Left_QTreeView.setStyleSheet(left_area_style)

            # 设置左下角侧框架样式
            self.Left_QFrame.setStyleSheet(left_qframe_style)


            # 设置右侧顶部按钮下拉框样式
            self.RT_QPushButton3.setStyleSheet(button_style)
            self.RT_QPushButton5.setStyleSheet(button_style)

            self.RT_QComboBox.setStyleSheet(combobox_style2)
            self.RT_QComboBox1.setStyleSheet(combobox_style2)

            self.RT_QComboBox0.setStyleSheet(combobox_style)
            self.RT_QComboBox2.setStyleSheet(combobox_style)
            self.RT_QComboBox3.setStyleSheet(combobox_style)

            # 设置右侧中间表格区域样式
            self.RB_QTableWidget0.setStyleSheet(table_style)

            # 设置底部状态栏区域样式 self.statusbar --> self.statusbar_widget --> self.statusbar_QHBoxLayout --> self.statusbar_button1 self.statusbar_button2
            self.statusbar.setStyleSheet(statusbar_style)
            self.statusbar_button1.setStyleSheet(statusbar_button_style)
            # 设置版本按钮更新样式
            if self.new_version_info:
                self.statusbar_button2.setStyleSheet(statusbar_button_style_version)
            else:
                self.statusbar_button2.setStyleSheet(statusbar_button_style)
            self.statusbar_label.setStyleSheet(statusbar_label_style)
            self.statusbar_label0.setStyleSheet(statusbar_label_style)
            self.statusbar_label1.setStyleSheet(statusbar_label_style)

            # 返回主窗口样式
            return f"""
                QWidget#main_body {{ /* 主窗口背景色 */
                    background-color: black;
                    color: white;
                }}

                QSplitter {{ /* 分割器背景色 */
                    background-color: black;
                    color: white;
                }}
                QSplitter::handle {{ /* 分割器手柄背景色 */
                    background-color: black;
                    color: white;
                }}
                QSplitter::handle:hover {{ /* 分割器手柄悬停背景色 */
                    background-color: black;
                    color: white;
                }}

                QGroupBox#Left_QGroupBox {{ /* 左侧组框1_背景色 */
                    background-color: black;
                    color: white;
                }}
                QGroupBox#Left_QGroupBox::title {{ /* 左侧组框1_标题背景色 */
                    background-color: black;
                    color: white;
                }}
                QGroupBox#Left_QGroupBox::title:hover {{ /* 左侧组框1_标题悬停背景色 */
                    background-color: black;
                    color: white;
                }}

                QGroupBox#Right_Top_QGroupBox {{ /* 右侧组框2_背景色 */
                    background-color: black;
                    color: white;
                }}   
                QGroupBox#Right_Top_QGroupBox::title {{ /* 右侧组框2_标题背景色 */
                    background-color: black;
                    color: white;
                }}
                QGroupBox#Right_Top_QGroupBox::title:hover {{ /* 右侧组框2_标题悬停背景色 */
                    background-color: black;
                    color: white;
                }}

                QGroupBox#Right_Bottom_QGroupBox {{ /* 右侧组框3_背景色 */
                    background-color: black;
                    color: white;
                }}   
                QGroupBox#Right_Bottom_QGroupBox::title {{ /* 右侧组框3_标题背景色 */
                    background-color: black;
                    color: white;
                }}
                QGroupBox#Right_Bottom_QGroupBox::title:hover {{ /* 右侧组框3_标题悬停背景色 */
                    background-color: black;
                    color: white;
                }}
                
                /* 表格样式 */
                
            """

    def cleanup(self):
        """清理资源"""
        self.cancel_preloading()
        if self.compare_window:
            self.compare_window.deleteLater()
            self.compare_window = None
            
        self.threadpool.clear()
        self.threadpool.waitForDone()
        
        gc.collect()

    """缓存文件路径列表，避免重复加载"""
    def load_settings(self):
        """从JSON文件加载设置"""
        print("[load_settings]-->从JSON文件加载之前的设置")
        try:
            settings_path = os.path.join(os.path.dirname(__file__), "config", "basic_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding='utf-8', errors='ignore') as f:
                    settings = json.load(f)

                    # 恢复地址栏历史记录和当前目录
                    combobox_history = settings.get("combobox_history", [])
                    self.RT_QComboBox.clear()
                    self.RT_QComboBox.addItems(combobox_history)
                    current_directory = settings.get("current_directory", "")
                    if current_directory and os.path.exists(current_directory):
                        self.RT_QComboBox.setCurrentText(current_directory)

                    # 恢复文件类型选择
                    selected_option = settings.get("file_type_option", "显示图片文件")
                    index = self.RT_QComboBox0.findText(selected_option)
                    if index >= 0:
                        self.RT_QComboBox0.setCurrentIndex(index)

                    # 恢复排序方式
                    sort_option = settings.get("sort_option", "按创建时间排序")
                    index = self.RT_QComboBox2.findText(sort_option)
                    if index >= 0:
                        self.RT_QComboBox2.setCurrentIndex(index)

                    # 恢复主题设置
                    theme_option = settings.get("theme_option", "默认主题")
                    index = self.RT_QComboBox3.findText(theme_option)
                    if index >= 0:
                        self.RT_QComboBox3.setCurrentIndex(index)
                        self.current_theme = settings.get("current_theme", "默认主题")
                        self.apply_theme()

                    # 恢复文件夹选择状态
                    all_items = settings.get("combobox1_all_items", [])
                    checked_items = settings.get("combobox1_checked_items", [])
                    
                    if all_items:
                        self.model = CheckBoxListModel(all_items)
                        self.RT_QComboBox1.setModel(self.model)
                        self.RT_QComboBox1.setItemDelegate(CheckBoxDelegate())
                        self.RT_QComboBox1.setContextMenuPolicy(Qt.NoContextMenu)

                        # 恢复选中状态
                        for i, item in enumerate(self.model.items):
                            if item in checked_items:
                                self.model.setChecked(self.model.index(i))
                        # 更新同级文件夹下拉框选项
                        self.updateComboBox1Text()
                    else:
                        # 初始化同级文件夹下拉框选项
                        self.RT_QComboBox1_init()

                    # 恢复极简模式状态,默认开启
                    self.simple_mode = settings.get("simple_mode", True)

                    # 恢复拖拽模式状态,默认开启
                    self.drag_flag = settings.get("drag_flag", True)
            else:
                # 若没有cache/设置，则在此初始化主题设置--默认主题
                self.apply_theme()

        except Exception as e:
            print(f"[load_settings]-->加载设置时出错: {e}")
            return

    def save_settings(self):
        """保存当前设置到JSON文件"""
        try:
            settings_path = os.path.join(os.path.dirname(__file__), "config", "basic_settings.json")
            
            # 确保cache目录存在
            cache_dir = os.path.dirname(settings_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            # 收集所有需要保存的设置
            settings = {
                # 地址栏历史记录和当前目录
                "combobox_history": [self.RT_QComboBox.itemText(i) for i in range(self.RT_QComboBox.count())],
                "current_directory": self.RT_QComboBox.currentText(),
                
                # 文件类型选择
                "file_type_option": self.RT_QComboBox0.currentText(),
                
                # 文件夹选择状态
                "combobox1_checked_items": self.model.getCheckedItems() if hasattr(self, 'model') and self.model else [],
                "combobox1_all_items": self.model.items[1:] if hasattr(self, 'model') and self.model else [],
                
                # 排序方式
                "sort_option": self.RT_QComboBox2.currentText(),
                
                # 主题设置
                "theme_option": self.RT_QComboBox3.currentText(),
                "current_theme": self.current_theme,
                
                # 极简模式状态
                "simple_mode": self.simple_mode,

                # 拖拽模式状态
                "drag_flag": self.drag_flag

            }

            # 保存设置到JSON文件
            with open(settings_path, "w", encoding='utf-8', errors='ignore') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"[save_settings]-->保存设置时出错: {e}")


    def press_space_and_b_get_selected_file_paths(self, key_type):
        """返回右侧表格选中的文件的路径列表"""
        try:
            selected_items = self.RB_QTableWidget0.selectedItems()  # 获取选中的项
            if not selected_items:
                # 弹出提示框
                show_message_box("没有选中的项！", "提示", 500)
                print("[press_space_and_b_get_selected_file_paths]-->没有检测到选中项！")
                return [], []
            
            # 获取最大最小的行索引
            row_min, row_max = 0, self.RB_QTableWidget0.rowCount() - 1 
            # 用于存储文件路径和文件索引的列表
            file_paths, current_image_index = [], []  
            # 判断是否是首次按键
            if not self.last_key_press:
                step_row = 0   # 首次按键不移动
                self.last_key_press = True # 第二次进入设置为True
            else:
                # 统计行索引需要移动step
                if len(set([item.column() for item in selected_items])) == len(selected_items):
                    # 如果选中项的个数和图片列数相等，则表示是单选，行索引移动step_row = 1
                    step_row = 1
                else:
                    # 如果选中项的个数和图片列数不相等，则表示是多选，行索引移动step_row = 选中项的行索引去重后长度
                    step_row = len(set([item.row() for item in selected_items]))   
            
            # 清除所有选中的项
            self.RB_QTableWidget0.clearSelection() 

            # 遍历选中的项
            for item in selected_items:
                # 获取当前项的列索引行索引
                col_index = item.column()
                row_index = item.row()
                # 判断按下space和b来控制选中的单元格上移和下移
                if key_type == 'space':    # 空格键获取下一组图片
                    row_index += step_row
                elif key_type == 'b':      # B键获取上一组图片
                    row_index -= step_row
                else:
                    print("没有按下space和b键")

                if row_index > row_max or row_index < row_min:  # 修正边界检查
                    self.RB_QTableWidget0.clearSelection()      # 清除所有选中的项
                    print(f"已超出表格范围: {row_index}")
                    return [], []
                else:
                    item = self.RB_QTableWidget0.item(row_index, col_index)
                    if item and item.text():
                        item.setSelected(True)  # 选中当前单元格
                        # 构建图片完整路径
                        file_name = item.text().split('\n')[0]  # 获取文件名，修改获取方式(第一行为需要的文件名)
                        column_name = self.RB_QTableWidget0.horizontalHeaderItem(col_index).text()
                        current_directory = self.RT_QComboBox.currentText()  # 获取当前选中的目录
                        full_path = (Path(current_directory).parent / column_name / file_name).as_posix()
                        
                        if os.path.isfile(full_path):
                            file_paths.append(full_path)  # 只有在是有效文件时才添加到列表中
                        else:
                            print(f"无效文件路径: {full_path}")  # 输出无效文件路径的提示   
                    else:
                        print(f"item is None or item.text() is None")

                # 如果选中项的列数和图片列数相等，则打印当前处理图片张数
                if not self.image_index_max: # 如果image_index_max为空，则初始化为当前表格的最大行数
                    print("image_index_max is None")
                    self.image_index_max = [self.RB_QTableWidget0.rowCount()] * self.RB_QTableWidget0.columnCount()
                if row_index+1 > self.image_index_max[col_index]:
                    pass
                else:
                    current_image_index.append(f"{row_index+1}/{self.image_index_max[col_index]}")


            # 将选中的单元格滚动到视图中间位置
            self.RB_QTableWidget0.scrollToItem(item, QAbstractItemView.PositionAtCenter)

            
            return file_paths, current_image_index  # 返回文件路径列表
        except Exception as e:
            print(f"[press_space_and_b_get_selected_file_paths]-->处理键盘按下事件时发生错误: {e}")
            return [], []
    
    def on_f1_pressed(self):
        """处理F1键按下事件"""
        try:
            self.open_mipi2raw_tool()
        except Exception as e:
            print(f"[on_f1_pressed]-->处理F1键按下事件失败: {e}")
            return


    """键盘按下事件处理""" 
    def on_f2_pressed(self):
        """处理F2键按下事件"""
        selected_items = self.RB_QTableWidget0.selectedItems()  # 获取选中的项
        if not selected_items:
            show_message_box("没有选中的项！", "提示", 500)
            return
            
        current_folder, _ = self.press_space_and_b_get_selected_file_paths('test')
        if not current_folder:
            show_message_box("没有选中的项！", "提示", 500)
            return

        try:    
            if len(selected_items) == 1:
                # 单文件重命名
                dialog = SingleFileRenameDialog(current_folder[0], self)
                if dialog.exec_() == QDialog.Accepted:
                    
                    # 获取新的文件路径
                    new_file_path = dialog.get_new_file_path()
                    
                    if new_file_path:
                        # 获取新的文件名
                        new_file_name = os.path.basename(new_file_path)
                        # 获取选中的单元格
                        item = selected_items[0]
                        row = item.row()
                        col = item.column() 

                        # 更新单元格内容
                        current_text = item.text()
                        if '\n' in current_text:  # 如果有多行文本
                            # 保持原有的其他信息，只更新文件名
                            lines = current_text.split('\n')
                            lines[0] = new_file_name  # 更新第一行的文件名
                            new_text = '\n'.join(lines)
                        else:
                            new_text = new_file_name
                            
                        # 设置新的单元格文本
                        self.RB_QTableWidget0.item(row, col).setText(new_text)
            else:
                # 多文件重命名
                self.open_rename_tool(current_folder)

        except Exception as e:
            print(f"[on_f2_pressed]-->处理F2键按下事件失败: {e}")
            return


    def on_f4_pressed(self):
        """处理F4键按下事件"""
        current_folder = self.RT_QComboBox.currentText()
        current_folder = os.path.dirname(current_folder) # 获取当前选中的文件夹上一级文件夹路径
        if current_folder:
            try:
                self.open_rename_tool(current_folder)
            except Exception as e:
                print(f"[on_f4_pressed]-->处理F4键按下事件失败: {e}")
                return
        else:
            # 弹出提示框    
            show_message_box("当前没有选中的文件夹", "提示", 500)

    def on_f5_pressed(self):
        """处理F5键按下事件"""

        try:    
            # 刷新表格
            show_message_box("刷新表格&清除缓存-", "提示", 500)

            # 删除缓存文件中的zip文件
            cache_dir = os.path.join(os.path.dirname(__file__), "cache")
            if os.path.exists(cache_dir):
                # 强制删除缓存文件中的zip文件
                force_delete_folder(cache_dir, '.zip')

            # 清除图标缓存
            IconCache.clear_cache()
            
            # 更新表格
            self.update_RB_QTableWidget0()

        except Exception as e:
            print(f"[on_f5_pressed]-->刷新表格&清除缓存失败: {e}")
            return

    def on_f12_pressed(self):
        """处理F12键按下事件,重启程序"""
        self.close()
        try:
            program_path = os.path.join(os.path.dirname(__file__), "hiviewer.exe")
            if os.path.exists(program_path):
                
                # 使用os.startfile启动程序
                os.startfile(program_path)
                
                # 等待5秒确保程序启动
                time.sleep(3)  
                print(f"[on_f12_pressed]-->已启动程序: hiviewer.exe")
                
                return True
            else:
                print(f"[on_f12_pressed]-->程序文件不存在: {program_path}")
                return False
        except Exception as e:
            print(f"[on_f12_pressed]-->启动程序失败: {e}")
            return False

    def on_escape_pressed(self):
        print("[on_escape_pressed]-->escape被按下了")
        self.close()  # 关闭主界面
        self.save_settings()

    def on_alt_pressed(self):
        self.drag_flag = not self.drag_flag
        if self.drag_flag:
            show_message_box("切换到拖拽模式", "提示", 500)
        else:
            show_message_box("关闭拖拽模式", "提示", 500)
        

    def on_p_pressed(self):
        """处理P键按下事件"""
        print("[on_p_pressed]-->切换主题--P键已按下, 更新下拉框选项")
        try:
            if self.current_theme == "默认主题":
                self.RT_QComboBox3.setCurrentIndex(self.RT_QComboBox3.findText("暗黑主题"))
            else:
                self.RT_QComboBox3.setCurrentIndex(self.RT_QComboBox3.findText("默认主题"))

            # 更新主题
            self.toggle_theme()
        except Exception as e:
            print(f"[on_p_pressed]-->切换主题失败: {e}")
                

    def on_i_pressed(self):
        """处理i键按下事件,调用高通工具后台解析图片的exif信息"""
        # 获取当前选中的文件类型
        selected_option = self.RT_QComboBox.currentText()
        try:

            # 创建并显示自定义对话框,传入图片列表
            dialog = Qualcom_Dialog(selected_option)

            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 收集用户输入的参数
                dict_info = dialog.get_data()
                qualcom_path = dict_info.get("Qualcom工具路径","")
                images_path = dict_info.get("Image文件夹路径","")
                metadata_path = os.path.join(os.path.dirname(__file__), "resource", "tools", "metadata.exe")

                # 拼接参数命令字符串
                if qualcom_path and images_path and os.path.exists(metadata_path) and os.path.exists(images_path) and os.path.exists(qualcom_path):
                    command = f"{metadata_path} --chromatix \"{qualcom_path}\" --folder \"{images_path}\""

                    # 检查图片文件夹目录下是否存在xml文件，不存在则启动线程解析图片
                    xml_exists = any(f for f in os.listdir(images_path) if f.endswith('_new.xml'))

                    # 创建线程，必须在主线程中连接信号
                    self.command_thread = CommandThread(command, images_path)
                    self.command_thread.finished.connect(self.on_command_finished)  

                    # 如果xml文件不存在，则启动线程解析图片；否则提取xml信息保存到excel文件
                    if not xml_exists:
                        self.command_thread.start()   # 启动线程
                        show_message_box("正在使用高通工具后台解析图片Exif信息...", "提示", 1000)
                    else:
                        show_message_box("已有xml文件, 无须解析图片", "提示", 1000)
                        save_excel_data(images_path)  # 解析xml文件将其保存到excel中去

            # 无论对话框是接受还是取消，都手动销毁对话框
            dialog.deleteLater()
            dialog = None

        except Exception as e:
            print(f"[on_i_pressed]-->处理i键按下事件失败: {e}")
            return


    def on_command_finished(self, success, error_message, images_path=None):
        """处理命令执行完成的信号"""
        try:
            if success and images_path:
                # 解析xml文件将其保存到excel中去
                save_excel_data(images_path)
                # 提示
                show_message_box("高通工具后台解析图片成功！", "提示", 1000)
                print(f"[on_command_finished]-->高通工具后台解析图片成功！")
            else:
                show_message_box(f"高通工具后台解析图片失败: {error_message}", "提示", 2000)
                print(f"[on_command_finished]-->高通工具后台解析图片失败: {error_message}")

        except Exception as e:
            show_message_box(f"高通工具后台解析图片失败: {error_message}", "提示", 2000)
            print(f"[on_command_finished]-->高通工具后台解析图片成功失败: {e}")
            return


    def on_l_pressed(self):
        """处理L键打开图片处理工具"""
        try:
            # 获取选中项并验证
            selected_items = self.RB_QTableWidget0.selectedItems()
            if not selected_items or len(selected_items) != 1:
                show_message_box("请选择单个图片文件", "提示", 500)
                return

            # 构建完整文件路径
            current_dir = self.RT_QComboBox.currentText()
            if not current_dir:
                show_message_box("当前目录无效", "提示", 500)
                return

            # 获取文件信息
            item = selected_items[0]
            column_name = self.RB_QTableWidget0.horizontalHeaderItem(item.column()).text()
            file_name = item.text().split('\n')[0]
            full_path = (Path(current_dir).parent / column_name / file_name).as_posix()

            # 验证文件有效性
            if not full_path.lower().endswith(self.IMAGE_FORMATS):
                show_message_box(f"不支持的文件格式: {os.path.splitext(full_path)[1]}", "提示", 500)
                return
                
            if not os.path.isfile(full_path):
                show_message_box(f"文件不存在: {os.path.basename(full_path)}", "提示", 500)
                return

            # 打开处理窗口
            self.open_image_process_window(full_path)

        except Exception as e:
            error_msg = f"[on_l_pressed]-->打开图片失败: {str(e)}"
            show_message_box(error_msg, "错误", 1000)

    def on_ctrl_h_pressed(self):
        """处理Ctrl+h键按下事件, 打开帮助信息"""
        try:
            # 单例模式管理帮助窗口
            if not hasattr(self, 'help_dialog'):
                # 构建文档路径,使用说明文档+版本更新文档
                doc_dir = os.path.join(os.path.dirname(__file__), "resource", "docs")
                User_path = os.path.join(doc_dir, "User_Manual.md")
                Version_path = os.path.join(doc_dir, "Version_Updates.md")
                
                # 验证文档文件存在性
                if not os.path.isfile(User_path) or not os.path.isfile(Version_path):
                    show_message_box(f"帮助文档未找到:\n{User_path}or{Version_path}", "配置错误", 2000)
                    return
                
                # 初始化对话框
                self.help_dialog = AboutDialog(User_path,Version_path)

            # 激活现有窗口
            self.help_dialog.show()
            self.help_dialog.raise_()
            self.help_dialog.activateWindow()
            # 链接关闭事件
            self.help_dialog.finished.connect(self.close_helpinfo)
            
        except Exception as e:
            error_msg = f"无法打开帮助文档:\n{str(e)}\n请检查程序是否包含文件: ./resource/docs/update_main_logs.md"
            show_message_box(error_msg, "严重错误", 3000)

    def close_helpinfo(self):
        """关闭对话框事件"""
        # 手动销毁对话框
        if hasattr(self, 'help_dialog'):
            # 强制删除
            del self.help_dialog
            print("[close_helpinfo]-->成功销毁对话框")


    def on_ctrl_f_pressed(self):
        """处理Ctrl+f键按下事件, 打开图片模糊搜索工具"""
        try:
            # 构建图片名称列表，保持多维列表的结构, 保持图片名称的完整路径
            image_names = [[os.path.basename(path) for path in folder_paths] for folder_paths in self.paths_list]

            # 创建搜索窗口
            self.search_window = SearchOverlay(self, image_names)

            self.search_window.show_search_overlay()

            # 连接搜索窗口的选中项信号
            self.search_window.item_selected_from_search.connect(self.on_item_selected_from_search)
            print("[on_ctrl_f_pressed]-->打开图片模糊搜索工具成功")

        except Exception as e:
            print(f"[on_ctrl_f_pressed]-->打开图片模糊搜索工具失败: {e}")   

    def on_item_selected_from_search(self, position):
        """处理搜索窗口的选中项信号,返回行(row)和列(col)"""
        row, col = position
        # 清除表格选中项，设置表格选中项，滚动到选中项
        self.RB_QTableWidget0.clearSelection()
        item = self.RB_QTableWidget0.item(row, col)
        if item:
            item.setSelected(True)
            self.RB_QTableWidget0.scrollToItem(item, QAbstractItemView.PositionAtCenter)
            

        # 释放搜索窗口
        if self.search_window:
            self.search_window.deleteLater()
            self.search_window = None

        print(f"[on_item_selected_from_search]-->选中图片: {row}, {col}")

    def on_search_window_closed(self):
        """处理搜索窗口关闭事件"""
        # 释放搜索窗口
        self.search_window = None
        print("[on_search_window_closed]-->搜索窗口关闭")

    def on_b_pressed(self):
        """处理B键按下事件，用于查看上一组图片/视频"""
        try:
            # 按键防抖机制，防止快速多次按下导致错误，设置0.5秒内不重复触发
            current_time = time.time()
            if hasattr(self, 'last_space_press_time') and current_time - self.last_space_press_time < 0.5:  
                raise ValueError(f"触发了按键防抖机制0.5s内重复按键")
            self.last_space_press_time = current_time

            # 获取选中单元格的文件路径和索引
            selected_file_paths, image_indexs = self.press_space_and_b_get_selected_file_paths('b')
            if not selected_file_paths:
                raise ValueError(f"无法获取选中的文件路径和索引")
            
            # 获取所有文件的扩展名并去重，判断这一组文件的格式，纯图片，纯视频，图片+视频
            flag_video, flag_image, flag_other = 0, 0, 0
            file_extensions = {os.path.splitext(path)[1].lower() for path in selected_file_paths}
            if not file_extensions:
                raise ValueError(f"没有提取到有效的文件格式")
            # 检查文件类型的合法性
            for ext in list(file_extensions):
                if ext.endswith(self.VIDEO_FORMATS):
                    flag_video = 1
                elif ext.endswith(self.IMAGE_FORMATS):
                    flag_image = 1
                else:
                    flag_other = 1
            # 检查是否多个文件混合
            if flag_video + flag_image + flag_other > 1:
                show_message_box("不支持同时选中图片/视频和其它文件格式,\n请重新选择文件打开", "提示", 1000)
                raise ValueError(f"不支持同时选中图片和其它文件")

            # 根据文件类型选择是否打开或者打开是什么子界面
            if flag_video:
                # 限制视频文件的数量
                if len(selected_file_paths) > 5:
                    show_message_box("最多支持同时比较5个视频文件", "提示", 1000)
                    raise ValueError(f"没有提取到有效的文件格式")
                # 调用视频播放子界面
                self.create_video_player(selected_file_paths, image_indexs)
            
            elif flag_image:
                # 限制最多选中8个文件
                if len(selected_file_paths) > 8:
                    show_message_box("最多只能同时选中8个文件", "提示", 1000)
                    raise ValueError(f"没有提取到有效的文件格式")  
                           
                # 调用看图子界面
                self.create_compare_window(selected_file_paths, image_indexs)

            else:
                show_message_box("不支持打开该文件格式", "提示", 1000)
                raise ValueError(f"不支持打开的文件格式")

        except Exception as e:
            # 恢复第一次按下键盘空格键或B键
            self.last_key_press = False 
            print(f"[on_b_pressed]-->主界面--处理B键时发生错误: {e}")
            

    def on_space_pressed(self):
        """处理空格键按下事件"""
        try:

            # 按键防抖机制，防止快速多次按下导致错误，设置0.5秒内不重复触发
            current_time = time.time()
            if hasattr(self, 'last_space_press_time') and current_time - self.last_space_press_time < 0.5:  
                return
            self.last_space_press_time = current_time

            # 获取选中单元格的文件路径和索引
            selected_file_paths, image_indexs = self.press_space_and_b_get_selected_file_paths('space')
            if not selected_file_paths:
                raise ValueError(f"无法获取选中的文件路径和索引")

            # 限制最多选中8个文件
            if len(selected_file_paths) > 10:
                show_message_box("最多只能同时选中10个文件", "提示", 1000)
                raise ValueError(f"没有提取到有效的文件格式")
            
            # 获取所有文件的扩展名并去重，判断这一组文件的格式，纯图片，纯视频，图片+视频
            flag_video, flag_image, flag_other = 0, 0, 0
            file_extensions = {os.path.splitext(path)[1].lower() for path in selected_file_paths}
            if not file_extensions:
                raise ValueError(f"没有提取到有效的文件格式")
            # 检查文件类型的合法性
            for ext in list(file_extensions):
                if ext.endswith(self.VIDEO_FORMATS):
                    flag_video = 1
                elif ext.endswith(self.IMAGE_FORMATS):
                    flag_image = 1
                else:
                    flag_other = 1
            # 检查是否多个文件混合
            if flag_video + flag_image + flag_other > 1:
                show_message_box("不支持同时选中图片/视频和其它文件格式,\n请重新选择文件打开", "提示", 1000)
                raise ValueError(f"不支持同时选中图片和其它文件")

            # 根据文件类型选择是否打开或者打开是什么子界面
            if flag_video:
                # 限制视频文件的数量
                if len(selected_file_paths) > 5:
                    show_message_box("最多支持同时比较5个视频文件", "提示", 1000)
                    raise ValueError(f"没有提取到有效的文件格式")
                # 调用视频播放子界面
                self.create_video_player(selected_file_paths, image_indexs)
            
            elif flag_image:
                # 限制最多选中8个文件
                if len(selected_file_paths) > 8:
                    show_message_box("最多只能同时选中8个文件", "提示", 1000)
                    raise ValueError(f"没有提取到有效的文件格式")             
                # 调用看图子界面
                self.create_compare_window(selected_file_paths, image_indexs)

            else:
                show_message_box("不支持打开该文件格式", "提示", 1000)
                raise ValueError(f"不支持打开的文件格式")

        except Exception as e:
            # 恢复第一次按下键盘空格键或B键
            self.last_key_press = False 
            print(f"[on_space_pressed]-->主界面--处理B键时发生错误: {e}")


    def create_compare_window(self, selected_file_paths, image_indexs):
        """创建看图子窗口的统一方法"""
        try:
            # 暂停预加载
            # self.pause_preloading() # modify by diamond_cz 20250217 不暂停预加载，看图时默认后台加载图标
            
            # 初始化标签文本
            self.statusbar_label1.setText(f"🔉: 正在打开看图子界面...")
            self.statusbar_label1.repaint()  # 刷新标签文本

            # 初始化看图子界面
            if not self.compare_window:
                print("[create_compare_window]-->主界面--初始化看图子界面")
                self.compare_window = SubMainWindow(selected_file_paths, image_indexs, self)
            else:
                print("[create_compare_window]-->主界面--看图子界面已存在，传入图片及索引列表")
                self.compare_window.set_images(selected_file_paths, image_indexs)
                self.compare_window.show()

            # 连接看图子窗口的关闭信号
            self.compare_window.closed.connect(self.on_compare_window_closed)
            self.statusbar_label1.setText(f"🔉: 看图子界面打开成功")
            self.statusbar_label1.repaint()  # 刷新标签文本

            # self.hide()  # modify by diamond_cz 20250217 不隐藏主界面
        except Exception as e:
            print(f"[create_compare_window]-->主界面--创建看图子窗口时发生错误: {e}")
            return

    def on_compare_window_closed(self):
        """处理子窗口关闭事件"""
        if self.compare_window:
            print("[on_compare_window_closed]-->主界面,接受看图子窗口关闭事件")
            # 隐藏看图子界面，清理资源
            self.compare_window.hide(), self.compare_window.cleanup()
            self.statusbar_label1.setText(f"🔉: 看图子界面关闭成功")

        # 检查看图子窗口的主题是否与主窗口一致,若不一致则更新主窗口的主题
        if (self.background_color_default != self.compare_window.background_color_default or 
            self.background_color_table != self.compare_window.background_color_table or 
            self.font_color_exif != self.compare_window.font_color_exif or
            self.font_color_default != self.compare_window.font_color_default):
            self.background_color_default = self.compare_window.background_color_default
            self.background_color_table = self.compare_window.background_color_table
            self.font_color_exif = self.compare_window.font_color_exif
            self.font_color_default = self.compare_window.font_color_default
        
            # 更新主题
            self.apply_theme()
        
        # 恢复第一次按下键盘空格键或B键
        self.last_key_press = False  

    def pause_preloading(self):
        """暂停预加载"""
        if self.current_preloader and self.preloading:
            self.current_preloader.pause()
            print("[pause_preloading]-->预加载已暂停")

    def resume_preloading(self):
        """恢复预加载"""
        if self.current_preloader and self.preloading:
            self.current_preloader.resume()
            print("[resume_preloading]-->预加载已恢复")

    def create_video_player(self, selected_file_paths, image_indexs):
        """创建视频播放器的统一方法"""
        self.video_player = VideoWall(selected_file_paths) #, image_indexs
        self.video_player.setWindowTitle("多视频播放程序")
        self.video_player.setWindowFlags(Qt.Window) 
        # 设置窗口图标
        icon_path = (self.base_icon_path / "video_icon.ico").as_posix()
        self.video_player.setWindowIcon(QIcon(icon_path))
        self.video_player.closed.connect(self.on_video_player_closed)
        self.video_player.show()
        self.hide()  # 隐藏主窗口

    def open_rename_tool(self, current_folder):
        """创建批量重命名的统一方法"""
        self.rename_tool = FileOrganizer()
        self.rename_tool.select_folder(current_folder)  # 传递当前文件夹路径
        self.rename_tool.setWindowTitle("批量重命名")
        # 设置窗口最大化
        # self.rename_tool.showMaximized()
        # 设置窗口图标
        icon_path = (self.base_icon_path / "rename_ico_96x96.ico").as_posix()
        self.rename_tool.setWindowIcon(QIcon(icon_path))
        # 链接关闭事件
        self.rename_tool.closed.connect(self.on_rename_tool_closed) 
        self.rename_tool.show()
        self.hide()

    def open_image_process_window(self, image_path):
        """创建图片处理子窗口的统一方法"""
        self.image_process_window = SubCompare(image_path)
        self.image_process_window.setWindowTitle("图片调整")
        self.image_process_window.setWindowFlags(Qt.Window)
        # 设置窗口最大化
        # self.image_process_window.showMaximized()
        # 设置窗口图标
        icon_path = (self.base_icon_path / "ps_ico_96x96.ico").as_posix()
        self.image_process_window.setWindowIcon(QIcon(icon_path))
        # 链接关闭事件
        self.image_process_window.closed.connect(self.on_image_process_window_closed) 
        self.image_process_window.show()
        self.hide()

    def open_bat_tool(self):
        """创建批量执行命令的统一方法"""
        self.bat_tool = LogVerboseMaskApp()
        self.bat_tool.setWindowTitle("批量执行命令")
        # 设置窗口图标
        icon_path = (self.base_icon_path / "cmd_ico_96x96.ico").as_posix()
        self.bat_tool.setWindowIcon(QIcon(icon_path))
        # 设置窗口最大化
        # self.bat_tool.showMaximized()
        # 链接关闭事件 未添加
        self.bat_tool.closed.connect(self.on_bat_tool_closed)
        self.bat_tool.show()
        self.hide()

    def open_mipi2raw_tool(self):
        """打开MIPI RAW文件转换为JPG文件工具"""
        self.mipi2raw_tool = Mipi2RawConverterApp()
        self.mipi2raw_tool.setWindowTitle("MIPI RAW文件转换为JPG文件")
        
        # 设置窗口图标
        icon_path = (self.base_icon_path / "raw_ico_96x96.ico").as_posix()
        self.mipi2raw_tool.setWindowIcon(QIcon(icon_path))

        # 添加链接关闭事件
        self.mipi2raw_tool.closed.connect(self.on_mipi2ram_tool_closed)
        self.mipi2raw_tool.show()
        

    def on_video_player_closed(self):
        """处理视频播放器关闭事件"""
        if self.video_player: # 删除引用以释放资源
            self.video_player.deleteLater()
            self.video_player = None
        self.show() # 显示主窗口

        # 恢复第一次按下键盘空格键或B键
        self.last_key_press = False 

    def on_rename_tool_closed(self):
        """处理重命名工具关闭事件"""
        if self.rename_tool:
            self.rename_tool.deleteLater()
            self.rename_tool = None
        self.show()
        self.update_RB_QTableWidget0() # 更新右侧RB_QTableWidget0表格 

    def on_image_process_window_closed(self):
        """处理图片处理子窗口关闭事件"""
        if self.image_process_window:
            self.image_process_window.deleteLater()
            self.image_process_window = None
        self.show() 

    def on_bat_tool_closed(self):
        """处理批量执行命令工具关闭事件"""
        if self.bat_tool:
            self.bat_tool.deleteLater()
            self.bat_tool = None
        self.show()

    def on_mipi2ram_tool_closed(self):
        """处理MIPI RAW文件转换为JPG文件工具关闭事件"""
        if self.mipi2raw_tool:
            self.mipi2raw_tool.deleteLater()
            self.mipi2raw_tool = None
        self.show()


    def closeEvent(self, event):
        """重写关闭事件以保存设置和清理资源"""
        print("closeEvent()-主界面--关闭事件")
        self.save_settings()  # 保存关闭时基础设置
        self.cleanup()        # 清除内存
        print("接受主界面关闭事件, 保存关闭前的配置并清理内存")
        event.accept()



"""
python对象命名规范
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

类名都使用首字母大写开头(Pascal命名风格)的规范

全局变量全用大写字母，单词之间用 _分割

普通变量用小写字母，单词之间用 _分割

普通函数和普通变量一样；

私有函数以 __ 开头(2个下划线),其他和普通函数一样
"""



if __name__ == '__main__':
    print("[hiviewer主程序启动]:")

    # 初始化日志文件
    # setup_logging()  

    # 设置主程序app
    app = QApplication(sys.argv)
    window = HiviewerMainwindow()
    sys.exit(app.exec_())