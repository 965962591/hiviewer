import sys
import threading
import numpy as np
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QCursor, QKeySequence, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QSpinBox,
    QScrollArea,
    QSizePolicy,
    QDoubleSpinBox,
    QGridLayout,
    QShortcut,
    QMessageBox,
    QDialog,
)
import os
import time
import webbrowser
import shutil
import pathlib
import platform

"""设置本项目的入口路径, 以及图标根目录"""
BASEPATH = pathlib.Path(__file__).parent.parent.parent
ICONPATH = BASEPATH / "resource" / "icons" 


# 全局VLC参数缓存
_global_vlc_args = None
_vlc_args_lock = threading.Lock()

# VLC检测和导入
vlc = None

def check_vlc_installation():
    """检测VLC是否已安装"""
    global vlc
    
    # 方法1: 尝试导入python-vlc模块
    try:
        import vlc as vlc_module
        vlc = vlc_module
        # 尝试创建一个简单的VLC实例来验证可用性
        test_instance = vlc_module.Instance('--quiet')
        test_instance.release()
        print("✅ VLC Python模块检测成功")
        return True
    except ImportError:
        print("❌ VLC Python模块未安装")
    except Exception as e:
        print(f"❌ VLC模块导入失败: {str(e)}")
    
    # 方法2: 检查系统中是否安装了VLC可执行文件
    vlc_executables = []
    if platform.system() == "Windows":
        vlc_executables = ["vlc.exe"]
        # 检查常见的Windows VLC安装路径
        common_paths = [
            r"C:\Program Files\VideoLAN\VLC",
            r"C:\Program Files (x86)\VideoLAN\VLC",
            os.path.expanduser(r"~\AppData\Local\Programs\VideoLAN\VLC"),
        ]
        for path in common_paths:
            vlc_path = os.path.join(path, "vlc.exe")
            if os.path.exists(vlc_path):
                print(f"✅ 找到VLC安装: {vlc_path}")
                print("❌ 但VLC Python模块未安装，需要安装python-vlc")
                return False
    elif platform.system() == "Darwin":  # macOS
        vlc_executables = ["vlc"]
        # 检查macOS VLC安装路径
        if os.path.exists("/Applications/VLC.app"):
            print("✅ 找到VLC应用: /Applications/VLC.app")
            print("❌ 但VLC Python模块未安装，需要安装python-vlc")
            return False
    else:  # Linux
        vlc_executables = ["vlc"]
    
    # 检查系统PATH中的VLC
    for executable in vlc_executables:
        if shutil.which(executable):
            print(f"✅ 在系统PATH中找到VLC: {executable}")
            print("❌ 但VLC Python模块未安装，需要安装python-vlc")
            return False
    
    print("❌ 系统中未找到VLC安装")
    return False


def show_vlc_startup_dialog():
    """程序启动时的VLC检测和下载对话框"""
    vlc_dialog = VlcTipsDialog()    
    icon_path = (ICONPATH / "viewer_3.ico").as_posix()
    vlc_dialog.setWindowIcon(QIcon(icon_path))
    if vlc_dialog.exec_() == QDialog.Accepted:
        # 打开下载链接并复制密码到剪切板
        download_url = "https://wwco.lanzn.com/iGB7e36woydi"
        password = "1111"
        
        try:
            # 将密码复制到剪切板
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(password)
            
            # 打开浏览器
            webbrowser.open(download_url)
            
            print(f"✅ VLC下载链接已在浏览器中打开: {download_url}")
            print(f"✅ 提取码已复制到剪切板: {password}")
            
            show_message_box(f"✅ VLC下载链接已在浏览器中打开, 提取码{password}已复制到剪贴板", "提示", 5000)
            
        except Exception as e:
            print(f"❌ 打开VLC下载链接失败: {str(e)}")
            show_message_box(f"❌ 打开VLC下载链接失败: {str(e)}", "提示", 5000)
            
    else:
        print(f"[show_vlc_startup_dialog]-->取消VLC下载安转对话框")


def show_message_box(text, title="提示", timeout=None):
    """显示消息框，宽度自适应文本内容
    
    Args:
        text: 显示的文本内容
        title: 窗口标题，默认为"提示" 
        timeout: 自动关闭的超时时间(毫秒)，默认为None不自动关闭
    """
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    
    # 设置消息框主图标,获取项目根目录并拼接图标路径
    icon_path = (ICONPATH / "viewer_3.ico").as_posix()
    msg_box.setWindowIcon(QIcon(icon_path))

    # 设置定时器自动关闭
    if timeout is not None:
        QTimer.singleShot(timeout, msg_box.close)

    # 使用 exec_ 显示模态对话框
    msg_box.exec_() 


def get_global_vlc_args(rotate_angle=0):
    """获取全局VLC参数，默认使用硬件加速(auto)，支持旋转功能"""
    global _global_vlc_args, _vlc_args_lock
    
    # 如果旋转角度为0，使用缓存的参数
    if _global_vlc_args is not None and rotate_angle == 0:
        return _global_vlc_args
    
    with _vlc_args_lock:
        # 如果旋转角度为0，检查缓存
        if _global_vlc_args is not None and rotate_angle == 0:
            return _global_vlc_args
            
        # 基础参数
        args = [
            '--intf', 'dummy',  # 无界面模式
            '--no-audio',  # 禁用音频
            '--quiet',  # 静默模式
            '--no-video-title-show',  # 不显示视频标题
            '--no-video-deco',  # 禁用视频装饰
            '--input-repeat=65535',  # 设置循环播放
            '--no-xlib',  # 禁用X11库（Linux）
            '--no-qt-fs-controller',  # 禁用Qt全屏控制器
            '--no-embedded-video',  # 禁用嵌入式视频
        ]
        
        # 添加旋转滤镜参数（如果角度不为0）
        if rotate_angle != 0:
            # 使用VLC的滤镜链语法，将旋转和缩放组合在一起
            if rotate_angle == 90:
                args.extend([
                    '--video-filter=transform,scale',  # 启用变换和缩放滤镜
                    '--transform-type=90',  # 90度旋转
                    '--scale=1.0',  # 设置缩放比例
                ])
                print(f"启用视频旋转: {rotate_angle}度 (使用transform+scale滤镜)")
            elif rotate_angle == 180:
                args.extend([
                    '--video-filter=transform,scale',  # 启用变换和缩放滤镜
                    '--transform-type=180',  # 180度旋转
                    '--scale=1.0',  # 设置缩放比例
                ])
                print(f"启用视频旋转: {rotate_angle}度 (使用transform+scale滤镜)")
            elif rotate_angle == 270:
                args.extend([
                    '--video-filter=transform,scale',  # 启用变换和缩放滤镜
                    '--transform-type=270',  # 270度旋转
                    '--scale=1.0',  # 设置缩放比例
                ])
                print(f"启用视频旋转: {rotate_angle}度 (使用transform+scale滤镜)")
            else:
                # 对于其他角度，使用rotate滤镜
                args.extend([
                    '--video-filter=rotate,scale',  # 启用旋转和缩放滤镜
                    f'--rotate-angle={rotate_angle}',  # 设置旋转角度
                    '--scale=1.0',  # 设置缩放比例
                ])
                print(f"启用视频旋转: {rotate_angle}度 (使用rotate+scale滤镜)")
        
        # 只有在不旋转时才添加缩放滤镜（旋转时已经在上面添加了）
        if rotate_angle == 0:
            args.extend([
                '--video-filter=scale',  # 启用缩放滤镜
                '--scale=1.0',  # 设置缩放比例
            ])
        
        # 默认使用硬件加速(auto)
        args.extend([
            '--avcodec-hw=auto',  # 自动选择硬件加速
        ])
        print("启用硬件加速 (auto)")
        
        # 添加通用硬件加速优化参数
        args.extend([
            '--avcodec-skiploopfilter=4',  # 跳过循环滤波器以提高性能
            '--avcodec-skip-frame=0',  # 不跳过帧
            '--avcodec-skip-idct=0',  # 不跳过IDCT
            '--avcodec-fast',  # 快速解码
            '--avcodec-threads=0',  # 自动检测线程数
            '--avcodec-dr',  # 直接渲染
        ])
        
        # 添加性能优化参数
        args.extend([
            '--network-caching=1000',  # 网络缓存1秒
            '--live-caching=1000',  # 直播缓存1秒
            '--file-caching=1000',  # 文件缓存1秒
            '--sout-mux-caching=1000',  # 输出复用缓存1秒
            '--clock-jitter=0',  # 时钟抖动
            '--clock-synchro=0',  # 时钟同步
            '--drop-late-frames',  # 丢弃延迟帧
            '--skip-frames',  # 跳过帧以提高性能
        ])
        
        # 只有在旋转角度为0时才缓存参数
        if rotate_angle == 0:
            _global_vlc_args = args
            print("全局VLC参数已缓存，硬件加速: auto")
        else:
            print(f"VLC参数已生成，旋转角度: {rotate_angle}度")
        
        return args


class VlcTipsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VLC未安装提示")
        self.setFixedSize(400, 150)
        # self.setStyleSheet("""
        #     QDialog { background: #23242a; color: #fff; }
        #     QLabel { font-size: 20px; }
        #     QLineEdit { font-size: 20px; background: #23242a; color: #00bfff; border: 1px solid #444; border-radius: 4px; padding: 2px 2px; }
        #     QPushButton { background: #23242a; color: #00bfff; border: 1px solid #00bfff; border-radius: 4px; min-width: 80px; min-height: 30px; }
        #     QPushButton:hover { background: #00bfff; color: #23242a; }
        # """)
        # 整体垂直布局layout
        layout = QVBoxLayout(self)

        # 操作区layout,设置标签栏和编辑栏
        opera_layout = QVBoxLayout()
        self.label = QLabel("检测到当前程序未安装VLC播放器内核, \n是否立即下载安转?")
        # self.label.setStyleSheet("color: #23242a; font-weight: bold;")
        opera_layout.addWidget(self.label)
        layout.addLayout(opera_layout)

        # 按钮区layout,设置确定和取消按钮
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # 信号链接
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)



class VideoFrame(QWidget):
    """自定义视频显示组件，支持直接绘制图像和动态尺寸调整"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        self.aspect_ratio = None  # 宽高比
        self.rotation_angle = 0   # 当前旋转角度
        
        # 设置背景色
        self.setStyleSheet("background-color: black;")
        
        # 设置尺寸策略，允许动态调整
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        print("VideoFrame 初始化完成")
    
    def setPixmap(self, pixmap):
        """设置要显示的图像"""
        self.current_pixmap = pixmap
        if pixmap and not pixmap.isNull():
            # 更新宽高比
            self.aspect_ratio = pixmap.width() / pixmap.height()
        self.update()  # 触发重绘
    
    def set_rotation_angle(self, angle):
        """设置旋转角度"""
        self.rotation_angle = angle
        self.update()
    
    def paintEvent(self, event):
        """重写绘制事件"""
        from PyQt5.QtGui import QPainter
        from PyQt5.QtCore import QRect
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 绘制背景
        painter.fillRect(self.rect(), Qt.black)
        
        # 如果有图像，则绘制图像
        if self.current_pixmap and not self.current_pixmap.isNull():
            # 计算适合的显示尺寸（保持宽高比）
            widget_rect = self.rect()
            pixmap_rect = self.current_pixmap.rect()
            
            # 计算缩放比例，确保图像完全显示在窗口内
            scale_x = widget_rect.width() / pixmap_rect.width()
            scale_y = widget_rect.height() / pixmap_rect.height()
            scale = min(scale_x, scale_y)
            
            # 计算显示尺寸
            display_width = int(pixmap_rect.width() * scale)
            display_height = int(pixmap_rect.height() * scale)
            
            # 计算居中位置
            x = (widget_rect.width() - display_width) // 2
            y = (widget_rect.height() - display_height) // 2
            
            # 创建目标矩形
            target_rect = QRect(x, y, display_width, display_height)
            
            # 绘制图像
            painter.drawPixmap(target_rect, self.current_pixmap)
        
        painter.end()
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        # 当窗口大小改变时，重新绘制
        self.update()
        
        # 通知VLC窗口大小已改变，让VLC重新调整视频缩放
        if hasattr(self, 'parent') and hasattr(self.parent(), 'frame_reader'):
            try:
                if hasattr(self.parent().frame_reader, 'decoder'):
                    # 延迟设置缩放，确保窗口大小调整完成
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(50, self._notify_vlc_resize)
            except Exception as e:
                print(f"通知VLC窗口大小改变失败: {str(e)}")
    
    def _notify_vlc_resize(self):
        """通知VLC窗口大小已改变"""
        try:
            if hasattr(self, 'parent') and hasattr(self.parent(), 'frame_reader'):
                if hasattr(self.parent().frame_reader, 'decoder'):
                    decoder = self.parent().frame_reader.decoder
                    if hasattr(decoder, '_set_video_scale'):
                        decoder._set_video_scale()
                        print("✅ 通知VLC重新调整视频缩放")
        except Exception as e:
            print(f"通知VLC重新调整视频缩放失败: {str(e)}")
    


class VLCSlider(QSlider):
    """VLC原生进度条，支持点击跳转和拖拽"""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.vlc_player = None
        self.duration_ms = 0
        self.is_dragging = False
        self.last_seek_time = 0
        self.seek_threshold = 100  # 最小跳转间隔(毫秒)
        
        # 启用焦点支持，以便键盘事件能够正常工作
        self.setFocusPolicy(Qt.StrongFocus)
    
    def set_vlc_player(self, vlc_player):
        """设置VLC播放器引用"""
        self.vlc_player = vlc_player
    
    def set_duration(self, duration_ms):
        """设置视频总时长"""
        self.duration_ms = duration_ms
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 支持点击跳转"""
        if event.button() == Qt.LeftButton and self.vlc_player:
            # 计算点击位置对应的进度值
            click_pos = event.pos().x()
            slider_width = self.width()
            slider_min = self.minimum()
            slider_max = self.maximum()
            
            if slider_width > 0:
                # 计算点击位置对应的值
                value = slider_min + (slider_max - slider_min) * click_pos / slider_width
                value = max(slider_min, min(slider_max, int(value)))
                
                # 计算对应的时间
                time_ms = int((value / 100.0) * self.duration_ms)
                
                # 检查是否需要跳转（避免频繁跳转）
                if abs(time_ms - self.last_seek_time) >= self.seek_threshold:
                    try:
                        # 使用VLC原生跳转
                        self.vlc_player.set_time(time_ms)
                        self.last_seek_time = time_ms
                        print(f"VLC原生跳转到: {time_ms}ms ({value}%)")
                        
                        # 更新滑块位置
                        self.setValue(value)
                        
                        # 发送信号通知父组件
                        self.sliderMoved.emit(value)
                        
                    except Exception as e:
                        print(f"VLC跳转失败: {str(e)}")
                
                # 标记开始拖拽
                self.is_dragging = True
                self.sliderPressed.emit()
        
        # 调用父类的鼠标按下事件
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 支持拖拽"""
        if self.is_dragging and self.vlc_player and event.buttons() & Qt.LeftButton:
            # 计算拖拽位置对应的进度值
            click_pos = event.pos().x()
            slider_width = self.width()
            slider_min = self.minimum()
            slider_max = self.maximum()
            
            if slider_width > 0:
                value = slider_min + (slider_max - slider_min) * click_pos / slider_width
                value = max(slider_min, min(slider_max, int(value)))
                
                # 计算对应的时间
                time_ms = int((value / 100.0) * self.duration_ms)
                
                # 检查是否需要跳转（拖拽时降低跳转频率）
                if abs(time_ms - self.last_seek_time) >= self.seek_threshold * 2:
                    try:
                        # 使用VLC原生跳转
                        self.vlc_player.set_time(time_ms)
                        self.last_seek_time = time_ms
                        
                        # 更新滑块位置
                        self.setValue(value)
                        
                        # 发送信号通知父组件
                        self.sliderMoved.emit(value)
                        
                    except Exception as e:
                        print(f"VLC拖拽跳转失败: {str(e)}")
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.sliderReleased.emit()
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """滚轮事件 - 支持精细调节"""
        if self.vlc_player:
            # 获取滚轮滚动量
            delta = event.angleDelta().y()
            
            # 计算当前值
            current_value = self.value()
            current_time = int((current_value / 100.0) * self.duration_ms)
            
            # 根据滚动方向调整时间（每次调整100ms）
            if delta > 0:
                new_time = min(self.duration_ms, current_time + 100)
            else:
                new_time = max(0, current_time - 100)
            
            # 计算新的进度值
            new_value = int((new_time / self.duration_ms) * 100)
            
            try:
                # 使用VLC原生跳转
                self.vlc_player.set_time(new_time)
                self.last_seek_time = new_time
                
                # 更新滑块位置
                self.setValue(new_value)
                
                # 发送信号通知父组件
                self.sliderMoved.emit(new_value)
                
                print(f"VLC滚轮跳转到: {new_time}ms ({new_value}%)")
                
            except Exception as e:
                print(f"VLC滚轮跳转失败: {str(e)}")
        
        event.accept()
    
    def keyPressEvent(self, event):
        """键盘事件 - 支持方向键控制"""
        if self.vlc_player:
            current_value = self.value()
            current_time = int((current_value / 100.0) * self.duration_ms)
            
            # 根据按键调整时间
            if event.key() == Qt.Key_Left:
                # 左箭头：后退5秒
                new_time = max(0, current_time - 5000)
            elif event.key() == Qt.Key_Right:
                # 右箭头：前进5秒
                new_time = min(self.duration_ms, current_time + 5000)
            elif event.key() == Qt.Key_Up:
                # 上箭头：前进10秒
                new_time = min(self.duration_ms, current_time + 10000)
            elif event.key() == Qt.Key_Down:
                # 下箭头：后退10秒
                new_time = max(0, current_time - 10000)
            else:
                super().keyPressEvent(event)
                return
            
            # 计算新的进度值
            new_value = int((new_time / self.duration_ms) * 100)
            
            try:
                # 使用VLC原生跳转
                self.vlc_player.set_time(new_time)
                self.last_seek_time = new_time
                
                # 更新滑块位置
                self.setValue(new_value)
                
                # 发送信号通知父组件
                self.sliderMoved.emit(new_value)
                
                print(f"VLC键盘跳转到: {new_time}ms ({new_value}%)")
                
            except Exception as e:
                print(f"VLC键盘跳转失败: {str(e)}")
        
        event.accept()


class VLCDecoder:
    """VLC视频解码器类（使用原生VLC方法）"""
    
    def __init__(self, video_path, rotate_angle=0):
        self.video_path = video_path
        self.rotate_angle = rotate_angle  # 添加旋转角度参数
        self.instance = None
        self.media_player = None
        self.media = None
        self.is_initialized = False
        
        # 视频信息
        self.fps = 30.0  # 默认帧率
        self.total_frames = 0
        self.duration_ms = 0
        self.width = 1920  # 默认宽度
        self.height = 1080  # 默认高度
        
        # 播放状态
        self.is_playing = False
        self.current_time_ms = 0
        self._output_window_set = False  # 输出窗口设置标志
        
        # 硬件加速信息
        self.hardware_acceleration_enabled = True  # 默认启用硬件加速
        
        self._initialize_vlc()
    
    def _is_vlc_player_valid(self):
        """检查VLC播放器是否有效"""
        return (hasattr(self, 'media_player') and 
                self.media_player is not None and 
                hasattr(self.media_player, 'get_state'))
    
    def _safe_vlc_operation(self, operation, operation_name="VLC操作", default_return=None):
        """安全执行VLC操作，统一错误处理"""
        if not self._is_vlc_player_valid():
            print(f"{operation_name}失败: VLC播放器无效")
            return default_return
        
        try:
            return operation()
        except Exception as e:
            print(f"{operation_name}失败: {str(e)}")
            return default_return
    
    def _initialize_vlc(self):
        """初始化VLC实例"""
        # VLC检测已在程序启动时完成，这里直接初始化
        global vlc
        try:
            # 创建VLC实例，使用全局缓存的参数
            # 为每个实例添加唯一标识符，避免冲突
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # 使用全局缓存的VLC参数，传入旋转角度
            args = get_global_vlc_args(self.rotate_angle)
            
            # 硬件加速已默认启用
            self.hardware_acceleration_enabled = True
            
            self.instance = vlc.Instance(args)
            self.media_player = self.instance.media_player_new()
            
            # 创建媒体对象
            self.media = self.instance.media_new(self.video_path)
            self.media_player.set_media(self.media)
            
            print(f"VLC实例创建成功，ID: {unique_id}")
            print(f"VLC参数: {args}")
            if self.rotate_angle != 0:
                print(f"✅ 视频旋转已启用: {self.rotate_angle}度")
                print(f"🔧 旋转滤镜参数已设置")
            # 解析媒体以获取信息
            self.media.parse()
            
            # 等待解析完成
            import time as time_module
            timeout = 5  # 5秒超时
            start_time = time_module.time()
            while vlc and self.media.get_parsed_status() != vlc.MediaParsedStatus.done:
                if time_module.time() - start_time > timeout:
                    print("媒体解析超时，使用默认值继续...")
                    break
                time_module.sleep(0.1)
            
            # 获取视频信息
            self._get_video_info()
            
            self.is_initialized = True
            print(f"VLC解码器初始化成功: {self.video_path}")
            print("✅ 硬件加速已启用 (auto)")
            
        except Exception as e:
            print(f"VLC解码器初始化失败: {str(e)}")
            self.is_initialized = False
            raise Exception(f"无法初始化VLC解码器: {str(e)}")
    
    
    def _get_video_info(self):
        """获取视频信息"""
        try:
            # 获取视频时长（毫秒）
            self.duration_ms = self.media.get_duration()
            if self.duration_ms <= 0:
                self.duration_ms = 5000  # 默认5秒
            
            # 尝试获取视频尺寸
            try:
                if hasattr(self.media_player, 'video_get_size'):
                    width, height = self.media_player.video_get_size()
                    if width > 0 and height > 0:
                        self.width = width
                        self.height = height
            except Exception as e:
                print(f"获取视频尺寸失败: {str(e)}")
            
            # 获取视频帧率
            self._get_video_fps()
            
            # 计算总帧数
            if self.duration_ms > 0 and self.fps > 0:
                self.total_frames = int((self.duration_ms / 1000.0) * self.fps)
            else:
                self.total_frames = int(self.duration_ms / 33.33)  # 基于30fps计算
            
        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
    
    def _get_video_fps(self):
        """获取视频帧率 - 仅使用VLC方法"""
        try:
            # 方法1：尝试从VLC媒体播放器获取帧率
            if hasattr(self.media_player, 'get_fps'):
                try:
                    fps_value = self.media_player.get_fps()
                    if fps_value and fps_value > 0:
                        self.fps = fps_value
                        print(f"从VLC播放器获取帧率: {self.fps}")
                        return
                except Exception as e:
                    print(f"从VLC播放器获取帧率失败: {str(e)}")
            
            # 方法2：尝试从VLC媒体信息中获取帧率
            if hasattr(self.media, 'get_meta'):
                try:
                    # 尝试获取帧率元数据
                    fps_str = self.media.get_meta(vlc.Meta.FrameRate)
                    if fps_str:
                        fps_value = float(fps_str)
                        if fps_value > 0:
                            self.fps = fps_value
                            print(f"从VLC媒体元数据获取帧率: {self.fps}")
                            return
                except Exception as e:
                    print(f"从VLC媒体元数据获取帧率失败: {str(e)}")
            
            # 方法3：尝试从媒体轨道信息获取帧率
            try:
                # 获取媒体轨道
                tracks = self.media.get_tracks()
                for track in tracks:
                    if hasattr(track, 'i_codec'):
                        # 检查是否是视频轨道（通过轨道类型判断）
                        if hasattr(track, 'i_type') and track.i_type == 0:  # 0通常表示视频轨道
                            if hasattr(track, 'f_fps') and track.f_fps > 0:
                                self.fps = track.f_fps
                                print(f"从VLC轨道信息获取帧率: {self.fps}")
                                return
                            elif hasattr(track, 'i_rate') and track.i_rate > 0:
                                # 某些情况下，帧率可能存储在i_rate中
                                if 10 <= track.i_rate <= 120:  # 合理的帧率范围
                                    self.fps = track.i_rate
                                    print(f"从VLC轨道速率获取帧率: {self.fps}")
                                    return
            except Exception as e:
                print(f"从VLC轨道信息获取帧率失败: {str(e)}")
            
            # 方法4：尝试从媒体持续时间计算帧率
            try:
                duration_ms = self.media.get_duration()
                if duration_ms > 0 and hasattr(self, 'total_frames') and self.total_frames > 0:
                    # 从总帧数和持续时间计算帧率
                    duration_seconds = duration_ms / 1000.0
                    calculated_fps = self.total_frames / duration_seconds
                    if calculated_fps > 0:
                        self.fps = calculated_fps
                        print(f"从持续时间计算帧率: {self.fps}")
                        return
            except Exception as e:
                print(f"从持续时间计算帧率失败: {str(e)}")
            
            # 如果所有方法都失败，使用默认帧率
            self.fps = 30.0
            print(f"无法获取视频帧率，使用默认值: {self.fps}fps")
            
        except Exception as e:
            print(f"获取视频帧率失败: {str(e)}")
            self.fps = 30.0  # 使用默认帧率
    
    def get_frame_at_time(self, time_ms):
        """获取指定时间的帧（用于VLC直接播放模式）"""
        try:
            # 只有在已经设置输出窗口后才启动播放
            if not self.is_playing and hasattr(self, '_output_window_set') and self._output_window_set:
                self._safe_vlc_operation(
                    lambda: self.media_player.play(),
                    "VLC开始播放"
                )
                if self._safe_vlc_operation(lambda: self.media_player.get_state()) is not None:
                    self.is_playing = True
                    print(f"VLC开始播放")
            elif self.is_playing:
                # 如果已经在播放，检查播放状态
                state = self._safe_vlc_operation(
                    lambda: self.media_player.get_state(),
                    "获取VLC播放状态"
                )
                if vlc and state == vlc.State.Ended:
                    print("VLC播放结束（异常情况），等待FrameReader处理重播")
                    self.is_playing = False
                elif vlc and state == vlc.State.Stopped:
                    print("VLC播放器停止，等待FrameReader处理重播")
                    self.is_playing = False
            
            # 对于VLC直接播放模式，不频繁设置时间，让VLC自然播放
            # 只在需要跳转时才设置时间
            if hasattr(self, '_last_seek_time'):
                time_diff = abs(time_ms - self._last_seek_time)
                if time_diff > 1000:  # 只有时间差超过1秒才跳转
                    self._safe_vlc_operation(
                        lambda: self.media_player.set_time(int(time_ms)),
                        "VLC设置播放时间"
                    )
                    self._last_seek_time = time_ms
            else:
                self._last_seek_time = time_ms
            
            self.current_time_ms = time_ms
                
        except Exception as e:
            print(f"获取帧失败: {str(e)}")
            return None
    
    def force_refresh(self):
        """强制刷新VLC播放器"""
        if not self.is_playing:
            return
            
        def refresh_operation():
            # 获取当前播放位置
            current_time = self.media_player.get_time()
            
            # 稍微调整播放位置以触发刷新
            self.media_player.set_time(current_time + 1)
            self.media_player.set_time(current_time)
            
            print(f"VLC播放器强制刷新，时间: {current_time}ms")
            return current_time
        
        self._safe_vlc_operation(refresh_operation, "VLC播放器强制刷新")
    
    
    def get_frame_at_position(self, position):
        """根据位置百分比获取帧"""
        if self.duration_ms > 0:
            time_ms = int((position / 100.0) * self.duration_ms)
            return self.get_frame_at_time(time_ms)
        return None
    
    def set_output_window(self, window_handle):
        """设置VLC输出窗口"""
        try:
            if self.media_player and window_handle:
                # 设置VLC输出到指定的Qt窗口
                # 在Windows上使用set_hwnd，在Linux上使用set_xwindow
                import platform
                if platform.system() == "Windows":
                    # 在Windows上，需要将窗口句柄转换为整数
                    if hasattr(window_handle, 'int'):
                        hwnd = window_handle.int()
                    else:
                        hwnd = int(window_handle)
                    self.media_player.set_hwnd(hwnd)
                else:
                    self.media_player.set_xwindow(window_handle)
                    print(f"VLC输出窗口设置成功 (Linux): {window_handle}")
                
                # 设置输出窗口后，启用视频输出并开始播放
                self._output_window_set = True
                self._enable_video_and_play()
                
                # 设置视频缩放，确保视频能够自适应窗口大小
                self._set_video_scale()
                
                return True
        except Exception as e:
            print(f"设置VLC输出窗口失败: {str(e)}")
        return False
    
    def _enable_video_and_play(self):
        """启用视频输出并开始播放"""
        try:
            # 开始播放
            self.media_player.play()
            self.is_playing = True
            # 设置播放位置到开始
            self.media_player.set_time(0)
        except Exception as e:
            print(f"VLC视频输出启用并开始播放失败: {str(e)}")
    
    def _set_video_scale(self):
        """设置视频缩放，确保视频能够自适应窗口大小"""
        try:
            if not self.media_player:
                return
            
            # 设置视频缩放为自适应
            # 尝试不同的VLC缩放方法
            if hasattr(self.media_player, 'video_set_scale'):
                # 方法1：使用video_set_scale
                self.media_player.video_set_scale(0)  # 0表示自适应
                print("✅ 使用video_set_scale设置自适应缩放")
            elif hasattr(self.media_player, 'set_scale'):
                # 方法2：使用set_scale
                self.media_player.set_scale(0)  # 0表示自适应
                print("✅ 使用set_scale设置自适应缩放")
            elif hasattr(self.media_player, 'video_set_aspect_ratio'):
                # 方法3：使用video_set_aspect_ratio
                self.media_player.video_set_aspect_ratio("")  # 空字符串表示自适应
                print("✅ 使用video_set_aspect_ratio设置自适应缩放")
            else:
                print("⚠️ VLC播放器不支持缩放设置方法")
            
            # 检查VLC播放器状态
            self._check_vlc_status()
                
        except Exception as e:
            print(f"设置VLC视频缩放失败: {str(e)}")
    
    def _check_vlc_status(self):
        """检查VLC播放器状态"""
        try:
            if not self.media_player:
                return
            
            # 检查播放状态
            state = self.media_player.get_state()
            # 检查视频尺寸
            if hasattr(self.media_player, 'video_get_size'):
                try:
                    width, height = self.media_player.video_get_size()
                    print(f"VLC视频尺寸: {width}x{height}")
                except Exception as e:
                    print(f"获取VLC视频尺寸失败: {str(e)}")
            
            # 检查当前时间
            current_time = self.media_player.get_time()
            print(f"VLC当前播放时间: {current_time}ms")
            
        except Exception as e:
            print(f"检查VLC状态失败: {str(e)}")
    
    def set_video_scale(self, scale=0):
        """手动设置视频缩放比例"""
        try:
            if not self.media_player:
                return False
            
            # 设置视频缩放比例
            if hasattr(self.media_player, 'video_set_scale'):
                self.media_player.video_set_scale(scale)
                print(f"✅ 视频缩放比例设置为: {scale}")
                return True
            elif hasattr(self.media_player, 'set_scale'):
                self.media_player.set_scale(scale)
                print(f"✅ 视频缩放比例设置为: {scale}")
                return True
            else:
                print("⚠️ VLC播放器不支持缩放设置方法")
                return False
                
        except Exception as e:
            print(f"设置视频缩放比例失败: {str(e)}")
            return False
    
    def _restart_after_window_set(self):
        """设置输出窗口后重新启动播放"""
        try:
            # 停止当前播放
            if self.is_playing:
                self.media_player.stop()
                self.is_playing = False
            
            # 等待一小段时间让窗口设置生效
            import time
            time.sleep(0.1)
            
            # 重新开始播放
            self.media_player.play()
            self.is_playing = True
            
            # 设置播放位置到开始
            self.media_player.set_time(0)
            
            print("VLC窗口设置后重新启动播放成功")
        except Exception as e:
            print(f"VLC窗口设置后重新启动播放失败: {str(e)}")
    
    def release(self):
        """释放VLC资源 - 使用原生方法"""
        try:
            print(f"开始释放VLC资源: {self.video_path}")
            
            # 1. 停止播放
            if self.media_player and self.is_playing:
                try:
                    self.media_player.stop()
                    self.is_playing = False
                    print("✅ VLC播放器已停止")
                except Exception as e:
                    print(f"停止VLC播放器失败: {str(e)}")
            
            # 2. 释放媒体资源
            if self.media:
                try:
                    self.media.release()
                    print("✅ VLC Media资源已释放")
                except Exception as e:
                    print(f"释放VLC Media资源失败: {str(e)}")
            
            # 3. 释放播放器资源
            if self.media_player:
                try:
                    self.media_player.release()
                    print("✅ VLC MediaPlayer资源已释放")
                except Exception as e:
                    print(f"释放VLC MediaPlayer资源失败: {str(e)}")
            
            # 4. 释放VLC实例
            if self.instance:
                try:
                    self.instance.release()
                    print("✅ VLC Instance资源已释放")
                except Exception as e:
                    print(f"释放VLC Instance资源失败: {str(e)}")
            
            # 5. 清空所有引用
            self.media_player = None
            self.media = None
            self.instance = None
            
            print(f"✅ VLC资源释放完成: {self.video_path}")
            
        except Exception as e:
            print(f"释放VLC资源时出错: {str(e)}")
            # 即使出错也要清空引用
            self.media_player = None
            self.media = None
            self.instance = None
    
    def force_release(self):
        """强制释放VLC资源 - 异步方式，避免阻塞"""
        try:
            print(f"强制释放VLC资源: {self.video_path}")
            
            # 使用异步方式释放资源，避免阻塞主线程
            import threading
            
            def async_release():
                try:
                    # 1. 停止播放
                    if self.media_player and self.is_playing:
                        try:
                            self.media_player.stop()
                            self.is_playing = False
                        except:
                            pass
                    
                    # 2. 释放媒体资源
                    if self.media:
                        try:
                            self.media.release()
                        except:
                            pass
                    
                    # 3. 释放播放器资源
                    if self.media_player:
                        try:
                            self.media_player.release()
                        except:
                            pass
                    
                    # 4. 释放VLC实例
                    if self.instance:
                        try:
                            self.instance.release()
                        except:
                            pass
                    
                    print(f"✅ VLC资源异步释放完成: {self.video_path}")
                    
                except Exception as e:
                    print(f"异步释放VLC资源失败: {str(e)}")
            
            # 启动异步释放线程
            release_thread = threading.Thread(target=async_release)
            release_thread.daemon = True
            release_thread.start()
            
            # 立即清空引用，不等待异步释放完成
            self.media_player = None
            self.media = None
            self.instance = None
            
        except Exception as e:
            print(f"强制释放VLC资源时出错: {str(e)}")
            # 即使出错也要清空引用
            self.media_player = None
            self.media = None
            self.instance = None
    
    def get_rotated_video_size(self, angle):
        """计算旋转后的视频尺寸"""
        original_width = self.width
        original_height = self.height
        
        # 如果旋转角度是90度或270度，需要交换宽度和高度
        if angle in [90, 270]:
            return original_height, original_width
        else:
            return original_width, original_height
    
    def set_rotate_angle(self, angle):
        """设置视频旋转角度并重新初始化VLC实例"""
        try:
            if self.rotate_angle == angle:
                print(f"旋转角度已经是 {angle}度，无需更改")
                return True
            
            print(f"设置视频旋转角度: {self.rotate_angle}度 -> {angle}度")
            
            # 保存当前播放状态和输出窗口信息
            was_playing = self.is_playing
            current_time = 0
            saved_window_handle = None
            
            if self.media_player and self.is_playing:
                current_time = self._safe_vlc_operation(
                    lambda: self.media_player.get_time(),
                    "获取当前播放时间"
                ) or 0
            
            # 保存输出窗口句柄（如果已设置）
            if hasattr(self, '_output_window_set') and self._output_window_set:
                # 这里需要从外部获取窗口句柄，暂时标记需要重新设置
                print("保存输出窗口状态，准备重新设置")
            
            # 停止当前播放
            if self.media_player and self.is_playing:
                self._safe_vlc_operation(
                    lambda: self.media_player.stop(),
                    "停止VLC播放器"
                )
                self.is_playing = False
            
            # 释放当前VLC资源
            self.release()
            
            # 更新旋转角度
            self.rotate_angle = angle
            
            # 重新初始化VLC
            self._initialize_vlc()
            
            # 更新视频尺寸（旋转后可能需要调整）
            self._update_video_size_after_rotation(angle)
            
            # 标记需要重新设置输出窗口
            self._output_window_set = False
            
            print(f"✅ 视频旋转角度已更新为: {angle}度")
            print("⚠️ 需要重新设置VLC输出窗口")
            return True
            
        except Exception as e:
            print(f"设置旋转角度失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _update_video_size_after_rotation(self, angle):
        """旋转后更新视频尺寸"""
        try:
            # 计算旋转后的尺寸
            new_width, new_height = self.get_rotated_video_size(angle)
            
            # 更新内部尺寸记录
            self.width = new_width
            self.height = new_height
            
            print(f"旋转后视频尺寸更新: {new_width}x{new_height}")
            
        except Exception as e:
            print(f"更新旋转后视频尺寸失败: {str(e)}")

class FrameReader(QThread):
    frame_ready = pyqtSignal(int, object, int)  # 添加信号: 帧号, 帧数据, 时间戳

    def __init__(self, video_path, max_queue_size=30, rotate_angle=0):
        super().__init__()
        self.video_path = video_path
        self.max_queue_size = max_queue_size
        self.rotate_angle = rotate_angle  # 添加旋转角度参数
        self.running = True
        self.paused = False
        self.lock = threading.Lock()
        self.last_emit_time = time.time()  # 添加上次发射信号的时间
        self.playback_speed = 1.0  # 添加播放速度变量
        

        # 初始化解码器
        self.decoder = None      
        # 播放结束检测
        self.last_vlc_check_time = 0
        self.vlc_check_interval = 0.5  # 每0.5秒检查一次VLC状态
        
        self._initialize_decoder()

        # 获取视频信息
        self.current_frame_number = 0
        self.current_time_ms = 0
        self.fps = self.decoder.fps
        self.frame_time = 1000 / self.fps if self.fps > 0 else 33.33
    
    def _initialize_decoder(self):
        """初始化解码器，只使用VLC"""
        try:
            self.decoder = VLCDecoder(self.video_path, self.rotate_angle)
        except Exception as e:
            raise Exception(f"无法初始化VLC解码器: {str(e)}")


    def set_playback_speed(self, speed):
        """设置播放速度"""
        self.playback_speed = speed
        print(f"帧读取器播放速度设置为: {speed}")
        
        # 对于VLC直接播放模式，设置VLC的播放速度
        if hasattr(self.decoder, 'media_player') and self.decoder.media_player:
            try:
                # VLC的播放速度设置（1.0为正常速度）
                self.decoder.media_player.set_rate(speed)
                print(f"VLC播放速度设置为: {speed}")
            except Exception as e:
                print(f"设置VLC播放速度失败: {str(e)}")
    
    def set_rotate_angle(self, angle):
        """设置视频旋转角度"""
        try:
            if self.rotate_angle == angle:
                print(f"旋转角度已经是 {angle}度，无需更改")
                return True
            
            print(f"帧读取器设置旋转角度: {self.rotate_angle}度 -> {angle}度")
            
            # 更新旋转角度
            self.rotate_angle = angle
            
            # 通过解码器设置旋转角度
            if self.decoder:
                success = self.decoder.set_rotate_angle(angle)
                if success:
                    print(f"✅ 帧读取器旋转角度已更新为: {angle}度")
                    return True
                else:
                    print(f"❌ 帧读取器旋转角度更新失败")
                    return False
            else:
                print("❌ 解码器未初始化，无法设置旋转角度")
                return False
                
        except Exception as e:
            print(f"设置帧读取器旋转角度失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def run(self):
        while self.running:
            if self.paused:
                time.sleep(0.016)  # 暂停时降低CPU使用，约60fps检查频率
                continue

            # 对于VLC直接播放模式，不需要频繁调用get_frame_at_time
            # 只需要定期检查播放状态和更新时间信息
            current_time = time.time()
            elapsed = current_time - self.last_emit_time
            
            # 降低更新频率，避免干扰VLC播放
            target_update_interval = 0.1  # 每100ms更新一次状态信息
            
            if elapsed < target_update_interval:
                time.sleep(0.01)  # 短暂睡眠
                continue
            
            # 定期检查VLC播放状态（简化版本，主要用于监控）
            if current_time - self.last_vlc_check_time >= self.vlc_check_interval:
                self.last_vlc_check_time = current_time
                if self.decoder._is_vlc_player_valid():
                    vlc_state = self.decoder._safe_vlc_operation(
                        lambda: self.decoder.media_player.get_state(),
                        "检查VLC播放状态"
                    )
                    # 由于设置了循环播放，通常不会出现Ended状态
                    if vlc and vlc_state == vlc.State.Stopped:
                        print(f"检测到VLC播放器停止，尝试重新启动: {self.video_path}")
                        self._simple_restart_vlc()
            
            with self.lock:
                # 对于VLC直接播放，获取当前播放时间而不是设置时间
                if self.decoder._is_vlc_player_valid():
                    # 获取VLC当前播放时间
                    vlc_time = self.decoder._safe_vlc_operation(
                        lambda: self.decoder.media_player.get_time(),
                        "获取VLC播放时间"
                    )
                    vlc_state = self.decoder._safe_vlc_operation(
                        lambda: self.decoder.media_player.get_state(),
                        "获取VLC播放状态"
                    )
                    
                    # 检查VLC播放状态（由于设置了循环播放，通常不会出现Ended状态）
                    if vlc and vlc_state == vlc.State.Ended:
                        # VLC播放结束，使用简单重启
                        print(f"检测到VLC播放结束，简单重启: {self.video_path}")
                        self._simple_restart_vlc()
                        return
                    
                    if vlc_time is not None and vlc_time >= 0:
                        self.current_time_ms = vlc_time
                    else:
                        # 如果VLC返回无效时间，使用我们自己的计时
                        self.current_time_ms += int(self.frame_time * self.playback_speed)
                else:
                    # 如果没有VLC播放器，使用我们自己的计时
                    self.current_time_ms += int(self.frame_time * self.playback_speed)
                
                # 计算当前帧号
                self.current_frame_number = int((self.current_time_ms / 1000.0) * self.fps)
                
                # 记录发送时间
                self.last_emit_time = time.time()

                # 发送帧数据（frame为None，让VLC直接播放）
                self.frame_ready.emit(
                    self.current_frame_number, None, self.current_time_ms
                )
                
                # 备用检查：如果时间超过视频长度，也触发重播（简化版本）
                if self.current_time_ms >= self.decoder.duration_ms:
                    print(f"时间检查：视频播放完毕，简单重启: {self.video_path}")
                    self._simple_restart_vlc()
                    return

    def seek(self, frame_number):
        with self.lock:
            if frame_number >= 0:
                # 计算对应的时间
                self.current_time_ms = int(frame_number * self.frame_time)
                self.current_frame_number = frame_number
                
                # 使用解码器获取帧
                frame = self.decoder.get_frame_at_time(self.current_time_ms)
                if frame is not None:
                    # 将帧发送给播放器
                    self.frame_ready.emit(self.current_frame_number, frame, self.current_time_ms)
                else:
                    print(f"Seek到帧 {frame_number} 失败")

    def _simple_restart_vlc(self):
        """简单重启VLC播放"""
        try:
            print(f"简单重启VLC播放: {self.video_path}")
            
            # 重置时间状态
            self.current_time_ms = 0
            self.current_frame_number = 0
            
            # 简单重启VLC播放器
            if hasattr(self.decoder, 'media_player') and self.decoder.media_player:
                try:
                    # 直接重新开始播放
                    self.decoder.media_player.play()
                    self.decoder.is_playing = True
                    
                    # 设置播放位置到开始
                    self.decoder.media_player.set_time(0)
                    
                    print("VLC简单重启成功")
                        
                except Exception as e:
                    print(f"简单重启VLC播放器失败: {str(e)}")
            
            # 发送重播信号，通知VideoPlayer更新UI状态
            self.frame_ready.emit(0, None, 0)
            
        except Exception as e:
            print(f"简单重启VLC播放失败: {str(e)}")


    def seek_time(self, time_ms):
        """按时间戳定位视频位置"""
        with self.lock:
            if time_ms >= 0:
                self.current_time_ms = time_ms
                self.current_frame_number = int((time_ms / 1000.0) * self.fps)

    def pause(self):
        self.paused = True
        # 暂停VLC播放器 - 添加安全检查
        if self.decoder._is_vlc_player_valid():
            state = self.decoder._safe_vlc_operation(
                lambda: self.decoder.media_player.get_state(),
                "获取VLC播放状态"
            )
            if vlc and state in [vlc.State.Ended, vlc.State.Stopped]:
                print(f"VLC播放器已结束，跳过暂停操作")
                return
            
            self.decoder._safe_vlc_operation(
                lambda: self.decoder.media_player.pause(),
                f"VLC播放器暂停: {self.video_path}"
            )

    def resume(self):
        self.paused = False
        # 恢复VLC播放器
        self.decoder._safe_vlc_operation(
            lambda: self.decoder.media_player.play(),
            f"VLC播放器恢复: {self.video_path}"
        )

    def stop(self):
        """停止帧读取器"""
        try:
            print(f"停止帧读取器: {self.video_path}")
            self.running = False
            self.paused = True
            
            # 停止VLC播放器 - 添加更安全的检查
            if hasattr(self.decoder, 'media_player') and self.decoder.media_player:
                try:
                    # 先检查VLC播放器是否仍然有效
                    if hasattr(self.decoder.media_player, 'get_state'):
                        try:
                            state = self.decoder.media_player.get_state()
                            print(f"VLC播放器当前状态: {state}")
                        except Exception as e:
                            print(f"无法获取VLC播放器状态: {str(e)}")
                            # 如果无法获取状态，说明对象可能已损坏，跳过停止操作
                            return
                    
                    self.decoder.media_player.stop()
                    print("VLC播放器已停止")
                except Exception as e:
                    print(f"停止VLC播放器失败: {str(e)}")
                    # 继续执行，不因为VLC停止失败而阻塞
            
            # 等待线程结束（带超时）
            if not self.wait(1500):  # 缩短到1.5秒超时
                self.terminate()
                if not self.wait(500):  # 缩短到0.5秒
                    print("强制终止线程失败，继续执行")
            
            # 释放解码器资源
            if self.decoder:
                try:
                    self.decoder.release()
                except Exception as e:
                    print(f"释放解码器资源失败: {str(e)}")
                    
        except Exception as e:
            print(f"停止帧读取器时出错: {str(e)}")
            import traceback
            traceback.print_exc()


class VideoPlayer(QWidget):
    def __init__(self, video_path, parent=None, rotate_angle=0):
        super().__init__(parent)
        self.video_wall = parent  # 保存 VideoWall 的引用
        self.video_path = video_path
        self.rotate_angle = rotate_angle  # 添加旋转角度参数

        # VLC检测已在程序启动时完成，这里直接初始化

        try:
            # 初始化帧读取线程，使用信号槽代替队列
            self.frame_reader = FrameReader(video_path, rotate_angle=rotate_angle)
            self.frame_reader.frame_ready.connect(self.on_frame_ready)

            # 从帧读取器获取视频基本信息
            self.total_frames = self.frame_reader.decoder.total_frames
            self.fps = self.frame_reader.decoder.fps
            self.duration_ms = self.frame_reader.decoder.duration_ms

            self.init_ui()
            
            # 设置VLC输出到VideoFrame
            self.setup_vlc_output()
            
            
            # 启动帧读取线程
            self.frame_reader.start()
            
            # 更新VLC进度条的时长信息
            self.update_vlc_slider_duration()
            self.is_paused = False
            self.playback_speed = 1.0
            # 移除旋转功能，不再需要
            self.frame_skip = 0
            self.current_frame = 0
            self.current_time = 0  # 当前播放时间(毫秒)
            self.last_update_time = time.time()  # 上次更新帧的时间
            
            # 添加进度条拖拽状态标志
            self.slider_dragging = False
            

            # 添加缓冲最新帧
            self.latest_frame = None
            self.latest_frame_number = -1
            self.latest_frame_time = 0

            # 标记是否处于循环播放的过渡期
            self.is_looping = False
            
            # 添加帧缓存机制，用于逐帧操作
            self.frame_cache = {}
            self.max_cache_size = 10  # 最多缓存10帧


            
            # 添加析构时的清理
            self.destroyed.connect(self.cleanup)
            self.is_cleaning_up = False  # 添加清理标志

        except Exception as e:
            error_msg = f"无法加载视频 {video_path}: {str(e)}"
            if "VLC未安装" not in str(e):
                QMessageBox.critical(parent, "错误", error_msg)
            raise

    def format_time(self, time_ms):
        """将毫秒时间格式化为分:秒.毫秒"""
        total_seconds = time_ms / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        ms = int((total_seconds - int(total_seconds)) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{ms:03d}"
    
    def _update_progress_bar(self, time_ms):
        """统一更新进度条的方法"""
        if not self.slider_dragging and self.duration_ms > 0:
            progress = (time_ms / self.duration_ms) * 100
            progress = max(0, min(100, int(progress)))
            try:
                if hasattr(self.slider, 'setValue') and self.slider is not None:
                    self.slider.setValue(progress)
            except Exception as e:
                print(f"更新进度条失败: {str(e)}")
    
    def _update_info_label(self, frame_number, time_ms):
        """统一更新信息标签的方法"""
        current_time_str = self.format_time(time_ms)
        total_time_str = self.format_time(self.duration_ms)
        info_text = f"帧: {frame_number}/{self.total_frames} 时间: {current_time_str}/{total_time_str}"
        self.info_label.setText(info_text)

    def on_frame_ready(self, frame_number, frame, time_ms):
        """当帧准备好时，显示它并更新状态"""
        try:
            # 更新当前帧信息
            self.current_frame = frame_number
            self.current_time = time_ms
            
            # 如果frame为None，说明VLC正在直接播放，不需要显示占位符
            if frame is None:
                # 但是需要更新UI状态，特别是VLC原生进度条
                self._update_progress_bar(time_ms)
                self._update_info_label(frame_number, time_ms)
                return

            # 轻量级帧变化检测
            if hasattr(self, 'last_frame_number') and frame_number == self.last_frame_number:
                return  # 帧号没有变化，跳过处理
            self.last_frame_number = frame_number

            # 更新缓存的最新帧
            self.latest_frame = frame
            self.latest_frame_number = frame_number
            self.latest_frame_time = time_ms
            
            # 缓存当前帧用于逐帧操作
            self.cache_frame(frame_number, frame)

            # 更新当前帧和时间
            self.current_frame = frame_number
            self.current_time = time_ms

            # 自适应UI更新频率
            update_ui = (frame_number % 3 == 0)
            
            if update_ui:  # 拖拽时不自动更新进度条
                self._update_progress_bar(time_ms)

            # 显示帧（VLC直接播放时不需要旋转处理）
            self.display_frame(frame)

            # 自适应信息更新
            if frame_number % 5 == 0:
                self._update_info_label(frame_number, time_ms)

        except Exception as e:
            print(f"处理帧时出错: {str(e)}")


    def cleanup(self):
        """清理资源"""
        try:
            self.is_cleaning_up = True  # 设置清理标志
            
            # 断开信号连接，防止内存泄漏
            if hasattr(self, "frame_reader") and self.frame_reader:
                if self.safe_disconnect_signal(self.frame_reader.frame_ready):
                    print("已断开FrameReader信号连接")
                else:
                    print("FrameReader信号连接已断开或未连接")
            
            # 停止UI定时器 - 确保在主线程中执行
            if hasattr(self, "ui_timer"):
                try:
                    # 使用QTimer.singleShot确保在主线程中执行
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self._stop_ui_timer)
                except Exception as e:
                    print(f"停止UI定时器失败: {str(e)}")
            
            # 停止帧读取器 - 使用更安全的方式
            if hasattr(self, "frame_reader") and self.frame_reader:
                try:
                    # 先标记为停止状态
                    self.frame_reader.running = False
                    self.frame_reader.paused = True
                    
                    # 等待线程自然结束，不调用可能有问题的stop方法
                    if not self.frame_reader.wait(1000):  # 1秒超时
                        print("FrameReader线程等待超时，尝试强制终止")
                        try:
                            self.frame_reader.terminate()
                            if not self.frame_reader.wait(500):
                                print("强制终止FrameReader线程失败，继续执行")
                        except Exception as e:
                            print(f"终止FrameReader线程时出错: {str(e)}")
                    
                    # 清理FrameReader的VLC资源
                    if hasattr(self.frame_reader, "decoder") and self.frame_reader.decoder:
                        self.frame_reader.decoder.release()
                        self.frame_reader.decoder = None
                    
                    # 清空FrameReader引用
                    self.frame_reader = None
                except Exception as e:
                    print(f"停止帧读取器失败: {str(e)}")
            
            # 清空帧缓存
            if hasattr(self, "frame_cache"):
                try:
                    self.clear_frame_cache()
                except Exception as e:
                    print(f"清空帧缓存失败: {str(e)}")
            
            # 断开与父窗口的循环引用
            if hasattr(self, "video_wall"):
                self.video_wall = None
            
            # 清理其他资源（移除缩放缓存相关代码）
        except Exception as e:
            print(f"清理VideoPlayer资源时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _stop_ui_timer(self):
        """在主线程中停止UI定时器"""
        try:
            if hasattr(self, "ui_timer") and self.ui_timer:
                self.ui_timer.stop()
        except Exception as e:
            print(f"停止UI定时器失败: {str(e)}")
    
    def _cleanup_vlc_resources(self):
        """清理VLC相关资源（可在后台线程中调用）"""
        try:
            # 停止帧读取器 - 使用更安全的方式
            if hasattr(self, "frame_reader") and self.frame_reader:
                try:
                    # 先标记为停止状态
                    self.frame_reader.running = False
                    self.frame_reader.paused = True
                    
                    # 等待线程自然结束，不调用可能有问题的stop方法
                    if not self.frame_reader.wait(1000):  # 1秒超时
                        print("_cleanup_vlc_resources: FrameReader线程等待超时，尝试强制终止")
                        try:
                            self.frame_reader.terminate()
                            if not self.frame_reader.wait(500):
                                print("_cleanup_vlc_resources: 强制终止FrameReader线程失败，继续执行")
                        except Exception as e:
                            print(f"_cleanup_vlc_resources: 终止FrameReader线程时出错: {str(e)}")
                    
                    # 清理FrameReader的VLC资源
                    if hasattr(self.frame_reader, "decoder") and self.frame_reader.decoder:
                        self.frame_reader.decoder.release()
                        self.frame_reader.decoder = None
                    
                    # 清空FrameReader引用
                    self.frame_reader = None
                except Exception as e:
                    print(f"停止帧读取器失败: {str(e)}")
            
            # 清空帧缓存
            if hasattr(self, "frame_cache"):
                try:
                    self.clear_frame_cache()
                except Exception as e:
                    print(f"清空帧缓存失败: {str(e)}")
            
            # 断开与父窗口的循环引用
            if hasattr(self, "video_wall"):
                self.video_wall = None
                
        except Exception as e:
            print(f"清理VLC资源时出错: {str(e)}")

    def init_ui(self):
        self.video_frame = VideoFrame(self)
        self.video_frame.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.5);"
        )  # 设置背景色为18%灰色
        self.video_frame.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )  # 允许动态调整大小

        # 文件名标签
        self.filename_label = QLabel(self)
        # 从解码器获取视频的帧率和尺寸信息
        fps = self.frame_reader.decoder.fps
        width = self.frame_reader.decoder.width
        height = self.frame_reader.decoder.height
        # 设置文件名标签，包含帧率和尺寸信息
        filename = os.path.basename(self.video_path)
        self.filename_label.setText(f"{filename} ({fps:.2f}fps, {width}x{height})")
        self.filename_label.setStyleSheet(
            "color: white; background-color: rgba(0, 0, 0, 0.5);"
        )
        self.filename_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.filename_label.setMargin(5)

        # 添加帧数和时间信息标签
        self.info_label = QLabel("帧: 0/0 时间: 00:00.000/00:00.000", self)
        self.info_label.setStyleSheet(
            "color: white; background-color: rgba(0, 0, 0, 0.5);"
        )
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setMargin(2)

        # VLC原生进度条 - 支持点击跳转和拖拽
        self.slider = VLCSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self.seek_position)
        self.slider.sliderPressed.connect(self.handle_slider_pressed)
        self.slider.sliderReleased.connect(self.handle_slider_released)
        # 设置VLC播放器引用，用于原生进度条控制
        self.slider.set_vlc_player(self.frame_reader.decoder.media_player)
        self.slider.set_duration(self.duration_ms)

        # 控制按钮和设置
        self.play_button = QPushButton(self)
        # 设置图标路径
        play_icon_path = (ICONPATH / "play.ico").as_posix()
        self.play_button.setIcon(QIcon(play_icon_path))  # 设置播放图标
        self.play_button.setToolTip("播放/暂停")
        self.play_button.setStyleSheet("border: none;")  # 去掉按钮边框
        self.play_button.clicked.connect(self.play_pause)

        self.replay_button = QPushButton(self)
        # 设置图标路径
        replay_icon_path = (ICONPATH / "replay.ico").as_posix()
        self.replay_button.setIcon(QIcon(replay_icon_path))  # 设置重播图标
        self.replay_button.setStyleSheet("border: none;")  # 去掉按钮边框
        self.replay_button.setToolTip("重播")
        self.replay_button.clicked.connect(self.replay)

        self.speed_label = QLabel("速度:", self)
        self.speed_spinbox = QDoubleSpinBox(self)
        self.speed_spinbox.setRange(0.05, 10.0)  # 支持最小0.05倍速
        self.speed_spinbox.setValue(1.0)
        self.speed_spinbox.setSingleStep(0.05)  # 调整步长为0.05
        self.speed_spinbox.setDecimals(2)  # 设置小数位数为2位
        self.speed_spinbox.valueChanged.connect(self.set_speed)

        # 跳帧数量
        self.frame_skip_label = QLabel("跳帧:", self)
        self.frame_skip_spin = QSpinBox(self)
        self.frame_skip_spin.setRange(0, self.total_frames)
        self.frame_skip_spin.setValue(0)
        self.frame_skip_spin.valueChanged.connect(self.set_frame_skip)

        # 旋转控制按钮 - 左转90度
        self.rotate_left_button = QPushButton(self)
        # 设置左转图标路径
        left_icon_path = (ICONPATH / "left.ico").as_posix()
        self.rotate_left_button.setIcon(QIcon(left_icon_path))  # 设置左转图标
        self.rotate_left_button.setToolTip("向左旋转90度")
        self.rotate_left_button.setStyleSheet("border: none;")  # 去掉按钮边框
        self.rotate_left_button.clicked.connect(self.rotate_left_90)

        # 旋转控制按钮 - 右转90度  
        self.rotate_right_button = QPushButton(self)
        # 设置右转图标路径
        right_icon_path = (ICONPATH / "right.ico").as_posix()
        self.rotate_right_button.setIcon(QIcon(right_icon_path))  # 设置右转图标
        self.rotate_right_button.setToolTip("向右旋转90度")
        self.rotate_right_button.setStyleSheet("border: none;")  # 去掉按钮边框
        self.rotate_right_button.clicked.connect(self.rotate_right_90)

        # 控制布局
        control_layout = QHBoxLayout()
        control_layout.addStretch()  # 添加弹性空间以实现水平居中
        control_layout.addWidget(self.speed_label)
        control_layout.addWidget(self.speed_spinbox)
        control_layout.addWidget(self.frame_skip_label)
        control_layout.addWidget(self.frame_skip_spin)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.replay_button)
        control_layout.addWidget(self.rotate_left_button)
        control_layout.addWidget(self.rotate_right_button)
        control_layout.addStretch()

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.slider, stretch=1)
        bottom_layout.addLayout(control_layout, stretch=1)
        bottom_layout.addWidget(self.info_label, stretch=1)  # 添加信息标签在最下方

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.filename_label)
        main_layout.addWidget(self.video_frame, stretch=1)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        self.setMinimumSize(300, 200)  # 设置最小大小，防止过小

        # 性能优化：降低UI更新频率
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(33)  # 约30fps的UI刷新率，减少CPU占用
    
    def setup_vlc_output(self):
        """设置VLC输出到VideoFrame"""
        try:
            # 延迟设置VLC输出窗口，确保VideoFrame已经完全初始化
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, self._delayed_setup_vlc_output)  # 增加延迟时间
        except Exception as e:
            print(f"设置VLC输出失败: {str(e)}")
    
    def _delayed_setup_vlc_output(self):
        """延迟设置VLC输出窗口"""
        try:
            # 获取VideoFrame的窗口句柄
            if hasattr(self.video_frame, 'winId'):
                window_handle = self.video_frame.winId()
                if window_handle:
                    # 设置VLC输出到VideoFrame
                    success = self.frame_reader.decoder.set_output_window(window_handle)
                else:
                    print("VideoFrame窗口句柄为空")
            else:
                print("无法获取VideoFrame窗口句柄")
        except Exception as e:
            print(f"延迟设置VLC输出失败: {str(e)}")
    
    def _retry_vlc_output(self):
        """重试设置VLC输出"""
        try:
            if hasattr(self.video_frame, 'winId'):
                window_handle = self.video_frame.winId()
                if window_handle:
                    success = self.frame_reader.decoder.set_output_window(window_handle)
                    if success:
                        print("VLC输出窗口重试设置成功")
                    else:
                        print("VLC输出窗口重试设置失败")
        except Exception as e:
            print(f"重试设置VLC输出失败: {str(e)}")
    
    
    def update_vlc_slider_duration(self):
        """更新VLC进度条的时长信息"""
        try:
            if hasattr(self, 'slider') and hasattr(self.slider, 'set_duration'):
                self.slider.set_duration(self.duration_ms)
        except Exception as e:
            print(f"更新VLC进度条时长失败: {str(e)}")

    def update_ui(self):
        """确保UI定期更新，即使没有新帧到达"""
        # 更新帧数和时间信息
        self._update_info_label(self.current_frame, self.current_time)

    def display_frame(self, frame):
        """
        显示帧数据 - 简化版本
        注意：当VLC直接播放时，frame参数为None，此时不需要处理
        此方法仅用于特殊情况下的帧显示，大部分情况下VLC直接播放
        """
        if frame is None:
            # VLC直接播放模式，不需要处理
            return

        try:
            # 检查frame是否为numpy数组
            if not isinstance(frame, np.ndarray):
                print("警告：frame不是numpy数组，无法显示")
                return
            
            # 直接转换numpy数组为QImage，不进行缩放和居中处理
            if len(frame.shape) == 3:
                # 彩色图像
                height, width, channel = frame.shape
                bytes_per_line = channel * width
                
                # 确保数据连续性
                if not frame.flags['C_CONTIGUOUS']:
                    frame = np.ascontiguousarray(frame)
                
                # 根据通道数选择格式
                if channel == 3:
                    q_img = QImage(
                        frame.data, width, height, bytes_per_line, QImage.Format_RGB888
                    )
                elif channel == 4:
                    q_img = QImage(
                        frame.data, width, height, bytes_per_line, QImage.Format_RGBA8888
                    )
                else:
                    print(f"不支持的通道数: {channel}")
                    return
            else:
                # 灰度图像
                height, width = frame.shape
                
                # 确保数据连续性
                if not frame.flags['C_CONTIGUOUS']:
                    frame = np.ascontiguousarray(frame)
                    
                q_img = QImage(
                    frame.data, width, height, width, QImage.Format_Grayscale8
                )

            # 转换为像素图并显示
            pixmap = QPixmap.fromImage(q_img)
            self.video_frame.setPixmap(pixmap)
        except Exception as e:
            print(f"显示帧时出错: {str(e)}")

    def play_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.frame_reader.resume()
            self.last_update_time = time.time()  # 重置时间基准
            play_icon_path = (ICONPATH / "play.ico").as_posix()
            self.play_button.setIcon(QIcon(play_icon_path))
        else:
            self.is_paused = True
            self.frame_reader.pause()
            pause_icon_path = (ICONPATH / "pause.ico").as_posix()
            self.play_button.setIcon(QIcon(pause_icon_path))

    def replay(self):
        """重播视频"""
        try:
            print(f"重播视频: {self.video_path}")
            
            # 重置播放状态
            self.current_time = 0
            self.current_frame = 0
            
            # 重置VLC播放器到开始位置
            if hasattr(self.frame_reader, 'decoder') and hasattr(self.frame_reader.decoder, 'media_player'):
                try:
                    # 设置VLC播放位置到开始
                    self.frame_reader.decoder.media_player.set_time(0)
                    print("VLC播放器重置到开始位置")
                except Exception as e:
                    print(f"重置VLC播放器位置失败: {str(e)}")
            
            # 重置FrameReader状态
            self.frame_reader.seek_time(0)
            
            # 重置UI状态
            self.slider.setValue(0)
            
            # 如果当前是暂停状态，切换为播放
            if self.is_paused:
                self.play_pause()
                
            print("视频重播完成")
            
        except Exception as e:
            print(f"重播视频失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def set_speed(self, value):
        """设置播放速度，影响帧读取器的行为"""
        old_speed = self.playback_speed
        self.playback_speed = value

        # 将播放速度传递给帧读取器
        if hasattr(self, "frame_reader"):
            self.frame_reader.set_playback_speed(value)

        print(f"播放速度从 {old_speed} 更改为 {value}")

    def set_frame_skip(self, value):
        self.frame_skip = value
        if self.frame_skip < self.total_frames:
            time_ms = int(self.frame_skip * (1000 / self.fps))
            self.current_time = time_ms
            self.frame_reader.seek_time(time_ms)
            self.current_frame = self.frame_skip
            self.last_update_time = time.time()  # 重置时间基准

    def seek_position(self, position):
        """VLC原生进度条跳转处理"""
        # 根据百分比计算目标时间
        target_time = int((position / 100) * self.duration_ms)
        self.current_time = target_time
        
        # 使用VLC原生跳转（VLCSlider已经处理了VLC跳转，这里只需要更新状态）
        if hasattr(self.frame_reader, 'decoder') and hasattr(self.frame_reader.decoder, 'media_player'):
            try:
                # VLCSlider已经调用了set_time，这里只需要同步状态
                self.frame_reader.seek_time(target_time)
                self.last_update_time = time.time()  # 重置时间基准
                print(f"进度条跳转到: {target_time}ms ({position}%)")
            except Exception as e:
                print(f"同步VLC跳转状态失败: {str(e)}")

    def handle_slider_pressed(self):
        """VLC原生滑块按下时的处理"""
        # 暂停自动更新进度条，避免冲突
        self.slider_dragging = True
        print("VLC进度条开始拖拽")
        
    def handle_slider_released(self):
        """VLC原生滑块释放时的处理"""
        # 恢复自动更新进度条
        self.slider_dragging = False
        print("VLC进度条拖拽结束")
        # VLCSlider已经处理了跳转，这里只需要同步状态
        self.seek_position(self.slider.value())


    def get_cached_frame(self, frame_number):
        """获取缓存的帧，如果没有则返回None"""
        return self.frame_cache.get(frame_number)
    
    def cache_frame(self, frame_number, frame):
        """缓存帧"""
        # 如果缓存已满，移除最旧的帧
        if len(self.frame_cache) >= self.max_cache_size:
            oldest_frame = min(self.frame_cache.keys())
            del self.frame_cache[oldest_frame]
        
        # 缓存当前帧
        self.frame_cache[frame_number] = frame.copy()
    
    def clear_frame_cache(self):
        """清空帧缓存"""
        self.frame_cache.clear()
    
    def safe_disconnect_signal(self, signal, slot=None):
        """安全断开信号连接，避免重复断开错误"""
        try:
            if slot is None:
                # 断开所有连接
                try:
                    signal.disconnect()
                    return True
                except TypeError:
                    # 如果没有连接，disconnect()会抛出TypeError
                    return False
            else:
                # 断开特定连接
                try:
                    signal.disconnect(slot)
                    return True
                except TypeError:
                    # 如果没有连接，disconnect()会抛出TypeError
                    return False
        except Exception as e:
            print(f"断开信号连接失败: {str(e)}")
            return False
    
    def set_rotate_angle(self, angle):
        """设置视频旋转角度"""
        try:
            if self.rotate_angle == angle:
                print(f"旋转角度已经是 {angle}度，无需更改")
                return True
            
            print(f"VideoPlayer设置旋转角度: {self.rotate_angle}度 -> {angle}度")
            
            # 保存当前播放状态
            was_playing = not self.is_paused
            current_time = self.current_time
            
            # 暂停播放
            if was_playing:
                self.play_pause()
            
            # 通过帧读取器设置旋转角度
            if self.frame_reader:
                success = self.frame_reader.set_rotate_angle(angle)
                if success:
                    # 更新旋转角度
                    self.rotate_angle = angle
                    
                    # 调整VideoFrame大小以适应旋转后的视频（包含VLC输出窗口设置）
                    self._adjust_video_frame_size(angle)
                    
                    # 跳转到之前的时间位置
                    if current_time > 0:
                        self.seek_time(current_time)
                    
                    # 恢复播放状态
                    if was_playing:
                        self.play_pause()
                    
                    print(f"✅ VideoPlayer旋转角度已更新为: {angle}度")
                    return True
                else:
                    print(f"❌ VideoPlayer旋转角度更新失败")
                    return False
            else:
                print("❌ 帧读取器未初始化，无法设置旋转角度")
                return False
                
        except Exception as e:
            print(f"设置VideoPlayer旋转角度失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _adjust_video_frame_size(self, angle):
        """调整VideoFrame大小以适应旋转后的视频"""
        try:
            if not hasattr(self, 'video_frame') or not self.video_frame:
                return
            
            # 获取旋转后的视频尺寸
            if hasattr(self.frame_reader, 'decoder'):
                new_width, new_height = self.frame_reader.decoder.get_rotated_video_size(angle)
                
                # 验证尺寸的合理性
                if new_width <= 0 or new_height <= 0:
                    print(f"❌ 无效的视频尺寸: {new_width}x{new_height}")
                    return
                
                # 设置VideoFrame的旋转角度
                self.video_frame.set_rotation_angle(angle)
                
                # 不改变VideoFrame的尺寸，让布局管理器自动处理
                # 只更新内部状态，不强制改变QWidget大小
                
                # 更新文件名标签中的尺寸信息
                if hasattr(self, 'filename_label'):
                    filename = os.path.basename(self.video_path)
                    fps = self.frame_reader.decoder.fps
                    self.filename_label.setText(f"{filename} ({fps:.2f}fps, {new_width}x{new_height})")
                
                print(f"VideoFrame旋转角度已更新: {angle}度 (原始视频尺寸: {new_width}x{new_height})")
                
                # 立即重新设置VLC输出窗口
                self._setup_vlc_output_immediately()
                
        except Exception as e:
            print(f"调整VideoFrame尺寸失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _setup_vlc_output_immediately(self):
        """立即设置VLC输出窗口"""
        try:
            if hasattr(self, 'video_frame') and hasattr(self.video_frame, 'winId'):
                window_handle = self.video_frame.winId()
                if window_handle and hasattr(self, 'frame_reader') and hasattr(self.frame_reader, 'decoder'):
                    success = self.frame_reader.decoder.set_output_window(window_handle)
                    if success:
                        print("✅ 立即设置VLC输出窗口成功")
                        
                        # 设置视频缩放，确保旋转后视频能够自适应窗口大小
                        self.frame_reader.decoder._set_video_scale()
                        
                        # 恢复播放状态
                        if not self.is_paused:
                            self.frame_reader.decoder._safe_vlc_operation(
                                lambda: self.frame_reader.decoder.media_player.play(),
                                "恢复VLC播放"
                            )
                    else:
                        print("❌ 立即设置VLC输出窗口失败")
        except Exception as e:
            print(f"立即设置VLC输出窗口失败: {str(e)}")
    
    def _delayed_vlc_output_setup(self):
        """延迟设置VLC输出窗口"""
        try:
            if hasattr(self, 'video_frame') and hasattr(self.video_frame, 'winId'):
                window_handle = self.video_frame.winId()
                if window_handle and hasattr(self, 'frame_reader') and hasattr(self.frame_reader, 'decoder'):
                    success = self.frame_reader.decoder.set_output_window(window_handle)
                    if success:
                        print("✅ 延迟设置VLC输出窗口成功")
                    else:
                        print("❌ 延迟设置VLC输出窗口失败")
        except Exception as e:
            print(f"延迟设置VLC输出窗口失败: {str(e)}")
    
    def seek_time(self, time_ms):
        """按时间戳定位视频位置"""
        try:
            self.current_time = time_ms
            self.current_frame = int((time_ms / 1000.0) * self.fps)
            
            # 使用VLC原生跳转
            if hasattr(self.frame_reader, 'decoder') and hasattr(self.frame_reader.decoder, 'media_player'):
                self.frame_reader.decoder._safe_vlc_operation(
                    lambda: self.frame_reader.decoder.media_player.set_time(time_ms),
                    f"设置VLC播放器位置: {os.path.basename(self.video_path)}"
                )
            
            # 更新FrameReader状态
            if hasattr(self.frame_reader, 'seek_time'):
                self.frame_reader.seek_time(time_ms)
            
            # 更新进度条
            self._update_progress_bar(time_ms)
            
        except Exception as e:
            print(f"跳转到时间位置失败: {str(e)}")
    
    def rotate_left_90(self):
        """向左旋转90度（逆时针）"""
        new_angle = (self.rotate_angle + 270) % 360
        return self.set_rotate_angle(new_angle)
    
    def rotate_right_90(self):
        """向右旋转90度（顺时针）"""
        new_angle = (self.rotate_angle + 90) % 360
        return self.set_rotate_angle(new_angle)
    
    def reset_rotation(self):
        """重置旋转角度为0度"""
        return self.set_rotate_angle(0)
    
    def set_video_scale(self, scale=0):
        """设置视频缩放比例"""
        try:
            if hasattr(self, 'frame_reader') and hasattr(self.frame_reader, 'decoder'):
                success = self.frame_reader.decoder.set_video_scale(scale)
                if success:
                    print(f"✅ VideoPlayer视频缩放比例设置为: {scale}")
                    return True
                else:
                    print(f"❌ VideoPlayer设置视频缩放比例失败: {scale}")
                    return False
            else:
                print("❌ 帧读取器未初始化，无法设置视频缩放比例")
                return False
        except Exception as e:
            print(f"设置VideoPlayer视频缩放比例失败: {str(e)}")
            return False
    
    def fit_to_window(self):
        """让视频适应窗口大小"""
        return self.set_video_scale(0)  # 0表示自适应
    
    def zoom_in(self):
        """放大视频"""
        return self.set_video_scale(1.2)  # 放大20%
    
    def zoom_out(self):
        """缩小视频"""
        return self.set_video_scale(0.8)  # 缩小20%


class VideoWall(QWidget):
    # 定义关闭信号
    closed = pyqtSignal()
    def __init__(self):
        super().__init__()
        # 首先检测VLC，如果未安装则显示下载对话框并退出程序 
        self.vlc_flag = False
        if not check_vlc_installation():
            show_vlc_startup_dialog()
            self.vlc_flag = True
            return 

        # 设置图标路径
        icon_path = (ICONPATH / "video_icon.ico").as_posix()
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("多视频播放器")
        self.setAcceptDrops(True)
        self.init_ui()
        self.players = []

        # 将窗口移动到鼠标所在的屏幕
        self.move_to_current_screen()
        self.resize(1400, 1000)

        # 添加全屏快捷键
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.is_fullscreen = False

        # 添加 D 快捷键用于清空视频
        clear_shortcut = QShortcut(QKeySequence("D"), self)
        clear_shortcut.activated.connect(self.clear_videos)

        # 修改 Q 快捷键用于播放/暂停所有视频
        play_pause_all_shortcut = QShortcut(QKeySequence("Q"), self)
        play_pause_all_shortcut.activated.connect(self.play_pause_all_videos)

        # 修改 W 快捷键用于重播所有视频
        replay_all_shortcut = QShortcut(QKeySequence("W"), self)
        replay_all_shortcut.activated.connect(self.replay_all_videos)

        # 添加 E 快捷键用于快进所有视频
        speed_up_shortcut = QShortcut(QKeySequence("E"), self)
        speed_up_shortcut.activated.connect(self.speed_up_all_videos)

        # 添加 R 快捷键用于慢放所有视频
        slow_down_shortcut = QShortcut(QKeySequence("R"), self)
        slow_down_shortcut.activated.connect(self.slow_down_all_videos)

        # 添加 T 快捷键用于从跳帧数开始播放所有视频
        jump_to_frame_shortcut = QShortcut(QKeySequence("T"), self)
        jump_to_frame_shortcut.activated.connect(self.jump_to_frame_all_videos)

        # 添加 Z 快捷键用于逐帧后退
        frame_backward_shortcut = QShortcut(QKeySequence("Z"), self)
        frame_backward_shortcut.activated.connect(self.frame_backward_all_videos)

        # 添加 X 快捷键用于逐帧前进
        frame_forward_shortcut = QShortcut(QKeySequence("X"), self)
        frame_forward_shortcut.activated.connect(self.frame_forward_all_videos)

        # 添加 ESC 快捷键用于退出程序
        exit_shortcut = QShortcut(QKeySequence("Esc"), self)
        exit_shortcut.activated.connect(self.close_properly)
        
        

    def init_ui(self):
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)  # 允许滚动区域内容自动调整大小

        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)  # 将边距设为0
        self.grid_layout.setSpacing(3)  # 将间距设为0

        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        # 添加提示标签
        self.hint_label = QLabel("请将视频拖入程序窗口内", self)
        self.hint_label.setAlignment(Qt.AlignCenter)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.hint_label)  # 添加提示标签到布局
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
        self.resize(1800, 1200)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        video_extensions = (".mp4", ".avi", ".mkv", ".mov")
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(video_extensions):
                try:
                    player = VideoPlayer(file_path, parent=self, rotate_angle=0)  # 将 self 作为父级传递
                    self.players.append(player)
                except Exception as e:
                    print(f"加载视频失败 {file_path}: {str(e)}")

        # 隐藏提示标签
        if self.players:
            self.refresh_layout()
            self.hint_label.hide()

    def add_video_list(self, video_paths):
        """
        添加视频文件列表到播放器
        
        Args:
            video_paths (list): 视频文件路径列表
            
        Returns:
            dict: 包含成功和失败信息的字典
                {
                    'success': [成功添加的视频路径列表],
                    'failed': [失败的视频路径列表],
                    'errors': {路径: 错误信息}
                }
        """
        if not isinstance(video_paths, (list, tuple)):
            print("错误：video_paths 必须是列表或元组")
            return {
                'success': [],
                'failed': video_paths if isinstance(video_paths, str) else [],
                'errors': {'input': '参数必须是列表或元组'}
            }
        
        # VLC检测已在程序启动时完成，这里直接处理视频文件
        
        # 支持的视频格式
        video_extensions = (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v")
        
        result = {
            'success': [],
            'failed': [],
            'errors': {}
        } 
        for i, video_path in enumerate(video_paths):
            try:
                # 验证文件路径
                if not isinstance(video_path, str):
                    error_msg = f"文件路径必须是字符串，当前类型: {type(video_path)}"
                    result['failed'].append(str(video_path))
                    result['errors'][str(video_path)] = error_msg
                    continue
                
                # 检查文件是否存在
                if not os.path.exists(video_path):
                    error_msg = "文件不存在"
                    print(f"跳过文件 {i+1}: {video_path} - {error_msg}")
                    result['failed'].append(video_path)
                    result['errors'][video_path] = error_msg
                    continue
                
                # 检查文件扩展名
                if not video_path.lower().endswith(video_extensions):
                    error_msg = f"不支持的视频格式，支持的格式: {', '.join(video_extensions)}"
                    print(f"跳过文件 {i+1}: {video_path} - {error_msg}")
                    result['failed'].append(video_path)
                    result['errors'][video_path] = error_msg
                    continue
                
                # 检查是否已经添加过
                if any(player.video_path == video_path for player in self.players):
                    error_msg = "视频已经添加过了"
                    print(f"跳过文件 {i+1}: {video_path} - {error_msg}")
                    result['failed'].append(video_path)
                    result['errors'][video_path] = error_msg
                    continue
                
                # 尝试创建视频播放器
                print(f"添加视频 {i+1}/{len(video_paths)}: {os.path.basename(video_path)}")
                player = VideoPlayer(video_path, parent=self, rotate_angle=0)
                self.players.append(player)
                result['success'].append(video_path)
                
            except Exception as e:
                error_msg = f"创建播放器失败: {str(e)}"
                print(f"添加视频失败 {i+1}: {video_path} - {error_msg}")
                result['failed'].append(video_path)
                result['errors'][video_path] = error_msg
                import traceback
                traceback.print_exc()
        
        # 刷新布局
        if result['success']:
            self.refresh_layout()
            # 隐藏提示标签
            self.hint_label.hide()
        
        if result['failed']:
            print("失败的文件:")
            for failed_path in result['failed']:
                error_info = result['errors'].get(failed_path, "未知错误")
                print(f"  - {os.path.basename(failed_path)}: {error_info}")
        
        return result

    def cleanup_all_resources(self):
        """
        公共方法：清理所有资源，供外部程序调用 - 优化版本
        当其他程序使用VideoWall时，应该在程序结束前调用此方法
        """
        try:
            print("开始清理VideoWall所有资源...")
            
            # 直接调用clear_videos进行清理
            self.clear_videos()
            
            # 清理其他资源
            try:
                if hasattr(self, "scroll_area"):
                    self.scroll_area.setWidget(None)
                
                if hasattr(self, "scroll_widget"):
                    self.scroll_widget.setParent(None)
                    self.scroll_widget = None
            except:
                pass
            
            # 强制垃圾回收
            try:
                import gc
                gc.collect()
                print("✅ VideoWall资源清理完成，内存已回收")
            except Exception as e:
                print(f"垃圾回收失败: {str(e)}")
                
        except Exception as e:
            print(f"清理VideoWall资源时出错: {str(e)}")
            # 紧急清理
            try:
                import gc
                gc.collect()
            except:
                pass

    def add_videos_from_folder(self, folder_path, recursive=False):
        """
        从文件夹添加所有视频文件
        
        Args:
            folder_path (str): 文件夹路径
            recursive (bool): 是否递归搜索子文件夹
            
        Returns:
            dict: 同 add_video_list 的返回值
        """
        if not os.path.exists(folder_path):
            print(f"错误：文件夹不存在: {folder_path}")
            return {
                'success': [],
                'failed': [],
                'errors': {'folder': f'文件夹不存在: {folder_path}'}
            }
        
        if not os.path.isdir(folder_path):
            print(f"错误：路径不是文件夹: {folder_path}")
            return {
                'success': [],
                'failed': [],
                'errors': {'folder': f'路径不是文件夹: {folder_path}'}
            }
        
        # 支持的视频格式
        video_extensions = (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v")
        
        video_files = []
        
        try:
            if recursive:
                # 递归搜索
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(video_extensions):
                            video_files.append(os.path.join(root, file))
            else:
                # 只搜索当前文件夹
                for file in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, file)
                    if os.path.isfile(file_path) and file.lower().endswith(video_extensions):
                        video_files.append(file_path)
            
            print(f"在文件夹 {folder_path} 中找到 {len(video_files)} 个视频文件")
            
            if not video_files:
                print("没有找到任何视频文件")
                return {
                    'success': [],
                    'failed': [],
                    'errors': {'folder': '没有找到任何视频文件'}
                }
            
            # 使用 add_video_list 添加视频
            return self.add_video_list(video_files)
            
        except Exception as e:
            error_msg = f"扫描文件夹失败: {str(e)}"
            print(error_msg)
            return {
                'success': [],
                'failed': [],
                'errors': {'folder': error_msg}
            }

    def resizeEvent(self, event):
        self.refresh_layout()
        super().resizeEvent(event)

    def refresh_layout(self):
        # 清空现有布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                self.grid_layout.removeWidget(widget)

        if not self.players:
            self.hint_label.show()  # 如果没有播放器，显示提示标签
            return

        # 动态计算每行最多显示的播放器数量
        available_width = self.scroll_area.width()  # 不再减去边距
        player_width = 300  # 每个播放器的建议宽度
        columns = max(1, available_width // player_width)

        for index, player in enumerate(self.players):
            row = index // columns
            col = index % columns
            self.grid_layout.addWidget(player, row, col)

            # 移除播放器内部的边距
            if hasattr(player, "layout"):
                player.layout().setContentsMargins(0, 0, 0, 0)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True

    def clear_videos(self):
        """清空所有视频播放器并释放资源 - 优化版本"""
        try:
            print("开始清空所有视频...")
            
            # 强制清理所有播放器资源
            for i, player in enumerate(self.players):
                try:
                    # 强制停止UI定时器
                    if hasattr(player, "ui_timer") and player.ui_timer:
                        player.ui_timer.stop()
                        player.ui_timer = None
                    
                    # 强制终止线程
                    if hasattr(player, "frame_reader") and player.frame_reader:
                        player.frame_reader.running = False
                        player.frame_reader.paused = True
                        
                        # 强制终止线程，不等待
                        try:
                            player.frame_reader.terminate()
                        except:
                            pass
                        
                        # 使用VLC原生方法释放资源
                        if hasattr(player.frame_reader, "decoder") and player.frame_reader.decoder:
                            try:
                                # 使用强制释放方法，避免阻塞
                                player.frame_reader.decoder.force_release()
                            except Exception as e:
                                print(f"强制释放VLC解码器资源失败: {str(e)}")
                        
                        # 清空解码器引用
                        player.frame_reader.decoder = None
                        player.frame_reader = None
                    
                    # 从布局中移除并立即删除
                    if hasattr(player, "setParent"):
                        player.setParent(None)
                    
                    # 清空播放器引用
                    del player
                        
                except Exception as e:
                    print(f"清理播放器{i+1}时出错: {str(e)}")
            
            # 清空播放器列表
            self.players.clear()
            
            # 立即执行垃圾回收
            try:
                import gc
                gc.collect()
                print("✅ 视频清理完成，内存已回收")
            except Exception as e:
                print(f"垃圾回收失败: {str(e)}")
            
            # 显示提示标签并刷新布局
            self.hint_label.show()
            self.refresh_layout()

        except Exception as e:
            print(f"清空视频时发生错误: {str(e)}")
            # 紧急清理
            try:
                self.players.clear()
                self.hint_label.show()
                self.refresh_layout()
                import gc
                gc.collect()
            except:
                pass

    def play_pause_all_videos(self):
        for player in self.players:
            player.play_pause()

    def replay_all_videos(self):
        for player in self.players:
            player.replay()

    def speed_up_all_videos(self):
        for player in self.players:
            # 智能步长：低速时使用小步长，高速时使用大步长
            if player.playback_speed < 0.2:
                step = 0.05
            elif player.playback_speed < 1.0:
                step = 0.1
            else:
                step = 0.2
            new_speed = min(player.playback_speed + step, 10.0)  # 限制最大速度为10.0
            player.set_speed(new_speed)
            player.speed_spinbox.setValue(new_speed)  # 同步更新spinbox的值

    def slow_down_all_videos(self):
        for player in self.players:
            # 智能步长：低速时使用小步长，高速时使用大步长
            if player.playback_speed <= 0.2:
                step = 0.05
            elif player.playback_speed <= 1.0:
                step = 0.1
            else:
                step = 0.2
            new_speed = max(player.playback_speed - step, 0.05)  # 支持最小速度0.05
            player.set_speed(new_speed)
            player.speed_spinbox.setValue(new_speed)  # 同步更新spinbox的值

    def jump_to_frame_all_videos(self):
        """从每个视频的跳帧数开始播放所有视频"""
        for player in self.players:
            try:
                # 获取跳帧数
                frame_skip = player.frame_skip_spin.value()

                if frame_skip < player.total_frames:
                    # 计算帧对应的时间(毫秒)
                    time_ms = int(frame_skip * (1000 / player.fps))
                    
                    print(f"跳转到帧 {frame_skip} (时间: {time_ms}ms): {os.path.basename(player.video_path)}")

                    # 直接设置VLC播放器位置
                    if hasattr(player, "frame_reader") and hasattr(player.frame_reader, 'decoder'):
                        player.frame_reader.decoder._safe_vlc_operation(
                            lambda: player.frame_reader.decoder.media_player.set_time(time_ms),
                            f"设置VLC播放器位置: {os.path.basename(player.video_path)}"
                        )

                    # 更新FrameReader状态
                    if hasattr(player, "frame_reader"):
                        player.frame_reader.seek_time(time_ms)

                    # 更新播放器状态
                    player.current_frame = frame_skip
                    player.current_time = time_ms

                    # 更新进度条
                    if player.duration_ms > 0:
                        progress = (time_ms / player.duration_ms) * 100
                        progress = max(0, min(100, int(progress)))
                        try:
                            if hasattr(player.slider, 'setValue') and player.slider is not None:
                                player.slider.setValue(progress)
                        except Exception as e:
                            print(f"更新播放器进度条失败: {str(e)}")

                    # 如果视频当前是暂停状态，则恢复播放
                    if player.is_paused:
                        player.is_paused = False
                        player.last_update_time = time.time()  # 重置时间基准

                        # 更新播放/暂停按钮图标
                        play_icon_path = (ICONPATH / "play.ico").as_posix()
                        player.play_button.setIcon(QIcon(play_icon_path))
            except Exception as e:
                print(f"跳转到帧时出错: {str(e)}")
                import traceback
                traceback.print_exc()
    def frame_forward_all_videos(self):
        """所有视频前进一帧 - 使用VLC原生实现"""
        for player in self.players:
            try:
                
                # 确保视频处于暂停状态
                if not player.is_paused:
                    player.play_pause()

                # 计算下一帧的帧数和时间
                next_frame = min(player.total_frames - 1, player.current_frame + 1)
                time_ms = int(next_frame * (1000 / player.fps))
                
                print(f"目标帧: {next_frame}, 目标时间: {time_ms}ms")

                # 使用VLC原生逐帧前进功能
                if hasattr(player, "frame_reader") and hasattr(player.frame_reader, 'decoder'):
                    if player.frame_reader.decoder._is_vlc_player_valid():
                        def frame_forward_operation():
                            # VLC原生逐帧前进 - 尝试不同的方法名
                            if hasattr(player.frame_reader.decoder.media_player, 'next_frame'):
                                player.frame_reader.decoder.media_player.next_frame()
                            elif hasattr(player.frame_reader.decoder.media_player, 'frame_step'):
                                player.frame_reader.decoder.media_player.frame_step()
                            elif hasattr(player.frame_reader.decoder.media_player, 'step'):
                                player.frame_reader.decoder.media_player.step()
                            else:
                                raise AttributeError("VLC播放器不支持逐帧前进方法")
                            
                            # 使用我们计算的帧数，而不是VLC返回的时间
                            player.current_frame = next_frame
                            player.current_time = time_ms
                            
                            # 同步VLC播放器的时间
                            player.frame_reader.decoder.media_player.set_time(time_ms)
                            
                            # 更新FrameReader状态
                            if hasattr(player, "frame_reader"):
                                player.frame_reader.seek_time(time_ms)
                            
                            # 更新进度条
                            player._update_progress_bar(time_ms)
                            
                        result = player.frame_reader.decoder._safe_vlc_operation(
                            frame_forward_operation,
                            f"VLC原生逐帧前进: {os.path.basename(player.video_path)}"
                        )
                        
                        if result is None:
                            # 备用方案：使用时间计算
                            self._fallback_frame_forward(player)

            except Exception as e:
                print(f"前进一帧时出错: {str(e)}")
                import traceback
                traceback.print_exc()

    def frame_backward_all_videos(self):
        """所有视频后退一帧 - 使用VLC原生实现"""
        for player in self.players:
            try:
                
                # 确保视频处于暂停状态
                if not player.is_paused:
                    player.play_pause()

                # 计算上一帧的帧数和时间
                prev_frame = max(0, player.current_frame - 1)
                time_ms = int(prev_frame * (1000 / player.fps))
                
                print(f"目标帧: {prev_frame}, 目标时间: {time_ms}ms")

                # 使用VLC原生逐帧后退功能
                if hasattr(player, "frame_reader") and hasattr(player.frame_reader, 'decoder'):
                    if player.frame_reader.decoder._is_vlc_player_valid():
                        def frame_backward_operation():
                            # VLC原生逐帧后退 - 尝试不同的方法名
                            if hasattr(player.frame_reader.decoder.media_player, 'previous_frame'):
                                player.frame_reader.decoder.media_player.previous_frame()
                            elif hasattr(player.frame_reader.decoder.media_player, 'frame_step_back'):
                                player.frame_reader.decoder.media_player.frame_step_back()
                            elif hasattr(player.frame_reader.decoder.media_player, 'step_back'):
                                player.frame_reader.decoder.media_player.step_back()
                            else:
                                raise AttributeError("VLC播放器不支持逐帧后退方法")
                            
                            # 使用我们计算的帧数，而不是VLC返回的时间
                            player.current_frame = prev_frame
                            player.current_time = time_ms
                            
                            # 同步VLC播放器的时间
                            player.frame_reader.decoder.media_player.set_time(time_ms)
                            
                            # 更新FrameReader状态
                            if hasattr(player, "frame_reader"):
                                player.frame_reader.seek_time(time_ms)
                            
                            # 更新进度条
                            player._update_progress_bar(time_ms)
                            
                        result = player.frame_reader.decoder._safe_vlc_operation(
                            frame_backward_operation,
                            f"VLC原生逐帧后退: {os.path.basename(player.video_path)}"
                        )
                        
                        if result is None:
                            # 备用方案：使用时间计算
                            self._fallback_frame_backward(player)

            except Exception as e:
                print(f"后退一帧时出错: {str(e)}")
                import traceback
                traceback.print_exc()

    def _fallback_frame_forward(self, player):
        """备用方案：使用时间计算前进一帧"""
        try:
            # 计算下一帧的时间
            next_frame = min(player.total_frames - 1, player.current_frame + 1)
            time_ms = int(next_frame * (1000 / player.fps))
            
            # 直接设置VLC播放器位置
            if hasattr(player, "frame_reader") and hasattr(player.frame_reader, 'decoder'):
                player.frame_reader.decoder._safe_vlc_operation(
                    lambda: player.frame_reader.decoder.media_player.set_time(time_ms),
                    f"备用方案设置VLC播放器位置: {os.path.basename(player.video_path)}"
                )

            # 更新FrameReader状态
            if hasattr(player, "frame_reader"):
                player.frame_reader.seek_time(time_ms)

            # 更新播放器状态 - 使用我们计算的帧数
            player.current_frame = next_frame
            player.current_time = time_ms

            # 更新进度条
            player._update_progress_bar(time_ms)
                
            print(f"备用方案前进一帧完成 - 帧: {player.current_frame}, 时间: {player.current_time}ms")
                
        except Exception as e:
            print(f"备用方案前进一帧失败: {str(e)}")

    def _fallback_frame_backward(self, player):
        """备用方案：使用时间计算后退一帧"""
        try:
            # 计算上一帧的时间
            prev_frame = max(0, player.current_frame - 1)
            time_ms = int(prev_frame * (1000 / player.fps))
            
            print(f"使用备用方案后退一帧到 {prev_frame} (时间: {time_ms}ms)")
            
            # 直接设置VLC播放器位置
            if hasattr(player, "frame_reader") and hasattr(player.frame_reader, 'decoder'):
                player.frame_reader.decoder._safe_vlc_operation(
                    lambda: player.frame_reader.decoder.media_player.set_time(time_ms),
                    f"备用方案设置VLC播放器位置: {os.path.basename(player.video_path)}"
                )

            # 更新FrameReader状态
            if hasattr(player, "frame_reader"):
                player.frame_reader.seek_time(time_ms)

            # 更新播放器状态 - 使用我们计算的帧数
            player.current_frame = prev_frame
            player.current_time = time_ms

            # 更新进度条
            player._update_progress_bar(time_ms)
                
            print(f"备用方案后退一帧完成 - 帧: {player.current_frame}, 时间: {player.current_time}ms")
                
        except Exception as e:
            print(f"备用方案后退一帧失败: {str(e)}")
    def close_properly(self):
        """ESC键调用的正确关闭方法，确保资源释放"""
        print("ESC键触发程序关闭，开始清理资源...")
        try:
            # 直接调用clear_videos进行清理
            self.clear_videos()
            
            # 强制垃圾回收
            try:
                import gc
                gc.collect()
                print("✅ ESC键清理完成，内存已回收")
            except Exception as e:
                print(f"垃圾回收失败: {str(e)}")
            
            # 关闭窗口
            self.close()
            
        except Exception as e:
            print(f"ESC键关闭程序时出错: {str(e)}")
            # 出错时强制退出
            import os
            os._exit(0)

    def closeEvent(self, event):
        """程序关闭时的清理 - 优化版本"""
        try:
            print("[sub_compare_vlc_video_view]-->info--开始程序关闭清理...")
            # 直接调用clear_videos进行清理
            self.clear_videos()
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            # # 接受关闭事件
            # event.accept()
                
            # 发射关闭信号（新增），统一在这里发送信号
            self.closed.emit()
            
            # 最后调用父类方法
            super().closeEvent(event)

        except Exception as e:
            print(f"程序关闭时出错: {str(e)}")
            # 出错时立即退出
            import os
            os._exit(0)
        

    def move_to_current_screen(self):
        # 获取鼠标当前位置
        cursor_pos = QCursor.pos()
        # 获取包含鼠标的屏幕
        if current_screen := QApplication.screenAt(cursor_pos):
            # 获取屏幕几何信息
            screen_geometry = current_screen.geometry()
            # 计算窗口在屏幕上的居中位置
            window_x = (
                screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
            )
            window_y = (
                screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
            )
            # 移动窗口到计算出的位置
            self.move(window_x, window_y)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 添加信号处理，确保程序能够强制退出
    import signal
    import os
    def signal_handler(signum, frame):
        print(f"收到信号 {signum}，强制退出程序")
        try:
            # 强制退出所有线程
            import threading
            for thread in threading.enumerate():
                if thread != threading.current_thread():
                    print(f"强制终止线程: {thread.name}")
                    # 注意：在Windows上terminate()可能不可用
                    try:
                        if hasattr(thread, 'terminate'):
                            thread.terminate()
                    except:
                        pass
            # 强制退出程序
            os._exit(0)
        except Exception as e:
            print(f"强制退出时出错: {str(e)}")
            os._exit(1)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    try:
        wall = VideoWall()
        wall.show()
        # video_paths = [
        # r"D:\o19\image\0616\0616 O19国际二供FT1原图\0616 O19国际二供FT1原图\Video\N12\4-VID_20250616_144723.mp4",
        # r"D:\o19\image\0616\0616 O19国际二供FT1原图\0616 O19国际二供FT1原图\Video\N12\6-VID_20250616_144918.mp4",
        # r"D:\o19\image\0616\0616 O19国际二供FT1原图\0616 O19国际二供FT1原图\Video\N12\10-VID_20250616_145854.mp4"
        # ]
        # wall.add_video_list(video_paths)
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("收到键盘中断，退出程序")
        sys.exit(0)
    except Exception as e:
        print(f"程序运行时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

