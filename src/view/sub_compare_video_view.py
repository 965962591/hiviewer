# -*- coding: utf-8 -*-
"""导入python内置模块"""
import os
import sys
import time
import json
import pathlib
import threading

"""导入python第三方模块"""
import cv2
from cv2 import VideoCapture
import numpy as np
from PyQt5.QtGui import QImage, QPixmap, QCursor, QKeySequence, QIcon, QMovie, QKeySequence
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QMenu,
    QHBoxLayout, QVBoxLayout, QSlider, QFileDialog, QAction, QShortcut,
    QSpinBox, QScrollArea, QSizePolicy, QDoubleSpinBox, QGridLayout, QMessageBox)

"""导入自定义模块"""
from src.common.font_manager import SingleFontManager 
from src.common.settings_ColorAndExif import load_color_settings 

"""设置本项目的入口路径,全局变量BasePath"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))  


""""自定义类"""
class FrameFinderThread(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, baseline_video_path, target_video_paths, frame_num):
        super().__init__()
        self.baseline_video_path = baseline_video_path
        self.target_video_paths = target_video_paths
        self.frame_num = frame_num

    def run(self):
        try:
            # 打开基准视频
            baseline_cap = cv2.VideoCapture(self.baseline_video_path)
            if not baseline_cap.isOpened():
                self.error_occurred.emit(f"无法打开基准视频: {self.baseline_video_path}")
                return

            # 获取基准视频的总帧数
            total_frames = int(baseline_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if self.frame_num >= total_frames:
                self.error_occurred.emit(f"指定的帧数 {self.frame_num} 超出视频总帧数 {total_frames}")
                baseline_cap.release()
                return

            # 读取基准视频的目标帧
            baseline_frame = self.safe_read_frame(baseline_cap, self.frame_num)
            if baseline_frame is None:
                self.error_occurred.emit(f"无法读取基准视频的帧 {self.frame_num} 帧")
                baseline_cap.release()
                return

            # 转换为灰度图，提取特征
            baseline_gray = cv2.cvtColor(baseline_frame, cv2.COLOR_BGR2GRAY)
            baseline_cap.release()

            # 为每个目标视频找到最佳匹配帧
            best_frame_indices = {}
            for target_path in self.target_video_paths:
                try:
                    # 跳过基准视频自身
                    if target_path == self.baseline_video_path:
                        continue

                    # 打开目标视频
                    target_cap = cv2.VideoCapture(target_path)
                    if not target_cap.isOpened():
                        print(f"无法打开目标视频: {target_path}")
                        continue

                    total_frames = int(target_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    best_match_index, best_match_score = self.find_best_match(
                        target_cap, baseline_gray, total_frames
                    )

                    target_cap.release()

                    if best_match_index != -1:
                        best_frame_indices[target_path] = best_match_index
                except Exception as e:
                    print(f"处理视频 {target_path} 时出错: {str(e)}")
                    continue

            self.result_ready.emit(best_frame_indices)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def safe_read_frame(self, cap, frame_index):
        """安全读取指定帧，使用多种方法尝试"""
        try:
            # 方法1：使用set() + read()
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            if ret:
                return frame
                
            # 方法2：重新打开视频，逐帧读取
            cap.release()
            cap = cv2.VideoCapture(self.baseline_video_path)
            current_frame = 0
            while current_frame < frame_index:
                ret, _ = cap.read()
                if not ret:
                    return None
                current_frame += 1
            
            ret, frame = cap.read()
            return frame if ret else None
            
        except Exception as e:
            print(f"安全读取帧失败: {str(e)}")
            return None

    def find_best_match(self, cap, baseline_gray, total_frames):
        """在目标视频中查找与基准帧最相似的帧"""
        best_score = float("inf")  # 较小的差异值表示更好的匹配
        best_index = -1
        
        # 逐帧采样策略，避免处理过多帧
        sample_step = max(1, total_frames // 100)  # 最多采样100帧
        
        for i in range(0, total_frames, sample_step):
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # 转换为灰度并计算差异
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 确保尺寸匹配
                if gray.shape != baseline_gray.shape:
                    gray = cv2.resize(
                        gray, (baseline_gray.shape[1], baseline_gray.shape[0])
                    )

                # 使用平均绝对差异(MAD)来比较相似度
                diff = cv2.absdiff(gray, baseline_gray)
                score = np.mean(diff)
                
                if score < best_score:
                    best_score = score
                    best_index = i
                    
            except Exception as e:
                print(f"比较帧 {i} 时出错: {str(e)}")
                continue
                
        return best_index, best_score

class FrameReader(QThread):
    frame_ready = pyqtSignal(int, object, int)  # 添加信号: 帧号, 帧数据, 时间戳
    
    def __init__(self, video_path, max_queue_size=30):
        super().__init__()
        self.video_path = video_path
        self.max_queue_size = max_queue_size
        self.running = True
        self.paused = False
        self.lock = threading.Lock()
        self.last_emit_time = time.time()  # 添加上次发射信号的时间
        self.playback_speed = 1.0  # 添加播放速度变量
        
        # 尝试不同的后端打开视频
        self.cap = None
        self.open_with_backends()
        
        if not self.cap or not self.cap.isOpened():
            raise Exception(f"无法打开视频: {video_path}")
            
        self.current_frame_number = 0
        self.current_time_ms = 0
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_time = 1000 / self.fps if self.fps > 0 else 33.33
        print(f"视频帧率: {self.fps}, 每帧时长: {self.frame_time}ms")
        
        # 预读一帧确认格式
        ret, test_frame = self.cap.read()
        if ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置到开始
            print(
                f"视频 {video_path} 打开成功，分辨率: {test_frame.shape[1]}x{test_frame.shape[0]}"
            )
        else:
            raise Exception(f"无法读取视频帧: {video_path}")
    
    def open_with_backends(self):
        """尝试使用不同的后端打开视频"""
        backends = [
            cv2.CAP_FFMPEG,
            cv2.CAP_GSTREAMER,
            cv2.CAP_DSHOW,
            cv2.CAP_ANY
        ]
        
        for backend in backends:
            try:
                print(f"尝试使用后端 {backend} 打开视频 {self.video_path}")
                cap = cv2.VideoCapture(self.video_path, backend)
                if cap.isOpened():
                    self.cap = cap
                    return
                else:
                    cap.release()
            except Exception as e:
                print(f"使用后端 {backend} 打开失败: {str(e)}")
        
        # 最后尝试原始路径，不指定后端
        self.cap = cv2.VideoCapture(self.video_path)
        
    def set_playback_speed(self, speed):
        """设置播放速度"""
        self.playback_speed = speed
        print(f"帧读取器播放速度设置为: {speed}")
    
    def run(self):
        while self.running:
            if self.paused:
                time.sleep(0.01)  # 暂停时降低CPU使用
                continue
            
            # 控制帧发送频率，根据视频帧率和播放速度调整
            current_time = time.time()
            elapsed = current_time - self.last_emit_time
            target_frame_time = (
                (1.0 / self.fps) / self.playback_speed
                if self.fps > 0
                else 0.033 / self.playback_speed
            )  # 秒

            if elapsed < target_frame_time:
                # 等待直到达到正确的时间间隔再发送下一帧
                sleep_time = target_frame_time - elapsed
                time.sleep(sleep_time / 2)  # 除以2避免过度睡眠
                continue
                
            with self.lock:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame_number = int(
                        self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                    )
                    self.current_time_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
                    
                    # 记录发送时间
                    self.last_emit_time = time.time()
                    
                    # 发送信号
                    self.frame_ready.emit(
                        self.current_frame_number, frame.copy(), self.current_time_ms
                    )
                else:
                    # 视频结束时重置到开始
                    print(f"视频 {self.video_path} 播放完毕，重置到开始")
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_time_ms = 0
                    self.current_frame_number = 0
                    time.sleep(0.5)  # 添加小延迟防止立即循环
            
    def seek(self, frame_number):
        with self.lock:
            if frame_number >= 0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                self.current_frame_number = frame_number
                self.current_time_ms = int(frame_number * self.frame_time)
            
    def seek_time(self, time_ms):
        """按时间戳定位视频位置"""
        with self.lock:
            if time_ms >= 0:
                self.cap.set(cv2.CAP_PROP_POS_MSEC, time_ms)
                self.current_time_ms = time_ms
                self.current_frame_number = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            
    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        
    def stop(self):
        self.running = False
        self.wait()
        if self.cap:
            self.cap.release()

class VideoPlayer(QWidget):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        
        # 保存 VideoWall 的引用
        self.video_wall = parent  
        self.video_path = video_path

        # 初始化字体管理器
        self.font_manager = SingleFontManager.get_font(10)
        self.font_manager_small = SingleFontManager.get_font(10)
        
        try:
            # 初始化帧读取线程，使用信号槽代替队列
            self.frame_reader = FrameReader(video_path)
            self.frame_reader.frame_ready.connect(self.on_frame_ready)
            
            # 临时打开视频获取基本信息(总帧数、帧率、尺寸、时长)
            cap = cv2.VideoCapture(video_path)
            try:
                if not cap.isOpened():
                    raise ValueError(f"无法打开视频文件: {video_path}")
                # 总帧数、帧率、尺寸
                self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = cap.get(cv2.CAP_PROP_FPS)
                self.size_ = [
                    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                ]
                # 视频总时长(毫秒)
                self.duration_ms = int(self.total_frames * (1000 / self.fps)) 
            finally:
                cap.release()

            # 初始化相关组件
            self.init_ui()

            # 变量初始化
            self.is_paused = False
            self.playback_speed = 1.0
            self.rotation_angle = 0
            self.frame_skip = 0
            self.current_frame = 0
            self.current_time = 0  # 当前播放时间(毫秒)
            self.last_update_time = time.time()  # 上次更新帧的时间
            
            # 添加缩放比例属性
            self.scale_factor = 1.0
            # 添加缩放后的帧缓存
            self.scaled_frame_cache = None
            self.last_scale_factor = 1.0
            # 控制缩放质量的阈值
            self.high_quality_threshold = 2.0
            # 添加节流变量，用于控制缩放频率
            self.last_scale_time = 0
            self.scale_throttle_ms = 100  # 缩放操作间隔(毫秒)

            # 添加缓冲最新帧
            self.latest_frame = None
            self.latest_frame_number = -1
            self.latest_frame_time = 0
            
            # 标记是否处于循环播放的过渡期
            self.is_looping = False

            # 添加平移相关属性
            self.is_panning = False
            self.pan_start_pos = None
            self.pan_offset = np.array([0, 0]) # 使用numpy数组方便计算
            self.current_display_offset = np.array([0, 0])

            # 添加析构时的清理
            self.destroyed.connect(self.cleanup)
            self.is_cleaning_up = False  # 添加清理标志
            
            # 启动帧读取线程
            self.frame_reader.start()

            # 设置右键菜单
            self.menu()
            
        except Exception as e:
            QMessageBox.critical(parent, "错误", f"无法加载视频 {video_path}: {str(e)}")
            return

    def format_time(self, time_ms):
        """将毫秒时间格式化为分:秒.毫秒"""
        total_seconds = time_ms / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        ms = int((total_seconds - int(total_seconds)) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{ms:03d}"

    def on_frame_ready(self, frame_number, frame, time_ms):
        """当帧准备好时，显示它并更新状态"""
        try:
            if frame is None:
                return
                
            # 更新缓存的最新帧
            self.latest_frame = frame
            self.latest_frame_number = frame_number
            self.latest_frame_time = time_ms
                
            # 更新当前帧和时间
            self.current_frame = frame_number
            self.current_time = time_ms
                
            # 更新进度条位置（基于时间）
            if self.duration_ms > 0:
                progress = (time_ms / self.duration_ms) * 100
                self.slider.setValue(int(progress))
                
            # 应用旋转
            if self.rotation_angle != 0:
                frame = self.rotate_image(frame, self.rotation_angle)

            # 清除缩放缓存，因为有新帧
            self.scaled_frame_cache = None
            
            # 显示帧
            self.display_frame(frame)
                
            # 更新时间和帧信息显示
            current_time_str = self.format_time(time_ms)
            total_time_str = self.format_time(self.duration_ms)
            info_text = f"帧: {frame_number}/{self.total_frames} 时间: {current_time_str}/{total_time_str}"
            self.info_label.setText(info_text)
                
        except Exception as e:
            print(f"处理帧时出错: {str(e)}")

    def cleanup(self):
        """清理资源"""
        self.is_cleaning_up = True  # 设置清理标志
        if hasattr(self, 'frame_reader'):
            self.frame_reader.stop()

    def menu(self):
        """添加右键菜单函数"""
        # 添加右键菜单支持
        self.video_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_label.customContextMenuRequested.connect(self.show_context_menu)
        
        # 创建右键菜单
        self.context_menu = QMenu(self)

        # 设置菜单样式
        self.context_menu.setStyleSheet(f"""
            QMenu {{
                /*background-color: #F0F0F0;   背景色 */

                font-family: "{self.font_manager.family()}";
                font-size: {self.font_manager.pointSize()}pt;    
            }}
            QMenu::item:selected {{
                background-color: {self.background_color_default};   /* 选中项背景色 */
                color: #000000;               /* 选中项字体颜色 */
            }}
        """)
        
        # 添加保存当前帧动作
        save_frame_action = QAction("保存视频当前帧", self)
        save_frame_action.triggered.connect(self.save_current_frame)
        self.context_menu.addAction(save_frame_action)

        # 添加保存所有视频当前帧动作
        save_all_frames_action = QAction("保存所有视频当前帧", self)
        save_all_frames_action.triggered.connect(self.save_all_current_frames)  # 新增的动作
        self.context_menu.addAction(save_all_frames_action)  # 添加到菜单
        
        # 添加重命名动作
        rename_action = QAction("退出当前界面", self)
        rename_action.triggered.connect(self.close_video)
        self.context_menu.addAction(rename_action)
        
    def show_context_menu(self, pos):
        """显示右键菜单"""
        # 将 QLabel 的局部坐标转换为全局坐标
        global_pos = self.video_label.mapToGlobal(pos)
        self.context_menu.exec_(global_pos)

    def save_current_frame(self):
        """保存当前帧为PNG图片"""
        try:
            if self.latest_frame is not None:
                # 获取视频文件名（不含扩展名）
                base_name = os.path.splitext(os.path.basename(self.video_path))[0]
                dir_name = os.path.basename(os.path.dirname(self.video_path))
                # 生成默认文件名
                default_name = f"{dir_name}_{base_name}_frame_{self.current_frame}.png"
                
                # 打开文件保存对话框,支持选择保存位置
                if False:
                    file_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "保存当前帧",
                        default_name,
                        "PNG图片 (*.png)"
                    )

                if True:
                    # 直接设置默认保存到当前视频文件的父目录下  
                    file_path = pathlib.Path(self.video_path).parent / default_name
                    file_path = str(file_path.resolve())

                if file_path:
                    # 确保文件扩展名为.png
                    if not file_path.lower().endswith('.png'):
                        file_path += '.png'
                    
                    # 保存图片，cv2.imwrite不支持中文路径，
                    # cv2.imwrite(file_path, self.latest_frame)

                    # 方案1：使用 imencode() 和 tofile()
                    img_encode = cv2.imencode('.png', self.latest_frame)[1]
                    img_encode.tofile(file_path)

                    # 方案2：将OpenCV的BGR格式转换为RGB格式
                    # rgb_frame = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
                    # 使用PIL保存图片
                    # Image.fromarray(rgb_frame).save(file_path)

                    QMessageBox.information(self, "成功", f"当前视频帧：{default_name}\n已成功保存到对应视频文件目录下")
            else:
                QMessageBox.warning(self, "错误", "没有可用的视频帧")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存帧时出错: {str(e)}")

    def save_all_current_frames(self):
        """保存所有视频的当前帧为PNG图片"""
        try:
            if not self.is_paused:
                QMessageBox.information(self, "提示", "请先按下Q暂停所有视频, 确定当前帧后保存")
                return

            for player in self.video_wall.players:
                if player.latest_frame is not None:
                    # 获取视频文件名（不含扩展名）
                    base_name = os.path.splitext(os.path.basename(player.video_path))[0]
                    dir_name = os.path.basename(os.path.dirname(player.video_path))
                    # 生成默认文件名
                    default_name = f"{dir_name}_{base_name}_frame_{player.current_frame}.png"
                    
                    # 直接设置默认保存到当前视频文件的父目录下  
                    file_path = pathlib.Path(player.video_path).parent / default_name
                    file_path = str(file_path.resolve())

                    # 确保文件扩展名为.png
                    if not file_path.lower().endswith('.png'):
                        file_path += '.png'
                    
                    # 保存图片
                    try:
                        img_encode = cv2.imencode('.png', player.latest_frame)[1]  # 使用player的latest_frame
                        img_encode.tofile(file_path)
                    except Exception as e:
                        QMessageBox.warning(self, "警告", f"保存帧 {default_name} 时出错: {str(e)}")
                        continue  # 继续保存下一个帧

            QMessageBox.information(self, "成功", "所有视频的当前帧已成功保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存所有帧时出错: {str(e)}")

    def close_video(self):
        """退出视频界面"""
        self.video_wall.close()
        pass

    def init_ui(self):
        # 加载保存的颜色设置
        self.color_settings = load_color_settings().get("basic_color_settings")
        # 设置背景色和字体颜色，使用保存的设置或默认值
        self.background_color_default = self.color_settings.get("background_color_default", "rgb(173,216,230)")  # 深色背景色_好蓝
        self.background_color_table = self.color_settings.get("background_color_table", "rgb(127, 127, 127)")    # 表格背景色_18度灰
        self.font_color_default = self.color_settings.get("font_color_default", "rgb(0, 0, 0)")                  # 默认字体颜色_纯黑色
        self.font_color_exif = self.color_settings.get("font_color_exif", "rgb(255, 255, 255)")                  # Exif字体颜色_纯白色
        label_style_top = f"background-color: {self.background_color_default}; color: {self.font_color_default}; text-align: center;border: 2px solid rgb(127, 127, 127);"
        label_style_bottom = f"background-color: {self.background_color_default}; color: {self.font_color_default}; text-align: center; border-radius:10px;border: 2px solid rgb(127, 127, 127);"

        # 视频背景
        self.video_label = QLabel(self)
        label_style_video = f"background-color: {self.background_color_table}; text-align: center; border-radius:10px;"
        self.video_label.setStyleSheet(label_style_video)  # 设置背景色为18%灰色
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)  # 允许缩放
        self.video_label.setAlignment(Qt.AlignCenter)  # 居中对齐

        # 顶部 文件名标签
        self.filename_label = QLabel(self)
        _label_temp = f"{(os.path.basename(os.path.dirname(self.video_path))).upper()}: {os.path.basename(self.video_path)} " \
                    f"(fps:{self.fps:.2f}) ({self.size_[0]}x{self.size_[-1]})"
        self.filename_label.setText(_label_temp)
        self.filename_label.setStyleSheet(label_style_top)
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setMargin(5)
        self.filename_label.setFont(self.font_manager)

        # 底部 帧数和时间信息标签
        self.info_label = QLabel("帧: 0/0 时间: 00:00.000/00:00.000", self)
        self.info_label.setStyleSheet(label_style_bottom)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setMargin(5)
        self.info_label.setFont(self.font_manager)

        # 进度条
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self.seek_position)
        self.slider.sliderPressed.connect(self.handle_slider_pressed)

        # 控制按钮和设置
        self.play_button = QPushButton(self)
        play_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "play.ico"))
        self.play_button.setIcon(QIcon(play_icon_path))  # 设置播放图标
        self.play_button.setToolTip("播放/暂停")
        self.play_button.setStyleSheet("border: none;")  # 去掉按钮边框
        self.play_button.clicked.connect(self.play_pause)

        self.replay_button = QPushButton(self)
        replay_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "replay.ico"))
        self.replay_button.setIcon(QIcon(replay_icon_path))  # 设置重播图标
        self.replay_button.setStyleSheet("border: none;")    # 去掉按钮边框
        self.replay_button.setToolTip("重播")
        self.replay_button.clicked.connect(self.replay)

        self.speed_label = QLabel("速度:", self)
        self.speed_label.setFont(self.font_manager_small)
        self.speed_spinbox = QDoubleSpinBox(self)
        self.speed_spinbox.setRange(0.1, 10.0)
        self.speed_spinbox.setValue(1.0)
        self.speed_spinbox.setSingleStep(0.1)
        self.speed_spinbox.valueChanged.connect(self.set_speed)

        # 跳帧数量
        self.frame_skip_label = QLabel("跳帧:", self)
        self.frame_skip_label.setFont(self.font_manager_small)
        self.frame_skip_spin = QSpinBox(self)
        self.frame_skip_spin.setRange(0, self.total_frames)
        self.frame_skip_spin.setValue(0)
        self.frame_skip_spin.valueChanged.connect(self.set_frame_skip)

        # 旋转按钮
        self.rotate_left_button = QPushButton(self)
        self.rotate_left_button.setStyleSheet("border: none;")
        rotate_left_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "left.ico"))
        self.rotate_left_button.setToolTip("左转90°")
        self.rotate_left_button.setIcon(QIcon(rotate_left_icon_path))  # 设置左转图标
        self.rotate_left_button.clicked.connect(self.rotate_left)

        self.rotate_right_button = QPushButton(self)
        self.rotate_right_button.setStyleSheet("border: none;")
        rotate_right_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "right.ico"))
        self.rotate_right_button.setToolTip("右转90°")
        self.rotate_right_button.setIcon(QIcon(rotate_right_icon_path))  # 设置右转图标
        self.rotate_right_button.clicked.connect(self.rotate_right)

        # 添加 "main" 按钮
        self.main_button = QPushButton(self)
        main_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "base.ico"))
        self.main_button.setIcon(QIcon(main_icon_path))  # 设置主图标
        self.main_button.setToolTip("设置为基准视频，计算并设置其他视频的跳帧数")
        self.main_button.setStyleSheet("border: none;")
        self.main_button.clicked.connect(self.set_as_baseline)

        # 控制布局
        control_layout = QHBoxLayout()
        control_layout.addStretch()  # 添加弹性空间以实现水平居中
        control_layout.addWidget(self.speed_label)
        control_layout.addWidget(self.speed_spinbox)
        control_layout.addWidget(self.frame_skip_label)
        control_layout.addWidget(self.frame_skip_spin)
        control_layout.addWidget(self.main_button)          # 添加 "main" 按钮到布局
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.replay_button)
        control_layout.addWidget(self.rotate_left_button)   # 添加左转按钮
        control_layout.addWidget(self.rotate_right_button)  # 添加右转按钮
        control_layout.addStretch()

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.slider, stretch=1)
        bottom_layout.addLayout(control_layout, stretch=1)
        bottom_layout.addWidget(self.info_label, stretch=1)  # 添加信息标签在最下方

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.filename_label)
        main_layout.addWidget(self.video_label, stretch=1)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        self.setMinimumSize(300, 200)  # 设置最小大小，防止过小

        # 添加一个定时器以确保UI定期更新，即使没有新帧
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(16)  # 约60fps的UI刷新率

    def update_ui(self):
        """确保UI定期更新，即使没有新帧到达"""
        # 更新帧数和时间信息
        current_frame = self.current_frame
        total_frames = self.total_frames
        
        current_time_ms = self.current_time
        total_time_ms = self.duration_ms
        
        # 格式化时间
        current_time_str = self.format_time(current_time_ms)
        total_time_str = self.format_time(total_time_ms)
        
        # 更新信息标签
        info_text = f"帧: {current_frame}/{total_frames} 时间: {current_time_str}/{total_time_str}"
        self.info_label.setText(info_text)

    def display_frame(self, frame):
        if frame is None:
            return
            
        try:
            # 获取视频标签的当前大小
            label_w = self.video_label.width()
            label_h = self.video_label.height()
            frame_h_orig, frame_w_orig = frame.shape[:2]

            # 检查是否需要重新缩放
            needs_rescale = (self.scaled_frame_cache is None or 
                            abs(self.last_scale_factor - self.scale_factor) > 0.01)
            
            if needs_rescale:
                # 计算基础缩放比例，再乘以用户设置的缩放因子
                base_scale = min(
                    label_w / frame_w_orig, label_h / frame_h_orig
                )
                current_scale = base_scale * self.scale_factor
                
                # 记录当前使用的缩放因子
                self.last_scale_factor = self.scale_factor
                
                scaled_w = max(1, int(frame_w_orig * current_scale))
                scaled_h = max(1, int(frame_h_orig * current_scale))

                # 优化大尺寸图像的缩放方式
                if self.scale_factor > self.high_quality_threshold:
                    intermediate_scale = min(1.0, current_scale / 2)
                    if intermediate_scale < 1.0:
                        intermediate_w = max(1, int(frame_w_orig * intermediate_scale))
                        intermediate_h = max(1, int(frame_h_orig * intermediate_scale))
                        intermediate = cv2.resize(
                            frame, (intermediate_w, intermediate_h), 
                            interpolation=cv2.INTER_AREA
                        )
                        self.scaled_frame_cache = cv2.resize(
                            intermediate, (scaled_w, scaled_h),
                            interpolation=cv2.INTER_LINEAR
                        )
                    else:
                        self.scaled_frame_cache = cv2.resize(
                            frame, (scaled_w, scaled_h),
                            interpolation=cv2.INTER_LINEAR
                        )
                else:
                    self.scaled_frame_cache = cv2.resize(
                        frame, (scaled_w, scaled_h),
                        interpolation=cv2.INTER_AREA if current_scale < 1 else cv2.INTER_LINEAR
                    )
            
            # 使用缓存的缩放帧
            current_scaled_frame = self.scaled_frame_cache
            scaled_h, scaled_w = current_scaled_frame.shape[:2]

            # 应用平移
            display_frame = current_scaled_frame
            if self.scale_factor > 1.0: # 仅当放大时才应用平移
                # 创建一个和标签一样大的黑色背景
                output_frame = np.zeros((label_h, label_w, 3), dtype=np.uint8)
                
                # 计算实际用于裁切的偏移量 (中心对齐 + 用户拖动偏移)
                center_offset_x = max(0, (scaled_w - label_w) // 2)
                center_offset_y = max(0, (scaled_h - label_h) // 2)

                # 实际裁切的起点，考虑用户拖动
                start_x = int(max(0, center_offset_x - self.pan_offset[0]))
                start_y = int(max(0, center_offset_y - self.pan_offset[1]))

                # 确保裁切区域不超出缩放后图像的边界
                start_x = min(start_x, max(0, scaled_w - label_w))
                start_y = min(start_y, max(0, scaled_h - label_h))
                
                # 计算实际可用的宽度和高度
                available_w = min(label_w, scaled_w - start_x)
                available_h = min(label_h, scaled_h - start_y)
                
                if available_w > 0 and available_h > 0:
                    # 从缩放后的图像中裁切出要显示的部分
                    cropped = current_scaled_frame[start_y:start_y+available_h, start_x:start_x+available_w]
                    
                    # 计算在输出帧中的位置（居中）
                    paste_x = (label_w - available_w) // 2
                    paste_y = (label_h - available_h) // 2
                    
                    # 将裁切的部分粘贴到输出帧上
                    output_frame[paste_y:paste_y+available_h, paste_x:paste_x+available_w] = cropped
                
                display_frame = output_frame
            else:
                # 如果没有放大，或者缩小了，则居中显示
                self.pan_offset = np.array([0,0])
                
                # 创建一个和标签一样大的黑色背景
                output_frame = np.zeros((label_h, label_w, 3), dtype=np.uint8)
                
                # 计算粘贴位置，使其居中
                paste_x = max(0, (label_w - scaled_w) // 2)
                paste_y = max(0, (label_h - scaled_h) // 2)
                
                # 确保不会越界
                paste_w = min(scaled_w, label_w - paste_x)
                paste_h = min(scaled_h, label_h - paste_y)
                
                if paste_w > 0 and paste_h > 0:
                    output_frame[paste_y:paste_y+paste_h, paste_x:paste_x+paste_w] = \
                        current_scaled_frame[0:paste_h, 0:paste_w]
                
                display_frame = output_frame

            # 使用 RGB 格式处理图像
            if len(display_frame.shape) == 3:
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                height, width, channel = rgb_frame.shape
                bytes_per_line = 3 * width
                q_img = QImage(
                    rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888
                )
            else:
                height, width = display_frame.shape
                q_img = QImage(
                    display_frame.data, width, height, width, QImage.Format_Grayscale8
                )

            pixmap = QPixmap.fromImage(q_img)
            self.video_label.setPixmap(pixmap)
        except Exception as e:
            print(f"显示帧时出错: {str(e)}")

    def play_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.frame_reader.resume()
            self.last_update_time = time.time()  # 重置时间基准
            play_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "play.ico"))
            self.play_button.setIcon(QIcon(play_icon_path))
        else:
            self.is_paused = True
            self.frame_reader.pause()
            pause_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "pause.ico"))
            self.play_button.setIcon(QIcon(pause_icon_path))

    def replay(self):
        self.current_time = 0
        self.current_frame = 0
        self.frame_reader.seek_time(0)
        self.slider.setValue(0)
        
        if self.is_paused:
            self.play_pause()  # 如果是暂停状态，切换为播放

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
        # 根据百分比计算目标时间
        target_time = int((position / 100) * self.duration_ms)
        self.current_time = target_time
        self.frame_reader.seek_time(target_time)
        self.last_update_time = time.time()  # 重置时间基准

    def handle_slider_pressed(self):
        # 获取鼠标点击的位置
        mouse_pos = self.slider.mapFromGlobal(QCursor.pos()).x()
        # 计算点击位置对应的滑块值
        slider_value = int((mouse_pos / self.slider.width()) * self.slider.maximum())
        # 设置滑块的位置
        self.slider.setValue(slider_value)
        # 调用 seek_position 方法并传递位置
        self.seek_position(slider_value)

    def rotate_image(self, image, angle):
        if angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    def set_as_baseline(self):
        # 创建一个 QWidget 作为容器
        self.progress_widget = QWidget(self.video_wall)
        
        # 创建 QLabel 用于显示 GIF
        self.progress_label = QLabel(self.progress_widget)
        # 路径
        gif_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "ncat.gif"))
        self.movie = QMovie(gif_path)
        
        # 设置GIF显示大小
        self.progress_label.setFixedSize(200, 50)
        self.progress_label.setMovie(self.movie)
        # 设置GIF填充模式
        self.movie.setScaledSize(self.progress_label.size())
        
        # 创建 QLabel 用于显示文字
        self.text_label = QLabel("正在检索相似帧...", self.progress_widget)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet(
            "color: white; font-weight: bold;"
        )  # 设置文字颜色为白色并加粗

        # 创建布局并添加 GIF 和文字
        layout = QVBoxLayout(self.progress_widget)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.text_label)
        
        # 设置容器大小策略
        self.progress_widget.setFixedSize(220, 100)  # 调整大小以适应内容
        
        # 将容器固定在程序窗口正中心
        center_x = (self.video_wall.width() - self.progress_widget.width()) // 2
        center_y = (self.video_wall.height() - self.progress_widget.height()) // 2
        self.progress_widget.move(center_x, center_y)
        
        self.progress_widget.show()
        self.movie.start()

        # 使用保存的 VideoWall 引用
        if hasattr(self.video_wall, "players"):
            all_video_paths = [player.video_path for player in self.video_wall.players]
        else:
            QMessageBox.warning(self, "错误", "无法找到 VideoWall 的实例")
            self.progress_widget.close()  # 关闭 GIF
            return

        # 设置基准视频路径
        baseline_video_path = self.video_path
        # 设置目标视频路径
        target_video_paths = [
            path for path in all_video_paths if path != baseline_video_path
        ]

        # 获取基准视频的跳帧数值
        frame_num = self.frame_skip_spin.value()
        if frame_num == 0:
            frame_num += 1  # 如果为0，则加1

        # 创建并启动线程
        self.frame_finder_thread = FrameFinderThread(
            baseline_video_path, target_video_paths, frame_num
        )
        self.frame_finder_thread.result_ready.connect(self.on_frame_indices_ready)
        self.frame_finder_thread.error_occurred.connect(self.on_frame_indices_error)
        self.frame_finder_thread.start()

    def on_frame_indices_ready(self, best_frame_indices):
        # 关闭 GIF
        self.progress_widget.close()
        
        # 遍历所有播放器并设置跳帧数
        for player in self.video_wall.players:
            if player.video_path in best_frame_indices:
                frame_index = best_frame_indices[player.video_path]
                print(f"设置 {player.video_path} 的跳帧为 {frame_index}")
                player.frame_skip_spin.setValue(frame_index)
                player.set_frame_skip(frame_index)  # 确保更新视频到指定帧

        # 调用一下jump_to_frame_all_videos函数
        self.video_wall.jump_to_frame_all_videos()

    def on_frame_indices_error(self, error_message):
        QMessageBox.critical(self, "错误", f"查找相似帧时发生错误: {error_message}")
        self.progress_widget.close()  # 关闭 GIF

    def rotate_left(self):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.update_ui()

    def rotate_right(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.update_ui()

    # 添加鼠标滚轮事件处理函数
    def wheelEvent(self, event):
        # 获取当前时间，用于节流
        current_time = time.time() * 1000  # 转换为毫秒
        
        # 如果自上次缩放后没有经过足够的时间，则忽略此次滚轮事件
        if current_time - self.last_scale_time < self.scale_throttle_ms:
            event.accept()
            return
            
        # 更新上次缩放时间
        self.last_scale_time = current_time
        
        # 获取滚轮滚动的角度，正值为向上滚动（放大），负值为向下滚动（缩小）
        delta = event.angleDelta().y()
        
        # 根据滚动方向调整缩放因子
        old_scale_factor = self.scale_factor
        if delta > 0:
            # 向上滚动，放大 - 减小增量以使大比例变化更平滑
            increment = 0.1 if self.scale_factor < 3.0 else 0.05
            self.scale_factor = min(4.0, self.scale_factor + increment)  # 限制最大缩放为5倍
        else:
            # 向下滚动，缩小
            self.scale_factor = max(0.5, self.scale_factor - 0.1)
        
        # 如果缩放因子变化不大，不更新显示
        if abs(old_scale_factor - self.scale_factor) < 0.01:
            # 即使缩放因子变化不大，如果从放大变为不放大，也需要重置pan_offset
            if old_scale_factor > 1.0 and self.scale_factor <= 1.0:
                self.pan_offset = np.array([0, 0])
                # 需要刷新一下显示以移除平移
                if self.latest_frame is not None:
                    if self.rotation_angle != 0:
                        rotated_frame = self.rotate_image(self.latest_frame, self.rotation_angle)
                        self.display_frame(rotated_frame)
                    else:
                        self.display_frame(self.latest_frame)
            event.accept() # 仍然接受事件，因为VideoWall可能需要处理
            return
            
        # 如果从放大状态变为非放大状态，或者从非放大状态变为放大状态，重置pan_offset
        if (old_scale_factor > 1.0 and self.scale_factor <= 1.0) or \
           (old_scale_factor <= 1.0 and self.scale_factor > 1.0):
            self.pan_offset = np.array([0, 0])

        # 如果有最新帧，重新显示应用缩放效果
        if self.latest_frame is not None:
            if self.rotation_angle != 0:
                rotated_frame = self.rotate_image(self.latest_frame, self.rotation_angle)
                self.display_frame(rotated_frame)
            else:
                self.display_frame(self.latest_frame)
        
        # 将事件传递给父组件，以便VideoWall可以处理所有视频的缩放
        if self.video_wall:
            self.video_wall.scale_all_videos(self.scale_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.scale_factor > 1.0 and self.video_label.geometry().contains(event.pos()):
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor) # 改变鼠标样式为拖动
            event.accept()
        else:
            event.ignore() # 如果不满足条件，忽略事件，允许父组件处理

    def mouseMoveEvent(self, event):
        if self.is_panning and self.pan_start_pos is not None:
            delta = event.pos() - self.pan_start_pos
            # 更新总偏移量
            self.pan_offset += np.array([delta.x(), delta.y()])
            # 更新下一次拖动的起始点，这样拖动更平滑
            self.pan_start_pos = event.pos() 

            # 重新显示帧以应用平移
            if self.latest_frame is not None:
                if self.rotation_angle != 0:
                    rotated_frame = self.rotate_image(self.latest_frame, self.rotation_angle)
                    self.display_frame(rotated_frame)
                else:
                    self.display_frame(self.latest_frame)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_panning:
            self.is_panning = False
            self.pan_start_pos = None
            self.unsetCursor() # 恢复默认鼠标样式
            event.accept()
        else:
            event.ignore()


class VideoWall(QWidget):
    """多视频播放程序"""
    # 定义关闭信号
    closed = pyqtSignal()

    def __init__(self, video_list):
        super().__init__()
        self.setWindowTitle("多视频播放程序")
        icon_path = os.path.join(BasePath, "resource", "icons", "video_icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setAcceptDrops(True)

        self.players = []
        # 添加全局缩放因子
        self.global_scale_factor = 1.0
        # 添加节流变量，防止频繁缩放
        self.last_scale_time = 0
        self.scale_throttle_ms = 100  # 缩放操作间隔(毫秒)
		
        # 初始化相关组件
        self.init_ui()

        # 设置快捷键
        self.shortcut()

        # 初始化视频列表
        self.video_list = video_list
        if self.video_list:
            for video_path in self.video_list:
                if os.path.exists(video_path):
                    # 路径后缀转换为小写
                    video_path = video_path.lower()
                    player = VideoPlayer(video_path, parent=self)
                    self.players.append(player)
            self.refresh_layout()

        # 将窗口移动到鼠标所在的屏幕
        self.move_to_current_screen()
        self.resize(1400, 1000)
        
        # 默认全屏显示
        # self.showFullScreen()  # 添加这一行以默认全屏显示
        # 设置窗口最大化
        self.showMaximized()

        self.resize(1800, 1200)

    def shortcut(self):
        # 添加全屏快捷键
        fullscreen_shortcut = QShortcut(QKeySequence('F11'), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.is_fullscreen = False

        # 添加 D 快捷键用于清空视频
        clear_shortcut = QShortcut(QKeySequence('D'), self)
        clear_shortcut.activated.connect(self.clear_videos)

        # 修改 Q 快捷键用于播放/暂停所有视频
        play_pause_all_shortcut = QShortcut(QKeySequence('Q'), self)
        play_pause_all_shortcut.activated.connect(self.play_pause_all_videos)

        # 修改 W 快捷键用于重播所有视频
        replay_all_shortcut = QShortcut(QKeySequence('W'), self)
        replay_all_shortcut.activated.connect(self.replay_all_videos)

        # 添加 E 快捷键用于快进所有视频
        speed_up_shortcut = QShortcut(QKeySequence('E'), self)
        speed_up_shortcut.activated.connect(self.speed_up_all_videos)

        # 添加 R 快捷键用于慢放所有视频
        slow_down_shortcut = QShortcut(QKeySequence('R'), self)
        slow_down_shortcut.activated.connect(self.slow_down_all_videos)

        # 添加 T 快捷键用于从跳帧数开始播放所有视频
        jump_to_frame_shortcut = QShortcut(QKeySequence('T'), self)
        jump_to_frame_shortcut.activated.connect(self.jump_to_frame_all_videos)

        # 添加 Z 快捷键用于逐帧后退
        frame_backward_shortcut = QShortcut(QKeySequence('Z'), self)
        frame_backward_shortcut.activated.connect(self.frame_backward_all_videos)

        # 添加 X 快捷键用于逐帧前进
        frame_forward_shortcut = QShortcut(QKeySequence('X'), self)
        frame_forward_shortcut.activated.connect(self.frame_forward_all_videos)

        # 添加 ESC 快捷键用于退出程序
        exit_shortcut = QShortcut(QKeySequence('Esc'), self)
        exit_shortcut.activated.connect(self.close)
        
    # 添加鼠标滚轮事件处理函数
    def wheelEvent(self, event):
        # 获取当前时间，用于节流
        current_time = time.time() * 1000  # 转换为毫秒
        
        # 如果自上次缩放后没有经过足够的时间，则忽略此次滚轮事件
        if current_time - self.last_scale_time < self.scale_throttle_ms:
            event.accept()
            return
            
        # 更新上次缩放时间
        self.last_scale_time = current_time
        
        # 获取滚轮滚动的角度
        delta = event.angleDelta().y()
        
        # 根据滚动方向调整全局缩放因子
        old_scale_factor = self.global_scale_factor
        if delta > 0:
            # 向上滚动，放大 - 减小增量以使大比例变化更平滑
            increment = 0.1 if self.global_scale_factor < 3.0 else 0.05
            self.global_scale_factor = min(4.0, self.global_scale_factor + increment)  # 限制最大缩放为5倍
        else:
            # 向下滚动，缩小
            self.global_scale_factor = max(0.5, self.global_scale_factor - 0.1)
            
        # 如果缩放因子变化不大，不更新显示
        if abs(old_scale_factor - self.global_scale_factor) < 0.01:
            return
        
        # 对所有视频应用相同的缩放
        self.scale_all_videos(self.global_scale_factor)
        
    # 添加缩放所有视频的方法
    def scale_all_videos(self, scale_factor):
        # 更新所有播放器的缩放因子
        for player in self.players:
            if abs(player.scale_factor - scale_factor) > 0.01:
                player.scale_factor = scale_factor
                
                # 重新显示当前帧以应用新的缩放
                if player.latest_frame is not None:
                    if player.rotation_angle != 0:
                        rotated_frame = player.rotate_image(player.latest_frame, player.rotation_angle)
                        player.display_frame(rotated_frame)
                    else:
                        player.display_frame(player.latest_frame)

    def init_ui(self):
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)  # 允许滚动区域内容自动调整大小

        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)  # 将边距设为0
        self.grid_layout.setSpacing(3)  # 将间距设为0

        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)


        main_layout = QVBoxLayout()
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
        self.resize(1800, 1200)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        video_extensions = ('.mp4', '.avi', '.mkv', '.mov')
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(video_extensions):
                player = VideoPlayer(file_path, parent=self)  # 将 self 作为父级传递
                self.players.append(player)
                self.refresh_layout()
        

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

        # 动态计算每行最多显示的播放器数量
        available_width = self.scroll_area.width()  # 不再减去边距
        player_width = 300  # 每个播放器的建议宽度
        columns = max(1, available_width // player_width)

        for index, player in enumerate(self.players):
            row = index // columns
            col = index % columns
            self.grid_layout.addWidget(player, row, col)
            
            # 移除播放器内部的边距
            if hasattr(player, 'layout'):
                player.layout().setContentsMargins(0, 0, 0, 0)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            # self.showNormal()
            self.showMaximized() # 最大化
            self.is_fullscreen = False
        else:
            self.showFullScreen() # 全屏
            self.is_fullscreen = True

    def clear_videos(self):
        """清空所有视频播放器并释放资源"""
        try:
            # 先停止所有计时器和线程
            for player in self.players:
                if hasattr(player, "timer"):
                    player.timer.stop()
                if hasattr(player, "frame_reader"):
                    player.frame_reader.pause()
                    player.frame_reader.running = False
            
            # 等待所有线程结束
            for player in self.players:
                if hasattr(player, "frame_reader"):
                    player.frame_reader.wait()
            
            # 清理每个播放器的资源
            for player in self.players:
                try:
                    player.cleanup()
                    player.setParent(None)
                    player.deleteLater()
                except Exception as e:
                    print(f"清理播放器时出错: {str(e)}")
            
            # 清空播放器列表
            self.players.clear()
            
            
            # 刷新布局
            self.refresh_layout()
            
        except Exception as e:
            print(f"清空视频时发生错误: {str(e)}")

    def play_pause_all_videos(self):
        for player in self.players:
            player.play_pause()

    def replay_all_videos(self):
        for player in self.players:
            player.replay()

    def speed_up_all_videos(self):
        for player in self.players:
            new_speed = min(player.playback_speed + 0.1, 10.0)  # 限制最大速度为10.0
            player.set_speed(new_speed)
            player.speed_spinbox.setValue(new_speed)  # 同步更新spinbox的值

    def slow_down_all_videos(self):
        for player in self.players:
            new_speed = max(player.playback_speed - 0.1, 0.1)  # 限制最小速度为0.1
            player.set_speed(new_speed)
            player.speed_spinbox.setValue(new_speed)  # 同步更新spinbox的值

    def jump_to_frame_all_videos(self):
        """从每个视频的跳帧数开始播放所有视频"""
        for player in self.players:
            try:
                # 获取跳帧数
                frame_skip = player.frame_skip_spin.value()
                
                if frame_skip < player.total_frames:
                    # 将视频定位到指定帧
                    if hasattr(player, "frame_reader"):
                        # 计算帧对应的时间(毫秒)
                        time_ms = int(frame_skip * (1000 / player.fps))
                        
                        # 先暂停视频读取器
                        player.frame_reader.pause()
                        
                        # 跳转到指定时间
                        player.frame_reader.seek_time(time_ms)
                        
                        # 更新播放器状态
                        player.current_frame = frame_skip
                        player.current_time = time_ms
                        
                        # 如果视频当前是暂停状态，则恢复播放
                        if player.is_paused:
                            player.is_paused = False
                            player.last_update_time = time.time()  # 重置时间基准
                            
                            # 更新播放/暂停按钮图标
                            play_icon_path = os.path.abspath(os.path.join(BasePath, "resource", "icons", "play.ico"))   
                            player.play_button.setIcon(QIcon(play_icon_path))
                        
                        # 恢复视频读取器运行
                        player.frame_reader.resume()

                        print(
                            f"视频 {os.path.basename(player.video_path)} 跳转到帧: {frame_skip}"
                        )
            except Exception as e:
                print(f"跳转到帧时出错: {str(e)}")

    def frame_forward_all_videos(self):
        """所有视频前进一帧"""
        try:
            for player in self.players:
                if hasattr(player, 'frame_reader'):
                    # 计算下一帧的时间
                    next_frame = min(player.total_frames - 1, player.current_frame + 1)
                    
                    # 暂停视频（如果正在播放）
                    if not player.is_paused:
                        player.play_pause()
                    
                    # 使用临时的视频捕获器来准确读取帧
                    cap = cv2.VideoCapture(player.video_path)
                    
                    # 使用逐帧读取的方式获取目标帧
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    current = 0
                    frame = None
                    ret = False
                    
                    # 读取到目标帧
                    while current <= next_frame:
                        ret, temp_frame = cap.read()
                        if not ret:
                            break
                        frame = temp_frame
                        current += 1
                    
                    cap.release()
                    
                    if frame is not None:
                        # 更新播放器状态
                        player.current_frame = next_frame
                        player.current_time = int(next_frame * (1000 / player.fps))
                        
                        # 应用旋转（如果有）
                        if player.rotation_angle != 0:
                            frame = player.rotate_image(frame, player.rotation_angle)
                            
                        # 显示帧
                        player.display_frame(frame)
                        
                        # 更新进度条
                        if player.duration_ms > 0:
                            progress = (player.current_time / player.duration_ms) * 100
                            player.slider.setValue(int(progress))
                            
                        # 更新帧读取器的位置
                        player.frame_reader.seek(next_frame)
                
        except Exception as e:
            print(f"前进一帧时出错: {str(e)}")

    def frame_backward_all_videos(self):
        """所有视频后退一帧"""
        
        try:
            for player in self.players:
                if hasattr(player, 'frame_reader'):
                    # 计算上一帧的时间
                    prev_frame = max(0, player.current_frame - 1)
                    
                    # 暂停视频（如果正在播放）
                    if not player.is_paused:
                        player.play_pause()
                    
                    # 使用临时的视频捕获器来准确读取帧
                    cap = cv2.VideoCapture(player.video_path)
                    
                    # 使用逐帧读取的方式获取目标帧
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    current = 0
                    frame = None
                    ret = False
                    
                    # 读取到目标帧
                    while current <= prev_frame:
                        ret, temp_frame = cap.read()
                        if not ret:
                            break
                        frame = temp_frame
                        current += 1
                    
                    cap.release()
                    
                    if frame is not None:
                        # 更新播放器状态
                        player.current_frame = prev_frame
                        player.current_time = int(prev_frame * (1000 / player.fps))
                        
                        # 应用旋转（如果有）
                        if player.rotation_angle != 0:
                            frame = player.rotate_image(frame, player.rotation_angle)
                            
                        # 显示帧
                        player.display_frame(frame)
                        
                        # 更新进度条
                        if player.duration_ms > 0:
                            progress = (player.current_time / player.duration_ms) * 100
                            player.slider.setValue(int(progress))
                            
                        # 更新帧读取器的位置
                        player.frame_reader.seek(prev_frame)
                
        except Exception as e:
            print(f"后退一帧时出错: {str(e)}")

    def closeEvent(self, event):
        """程序关闭时的清理"""
        for player in self.players:
            player.cleanup()

        # 发射关闭信号（新增），统一在这里发送信号
        self.closed.emit()
        
        # 最后调用父类方法
        super().closeEvent(event)

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

def main():
    # 测试视频列表
    video_list = [
        'D:/Tuning/M5151/0_picture/20241121_FT/1122-C3N后置GL四供第二轮FT（小米之家+小米园区）/video/四供/VID_20241122_100543.mp4',
        'D:/Tuning/M5151/0_picture/20241121_FT/1122-C3N后置GL四供第二轮FT（小米之家+小米园区）/video/2024_11_22_15_54_IMG_4233.MOV'
    ]
    video_list1 = [
        'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/Video\\iPhone\\IMG_2484.MOV', 
        'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/Video\\14U\\VID_20241105_185158_DOLBY.mp4', 
        'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/Video\\C3N\\VID_20241105_125627.mp4', 
        'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/Video\\M19A\\VID_20241105_185056.mp4', 
        'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/Video\\一供\\VID_20241105_185012.mp4']
    video_list_info = [
        '1/1',
        '1/1',
        '1/1',
        '1/1',
        '1/1'
    ]
    
    app = QApplication(sys.argv)
    wall = VideoWall(video_list)
    wall.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
