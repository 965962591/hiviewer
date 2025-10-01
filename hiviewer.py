#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File         :hiviewer.py
@Time         :2025/09/03
@Author       :diamond_cz@163.com
@Version      :release-v3.6.1
@Description  :hiviewer看图工具主界面
注意事项：
  1. 使用函数get_app_dir()获取当前程序根目录,避免在冻结态使用 __file__ 推导资源路径，
    会出现短文件名别名报错(如:HIVIEW~1.DIS)
  2. 使用函数make_unique_dir_names()获取指定文件夹内的唯一文件夹名称
'''

"""记录程序启动时间"""
import time
STIME = time.time()

"""导入python内置模块"""
import gc
import os
import sys
import json
import stat
import shutil
import subprocess
from pathlib import Path
from itertools import zip_longest
from collections import Counter

"""导入python第三方模块"""
from PyQt5.QtGui import (
    QIcon, QKeySequence, QPixmap)
from PyQt5.QtWidgets import (
    QFileSystemModel, QAbstractItemView, QMenu, 
    QHeaderView, QShortcut, QMainWindow, QDialog,
    QSplashScreen, QSizePolicy, QTableWidgetItem,
    QApplication, QTreeView, QProgressDialog, QLabel)
from PyQt5.QtCore import (
    Qt, QDir, QSize, QTimer, QThreadPool, QUrl, QSize, 
    QMimeData, QPropertyAnimation, QItemSelection, QItemSelectionModel)


"""导入用户自定义的模块"""
from src.components.ui_main import Ui_MainWindow                                     # 假设你的主窗口类名为Ui_MainWindow
from src.components.custom_qMbox_showinfo import show_message_box                    # 导入消息框类
from src.components.custom_qCombox_spinner import CheckBoxListModel,CheckBoxDelegate # 导入自定义下拉框类中的数据模型和委托代理类
from src.utils.xml import save_excel_data                                            # 导入xml文件解析工具类
from src.utils.Icon import IconCache                                                 # 导入文件Icon图标加载类
from src.common.decorator import log_performance_decorator, log_error_decorator      # 导入自定义装饰器函数 
from src.common.manager_version import version_init, fastapi_init                    # 版本号&IP地址初始化
from src.common.manager_color_exif import load_color_settings                        # 导入自定义json配置文件
from src.common.manager_log import setup_logging, get_logger                         # 导入日志文件相关配置
from src.common.font import JetBrainsMonoLoader                                      # 字体管理器

"""
设置全局函数的方法
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
def get_app_dir():
    """获取应用程序根目录（冻结态优先使用可执行文件目录，并尽量展开为长路径）"""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent

    if os.name == "nt":
        try:
            import ctypes  # 延迟导入，避免非 Windows 环境报错
            GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
            GetLongPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
            buf = ctypes.create_unicode_buffer(32768)
            if GetLongPathNameW(str(base), buf, 32768):
                return Path(buf.value)
        except Exception:
            pass
    return base

def make_unique_dir_names(folder_paths):
    """ 从【文件夹路径列表】中获取唯一的【名称列表】
    输入: 文件夹路径列表(str 或 Path)
    返回: 与输入顺序对应的唯一化目录名列表
    """
    ps = [Path(p).resolve() for p in folder_paths]
    cnt = Counter(p.name for p in ps)
    # 第一轮：只用 parent/name
    names = [f"{p.parent.name}/{p.name}" if cnt[p.name] > 1 else p.name for p in ps]
    # 如果仍全同名，再往上加一层，一般也就加到这一层就可以保证唯一
    if len(set(names)) == 1:
        names = [f"{p.parent.parent.name}/{p.parent.name}/{p.name}" if cnt[p.name] > 1 else p.name for p in ps]
    return names

"""
设置主界面类区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

class HiviewerMainwindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(HiviewerMainwindow, self).__init__(parent)
        # 记录程序启动时间；设置图标路径；读取本地版本信息，并初始化新版本信息
        self.start_time = STIME
        # 设置根目录和icon图标目录
        self.root_path = get_app_dir()
        self.icon_path =  self.root_path / "resource" / "icons"
        
        # 初始化日志信息
        setup_logging(self.root_path) 

        # 获取活动的日志记录器,打印相关信息
        self.logger = get_logger(__name__)
        self.logger.info(f""" {"-" * 25} hiviewer主程序开始启动 {"-" * 25}""")
        print(f"----------[程序预启动时间]----------: {(time.time()-self.start_time):.2f} 秒")
        self.logger.info(f"""【程序预启动】-->耗时: {(time.time()-self.start_time):.2f} 秒""")

        # 版本信息和fast api地址端口的初始化
        self.version_info, self.new_version_info,  = version_init(), False     
        self.fast_api_host, self.fast_api_port = fastapi_init()

        # 创建启动画面、启动画面、显示主窗口以及相关初始化在self.update_splash_message()函数通过定时器实现
        self.create_splash_screen()

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
        self.paths_index = {}                   # 文件路径索引字典
        self.dirnames_list = []                 # 选中的同级文件夹列表
        self.image_index_max = []               # 存储当前选中及复选框选中的，所有图片列有效行最大值
        self.additional_folders_for_table = []  # 存储通过右键菜单添加到表格的文件夹的完整路径
        self.compare_window = None              # 添加子窗口引用
        self.last_key_press = False             # 记录第一次按下键盘空格键或B键
        self.left_tree_file_display = False     # 设置左侧文件浏览器初始化标志位，只显示文件夹
        self.simple_mode = True                 # 设置默认模式为简单模式，同EXIF信息功能
        self.current_theme = "默认主题"          # 设置初始主题为默认主题
        self.player_key = True                  # 设置播放器内核，true:cv内核，false:vlc内核
        

        # 添加预加载相关的属性初始化
        self.current_preloader = None 
        self.preloading = False        

        # 初始化线程池
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(max(4, os.cpu_count()))  

        # 初始化压缩工作线程,压缩包路径  
        self.compress_worker = None

        """加载颜色相关设置""" # 设置背景色和字体颜色，使用保存的设置或默认值
        basic_color_settings = load_color_settings().get('basic_color_settings',{})
        self.background_color_default = basic_color_settings.get("background_color_default", "rgb(173,216,230)")  # 深色背景色_好蓝
        self.background_color_table = basic_color_settings.get("background_color_table", "rgb(127, 127, 127)")    # 表格背景色_18度灰
        self.font_color_default = basic_color_settings.get("font_color_default", "rgb(0, 0, 0)")                  # 默认字体颜色_纯黑色
        self.font_color_exif = basic_color_settings.get("font_color_exif", "rgb(255, 255, 255)")                  # Exif字体颜色_纯白色

        """加载字体相关设置""" # 初始化字体管理器,并获取字体，设置默认字体 self.custom_font
        self.font_jetbrains = JetBrainsMonoLoader.font(12)
        self.font_jetbrains_m = JetBrainsMonoLoader.font(11)
        self.font_jetbrains_s = JetBrainsMonoLoader.font(10)

    """
    设置动画显示区域开始线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """
    @log_performance_decorator(tips="创建hiviewer的启动画面 | 设置定时器后台初始化配置", log_args=False, log_result=False)
    def create_splash_screen(self):
        """创建带渐入渐出效果的启动画面"""
        # 加载启动画面图片
        splash_path = (self.icon_path / "viewer_0.png").as_posix()
        splash_pixmap = QPixmap(splash_path)
        
        # 如果启动画面图片为空，则创建一个空白图片
        if splash_pixmap.isNull():
            splash_pixmap = QPixmap(400, 200)
            splash_pixmap.fill(Qt.white)
            
        # 创建启动画面；获取当前屏幕并计算居中位置, 移动到该位置, 设置半透明效果
        self.splash = QSplashScreen(splash_pixmap)
        x, y, _, _ = self.get_screen_geometry()
        self.splash.move(x, y)
        self.splash.setWindowOpacity(0)
        
        # 创建渐入动画，设置800ms的渐入动画
        self.fade_anim = QPropertyAnimation(self.splash, b"windowOpacity")
        self.fade_anim.setDuration(800)  
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
        self.splash.show() # 显示启动画面
        
        # 设置进度更新定时器，记录启动画面更新次数，记录启动画面更新点，启动进度更新定时器，设置每10ms更新一次
        self.fla = 0      
        self.dots_count = 0
        self.splash_progress_timer = QTimer() 
        self.splash_progress_timer.timeout.connect(self.update_splash_message)
        self.splash_progress_timer.start(10)   


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
            self.fade_out.setDuration(800)  # 800ms的渐出动画
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
            print(f"[get_screen_geometry]-->error--无法获取当前鼠标所在屏幕信息 | 报错：{e}")
            self.logger.error(f"【get_screen_geometry】-->无法获取当前鼠标所在屏幕信息 | 报错：{e}")


    """
    设置右键菜单函数区域开始线
    ---------------------------------------------------------------------------------------------------------------------------------------------
    """
    @log_performance_decorator(tips="设置右侧表格区域的右键菜单", log_args=False, log_result=False)
    def setup_context_menu(self):
        """设置右侧表格区域的右键菜单,连接右键菜单到表格"""
        self.RB_QTableWidget0.setContextMenuPolicy(Qt.CustomContextMenu)
        self.RB_QTableWidget0.customContextMenuRequested.connect(self.show_table_context_menu)


    @log_error_decorator(tips="显示表格区域右键菜单")
    def show_table_context_menu(self, pos):
        """显示左侧表格右键菜单"""
        # 设置右侧表格区域的右键菜单栏
        self.context_menu = QMenu(self)
    
        # 设置菜单样式 modify by diamond_cz 20250217 优化右键菜单栏的显示
        self.context_menu.setStyleSheet(f"""
            QMenu {{
                /*background-color: #F0F0F0;   背景色 */

                font-family: "{self.font_jetbrains_s.family()}";
                font-size: {self.font_jetbrains_s.pointSize()}pt;    
            }}
            QMenu::item:selected {{
                background-color: {self.background_color_default};   /* 选中项背景色 */
                color: #000000;               /* 选中项字体颜色 */
            }}
        """)

        # 添加主菜单项并设置图标
        delete_icon = QIcon((self.icon_path / "delete_ico_96x96.ico").as_posix()) 
        paste_icon = QIcon((self.icon_path / "paste_ico_96x96.ico").as_posix()) 
        refresh_icon = QIcon((self.icon_path / "update_ico_96x96.ico").as_posix()) 
        theme_icon = QIcon((self.icon_path / "theme_ico_96x96.ico").as_posix()) 
        image_size_reduce_icon = QIcon((self.icon_path / "image_skinny.ico").as_posix())
        ps_icon = QIcon((self.icon_path / "ps_ico_96x96.ico").as_posix()) 
        command_icon = QIcon((self.icon_path / "cmd_ico_96x96.ico").as_posix())
        exif_icon = QIcon((self.icon_path / "exif_ico_96x96.ico").as_posix())
        raw_icon = QIcon((self.icon_path / "raw_ico_96x96.ico").as_posix())
        rename_icon = QIcon((self.icon_path / "rename_ico_96x96.ico").as_posix())
        help_icon = QIcon((self.icon_path / "about.ico").as_posix()) 
        zip_icon = QIcon((self.icon_path / "file_zip_ico_96x96.ico").as_posix())
        tcp_icon = QIcon((self.icon_path / "TCP_ico_96x96.ico").as_posix())
        rotator_icon = QIcon((self.icon_path / "rorator_plus_ico_96x96.ico").as_posix())
        filtrate_icon = QIcon((self.icon_path / "line_filtrate_ico_96x96.ico").as_posix())
        win_folder_icon = QIcon((self.icon_path / "win_folder_ico_96x96.ico").as_posix())
        log_icon = QIcon((self.icon_path / "log.png").as_posix())
        restart_icon = QIcon((self.icon_path / "restart_ico_96x96.ico").as_posix())
        icon_0 = QIcon((self.icon_path / "16gl-0.png").as_posix())
        icon_1 = QIcon((self.icon_path / "16gl-1.png").as_posix())
        icon_2 = QIcon((self.icon_path / "16gl-2.png").as_posix())
        icon_3 = QIcon((self.icon_path / "16gl-3.png").as_posix())
        icon_4 = QIcon((self.icon_path / "16gl-4.png").as_posix())
        icon_5 = QIcon((self.icon_path / "16gl-5.png").as_posix())

        # 创建二级菜单-删除选项
        sub_menu = QMenu("删除选项", self.context_menu) 
        sub_menu.setIcon(delete_icon)  
        sub_menu.addAction(icon_0, "从列表中移除(D)", self.delete_from_list)  
        sub_menu.addAction(icon_1, "从源文件删除(Ctrl+D)", self.delete_from_file)  

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
        self.context_menu.addAction(zip_icon, "压缩文件(Z)", self.compress_selected_files)
        self.context_menu.addAction(theme_icon, "切换主题(P)", self.on_p_pressed)
        self.context_menu.addAction(image_size_reduce_icon, "图片瘦身(X)", self.on_x_pressed) 
        self.context_menu.addAction(ps_icon, "图片调整(L)", self.on_l_pressed)
        self.context_menu.addAction(tcp_icon, "截图功能(T)", self.screen_shot_tool)
        self.context_menu.addAction(command_icon, "批量执行命令工具(M)", self.open_bat_tool)
        self.context_menu.addAction(rename_icon, "批量重命名工具(F4)", self.on_f4_pressed)
        self.context_menu.addAction(raw_icon, "RAW转JPG工具(F1)", self.on_f1_pressed)
        self.context_menu.addAction(log_icon, "打开日志文件(F3)", self.on_f3_pressed)
        self.context_menu.addAction(win_folder_icon, "打开资源管理器(W)", self.reveal_in_explorer)
        self.context_menu.addAction(refresh_icon, "刷新(F5)", self.on_f5_pressed)
        self.context_menu.addAction(restart_icon, "重启程序", self.restart)
        self.context_menu.addAction(help_icon, "关于(Ctrl+H)", self.on_ctrl_h_pressed)

        # 设置右键菜单绑定右侧表格组件
        self.context_menu.exec_(self.RB_QTableWidget0.mapToGlobal(pos))

    @log_performance_decorator(tips="设置左侧文件浏览器右键菜单", log_args=False, log_result=False)
    def setup_treeview_context_menu(self):
        """设置左侧文件浏览器右键菜单,连接到文件浏览树self.Left_QTreeView上"""
        self.Left_QTreeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.Left_QTreeView.customContextMenuRequested.connect(self.show_treeview_context_menu)

    @log_error_decorator(tips="显示文件树右键菜单")
    def show_treeview_context_menu(self, pos):
        """显示文件树右键菜单"""
        # 设置左侧文件浏览器的右键菜单栏
        self.treeview_context_menu = QMenu(self)
    
        # 设置右键菜单样式
        self.treeview_context_menu.setStyleSheet(f"""
            QMenu {{
                /*background-color: #F0F0F0;   背景色 */
                font-family: "{self.font_jetbrains_s.family()}";
                font-size: {self.font_jetbrains_s.pointSize()}pt;    
            }}
            QMenu::item:selected {{
                /* 选中项背景色 */
                background-color: {self.background_color_default};   
                /* 选中项字体颜色 */
                color: #000000; 
            }}
        """)

        # 添加常用操作
        show_file_action = self.treeview_context_menu.addAction(
            "显示文件" if not self.left_tree_file_display else "隐藏文件")
        add_to_table_action = self.treeview_context_menu.addAction("添加到table(多选)")
        send_path_to_aebox = self.treeview_context_menu.addAction("发送到aebox(单选)")
        breakup_acton = self.treeview_context_menu.addAction("解散文件夹")
        zoom_action = self.treeview_context_menu.addAction("按zoom分类")
        size_action = self.treeview_context_menu.addAction("按size分类")
        open_action = self.treeview_context_menu.addAction("打开")
        copy_path_action = self.treeview_context_menu.addAction("复制")
        rename_action = self.treeview_context_menu.addAction("重命名")        
        delete_action = self.treeview_context_menu.addAction("删除")

        # 获取选中的文件信息, 并链接相应事件函数
        if selection := self.Left_QTreeView.selectionModel().selectedRows(0):
            # 获取选中文件或者文件夹列表
            file_path = [self.file_system_model.filePath(idx) for idx in selection]
            # 连接想信号槽函数
            open_action.triggered.connect(lambda: self.open_file_location(file_path))  
            copy_path_action.triggered.connect(lambda: self.copy_file_path(file_path))
            send_path_to_aebox.triggered.connect(lambda: self.send_file_path_to_aebox(file_path))
            rename_action.triggered.connect(lambda: self.rename_file(file_path))
            show_file_action.triggered.connect(self.show_file_visibility)
            breakup_acton.triggered.connect(lambda: self.breakup_folder(file_path))
            delete_action.triggered.connect(lambda: self.delete_file(file_path))
            add_to_table_action.triggered.connect(lambda: self.add_folder_to_table(file_path))
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
        self.main_ui_icon = (self.icon_path / "viewer_3.ico").as_posix()
        self.setWindowIcon(QIcon(self.main_ui_icon))
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

        # 设置可以选中多个文件夹，通过右键处理 modify by diamond-cz-20250908
        self.Left_QTreeView.setSelectionMode(QTreeView.ExtendedSelection)
        self.Left_QTreeView.setSelectionBehavior(QAbstractItemView.SelectRows)

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
        self.RT_QComboBox.addItem(self.root_path.as_posix())
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
        # 添加快捷键 y 打开展锐工具解析窗口
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
        self.z_shortcut.activated.connect(self.on_x_pressed) 
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
        try:
            # 标志位为 TRUE 时，显示所有文件
            self.left_tree_file_display = not self.left_tree_file_display
            if self.left_tree_file_display:
                self.file_system_model.setFilter(QDir.NoDot | QDir.NoDotDot |QDir.AllEntries)  # 显示所有文件和文件夹
                return

            # 默认只显示文件夹
            self.file_system_model.setFilter(QDir.NoDot | QDir.NoDotDot | QDir.AllDirs)    # 使用QDir的过滤器,只显示文件夹  
        except Exception as e:
            print(f"[show_file_visibility]-->error--设置左侧文件浏览器的显示时 | 报错: {e}")
            self.logger.error(f"【show_file_visibility】-->设置左侧文件浏览器的显示时 | 报错：{e}")
            show_message_box("🚩设置左侧文件浏览器的显示时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def zoom_file(self, path):
        """按zoom值分类"""
        try:
            # 导入分类函数
            from src.utils.cls_zoom_size import classify_images_by_zoom

            # 统一为可迭代的文件夹路径列表
            folder_paths = [str(p) for p in path if p] if isinstance(path, (list, tuple, set)) else []
            if not folder_paths:
                show_message_box("🚩未获取到有效的文件夹路径", "提示", 1500)
                return

            # 确保选中的是单个文件夹
            if len(folder_paths) > 1 or not os.path.isdir(path := folder_paths[0]):
                show_message_box("🚩仅支持对单个-^文件夹^-进行<按ZOOM分类>", "提示", 1500)
                return
                
            # 调用分类函数
            classify_images_by_zoom(path)
        except Exception as e:
            print(f"[zoom_file]-->error--处理文件夹内图片按Zoom大小分类事件时 | 报错: {e}")
            self.logger.error(f"【zoom_file】-->处理文件夹内图片按Zoom大小分类事件时 | 报错: {e}")


    def size_file(self, path):
        """按尺寸分类"""
        try:
            # 导入分类函数
            from src.utils.cls_zoom_size import classify_images_by_size

            # 统一为可迭代的文件夹路径列表
            folder_paths = [str(p) for p in path if p] if isinstance(path, (list, tuple, set)) else []
            if not folder_paths:
                show_message_box("🚩未获取到有效的文件夹路径", "提示", 1500)
                return

            # 确保选中的是单个文件夹
            if len(folder_paths) > 1 or not os.path.isdir(path := folder_paths[0]):
                show_message_box("🚩仅支持对单个-^文件夹^-进行<按SIZE分类>", "提示", 1500)
                return

            # 调用分类函数
            classify_images_by_size(path)
        except Exception as e:
            print(f"[size_file]-->error--处理文件夹内图片按尺寸分类事件时 | 报错: {e}")
            self.logger.error(f"【size_file】-->处理文件夹内图片按尺寸分类事件时 | 报错: {e}")

    def breakup_folder(self, folder_path):
        """解散选中的文件夹，将文件夹中的所有文件移动到上一级文件夹后删除空文件夹"""
        try:
            # 统一为可迭代的文件夹路径列表
            folder_paths = [str(p) for p in folder_path if p] if isinstance(folder_path, (list, tuple, set)) else []
            if not folder_paths:
                show_message_box("🚩未获取到有效的文件夹路径", "提示", 1500)
                return

            # 校验：全部为存在的文件夹
            invalid = [p for p in folder_paths if not os.path.isdir(p)]
            if invalid:
                show_message_box("🚩仅支持解散已存在的文件夹，请检查所选路径", "提示", 1500)
                return

            # 校验：如果多选，必须为同级文件夹（同一父目录）
            parent_dirs = {os.path.dirname(p) for p in folder_paths}
            if len(folder_paths) > 1 and len(parent_dirs) != 1:
                show_message_box("🚩仅支持解散同级文件夹，请确保选中同一父目录下的多个文件夹", "提示", 1800)
                return

            for one_folder in folder_paths:
                # 检查路径是否存在且为文件夹
                if not os.path.isdir(one_folder):
                    self.logger.warning(f"【breakup_folder】-->跳过非文件夹或不存在路径: {one_folder}")
                    continue

                # 获取文件夹中的所有文件（包括子文件夹中的文件）
                all_files = []
                for root, dirs, files in os.walk(one_folder):
                    for file in files:
                        # 计算相对路径，用于在父文件夹中重建目录结构
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, one_folder)
                        all_files.append((file_path, rel_path))

                # 如果文件夹为空，直接删除
                if not all_files:
                    try:
                        os.rmdir(one_folder)
                    except Exception as e:
                        self.logger.error(f"【breakup_folder】-->删除空文件夹失败: {one_folder} | 报错: {e}")
                    continue

                # 获取父文件夹路径,并将解散的文件夹内所有文件移动到父文件夹中
                parent_folder = os.path.dirname(one_folder)
                for file_path, rel_path in all_files:
                    try:
                        # 构建目标路径
                        target_path = os.path.join(parent_folder, rel_path)
                        target_dir = os.path.dirname(target_path)

                        # 创建目标目录（如果不存在）
                        if not os.path.isdir(target_dir):
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
                        self.logger.error(f"【breakup_folder】-->移动文件:{file_path}失败时 | 报错: {e}")
                        continue

                # 删除原文件夹（现在应该是空的）
                shutil.rmtree(one_folder, ignore_errors=True)

            # 获取同级文件夹的父文件夹, 统一刷新并定位到上一级父目录
            target_parent_dir = next(iter(parent_dirs)) if parent_dirs else ''
            if target_parent_dir and (index := self.file_system_model.index(target_parent_dir)).isValid():
                # 设置当前索引,展开该目录,滚动到该项，确保垂直方向居中,水平滚动条置0
                self.Left_QTreeView.setCurrentIndex(index)    
                self.Left_QTreeView.setExpanded(index, True)  
                self.Left_QTreeView.scrollTo(index, QAbstractItemView.PositionAtCenter)
                self.Left_QTreeView.horizontalScrollBar().setValue(0)
                # 触发左侧文件浏览器点击事件
                self.update_combobox(index)
        except Exception as e:
            show_message_box("🚩处理解散文件夹任务发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            print(f"[breakup_folder]-->error--处理解散文件夹事件时 | 报错: {e}")
            self.logger.error(f"【breakup_folder】-->处理解散文件夹事件时 | 报错: {e}")
            

    def delete_file(self, path):
        """安全删除文件/文件夹"""
        try:
            # 统一为可迭代的文件夹路径列表
            folder_paths = [str(p) for p in path if p] if isinstance(path, (list, tuple, set)) else []
            if not folder_paths:
                show_message_box("🚩未获取到有效的文件夹路径", "提示", 1500)
                return

            # Windows系统处理只读属性
            def remove_readonly(func, path, _):
                os.chmod(path, stat.S_IWRITE)
                func(path)

            deleted_count, failed_paths = 0, []
            for one_path in path:
                try:
                    if not os.path.exists(one_path):
                        self.logger.warning(f"【delete_file】-->跳过不存在的路径: {one_path}")
                        continue
                        
                    # 移除只读属性, 删除文件
                    if os.path.isfile(one_path): 
                        os.chmod(one_path, stat.S_IWRITE)
                        os.remove(one_path)
                    else: # 删除文件夹
                        shutil.rmtree(one_path, onerror=remove_readonly if os.name == 'nt' else None)
                    
                    deleted_count += 1
                except Exception as e:
                    failed_paths.append(one_path)
                    self.logger.error(f"【delete_file】-->删除失败: {one_path} | 报错: {e}")
                    continue

            # 显示删除结果
            if failed_paths:
                show_message_box(f"🚩删除完成，成功: {deleted_count} 个，失败: {len(failed_paths)} 个\n🐬失败路径请查看日志", "提示", 2000)
            elif deleted_count > 0:
                show_message_box(f"✅成功删除 {deleted_count} 个文件/文件夹", "提示", 1500)

            # 刷新文件系统模型和表格
            self.file_system_model.setRootPath('')
            self.Left_QTreeView.viewport().update()
            self.update_RB_QTableWidget0()

        except Exception as e:
            print(f"[delete_file]-->error--安全删除文件/文件夹事件时 | 报错: {e}")
            self.logger.error(f"【delete_file】-->安全删除文件/文件夹事件时 | 报错: {e}")
            show_message_box("🚩删除选中的文件/文件夹时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def open_file_location(self, path=[]):
        """在资源管理器中打开路径(适用于window系统)"""
        try:
            # 如果选中多个文件或者文件夹，只取列表中的第一个
            if isinstance(path, list):
                path = path[0]
            
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

        except Exception as e:
            print(f"[open_file_location]-->error--在资源管理器中打开路径(适用于window系统)时 | 报错: {e}")
            self.logger.error(f"【open_file_location】-->在资源管理器中打开路径(适用于window系统)时 | 报错: {e}")
            show_message_box("🚩在资源管理器中打开选中的路径时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    @log_error_decorator(tips="处理左侧文件浏览区复制文件路径到剪贴板事件")
    def copy_file_path(self, path): 
        """复制文件路径到剪贴板
        支持传入单个路径字符串，或 list/tuple/set 的多个路径。
        多个路径时以换行分隔复制。
        """
        try:
            # 统一处理集合类型
            if isinstance(path, list):
                paths = [str(p) for p in path if p]
                text = paths[0] if len(paths) == 1 else "\n".join(paths)
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
        except Exception as e:
            print(f"[copy_file_path]-->error--复制文件路径到剪贴板时 | 报错: {e}")
            self.logger.error(f"【copy_file_path】-->复制文件路径到剪贴板时 | 报错: {e}")


    def add_folder_to_table(self, folder_path):
        """将选中的文件夹添加到右侧表格中作为新的一列"""
        try:
            # 统一为可迭代的文件夹路径列表
            folder_paths = [str(p) for p in folder_path if os.path.isdir(p)] if isinstance(folder_path, (list, tuple, set)) else []
            if not folder_paths:
                show_message_box("🚩未获取到有效的文件夹路径", "提示", 1500)
                return

            # 添加到新增的文件夹列表,更新右侧表格
            self.additional_folders_for_table = folder_paths
            self.update_RB_QTableWidget0()

        except Exception as e:
            print(f"[add_folder_to_table]-->error--添加文件夹到表格时 | 报错: {e}")
            self.logger.error(f"【add_folder_to_table】-->添加文件夹到表格时 | 报错: {e}")
            show_message_box("🚩将选中的文件夹添加到表格时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def send_file_path_to_aebox(self, path): 
        """将文件夹路径发送到aebox"""
        try:
            # 如果选中多个文件或者文件夹，只取列表中的第一个
            if isinstance(path, list):
                path = path[0]

            if not os.path.isdir(path):
                show_message_box(f"仅支持发送文件夹, 请确保选中文件夹后发送", "提示", 1500)
                return                

            # 导入Fast API配置与Aebox通信
            from src.utils.aebox_link import check_process_running, urlencode_folder_path, get_api_data 
            if not check_process_running("aebox"):
                show_message_box(f"未检测到aebox进程, 请先手动打开aebox软件", "提示", 1500)
                return

            if not self.statusbar_checkbox.isChecked():
                show_message_box(f"未启用Fast_API功能, 请先手动打开界面底部复选框启用", "提示", 1500)
                return

            # 获取url编码，拼接文件夹, 发送请求通信到aebox
            if image_path_url := urlencode_folder_path(path):
                image_path_url = f"http://{self.fast_api_host}:{self.fast_api_port}/set_image_folder/{image_path_url}"
                response = get_api_data(url=image_path_url, timeout=3)
                message = "发送文件夹成功" if response else "发送文件夹失败"
                print(f"[send_file_path_to_aebox]-->执行函数任务, {message}")
            
        except Exception as e:
            print(f"[send_file_path_to_aebox]-->error--将文件夹路径发送到aebox时 | 报错: {e}")
            self.logger.error(f"【send_file_path_to_aebox】-->将文件夹路径发送到aebox时 | 报错: {e}")
            show_message_box("🚩将文件夹路径发送到aebox时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            

    def rename_file(self, path):
        """重命名文件/文件夹"""
        try:
            # 导入自定义重命名对话框类
            from src.components.custom_qdialog_rename import SingleFileRenameDialog 

            # 分别处理选中多个文件夹和单个文件夹重命名的情况
            if isinstance(path, list):
                # 多个选中
                if len(path) != 1: 
                    self.open_rename_tool(path)
                    return
                # 单个选中
                else: 
                    path = path[0]
                    dialog = SingleFileRenameDialog(path, self)
                    dialog.setWindowTitle("重命名文件/文件夹")
                    if dialog.exec_() == QDialog.Accepted:
                        if (new_path := dialog.get_new_file_path()):
                            # 更新文件系统模型以及地址栏和表格显示
                            if (index := self.file_system_model.index(new_path)).isValid():
                                # 设置当前索引,展开该目录,滚动到该项，确保垂直方向居中,水平滚动条置0
                                self.Left_QTreeView.setCurrentIndex(index)    
                                self.Left_QTreeView.setExpanded(index, True)  
                                self.Left_QTreeView.scrollTo(index, QAbstractItemView.PositionAtCenter)
                                self.Left_QTreeView.horizontalScrollBar().setValue(0)
                                self.update_combobox(index)
        except Exception as e:
            print(f"[rename_file]-->error--执行重命名事件时 | 报错: {e}")
            self.logger.error(f"【rename_file】-->执行重命名事件时 | 报错: {e}")

    """
    右侧信号槽函数
    """
    @log_error_decorator(tips="模仿用户在地址栏按下回车键")
    def input_enter_action(self): 
        # 定位到左侧文件浏览器中
        self.locate_in_tree_view()
        # 初始化同级文件夹下拉框选项
        self.RT_QComboBox1_init()
        # 更新右侧表格
        self.update_RB_QTableWidget0()


    @log_error_decorator(tips="处理右上角清除按钮点击事件")
    def clear_combox(self, index):
        # 清空地址栏
        self.RT_QComboBox.clear()
        # 手动清除图标缓存
        IconCache.clear_cache()
        # 清除日志文件和缓存
        self.clear_log_and_cache_files()
        # 模拟用户在地址回车
        self.input_enter_action()
        # 释放内存
        self.cleanup() 
        
    @log_error_decorator(tips="处理右上角对比按钮点击事件")
    def compare(self, index):
        self.on_space_pressed()

    @log_error_decorator(tips="处理底部栏设置按钮点击事件")
    def setting(self, index):
        self.open_settings_window()
    
    @log_performance_decorator(tips="底部栏点击版本信息按钮检查更新任务", log_args=False, log_result=False)
    def update(self, index):
        # 处理底部栏版本信息按钮点击事件
        from src.utils.update import check_update
        check_update()


    def fast_api_switch(self):
        """设置fast_api服务的开关使能"""
        try:
            # 设置开关使能标志位,勾选复选框使能服务关闭横线，反之有横线
            flag_fast_api = not self.statusbar_checkbox.isChecked()
            font = self.statusbar_button3.font()
            font.setStrikeOut(flag_fast_api)
            self.statusbar_button3.setFont(font)
            
            # 提示信息，输出日志
            meesage = "开启" if not flag_fast_api else "关闭"
            print(f"[fast_api_switch]-->执行函数任务, {meesage}FastAPI服务")
            self.logger.info(f"[fast_api_switch]-->执行函数任务, {meesage}FastAPI服务")
        except Exception as e:
            print(f"[fast_api_switch]-->error--设置fast_api开关使能时 | 报错: {e}")
            self.logger.error(f"【fast_api_switch】-->设置fast_api开关使能时 | 报错: {e}")
            show_message_box("🚩设置fast_api服务的开关使能时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def fast_api(self):
        """设置fast_api服务地址"""
        try:
            from src.components.custom_qdialog_fastapi import FastApiDialog 
            dialog = FastApiDialog(self)
            if dialog: # 设置图标以及host和port
                dialog.setWindowIcon(QIcon(self.main_ui_icon))
                dialog.ip_edit.setText(self.fast_api_host)
                dialog.port_edit.setText(self.fast_api_port)
            if dialog.exec_() == QDialog.Accepted:
                # 获取会话框上面的用户输入的IP地址和端口
                self.fast_api_host, self.fast_api_port = dialog.get_result()
                
                # 打印提示信息，输出日志，更新底部信息栏
                print(f"[fast_api]-->执行函数任务, 设置FastAPI服务地址为: {self.fast_api_host}:{self.fast_api_port}")
                self.logger.info(f"[fast_api]-->执行函数任务, 设置FastAPI服务地址为: {self.fast_api_host}:{self.fast_api_port}")
                self.statusbar_button3.setText(f"{self.fast_api_host}:{self.fast_api_port}")

                # 保存fast_api地址和端口到ipconfig.ini配置文件
                FASTAPI=f"[API]\nhost = {self.fast_api_host}\nport = {self.fast_api_port}"
                default_version_path = self.root_path / "config" / "ipconfig.ini"
                default_version_path.parent.mkdir(parents=True, exist_ok=True)
                with open(default_version_path, 'w', encoding='utf-8') as f:
                    f.write(FASTAPI)
            else:
                print(f"[fast_api]-->执行函数任务, 取消设置FastAPI服务地址会话")
                self.logger.info(f"[fast_api]-->执行函数任务, 取消设置FastAPI服务地址会话")
        except Exception as e:
            print(f"[fast_api]-->error--设置fast_api服务地址时 | 报错: {e}")
            self.logger.error(f"【fast_api】-->设置fast_api服务地址时 | 报错: {e}")
            return


    @log_performance_decorator(tips="预更新版本", log_args=False, log_result=False)
    def pre_update(self):
        """预更新版本函数
        检查更新版本信息，并更新状态栏按钮，如果耗时超过2秒，则提示用户更新失败
        """
        # 预检查更新,检查是否有最新版本
        from src.utils.update import pre_check_update     
        self.new_version_info = pre_check_update()
        if not self.new_version_info:
            self.statusbar_button2.setToolTip("已是最新版本")
            return
        # 有新版本可用
        self.statusbar_button2.setText(f"🚀有新版本可用") 
        self.statusbar_button2.setToolTip(f"🚀新版本: {self.version_info}-->{self.new_version_info}")
        self.apply_theme() 

        
    def show_exif(self):
        """打开Exif信息显示"""
        print("[show_exif]-->执行函数任务,处理【Alt+I】键事件, 打开Exif信息显示")
        self.logger.info("[show_exif]-->执行函数任务,处理【Alt+I】键事件, 打开Exif信息显示")
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
            print(f"[show_exif]-->error--使用【Alt+I】键打开Exif信息显示时 | 报错: {e}")
            self.logger.error(f"【show_exif】-->使用【Alt+I】键打开Exif信息显示时 | 报错: {e}")
        finally:
            # 更新 RB_QTableWidget0 中的内容    
            self.update_RB_QTableWidget0() 

    
    def show_filter_rows(self, row_type):
        """显示筛选行"""
        print(f"[show_filter_rows]-->执行函数任务, 显示筛选行")
        self.logger.error(f"[show_filter_rows]-->执行函数任务, 显示筛选行")
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
            print(f"[show_filter_rows]-error--显示筛选行时 | 报错: {e}")
            self.logger.error(f"【show_filter_rows】-->显示筛选行时 | 报错: {e}")
            return

    def filter_rows(self, row_type):
        """批量选中指定模式行（使用类switch结构优化）"""
        # 清空选中状态
        self.RB_QTableWidget0.clearSelection()

        # 获取总行数，获取选中状态,定义选择范围
        total_rows = self.RB_QTableWidget0.rowCount()
        selection = self.RB_QTableWidget0.selectionModel()
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
        try:
            # 获取判断条件
            if not (condition := condition_map.get(row_type)):
                show_message_box(f"未知筛选模式: {row_type}", "错误", 1000)
                return
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
            print(f"[filter_rows]-error--批量选中指定模式行时 | 报错: {e}")
            self.logger.error(f"【filter_rows】-->批量选中指定模式行时 | 报错: {e}")
            return

    def jpg_lossless_rotator(self, para=''):
        """无损旋转图片"""
        print(f"[jpg_lossless_rotator]-->执行函数任务, 启动无损旋转图片任务...")
        self.logger.info(f"[jpg_lossless_rotator]-->执行函数任务, 启动无损旋转图片任务...")
        try:
            # 取消当前的预加载任务
            self.cancel_preloading()

            # 构建jpegoptim的完整路径
            jpegr_path = (self.root_path / "resource" / 'tools' / 'jpegr_lossless_rotator' / 'jpegr.exe').as_posix()
            if not os.path.exists(jpegr_path):
                show_message_box(f"jpegr.exe 不存在，请检查/tools/jpegr_lossless_rotator/", "提示", 1500)
                return
            
           # 获取选中的项文件路径列表
            if not(files := self.get_selected_file_path()):
                show_message_box(f"🚩无法获取选中项的文件路径列表, 请确保选中了单元格", "提示", 2000)
                return

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
                            show_message_box(f"用户手动取消无损旋转操作，\n已无损旋转前{index+1}张图,共{len(files)}张", "提示", 2000)
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
            print(f"[jpg_lossless_rotator]-error--无损旋转图片 | 报错: {e}")
            self.logger.error(f"【jpg_lossless_rotator】-->无损旋转图片 | 报错: {e}")
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
                    # 常规拼接构建完整路径的办法，效率较低
                    else: 
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


    def copy_selected_file_path(self):
        """复制所有选中的单元格的文件路径到系统粘贴板"""
        try:
            # 获取选中的项文件路径列表
            if not(file_paths := self.get_selected_file_path()):
                show_message_box(f"🚩无法获取选中项的文件路径列表, 请确保选中了单元格", "提示", 2000)
                return

            # 将文件路径复制到剪贴板，使用换行符分隔
            clipboard_text = "\n".join(file_paths)
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            show_message_box(f"{len(file_paths)} 个文件路径已复制到剪贴板", "提示", 2000)

        except Exception as e:
            print(f"[copy_selected_file_path]-->error--复制选中的单元格文件路径到系统剪贴板时 | 报错: {e}")
            self.logger.error(f"【copy_selected_file_path】-->复制选中的单元格文件路径到系统剪贴板时 | 报错: {e}")
            show_message_box("🚩复制选中文件路径到系统剪贴板时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def copy_selected_files(self):
        """复制选中的单元格对应的所有文件到系统剪贴板"""
        try:
            # 获取选中的项文件路径列表
            if not(file_paths := self.get_selected_file_path()):
                show_message_box(f"🚩无法获取选中项的文件路径列表, 请确保选中了单元格", "提示", 2000)
                return

            # 创建QMimeData对象，设置文件路径
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(path) for path in file_paths])

            # 将QMimeData放入剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setMimeData(mime_data)
            show_message_box(f"{len(file_paths)} 个文件已复制到剪贴板", "提示", 2000)

        except Exception as e:
            print(f"[copy_selected_files]-->error--复制选中的单元格文件到系统剪贴板时 | 报错: {e}")
            self.logger.error(f"【copy_selected_files】-->复制选中的单元格文件到系统剪贴板时 | 报错: {e}")
            show_message_box("🚩复制选中文件到系统剪贴板时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def delete_from_list(self):
        """从列表中移除选中的单元格"""
        # 收集要删除的项目信息
        items_to_delete = []
        try:
            # 获取选中的项并判断是否选中
            if not (selected_items := self.RB_QTableWidget0.selectedItems()):
                show_message_box("没有选中的项！", "提示", 500)
                return

            # 遍历选中项
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
            
            # 执行移除操作
            for col_idx, row in items_to_delete:
                if col_idx < len(self.files_list) and row < len(self.files_list[col_idx]):
                    del self.files_list[col_idx][row]
                    del self.paths_list[col_idx][row]
            
            # 更新文件路径索引，方便加载图标
            self.paths_index = {value: (i, j) for i, row in enumerate(self.paths_list) for j, value in enumerate(row)}

            # 更新表格显示
            self.update_RB_QTableWidget0_from_list(self.files_list, self.paths_list, self.dirnames_list)
        except Exception as e:
            print(f"[delete_from_list]-->error--从列表中移除选中的单元格时 | 报错: {e}")
            self.logger.error(f"【delete_from_list】-->从列表中移除选中的单元格时 | 报错: {e}")
            show_message_box("🚩从列表中移除选中的单元格时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def delete_from_file(self):
        """从源文件删除选中的单元格文件"""
        try:
            # 获取选中的项文件路径列表
            if not(file_paths_to_delete := self.get_selected_file_path()):
                show_message_box(f"🚩无法获取选中项的文件路径列表, 请确保选中了单元格", "提示", 2000)
                return

            # 删除文件
            for file_path in file_paths_to_delete:
                os.remove(file_path)

            # 删除表格中的行，可以直接更新表格
            show_message_box(f"{len(file_paths_to_delete)} 个文件已从列表中删除并删除原文件", "提示", 1000)
            self.update_RB_QTableWidget0()

        except Exception as e:
            print(f"[delete_from_file]-->error--从源文件删除选中的单元格文件时 | 报错: {e}")
            self.logger.error(f"【delete_from_file】-->从源文件删除选中的单元格文件时 | 报错: {e}")
            show_message_box("🚩从源文件删除选中的文件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            

    def compress_selected_files(self):
        """压缩选中的文件并复制压缩包文件到剪贴板"""
        try:
            # 获取将要压缩的文件路径列表
            if not (files_to_compress := self.get_selected_file_path()):
                show_message_box("🚩没有选中的项 | 没有有效的文件可压缩!!!", "提示", 1000)
                return
            
            # 导入自定义压缩进度对话框类       
            from src.components.custom_qdialog_progress import InputDialog, ProgressDialog, CompressWorker   

            # 获取压缩包名称
            zip_name_dialog = InputDialog(self)
            if zip_name_dialog.exec_() == QDialog.Accepted:
                # 获取输入框的名称，确保不为空
                zip_name = zip_name if (zip_name := zip_name_dialog.get_result()) else "zip压缩文件"
            else:
                print(f"[compress_selected_files]-->取消压缩文件 | 未输入有效压缩文件名")
                self.logger.error(f"[compress_selected_files]-->取消压缩文件 | 未输入有效压缩文件名")
                return

            # 设置压缩包文件路径存在; 确保父目录存在; 将path格式转换为str格式
            zip_path = self.root_path / "cache" / f"{zip_name}.zip"
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            zip_path = zip_path.as_posix()

            # 创建并启动压缩工作线程
            self.compress_worker = CompressWorker(files_to_compress, zip_path)
            
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
            print(f"[compress_selected_files]-->启动压缩压缩任务线程")
            self.logger.info(f"[compress_selected_files]-->启动压缩压缩任务线程")
        except Exception as e:
            print(f"[compress_selected_files]-->error--压缩选中的文件并复制压缩包文件到剪贴板时 | 报错: {e}")
            self.logger.error(f"[compress_selected_files]-->压缩选中的文件并复制压缩包文件到剪贴板时 | 报错: {e}")
            return  

    @log_error_decorator(tips="打开【T】键截图界面")
    def screen_shot_tool(self):
        """截图功能"""
        # 导入截图工具类
        from src.utils.hisnot import WScreenshot 
        WScreenshot.run()

    def on_x_pressed(self):
        """打开图片瘦身工具"""
        try:
            # 获取选中的项文件路径列表
            if not(file_paths := self.get_selected_file_path()):
                show_message_box(f"🚩无法获取选中项的文件路径列表, 请确保选中了单元格", "提示", 2000)
                return

            # 打开图片瘦身子界面
            from src.view.sub_image_skinny_view import PicZipMainWindow                
            self.image_skinny_window = PicZipMainWindow()
            self.image_skinny_window.set_image_list(file_paths)
            self.image_skinny_window.setWindowIcon(QIcon((self.icon_path/"image_skinny.ico").as_posix()))  
            self.image_skinny_window.show()
        except Exception as e:
            show_message_box(f"启动图片瘦身工具失败: {str(e)}", "错误", 2000)
            print(f"[on_x_pressed]-->error--启动图片瘦身工具时 | 报错: {e}")
            self.logger.error(f"on_x_pressed-->启动图片瘦身工具时 | 报错: {e}")
            show_message_box("🚩打开图片体积压缩工具发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def reveal_in_explorer(self):
        """在资源管理器中高亮定位选中的文件(适用于window系统)"""
        try:
            # 获取选中单元格的文件路径列表
            if not(file_paths := self.get_selected_file_path()):
                show_message_box("请先选择要定位的文件", "提示", 1000)
                return

            # 默认选取文件路径列表中的首个路径进行定位
            full_path = file_paths[0]

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
                show_message_box(f"🚩当前平台为{sys.platform}, 暂不支持在系统资源管理器中打开", "提示", 1500)
                ...
        except Exception as e:
            show_message_box("🚩在资源管理器中高亮定位选中的文件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            print(f"[reveal_in_explorer]-->error--在资源管理器中高亮定位选中的文件时 | 报错: {e}")
            self.logger.error(f"【reveal_in_explorer】-->在资源管理器中高亮定位选中的文件时 | 报错: {e}")
            

    def on_compress_progress(self, current, total):
        """处理压缩进度"""
        try:
            progress_value = int((current / total) * 100)  # 计算进度百分比
            self.progress_dialog.update_progress(progress_value)
            self.progress_dialog.set_message(f"显示详情：正在压缩文件... {current}/{total}")
        except Exception as e:
            print(f"[on_compress_progress]-->error--压缩进度信号 | 报错：{e}")
            self.logger.error(f"【on_compress_progress】-->压缩进度信号 | 报错：{e}")

    @log_error_decorator(tips="压缩线程-->触发取消压缩信号")
    def cancel_compression(self):
        """取消压缩任务"""
        if self.compress_worker:
            self.compress_worker.cancel()  
        self.progress_dialog.close()  
        
        # 若是压缩取消，强制删除缓存文件中的zip文件
        if (cache_dir := self.root_path / "cache").exists():
            # 导入强制删除函数并调用
            from src.utils.delete import force_delete_folder
            force_delete_folder(cache_dir.as_posix(), '.zip')
        
        # 提示信息
        print(f"-->成功 取消压缩任务 | 删除所有zip缓存文件")
        self.logger.info(f"-->成功 取消压缩任务 | 删除所有zip缓存文件")
        

    @log_error_decorator(tips="压缩线程-->触发压缩完成信号")
    def on_compress_finished(self, zip_path):
        """处理压缩完成"""
        self.progress_dialog.close()
        # 将压缩包复制到剪贴板
        mime_data = QMimeData()
        url = QUrl.fromLocalFile(zip_path)
        mime_data.setUrls([url])
        QApplication.clipboard().setMimeData(mime_data)
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"📢:文件压缩完成,已复制到剪贴板🍃")
        self.logger.info(f"[on_compress_finished]-->选中的文件已完成压缩 | 保存路径: {zip_path}")
        show_message_box(f"🚩文件压缩完成,已复制到剪贴板", "提示", 1000)

    @log_error_decorator(tips="压缩线程-->触发压缩错误信号")
    def on_compress_error(self, error_msg):
        """处理压缩错误"""
        self.progress_dialog.close()  
        # 更新状态栏信息显示
        self.statusbar_label1.setText(f"📢:压缩出错🍃")
        print(f"[on_compress_error]-->error--触发压缩错误信号 | 报错：{error_msg}")
        self.logger.error(f"【on_compress_error】-->触发压缩错误信号 | 报错：{error_msg}")
        # 弹出提示框
        show_message_box(error_msg, "错误", 2000)


    """
    自定义功能函数区域：
    拖拽功能函数 self.dragEnterEvent(), self.dropEvent()
    左侧文件浏览器与地址栏联动功能函数 self.locate_in_tree_view, selfupdate_combobox
    右侧表格显示功能函数 self.update_RB_QTableWidget0()
    """
    @log_error_decorator(tips="触发拖拽事件-->仅接受文件夹拖拽")
    def dragEnterEvent(self, event):
        # 如果拖入的是文件夹，则接受拖拽
        if event.mimeData().hasUrls():
            event.accept()

    @log_error_decorator(tips="接受拖拽事件-->更新拖拽文件夹到地址栏-->定位到文件浏览区-->更新到同级下拉框-->更新表格显示")
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
        """处理左侧文件浏览区点击事件, 定位更新右侧combobox事件处理函数"""
        print("[update_combobox]-->执行函数任务, 处理左侧文件浏览区点击事件")
        self.logger.info(f"[update_combobox]-->执行函数任务, 处理左侧文件浏览区点击事件")
        try:
            # 清空历史的已选择,清空新增的文件夹列表
            self.statusbar_label.setText(f"💦已选文件数[0]个")
            self.additional_folders_for_table = []

            # 更新左侧文件浏览器中的预览区域显示-->先清空旧预览内容-->然后显示预览信息
            self.clear_preview_layout() 
            self.show_preview_error("预览区域")

            # 获取左侧文件浏览器中当前点击的文件夹路径，并显示在地址栏
            if os.path.isdir(current_path := self.file_system_model.filePath(index)):
                if self.RT_QComboBox.findText(current_path) == -1:
                    self.RT_QComboBox.addItem(current_path)
                self.RT_QComboBox.setCurrentText(current_path)
                print(f"-->[update_combobox]-->左侧文件浏览区点击的文件夹【{current_path}】已成功更新到地址栏中")

            # 禁用左侧文件浏览器中的滚动条自动滚动
            self.Left_QTreeView.setAutoScroll(False)

            # 将同级文件夹添加到 RT_QComboBox1 中
            self.RT_QComboBox1_init()      

            # 更新右侧RB_QTableWidget0表格
            self.update_RB_QTableWidget0()
        except Exception as e:
            print(f"[update_combobox]-->error--左侧文件浏览器点击事件,定位更新右侧combobox事件处理函数 | 报错：{e}")
            self.logger.error(f"【update_combobox】-->左侧文件浏览器点击事件,定位更新右侧combobox事件处理函数 | 报错：{e}")
            show_message_box("🚩处理左侧文件浏览器点击事件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
        
    @log_error_decorator(tips="定位到左侧文件浏览器中(地址栏或拖拽文件夹路径)")
    def locate_in_tree_view(self):
        """地址栏或者拖拽文件夹定位到左侧文件浏览器函数"""
        # 检查路径是否有效; 获取当前目录的索引,并确保索引有效
        if os.path.isdir(current_directory := self.RT_QComboBox.currentText()) and (index := self.file_system_model.index(current_directory)).isValid():
            # 设置当前索引,展开该目录,滚动到该项，确保垂直方向居中,水平滚动条置0
            self.Left_QTreeView.setCurrentIndex(index)    
            self.Left_QTreeView.setExpanded(index, True)  
            self.Left_QTreeView.scrollTo(index, QAbstractItemView.PositionAtCenter)
            self.Left_QTreeView.horizontalScrollBar().setValue(0)


    def update_RB_QTableWidget0_from_list(self, file_infos_list, file_paths, dir_name_list):
        """从当前列表中更新表格，适配从当前列表删除文件功能"""
        try:
            # 输出日志文件
            self.logger.info(f"[update_RB_QTableWidget0_from_list]-->执行函数任务，从当前列表中更新表格函数任务")
            print(f"[update_RB_QTableWidget0_from_list]-->执行函数任务，从当前列表中更新表格")    
           
            # 清空表格和缓存
            self.RB_QTableWidget0.clear()
            self.RB_QTableWidget0.setRowCount(0)
            self.RB_QTableWidget0.setColumnCount(0)

            # 先初始化表格结构和内容，不加载图标,并获取图片列有效行最大值；重绘表格,更新显示
            self.image_index_max = self.init_table_structure(file_infos_list, dir_name_list)
            self.RB_QTableWidget0.repaint()

            # 对file_paths进行转置,实现加载图标按行加载,使用列表推导式
            file_name_paths = [path for column in zip_longest(*file_paths, fillvalue=None) for path in column if path is not None]
            if file_name_paths: # 确保文件路径存在后，开始预加载
                self.start_image_preloading(file_name_paths)

        except Exception as e:
            print(f"[update_RB_QTableWidget0_from_list]-->error--从当前列表中更新表格任务失败: {e}")
            self.logger.error(f"【update_RB_QTableWidget0_from_list】-->从当前列表中更新表格任务失败: {e}")
            show_message_box("🚩从当前列表中更新表格时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def update_RB_QTableWidget0(self):
        """更新右侧表格功能函数"""
        try:
            # 输出日志文件
            self.logger.info(f"[update_RB_QTableWidget0]-->执行函数任务,更新右侧表格功能函数任务")
            print(f"[update_RB_QTableWidget0]-->执行函数任务,更新右侧表格功能函数任务")

            # 清空表格和缓存
            self.RB_QTableWidget0.clear()
            self.RB_QTableWidget0.setRowCount(0)
            self.RB_QTableWidget0.setColumnCount(0)
            
            # 收集文件名基本信息以及文件路径，文件索引字典，同级文件夹列表，并将相关信息初始化为类中全局变量
            file_infos_list, file_paths, path_indexs, dir_name_list = self.collect_file_paths()
            self.files_list = file_infos_list      # 初始化文件名及基本信息列表
            self.paths_list = file_paths           # 初始化文件路径列表
            self.paths_index = path_indexs         # 初始化文件路径索引字典
            self.dirnames_list = dir_name_list     # 初始化选中的同级文件夹列表

            # 先初始化表格结构和内容，不加载图标, 并获取图片列有效行最大值；重绘表格,更新显示    
            self.image_index_max = self.init_table_structure(file_infos_list, dir_name_list)    
            self.RB_QTableWidget0.repaint()

            # 对file_paths进行转置,实现加载图标按行加载，并初始化预加载图标线程前的问价排列列表
            file_name_paths = [path for column in zip_longest(*file_paths, fillvalue=None) for path in column if path is not None]
            if file_name_paths:  # 确保有文件路径, 开始预加载图标  
                self.start_image_preloading(file_name_paths)

        except Exception as e:
            print(f"[update_RB_QTableWidget0]-->error--更新右侧表格功能函数任务失败: {e}")
            self.logger.error(f"【update_RB_QTableWidget0】-->更新右侧表格功能函数任务时 | 报错: {e}")
            show_message_box("🚩更新右侧表格功能函数任务时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def init_table_structure(self, file_name_list, dir_name_list):
        """初始化表格结构和内容，不包含图标"""
        try:
            # 判断是否存在文件
            if not file_name_list or not file_name_list[0]:
                print(f"[init_table_structure]-->waring--传入的文件名列表为空，无法初始化表格结构和内容")
                self.logger.warning(f"[init_table_structure]-->传入的文件名列表为空，无法初始化表格结构和内容")
                return []  

            # 设置表格的列数;设置列标题名称为当前选中的文件夹名
            self.RB_QTableWidget0.setColumnCount(len(file_name_list))
            self.RB_QTableWidget0.setHorizontalHeaderLabels(dir_name_list)  
            
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
            print(f"[init_table_structure]-->error--初始化表格结构和内容失败: {e}")
            self.logger.error(f"【init_table_structure】-->初始化表格结构和内容失败: {e}")
            return []

    def collect_file_paths(self):
        """收集需要显示的文件路径"""
        # 初始化文件名列表,文件路径列表，文件夹名列表
        file_infos, file_paths, paths_index, dir_name_list = [], [], [], []     
        try:
            # 获取同级文件夹复选框中选择的文件夹路径列表
            selected_folders = self.model.getCheckedItems()
            # 读取地址栏当前显示的文件夹路径, 兼容路径最后一位字符为"/"的情况，获取父文件夹
            if current_directory := self.RT_QComboBox.currentText(): 
                current_directory = current_directory[:-1] if current_directory[-1] == "/" else current_directory 
            parent_directory = os.path.dirname(current_directory)
            
            # 构建所有需要显示的文件夹路径, 并将当前选中的文件夹路径插入到列表的最前面 
            selected_folders_path = [Path(parent_directory, path).as_posix() for path in selected_folders]
            selected_folders_path.insert(0, current_directory)
            
            # 添加通过右键菜单添加到表格的文件夹
            if self.additional_folders_for_table:
                # 直接替换同级文件夹列表
                selected_folders_path = self.additional_folders_for_table
                # 更新地址栏上的显示信息
                display_str = (
                "---右键单选添加到table模式,同级下拉框不可用,单击左侧文件夹可恢复---" 
                if len(self.additional_folders_for_table) == 1 else 
                "---右键多选添加到table模式,同级下拉框不可用,单击左侧文件夹可恢复---")
                self.RT_QComboBox.setCurrentText(display_str)

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
            elif selected_option == "显示所有文件":
                selected_folders_path = [folder for folder in selected_folders_path 
                                    if os.path.exists(folder) and any(os.scandir(folder))]
            else: # 默认显示所有文件
                selected_folders_path = [folder for folder in selected_folders_path 
                                    if os.path.exists(folder) and any(os.scandir(folder))]

            # 遍历selected_folders_path，提取文件信息列表和文件路径列表
            for folder in selected_folders_path:
                if not os.path.exists(folder):
                    continue
                # 根据选项过滤文件列表，提取文件信息列表和文件路径列表
                if file_info_list := self.filter_files(folder):
                    # 文件信息列表，获取带EXIF信息的文件信息列表
                    file_infos.append(file_info_list) 
                    # 文件路径列表，获取文件信息列表file_name_list的最后一列
                    file_paths.append([item[-1] for item in file_info_list])
            
            # 根据文件路径列表获取文件路径索引映射字典
            paths_index = {value: (i, j) for i, row in enumerate(file_paths) for j, value in enumerate(row)}

            # 获取文件夹名列表，保证名称唯一
            # dir_name_list = [os.path.basename(dir_name) for dir_name in selected_folders_path]
            dir_name_list = make_unique_dir_names(selected_folders_path)

            # 返回提取的结果,文件信息列表,文件路径列表，文件夹名列表
            return file_infos, file_paths, paths_index, dir_name_list
        except Exception as e:
            print(f"【collect_file_paths】-->error--收集需要显示的文件路径 | 报错：{e}")
            self.logger.error(f"【collect_file_paths】-->收集需要显示的文件路径 | 报错：{e}")
            return [], [], [], []
        
    def filter_files(self, folder):
        """根据选项过滤文件"""
        # 导入图片处理工具类
        from src.utils.image import ImageProcessor 
        # 导入文件排序工具类
        from src.utils.sort import sort_by_custom 

        files_and_dirs_with_mtime = [] 
        opt = self.RT_QComboBox0.currentText()
        sort_option = self.RT_QComboBox2.currentText()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    # 使用follow_symlinks=False避免跟随软链接带来的 IO
                    if not entry.is_file(follow_symlinks=False):
                        continue

                    # 统一转换为小写后判断
                    name_lower = entry.name.lower()
                    if opt == "显示图片文件" and not name_lower.endswith(self.IMAGE_FORMATS):
                        continue
                    if opt == "显示视频文件" and not name_lower.endswith(self.VIDEO_FORMATS):
                        continue
                    if opt not in ("显示图片文件", "显示视频文件", "显示所有文件"):
                        continue
                    
                    # 收集(宽、高、曝光时间、ISO)等信息
                    width = height = exposure_time = iso = None
                    if opt == "显示图片文件" and not self.simple_mode:
                        try:
                            with ImageProcessor(entry.path) as img:
                                width, height = img.width, img.height
                                exposure_time, iso = img.exposure_time, img.iso
                        except Exception as e:
                            self.logger.error(f"类【ImageProcessor】-->获取图片exif信息 | 报错：{e}")
                            print(f"类[ImageProcessor]-->获取图片exif信息 | 报错：{e}")

                    # 使用pathlib确保文件路径都用正斜杠 / 表示；拼接根据opt筛选后的文件信息列表
                    norm_path = Path(entry.path).as_posix()
                    st = entry.stat()
                    files_and_dirs_with_mtime.append((
                    entry.name, st.st_ctime, st.st_mtime, st.st_size,
                    (width, height), exposure_time, iso, norm_path))
                        
            # 使用sort_by_custom函数进行排序
            files_and_dirs_with_mtime = sort_by_custom(sort_option, files_and_dirs_with_mtime, self.simple_mode, opt)

            # 返回提取的带exif信息的列表和文件路径列表
            return files_and_dirs_with_mtime
        except Exception as e:
            print(f"[filter_files]-->error--根据选项过滤文件 | 报错：{e}")
            self.logger.error(f"【filter_files】-->根据选项过滤文件 | 报错：{e}")
            return []

        
    def start_image_preloading(self, file_paths):
        """开始预加载图片"""
        # 导入文件Icon图标加载类
        from src.utils.Icon import ImagePreloader                        

        # 输出打印日志文件
        print("[start_image_preloading]-->执行函数任务, 开始预加载图标, 启动预加载线程")
        self.logger.info(f"[start_image_preloading]-->执行函数任务, 开始预加载图标, 启动预加载线程")
        try:
            # 执行取消预加载任务
            if self.current_preloader and self.preloading:
                print("-->检测到预加载已启动, 取消预加载任务...")
                self.logger.info(f"[start_image_preloading]-->检测到预加载已启动, 取消预加载任务...")
                self.current_preloader._stop = True
                self.current_preloader = None  

            # 设置预加载状态以及时间
            self.preloading = True
            self.start_time_image_preloading = time.time()
        
            # 创建新的预加载器
            batch = len(self.paths_list) if self.paths_list else 10
            self.current_preloader = ImagePreloader(file_paths, batch)
            self.current_preloader.signals.progress.connect(self.update_preload_progress)
            self.current_preloader.signals.batch_loaded.connect(self.on_batch_loaded)
            self.current_preloader.signals.finished.connect(self.on_preload_finished)
            self.current_preloader.signals.error.connect(self.on_preload_error)
            
            # 启动预加载
            self.threadpool.start(self.current_preloader)
            print("-->开始后台预加载图标...")
            self.logger.info(f"[start_image_preloading]-->开始后台预加载图标...")
        except Exception as e:
            print(f"[start_image_preloading]-->error--开始预加载图标, 启动预加载线程失败: {e}")
            self.logger.error(f"【start_image_preloading】-->开始预加载图标,启动预加载线程失败: {e}")

    @log_error_decorator(tips="取消当前预加载任务")
    def cancel_preloading(self):
        """取消当前预加载任务"""
        # 执行取消预加载任务
        if self.current_preloader and self.preloading:
            self.current_preloader._stop = True  
            self.preloading = False
            self.current_preloader = None     

    
    def on_batch_loaded(self, batch):
        """处理批量加载完成的图标"""
        try:
            # 更新表格中对应的图标
            for path, icon in batch:
                self.update_table_icon(path, icon)
        except Exception as e:
            print(f"[on_batch_loaded]-->error--处理批量加载完成的图标任务 | 报错：{e}")
            self.logger.error(f"【on_batch_loaded】-->处理批量加载完成的图标任务 | 报错：{e}")

    def update_table_icon(self, file_path, icon):
        """更新表格中的指定图标"""
        # 使用字典self.paths_index快速查找索引
        if file_path and file_path in self.paths_index:
            col, row = self.paths_index[file_path]
            if (item := self.RB_QTableWidget0.item(row, col)) and icon:
                item.setIcon(icon)
        if False: # 原来双循环方案，效率较低，移除
            filename = os.path.basename(file_path)
            folder = os.path.basename(os.path.dirname(file_path))
            # 先在每一行中查找文件名
            for row in range(self.RB_QTableWidget0.rowCount()):
                # 遍历每一列查找匹配的文件夹
                for col in range(self.RB_QTableWidget0.columnCount()):
                    header = self.RB_QTableWidget0.horizontalHeaderItem(col)
                    item = self.RB_QTableWidget0.item(row, col)
                    if (header and header.text().split('/')[-1] == folder and item and item.text().split('\n')[0] == filename):
                        if bool(icon):
                            item.setIcon(icon)
                        return  # 找到并更新后直接返回

    def update_preload_progress(self, current, total):
        """处理预加载进度"""
        self.statusbar_label1.setText(f"📢:图标加载进度...{current}/{total}🍃")
        
    def on_preload_finished(self):
        """处理预加载完成"""
        print(f"[on_preload_finished]-->所有图标预加载完成, 耗时:{time.time()-self.start_time_image_preloading:.2f}秒")
        self.logger.info(f"[on_preload_finished]-->所有图标预加载完成 | 耗时:{time.time()-self.start_time_image_preloading:.2f}秒")
        self.statusbar_label1.setText(f"📢:图标已全部加载-^-耗时:{time.time()-self.start_time_image_preloading:.2f}秒🍃")
        gc.collect()

    def on_preload_error(self, error):
        """处理预加载错误"""
        print(f"[on_preload_error]-->图标预加载错误: {error}")
        self.logger.error(f"【on_preload_error】-->图标预加载错误: {error}")
            
    def RT_QComboBox1_init(self):
        """自定义RT_QComboBox1, 添加复选框选项"""
        try:
            # 写入日志信息
            print("[RT_QComboBox1_init]-->开始添加地址栏文件夹的同级文件夹到下拉复选框中")
            self.logger.info(f"[RT_QComboBox1_init]-->开始添加地址栏文件夹的同级文件夹到下拉复选框中")
            # 获取同级文件夹列表
            sibling_folders = []
            if current_directory := self.RT_QComboBox.currentText():
                sibling_folders = self.getSiblingFolders(current_directory)    
            # 初始化模型，绑定模型到 QComboBox, 设置自定义委托，禁用右键菜单
            self.model = CheckBoxListModel(sibling_folders)  
            self.RT_QComboBox1.setModel(self.model)  
            self.RT_QComboBox1.setItemDelegate(CheckBoxDelegate())  
            self.RT_QComboBox1.setContextMenuPolicy(Qt.NoContextMenu)
        except Exception as e:
            print(f"[RT_QComboBox1_init]-->error--初始化失败: {e}")
            self.logger.error(f"【RT_QComboBox1_init】-->添加地址栏文件夹的同级文件夹到下拉复选框时 | 报错: {e}")

    def handleComboBoxPressed(self, index):
        """处理同级文件夹复选框选项被按下时的事件。"""
        print("[handleComboBoxPressed]-->更新复选框状态")
        try:
            if not index.isValid():
                show_message_box(f"🚩下拉复选框点击无效,当前index:{index}", "提示", 1500)
                return
            self.model.setChecked(index)  # 更新复选框的状态
        except Exception as e:
            print(f"[handleComboBoxPressed]-->error--更新复选框状态失败: {e}")
            self.logger.error(f"【handleComboBoxPressed】-->处理显示同级文件夹下拉框选项按下事件时 | 报错: {e}")
    
    def handleComboBox0Pressed(self, index):
        """处理显示(图片/视频/所有文件)下拉框选项被按下事件"""
        try:
            # 链式三目表达式选择显示文件类型，记录log信息
            display_txt = "图片" if index == 0 else ("视频" if index == 1 else "所有")
            self.logger.info(f"[handleComboBox0Pressed]-->处理显示{display_txt}文件下拉框选项按下事件")
            self.update_RB_QTableWidget0()
        except Exception as e:
            print(f"[handleComboBox0Pressed]-->error--处理显示{display_txt}文件下拉框选项按下事件失败: {e}")
            self.logger.error(f"【handleComboBox0Pressed】-->处理显示{display_txt}文件下拉框选项按下事件时 | 报错: {e}")
            show_message_box(f"🚩处理显示{display_txt}文件下拉框选项按下事件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def updateComboBox1Text(self):
        """更新 RT_QComboBox1 的显示文本。"""
        print("[updateComboBox1Text]-->执行函数任务, 更新<RT_QComboBox1>同级文件夹下拉框的显示文本")
        self.logger.info(f"[updateComboBox1Text]-->执行函数任务, 更新<RT_QComboBox1>同级文件夹下拉框的显示文本")
        try:# 获取选中的文件夹,并更新RT_QComboBox1显示
            current_text = '; '.join(selected_folders) if (selected_folders := self.model.getCheckedItems()) else "(请选择)"
            self.RT_QComboBox1.setCurrentText(current_text)
            # 更新右侧表格
            self.update_RB_QTableWidget0()
        except Exception as e:
            print(f"[updateComboBox1Text]-->error--更新显示文本失败: {e}")
            self.logger.error(f"【updateComboBox1Text】-->更新显示文本下拉框失败: {e}")
            show_message_box("🚩更新显示文本时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def getSiblingFolders(self, folder_path):
        """获取指定文件夹的同级文件夹列表。"""
        try:
            # 获取父文件夹路径（兼容地址栏最后一位为"/"的情况）, 然后过滤出同级文件夹，不包括当前选择的文件夹
            folder_path = folder_path[:-1] if folder_path[-1] == "/" else folder_path
            
            # 获取folder_path父文件夹内的同级文件夹列表
            parent_folder = os.path.dirname(folder_path)   
            sibling_folders = [
                name for name in os.listdir(parent_folder) 
                if os.path.isdir(os.path.join(parent_folder, name)) and name != os.path.basename(folder_path)  
                ]
            
            # 打印提示信息，并返回同级文件夹列表
            print(f"[getSiblingFolders]-->获取【{folder_path}】的同级文件夹列表: \n-->{sibling_folders}")
            return sibling_folders
        except Exception as e:
            print(f"[getSiblingFolders]-->error--获取同级文件夹列表失败: {e}")
            self.logger.error(f"【getSiblingFolders】-->获取指定文件夹的同级文件夹列表 | 报错: {e}")
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
                # 清空旧预览内容,根据预览文件完整路径动态选则预览区显示图像,更新状态栏显示选中数量
                self.clear_preview_layout() 
                self.display_preview_image_dynamically(file_paths[0])
                self.statusbar_label.setText(f"💦已选文件数[{len(file_paths)}]个")
        except Exception as e:
            print(f"[handle_table_selection]-->error--处理表格选中事件失败: {e}")
            self.logger.error(f"【handle_table_selection】-->处理主界面右侧表格选中事件 | 报错: {e}")
            show_message_box("🚩处理表格选中事件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def display_preview_image_dynamically(self, preview_file_path):
        """动态显示预览图像"""
        try:
            # 导入视频预览工具类
            from src.utils.video import extract_video_first_frame   
            # 导入heic文件解析工具类
            from src.utils.heic import extract_jpg_from_heic

            # 图片文件处理,更具文件类型创建图片预览
            if (file_extension := os.path.splitext(preview_file_path)[1].lower()).endswith(self.IMAGE_FORMATS):
                # 处理HEIC格式图片，成功提取则创建并显示图片预览，反之则显示提取失败
                if file_extension.endswith(".heic"):
                    if new_path := extract_jpg_from_heic(preview_file_path):
                        self.create_image_preview(new_path)
                        return
                    self.show_preview_error("提取HEIC图片失败")
                # 非".heic"文件直接使用图片文件生成预览
                self.create_image_preview(preview_file_path)
                return

            # 视频文件处理,提取视频文件首帧图，创建并显示预览图
            elif file_extension.endswith(self.VIDEO_FORMATS):
                if (video_path := extract_video_first_frame(preview_file_path)):
                    self.create_image_preview(video_path) 
                else: 
                    self.show_preview_error("视频文件预览失败")
                return

            # 非图片/视频格式文件处理
            self.show_preview_error("不支持预览的文件类型")
        except Exception as e:
            print(f"[display_preview_image_dynamically]-->error--动态显示预览图像 | 报错: {e}")
            self.logger.error(f"【display_preview_image_dynamically】-->动态显示预览图像 | 报错: {e}")
            show_message_box("🚩动态显示预览图像时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def clear_preview_layout(self):
        """清空预览区域"""
        try:
            # 清理 image_viewer 引用
            if hasattr(self, 'image_viewer') and self.image_viewer:
                try: # 先调用自定义清理方法，然后删除对象
                    if hasattr(self.image_viewer, 'cleanup'):
                        self.image_viewer.cleanup()
                    self.image_viewer.deleteLater()
                except Exception as e:
                    print(f"[clear_preview_layout]-->error--清理image_viewer失败: {e}")
                    self.logger.error(f"【clear_preview_layout】-->清理image_viewer失败: {e}")
                finally:
                    self.image_viewer = None
            
            # 清理布局中的所有组件
            while self.verticalLayout_left_2.count():
                item = self.verticalLayout_left_2.takeAt(0)
                if (widget := item.widget()):
                    widget.deleteLater()
        except Exception as e:
            print(f"[clear_preview_layout]-->error--清空预览区域失败 | 报错: {e}")
            self.logger.error(f"【clear_preview_layout】-->清空预览区域 | 报错: {e}")
            show_message_box("🚩清空预览区域时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    
    def create_image_preview(self, path):
        """创建图片预览"""
        try:
            # 导入自定义图片预览组件
            from src.common.img_preview import ImageViewer                                

            # 清空旧预览内容
            self.clear_preview_layout()
            # 创建 ImageViewer 实例-->加载图片-->添加到layout
            self.image_viewer = ImageViewer(self.Left_QFrame)
            self.image_viewer.load_image(path)
            self.verticalLayout_left_2.addWidget(self.image_viewer)
            self.Left_QFrame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception as e:
            print(f"[create_image_preview]-->error--创建图片预览区域失败 | 报错: {e}")
            self.logger.error(f"【create_image_preview】-->创建图片预览 | 报错: {e}")
            show_message_box("🚩创建图片预览时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    def show_preview_error(self, message):
        """显示预览错误信息"""
        try:
            error_label = QLabel(message)
            error_label.setStyleSheet("color: white;")
            error_label.setFont(self.font_jetbrains_m)
            error_label.setAlignment(Qt.AlignCenter)
            self.verticalLayout_left_2.addWidget(error_label)
        except Exception as e:
            print(f"[show_preview_error]-->error--显示预览错误信息失败 | 报错：{e}")
            self.logger.error(f"【show_preview_error】-->显示预览错误信息 | 报错：{e}")
            show_message_box("🚩显示预览错误信息时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def handle_sort_option(self):
        """处理排序选项"""
        print(f"[handle_sort_option]-->执行函数任务，处理排序下拉框事件")
        self.logger.info(f"[handle_sort_option]-->执行函数任务，处理排序下拉框事件")
        try:
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
            print(f"[handle_sort_option]-->error--处理排序下拉框事件失败 | 报错：{e}")
            self.logger.error(f"【handle_sort_option】-->处理排序下拉框事件 | 报错：{e}")
            show_message_box("🚩处理排序下拉框事件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)


    @log_error_decorator(tips=f"处理主题切换下拉框选择事件")
    def handle_theme_selection(self, index=None):
        """处理下拉框选择事件"""
        self.current_theme = "默认主题" if self.RT_QComboBox3.currentText() == "默认主题" else "暗黑主题"
        self.apply_theme()
    
    @log_error_decorator(tips=f"切换主题")
    def toggle_theme(self):
        """切换主题"""
        self.current_theme = "暗黑主题" if self.current_theme == "默认主题" else "默认主题"
        self.apply_theme()

    def apply_theme(self):
        """更新主题"""
        try:
            print(f"[apply_theme]-->执行函数任务, 当前主题更新为{self.current_theme}")
            self.logger.info(f"[apply_theme]-->执行函数任务, 当前主题更新为{self.current_theme}")
            self.setStyleSheet(self.dark_style() if self.current_theme == "暗黑主题" else self.default_style())
        except Exception as e:
            print(f"[apply_theme]-->error-更新主题 | 报错：{e}")
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
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
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
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
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
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
            }}
            QComboBox QAbstractItemView {{
                /* 下拉列表样式 */
                background-color: {QCOMBox_BACKCOLOR};
                color: {FONTCOLOR};
                selection-background-color: {BACKCOLOR};
                selection-color: {FONTCOLOR};
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
            }}
            QComboBox QAbstractItemView::item {{
                /* 下拉项样式 */
                min-height: 25px;
                padding: 5px;
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
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
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
            }}
            QComboBox QAbstractItemView {{
                /* 下拉列表样式 */
                background-color: {QCOMBox_BACKCOLOR};
                color: {FONTCOLOR};
                selection-background-color: {BACKCOLOR};
                selection-color: {FONTCOLOR};
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
            }}
            QComboBox QAbstractItemView::item {{
                /* 下拉项样式 */
                min-height: 25px;
                padding: 5px;
                font-family: "{self.font_jetbrains.family()}";
                font-size: {self.font_jetbrains.pointSize()}pt;
            }}

        """
        # 标签的样式表
        statusbar_label_style = f"""
            QLabel {{
                border: none;
                color: {"rgb(255,255,255)"};
                text-align: center;
                font-family: "{self.font_jetbrains_s.family()}";
                font-size: {self.font_jetbrains_s.pointSize()}pt;
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
                font-family: "{self.font_jetbrains_s.family()}";
                font-size: {self.font_jetbrains_s.pointSize()}pt;
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
                font-family: "{self.font_jetbrains_s.family()}";
                font-size: {self.font_jetbrains_s.pointSize()}pt;
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
            font-family: {self.font_jetbrains_s.family()};
            font-size: {self.font_jetbrains_s.pointSize()}pt;
            
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
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
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
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
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
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
                }}
                QComboBox QAbstractItemView {{
                    /* 下拉列表样式 */
                    background-color: {BLACK};
                    color: {WHITE};
                    selection-background-color: {WHITE};
                    selection-color: {BLACK};
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
                }}
                QComboBox QAbstractItemView::item {{
                    /* 下拉项样式 */
                    min-height: 25px;
                    padding: 5px;
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
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
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
                }}
                QComboBox QAbstractItemView {{
                    /* 下拉列表样式 */
                    background-color: {WHITE};
                    color: {BLACK};
                    selection-background-color: {BACKCOLOR_};
                    selection-color: {WHITE};
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
                }}
                QComboBox QAbstractItemView::item {{
                    /* 下拉项样式 */
                    min-height: 25px;
                    padding: 5px;
                    font-family: "{self.font_jetbrains.family()}";
                    font-size: {self.font_jetbrains.pointSize()}pt;
                }}
            """
            statusbar_label_style = f"""
                border: none;
                color: {WHITE};
                font-family: {self.font_jetbrains_s.family()};
                font-size: {self.font_jetbrains_s.pointSize()}pt;
            """
            statusbar_button_style = f"""
                QPushButton {{
                    background-color: {BLACK};
                    color: {WHITE};
                    text-align: center;
                    font-family: "{self.font_jetbrains_s.family()}";
                    font-size: {self.font_jetbrains_s.pointSize()}pt;
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
                    font-family: "{self.font_jetbrains_s.family()}";
                    font-size: {self.font_jetbrains_s.pointSize()}pt;
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
            self.paths_index = {}  
            self.dirnames_list = []
            self.additional_folders_for_table = []
            # 12. 强制垃圾回收
            gc.collect()
            # 打印提示信息，输出日志信息
            print("[cleanup]-->资源清理完成")
            self.logger.info("[cleanup]-->资源清理完成")
        except Exception as e:
            print(f"[cleanup]-->error--资源清理过程中发生错误: {e}")
            self.logger.error(f"【cleanup】-->资源清理过程中发生错误: {e}")
            
    def _cleanup_sub_windows(self):
        """清理所有子窗口"""
        # 清理看图子窗口
        if hasattr(self, 'compare_window') and self.compare_window:
            try:
                self.compare_window.deleteLater()
                self.compare_window = None
            except Exception as e:
                print(f"[_cleanup_sub_windows]-->error--清理compare_window失败: {e}")
                self.logger.error(f"【_cleanup_sub_windows】-->清理compare_window失败: {e}")
        
        # 清理视频播放器
        if hasattr(self, 'video_player') and self.video_player:
            try:
                self.video_player.deleteLater()
                self.video_player = None
            except Exception as e:
                print(f"[_cleanup_sub_windows]-->error--清理video_player失败: {e}")
                self.logger.error(f"【_cleanup_sub_windows】-->清理video_player失败: {e}")
        
        # 清理搜索窗口
        if hasattr(self, 'search_window') and self.search_window:
            try:
                self.search_window.deleteLater()
                self.search_window = None
            except Exception as e:
                print(f"[_cleanup_sub_windows]-->error--清理search_window失败: {e}")
                self.logger.error(f"【_cleanup_sub_windows】-->清理search_window失败: {e}")
    
    def _cleanup_tool_windows(self):
        """清理所有工具窗口"""
        tool_windows = [
            'rename_tool',
            'image_process_window', 
            'bat_tool',
            'raw2jpg_tool'
        ]
        # 遍历子窗口并清理
        for tool_name in tool_windows:
            if hasattr(self, tool_name) and getattr(self, tool_name):
                try:
                    tool = getattr(self, tool_name)
                    tool.deleteLater()
                    setattr(self, tool_name, None)
                except Exception as e:
                    print(f"[_cleanup_tool_windows]-->error--清理{tool_name}失败: {e}")
                    self.logger.error(f"【_cleanup_tool_windows】-->清理{tool_name}失败: {e}")
    
    def _cleanup_dialogs(self):
        """清理所有对话框"""
        # 清理帮助对话框
        if hasattr(self, 'help_dialog') and self.help_dialog:
            try:
                del self.help_dialog
            except Exception as e:
                print(f"[_cleanup_dialogs]-->error--清理help_dialog失败: {e}")
                self.logger.error(f"【_cleanup_dialogs】-->清理help_dialog失败: {e}")
        
        # 清理进度对话框
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            try:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
                self.progress_dialog = None
            except Exception as e:
                print(f"[_cleanup_dialogs]-->error--清理progress_dialog失败: {e}")
                self.logger.error(f"【_cleanup_dialogs】-->清理progress_dialog失败: {e}")
    
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
                    print(f"[_cleanup_threads]-->error--清理{thread_name}失败: {e}")
                    self.logger.error(f"【_cleanup_threads】-->清理{thread_name}失败: {e}")
    
    def _cleanup_compression_resources(self):
        """清理压缩相关资源"""
        # 清理压缩工作线程
        if hasattr(self, 'compress_worker') and self.compress_worker:
            try:
                self.compress_worker.cancel()
                self.compress_worker = None
            except Exception as e:
                print(f"[_cleanup_compression_resources]-->error--清理compress_worker失败: {e}")
                self.logger.error(f"【_cleanup_compression_resources】-->清理compress_worker失败: {e}")
        

    @log_performance_decorator(tips="从JSON文件加载上一次关闭时的设置", log_args=True, log_result=False)
    def load_settings(self):
        """从JSON文件加载设置"""
        if (settings_path := self.root_path / "config" / "basic_settings.json").exists():
            with open(settings_path, "r", encoding='utf-8', errors='ignore') as f:
                settings = json.load(f)

                # 恢复地址栏历史记录和当前目录
                self.RT_QComboBox.clear()
                self.RT_QComboBox.addItems(settings.get("combobox_history", []))
                current_directory = settings.get("current_directory", "")
                current_directory = current_directory if os.path.isdir(current_directory) else self.root_path.as_posix()
                self.RT_QComboBox.setCurrentText(current_directory)

                # 恢复地址栏后，定位地址栏文件夹到左侧文件浏览器中
                self.locate_in_tree_view()

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

                # 恢复极简模式状态,默认开启
                self.simple_mode = settings.get("simple_mode", True)

                # 恢复拖拽模式状态,默认开启
                self.drag_flag = settings.get("drag_flag", True)

                # 恢复fast_api使能开关,默认关闭,并初始化一下
                self.api_flag = settings.get("api_flag", False)
                self.statusbar_checkbox.setChecked(self.api_flag)
                self.fast_api_switch()

                # 恢复播放器内核key
                self.player_key = settings.get("player_key", True)

                # 恢复同级文件夹选择状态，放在最后
                all_items = settings.get("combobox1_all_items", [])
                checked_items = settings.get("combobox1_checked_items", [])
                if all_items and checked_items:
                    # 判断同级文件夹选中项是否存在
                    if any(p for p in [Path(current_directory).parent / name for name in checked_items] if p.exists()):
                        # 设置同级下拉框初始化
                        self.model = CheckBoxListModel(all_items)
                        self.RT_QComboBox1.setModel(self.model)
                        self.RT_QComboBox1.setItemDelegate(CheckBoxDelegate())
                        self.RT_QComboBox1.setContextMenuPolicy(Qt.NoContextMenu)

                        # 恢复选中状态
                        for i, item in enumerate(self.model.items):
                            if item in checked_items:
                                self.model.setChecked(self.model.index(i))

                        # 更新同级文件夹下拉框选项, 会触发更新表格事件self.update_RB_QTableWidget0()
                        self.updateComboBox1Text()
                        return
                
                # 模仿用户按下回车
                self.input_enter_action()
                return
                
        # 初始化主题设置，并模仿用户在地址栏按下回车
        self.apply_theme()
        self.input_enter_action()
        

    def save_settings(self):
        """保存当前设置到JSON文件"""
        try:
            # 使用 pathlib.Path 统一路径处理，确保目录存在
            settings_path = self.root_path / "config" / "basic_settings.json"
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
                "api_flag":self.statusbar_checkbox.isChecked(),

                # 播放器内核开关，True:CV; False:VLC
                "player_key":self.player_key
            }
            # 保存设置到JSON文件，使用 pathlib 的 write_text 方法
            settings_path.write_text(
                json.dumps(settings, ensure_ascii=False, indent=4), 
                encoding='utf-8'
            )
            
            # 打印提示信息，输出日志信息
            print(f"[save_settings]-->成功保存设置信息到: {settings_path.as_posix()}")
            self.logger.info(f"[save_settings]-->成功保存设置信息到JSON文件 | 路径: {settings_path.as_posix()}")
        except Exception as e:
            print(f"[save_settings]-->error--保存设置时出错: {e}")
            self.logger.error(f"【save_settings】-->保存设置到JSON文件失败: {e}")
            show_message_box("🚩保存设置到JSON文件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            

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
                if key_type == 'b': 
                    row_index -= step_row[col_index] # 使用上移方案【也是按下 b键的功能】 
                elif key_type == 'space':
                    row_index += step_row[col_index] # 默认使用下移方案【同时也是按下space键的功能】
                else:
                    row_index += step_row[col_index] # 默认使用下移方案【同时也是按下space键的功能】

                # 获取选中项文件完整路径列表. 
                # 1.先判断选中项移动位置是否超出表格范围，若超出则抛出异常，退出函数
                # 2.未超出表格范围，移动到正确的位置后，收集完整路径保存到列表中
                if row_min <= row_index <= row_max:
                    if(new_item := self.RB_QTableWidget0.item(row_index, col_index)):
                        # 选中新的单元格; 直接根据单元格索引从self.paths_list列表中拿完整文件路径
                        new_item.setSelected(True)
                        if (full_path := self.paths_list[col_index][row_index]) and os.path.isfile(full_path):  
                            file_path_list.append(full_path)
                        # 备用低效方案，拼接各个组件获取完整路径
                        else: 
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

            # 将选中的单元格滚动到视图中间位置; 返回文件路径列表和当前图片张数列表
            self.RB_QTableWidget0.scrollToItem(new_item, QAbstractItemView.PositionAtCenter)
            return file_path_list, file_index_list  
        except Exception as e:
            print(f"[press_space_or_b_get_selected_file_list]-->error--处理键盘按下事件报错: {e}")
            self.logger.error(f"【press_space_or_b_get_selected_file_list】-->处理键盘按下事件时 | 报错: {e}")
            return [], []
    
    @log_error_decorator(tips="处理F1键按下事件")
    def on_f1_pressed(self):                        
        """处理F1键按下事件
        函数功能说明: 打开MIPI RAW文件转换为JPG文件工具
        """
        # 导入MIPI RAW文件转换为JPG文件的类
        from src.utils.raw2jpg import Mipi2RawConverterApp  

        # 初始化文件格式转化类，设置窗口图标，添加链接关闭事件
        self.raw2jpg_tool = Mipi2RawConverterApp()
        self.raw2jpg_tool.setWindowTitle("MIPI RAW文件转换为JPG文件")
        icon_path = (self.icon_path / "raw_ico_96x96.ico").as_posix()
        self.raw2jpg_tool.setWindowIcon(QIcon(icon_path))
        self.raw2jpg_tool.closed.connect(self.on_raw2jpg_tool_closed)
        self.raw2jpg_tool.show()


    @log_error_decorator(tips="处理F3键按下事件,打开日志文件")
    def on_f3_pressed(self):
        """处理F3键按下事件"""
        # 定位日志文件路径
        if not (log_path := self.root_path / "cache" / "logs" / "hiviewer.log").exists():
            show_message_box("🚩定位日志文件【hiviewer.log】失败!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)
            self.logger.warning(f"on_f3_pressed()-->日志文件【hiviewer.log】不存在 | 路径:{log_path.as_posix()}")
            return

        # 使用系统记事本打开日志文件
        subprocess.Popen(["notepad.exe", log_path])
        print(f"[on_f3_pressed]-->使用系统记事本打开日志文件成功 | 路径: {log_path} ")
        self.logger.info(f"[on_f3_pressed]-->使用系统记事本打开日志文件成功 | 路径: {log_path} ")

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
        # 获取当前选中的文件路径列表
        if not (current_folder := self.get_selected_file_path()):
            show_message_box("当前没有选中的文件夹", "提示", 500)
            return

        # 将单个文件夹路径封装成列表传入，打开多文件夹重命名工具
        dir_path_list = [Path(_s).parent.parent.as_posix()] if (_s := current_folder[0]) else []
        self.open_rename_tool(dir_path_list)
 
    @log_error_decorator(tips="处理F4键按下事件")
    def on_f5_pressed(self):
        """处理F5键按下事件
        函数功能说明：刷新表格&清除缓存
        """  
        # 弹出刷新表格&清除缓存的提示框
        show_message_box("刷新表格&清除缓存-", "提示", 500)
        # 清除icon缓存
        IconCache.clear_cache()
        # 重新更新表格
        self.update_RB_QTableWidget0()

    @log_error_decorator(tips="清除日志文件以及zip缓存文件")
    def clear_log_and_cache_files(self):
        """清除日志文件以及zip缓存文件"""
        from src.utils.delete import clear_log_files, clear_cache_files
        # 使用工具函数清除日志文件以及zip等缓存
        clear_log_files()
        clear_cache_files(base_path=None, file_types=[".zip",".json",".ini"])
        # 重新初始化日志系统
        setup_logging(self.root_path)
        self.logger = get_logger(__name__)
        self.logger.info("---->成功清除日志文件，并重新初始化日志系统<----")
        print("---->成功清除日志文件，并重新初始化日志系统<----")

    @log_error_decorator(tips="重启hiviewer主程序")
    def restart(self):
        """处理 重启hiviewer主程序 事件
        函数功能说明: 重启hiviewer主程序
        """
        # 查找hiviewer主程序路径并判断是否存在
        program_path = self.root_path / "hiviewer.exe"
        if not program_path.exists():
            show_message_box("🚩无法重新启动主程序:【hiviewer.exe】\n🐬程序路径不存在!!!", "提示", 1500)
            self.logger.warning(f"[restart]-->无法重启hiviewer主程序,程序文件不存在: {program_path}")  
            return

        # 关闭主程序
        self.close()

        # 使用os.startfile启动程序，并等待3秒确保程序启动
        os.startfile(program_path)
        time.sleep(3)  
        self.logger.info(f"[restart]-->已重新启动主程序:【hiviewer.exe】")


    @log_error_decorator(tips="处理【Alt+Q】键按下事件")
    def on_escape_pressed(self):
        """处理【Alt+Q】键按下事件
        函数功能说明: 退出hiviewer主程序
        """
        self.logger.info("on_escape_pressed()-->组合键【Alt+Q】被按下, 退出hiviewer主程序")
        self.close()

    @log_error_decorator(tips="处理【Alt+A】键按下事件")
    def on_alt_pressed(self):
        """处理【Alt+A】键按下事件
        函数功能说明: 拖拽模式【开启\关闭】切换
        """
        self.drag_flag = not self.drag_flag
        message = "切换到拖拽模式" if self.drag_flag else "关闭拖拽模式"
        show_message_box(message, "提示", 500)
        

    @log_error_decorator(tips="处理【P】键按下事件, 准备切换主题")
    def on_p_pressed(self):
        """处理【P】键按下事件
        函数功能说明: 拖拽模式【开启\关闭】切换
        """
        # 设置下拉框显示并切换主题
        theme = "暗黑主题" if self.current_theme == "默认主题" else "默认主题"
        self.RT_QComboBox3.setCurrentIndex(self.RT_QComboBox3.findText(theme))
        self.toggle_theme()
                

    def on_i_pressed(self):
        """处理【i】键按下事件
        函数功能说明: 调用高通工具后台解析图片的exif信息
        """
        try:
            # 导入高通工具自定义对话框的类
            from src.components.custom_qdialog_LinkQualcomAebox import Qualcom_Dialog   

            # 创建自定义对话框, 传入地址栏文件夹路径，设置图标
            select_ = str(self.RT_QComboBox.currentText())
            dialog = Qualcom_Dialog(select_, self)
            dialog.setWindowIcon(QIcon(self.main_ui_icon))

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
            print(f"[on_i_pressed]-->error--处理i键按下事件 | 报错: {e}")
            self.logger.error(f"【on_i_pressed】-->处理i键按下事件 | 报错: {e}")
            show_message_box("🚩处理i键按下事件时发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

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
            print(f"[on_qualcom_finished]-->高通工具后台解析图片失败: {e}")
            self.logger.error(f"【on_qualcom_finished】-->高通工具后台解析图片失败: {e}")
            show_message_box("🚩高通工具后台解析图片发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def on_u_pressed(self):
        """处理【u】键按下事件
        函数功能说明: 调用联发科工具后台解析图片的exif信息
        """
        try:
            # 导入MTK工具自定义对话框的类
            from src.components.custom_qdialog_LinkMTKAebox import MTK_Dialog

            # 创建自定义对话框, 传入地址栏文件夹路径，设置图标
            select_ = str(self.RT_QComboBox.currentText())
            dialog = MTK_Dialog(select_, self)
            dialog.setWindowIcon(QIcon(self.main_ui_icon))

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
            print(f"[on_u_pressed]-->error--处理u键按下事件(MTK工具解析图片)失败: {e}")
            self.logger.error(f"【on_u_pressed】-->处理u键按下事件(MTK工具解析图片)失败: {e}")
            show_message_box("🚩MTK工具解析图片发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

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
            print(f"[on_mtk_finished]-->error--MTK_DebugParser工具后台解析图片失败: {e}")
            self.logger.error(f"【on_mtk_finished】-->MTK_DebugParser工具后台解析图片失败: {e}")

    def on_y_pressed(self):
        """处理【y】键按下事件
        函数功能说明: 调用展锐工具后台解析图片的exif信息
        """
        try:
            # 导入展锐工具自定义对话框的类
            from src.components.custom_qdialog_LinkUnisocAebox import Unisoc_Dialog 

            # 创建自定义对话框, 传入地址栏文件夹路径，设置图标
            select_ = str(self.RT_QComboBox.currentText())
            dialog = Unisoc_Dialog(select_, self)
            dialog.setWindowIcon(QIcon(self.main_ui_icon))
            
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
            print(f"[on_y_pressed]-->error--处理y键按下事件(展锐IQT工具解析图片)失败: {e}")
            self.logger.error(f"【on_y_pressed】-->处理y键按下事件(展锐IQT工具解析图片)失败: {e}")
            show_message_box("🚩展锐IQT工具解析图片发生错误!\n🐬具体报错请按【F3】键查看日志信息", "提示", 1500)

    def on_unisoc_finished(self, success, error_message, images_path=None):
        """unisoc_thread线程完成链接事件
        函数功能说明: 展锐IQT工具后台解析图片线程完成后的链接事件
        """
        try:
            # 导入展锐平台txt文件解析函数
            from src.utils.xml import save_excel_data_by_unisoc                                            
            if success and images_path:
                # 解析txt文件将其保存到excel中去
                if any(f for f in os.listdir(images_path) if f.endswith('.txt')):
                    save_excel_data_by_unisoc(images_path)
                use_time = time.time() - self.time_start
                show_message_box(f"展锐IQT工具后台解析图片成功! 用时: {use_time:.2f}秒", "提示", 1500)
                self.logger.info(f"on_unisoc_finished()-->展锐IQT工具后台解析图片成功! | 耗时: {use_time:.2f}秒")
            else:
                show_message_box(f"展锐IQT工具后台解析图片失败: {error_message}", "提示", 2000)
                self.logger.error(f"【on_unisoc_finished】-->展锐IQT工具后台解析图片失败: {error_message}")
        except Exception as e:
            show_message_box(f"展锐IQT工具后台解析图片失败: {error_message}", "提示", 2000)
            print(f"[on_unisoc_finished]-->error--展锐IQT工具后台解析图片失败: {e}")
            self.logger.error(f"【on_unisoc_finished】-->展锐IQT工具后台解析图片失败: {e}")


    @log_error_decorator(tips="处理【L】键按下事件,打开图片调整子界面")
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
            # 导入关于对话框类,显示帮助信息
            from src.components.custom_qdialog_about import AboutDialog                 

            # 单例模式管理帮助窗口
            if not hasattr(self, 'help_dialog'):
                # 构建文档路径,使用说明文档+版本更新文档
                User_path = self.root_path / "resource" / 'docs' / "User_Manual.md"
                Version_path = self.root_path / "resource" / 'docs' / "Version_Updates.md"
                # 验证文档文件存在性
                if not User_path.exists() or not Version_path.exists():
                    show_message_box(f"🚩帮助文档未找到:\n{User_path.as_posix()}or{Version_path.as_posix()}", "配置错误", 2000)
                    return

                # 初始化对话框
                self.help_dialog = AboutDialog(User_path, Version_path)
            
            # 激活现有窗口
            self.help_dialog.show()
            self.help_dialog.raise_()
            self.help_dialog.activateWindow()

            # 链接关闭事件
            self.help_dialog.finished.connect(self.close_helpinfo)
        except Exception as e:
            show_message_box("🚩打开关于子界面失败.🐬报错信息请打开日志文件查看...", "提示", 2000)
            error_msg = f"【on_ctrl_h_pressed】-->无法打开帮助文档:\n{str(e)}\n请检查程序是否包含文件: ./resource/docs/update_main_logs.md"
            print(f"[on_ctrl_h_pressed]-->error--无法打开帮助文档:{str(e)}")
            self.logger.error(error_msg)


    def open_settings_window(self):
        """打开设置窗口"""
        print("打开设置窗口...")
        from src.view.sub_setting_view import setting_Window
        self.setting_window = setting_Window(self)
        
        # 设置窗口标志，确保设置窗口显示在最顶层
        # self.setting_window.setWindowFlags(
        #     Qt.Window |  # 独立窗口
        #     Qt.WindowStaysOnTopHint |  # 保持在最顶层
        #     Qt.WindowCloseButtonHint |  # 显示关闭按钮
        #     Qt.WindowMinimizeButtonHint |  # 显示最小化按钮
        #     Qt.WindowMaximizeButtonHint  # 显示最大化按钮
        # )
        
        self.setting_window.show_setting_ui()

        # 连接设置子窗口的关闭信号
        self.setting_window.closed.connect(self.setting_window_closed)

    def setting_window_closed(self):
        """处理设置子窗口关闭事件"""
        if hasattr(self, 'setting_window') and self.setting_window:
            print("[setting_window_closed]-->看图子界面,接受设置子窗口关闭事件")
            # 清理资源
            self.setting_window.deleteLater()
            self.setting_window = None


    @log_error_decorator(tips="关闭关闭对话框")
    def close_helpinfo(self, index):
        """关闭对话框事件"""
        if hasattr(self, 'help_dialog'):
            del self.help_dialog
        
    @log_error_decorator(tips="处理【Ctrl+f】键按下事件,打开主界面图片模糊搜索工具")
    def on_ctrl_f_pressed(self):
        """处理【Ctrl+f】键按下事件
        函数功能说明: 打开主界面图片模糊搜索工具
        """
        # 导入图片搜索工具类(ctrl+f)
        from src.view.sub_search_view import SearchOverlay                          
        
        # 构建图片名称列表，保持多维列表的结构, 保持图片名称的完整路径
        image_names = [[os.path.basename(path) for path in folder_paths] for folder_paths in self.paths_list]
        # 创建搜索窗口并显示；设置链接信号；打印输出日志文件
        self.search_window = SearchOverlay(self, image_names)
        self.search_window.show_search_overlay()
        self.search_window.item_selected_from_search.connect(self.on_item_selected_from_search)
        self.logger.info("on_ctrl_f_pressed()-->打开图片模糊搜索工具成功")

    @log_error_decorator(tips="处理图片模糊搜索工具选中事件")
    def on_item_selected_from_search(self, position):
        """处理图片模糊搜索工具选中事件
        函数功能说明: 处理搜索窗口的选中项信号,返回行(row)和列(col)后再主界面中定位选中项
        """
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


    def check_file_type(self, list_file_path):
        """检查文件类型
        函数功能说明: 根据传入的文件路径列表，统计图片、视频、其它文件是否出现
        返回: 置为1表示出现 置为0表示未出现
        flag_video: 视频文件出现标志位   
        flag_image: 图片文件出现标志位
        flag_other: 其它格式文件出现标志位
        """
        try:
            # 解析传入的文件路径列表中的扩展名
            if not (file_extensions := {os.path.splitext(path)[1].lower() for path in list_file_path}):
                raise Exception(f"无法解析传入的文件路径列表扩展名")
            # 检查文件类型的合法性, 使用集合操作和in操作符，比endswith()更高效
            flag_video = 1 if any(ext in self.VIDEO_FORMATS for ext in file_extensions) else 0
            flag_image = 1 if any(ext in self.IMAGE_FORMATS for ext in file_extensions) else 0
            flag_other = 1 if any(ext not in self.VIDEO_FORMATS and ext not in self.IMAGE_FORMATS for ext in file_extensions) else 0
            return flag_video, flag_image, flag_other
        except Exception as e:
            print(f"[check_file_type]-->error--【Space/B】键按下后, 检查文件类型功能函数 | 报错：{e}")
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
            print(f"[open_subwindow_dynamically]-->error--【Space/B】键按下后, 动态打开对应子窗口 | 报错：{e}")
            self.logger.error(f"【open_subwindow_dynamically】-->【Space/B】键按下后, 动态打开对应子窗口 | 报错：{e}")

    @log_error_decorator(tips="处理【Space/B】键防抖检测任务")
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
            print(f"[on_b_pressed]-->执行函数任务, 主界面处理【B】键按下事件")
            self.logger.info(f"[on_b_pressed]-->执行函数任务, 主界面处理【B】键按下事件")
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
            print(f"[on_b_pressed]-->error--主界面处理【B】键按下事件发生错误: {e}")
            self.logger.error(f"【on_b_pressed】-->主界面处理【B】键按下事件发生错误: {e}")
            

    def on_space_pressed(self):
        """处理【Space】键按下事件
        函数功能说明: 用于查看下一组图片/视频，在看图子界面功能保持一致
        """
        try:
            print(f"[on_space_pressed]-->执行函数任务, 主界面处理【Space】键按下事件")
            self.logger.info(f"[on_space_pressed]-->执行函数任务, 主界面处理【Space】键按下事件")
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
            print(f"[on_space_pressed]-->error--主界面处理【Space】键时发生错误: {e}")
            self.logger.error(f"【on_space_pressed】-->主界面处理【Space】键时发生错误: {e}")


    @log_error_decorator(tips="创建看图子窗口的统一方法")
    def create_compare_window(self, selected_file_paths, image_indexs):
        """创建看图子窗口的统一方法"""
        # 导入看图子界面类
        from src.view.sub_compare_image_view import SubMainWindow  

        # 初始化看图子界面类，设置窗口图标以及相关槽函数
        # self.pause_preloading() # modify by diamond_cz 20250217 禁用暂停预加载功能，看图时默认后台加载图标
        # 打印主界面底部栏标签提示信息并立即重绘
        self.statusbar_label1.setText(f"📢:正在打开看图子界面..."), self.statusbar_label1.repaint()
        # 初始化看图子界面
        if not self.compare_window:
            self.logger.info("[create_compare_window]-->开始初始化看图子界面并出入图片路径和索引列表")
            self.compare_window = SubMainWindow(selected_file_paths, image_indexs, self)
        else:
            self.logger.info("[create_compare_window]-->看图子界面已存在，直接传入图片路径和索引列表")
            self.compare_window.load_settings()
            self.compare_window.set_images(selected_file_paths, image_indexs)
            # self.compare_window.show()
            self.compare_window.toggle_screen_display()

        self.compare_window.closed.connect(self.on_compare_window_closed)
        self.statusbar_label1.setText(f"📢:看图子界面打开成功")
        self.statusbar_label1.repaint()  # 刷新标签文本
        # self.hide()  # modify by diamond_cz 20250217 不隐藏主界面


    @log_error_decorator(tips="处理看图子窗口关闭事件")
    def on_compare_window_closed(self):
        """处理看图子窗口关闭事件"""
        if self.compare_window:
            # 打印输出日志信息
            self.logger.info("[on_compare_window_closed]-->主程序【hiviewer.exe】接受看图子窗口关闭事件")
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
        if self.player_key:
            # 使用opencv方式打开视频
            from src.view.sub_compare_video_view import VideoWall                
            self.video_player = VideoWall(selected_file_paths)
            self.video_player.setWindowTitle("多视频播放程序")
            self.video_player.setWindowFlags(Qt.Window) 
            # 设置窗口图标
            icon_path = (self.icon_path / "video_icon.ico").as_posix()
            self.video_player.setWindowIcon(QIcon(icon_path))
            self.video_player.closed.connect(self.on_video_player_closed)
            self.video_player.show()
            self.hide()
            return
        else:
            # 使用vlc播放器打开视频文件
            from src.view.sub_compare_vlc_video_view import VideoWall
            self.video_player = VideoWall()
            self.video_player.closed.connect(self.on_video_player_closed)
            if not self.video_player.vlc_flag:
                self.video_player.add_video_list(selected_file_paths)
                self.video_player.showFullScreen()
                self.hide()
            else:
                self.on_video_player_closed()
            return


    @log_error_decorator(tips="打开单文件重命名功能子界面")
    def open_sigle_file_rename_tool(self, current_folder, selected_items):
        """创建单文件重命名方法"""
        # 导入自定义重命名对话框类
        from src.components.custom_qdialog_rename import SingleFileRenameDialog     
         
        # 初始化单文件重命名类，设置接受事件 
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
        # 导入批量重命名子界面类
        from src.view.sub_rename_view import FileOrganizer
        
        # 初始化批量重命名类，设置窗口图标以及相关槽函数
        self.rename_tool = FileOrganizer(dir_list=current_folder)
        self.rename_tool.setWindowTitle("批量重命名")
        icon_path = (self.icon_path / "rename_ico_96x96.ico").as_posix()
        self.rename_tool.setWindowIcon(QIcon(icon_path))
        self.rename_tool.imagesRenamed.connect(self.on_rename_tool_closed) 
        self.rename_tool.show()
        self.hide()

    @log_error_decorator(tips="打开图片调整功能子界面")
    def open_image_process_window(self, image_path):
        """创建图片处理子窗口的统一方法"""
        # 导入图片调整子界面类
        from src.view.sub_image_process_view import SubCompare  
        
        # 初始化相关图片调整子界面类，设置图标以及相关槽函数
        self.image_process_window = SubCompare(image_path)
        self.image_process_window.setWindowTitle("图片调整") 
        self.image_process_window.setWindowFlags(Qt.Window)
        icon_path = (self.icon_path / "ps_ico_96x96.ico").as_posix()
        self.image_process_window.setWindowIcon(QIcon(icon_path))
        self.image_process_window.closed.connect(self.on_image_process_window_closed) 
        self.image_process_window.show()
        self.hide()

    @log_error_decorator(tips="批量执行命令界面")
    def open_bat_tool(self):
        """创建批量执行命令的统一方法"""
        # 导入批量执行命令的类
        from src.view.sub_bat_view import LogVerboseMaskApp                         
        
        # 初始化类并设置窗口图标以及相关槽函数
        self.bat_tool = LogVerboseMaskApp()
        self.bat_tool.setWindowTitle("批量执行命令")
        icon_path = (self.icon_path / "cmd_ico_96x96.ico").as_posix()
        self.bat_tool.setWindowIcon(QIcon(icon_path))
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
            gc.collect()
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

    
    def closeEvent(self, event):
        """重写关闭事件以保存设置和清理资源"""
        print("[closeEvent]-->触发【hiviewer.exe】主程序关闭事件")
        self.logger.info("[closeEvent]-->触发【hiviewer.exe】主程序关闭事件")
        try:
            # 保存设置
            self.save_settings()
            # 清理资源
            self.cleanup()
            # 等待一小段时间确保清理完成
            QTimer.singleShot(100, lambda: self._final_cleanup())
            self.logger.info("[closeEvent]-->接受【hiviewer.exe】关闭事件, 成功保存配置并清理内存！")
        except Exception as e:
            print(f"[closeEvent]-->error--关闭事件处理失败: {e}")
            self.logger.error(f"[closeEvent]-->关闭事件处理失败: {e}")
        finally:
            event.accept()
    
    @log_error_decorator(tips="最终清理，确保所有资源都被释放")
    def _final_cleanup(self):
        """最终清理，确保所有资源都被释放"""
        # 再次强制垃圾回收
        gc.collect()
        # 清理任何剩余的定时器
        if hasattr(self, 'splash_progress_timer'):
            self.splash_progress_timer.stop()
        # 记录最终清理完成
        print("[_final_cleanup]-->最终清理完成")
        self.logger.info("[_final_cleanup]-->最终清理完成")

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
    # 设置主程序app，启动主界面
    app = QApplication(sys.argv)
    window = HiviewerMainwindow()
    sys.exit(app.exec_())