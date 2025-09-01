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

"""记录程序启动时间"""
import time
flag_start = time.time()

"""导入python内置模块"""
import gc
import os
import sys
import json
import subprocess
from pathlib import Path
from itertools import zip_longest
import shutil
import stat

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
from src.view.sub_compare_image_view import SubMainWindow                   # 假设这是你的子窗口类名
from src.view.sub_compare_video_view import VideoWall                       # 假设这是你的子窗口类名 
from src.view.sub_rename_view import FileOrganizer                          # 添加这行以导入批量重名名类名
from src.view.sub_image_process_view import SubCompare                      # 确保导入 SubCompare 类
from src.view.sub_bat_view import LogVerboseMaskApp                         # 导入批量执行命令的类
from src.view.sub_search_view import SearchOverlay                          # 导入图片搜索工具类(ctrl+f)
from src.components.ui_main import Ui_MainWindow                            # 假设你的主窗口类名为Ui_MainWindow
from src.components.custom_qMbox_showinfo import show_message_box           # 导入消息框类
from src.components.custom_qdialog_about import AboutDialog                 # 导入关于对话框类,显示帮助信息
from src.components.custom_qdialog_LinkQualcomAebox import Qualcom_Dialog   # 导入高通工具自定义对话框的类
from src.components.custom_qdialog_LinkUnisocAebox import Unisoc_Dialog     # 导入展锐工具自定义对话框的类
from src.components.custom_qdialog_LinkMTKAebox import MTK_Dialog           # 导入展锐工具自定义对话框的类
from src.components.custom_qdialog_rename import SingleFileRenameDialog     # 导入自定义重命名对话框类
from src.components.custom_qCombox_spinner import (                         # 导入自定义下拉框类中的数据模型和委托代理类
CheckBoxListModel, CheckBoxDelegate)       
from src.components.custom_qdialog_progress import (                        # 导入自定义压缩进度对话框类
ProgressDialog, CompressWorker)      
from src.common.img_preview import ImageViewer                              # 导入自定义图片预览组件  
from src.common.manager_font import MultiFontManager                        # 字体管理器
from src.common.manager_version import version_init, fastapi_init           # 版本号&IP地址初始化
from src.common.manager_color_exif import load_color_settings               # 导入自定义json配置文件
from src.common.manager_log import setup_logging, get_logger                # 导入日志文件相关配置
from src.common.decorator import (                                          # 导入自定义装饰器函数 
CC_TimeDec, log_performance_decorator, log_error_decorator)             
from src.utils.raw2jpg import Mipi2RawConverterApp                          # 导入MIPI RAW文件转换为JPG文件的类
from src.utils.update import check_update, pre_check_update                 # 导入自动更新检查程序
from src.utils.hisnot import WScreenshot                                    # 导入截图工具类
from src.utils.xml import save_excel_data                                   # 导入xml文件解析工具类
from src.utils.delete import (                                              # 导入强制删除文件夹功能函数，清除日志，清除缓存相关函数
force_delete_folder, clear_log_files,clear_cache_files)          
from src.utils.Icon import IconCache, ImagePreloader                        # 导入文件Icon图标加载类
from src.utils.heic import extract_jpg_from_heic                            # 导入heic文件解析工具类
from src.utils.video import extract_video_first_frame                       # 导入视频预览工具类
from src.utils.image import ImageProcessor                                  # 导入图片处理工具类
from src.utils.sort import sort_by_custom                                   # 导入文件排序工具类
from src.utils.aebox_link import (                                          # 导入Fast API配置与Aebox通信
check_process_running, urlencode_folder_path, get_api_data)



"""
设置主界面类区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
class HiviewerMainwindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(HiviewerMainwindow, self).__init__(parent)

        # 记录程序启动时间；设置图标路径；读取本地版本信息，并初始化新版本信息
        self.start_time = flag_start

        # 获取活动的日志记录器,打印相关信息
        self.logger = get_logger(__name__)
        self.logger.info(f""" {"-" * 25} hiviewer主程序开始启动 {"-" * 25}""")
        print(f"----------[程序预启动时间]----------: {(time.time()-self.start_time):.2f} 秒")
        self.logger.info(f"""[ 程序预启动 ]-->耗时: {(time.time()-self.start_time):.2f} 秒""")

        # 设置icon路径以及版本信息和fast api地址端口的初始化
        self.base_icon_path = Path(__file__).parent / "resource" / "icons"
        self.version_info, self.new_version_info,  = version_init(), False     
        self.fast_api_host, self.fast_api_port = fastapi_init()
        
        # 创建启动画面、启动画面、显示主窗口以及相关初始化在self.update_splash_message()函数通过定时器实现
        self.create_splash_screen()

    @CC_TimeDec(tips="初始化所有组件", show_time=True, show_args=False)
    @log_performance_decorator(tips="初始化所有组件", log_args=False, log_result=False)
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


    @log_performance_decorator(tips="变量初始化", log_args=False, log_result=False)
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
    @log_performance_decorator(tips="创建hiviewer的启动画面 | 设置定时器后台初始化配置", log_args=False, log_result=False)
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
        x, y, _, _ = self.get_screen_geometry()
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
        self.logger.info(f"【第 {self.fla} 次】-->进入定时器更新函数【update_splash_message()】中 | 当前程序运行时长: {(time.time()-self.start_time):.2f} 秒")
              

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
            x, y, _, _ = self.get_screen_geometry()
            self.move(x, y)

            # 预先检查更新  
            self.pre_update()

            # 延时显示主窗口,方便启动画面渐出
            QTimer.singleShot(800, self.show)


            # 记录结束时间并计算耗时
            self.preview_label.setText(f"⏰启动耗时: {(time.time()-self.start_time):.2f} 秒")
            print(f"----------[hiviewer主程序启动成功], 共耗时: {(time.time()-self.start_time):.2f} 秒----------")
            self.logger.info(f"""{"-" * 25} hiviewer主程序启动成功 | 共耗时: {(time.time()-self.start_time):.2f} 秒{"-" * 25}""")
            

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
    def get_screen_geometry(self)->tuple:
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
        try:
            screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
            screen_geometry = QApplication.desktop().screenGeometry(screen)
            x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
            y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
            w = screen_geometry.width()
            h = screen_geometry.height()
            return x, y, w, h
        except Exception as e:
            self.logger.error(f"get_screen_geometry()-->无法获取当前鼠标所在屏幕信息 | 报错：{e}")



    """
    设置右键菜单函数区域开始线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """
    @log_performance_decorator(tips="设置右侧表格区域的右键菜单", log_args=False, log_result=False)
    def setup_context_menu(self):
        """设置右侧表格区域的右键菜单"""
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
        icon_path = (self.base_icon_path / "log.png").as_posix()
        log_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "restart_ico_96x96.ico").as_posix()
        restart_icon = QIcon(icon_path)
        icon_path = (self.base_icon_path / "16gl-0.png").as_posix()
        icon_0 = QIcon(icon_path)
        icon_path = (self.base_icon_path / "16gl-1.png").as_posix()
        icon_1 = QIcon(icon_path)
        icon_path = (self.base_icon_path / "16gl-2.png").as_posix()
        icon_2 = QIcon(icon_path)
        icon_path = (self.base_icon_path / "16gl-3.png").as_posix()
        icon_3 = QIcon(icon_path)
        icon_path = (self.base_icon_path / "16gl-4.png").as_posix()
        icon_4 = QIcon(icon_path)
        icon_path = (self.base_icon_path / "16gl-5.png").as_posix()
        icon_5 = QIcon(icon_path)

        # 创建二级菜单-删除选项
        sub_menu = QMenu("删除选项", self.context_menu) 
        sub_menu.setIcon(delete_icon)  
        sub_menu.addAction(icon_0, "从列表中删除(D)", self.delete_from_list)  
        sub_menu.addAction(icon_1, "从原文件删除(Ctrl+D)", self.delete_from_file)  

        # 创建二级菜单-复制选项
        sub_menu2 = QMenu("复制选项", self.context_menu)  
        sub_menu2.setIcon(paste_icon)  
        sub_menu2.addAction(icon_0, "复制文件路径(C)", self.copy_selected_file_path)  
        sub_menu2.addAction(icon_1, "复制文件(Ctrl+C)", self.copy_selected_files)  

        # 创建二级菜单-无损旋转
        sub_menu3 = QMenu("无损旋转", self.context_menu)  
        sub_menu3.setIcon(rotator_icon)  
        sub_menu3.addAction(icon_0, "逆时针旋转", lambda: self.jpg_lossless_rotator('l'))  
        sub_menu3.addAction(icon_1, "顺时针旋转", lambda: self.jpg_lossless_rotator('r'))  
        sub_menu3.addAction(icon_2, "旋转180度", lambda: self.jpg_lossless_rotator('u'))  
        sub_menu3.addAction(icon_3, "水平翻转", lambda: self.jpg_lossless_rotator('h'))  
        sub_menu3.addAction(icon_4, "垂直翻转", lambda: self.jpg_lossless_rotator('v'))  
        sub_menu3.addAction(icon_5, "自动校准EXIF旋转信息", lambda: self.jpg_lossless_rotator('auto'))  

        # 创建二级菜单-按行筛选
        sub_menu4 = QMenu("按行筛选", self.context_menu)  
        sub_menu4.setIcon(filtrate_icon)  
        sub_menu4.addAction(icon_0, "奇数行", lambda: self.show_filter_rows('odd'))  
        sub_menu4.addAction(icon_1, "偶数行", lambda: self.show_filter_rows('even'))  
        sub_menu4.addAction(icon_2, "3选1", lambda: self.show_filter_rows('three_1'))  
        sub_menu4.addAction(icon_3, "3选2", lambda: self.show_filter_rows('three_2'))  
        sub_menu4.addAction(icon_4, "5选1", lambda: self.show_filter_rows('five_1'))  

        # 创建二级菜单-平台图片解析工具
        sub_menu5 = QMenu("平台图片解析工具", self.context_menu)  
        sub_menu5.setIcon(exif_icon)  
        sub_menu5.addAction(icon_0, "高通_C7工具解析图片(I)", self.on_i_pressed)  
        sub_menu5.addAction(icon_1, "联发科_DP工具解析图片(U)", self.on_u_pressed)  
        sub_menu5.addAction(icon_2, "展锐_IQT工具解析图片(Y)", self.on_y_pressed)  


        # 将二级菜单添加到主菜单
        self.context_menu.addMenu(sub_menu)   
        self.context_menu.addMenu(sub_menu2)  
        self.context_menu.addMenu(sub_menu4)  
        self.context_menu.addMenu(sub_menu5) 
        self.context_menu.addMenu(sub_menu3)  
        
        
        # 设置右键菜单槽函数
        # self.context_menu.addAction(exif_icon, "高通AEC10解析图片(I)", self.on_i_pressed)
        self.context_menu.addAction(zip_icon, "压缩文件(Z)", self.compress_selected_files)
        self.context_menu.addAction(theme_icon, "切换主题(P)", self.on_p_pressed)
        self.context_menu.addAction(image_size_reduce_icon, "图片瘦身(X)", self.jpgc_tool) 
        self.context_menu.addAction(ps_icon, "图片调整(L)", self.on_l_pressed)
        self.context_menu.addAction(tcp_icon, "截图功能(T)", self.screen_shot_tool)
        self.context_menu.addAction(command_icon, "批量执行命令工具(M)", self.open_bat_tool)
        self.context_menu.addAction(rename_icon, "批量重命名工具(F4)", self.on_f4_pressed)
        self.context_menu.addAction(raw_icon, "RAW转JPG工具(F1)", self.on_f1_pressed)
        self.context_menu.addAction(log_icon, "打开日志文件(F3)", self.on_f3_pressed)
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

    @log_performance_decorator(tips="设置左侧文件浏览器右键菜单", log_args=False, log_result=False)
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
        send_path_to_aebox = self.treeview_context_menu.addAction("发送到aebox")

        zoom_action = self.treeview_context_menu.addAction("按zoom分类")
        size_action = self.treeview_context_menu.addAction("按size分类")

        copy_path_action = self.treeview_context_menu.addAction("复制路径")
        rename_action = self.treeview_context_menu.addAction("重命名")
        open_action = self.treeview_context_menu.addAction("打开")
        breakup_acton = self.treeview_context_menu.addAction("解散")
        delete_action = self.treeview_context_menu.addAction("删除")

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
            breakup_acton.triggered.connect(lambda: self.breakup_folder(file_path))
            delete_action.triggered.connect(lambda: self.delete_file(file_path))

            # 连接zoom值分类信号槽函数
            zoom_action.triggered.connect(lambda: self.zoom_file(file_path))
            size_action.triggered.connect(lambda: self.size_file(file_path))

            # 设置右键菜单绑定左侧文件浏览器
            self.treeview_context_menu.exec_(self.Left_QTreeView.viewport().mapToGlobal(pos))


    
    """
    设置右键菜单函数区域结束线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """

    @log_performance_decorator(tips="设置主界面图标以及标题", log_args=False, log_result=False)
    def set_stylesheet(self):
        """设置主界面图标以及标题"""
        # print("[set_stylesheet]-->设置主界面相关组件")

        self.icon_path = os.path.join(self.base_icon_path, "viewer_3.ico")
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowTitle(f"HiViewer")

        # 根据鼠标的位置返回当前光标所在屏幕的几何信息
        _, _, w, h = self.get_screen_geometry()
        width, height = int(w * 0.65), int(h * 0.65)
        self.resize(width, height)

        # 启用拖放功能
        self.setAcceptDrops(True)

        """界面底部状态栏设置"""
        # self.statusbar --> self.statusbar_widget --> self.statusbar_QHBoxLayout --> self.statusbar_button1 self.statusbar_button2
        # 设置按钮无边框
        self.statusbar_button1.setFlat(True)
        self.statusbar_button2.setFlat(True)
        self.statusbar_button3.setFlat(True)

        # 初始化版本更新按钮文本
        self.statusbar_button2.setText(f"🌼{self.version_info}")            

        # 初始化FastAPI按钮文本 🐹
        self.statusbar_button3.setText(f"{self.fast_api_host}:{self.fast_api_port}")     

        # 初始化标签文本
        self.statusbar_label1.setText(f"📢:进度提示标签🍃")
        self.statusbar_label0.setText(f"📢:选中或筛选的文件夹中包含{self.image_index_max}张图")
        self.statusbar_label.setText(f"💦已选文件数[0]个")

        
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
        # 设置下拉框可编辑，设置下拉框文本不可编辑，设置下拉框提示文本
        self.RT_QComboBox1.setEditable(True)
        self.RT_QComboBox1.lineEdit().setReadOnly(True)  
        self.RT_QComboBox1.lineEdit().setPlaceholderText("请选择") 
        
    @log_performance_decorator(tips="快捷键和槽函数连接事件", log_args=False, log_result=False)
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
        # 添加快捷键F2，打开单个或多个文件重命名对话框
        self.f2_shortcut = QShortcut(QKeySequence(Qt.Key_F2), self)
        self.f2_shortcut.activated.connect(self.on_f2_pressed)
        # 添加快捷键F3，打开日志文件
        self.f2_shortcut = QShortcut(QKeySequence(Qt.Key_F3), self)
        self.f2_shortcut.activated.connect(self.on_f3_pressed)
        # 添加快捷键F4，打开批量执行命令工具
        self.f4_shortcut = QShortcut(QKeySequence(Qt.Key_F4), self)
        self.f4_shortcut.activated.connect(self.on_f4_pressed)
        # 添加快捷键 F5,刷新表格
        self.f5_shortcut = QShortcut(QKeySequence(Qt.Key_F5), self)
        self.f5_shortcut.activated.connect(self.on_f5_pressed)
        # 添加快捷键 i 打开高通工具解析窗口
        self.p_shortcut = QShortcut(QKeySequence('i'), self)
        self.p_shortcut.activated.connect(self.on_i_pressed)
        # 添加快捷键 u 打开MTK工具解析窗口
        self.p_shortcut = QShortcut(QKeySequence('u'), self)
        self.p_shortcut.activated.connect(self.on_u_pressed)
        # 添加快捷键 y 打开高通工具解析窗口
        self.p_shortcut = QShortcut(QKeySequence('y'), self)
        self.p_shortcut.activated.connect(self.on_y_pressed)
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
        self.statusbar_checkbox.stateChanged.connect(self.fast_api_switch)
        self.statusbar_button3.clicked.connect(self.fast_api)  # 127.0.0.1:8000按钮槽函数


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

    def zoom_file(self, path):
        """按zoom值分类"""
        from src.utils.cls_zoom_size import classify_images_by_zoom
        classify_images_by_zoom(path)

    def size_file(self, path):
        """按尺寸分类"""
        from src.utils.cls_zoom_size import classify_images_by_size
        classify_images_by_size(path)


    def breakup_folder(self, folder_path):
        """解散选中的文件夹，将文件夹中的所有文件移动到上一级文件夹后删除空文件夹"""
        try:
            # 检查路径是否存在且为文件夹
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                return

            # 获取父文件夹路径
            parent_folder = os.path.dirname(folder_path)

            # 获取文件夹中的所有文件（包括子文件夹中的文件）
            all_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径，用于在父文件夹中重建目录结构
                    rel_path = os.path.relpath(file_path, folder_path)
                    all_files.append((file_path, rel_path))

            # 如果文件夹为空，直接删除
            if not all_files:
                os.rmdir(folder_path)
                return

            # 移动所有文件
            for file_path, rel_path in all_files:
                try:
                    # 构建目标路径
                    target_path = os.path.join(parent_folder, rel_path)
                    target_dir = os.path.dirname(target_path)

                    # 创建目标目录（如果不存在）
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir, exist_ok=True)

                    # 处理文件名冲突
                    if os.path.exists(target_path):
                        base_name, ext = os.path.splitext(target_path)
                        counter = 1
                        while os.path.exists(target_path):
                            target_path = f"{base_name}_{counter}{ext}"
                            counter += 1

                    # 移动文件
                    shutil.move(file_path, target_path)

                except Exception as e:
                    print(f"移动文件失败 {file_path}: {e}")
                    continue

            # 删除原文件夹（现在应该是空的）
            shutil.rmtree(folder_path, ignore_errors=True)

            # 刷新文件系统模型和表格
            self.file_system_model.setRootPath('')
            self.Left_QTreeView.viewport().update()
            self.update_RB_QTableWidget0()

        except Exception as e:
            print(f"[breakup_folder]-->解散文件夹失败: {e}")

    def delete_file(self, path):
        """安全删除文件/文件夹"""
        try:
            if not os.path.exists(path):
                return
                
            # Windows系统处理只读属性
            def remove_readonly(func, path, _):
                os.chmod(path, stat.S_IWRITE)
                func(path)

            if os.path.isfile(path): # 移除只读属性, 删除文件
                os.chmod(path, stat.S_IWRITE)
                os.remove(path)
            else: # 删除文件夹
                shutil.rmtree(path, onerror=remove_readonly if os.name == 'nt' else None)

        except Exception as e:
            show_message_box(f"删除失败: {str(e)}", "错误", 2000)

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

            if not check_process_running("aebox"):
                show_message_box(f"未检测到aebox进程，请先手动打开aebox软件", "错误", 1500)
                return

            if not self.statusbar_checkbox.isChecked():
                show_message_box(f"未启用Fast_API功能,请先手动打开界面底部复选框启用", "错误", 1500)
                return

            # url编码
            image_path_url = urlencode_folder_path(path)
            if image_path_url:
                # 拼接文件夹
                image_path_url = f"http://{self.fast_api_host}:{self.fast_api_port}/set_image_folder/{image_path_url}"
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
    @log_performance_decorator(tips="模仿用户按下回车键", log_args=False, log_result=False)
    def input_enter_action(self):
        # 输出相关log信息
        print("[input_enter_action]-->在地址栏按下回车/拖拽了文件进来,开始在左侧文浏览器中定位") 
        
        # 定位到左侧文件浏览器中
        self.locate_in_tree_view()
        # 初始化同级文件夹下拉框选项
        self.RT_QComboBox1_init()
        # 更新右侧表格
        self.update_RB_QTableWidget0()


    def clear_combox(self):
        print("[clear_combox]-清除按钮被点击")
        # 清空地址栏
        self.RT_QComboBox.clear()
        # 刷新右侧表格
        self.update_RB_QTableWidget0()
        # 手动清除图标缓存
        IconCache.clear_cache()
        # 清除日志文件
        self.clear_log_and_cache_files()
        # 释放内存
        self.cleanup() 
        


    def compare(self):
        print("[compare]-对比按钮被点击")
        self.on_space_pressed()


    def setting(self):
        print("[setting]-设置按钮被点击")
        # 暂时调用关于信息，后续添加设置界面
        self.on_ctrl_h_pressed()
    

    def update(self):
        print("[update]-版本按钮被点击")
        check_update()


    def fast_api_switch(self):
        """设置fast_api服务的开关使能"""
        try:
            font = self.statusbar_button3.font()
            if self.statusbar_checkbox.isChecked():
                # False = 关闭横线
                font.setStrikeOut(False)        
                self.statusbar_button3.setFont(font)
        
            else:
                # True = 显示横线
                font.setStrikeOut(True)        
                self.statusbar_button3.setFont(font)
                
        except Exception as e:
            print(f"[fast_api_switch]-error--设置fast_api开关使能失败: {e}")
            return

    def fast_api(self):
        """设置fast_api服务地址"""
        try:
            from src.components.custom_qdialog_fastapi import FastApiDialog 
            dialog = FastApiDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self.fast_api_host, self.fast_api_port = dialog.get_result()
                
                # 打印log
                print(f"[fast_api]-->设置FastAPI服务地址: {self.fast_api_host}:{self.fast_api_port}")

                # 更新底部信息栏按钮信息显示
                self.statusbar_button3.setText(f"{self.fast_api_host}:{self.fast_api_port}")

                # 保存fast_api地址和端口到ipconfig.ini配置文件
                FASTAPI=f"[API]\nhost = {self.fast_api_host}\nport = {self.fast_api_port}"
                default_version_path = Path(__file__).parent / "config" / "ipconfig.ini"
                default_version_path.parent.mkdir(parents=True, exist_ok=True)
                with open(default_version_path, 'w', encoding='utf-8') as f:
                    f.write(FASTAPI)
            else:
                print("[fast_api]-->取消设置FastAPI服务地址")
        except Exception as e:
            print(f"[fast_api]-error--设置fast_api失败: {e}")
            return


    @log_performance_decorator(tips="预更新版本", log_args=False, log_result=False)
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
            print(f"[pre_update]-error--预更新版本失败: {e}")
            return
        
    def show_exif(self):
        """打开Exif信息显示，类似快捷键CTRL+P功能  """
        print("[show_exif]-打开Exif信息显示")

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
            print(f"[show_exif]-error--打开Exif信息显示失败: {e}")
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
            print(f"[show_filter_rows]-error--显示筛选行失败: {e}")
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
            print(f"[filter_rows]-error--批量选中指定模式行失败: {e}")
            return

    def jpg_lossless_rotator(self, para=''):
        """无损旋转图片"""
        print(f"[jpg_lossless_rotator]-启动无损旋转图片任务:")
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
            print(f"[jpg_lossless_rotator]-error--无损旋转图片失败: {e}")
            return


    def get_selected_file_path(self):
            """获取选中的单元格的文件路径
            函数功能说明：捕获主界面右侧选中的所有单元格，解析出完整文件路径，汇总到列表file_full_path_list中并返回
            """
            try:
                # 获取表格选中项，并判断是否有值返回
                if not (selected_items := self.RB_QTableWidget0.selectedItems()):
                    return []

                # 定义存储选中单元格完整文件路径列表，解析出选中单元格获取完整路径
                file_full_path_list = []  
                for item in selected_items:
                    row, col = item.row(), item.column()
                    # 高效提取路径方法, 根据表格索引直接从self.paths_list中拿文件路径
                    if (full_path := self.paths_list[col][row]) and os.path.isfile(full_path):
                        file_full_path_list.append(full_path) 
                    else: # 常规拼接构建完整路径的办法，效率较低
                        if(full_path := self.get_single_full_path(row, col)): 
                            file_full_path_list.append(full_path) 
                return file_full_path_list
            except Exception as e:
                print(f"[get_selected_file_path]-->error: 获取文件路径失败: {e}")
                self.logger.error(f"【get_selected_file_path】-->获取选中的单元格的文件路径 | 报错: {e}")
                return []


    def get_single_full_path(self, row, col):
            """获取主界面右侧表格被选中的单个单元格完整文件路径--常规拼接方法
            函数功能说明: 根据捕获的单个单元格索引, 解析拼接出完整文件路径并返回
            """
            try:
                single_file_full_path = "" # 初始化单个文件完整路径为空字符串
                file_name = self.RB_QTableWidget0.item(row, col).text().split('\n')[0]      # 获取文件名
                column_name = self.RB_QTableWidget0.horizontalHeaderItem(col).text()        # 获取列名
                current_directory = self.RT_QComboBox.currentText()                         # 获取当前选中的目录
                # 构建文件完整路径并判断文件是否存在，存在则返回对应文件路径str
                if (full_path := Path(current_directory).parent / column_name / file_name) and full_path.exists():        
                    single_file_full_path = full_path.as_posix()    
                return single_file_full_path
            except Exception as e:
                print(f"[get_single_full_path]-->error: 获取被选中的单个单元格完整文件路径失败: {e}")
                self.logger.error(f"【get_single_full_path】-->获取被选中的单个单元格完整文件路径 | 报错: {e}")
                return ""


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
            print(f"[copy_selected_file_path]-error--复制文件路径失败: {e}")
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
            print(f"[copy_selected_files]-error--复制文件失败: {e}")
            return


    def delete_from_list(self):
        """从列表中删除选中的单元格"""
        print(f"[delete_from_list]-从列表中删除选中的单元格")

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
            print(f"[delete_from_list]-error--删除失败: {e}")
            return

    def delete_from_file(self):
        """从源文件删除选中的单元格并删除原文件"""
        print(f"[delete_from_file]-从原文件删除选中的单元格并删除原文件")

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
            show_message_box(f"{len(file_paths_to_delete)} 个文件已从列表中删除并删除原文件", "提示", 1000)
            self.update_RB_QTableWidget0()

        except Exception as e:
            print(f"[delete_from_file]-error--删除失败: {e}")
            return


    def compress_selected_files(self):
        """压缩选中的文件并复制压缩包文件到剪贴板"""
        print("[compress_selected_files]-启动压缩文件任务")
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
            print(f"[compress_selected_files]-error--压缩失败: {e}")
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
        self.statusbar_label1.setText(f"📢:压缩完成🍃")
        show_message_box(f"文件已压缩为: {zip_path} 并复制到剪贴板", "提示", 500)

    def on_compress_error(self, error_msg):
        """处理压缩错误"""
        self.progress_dialog.close()  
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"📢:压缩出错🍃")
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
        self.statusbar_label.setText(f"💦已选文件数[0]个")

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
            # 输出日志文件
            self.logger.info(f"update_RB_QTableWidget0_from_list()-->启动从当前列表中更新表格函数任务")    
           
            # 先取消当前的预加载任务
            self.cancel_preloading()
           
            # 清空表格和缓存
            self.RB_QTableWidget0.clear()
            self.RB_QTableWidget0.setRowCount(0)
            self.RB_QTableWidget0.setColumnCount(0)

            # 先初始化表格结构和内容，不加载图标,并获取图片列有效行最大值
            self.image_index_max = self.init_table_structure(file_infos_list, dir_name_list)

            # 对file_paths进行转置,实现加载图标按行加载,使用列表推导式
            file_name_paths = [path for column in zip_longest(*file_paths, fillvalue=None) for path in column if path is not None]

            # 确保文件路径存在后，开始预加载
            if file_name_paths:  
                self.start_image_preloading(file_name_paths)

        except Exception as e:
            print(f"[update_RB_QTableWidget0_from_list]-->error--从当前列表中更新表格任务失败: {e}")
            self.logger.error(f"[update_RB_QTableWidget0_from_list]-->从当前列表中更新表格任务失败: {e}")


    def update_RB_QTableWidget0(self):
        """更新右侧表格功能函数"""
        try:
            # 输出日志文件
            self.logger.info(f"update_RB_QTableWidget0()-->执行--更新右侧表格功能函数任务")

            # 取消当前的预加载任务
            self.cancel_preloading()

            # 清空表格和缓存
            self.RB_QTableWidget0.clear()
            self.RB_QTableWidget0.setRowCount(0)
            self.RB_QTableWidget0.setColumnCount(0)
            
            # 收集文件名基本信息以及文件路径，并将相关信息初始化为类中全局变量
            file_infos_list, file_paths, dir_name_list = self.collect_file_paths()
            self.files_list = file_infos_list      # 初始化文件名及基本信息列表
            self.paths_list = file_paths           # 初始化文件路径列表
            self.dirnames_list = dir_name_list     # 初始化选中的同级文件夹列表

            # 先初始化表格结构和内容，不加载图标,并获取图片列有效行最大值
            self.image_index_max = self.init_table_structure(file_infos_list, dir_name_list)    
            # 重绘表格
            self.RB_QTableWidget0.repaint()

            # 对file_paths进行转置,实现加载图标按行加载，并初始化预加载图标线程前的问价排列列表
            file_name_paths = [path for column in zip_longest(*file_paths, fillvalue=None) for path in column if path is not None]
            self.preloading_file_name_paths = file_name_paths 

            # 开始预加载图标    
            if file_name_paths:  # 确保有文件路径才开始预加载
                self.start_image_preloading(file_name_paths)

        except Exception as e:
            self.logger.error(f"update_RB_QTableWidget0()-->执行报错--更新右侧表格功能函数任务失败: {e}")

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
            self.statusbar_label0.setText(f"🎃已选文件夹数{pic_num_list}个 ")  

            return pic_num_list
        except Exception as e:
            print(f"[init_table_structure]-->初始化表格结构和内容失败: {e}")
            self.logger.error(f"init_table_structure()-->初始化表格结构和内容失败: {e}")
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
            self.logger.info(f"start_image_preloading()-->图标预加载线程已启动, 跳过该函数")
            return
        
        # 输出打印日志文件
        print("[start_image_preloading]-->开始预加载图标, 启动预加载线程")
        self.logger.info(f"start_image_preloading()-->开始预加载图标, 启动预加载线程")

        # 设置预加载状态以及时间
        self.preloading = True
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
            self.logger.error(f"start_image_preloading()-->开始预加载图标,启动预加载线程失败: {e}")

    
    def cancel_preloading(self):
        """取消当前预加载任务"""
        try:
            # 执行取消预加载任务
            if self.current_preloader and self.preloading:
                self.current_preloader._stop = True  
                self.preloading = False
                self.current_preloader = None     
        except Exception as e:
            print(f"[cancel_preloading]-->取消当前预加载任务失败: {e}")
            self.logger.error(f"cancel_preloading()-->执行报错--取消当前预加载任务: {e}")

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
        self.statusbar_label1.setText(f"📢:图标加载进度...{current}/{total}🍃")
        
    def on_preload_finished(self):
        """处理预加载完成"""
        # 打印并输出日志信息
        print(f"[on_preload_finished]-->所有图标预加载完成,耗时:{time.time()-self.start_time_image_preloading:.2f}秒")
        self.logger.info(f"on_preload_finished()-->所有图标预加载完成 | 耗时:{time.time()-self.start_time_image_preloading:.2f}秒")
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"📢:图标已全部加载-^-耗时:{time.time()-self.start_time_image_preloading:.2f}秒🍃")
        gc.collect()
        
    def on_preload_error(self, error):
        """处理预加载错误"""
        print(f"[on_preload_error]-->图标预加载错误: {error}")
        self.logger.error(f"on_preload_error-->图标预加载错误: {error}")

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
            self.logger.error(f"updateComboBox1Text()-->更新显示文本下拉框失败: {e}")

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

    
    def handle_table_selection(self):
        """处理主界面右侧表格选中事件
        函数功能说明: 获取当前主界面表格中选中的单元格，如果选中的单元格为图片或视频文件，将会在左侧预览区显示预览图像
        """
        try:
            # 看图子界面更新图片时忽略表格选中事件
            if self.compare_window and self.compare_window.is_updating:
                # 若预览区域显示的是ImageViewer，清空旧预览内容, 显示label
                if (self.verticalLayout_left_2.itemAt(0) and self.verticalLayout_left_2.itemAt(0).widget() 
                    and type(self.verticalLayout_left_2.itemAt(0).widget()).__name__ == "ImageViewer"):
                    self.clear_preview_layout()
                    self.show_preview_error("预览区域")
                return
            
            # 非拖拽模式，不显示预览图
            if not self.drag_flag:
                self.clear_preview_layout() 
                self.show_preview_error("非拖拽模式!\n不显示预览图.\n【ALT+A】键启用拖拽模式")
                return

            # 获取选中单元格完整文件路径列表, 若存在则进行预览区域内容更新
            if (file_paths := self.get_selected_file_path()):
                # 清空旧预览内容
                self.clear_preview_layout() 
                # 根据预览文件完整路径动态选则预览区显示图像
                self.display_preview_image_dynamically(file_paths[0])
                # 更新状态栏显示选中数量
                self.statusbar_label.setText(f"💦已选文件数[{len(file_paths)}]个")
        except Exception as e:
            print(f"[handle_table_selection]-->处理表格选中事件失败: {e}")
            self.logger.error(f"【handle_table_selection】-->处理主界面右侧表格选中事件 | 报错: {e}")


    def display_preview_image_dynamically(self, preview_file_path):
        """动态显示预览图像"""
        try:
            # 统一转换传入文件路径的为小写字母
            file_path = preview_file_path.lower()
            # 根据文件类型创建预览, 图片文件处理
            if file_path.endswith(tuple(self.IMAGE_FORMATS)):
                # 处理HEIC格式图片，成功提取则创建并显示图片预览，反之则显示提取失败
                if file_path.endswith(tuple(".heic")):
                    if (new_path := extract_jpg_from_heic(preview_file_path)):
                        self.create_image_preview(new_path)
                    else: 
                        self.show_preview_error("提取HEIC图片失败")
                else: # 非".heic"格式图片直接创建并显示预览图像
                    self.create_image_preview(preview_file_path)
            # 视频文件处理
            elif file_path.endswith(tuple(self.VIDEO_FORMATS)):
                # 提取视频文件首帧图，创建并显示预览图
                if video_path := extract_video_first_frame(preview_file_path):
                    self.create_image_preview(video_path)     
                else:
                    self.show_preview_error("视频文件预览失败")
            # 非图片/视频格式文件处理
            else:
                self.show_preview_error("不支持预览的文件类型")
        except Exception as e:
            print(f"[display_preview_image_dynamically]-->动态显示预览图像: {e}")
            self.logger.error(f"【display_preview_image_dynamically】-->动态显示预览图像 | 报错: {e}")


    def clear_preview_layout(self):
        """清空预览区域"""
        try:
            # 清理 image_viewer 引用
            if hasattr(self, 'image_viewer') and self.image_viewer:
                try:
                    # 先调用自定义清理方法
                    if hasattr(self.image_viewer, 'cleanup'):
                        self.image_viewer.cleanup()
                    # 然后删除对象
                    self.image_viewer.deleteLater()
                except Exception as e:
                    self.logger.error(f"clear_preview_layout()-->清理image_viewer失败: {e}")
                finally:
                    self.image_viewer = None
            
            # 清理布局中的所有组件
            while self.verticalLayout_left_2.count():
                item = self.verticalLayout_left_2.takeAt(0)
                widget = item.widget()
                if widget:
                    try:
                        widget.deleteLater()
                    except Exception as e:
                        self.logger.error(f"clear_preview_layout()-->清理widget失败: {e}")
        except Exception as e:
            show_message_box("清空预览区域报错!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.error(f"【clear_preview_layout】-->清空预览区域 | 报错: {e}")

    
    def create_image_preview(self, path):
        """创建图片预览"""
        try:
            # 清空旧预览内容
            self.clear_preview_layout()
            # 创建 ImageViewer 实例-->加载图片-->添加到layout
            self.image_viewer = ImageViewer(self.Left_QFrame)
            self.image_viewer.load_image(path)
            self.verticalLayout_left_2.addWidget(self.image_viewer)
            self.Left_QFrame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception as e:
            show_message_box("创建图片预览报错!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.error(f"【create_image_preview】-->创建图片预览 | 报错: {e}")


    def show_preview_error(self, message):
        """显示预览错误信息"""
        try:
            error_label = QLabel(message)
            error_label.setStyleSheet("color: white;")
            error_label.setFont(self.custom_font_jetbrains)
            error_label.setAlignment(Qt.AlignCenter)
            self.verticalLayout_left_2.addWidget(error_label)
        except Exception as e:
            show_message_box("显示预览错误信息报错!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.error(f"【show_preview_error】-->显示预览错误信息 | 报错：{e}")

    def handle_sort_option(self):
        """处理排序选项"""
        try:
            self.logger.info(f"handle_sort_option()-->执行函数任务，处理排序下拉框事件")
            sort_option = self.RT_QComboBox2.currentText()
            if self.simple_mode:
                if sort_option == "按曝光时间排序" or sort_option == "按曝光时间逆序排序":
                    # 弹出提示框，设置排序选项为默认排序
                    show_message_box("极简模式下不使能曝光时间排序，\nALT+I快捷键可切换进入极简模式", "提示", 1000)
                    self.RT_QComboBox2.setCurrentText("按文件名称排序")
                elif sort_option == "按ISO排序" or sort_option == "按ISO逆序排序":
                    # 弹出提示框，设置排序选项为默认排序
                    show_message_box("极简模式下不使能ISO排序, \nALT+I快捷键可切换进入极简模式", "提示", 1000)
                    self.RT_QComboBox2.setCurrentText("按文件名称排序")
            self.update_RB_QTableWidget0() # 更新右侧表格 
        except Exception as e:
            show_message_box("处理排序下拉框事件!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.error(f"【handle_sort_option】-->处理排序下拉框事件 | 报错：{e}")


    @log_error_decorator(tips=f"处理主题切换下拉框选择事件")
    def handle_theme_selection(self, index=None):
        """处理下拉框选择事件"""
        self.current_theme = "默认主题" if self.RT_QComboBox3.currentText() == "默认主题" else "暗黑主题"
        self.apply_theme()
    
    def toggle_theme(self):
        """切换主题"""
        self.current_theme = "暗黑主题" if self.current_theme == "默认主题" else "默认主题"
        self.apply_theme()

    def apply_theme(self):
        """初始化主题"""
        try:
            self.logger.info(f"apply_theme()-->当前主题更新为{self.current_theme}")
            self.setStyleSheet(self.dark_style() if self.current_theme == "暗黑主题" else self.default_style())
        except Exception as e:
            self.logger.error(f"【apply_theme】-->更新主题 | 报错：{e}")

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
        self.statusbar_button3.setStyleSheet(statusbar_button_style)
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
            self.statusbar_button3.setStyleSheet(statusbar_button_style)
            # 设置版本按钮更新样式
            self.statusbar_button2.setStyleSheet(statusbar_button_style)
            if self.new_version_info:
                self.statusbar_button2.setStyleSheet(statusbar_button_style_version)
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
                
            """

    @log_error_decorator(tips="清理资源")
    def cleanup(self):
        """清理资源 - 优化版本"""
        try:
            # 1. 取消预加载任务
            self.cancel_preloading()
            # 2. 清理所有子窗口
            self._cleanup_sub_windows()
            # 3. 清理所有工具窗口
            self._cleanup_tool_windows()
            # 4. 清理所有对话框
            self._cleanup_dialogs()
            # 5. 清理所有线程
            self._cleanup_threads()
            # 6. 清理线程池
            if hasattr(self, 'threadpool'):
                self.threadpool.clear()
                self.threadpool.waitForDone()
            # 7. 清理压缩相关资源
            self._cleanup_compression_resources()
            # 10. 清理表格数据
            if hasattr(self, 'RB_QTableWidget0'):
                self.RB_QTableWidget0.clear()
                self.RB_QTableWidget0.setRowCount(0)
                self.RB_QTableWidget0.setColumnCount(0)
            # 11. 清理列表数据
            self.files_list = []
            self.paths_list = []
            self.dirnames_list = []
            self.preloading_file_name_paths = []
            # 12. 强制垃圾回收
            gc.collect()
            self.logger.info("cleanup()-->资源清理完成")
        except Exception as e:
            self.logger.error(f"cleanup()-->资源清理过程中发生错误: {e}")
    
    def _cleanup_sub_windows(self):
        """清理所有子窗口"""
        # 清理看图子窗口
        if hasattr(self, 'compare_window') and self.compare_window:
            try:
                self.compare_window.deleteLater()
                self.compare_window = None
            except Exception as e:
                self.logger.error(f"_cleanup_sub_windows()-->清理compare_window失败: {e}")
        
        # 清理视频播放器
        if hasattr(self, 'video_player') and self.video_player:
            try:
                self.video_player.deleteLater()
                self.video_player = None
            except Exception as e:
                self.logger.error(f"_cleanup_sub_windows()-->清理video_player失败: {e}")
        
        # 清理搜索窗口
        if hasattr(self, 'search_window') and self.search_window:
            try:
                self.search_window.deleteLater()
                self.search_window = None
            except Exception as e:
                self.logger.error(f"_cleanup_sub_windows()-->清理search_window失败: {e}")
    
    def _cleanup_tool_windows(self):
        """清理所有工具窗口"""
        tool_windows = [
            'rename_tool',
            'image_process_window', 
            'bat_tool',
            'raw2jpg_tool'
        ]
        
        for tool_name in tool_windows:
            if hasattr(self, tool_name) and getattr(self, tool_name):
                try:
                    tool = getattr(self, tool_name)
                    tool.deleteLater()
                    setattr(self, tool_name, None)
                except Exception as e:
                    self.logger.error(f"_cleanup_tool_windows()-->清理{tool_name}失败: {e}")
    
    def _cleanup_dialogs(self):
        """清理所有对话框"""
        # 清理帮助对话框
        if hasattr(self, 'help_dialog') and self.help_dialog:
            try:
                del self.help_dialog
            except Exception as e:
                self.logger.error(f"_cleanup_dialogs()-->清理help_dialog失败: {e}")
        
        # 清理进度对话框
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            try:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
                self.progress_dialog = None
            except Exception as e:
                self.logger.error(f"_cleanup_dialogs()-->清理progress_dialog失败: {e}")
    
    def _cleanup_threads(self):
        """清理所有线程"""
        thread_names = [
            'qualcom_thread',
            'mtk_thread', 
            'unisoc_thread',
            'compress_worker'
        ]
        
        for thread_name in thread_names:
            if hasattr(self, thread_name) and getattr(self, thread_name):
                try:
                    thread = getattr(self, thread_name)
                    # 对于QThread类型的线程
                    if hasattr(thread, 'quit') and hasattr(thread, 'wait'):
                        thread.quit()
                        if not thread.wait(1000):  # 等待1秒
                            thread.terminate()  # 强制终止
                            thread.wait(1000)
                    # 对于QRunnable类型的工作线程
                    elif hasattr(thread, 'cancel'):
                        thread.cancel()
                    # 清理引用
                    if hasattr(thread, 'deleteLater'):
                        thread.deleteLater()
                    setattr(self, thread_name, None)
                except Exception as e:
                    self.logger.error(f"_cleanup_threads()-->清理{thread_name}失败: {e}")
    
    def _cleanup_compression_resources(self):
        """清理压缩相关资源"""
        # 清理压缩工作线程
        if hasattr(self, 'compress_worker') and self.compress_worker:
            try:
                self.compress_worker.cancel()
                self.compress_worker = None
            except Exception as e:
                self.logger.error(f"_cleanup_compression_resources()-->清理compress_worker失败: {e}")
        
        # 清理压缩包路径
        if hasattr(self, 'zip_path'):
            self.zip_path = None

    @log_performance_decorator(tips="从JSON文件加载之前的设置", log_args=False, log_result=False)
    def load_settings(self):
        """从JSON文件加载设置"""
        self.logger.info("load_settings()-->执行函数任务, 从JSON文件加载之前的设置")
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

                    # 定位地址栏文件夹到左侧文件浏览器中
                    self.locate_in_tree_view()

                    # 恢复极简模式状态,默认开启
                    self.simple_mode = settings.get("simple_mode", True)

                    # 恢复拖拽模式状态,默认开启
                    self.drag_flag = settings.get("drag_flag", True)

                    # 恢复fast_api使能开关,默认关闭,并初始化一下
                    self.api_flag = settings.get("api_flag", False)
                    self.statusbar_checkbox.setChecked(self.api_flag)
                    self.fast_api_switch()
            else:
                # 若没有cache/设置，则在此初始化主题设置--默认主题
                self.apply_theme()
        except Exception as e:
            print(f"[load_settings]-->加载设置时出错: {e}")
            return

    def save_settings(self):
        """保存当前设置到JSON文件"""
        try:
            # 使用 pathlib.Path 统一路径处理，更现代和跨平台
            settings_path = Path(__file__).parent / "config" / "basic_settings.json"
            # 确保config目录存在
            settings_path.parent.mkdir(parents=True, exist_ok=True)
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
                "drag_flag": self.drag_flag,

                # fast_api开关使能
                "api_flag":self.statusbar_checkbox.isChecked()
            }
            # 保存设置到JSON文件，使用 pathlib 的 write_text 方法
            settings_path.write_text(
                json.dumps(settings, ensure_ascii=False, indent=4), 
                encoding='utf-8'
            )
            self.logger.info(f"save_settings()-->成功保存设置信息到JSON文件 | 路径: {settings_path.as_posix()}")
        except Exception as e:
            self.logger.error(f"【save_settings】-->保存设置到JSON文件失败: {e}")
            print(f"[save_settings]-->保存设置时出错: {e}")


    def press_space_or_b_get_selected_file_list(self, key_type):
        """获取右侧表格选中的文件的路径列表和索引列表
        函数功能说明: 当按下快键键【space/B】时, 捕获在主界面右侧表格中选中的单元格，解析并返回文件路径列表和索引列表
        输入:
        key_type: 按键类型【space/B】
        返回:
        file_path_list: 表格选中文件完整路径列表
        current_image_index: 表格选中文件当前索引列表
        """
        # 常量定义，最大支持的同时比较文件数
        MAX_SELECTED_FILES = 8
        try:
            # 获取选中的项,判断是否存在选中项 ? 若没有选中项 --> 恢复首次按键状态，弹出提示信息，退出函数
            if not (selected_items := self.RB_QTableWidget0.selectedItems()): 
                self.last_key_press = False
                show_message_box("🚩没有选中的项！", "提示", 500)
                return [], []
            
            # 限制最多只能支持对8个文件进行对比
            if len(selected_items) > MAX_SELECTED_FILES:
                show_message_box(f"🚩最多只能同时选中{MAX_SELECTED_FILES}个文件进行比较", "提示", 1000)
                return [], []

            # 判断是否是首次按键，step_row表示每列行索引需要移动的步长，是一个列表
            if not self.last_key_press: # 首次按键不移动,并设置为True，保证后续按键移动step_row
                step_row = [0]*self.RB_QTableWidget0.columnCount()
                self.last_key_press = True 
            else: # 统计每列行索引需要移动step 
                step_row = [sum(1 for item in selected_items if item.column() == i) 
                            for i in range(max((item.column() for item in selected_items), default=-1) + 1)]
            # 清除所有选中的项; 初始化用于存储文件路径和文件索引的列表，初始化最大最小行索引
            self.RB_QTableWidget0.clearSelection() 
            row_min, row_max = 0, self.RB_QTableWidget0.rowCount() - 1
            file_path_list, file_index_list = [], []
            # 遍历选中项，移动到相应位置，返回选中文件路径列表和索引列表
            for item in selected_items: 
                # 获取表格列/行索引，然后通过判断按键类型key_type来控制选中的单元格上移和下移的位置 
                col_index, row_index = item.column(), item.row()
                row_index += step_row[col_index] # 默认使用下移方案【同时也是按下space键的功能】
                if key_type == 'b': # 使用上移方案【也是按下 b键的功能】 
                    row_index -= step_row[col_index]
                # 获取选中项文件完整路径列表. 
                # 1.先判断选中项移动位置是否超出表格范围，若超出则抛出异常，退出函数
                # 2.未超出表格范围，移动到正确的位置后，收集完整路径保存到列表中
                if row_min <= row_index <= row_max:
                    if(new_item := self.RB_QTableWidget0.item(row_index, col_index)):
                        # 选中新的单元格; 直接根据单元格索引从self.paths_list列表中拿完整文件路径
                        new_item.setSelected(True)
                        if (full_path := self.paths_list[col_index][row_index]) and os.path.isfile(full_path):  
                            file_path_list.append(full_path)
                        else: # 备用低效方案，拼接各个组件获取完整路径
                            if(full_path := self.get_single_full_path(row_index, col_index)):
                                file_path_list.append(full_path)
                    else:
                        raise Exception(f"new_item is None")
                else:
                    raise Exception(f"当前计算的行索引：{row_index}超出表格范围【{row_min}~{row_max}】")
                # 获取选中项文件索引列表.
                # 1. 先检查最大行索引image_index_max是否有效，然后再获取当前图片张数
                self.image_index_max = self.image_index_max if self.image_index_max else [self.RB_QTableWidget0.rowCount()] * self.RB_QTableWidget0.columnCount()
                index = f"{row_index+1}/{self.image_index_max[col_index]}" if row_index + 1 <= self.image_index_max[col_index] else "None" 
                file_index_list.append(index)
            # 将选中的单元格滚动到视图中间位置
            self.RB_QTableWidget0.scrollToItem(new_item, QAbstractItemView.PositionAtCenter)
            # 返回文件路径列表和当前图片张数列表
            return file_path_list, file_index_list  
        except Exception as e:
            show_message_box("🚩【Space/b】键按下发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.error(f"【press_space_or_b_get_selected_file_list】-->处理键盘按下事件时发生错误: {e}")
            return [], []
    
    @log_error_decorator(tips="处理F1键按下事件")
    def on_f1_pressed(self):
        """处理F1键按下事件
        函数功能说明: 打开MIPI RAW文件转换为JPG文件工具
        """
        # 初始化文件格式转化类
        self.raw2jpg_tool = Mipi2RawConverterApp()
        self.raw2jpg_tool.setWindowTitle("MIPI RAW文件转换为JPG文件")
        # 设置窗口图标
        icon_path = (self.base_icon_path / "raw_ico_96x96.ico").as_posix()
        self.raw2jpg_tool.setWindowIcon(QIcon(icon_path))
        # 添加链接关闭事件
        self.raw2jpg_tool.closed.connect(self.on_raw2jpg_tool_closed)
        self.raw2jpg_tool.show()


    @log_error_decorator(tips="处理F3键按下事件")
    def on_f3_pressed(self):
        """处理F3键按下事件"""
        # 定位日志文件路径
        if not (log_path := Path(__file__).parent / "cache" / "logs" / "hiviewer.log").exists():
            show_message_box("🚩定位日志文件【hiviewer.log】失败!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.warning(f"on_f3_pressed()-->日志文件【hiviewer.log】不存在 | 路径:{log_path.as_posix()}")
            return
        try: # 使用系统记事本打开日志文件
            subprocess.Popen(["notepad.exe", str(log_path)])
            self.logger.info(f"on_f3_pressed()-->使用系统记事本打开日志文件成功")
        except Exception as open_err:
            show_message_box("🚩打开日志失败!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.error(f"【on_f3_pressed】-->使用系统记事本打开日志文件 | 报错: {open_err}")

    """键盘按下事件处理""" 
    @log_error_decorator(tips="处理F2键按下事件")
    def on_f2_pressed(self):
        """处理F2键按下事件"""
        # 获取选中的项
        if not (selected_items := self.RB_QTableWidget0.selectedItems()):
            show_message_box("没有选中的项！", "提示", 500)
            return
        # 获取选中的文件路径列表, 直接从类属性paths_list中获取选中的文件夹路径列表
        if not (current_folder := [self.paths_list[item.column()][item.row()] for item in selected_items]):
            show_message_box("无法获取选中的文件路径列表！", "提示", 500)
            return
        # 若选中的单元格数量为1，打开对应的文件重命名交互界面
        if len(selected_items) == 1: 
            self.open_sigle_file_rename_tool(current_folder[0], selected_items[0])
            return
        # 默认打开多文件重命名功能
        self.open_rename_tool(current_folder)

    @log_error_decorator(tips="处理F4键按下事件")
    def on_f4_pressed(self):
        """处理F4键按下事件"""
        # 获取当前选中的文件夹上一级文件夹路径current_folder
        if not (current_folder := os.path.dirname(self.RT_QComboBox.currentText())):
            show_message_box("当前没有选中的文件夹", "提示", 500)
        # 打开多文件夹重命名工具    
        self.open_rename_tool(current_folder)
 

    @log_error_decorator(tips="处理F4键按下事件")
    def on_f5_pressed(self):
        """处理F5键按下事件
        函数功能说明：刷新表格&清除缓存
        """  
        # 弹出刷新表格&清除缓存的提示框
        show_message_box("刷新表格&清除缓存-", "提示", 500)
        # 清除日志文件，清除图标缓存
        self.clear_log_and_cache_files()
        IconCache.clear_cache()
        # 重新更新表格
        self.update_RB_QTableWidget0()

            
    def clear_log_and_cache_files(self):
        """清除日志文件以及zip缓存文件"""
        try:
            # 使用工具函数清除日志文件以及zip等缓存
            clear_log_files()
            clear_cache_files()
            # 重新初始化日志系统
            setup_logging()
            self.logger = get_logger(__name__)
            self.logger.info("clear_log_and_cache_files()--成功清除日志文件，并重新初始化日志系统")
        except Exception as e:
            self.logger.error(f"【clear_log_and_cache_files】-->清除日志文件失败: {e}")


    def on_f12_pressed(self):
        """处理【F12】键按下事件
        函数功能说明: 重启hiviewer主程序
        """
        try:
            # 先关闭主程序
            self.close()
            # 查找hiviewer主程序路径
            program_path = os.path.join(os.path.dirname(__file__), "hiviewer.exe")
            if os.path.exists(program_path):
                # 使用os.startfile启动程序
                os.startfile(program_path)
                # 等待3秒确保程序启动
                time.sleep(3)  
                self.logger.info(f"on_f12_pressed()-->已重新启动主程序:【hiviewer.exe】")
                return True
            else:
                self.logger.warning(f"on_f12_pressed()-->无法重启hiviewer主程序,程序文件不存在: {program_path}")
                return False
        except Exception as e:
            self.logger.error(f"【on_f12_pressed】-->重启hiviewer主程序失败: {e}")
            return False

    @log_error_decorator(tips="处理【Alt+Q】键按下事件")
    def on_escape_pressed(self):
        """处理【Alt+Q】键按下事件
        函数功能说明: 退出hiviewer主程序
        """
        self.logger.info("on_escape_pressed()-->组合键【Alt+Q】被按下, 退出hiviewer主程序")
        self.close()

    def on_alt_pressed(self):
        """处理【Alt+A】键按下事件
        函数功能说明: 拖拽模式【开启\关闭】切换
        """
        self.drag_flag = not self.drag_flag
        message = "切换到拖拽模式" if self.drag_flag else "关闭拖拽模式"
        show_message_box(message, "提示", 500)
        

    def on_p_pressed(self):
        """处理【P】键按下事件
        函数功能说明: 拖拽模式【开启\关闭】切换
        """
        self.logger.info("on_p_pressed()-->P键已按下, 准备切换主题")
        try:
            # 设置下拉框显示并切换主题
            theme = "暗黑主题" if self.current_theme == "默认主题" else "默认主题"
            self.RT_QComboBox3.setCurrentIndex(self.RT_QComboBox3.findText(theme))
            self.toggle_theme()
        except Exception as e:
            self.logger.error(f"【on_p_pressed】-->P键按下事件报错: {e}")
                

    def on_i_pressed(self):
        """处理【i】键按下事件
        函数功能说明: 调用高通工具后台解析图片的exif信息
        """
        try:
            # 获取当前选中的文件类型
            selected_option = self.RT_QComboBox.currentText()
            # 创建并显示自定义对话框,传入图片列表
            dialog = Qualcom_Dialog(selected_option)
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 记录时间
                self.time_start = time.time()
                # 收集用户输入的参数
                dict_info = dialog.get_data()
                qualcom_path = dict_info.get("Qualcom工具路径","")
                images_path = dict_info.get("Image文件夹路径","")
                # 检查高通解析工具是否存在
                if not qualcom_path or not os.path.exists(qualcom_path):
                    show_message_box("🚩没找到高通C7解析工具.🐬请正确加载工具路径...", "提示", 2000)
                    return
                # 拼接参数命令字符串
                if images_path and os.path.exists(images_path):
                    show_message_box("正在使用高通工具后台解析图片Exif信息...", "提示", 1000)
                    self.logger.info(f"on_i_pressed()-->正在使用高通工具后台解析图片Exif信息...")
                    # 创建线程，必须在主线程中连接信号
                    from src.qpm.qualcom import QualcomThread
                    self.qualcom_thread = QualcomThread(qualcom_path, images_path)
                    self.qualcom_thread.start()
                    self.qualcom_thread.finished.connect(self.on_qualcom_finished)  
            # 无论对话框是接受还是取消，都手动销毁对话框
            dialog.deleteLater()
            dialog = None
        except Exception as e:
            self.logger.error(f"【on_i_pressed】-->处理i键按下事件失败: {e}")
            return

    def on_qualcom_finished(self, success, error_message, images_path=None):
        """qualcom_thread线程完成链接事件
        函数功能说明: 高通工具后台解析图片线程完成后的链接事件
        """
        try:
            if success and images_path:
                # 解析xml文件将其保存到excel中去
                xml_exists = any(f for f in os.listdir(images_path) if f.endswith('_new.xml'))
                if xml_exists:
                    save_excel_data(images_path)
                use_time = time.time() - self.time_start
                show_message_box(f"高通工具后台解析图片成功！用时: {use_time:.2f}秒", "提示", 1000)
                self.logger.info(f"on_qualcom_finished()-->高通工具后台解析图片成功！| 耗时: {use_time:.2f}秒")
            else:
                show_message_box(f"高通工具后台解析图片失败: {error_message}", "提示", 2000)
                self.logger.error(f"【on_qualcom_finished】-->高通工具后台解析图片失败: {error_message}")
        except Exception as e:
            show_message_box(f"高通工具后台解析图片失败: {error_message}", "提示", 2000)
            self.logger.error(f"【on_qualcom_finished】-->高通工具后台解析图片失败: {e}")
            return

    def on_u_pressed(self):
        """处理【u】键按下事件
        函数功能说明: 调用联发科工具后台解析图片的exif信息
        """
        try:
            # 获取当前选中的文件类型
            selected_option = self.RT_QComboBox.currentText()
            # 创建并显示自定义对话框,传入图片列表
            dialog = MTK_Dialog(selected_option)
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 记录时间
                self.time_start = time.time()
                # 收集用户输入的参数
                dict_info = dialog.get_data()
                mtk_path = dict_info.get("MTK工具路径","")
                images_path = dict_info.get("Image文件夹路径","")
                # 检查MTK析工具是否存在
                if not mtk_path or not os.path.exists(mtk_path):
                    show_message_box("🚩没找到MTK DebugParser解析工具.🐬请正确加载工具路径...", "提示", 2000)
                    return
                # 拼接参数命令字符串
                if images_path and os.path.exists(images_path):
                    show_message_box("正在使用MTK工具后台解析图片Exif信息...", "提示", 1000)
                    self.logger.info(f"on_u_pressed()-->正在使用MTK工具后台解析图片Exif信息...")
                    # 创建线程，必须在主线程中连接信号
                    from src.mtk.mtk import MTKThread
                    self.mtk_thread = MTKThread(mtk_path, images_path)
                    self.mtk_thread.start()
                    self.mtk_thread.finished.connect(self.on_mtk_finished)  
            # 无论对话框是接受还是取消，都手动销毁对话框
            dialog.deleteLater()
            dialog = None
        except Exception as e:
            self.logger.error(f"【on_u_pressed】-->处理u键按下事件(MTK工具解析图片)失败: {e}")
            return

    def on_mtk_finished(self, success, error_message, images_path=None):
        """mtk_thread线程完成链接事件
        函数功能说明: MTK工具后台解析图片线程完成后的链接事件
        """
        try:
            if success and images_path:
                # 解析txt文件将其保存到excel中去
                xml_exists = any(f for f in os.listdir(images_path) if f.endswith('.exif'))
                if xml_exists:
                    # save_excel_data(images_path)
                    pass
                use_time = time.time() - self.time_start
                show_message_box(f"MTK_DebugParser工具后台解析图片成功! 用时: {use_time:.2f}秒", "提示", 1500)
                self.logger.info(f"on_mtk_finished()-->MTK_DebugParser工具后台解析图片成功! | 耗时: {use_time:.2f}秒")
            else:
                show_message_box(f"MTK_DebugParser工具后台解析图片失败: {error_message}", "提示", 2000)
                self.logger.error(f"【on_mtk_finished】-->MTK_DebugParser工具后台解析图片失败: {error_message}")
        except Exception as e:
            show_message_box(f"MTK_DebugParser工具后台解析图片失败: {error_message}", "提示", 2000)
            self.logger.error(f"【on_mtk_finished】-->MTK_DebugParser工具后台解析图片失败: {e}")
            return

    def on_y_pressed(self):
        """处理【y】键按下事件
        函数功能说明: 调用展锐工具后台解析图片的exif信息
        """
        try:
            # 获取当前选中的文件类型
            selected_option = self.RT_QComboBox.currentText()
            # 创建并显示自定义对话框,传入图片列表
            dialog = Unisoc_Dialog(selected_option)
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 记录起始时间
                self.time_start = time.time()
                # 收集用户输入的参数
                dict_info = dialog.get_data()
                unisoc_path = dict_info.get("Unisoc工具路径","")
                images_path = dict_info.get("Image文件夹路径","")
                # 检查展锐IQT解析工具是否存在
                if not unisoc_path or not os.path.exists(unisoc_path):
                    show_message_box("🚩没找到展锐IQT解析工具.🐬请正确加载工具路径...", "提示", 2000)
                    return
                # 拼接参数命令字符串
                if images_path and os.path.exists(images_path):
                    show_message_box("正在使用展锐IQT工具后台解析图片Exif信息...", "提示", 1000)
                    self.logger.info(f"on_y_pressed()-->正在使用展锐IQT工具后台解析图片Exif信息...")
                    # 创建线程，必须在主线程中连接信号
                    from src.unisoc.unisoc import UnisocThread
                    self.unisoc_thread = UnisocThread(unisoc_path, images_path)
                    self.unisoc_thread.start()
                    self.unisoc_thread.finished.connect(self.on_unisoc_finished)  
            # 无论对话框是接受还是取消，都手动销毁对话框
            dialog.deleteLater()
            dialog = None
        except Exception as e:
            self.logger.error(f"【on_y_pressed】-->处理y键按下事件(展锐IQT工具解析图片)失败: {e}")
            return

    def on_unisoc_finished(self, success, error_message, images_path=None):
        """unisoc_thread线程完成链接事件
        函数功能说明: 展锐IQT工具后台解析图片线程完成后的链接事件
        """
        try:
            if success and images_path:
                # 解析txt文件将其保存到excel中去
                xml_exists = any(f for f in os.listdir(images_path) if f.endswith('.txt'))
                if xml_exists:
                    # save_excel_data(images_path)
                    pass
                use_time = time.time() - self.time_start
                show_message_box(f"展锐IQT工具后台解析图片成功! 用时: {use_time:.2f}秒", "提示", 1500)
                self.logger.info(f"on_unisoc_finished()-->展锐IQT工具后台解析图片成功! | 耗时: {use_time:.2f}秒")
            else:
                show_message_box(f"展锐IQT工具后台解析图片失败: {error_message}", "提示", 2000)
                self.logger.error(f"【on_unisoc_finished】-->展锐IQT工具后台解析图片失败: {error_message}")
        except Exception as e:
            show_message_box(f"展锐IQT工具后台解析图片失败: {error_message}", "提示", 2000)
            self.logger.error(f"【on_unisoc_finished】-->展锐IQT工具后台解析图片失败: {e}")
            return


    @log_error_decorator(tips="处理【L】键按下事件")
    def on_l_pressed(self):
        """处理【L】键按下事件
        函数功能说明: 打开图片调整工具，支持对曝光、对比度以及色彩等方面进行调整
        """
        # 获取选中项并验证只有一个选中的单元格
        if not (selected_item_paths := self.get_selected_file_path()) or len(selected_item_paths) != 1:
            show_message_box("🚩请选择单个图片文件进行图片调整", "提示", 500)
            return
        if not (selected_item_path := selected_item_paths[0]).lower().endswith(self.IMAGE_FORMATS):
            show_message_box(f"🚩不支持【{os.path.splitext(selected_item_path)[-1]}】格式文件🐬", "提示", 500)
            return
        # 打开图片调整子界面
        self.open_image_process_window(selected_item_path)


    def on_ctrl_h_pressed(self):
        """处理【Ctrl+h】键按下事件
        函数功能说明: 打开关于界面，集成有作者信息、使用说明、更新日志、建议反馈以及检查更新等功能
        """
        try:
            # 单例模式管理帮助窗口
            if not hasattr(self, 'help_dialog'):
                # 构建文档路径,使用说明文档+版本更新文档
                doc_dir = os.path.join(os.path.dirname(__file__), "resource", "docs")
                User_path = os.path.join(doc_dir, "User_Manual.md")
                Version_path = os.path.join(doc_dir, "Version_Updates.md")
                # 验证文档文件存在性
                if not os.path.isfile(User_path) or not os.path.isfile(Version_path):
                    show_message_box(f"🚩帮助文档未找到:\n{User_path}or{Version_path}", "配置错误", 2000)
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
            show_message_box("🚩打开关于子界面失败.🐬报错信息请打开日志文件查看...", "提示", 2000)
            error_msg = f"【on_ctrl_h_pressed】-->无法打开帮助文档:\n{str(e)}\n请检查程序是否包含文件: ./resource/docs/update_main_logs.md"
            self.logger.error(error_msg)
            
    def close_helpinfo(self):
        """关闭对话框事件"""
        try:
            if hasattr(self, 'help_dialog'):
                del self.help_dialog
                self.logger.info("close_helpinfo()-->成功销毁关于对话框")
        except Exception as e:
            self.logger.error(f"【close_helpinfo】-->销毁关于对话框 | 报错：{e}")

    def on_ctrl_f_pressed(self):
        """处理【Ctrl+f】键按下事件
        函数功能说明: 打开主界面图片模糊搜索工具
        """
        try:
            # 构建图片名称列表，保持多维列表的结构, 保持图片名称的完整路径
            image_names = [[os.path.basename(path) for path in folder_paths] for folder_paths in self.paths_list]
            # 创建搜索窗口
            self.search_window = SearchOverlay(self, image_names)
            self.search_window.show_search_overlay()
            # 连接搜索窗口的选中项信号
            self.search_window.item_selected_from_search.connect(self.on_item_selected_from_search)
            # 打印输出日志文件
            self.logger.info("on_ctrl_f_pressed()-->打开图片模糊搜索工具成功")
        except Exception as e:
            show_message_box("🚩图片模糊搜索失败.🐬报错信息请打开日志文件查看...", "提示", 2000)
            self.logger.error(f"【on_ctrl_f_pressed】-->打开图片模糊搜索工具失败: {e}")   

    def on_item_selected_from_search(self, position):
        """处理图片模糊搜索工具选中事件
        函数功能说明: 处理搜索窗口的选中项信号,返回行(row)和列(col)后再主界面中定位选中项
        """
        try:
            # 获取选中的表格索引
            row, col = position
            # 先清除表格选中项，然后设置表格选中项，滚动到选中项
            self.RB_QTableWidget0.clearSelection()
            if (item := self.RB_QTableWidget0.item(row, col)):
                item.setSelected(True)
                self.RB_QTableWidget0.scrollToItem(item, QAbstractItemView.PositionAtCenter)
            # 释放搜索窗口
            if self.search_window:
                self.search_window.deleteLater()
                self.search_window = None
        except Exception as e:
            show_message_box("🚩图片模糊搜索失败.🐬报错信息请打开日志文件查看...", "提示", 2000)
            self.logger.error(f"【on_item_selected_from_search】-->无法使用主界面搜索窗口 | 报错：{e}")

    def check_file_type(self, lsit_file_path):
        """检查文件类型
        函数功能说明: 根据传入的文件路径列表，统计图片、视频、其它文件是否出现
        返回: 置为1表示出现 置为0表示未出现
        flag_video: 视频文件出现标志位   
        flag_image: 图片文件出现标志位
        flag_other: 其它格式文件出现标志位
        """
        try:
            # 解析传入的文件路径列表中的扩展名
            if not (file_extensions := {os.path.splitext(path)[1].lower() for path in lsit_file_path}):
                raise Exception(f"无法解析传入的文件路径列表扩展名")
            # 检查文件类型的合法性, 使用集合操作和in操作符，比endswith()更高效
            flag_video = 1 if any(ext in self.VIDEO_FORMATS for ext in file_extensions) else 0
            flag_image = 1 if any(ext in self.IMAGE_FORMATS for ext in file_extensions) else 0
            flag_other = 1 if any(ext not in self.VIDEO_FORMATS and ext not in self.IMAGE_FORMATS for ext in file_extensions) else 0
            return flag_video, flag_image, flag_other
        except Exception as e:
            self.logger.error(f"【check_file_type】-->【Space/B】键按下后, 检查文件类型功能函数 | 报错：{e}")
            return 0, 0, 0

    def open_subwindow_dynamically(self, selected_file_path_list, selected_file_index_list):
        """动态打开对应子窗口
        函数功能说明: 根据传入的文件类型,动态打开对应子界面
        输入: 
        selected_file_path_list: 传入选中文件的路径列表
        selected_file_index_list: 传入选中文件的索引列表 
        """
        # 常量定义
        MAX_VIDEO_FILES = 5
        
        def _clear_selection_and_show_error(message):
            """统一的错误处理：清理选择状态并显示错误消息"""
            self.RB_QTableWidget0.clearSelection()
            self.last_key_press = False
            show_message_box(message, "提示", 1000)
        
        try:
            # 检查文件类型
            flag_video, flag_image, flag_other = self.check_file_type(selected_file_path_list)
            # 检查是否混合文件类型（使用更清晰的逻辑）
            if sum([flag_video, flag_image, flag_other]) > 1:
                _clear_selection_and_show_error("🚩不支持同时选中图片/视频和其它文件格式,\n请重新选择文件打开")
                return
            # 根据文件类型处理
            if flag_video:
                if len(selected_file_path_list) > MAX_VIDEO_FILES:
                    _clear_selection_and_show_error("🚩最多支持同时比较5个视频文件")
                    return
                self.create_video_player(selected_file_path_list, selected_file_index_list)
            elif flag_image:
                self.create_compare_window(selected_file_path_list, selected_file_index_list)
            elif flag_other:
                _clear_selection_and_show_error("🚩不支持打开该文件格式")
            # 如果没有匹配的文件类型，静默返回
        except Exception as e:
            _clear_selection_and_show_error("🚩动态打开对应子窗口任务报错!\n🐬具体报错请按【F3】键查看日志信息")
            self.logger.error(f"【open_subwindow_dynamically】-->【Space/B】键按下后, 动态打开对应子窗口 | 报错：{e}")

    @log_error_decorator(tips="Space/B键防抖检测任务")
    def should_block_space_or_b_press(self):
        """Space/B键防抖检测，0.5秒内重复触发则拦截
        返回True表示应拦截本次处理，False表示放行
        """
        current_time = time.time()
        if hasattr(self, 'last_space_and_b_press_time') and current_time - self.last_space_and_b_press_time < 0.5:
            show_message_box("🚩触发了按键防抖机制0.5s内重复按键", "提示", 1000)
            return True
        self.last_space_and_b_press_time = current_time
        return False

    def on_b_pressed(self):
        """处理【B】键按下事件
        函数功能说明: 用于查看上一组图片/视频，在看图子界面功能保持一致
        """
        try:
            # 按键防抖机制，防止快速多次按下导致错误，设置0.5秒内不重复触发
            if self.should_block_space_or_b_press():
                return
            # 获取选中单元格的文件路径和索引
            selected_file_path_list, selected_file_index_list = self.press_space_or_b_get_selected_file_list('b')
            if not selected_file_path_list or not selected_file_index_list:
                return
            # 根据文件类型动态选择对应的子界面（当前支持看图子界面和视频播放子界面）
            self.open_subwindow_dynamically(selected_file_path_list, selected_file_index_list)
        except Exception as e:
            show_message_box("🚩处理【B】键按下事件失败.🐬报错信息请打开日志文件查看...", "提示", 2000)
            self.last_key_press = False  # 恢复第一次按下键盘空格键或B键
            self.logger.error(f"【on_b_pressed】-->主界面处理【B】键按下事件发生错误: {e}")
            

    def on_space_pressed(self):
        """处理【Space】键按下事件
        函数功能说明: 用于查看下一组图片/视频，在看图子界面功能保持一致
        """
        try:
            # 按键防抖机制，防止快速多次按下导致错误，设置0.5秒内不重复触发
            if self.should_block_space_or_b_press():
                return
            # 获取选中单元格的文件路径和索引,并判断是否有效
            selected_file_path_list, selected_file_index_list = self.press_space_or_b_get_selected_file_list('space')
            if not selected_file_path_list or not selected_file_index_list:
                return
            # 根据文件类型动态选择对应的子界面（当前支持看图子界面和视频播放子界面）
            self.open_subwindow_dynamically(selected_file_path_list, selected_file_index_list)
        except Exception as e:
            # 恢复第一次按下键盘空格键或B键
            show_message_box("🚩处理【Space】键按下事件失败.🐬报错信息请打开日志文件查看...", "提示", 2000)
            self.last_key_press = False 
            self.logger.error(f"【on_space_pressed】-->主界面处理【Space】键时发生错误: {e}")


    @log_error_decorator(tips="创建看图子窗口的统一方法")
    def create_compare_window(self, selected_file_paths, image_indexs):
        """创建看图子窗口的统一方法"""
        # self.pause_preloading() # modify by diamond_cz 20250217 禁用暂停预加载功能，看图时默认后台加载图标
        # 打印主界面底部栏标签提示信息并立即重绘
        self.statusbar_label1.setText(f"📢:正在打开看图子界面..."), self.statusbar_label1.repaint()
        # 初始化看图子界面
        if not self.compare_window:
            self.logger.info("create_compare_window()-->开始初始化看图子界面并出入图片路径和索引列表")
            self.compare_window = SubMainWindow(selected_file_paths, image_indexs, self)
        else:
            self.logger.info("create_compare_window()-->看图子界面已存在，直接传入图片路径和索引列表")
            self.compare_window.set_images(selected_file_paths, image_indexs)
            self.compare_window.show()
        # 连接看图子窗口的关闭信号
        self.compare_window.closed.connect(self.on_compare_window_closed)
        self.statusbar_label1.setText(f"📢:看图子界面打开成功")
        self.statusbar_label1.repaint()  # 刷新标签文本
        # self.hide()  # modify by diamond_cz 20250217 不隐藏主界面


    @log_error_decorator(tips="处理看图子窗口关闭事件")
    def on_compare_window_closed(self):
        """处理看图子窗口关闭事件"""
        if self.compare_window:
            # 打印输出日志信息
            self.logger.info("on_compare_window_closed()-->主程序【hiviewer.exe】接受看图子窗口关闭事件")
            # 隐藏看图子界面，清理资源
            self.compare_window.hide(), self.compare_window.cleanup()
            # 打印主界面底部栏标签提示信息
            self.statusbar_label1.setText(f"📢:看图子界面关闭成功")
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

    @log_error_decorator(tips="暂停预加载")
    def pause_preloading(self):
        """暂停预加载"""
        if self.current_preloader and self.preloading:
            self.current_preloader.pause()
            self.logger.info("[pause_preloading]-->预加载已暂停")

    @log_error_decorator(tips="恢复预加载")
    def resume_preloading(self):
        """恢复预加载"""
        if self.current_preloader and self.preloading:
            self.current_preloader.resume()
            self.logger.info("[resume_preloading]-->预加载已恢复")

    @log_error_decorator(tips="创建视频播放器的统一方法")
    def create_video_player(self, selected_file_paths, image_indexs):
        """创建视频播放器的统一方法"""
        self.video_player = VideoWall(selected_file_paths)
        self.video_player.setWindowTitle("多视频播放程序")
        self.video_player.setWindowFlags(Qt.Window) 
        # 设置窗口图标
        icon_path = (self.base_icon_path / "video_icon.ico").as_posix()
        self.video_player.setWindowIcon(QIcon(icon_path))
        self.video_player.closed.connect(self.on_video_player_closed)
        self.video_player.show()
        self.hide()

    @log_error_decorator(tips="打开单文件重命名功能子界面")
    def open_sigle_file_rename_tool(self, current_folder, selected_items):
        """创建单文件重命名方法"""
        dialog = SingleFileRenameDialog(current_folder, self)
        if dialog.exec_() == QDialog.Accepted:
            if (new_file_path := dialog.get_new_file_path()):
                # 获取新的文件名; 选中的单元格索引；新的单元格内容
                new_file_name = os.path.basename(new_file_path)
                row, col= selected_items.row(), selected_items.column()
                current_text = selected_items.text()
                # 更新内容
                new_text = new_file_name
                if '\n' in current_text:  
                    # 若有多行，则保持原有的其他信息，只更新文件名
                    lines = current_text.split('\n')
                    lines[0] = new_file_name  # 更新第一行的文件名
                    new_text = '\n'.join(lines)
                # 设置新的单元格文本
                self.RB_QTableWidget0.item(row, col).setText(new_text)

    @log_error_decorator(tips="打开批量重命名功能子界面")
    def open_rename_tool(self, current_folder):
        """创建批量重命名的统一方法"""
        self.rename_tool = FileOrganizer()
        self.rename_tool.select_folder(current_folder)
        self.rename_tool.setWindowTitle("批量重命名")
        # 设置窗口图标
        icon_path = (self.base_icon_path / "rename_ico_96x96.ico").as_posix()
        self.rename_tool.setWindowIcon(QIcon(icon_path))
        # 链接关闭事件
        self.rename_tool.closed.connect(self.on_rename_tool_closed) 
        self.rename_tool.show()
        self.hide()

    @log_error_decorator(tips="打开图片调整功能子界面")
    def open_image_process_window(self, image_path):
        """创建图片处理子窗口的统一方法"""
        self.image_process_window = SubCompare(image_path)
        self.image_process_window.setWindowTitle("图片调整") 
        self.image_process_window.setWindowFlags(Qt.Window)
        # 设置窗口图标
        icon_path = (self.base_icon_path / "ps_ico_96x96.ico").as_posix()
        self.image_process_window.setWindowIcon(QIcon(icon_path))
        # 链接关闭事件
        self.image_process_window.closed.connect(self.on_image_process_window_closed) 
        self.image_process_window.show()
        self.hide()

    @log_error_decorator(tips="批量执行命令界面")
    def open_bat_tool(self):
        """创建批量执行命令的统一方法"""
        self.bat_tool = LogVerboseMaskApp()
        self.bat_tool.setWindowTitle("批量执行命令")
        # 设置窗口图标
        icon_path = (self.base_icon_path / "cmd_ico_96x96.ico").as_posix()
        self.bat_tool.setWindowIcon(QIcon(icon_path))
        # 链接关闭事件
        self.bat_tool.closed.connect(self.on_bat_tool_closed)
        self.bat_tool.show()
        self.hide()
        
    @log_error_decorator(tips="处理视频播放器关闭事件")
    def on_video_player_closed(self):
        """处理视频播放器关闭事件"""
        if self.video_player: 
            # 删除引用以释放资源
            self.video_player.deleteLater()
            self.video_player = None
        # 显示主窗口
        self.show() 
        # 恢复第一次按下键盘空格键或B键
        self.last_key_press = False 

    @log_error_decorator(tips="处理重命名工具关闭事件")
    def on_rename_tool_closed(self):
        """处理重命名工具关闭事件"""
        if self.rename_tool:
            self.rename_tool.deleteLater()
            self.rename_tool = None
        self.show()
        self.update_RB_QTableWidget0() 

    @log_error_decorator(tips="处理图片处理子窗口关闭事件")
    def on_image_process_window_closed(self):
        """处理图片处理子窗口关闭事件"""
        if self.image_process_window:
            self.image_process_window.deleteLater()
            self.image_process_window = None
        self.show() 

    @log_error_decorator(tips="处理批量执行命令工具关闭事件")
    def on_bat_tool_closed(self):
        """处理批量执行命令工具关闭事件"""
        if self.bat_tool:
            self.bat_tool.deleteLater()
            self.bat_tool = None
        self.show()

    @log_error_decorator(tips="处理MIPI RAW文件转换为JPG文件工具关闭事件")
    def on_raw2jpg_tool_closed(self):
        """处理MIPI RAW文件转换为JPG文件工具关闭事件"""
        if self.raw2jpg_tool:
            self.raw2jpg_tool.deleteLater()
            self.raw2jpg_tool = None
        self.show()

    @log_error_decorator(tips="处理主程序关闭事件")
    def closeEvent(self, event):
        """重写关闭事件以保存设置和清理资源"""
        self.logger.info("closeEvent()-->触发【hiviewer.exe】主程序关闭事件")
        try:
            # 保存设置
            self.save_settings()
            # 清理资源
            self.cleanup()
            # 等待一小段时间确保清理完成
            QTimer.singleShot(100, lambda: self._final_cleanup())
            self.logger.info("closeEvent()-->接受【hiviewer.exe】关闭事件, 成功保存配置并清理内存！")
        except Exception as e:
            self.logger.error(f"closeEvent()-->关闭事件处理失败: {e}")
        finally:
            event.accept()
    
    def _final_cleanup(self):
        """最终清理，确保所有资源都被释放"""
        try:
            # 再次强制垃圾回收
            gc.collect()
            # 清理任何剩余的定时器
            if hasattr(self, 'splash_progress_timer'):
                self.splash_progress_timer.stop()
            # 记录最终清理完成
            self.logger.info("_final_cleanup()-->最终清理完成")
        except Exception as e:
            self.logger.error(f"_final_cleanup()-->最终清理失败: {e}")


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
    setup_logging() 

    # 设置主程序app，启动主界面
    app = QApplication(sys.argv)
    window = HiviewerMainwindow()
    sys.exit(app.exec_())