import os
import time
import json
import shutil
import hashlib
from io import BytesIO
from functools import lru_cache
from typing import Optional, Tuple

# 三方库
import cv2  
from PIL import Image
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import (QIcon, QPixmap,QImageReader,QImage)


"""设置本项目的入口路径,全局变量BASEICONPATH"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BASEICONPATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BASEICONPATH = os.path.dirname(os.path.abspath(sys.argv[0]))  

class IconCache:
    """图标缓存类"""
    _cache = {}
    _cache_dir = os.path.join(BASEICONPATH, "cache", "icons")
    _cache_index_file = os.path.join(_cache_dir, "icon_index.json")
    _max_cache_size = 1000  # 最大缓存数量，超过会删除最旧的缓存
    # 视频文件格式
    VIDEO_FORMATS = ('.mp4', '.avi', '.mov', '.wmv', '.mpeg', '.mpg', '.mkv')
    # 图片文件格式
    IMAGE_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.ico', '.webp')
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
            if os.path.exists(cache_path):
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
            # show_message_box(f"get_icon获取图标失败: {e}", "提示", 1500)
            return QIcon()

    # 在_get_cache_path方法中添加文件修改时间校验
    @classmethod
    def _get_cache_path(cls, file_path):
        file_stat = os.stat(file_path)
        file_hash = hashlib.md5(f"{file_path}-{file_stat.st_mtime}".encode()).hexdigest()
        return os.path.join(cls._cache_dir, f"{file_hash}.png")

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
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # 视频文件处理
            if file_ext in cls.VIDEO_FORMATS:
                return cls.get_video_thumbnail(file_path)
            
            # 图片文件处理
            elif file_ext in cls.IMAGE_FORMATS:
                return cls._generate_image_icon(file_path)
    
            # 其它文件类型
            else:
                """特殊文件类型处理"""
                return cls.get_default_icon(cls.FILE_TYPE_ICONS.get(file_ext, "default_icon.png"), (48, 48))

        except Exception as e:
            print(f"生成图标失败: {e}")
            # show_message_box(f"_generate_icon生成图标失败: {e}", "提示", 1500)
            return cls.get_default_icon("default_icon.png", (48, 48))


    @classmethod
    def _generate_image_icon(cls, file_path):
        """优化后的图片图标生成"""
        try:

            if False:
                # 方案一：考虑到图片EXIF原始信息标记旋转的方案。现弃用，使用不考虑旋转信息的高效方案二
                with Image.open(file_path) as img:
                    image_format  = img.format

                # 单独加载TIFF格式图片, 处理该格式文件会增加程序耗时
                if image_format == "TIFF":
                    return cls._generate_fallback_icon(file_path)  
                            
                # 使用QImageReader进行高效加载
                reader = QImageReader(file_path)
                reader.setScaledSize(QtCore.QSize(48, 48))
                reader.setAutoTransform(True)
                image = reader.read()
                pixmap = QPixmap.fromImage(image)

            if True:
                # 方案二：不考虑旋转信息,使用QImage直接加载图像
                image = QImage(file_path)
                if image.isNull():
                    raise ValueError("无法加载图像")

                # 缩放图像
                pixmap = QPixmap.fromImage(image.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
           
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"高效生成图标失败: {e}")
            # show_message_box(f"_generate_image_icon生成图标失败: {e}", "提示", 1500)
            return cls.get_default_icon("image_icon.png", (48, 48))

    @classmethod
    def _generate_fallback_icon(cls, file_path):
        """备用的高质量生成方式"""
        try:
            # 使用PIL进行渐进式加载
            with Image.open(file_path) as img:
                img.thumbnail((48, 48))
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                
                # 转换为QPixmap并缩放
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
                return QIcon(pixmap)
        except Exception as e:
            print(f"备用图标生成失败: {e}")
            # show_message_box(f"_generate_fallback_icon图标生成失败: {e}", "提示", 1500)
            return cls.get_default_icon("default_icon.png", (48, 48))


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
            default_icon_path = os.path.join(BASEICONPATH, icon_path)
            
            # 检查图标文件是否存在
            if os.path.exists(default_icon_path):
                try:
                    cls._default_icon = QIcon(default_icon_path)
                    if cls._default_icon.isNull():
                        raise ValueError("无法加载图标文件")
                except Exception as e:
                    print(f"加载图标文件失败: {str(e)}")
                    # 创建备用图标
                    cls._default_icon = cls._create_fallback_icon()
            else:
                print(f"图标文件不存在: {default_icon_path}")
                cls._default_icon = cls._create_fallback_icon()
                
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
        cap = None
        try:
            # 尝试打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
                
            # 读取第一帧
            # 设置超时机制
            start_time = time.time()
            while time.time() - start_time < 2:  # 最多等待2秒
                ret, frame = cap.read()
                if ret:
                    break
            cap.release()
            
            if not ret:
                return None
                
            # 转换颜色空间从 BGR 到 RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 创建 QImage
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            q_img = QtGui.QImage(frame.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
            
            # 创建并缩放 QPixmap
            pixmap = QPixmap.fromImage(q_img)
            pixmap = pixmap.scaled(size[0], size[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"获取视频缩略图失败 {video_path}: {str(e)}")
            # show_message_box(f"get_video_thumbnails获取视频缩略图失败{os.path.basename(video_path)}: {str(e)}", "提示", 1500)
            return cls.get_default_icon("video_icon.png", (48, 48))
        finally:
            # 确保资源释放
            if cap is not None:
                cap.release()  

    @classmethod
    def _save_to_cache(cls, file_path, icon):
        """保存图标到缓存"""
        try:
            # 确保缓存目录存在
            os.makedirs(cls._cache_dir, exist_ok=True)

            # 保存图标
            cache_path = cls._get_cache_path(file_path)
            icon.pixmap(48, 48).save(cache_path, "PNG")

            # 更新索引文件
            cls._update_cache_index(file_path)

        except Exception as e:
            print(f"保存图标缓存失败: {e}")
            # show_message_box(f"_save_to_cache保存图标缓存失败: {e}", "提示", 1500)
            
    @classmethod
    def _update_cache_index(cls, file_path):
        """更新缓存索引"""
        try:
            # 读取现有索引
            index = {}
            if os.path.exists(cls._cache_index_file):
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
            if os.path.exists(cls._cache_dir):
                shutil.rmtree(cls._cache_dir)
            if os.path.exists(cls._cache_index_file):
                os.remove(cls._cache_index_file)

        except Exception as e:
            print(f"清理缓存失败: {e}")
            # show_message_box(f"clear_cache清理缓存失败: {e}", "提示", 1500)
        
