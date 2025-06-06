# -*- coding: utf-8 -*-
import os
import time
import json
import shutil
import hashlib
import threading
from pathlib import Path
from functools import lru_cache
from typing import Optional, Tuple

# 三方库
from PIL import Image
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import (QIcon, QPixmap,QImageReader,QImage)
from PyQt5.QtCore import (QRunnable, QObject, pyqtSignal)

# 自定义模块
from src.utils.heic import extract_jpg_from_heic
from src.utils.video import extract_first_frame_from_video
from src.view.sub_compare_image_view import pil_to_pixmap


"""设置本项目的入口路径,全局变量BASEICONPATH"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BASEICONPATH = Path(__file__).parent.parent.parent
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BASEICONPATH = Path(sys.argv[0]).resolve().parent


class WorkerSignals(QObject):
    """工作线程信号类"""
    finished = pyqtSignal()           # 完成信号
    progress = pyqtSignal(int, int)   # 进度信号 (当前, 总数)
    error = pyqtSignal(str)           # 错误信号
    batch_loaded = pyqtSignal(list)   # 批量加载完成信号


class ImagePreloader(QRunnable):
    """改进的图片预加载工作线程"""
    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.signals = WorkerSignals()
        self._pause = False
        self._stop = False
        self._pause_condition = threading.Event()
        self._pause_condition.set()  # 初始状态为未暂停
        
    def pause(self):
        """暂停预加载"""
        self._pause = True
        self._pause_condition.clear()

    def resume(self):
        """恢复预加载"""
        self._pause = False
        self._pause_condition.set()
        
    def run(self):
        try:
            total = len(self.file_paths)
            batch = []
            batch_size = 10
            
            for i, file_path in enumerate(self.file_paths):
                if self._stop:
                    break
                    
                # 使用 Event 来实现暂停
                self._pause_condition.wait()
                    
                if file_path:
                    icon = IconCache.get_icon(file_path)  # 使用缓存系统获取图标
                    batch.append((file_path, icon))
                    
                    if len(batch) >= batch_size:
                        self.signals.batch_loaded.emit(batch)
                        batch = []
                        
                    self.signals.progress.emit(i + 1, total)
                    
            if batch:  # 发送最后的批次
                self.signals.batch_loaded.emit(batch)
                
            self.signals.finished.emit()
            
        except Exception as e:
            self.signals.error.emit(str(e))


class IconCache:
    """图标缓存类"""
    _cache = {}
    _cache_base_dir = BASEICONPATH / "cache"
    _cache_dir = BASEICONPATH / "cache" / "icons"
    _cache_index_file = BASEICONPATH / "cache" / "icons.json"
    _max_cache_size = 1000  # 最大缓存数量，超过会删除最旧的缓存
    # 视频文件格式
    VIDEO_FORMATS = ('.mp4', '.avi', '.mov', '.wmv', '.mpeg', '.mpg', '.mkv') 
    # 图片文件格式
    IMAGE_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.ico', '.webp', '.heic')
    # 其他文件格式类型图标维护
    FILE_TYPE_ICONS = {
    '.txt': "text_icon.png",
    '.py': "default_py_icon.png",
    }

    @classmethod
    @lru_cache(maxsize=_max_cache_size) # 使用LRU缓存策略替代简单的时间戳排序,该策略如何手动清除缓存？使用cls.get_icon.cache_clear()
    def get_icon(cls, file_path):
        """获取图标，优先从缓存获取"""
        try:
            # 检查内存缓存
            if file_path in cls._cache:
                # print("获取图标, 进入读缓存")
                return cls._cache[file_path]

            # 检查文件缓存
            cache_path = cls._get_cache_path(file_path)
            if Path(cache_path).exists():
                # print("获取图标, 进入文件缓存")
                icon = QIcon(cache_path)
                cls._cache[file_path] = icon
                return icon

            # 生成新图标 
            icon = cls._generate_icon(file_path)
            if icon:
                # print("获取图标, 进入生成新图标")
                cls._cache[file_path] = icon
                cls._save_to_cache(file_path, icon)
            
            return icon

        except Exception as e:
            print(f"获取图标失败: {e}")
            return QIcon()

    # 在_get_cache_path方法中添加文件修改时间校验
    @classmethod
    def _get_cache_path(cls, file_path):
        file_stat = os.stat(file_path)
        file_hash = hashlib.md5(f"{file_path}-{file_stat.st_mtime}".encode()).hexdigest()
        return str(cls._cache_dir / f"{file_hash}.png")

    @classmethod
    def _generate_icon(cls, file_path):
        """生成图标，确保正确处理图片旋转和视频缩略图
        
        Args:
            file_path: 文件路径
            
        Returns:
            QIcon: 处理后的图标对象
        """
        try:
            # 获取文件类型，提取后缀
            file_ext = Path(file_path).suffix.lower()
            
            # 视频文件处理
            if file_ext in cls.VIDEO_FORMATS:
                return cls.get_video_thumbnail(file_path)
            
            # 图片文件处理
            elif file_ext in cls.IMAGE_FORMATS:
                # HEIC文件处理,自动转换为jpg格式
                if file_ext == ".heic":
                    if new_path:= extract_jpg_from_heic(file_path):
                        file_path = new_path
                
                return cls._generate_image_icon(file_path)
            
            # 其它文件类型
            else:
                """特殊文件类型处理"""
                return cls.get_default_icon(cls.FILE_TYPE_ICONS.get(file_ext, "default_icon.png"), (48, 48))

        except Exception as e:
            print(f"生成图标失败: {e}")
            return cls.get_default_icon("default_icon.png", (48, 48))


    @classmethod
    def _generate_image_icon(cls, file_path):
        """
        该函数主要是实现了高效生成文件图标的功能.
        Args:
            file_path (str): 传入文件绝对路径.
        Returns:
            QIcon: 处理后的图标对象
        """
        try:
            # 方案一：使用QImageReader高效加载
            reader = QImageReader(file_path)
            reader.setAutoTransform(True)     # 设置自动转换（处理EXIF方向信息）
            reader.setQuality(100)            # 设置高质量缩放
            
            # 直接设置目标尺寸，QImageReader会自动处理等比例缩放，会导致图像比例失调，移除
            # reader.setScaledSize(QtCore.QSize(48, 48))

            if True:
                # 设置高效缩放，获取原始图像尺寸
                original_size = reader.size()
                if original_size.isValid():
                    # 计算等比例缩放尺寸
                    target_size = QtCore.QSize(48, 48)
                    # 计算缩放比例
                    width_ratio = target_size.width() / original_size.width()
                    height_ratio = target_size.height() / original_size.height()
                    scale_ratio = min(width_ratio, height_ratio)
                    
                    # 计算新的尺寸
                    new_width = int(original_size.width() * scale_ratio)
                    new_height = int(original_size.height() * scale_ratio)
                    
                    # 设置缩放尺寸
                    reader.setScaledSize(QtCore.QSize(new_width, new_height))
            
            # 尝试读取图像
            if bool(img := reader.read()):
                pixmap = QPixmap.fromImage(img)
                return QIcon(pixmap)
            
            # 方案二：使用PIL 加载，ImageOps.exif_transpose自动处理EXIF方向信息
            with Image.open(file_path) as img:
                if bool(pixmap := pil_to_pixmap(img)):
                    return QIcon(pixmap)

        except Exception as e:
            print(f"图片文件生成图标失败: {e}")
            return cls.get_default_icon("image_icon.png", (48, 48))


    @classmethod
    def get_default_icon(cls, icon_path: str, icon_size: Optional[Tuple[int, int]] = None) -> QIcon:
        """获取默认文件图标
        
        Args:
            icon_path: 图标文件路径
            icon_size: 可选的图标尺寸元组 (width, height)
            
        Returns:
            QIcon: 处理后的图标对象
        """
        try:
            # 构建默认图标路径
            default_icon_path = BASEICONPATH / "resource" / "icons" / icon_path
            
            # 检查图标文件是否存在
            if default_icon_path.exists():
                print(f"图标文件{default_icon_path}存在")
                try:
                    cls._default_icon = QIcon(default_icon_path._str)
                    if cls._default_icon.isNull():
                        raise ValueError("无法加载图标文件")
                except Exception as e:
                    print(f"加载图标文件失败: {str(e)}")
                    # 创建备用图标
                    cls._default_icon = cls._create_fallback_icon()
            else:
                print(f"图标文件不存在: {default_icon_path}")
                cls._default_icon = cls._create_fallback_icon()
                return cls._default_icon
                
            # 处理图标尺寸
            if icon_size:
                try:
                    pixmap = cls._default_icon.pixmap(QtCore.QSize(*icon_size))
                    if pixmap.isNull():
                        raise ValueError("调整图标尺寸失败")
                    return QIcon(pixmap)
                except Exception as e:
                    print(f"调整图标尺寸失败: {str(e)}")
                    return cls._default_icon
                    
            return cls._default_icon
            
        except Exception as e:
            print(f"获取默认图标时发生错误: {str(e)}")
            return cls._create_fallback_icon()

    @classmethod
    def _create_fallback_icon(cls) -> QIcon:
        """创建备用图标
        
        Returns:
            QIcon: 灰色背景的备用图标
        """
        try:
            pixmap = QPixmap(48, 48)
            pixmap.fill(QtCore.Qt.gray)
            return QIcon(pixmap)
        except Exception as e:
            print(f"创建备用图标失败: {str(e)}")
            # 返回空图标作为最后的备选方案
            return QIcon()

    @classmethod
    def get_video_thumbnail(cls, video_path: str, size: Tuple[int, int] = (48, 48)):
        """获取视频的第一帧作为缩略图
        
        Args:
            video_path: 视频文件路径
            size: 缩略图大小
            
        Returns:
            QPixmap: 视频缩略图，失败返回None
        """

        try:
            # 使用extract_first_frame_from_video()获取视频首帧，若失败则返回None
            frame = extract_first_frame_from_video(video_path)
            if frame is None:
                raise ValueError("无法读取视频首帧")

            # 创建 QImage
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            q_img = QtGui.QImage(frame.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
            
            # 创建并缩放 QPixmap
            pixmap = QPixmap.fromImage(q_img)
            pixmap = pixmap.scaled(size[0], size[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"get_video_thumbnail()-获取视频缩略图失败--{video_path}: {str(e)}")
            
            # 将默认图标video_icon.png替换video_preview_frame.jpg
            default_video_icon_path = BASEICONPATH / "resource" / "icons" / "video_icon.png"
            video_preview_frame_path = BASEICONPATH / "cache" / "videos" / "video_preview_frame.jpg"
            video_preview_frame_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(default_video_icon_path, video_preview_frame_path)

            # 返回默认视频图标
            return cls.get_default_icon("video_icon.png", (48, 48))


    @classmethod
    def _save_to_cache(cls, file_path, icon):
        """保存图标到缓存"""
        try:
            # 确保缓存目录存在
            cls._cache_dir.mkdir(parents=True, exist_ok=True)

            # 保存图标
            cache_path = cls._get_cache_path(file_path)
            icon.pixmap(48, 48).save(cache_path, "PNG")

            # 更新索引文件
            cls._update_cache_index(file_path)

        except Exception as e:
            print(f"保存图标缓存失败: {e}")
            
    @classmethod
    def _update_cache_index(cls, file_path):
        """更新缓存索引"""
        try:
            # 读取现有索引
            index = {}
            if cls._cache_index_file.exists():
                with open(cls._cache_index_file, 'r', encoding='utf-8', errors='ignore') as f:
                    index = json.load(f)

            # 更新索引
            cache_path = cls._get_cache_path(file_path)
            index[cache_path] = {
                'original_path': file_path,
                'timestamp': time.time()
            }

            # 保存索引
            with open(cls._cache_index_file, 'w', encoding='utf-8', errors='ignore') as f:
                json.dump(index, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"更新缓存索引失败: {e}")

    @classmethod
    def clear_cache(cls):
        """清理本地中的缓存"""
        try:
            # 清除lru_cache的缓存
            cls.get_icon.cache_clear()  

            # 清理内存缓存
            cls._cache.clear()

            # 清理文件缓存
            if cls._cache_base_dir.exists():
                shutil.rmtree(cls._cache_base_dir)

        except Exception as e:
            print(f"清理缓存失败: {e}")
            
        
