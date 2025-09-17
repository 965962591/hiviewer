#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片压缩工具
使用PyQt5和Pyvips实现多格式图片压缩和尺寸修改
"""

import sys
import os
from pathlib import Path
import time

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QComboBox,
    QSpinBox, QCheckBox, QGroupBox, QFileDialog,
    QProgressBar, QTextEdit, QTabWidget, QSplitter,
    QHeaderView, QMenu, QAction, QToolBar,QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QSlider, QLineEdit, QGridLayout, QRadioButton, QStyledItemDelegate
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal,QSettings, QSize, QRect
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QFont, QDragEnterEvent, QDropEvent, QColor
)

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QStyle
from PIL import Image, ImageDraw, ImageFont
# 支持的图片格式 (PIL/Pillow)
SUPPORTED_FORMATS = {
    'JPEG': ['.jpg', '.jpeg'],
    'PNG': ['.png'],
    'WEBP': ['.webp'],
    'TIFF': ['.tiff', '.tif'],
    'BMP': ['.bmp'],
    'GIF': ['.gif'],
    'ICO': ['.ico'],
    'TGA': ['.tga'],
    'PSD': ['.psd'],
    'PCX': ['.pcx'],
    'XBM': ['.xbm'],
    'XPM': ['.xpm'],
    'PPM': ['.ppm', '.pgm', '.pbm'],
    'DDS': ['.dds'],
    'DIB': ['.dib'],
    'EPS': ['.eps'],
    'FLI': ['.fli', '.flc'],
    'HEIC': ['.heic', '.heif'],  # 需要 pillow-heif
    'AVIF': ['.avif'],  # 需要 pillow-avif
    'JP2': ['.jp2', '.j2k', '.jpc'],  # JPEG 2000
    'SPIDER': ['.spi'],
    'SUN': ['.ras'],
    'WAL': ['.wal']
}

# 所有支持的扩展名
ALL_EXTENSIONS = []
for exts in SUPPORTED_FORMATS.values():
    ALL_EXTENSIONS.extend(exts)


class CompressionRatioDelegate(QStyledItemDelegate):
    """压缩率可视化委托"""
    def paint(self, painter, option, index):
        # 获取压缩率数据
        ratio = index.data(Qt.UserRole)
        if ratio is None or ratio <= 0:
            # 如果没有数据，使用默认绘制
            super().paint(painter, option, index)
            return
        
        # 设置绘制区域
        rect = option.rect
        painter.save()
        
        # 绘制背景
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.fillRect(rect, option.palette.base())
            painter.setPen(option.palette.text().color())
        
        # 计算进度条区域
        bar_width = int(rect.width() * 0.6)  # 进度条占60%宽度
        bar_height = rect.height() - 4
        bar_x = rect.x() + 2
        bar_y = rect.y() + 2
        
        # 绘制进度条背景
        bg_rect = QRect(bar_x, bar_y, bar_width, bar_height)
        painter.fillRect(bg_rect, QColor(240, 240, 240))
        
        # 绘制进度条
        progress_width = int(bar_width * (ratio / 100.0))
        if progress_width > 0:
            # 根据压缩率选择颜色
            if ratio >= 50:
                color = QColor(76, 175, 80)  # 绿色 - 高压缩率
            elif ratio >= 30:
                color = QColor(255, 193, 7)  # 黄色 - 中等压缩率
            else:
                color = QColor(244, 67, 54)  # 红色 - 低压缩率
            
            progress_rect = QRect(bar_x, bar_y, progress_width, bar_height)
            painter.fillRect(progress_rect, color)
        
        # 绘制边框
        painter.setPen(QColor(200, 200, 200))
        painter.drawRect(bg_rect)
        
        # 绘制文字
        text = f"{ratio:.1f}%"
        
        # 计算文字区域
        text_x = bar_x + bar_width + 5
        text_width = rect.width() - (text_x - rect.x())
        text_height = rect.height()
        
        # 创建文字绘制区域
        text_rect = QRect(text_x, rect.y(), text_width, text_height)
        
        # 使用drawText的居中绘制
        painter.drawText(text_rect, Qt.AlignCenter, text)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        return QSize(120, 20)


class MultiThreadFormatConvertWorker(QThread):
    """多线程图片格式转换处理线程"""
    progress_updated = pyqtSignal(int, str)  # 进度, 状态信息
    file_processed = pyqtSignal(int, str, str)  # 行号, 状态, 消息
    file_stats_updated = pyqtSignal(bool, int)  # 是否成功, 转换后文件大小
    file_info_updated = pyqtSignal(int, dict)  # 行号, 文件信息更新
    thread_finished = pyqtSignal()  # 单个线程完成信号
    finished = pyqtSignal()  # 所有线程完成信号
    
    def __init__(self, files_info, settings, thread_id, total_threads):
        super().__init__()
        self.files_info = files_info
        self.settings = settings
        self.thread_id = thread_id
        self.total_threads = total_threads
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            # 顺序处理文件（从上到下），但只处理分配给当前线程的文件
            total_files = len(self.files_info)
            files_per_thread = total_files // self.total_threads
            remainder = total_files % self.total_threads
            
            # 计算当前线程需要处理的文件范围
            start_idx = self.thread_id * files_per_thread
            if self.thread_id < remainder:
                start_idx += self.thread_id
                end_idx = start_idx + files_per_thread + 1
            else:
                start_idx += remainder
                end_idx = start_idx + files_per_thread
            
            # 顺序处理分配给当前线程的文件（从上到下）
            for i in range(start_idx, end_idx):
                if not self.is_running:
                    break
                
                if i < len(self.files_info):
                    try:
                        self.process_single_image(i, self.files_info[i])
                    except Exception as e:
                        self.file_processed.emit(i, "错误", str(e))
            
        except Exception as e:
            print(f"线程 {self.thread_id} 出错: {str(e)}")
        finally:
            self.thread_finished.emit()
    
    def process_single_image(self, row_index, file_info):
        """处理单个图片文件转换"""
        input_path = file_info['path']
        
        try:
            # 获取设置
            target_format = self.settings.get('target_format', 'JPEG')
            quality = self.settings.get('quality', 85)
            keep_exif = self.settings.get('keep_exif', True)
            output_dir = self.settings.get('output_dir') or os.path.dirname(input_path)
            naming_mode = self.settings.get('naming_mode', '保持原名')
            prefix = self.settings.get('prefix', '')
            
            # 生成输出文件名
            original_name = os.path.basename(input_path)
            name_without_ext = os.path.splitext(original_name)[0]
            target_ext = SUPPORTED_FORMATS.get(target_format, ['.jpg'])[0]
            
            if naming_mode == "保持原名":
                output_filename = name_without_ext + target_ext
            elif naming_mode == "添加格式后缀":
                output_filename = f"{name_without_ext}_{target_format.lower()}{target_ext}"
            else:  # 自定义前缀
                output_filename = prefix + name_without_ext + target_ext
            
            output_path = os.path.join(output_dir, output_filename)
            
            # 检查是否需要转换（相同格式直接复制）
            original_ext = os.path.splitext(original_name)[1].lower()
            if original_ext == target_ext.lower() and output_path == input_path:
                # 格式相同且路径相同，跳过转换
                self.file_processed.emit(row_index, "跳过", "格式相同，无需转换")
                # 发送统计信息，将跳过的文件计入成功数
                self.file_stats_updated.emit(True, 0)
                return
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 读取图片
            with Image.open(input_path) as image:
                # 保留原始EXIF信息
                exif_dict = image.info.get('exif') if keep_exif else None
                
                # 优化：只在需要时复制图片
                if target_format == 'JPEG' and image.mode in ['RGBA', 'P']:
                    # 转换为RGB模式（JPEG需要）
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    # 创建白色背景
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    processed_image = rgb_image
                elif target_format == 'GIF' and image.mode != 'P':
                    # GIF格式转换
                    processed_image = image.convert('P', palette=Image.ADAPTIVE)
                else:
                    # 其他格式直接使用原图
                    processed_image = image
                
                # 准备保存参数（优化：减少不必要的参数）
                save_kwargs = {}
                
                if target_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    # 质量100%时跳过压缩优化
                    if quality < 100:
                        save_kwargs['optimize'] = True
                    if exif_dict:
                        save_kwargs['exif'] = exif_dict
                elif target_format == 'PNG':
                    # 优化：使用更快的压缩级别
                    compress_level = min(6, int((100 - quality) / 16))  # 降低压缩级别以提高速度
                    save_kwargs['compress_level'] = compress_level
                    save_kwargs['optimize'] = False  # 关闭优化以提高速度
                elif target_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    # 质量100%时使用最高质量压缩方法
                    if quality < 100:
                        save_kwargs['method'] = 4  # 使用更快的压缩方法
                    else:
                        save_kwargs['method'] = 6  # 最高质量
                elif target_format == 'TIFF':
                    save_kwargs['compression'] = 'tiff_lzw'
                # 其他格式不需要额外参数
                
                # 保存图片
                processed_image.save(output_path, format=target_format, **save_kwargs)
                
                # 计算文件大小变化
                original_size = os.path.getsize(input_path)
                converted_size = os.path.getsize(output_path)
                size_change = converted_size - original_size
                size_change_percent = (size_change / original_size) * 100 if original_size > 0 else 0
                
                # 更新文件信息
                if row_index < len(self.files_info):
                    self.files_info[row_index]['converted_size'] = converted_size
                    self.files_info[row_index]['size_change'] = size_change
                    self.files_info[row_index]['size_change_percent'] = size_change_percent
                    self.files_info[row_index]['output_filename'] = output_filename
                    
                    # 发送文件信息更新信号
                    self.file_info_updated.emit(row_index, {
                        'converted_size': converted_size,
                        'size_change': size_change,
                        'size_change_percent': size_change_percent,
                        'output_filename': output_filename
                    })
                
                # 发送统计信息
                self.file_stats_updated.emit(True, converted_size)
                
                self.file_processed.emit(
                    row_index, 
                    "完成", 
                    f"转换完成 | 输出: {output_filename}"
                )
            
        except Exception as e:
            self.file_stats_updated.emit(False, 0)
            self.file_processed.emit(row_index, "错误", f"转换失败: {str(e)}")


class ImageFormatConvertWorker(QThread):
    """图片格式转换处理线程"""
    progress_updated = pyqtSignal(int, str)  # 进度, 状态信息
    file_processed = pyqtSignal(int, str, str)  # 行号, 状态, 消息
    file_stats_updated = pyqtSignal(bool, int)  # 是否成功, 转换后文件大小
    file_info_updated = pyqtSignal(int, dict)  # 行号, 文件信息更新
    finished = pyqtSignal()
    
    def __init__(self, files_info, settings):
        super().__init__()
        self.files_info = files_info
        self.settings = settings
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            total_files = len(self.files_info)
            target_format = self.settings.get('target_format', 'JPEG')
            target_ext = SUPPORTED_FORMATS.get(target_format, ['.jpg'])[0]
            
            # 预检查：统计需要转换的文件数量
            need_conversion_count = 0
            for file_info in self.files_info:
                original_ext = os.path.splitext(file_info['name'])[1].lower()
                if original_ext != target_ext.lower():
                    need_conversion_count += 1
            
            if need_conversion_count == 0:
                self.progress_updated.emit(100, "所有文件格式相同，无需转换")
                self.finished.emit()
                return
            
            processed_count = 0
            for i, file_info in enumerate(self.files_info):
                if not self.is_running:
                    break
                
                try:
                    self.process_single_image(i, file_info)
                    processed_count += 1
                    progress = int(processed_count * 100 / need_conversion_count)
                    self.progress_updated.emit(progress, f"已处理 {processed_count}/{need_conversion_count} 个需要转换的文件")
                except Exception as e:
                    self.file_processed.emit(i, "错误", str(e))
            
            if self.is_running:
                self.progress_updated.emit(100, "转换完成")
        except Exception as e:
            self.progress_updated.emit(0, f"转换出错: {str(e)}")
        finally:
            self.finished.emit()
    
    def process_single_image(self, row_index, file_info):
        """处理单个图片文件转换"""
        input_path = file_info['path']
        
        try:
            # 获取设置
            target_format = self.settings.get('target_format', 'JPEG')
            quality = self.settings.get('quality', 85)
            keep_exif = self.settings.get('keep_exif', True)
            output_dir = self.settings.get('output_dir') or os.path.dirname(input_path)
            naming_mode = self.settings.get('naming_mode', '保持原名')
            prefix = self.settings.get('prefix', '')
            
            # 生成输出文件名
            original_name = os.path.basename(input_path)
            name_without_ext = os.path.splitext(original_name)[0]
            target_ext = SUPPORTED_FORMATS.get(target_format, ['.jpg'])[0]
            
            if naming_mode == "保持原名":
                output_filename = name_without_ext + target_ext
            elif naming_mode == "添加格式后缀":
                output_filename = f"{name_without_ext}_{target_format.lower()}{target_ext}"
            else:  # 自定义前缀
                output_filename = prefix + name_without_ext + target_ext
            
            output_path = os.path.join(output_dir, output_filename)
            
            # 检查是否需要转换（相同格式直接复制）
            original_ext = os.path.splitext(original_name)[1].lower()
            if original_ext == target_ext.lower() and output_path == input_path:
                # 格式相同且路径相同，跳过转换
                self.file_processed.emit(row_index, "跳过", "格式相同，无需转换")
                # 发送统计信息，将跳过的文件计入成功数
                self.file_stats_updated.emit(True, 0)
                return
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 读取图片
            with Image.open(input_path) as image:
                # 保留原始EXIF信息
                exif_dict = image.info.get('exif') if keep_exif else None
                
                # 优化：只在需要时复制图片
                if target_format == 'JPEG' and image.mode in ['RGBA', 'P']:
                    # 转换为RGB模式（JPEG需要）
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    # 创建白色背景
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    processed_image = rgb_image
                elif target_format == 'GIF' and image.mode != 'P':
                    # GIF格式转换
                    processed_image = image.convert('P', palette=Image.ADAPTIVE)
                else:
                    # 其他格式直接使用原图
                    processed_image = image
                
                # 准备保存参数（优化：减少不必要的参数）
                save_kwargs = {}
                
                if target_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    # 质量100%时跳过压缩优化
                    if quality < 100:
                        save_kwargs['optimize'] = True
                    if exif_dict:
                        save_kwargs['exif'] = exif_dict
                elif target_format == 'PNG':
                    # 优化：使用更快的压缩级别
                    compress_level = min(6, int((100 - quality) / 16))  # 降低压缩级别以提高速度
                    save_kwargs['compress_level'] = compress_level
                    save_kwargs['optimize'] = False  # 关闭优化以提高速度
                elif target_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    # 质量100%时使用最高质量压缩方法
                    if quality < 100:
                        save_kwargs['method'] = 4  # 使用更快的压缩方法
                    else:
                        save_kwargs['method'] = 6  # 最高质量
                elif target_format == 'TIFF':
                    save_kwargs['compression'] = 'tiff_lzw'
                # 其他格式不需要额外参数
                
                # 保存图片
                processed_image.save(output_path, format=target_format, **save_kwargs)
                
                # 计算文件大小变化
                original_size = os.path.getsize(input_path)
                converted_size = os.path.getsize(output_path)
                size_change = converted_size - original_size
                size_change_percent = (size_change / original_size) * 100 if original_size > 0 else 0
                
                # 更新文件信息
                if row_index < len(self.files_info):
                    self.files_info[row_index]['converted_size'] = converted_size
                    self.files_info[row_index]['size_change'] = size_change
                    self.files_info[row_index]['size_change_percent'] = size_change_percent
                    self.files_info[row_index]['output_filename'] = output_filename
                    
                    # 发送文件信息更新信号
                    self.file_info_updated.emit(row_index, {
                        'converted_size': converted_size,
                        'size_change': size_change,
                        'size_change_percent': size_change_percent,
                        'output_filename': output_filename
                    })
                
                # 发送统计信息
                self.file_stats_updated.emit(True, converted_size)
                
                self.file_processed.emit(
                    row_index, 
                    "完成", 
                    f"转换完成 | 输出: {output_filename}"
                )
            
        except Exception as e:
            self.file_stats_updated.emit(False, 0)
            self.file_processed.emit(row_index, "错误", f"转换失败: {str(e)}")


class MultiThreadImageCompressionWorker(QThread):
    """多线程图片压缩处理线程"""
    progress_updated = pyqtSignal(int, str)  # 进度, 状态信息
    file_processed = pyqtSignal(int, str, str)  # 行号, 状态, 消息
    file_stats_updated = pyqtSignal(bool, int)  # 是否成功, 压缩后文件大小
    file_info_updated = pyqtSignal(int, dict)  # 行号, 文件信息更新
    thread_finished = pyqtSignal()  # 单个线程完成信号
    finished = pyqtSignal()  # 所有线程完成信号
    
    def __init__(self, files_info, settings, thread_id, total_threads):
        super().__init__()
        self.files_info = files_info
        self.settings = settings
        self.thread_id = thread_id
        self.total_threads = total_threads
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            # 顺序处理文件（从上到下），但只处理分配给当前线程的文件
            total_files = len(self.files_info)
            files_per_thread = total_files // self.total_threads
            remainder = total_files % self.total_threads
            
            # 计算当前线程需要处理的文件范围
            # 前remainder个线程每个处理(files_per_thread + 1)个文件
            # 后面的线程每个处理files_per_thread个文件
            if self.thread_id < remainder:
                start_idx = self.thread_id * (files_per_thread + 1)
                end_idx = start_idx + files_per_thread + 1
            else:
                start_idx = remainder * (files_per_thread + 1) + (self.thread_id - remainder) * files_per_thread
                end_idx = start_idx + files_per_thread
            
            print(f"线程 {self.thread_id}: 处理文件范围 [{start_idx}, {end_idx}), 共 {end_idx - start_idx} 个文件")
            
            # 顺序处理分配给当前线程的文件（从上到下）
            for i in range(start_idx, end_idx):
                if not self.is_running:
                    break
                
                if i < len(self.files_info):
                    try:
                        self.process_single_image(i, self.files_info[i])
                    except Exception as e:
                        self.file_processed.emit(i, "错误", str(e))
            
        except Exception as e:
            print(f"压缩线程 {self.thread_id} 出错: {str(e)}")
        finally:
            self.thread_finished.emit()
    
    def process_single_image(self, row_index, file_info):
        """处理单个图片文件压缩"""
        try:
            # 获取文件信息
            input_path = file_info['path']
            file_name = file_info['name']
            
            # 生成输出路径
            output_path = self.generate_output_path(input_path, file_name)
            
            # 检查是否需要处理
            if not self.should_process_file(input_path, output_path):
                self.file_processed.emit(row_index, "跳过", "文件已存在或格式相同")
                # 发送统计信息，将跳过的文件计入成功数
                self.file_stats_updated.emit(True, 0)
                return
            
            # 执行压缩
            success, compressed_size = self.compress_image(input_path, output_path)
            
            if success:
                # 计算原始文件大小
                original_size = os.path.getsize(input_path)
                saved_space = original_size - compressed_size
                compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                
                # 更新文件信息
                file_info['compressed_size'] = compressed_size
                file_info['output_path'] = output_path
                file_info['saved_space'] = saved_space
                file_info['compression_ratio'] = compression_ratio
                
                # 发送成功信号
                self.file_processed.emit(row_index, "完成", f"压缩完成: {os.path.basename(output_path)}")
                self.file_stats_updated.emit(True, compressed_size)
                
                # 更新文件信息
                self.file_info_updated.emit(row_index, {
                    'compressed_size': compressed_size,
                    'output_path': output_path,
                    'saved_space': saved_space,
                    'compression_ratio': compression_ratio
                })
            else:
                self.file_processed.emit(row_index, "错误", "压缩失败")
                self.file_stats_updated.emit(False, 0)
                
        except Exception as e:
            self.file_processed.emit(row_index, "错误", f"压缩失败: {str(e)}")
    
    def generate_output_path(self, input_path, file_name):
        """生成输出路径"""
        # 获取输出目录
        output_dir = self.settings.get('output_dir')
        if not output_dir:
            output_dir = os.path.dirname(input_path)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        name, ext = os.path.splitext(file_name)
        output_format = self.settings.get('output_format', 'JPEG')
        
        # 根据格式确定扩展名
        format_extensions = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'WEBP': '.webp'
        }
        output_ext = format_extensions.get(output_format, '.jpg')
        
        # 如果格式相同且输出目录相同，添加后缀
        if ext.lower() == output_ext.lower() and output_dir == os.path.dirname(input_path):
            output_name = f"{name}_compressed{output_ext}"
        else:
            output_name = f"{name}{output_ext}"
        
        return os.path.join(output_dir, output_name)
    
    def should_process_file(self, input_path, output_path):
        """检查是否需要处理文件"""
        # 如果输出文件已存在，跳过
        if os.path.exists(output_path):
            return False
        
        # 如果输入和输出路径相同，跳过
        if input_path == output_path:
            return False
        
        return True
    
    def compress_image(self, input_path, output_path):
        """压缩图片"""
        try:
            from PIL import Image
            
            print(f"开始压缩图片: {input_path} -> {output_path}")
            
            # 打开图片
            with Image.open(input_path) as img:
                print(f"原始图片模式: {img.mode}, 尺寸: {img.size}")
                
                # 转换为RGB模式（JPEG需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    print("转换图片模式为RGB")
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    print(f"转换图片模式从 {img.mode} 到 RGB")
                    img = img.convert('RGB')
                
                # 应用尺寸调整
                if self.settings.get('resize_enabled', False):
                    print("应用尺寸调整")
                    img = self.apply_resize(img)
                
                # 应用水印
                if self.settings.get('watermark', {}).get('enabled', False):
                    print("应用水印")
                    img = self.apply_watermark(img)
                
                # 保存图片
                output_format = self.settings.get('output_format', 'JPEG')
                quality = self.settings.get('quality', 85)
                
                print(f"输出格式: {output_format}, 质量: {quality}")
                
                save_kwargs = {'format': output_format}
                if output_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif output_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 6  # 最佳压缩
                
                # 暂时跳过EXIF信息处理
                print(f"保存参数: {save_kwargs}")
                print(f"保存图片到: {output_path}")
                
                img.save(output_path, **save_kwargs)
                
                # 返回压缩后文件大小
                compressed_size = os.path.getsize(output_path)
                print(f"压缩完成，文件大小: {compressed_size} bytes")
                return True, compressed_size
                
        except Exception as e:
            print(f"压缩图片失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, 0
    
    def apply_resize(self, img):
        """应用尺寸调整"""
        resize_mode = self.settings.get('resize_mode', 'percentage')
        
        if resize_mode == 'percentage':
            percentage = self.settings.get('resize_percentage', 80)
            new_size = (int(img.width * percentage / 100), int(img.height * percentage / 100))
        else:  # pixel
            new_width = self.settings.get('resize_width', 800)
            new_height = self.settings.get('resize_height', 600)
            new_size = (new_width, new_height)
        
        return img.resize(new_size, Image.Resampling.LANCZOS)
    
    def apply_watermark(self, img):
        """应用水印"""
        watermark_settings = self.settings.get('watermark', {})
        if not watermark_settings.get('enabled', False):
            return img
        
        # 这里可以添加水印逻辑
        # 暂时返回原图
        return img


class ImageCompressionWorker(QThread):
    """图片压缩处理线程（单线程版本，保持兼容性）"""
    progress_updated = pyqtSignal(int, str)  # 进度, 状态信息
    file_processed = pyqtSignal(int, str, str)  # 行号, 状态, 消息
    file_stats_updated = pyqtSignal(bool, int)  # 是否成功, 压缩后文件大小
    file_info_updated = pyqtSignal(int, dict)  # 行号, 文件信息更新
    finished = pyqtSignal()
    
    def __init__(self, files_info, settings):
        super().__init__()
        self.files_info = files_info
        self.settings = settings
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            total_files = len(self.files_info)
            for i, file_info in enumerate(self.files_info):
                if not self.is_running:
                    break
                
                try:
                    self.process_single_image(i, file_info)
                    progress = int((i + 1) * 100 / total_files)
                    self.progress_updated.emit(progress, f"已处理 {i + 1}/{total_files} 个文件")
                except Exception as e:
                    self.file_processed.emit(i, "错误", str(e))
            
            if self.is_running:
                self.progress_updated.emit(100, "处理完成")
        except Exception as e:
            self.progress_updated.emit(0, f"处理出错: {str(e)}")
        finally:
            self.finished.emit()
    
    def process_single_image(self, row_index, file_info):
        """处理单个图片文件"""
        input_path = file_info['path']
        
        try:
            # 读取图片
            with Image.open(input_path) as image:
                # 保留原始EXIF信息
                exif_dict = image.info.get('exif')
                
                # 获取设置
                quality = self.settings.get('quality', 85)
                resize_enabled = self.settings.get('resize_enabled', False)
                resize_width = self.settings.get('resize_width', image.width)
                resize_height = self.settings.get('resize_height', image.height)
                resize_mode = self.settings.get('resize_mode', 'percentage')
                resize_percentage = self.settings.get('resize_percentage', 100)
                output_format = self.settings.get('output_format', 'JPEG')
                keep_exif = self.settings.get('keep_exif', True)
                output_dir = self.settings.get('output_dir') or os.path.dirname(input_path)
                
                # 优化：只在需要时复制图片
                if output_format == 'JPEG' and image.mode in ['RGBA', 'P']:
                    # 转换为RGB模式（JPEG需要）
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    # 创建白色背景
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    processed_image = rgb_image
                else:
                    # 其他格式直接使用原图
                    processed_image = image
                
                # 尺寸调整
                if resize_enabled:
                    if resize_mode == 'percentage':
                        scale = resize_percentage / 100.0
                        new_width = int(image.width * scale)
                        new_height = int(image.height * scale)
                    else:
                        new_width = resize_width
                        new_height = resize_height
                    
                    if new_width != image.width or new_height != image.height:
                        # 使用高质量的重采样算法
                        processed_image = processed_image.resize(
                            (new_width, new_height), 
                            Image.Resampling.LANCZOS
                        )
                
                # 添加水印
                watermark_settings = self.settings.get('watermark', {})
                if watermark_settings.get('enabled', False):
                    processed_image = self.add_watermark(processed_image, watermark_settings)
                
                # 生成输出文件名
                input_name = os.path.splitext(os.path.basename(input_path))[0]
                if output_format == 'JPEG':
                    output_ext = '.jpg'
                elif output_format == 'PNG':
                    output_ext = '.png'
                elif output_format == 'WEBP':
                    output_ext = '.webp'
                else:
                    output_ext = '.jpg'
                
                output_filename = f"{input_name}_compressed{output_ext}"
                output_path = os.path.join(output_dir, output_filename)
                
                # 确保输出目录存在
                os.makedirs(output_dir, exist_ok=True)
                
                # 准备保存参数
                save_kwargs = {}
                
                if output_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                    if keep_exif and exif_dict:
                        save_kwargs['exif'] = exif_dict
                elif output_format == 'PNG':
                    # 优化：使用更快的压缩级别
                    compress_level = min(6, int((100 - quality) / 16))  # 降低压缩级别以提高速度
                    save_kwargs['compress_level'] = compress_level
                    save_kwargs['optimize'] = False  # 关闭优化以提高速度
                elif output_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 4  # 使用更快的压缩方法
                
                # 保存图片
                processed_image.save(output_path, format=output_format, **save_kwargs)
                
                # 计算文件大小变化
                original_size = os.path.getsize(input_path)
                compressed_size = os.path.getsize(output_path)
                saved_space = original_size - compressed_size
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                # 更新文件信息
                if row_index < len(self.files_info):
                    self.files_info[row_index]['compressed_size'] = compressed_size
                    self.files_info[row_index]['saved_space'] = saved_space
                    self.files_info[row_index]['compression_ratio'] = compression_ratio
                    self.files_info[row_index]['output_filename'] = output_filename
                    
                    # 发送文件信息更新信号
                    self.file_info_updated.emit(row_index, {
                        'compressed_size': compressed_size,
                        'saved_space': saved_space,
                        'compression_ratio': compression_ratio,
                        'output_filename': output_filename
                    })
                
                # 发送统计信息
                self.file_stats_updated.emit(True, compressed_size)
                
                self.file_processed.emit(
                    row_index, 
                    "完成", 
                    f"压缩率: {compression_ratio:.1f}% | 输出: {output_filename}"
                )
            
        except Exception as e:
            self.file_stats_updated.emit(False, 0)
            self.file_processed.emit(row_index, "错误", f"处理失败: {str(e)}")
    
    def add_watermark(self, image, watermark_settings):
        """添加水印到图片"""
        try:
            if watermark_settings.get('type') == 'text':
                return self.add_text_watermark(image, watermark_settings)
            else:
                # 图片水印功能可以在这里实现
                return image
        except Exception as e:
            print(f"添加水印失败: {e}")
            return image
    
    def add_text_watermark(self, image, settings):
        """添加文字水印"""
        try:
            # 获取水印设置
            text = settings.get('text', '© 2025')
            font_size = settings.get('font_size', 24)
            opacity = settings.get('opacity', 70)
            position = settings.get('position', '右下角')
            margin = settings.get('margin', 20)
            
            # 创建一个可绘制的图像副本
            watermarked = image.copy()
            
            # 创建绘图对象
            draw = ImageDraw.Draw(watermarked)
            
            # 尝试加载字体
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                try:
                    # 尝试使用默认字体
                    font = ImageFont.load_default()
                except:
                    font = None
            
            # 获取文字尺寸
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                # 如果没有字体，估算尺寸
                text_width = len(text) * (font_size // 2)
                text_height = font_size
            
            # 计算水印位置
            width, height = image.size
            
            if position == '右下角':
                x = width - text_width - margin
                y = height - text_height - margin
            elif position == '右上角':
                x = width - text_width - margin
                y = margin
            elif position == '左上角':
                x = margin
                y = margin
            elif position == '左下角':
                x = margin
                y = height - text_height - margin
            else:  # 居中
                x = (width - text_width) // 2
                y = (height - text_height) // 2
            
            # 确保坐标在图像范围内
            x = max(0, min(x, width - text_width))
            y = max(0, min(y, height - text_height))
            
            # 计算文字颜色（半透明白色）
            alpha = int(opacity * 2.55)  # 转换为0-255范围
            text_color = (255, 255, 255, alpha)
            
            # 如果图像不支持透明度，创建一个透明图层
            if image.mode != 'RGBA':
                # 创建透明图层
                overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                overlay_draw.text((x, y), text, font=font, fill=text_color)
                
                # 将透明图层合并到原图
                watermarked = Image.alpha_composite(
                    watermarked.convert('RGBA'), 
                    overlay
                )
                
                # 如果原图不是RGBA，转换回原模式
                if image.mode != 'RGBA':
                    if image.mode == 'RGB':
                        watermarked = watermarked.convert('RGB')
            else:
                # 直接在RGBA图像上绘制
                draw.text((x, y), text, font=font, fill=text_color)
            
            return watermarked
            
        except Exception as e:
            print(f"添加文字水印失败: {e}")
            return image


class ImagePreviewDialog(QDialog):
    """图片预览对话框"""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片预览")
        self.resize(400,300)
        
        layout = QVBoxLayout()
        
        # 图片显示
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        
        # 加载图片
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # 缩放图片以适应窗口
            scaled_pixmap = pixmap.scaled(500, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText("无法加载图片")
        
        layout.addWidget(self.image_label)
        
        # 信息标签
        info_text = self.get_image_info(image_path)
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_image_info(self, image_path):
        """获取图片信息"""
        try:
            with Image.open(image_path) as image:
                file_size = os.path.getsize(image_path) / (1024 * 1024)  # MB
                
                info = f"文件: {os.path.basename(image_path)}\n"
                info += f"尺寸: {image.width} × {image.height}\n"
                info += f"大小: {file_size:.2f} MB\n"
                info += f"格式: {image.format}\n"
                info += f"色彩模式: {image.mode}\n"
                
                # 获取EXIF信息
                if hasattr(image, '_getexif') and image._getexif():
                    info += "包含EXIF信息: 是\n"
                else:
                    info += "包含EXIF信息: 否\n"
                
                # 获取图像创建时间
                try:
                    creation_time = os.path.getctime(image_path)
                    import datetime
                    creation_date = datetime.datetime.fromtimestamp(creation_time)
                    info += f"创建时间: {creation_date.strftime('%Y-%m-%d %H:%M:%S')}"
                except:
                    pass
            
            return info
        except Exception as e:
            return f"无法获取图片信息: {str(e)}"


class WatermarkDialog(QDialog):
    """水印设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("水印设置")
        self.setMinimumSize(400, 350)
        
        layout = QVBoxLayout()
        
        # 启用水印
        self.enable_watermark = QCheckBox("启用水印")
        layout.addWidget(self.enable_watermark)
        
        # 水印类型选择
        type_group = QGroupBox("水印类型")
        type_layout = QVBoxLayout(type_group)
        
        self.text_radio = QRadioButton("文字水印")
        self.text_radio.setChecked(True)
        self.image_radio = QRadioButton("图片水印")
        
        type_layout.addWidget(self.text_radio)
        type_layout.addWidget(self.image_radio)
        layout.addWidget(type_group)
        
        # 文字水印设置
        text_group = QGroupBox("文字设置")
        text_layout = QFormLayout(text_group)
        
        self.watermark_text = QLineEdit("© 2025")
        text_layout.addRow("水印文字:", self.watermark_text)
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(10, 200)
        self.font_size_spinbox.setValue(24)
        text_layout.addRow("字体大小:", self.font_size_spinbox)
        
        self.opacity_spinbox = QSpinBox()
        self.opacity_spinbox.setRange(10, 100)
        self.opacity_spinbox.setValue(70)
        self.opacity_spinbox.setSuffix("%")
        text_layout.addRow("透明度:", self.opacity_spinbox)
        
        layout.addWidget(text_group)
        
        # 位置设置
        position_group = QGroupBox("位置设置")
        position_layout = QFormLayout(position_group)
        
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "右下角", "右上角", "左上角", "左下角", "居中"
        ])
        position_layout.addRow("位置:", self.position_combo)
        
        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, 200)
        self.margin_spinbox.setValue(20)
        position_layout.addRow("边距:", self.margin_spinbox)
        
        layout.addWidget(position_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_watermark_settings(self):
        """获取水印设置"""
        return {
            'enabled': self.enable_watermark.isChecked(),
            'type': 'text' if self.text_radio.isChecked() else 'image',
            'text': self.watermark_text.text(),
            'font_size': self.font_size_spinbox.value(),
            'opacity': self.opacity_spinbox.value(),
            'position': self.position_combo.currentText(),
            'margin': self.margin_spinbox.value()
        }


class BatchRenameDialog(QDialog):
    """批量重命名对话框"""
    def __init__(self, file_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名")
        self.setMinimumSize(500, 400)
        self.file_list = file_list
        
        layout = QVBoxLayout()
        
        # 重命名规则
        rules_group = QGroupBox("重命名规则")
        rules_layout = QFormLayout(rules_group)
        
        self.prefix_line = QLineEdit()
        self.prefix_line.setPlaceholderText("例如: IMG_")
        rules_layout.addRow("前缀:", self.prefix_line)
        
        self.suffix_line = QLineEdit()
        self.suffix_line.setPlaceholderText("例如: _compressed")
        rules_layout.addRow("后缀:", self.suffix_line)
        
        self.numbering_checkbox = QCheckBox("添加序号")
        self.numbering_checkbox.setChecked(True)
        rules_layout.addRow("", self.numbering_checkbox)
        
        self.start_number_spinbox = QSpinBox()
        self.start_number_spinbox.setRange(0, 9999)
        self.start_number_spinbox.setValue(1)
        rules_layout.addRow("起始序号:", self.start_number_spinbox)
        
        layout.addWidget(rules_group)
        
        # 预览
        preview_group = QGroupBox("重命名预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_list = QTextEdit()
        self.preview_list.setMaximumHeight(200)
        self.preview_list.setReadOnly(True)
        preview_layout.addWidget(self.preview_list)
        
        update_preview_btn = QPushButton("更新预览")
        update_preview_btn.clicked.connect(self.update_preview)
        preview_layout.addWidget(update_preview_btn)
        
        layout.addWidget(preview_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # 初始预览
        self.update_preview()
    
    def update_preview(self):
        """更新重命名预览"""
        preview_text = ""
        prefix = self.prefix_line.text()
        suffix = self.suffix_line.text()
        use_numbering = self.numbering_checkbox.isChecked()
        start_num = self.start_number_spinbox.value()
        
        for i, file_info in enumerate(self.file_list[:10]):  # 只显示前10个
            original_name = file_info['name']
            name_without_ext = os.path.splitext(original_name)[0]
            ext = os.path.splitext(original_name)[1]
            
            new_name = prefix
            if use_numbering:
                new_name += f"{start_num + i:04d}_"
            new_name += name_without_ext + suffix + ext
            
            preview_text += f"{original_name} → {new_name}\n"
        
        if len(self.file_list) > 10:
            preview_text += f"... 还有 {len(self.file_list) - 10} 个文件"
        
        self.preview_list.setPlainText(preview_text)
    
    def get_rename_settings(self):
        """获取重命名设置"""
        return {
            'prefix': self.prefix_line.text(),
            'suffix': self.suffix_line.text(),
            'use_numbering': self.numbering_checkbox.isChecked(),
            'start_number': self.start_number_spinbox.value()
        }


class BatchFormatConvertDialog(QDialog):
    """批量格式转换对话框"""
    def __init__(self, file_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量格式转换")
        self.setMinimumSize(600, 500)
        self.file_list = file_list
        
        layout = QVBoxLayout()
        
        # 转换设置
        convert_group = QGroupBox("转换设置")
        convert_layout = QFormLayout(convert_group)
        
        # 目标格式选择
        self.target_format_combo = QComboBox()
        # 添加常用格式
        common_formats = ['JPEG', 'PNG', 'WEBP', 'TIFF', 'BMP', 'GIF', 'ICO', 'TGA']
        self.target_format_combo.addItems(common_formats)
        convert_layout.addRow("目标格式:", self.target_format_combo)
        
        # 质量设置（仅对JPEG和WEBP有效）
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(1, 100)
        self.quality_spinbox.setValue(85)
        self.quality_spinbox.setSuffix("%")
        convert_layout.addRow("质量 (JPEG/WEBP):", self.quality_spinbox)
        
        # 保留EXIF信息
        self.keep_exif_checkbox = QCheckBox()
        self.keep_exif_checkbox.setChecked(True)
        convert_layout.addRow("保留EXIF信息:", self.keep_exif_checkbox)
        
        # 输出目录设置
        output_layout = QHBoxLayout()
        self.output_dir_line = QLineEdit()
        self.output_dir_line.setPlaceholderText("留空使用源文件目录")
        output_layout.addWidget(QLabel("输出目录:"))
        output_layout.addWidget(self.output_dir_line)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(browse_btn)
        convert_layout.addRow("", output_layout)
        
        # 文件命名设置
        naming_layout = QHBoxLayout()
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["保持原名", "添加格式后缀", "自定义前缀"])
        naming_layout.addWidget(QLabel("文件命名:"))
        naming_layout.addWidget(self.naming_combo)
        convert_layout.addRow("", naming_layout)
        
        # 自定义前缀输入框
        self.prefix_line = QLineEdit()
        self.prefix_line.setPlaceholderText("例如: converted_")
        self.prefix_line.setEnabled(False)
        convert_layout.addRow("自定义前缀:", self.prefix_line)
        
        # 连接信号
        self.naming_combo.currentTextChanged.connect(self.on_naming_changed)
        self.target_format_combo.currentTextChanged.connect(self.on_format_changed)
        
        layout.addWidget(convert_group)
        
        # 转换预览
        preview_group = QGroupBox("转换预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_list = QTextEdit()
        self.preview_list.setMaximumHeight(200)
        self.preview_list.setReadOnly(True)
        preview_layout.addWidget(self.preview_list)
        
        update_preview_btn = QPushButton("更新预览")
        update_preview_btn.clicked.connect(self.update_preview)
        preview_layout.addWidget(update_preview_btn)
        
        layout.addWidget(preview_group)
        
        # 统计信息
        stats_group = QGroupBox("转换统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # 初始预览和统计
        self.update_preview()
        self.update_stats()
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_line.setText(dir_path)
    
    def on_naming_changed(self, text):
        """命名方式改变时的处理"""
        self.prefix_line.setEnabled(text == "自定义前缀")
        self.update_preview()
    
    def on_format_changed(self, format_name):
        """格式改变时的处理"""
        # 根据格式调整质量设置的可视性
        if format_name in ['JPEG', 'WEBP']:
            self.quality_spinbox.setEnabled(True)
        else:
            self.quality_spinbox.setEnabled(False)
        self.update_preview()
    
    def update_preview(self):
        """更新转换预览"""
        preview_text = ""
        target_format = self.target_format_combo.currentText()
        naming_mode = self.naming_combo.currentText()
        prefix = self.prefix_line.text()
        
        # 获取目标格式的扩展名
        target_ext = SUPPORTED_FORMATS.get(target_format, ['.jpg'])[0]
        
        for i, file_info in enumerate(self.file_list[:10]):  # 只显示前10个
            original_name = file_info['name']
            name_without_ext = os.path.splitext(original_name)[0]
            original_ext = os.path.splitext(original_name)[1]
            
            # 生成新文件名
            if naming_mode == "保持原名":
                new_name = name_without_ext + target_ext
            elif naming_mode == "添加格式后缀":
                new_name = f"{name_without_ext}_{target_format.lower()}{target_ext}"
            else:  # 自定义前缀
                new_name = prefix + name_without_ext + target_ext
            
            # 检查是否需要转换
            needs_conversion = original_ext.lower() != target_ext.lower()
            status = "需要转换" if needs_conversion else "格式相同"
            
            preview_text += f"{original_name} → {new_name} ({status})\n"
        
        if len(self.file_list) > 10:
            preview_text += f"... 还有 {len(self.file_list) - 10} 个文件"
        
        self.preview_list.setPlainText(preview_text)
    
    def update_stats(self):
        """更新转换统计"""
        target_format = self.target_format_combo.currentText()
        target_ext = SUPPORTED_FORMATS.get(target_format, ['.jpg'])[0]
        
        total_files = len(self.file_list)
        need_conversion = 0
        same_format = 0
        
        for file_info in self.file_list:
            original_ext = os.path.splitext(file_info['name'])[1]
            if original_ext.lower() != target_ext.lower():
                need_conversion += 1
            else:
                same_format += 1
        
        stats_text = f"总文件数: {total_files} | 需要转换: {need_conversion} | 格式相同: {same_format}"
        self.stats_label.setText(stats_text)
    
    def get_conversion_settings(self):
        """获取转换设置"""
        return {
            'target_format': self.target_format_combo.currentText(),
            'quality': self.quality_spinbox.value(),
            'keep_exif': self.keep_exif_checkbox.isChecked(),
            'output_dir': self.output_dir_line.text().strip() or None,
            'naming_mode': self.naming_combo.currentText(),
            'prefix': self.prefix_line.text()
        }


class ColumnSettingsDialog(QDialog):
    """列设置对话框"""
    def __init__(self, column_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("列显示设置")
        self.setMinimumSize(300, 250)
        self.column_settings = column_settings.copy()
        
        layout = QVBoxLayout()
        
        # 说明文字
        info_label = QLabel("选择要显示的列:")
        layout.addWidget(info_label)
        
        # 列选择
        self.checkboxes = {}
        columns = ["文件名", "输出文件名", "尺寸", "原始大小", "压缩大小", "保存空间", "压缩率", "状态"]
        
        for i, column in enumerate(columns):
            checkbox = QCheckBox(column)
            checkbox.setChecked(self.column_settings.get(i, True))
            # 文件名列必须显示
            if i == 0:
                checkbox.setEnabled(False)
                checkbox.setChecked(True)
            self.checkboxes[i] = checkbox
            layout.addWidget(checkbox)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_default)
        button_layout.addWidget(reset_btn)
        
        layout.addLayout(button_layout)
        
        # 确认按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def select_all(self):
        """全选所有列"""
        for checkbox in self.checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)
    
    def reset_default(self):
        """恢复默认设置"""
        for i, checkbox in self.checkboxes.items():
            if checkbox.isEnabled():
                # 输出文件名列默认不选中
                if i == 1:  # 输出文件名列
                    checkbox.setChecked(False)
                else:
                    checkbox.setChecked(True)
    
    def get_column_settings(self):
        """获取列设置"""
        settings = {}
        for i, checkbox in self.checkboxes.items():
            settings[i] = checkbox.isChecked()
        return settings


class StatsDialog(QDialog):
    """处理统计对话框"""
    def __init__(self, stats_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("处理统计")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        # 统计信息
        stats_text = self.format_stats(stats_data)
        stats_label = QLabel(stats_text)
        stats_label.setWordWrap(True)
        stats_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(stats_label)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def format_stats(self, stats):
        """格式化统计信息"""
        text = "🎉 处理完成统计\n\n"
        text += f"总文件数: {stats.get('total_files', 0)}\n"
        text += f"成功处理: {stats.get('success_count', 0)}\n"
        text += f"处理失败: {stats.get('error_count', 0)}\n\n"
        
        if stats.get('total_original_size', 0) > 0:
            original_size_mb = stats['total_original_size'] / (1024 * 1024)
            compressed_size_mb = stats['total_compressed_size'] / (1024 * 1024)
            savings_mb = original_size_mb - compressed_size_mb
            savings_percent = (savings_mb / original_size_mb) * 100
            
            text += f"原始总大小: {original_size_mb:.2f} MB\n"
            text += f"压缩后大小: {compressed_size_mb:.2f} MB\n"
            text += f"节省空间: {savings_mb:.2f} MB ({savings_percent:.1f}%)\n\n"
        
        processing_time = stats.get('processing_time', 0)
        text += f"处理时间: {processing_time:.1f} 秒\n"
        
        if stats.get('success_count', 0) > 0:
            avg_time = processing_time / stats['success_count']
            text += f"平均每张: {avg_time:.2f} 秒"
        
        return text


class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级设置")
        self.setMinimumSize(450, 400)
        
        layout = QVBoxLayout()
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 基本设置选项卡
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        
        # 输出目录设置
        self.output_dir_combo = QComboBox()
        self.output_dir_combo.addItems(["源文件目录"])
        basic_layout.addRow("输出目录:", self.output_dir_combo)
        
        # 文件命名设置
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["添加后缀"])
        basic_layout.addRow("文件命名:", self.naming_combo)
        
        # 保留EXIF信息
        self.keep_exif_checkbox = QCheckBox()
        self.keep_exif_checkbox.setChecked(True)
        basic_layout.addRow("保留EXIF信息:", self.keep_exif_checkbox)
        
        # 自动删除原文件
        self.auto_delete_checkbox = QCheckBox()
        basic_layout.addRow("自动删除原文件:", self.auto_delete_checkbox)
        
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 性能设置选项卡
        performance_tab = QWidget()
        performance_layout = QFormLayout(performance_tab)
        
        # 多线程处理
        self.thread_count_spinbox = QSpinBox()
        self.thread_count_spinbox.setRange(1, 8)
        self.thread_count_spinbox.setValue(4)
        performance_layout.addRow("处理线程数:", self.thread_count_spinbox)
        
        # 内存优化
        self.memory_optimize_checkbox = QCheckBox()
        self.memory_optimize_checkbox.setChecked(True)
        performance_layout.addRow("内存优化:", self.memory_optimize_checkbox)
        
        # 缓存设置
        self.cache_enabled_checkbox = QCheckBox()
        self.cache_enabled_checkbox.setChecked(True)
        performance_layout.addRow("启用缓存:", self.cache_enabled_checkbox)
        
        tab_widget.addTab(performance_tab, "性能设置")
        
        # 高级功能选项卡
        advanced_tab = QWidget()
        advanced_layout = QFormLayout(advanced_tab)
        
        # 自动旋转
        self.auto_rotate_checkbox = QCheckBox()
        advanced_layout.addRow("根据EXIF自动旋转:", self.auto_rotate_checkbox)
        
        # 颜色配置文件
        self.color_profile_combo = QComboBox()
        self.color_profile_combo.addItems(["保持原始", "sRGB", "Adobe RGB"])
        advanced_layout.addRow("颜色配置文件:", self.color_profile_combo)
        
        # 渐进式JPEG
        self.progressive_checkbox = QCheckBox()
        advanced_layout.addRow("渐进式JPEG:", self.progressive_checkbox)
        
        tab_widget.addTab(advanced_tab, "高级功能")
        
        layout.addWidget(tab_widget)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def restore_defaults(self):
        """恢复默认设置"""
        self.output_dir_combo.setCurrentIndex(0)
        self.naming_combo.setCurrentIndex(0)
        self.keep_exif_checkbox.setChecked(True)
        self.auto_delete_checkbox.setChecked(False)
        self.thread_count_spinbox.setValue(4)
        self.memory_optimize_checkbox.setChecked(True)
        self.cache_enabled_checkbox.setChecked(True)
        self.auto_rotate_checkbox.setChecked(False)
        self.color_profile_combo.setCurrentIndex(0)
        self.progressive_checkbox.setChecked(False)


class PicZipMainWindow(QMainWindow):
    """图片压缩工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片压缩")
        self.resize(1500, 1000)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon", "compress.ico")
        self.setWindowIcon(QIcon(icon_path))        
        # 设置文件
        self.settings = QSettings("PicZip", "ImageCompressor")
        
        # 压缩线程
        self.compression_worker = None
        self.compression_workers = []  # 多线程压缩
        self.compression_thread_count = 0  # 当前运行的压缩线程数
        
        # 格式转换线程
        self.conversion_worker = None
        self.conversion_workers = []  # 多线程转换
        self.conversion_thread_count = 0  # 当前运行的转换线程数
        self.active_thread_count = 0  # 当前活跃的线程数
        
        # 文件列表
        self.file_list = []
        
        # 水印设置
        self.watermark_settings = {
            'enabled': False,
            'type': 'text',
            'text': '© 2025',
            'font_size': 24,
            'opacity': 70,
            'position': '右下角',
            'margin': 20
        }
        
        # 处理统计
        self.processing_stats = {
            'total_files': 0,
            'success_count': 0,
            'error_count': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'processing_time': 0
        }
        
        # 列显示设置 (默认显示所有列，除了输出文件名)
        self.column_settings = {
            0: True,  # 文件名
            1: False,  # 输出文件名
            2: True,  # 尺寸
            3: True,  # 原始大小
            4: True,  # 压缩大小
            5: True,  # 保存空间
            6: True,  # 压缩率
            7: True   # 状态
        }
        
        self.init_ui()
        self.load_settings()
        
        # 添加ESC键关闭快捷键
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.close)        

        # 启用拖拽
        self.setAcceptDrops(True)
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧文件列表区域
        left_widget = self.create_file_list_area()
        splitter.addWidget(left_widget)
        
        # 右侧设置区域
        right_widget = self.create_settings_area()
        splitter.addWidget(right_widget)
        
        # # 设置分割比例 (6:1)
        # splitter.setSizes([600, 100])
        # 设置拉伸因子以保持6:1比例
        splitter.setStretchFactor(0, 6)  # 左侧文件列表区域
        splitter.setStretchFactor(1, 1)  # 右侧设置区域
        
        main_layout.addWidget(splitter)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        add_files_action = QAction('添加文件...', self)
        add_files_action.setShortcut('Ctrl+O')
        add_files_action.triggered.connect(self.add_files)
        file_menu.addAction(add_files_action)
        
        add_folder_action = QAction('添加文件夹...', self)
        add_folder_action.setShortcut('Ctrl+Shift+O')
        add_folder_action.triggered.connect(self.add_folder)
        file_menu.addAction(add_folder_action)
        
        file_menu.addSeparator()
        
        clear_action = QAction('清空列表', self)
        clear_action.triggered.connect(self.clear_file_list)
        file_menu.addAction(clear_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        advanced_settings_action = QAction('高级设置...', self)
        advanced_settings_action.triggered.connect(self.show_advanced_settings)
        settings_menu.addAction(advanced_settings_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        watermark_action = QAction('水印设置...', self)
        watermark_action.triggered.connect(self.show_watermark_dialog)
        tools_menu.addAction(watermark_action)
        
        batch_rename_action = QAction('批量重命名...', self)
        batch_rename_action.triggered.connect(self.show_batch_rename_dialog)
        tools_menu.addAction(batch_rename_action)
        
        batch_convert_action = QAction('批量格式转换...', self)
        batch_convert_action.triggered.connect(self.show_batch_format_convert_dialog)
        tools_menu.addAction(batch_convert_action)
        
        tools_menu.addSeparator()
        
        preset_menu = tools_menu.addMenu('压缩预设')
        
        web_preset_action = QAction('网络优化 (质量60%, 800px)', self)
        web_preset_action.triggered.connect(lambda: self.apply_preset('web'))
        preset_menu.addAction(web_preset_action)
        
        print_preset_action = QAction('打印优化 (质量90%, 原尺寸)', self)
        print_preset_action.triggered.connect(lambda: self.apply_preset('print'))
        preset_menu.addAction(print_preset_action)
        
        mobile_preset_action = QAction('移动设备 (质量75%, 1080px)', self)
        mobile_preset_action.triggered.connect(lambda: self.apply_preset('mobile'))
        preset_menu.addAction(mobile_preset_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于...', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 添加文件按钮
        add_files_btn = QPushButton("添加文件")
        add_files_btn.clicked.connect(self.add_files)
        toolbar.addWidget(add_files_btn)
        
        # 添加文件夹按钮
        add_folder_btn = QPushButton("添加文件夹")
        add_folder_btn.clicked.connect(self.add_folder)
        toolbar.addWidget(add_folder_btn)
        
        # 分隔符
        toolbar.addSeparator()
        
        # 清空按钮
        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_file_list)
        toolbar.addWidget(clear_btn)
        
        # 分隔符
        toolbar.addSeparator()
        
        # 开始压缩按钮
        self.start_btn = QPushButton("开始压缩")
        self.start_btn.clicked.connect(self.start_compression)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        toolbar.addWidget(self.start_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_compression)
        self.stop_btn.setEnabled(False)
        toolbar.addWidget(self.stop_btn)
        
        # 添加第二个工具栏用于高级功能
        toolbar2 = QToolBar("高级功能")
        self.addToolBar(toolbar2)
        
        # 水印按钮
        watermark_btn = QPushButton("水印设置")
        watermark_btn.clicked.connect(self.show_watermark_dialog)
        toolbar2.addWidget(watermark_btn)
        
        # 批量重命名按钮
        rename_btn = QPushButton("批量重命名")
        rename_btn.clicked.connect(self.show_batch_rename_dialog)
        toolbar2.addWidget(rename_btn)
        
        # 批量格式转换按钮
        convert_btn = QPushButton("格式转换")
        convert_btn.clicked.connect(self.show_batch_format_convert_dialog)
        toolbar2.addWidget(convert_btn)
        
        # 分隔符
        toolbar2.addSeparator()
        
        # 预设下拉菜单
        preset_label = QLabel("快速预设:")
        toolbar2.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "自定义",
            "网络优化 (60%质量)",
            "打印优化 (90%质量)", 
            "移动设备 (75%质量)",
            "极限压缩 (30%质量)"
        ])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        toolbar2.addWidget(self.preset_combo)
    
    def create_file_list_area(self):
        """创建文件列表区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("文件列表")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 文件表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(8)
        self.column_headers = ["文件名", "输出文件名", "尺寸", "原始大小", "压缩大小", "保存空间", "压缩率", "状态"]
        self.file_table.setHorizontalHeaderLabels(self.column_headers)
        
        # 设置表格属性
        header = self.file_table.horizontalHeader()
        header.setStretchLastSection(True)  # 启用最后一列自动拉伸
        header.setSectionsMovable(True)  # 允许列移动
        header.setSectionsClickable(True)  # 允许点击列头排序
        
        # 设置列调整模式
        self.set_column_resize_modes()
        
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.show_context_menu)
        self.file_table.itemDoubleClicked.connect(self.preview_image)
        
        # 设置压缩率列的自定义委托
        self.compression_delegate = CompressionRatioDelegate()
        self.file_table.setItemDelegateForColumn(6, self.compression_delegate)
        
        # 设置行高为25px
        self.file_table.verticalHeader().setDefaultSectionSize(25)
        
        # 设置初始列宽
        self.set_initial_column_widths()
        
        # 应用列显示设置
        self.apply_column_settings()
        
        layout.addWidget(self.file_table)
        
        return widget
    
    def set_column_resize_modes(self):
        """设置列调整模式"""
        header = self.file_table.horizontalHeader()
        
        # 定义每列的调整模式
        resize_modes = {
            0: QHeaderView.Stretch,  # 文件名 - 拉伸
            1: QHeaderView.Stretch,  # 输出文件名 - 拉伸
            2: QHeaderView.ResizeToContents,  # 尺寸 - 内容适应
            3: QHeaderView.ResizeToContents,  # 原始大小 - 内容适应
            4: QHeaderView.ResizeToContents,  # 压缩大小 - 内容适应
            5: QHeaderView.ResizeToContents,  # 保存空间 - 内容适应
            6: QHeaderView.Interactive,  # 压缩率 - 交互式
            7: QHeaderView.Fixed   # 状态 - 固定宽度
        }
        
        # 应用调整模式
        for col, mode in resize_modes.items():
            header.setSectionResizeMode(col, mode)
        
        # 设置状态列为固定宽度30px
        self.file_table.setColumnWidth(7, 30)  # 状态列固定宽度30px
    
    def set_initial_column_widths(self):
        """设置初始列宽"""
        # 定义每列的初始宽度
        column_widths = {
            0: 200,  # 文件名
            1: 200,  # 输出文件名
            2: 100,  # 尺寸
            3: 100,  # 原始大小
            4: 100,  # 压缩大小
            5: 100,  # 保存空间
            6: 120,  # 压缩率
            7: 30    # 状态 - 固定30px
        }
        
        # 应用列宽设置
        for col, width in column_widths.items():
            self.file_table.setColumnWidth(col, width)
    
    def save_column_widths(self):
        """保存列宽设置"""
        # 只保存非拉伸列和非内容适应列的宽度
        saveable_columns = [2, 3, 4, 5, 6]  # 尺寸、大小、压缩率列（排除状态列）
        for i in saveable_columns:
            width = self.file_table.columnWidth(i)
            self.settings.setValue(f"column_width_{i}", width)
    
    def load_column_widths(self):
        """加载列宽设置"""
        # 只加载非拉伸列和非内容适应列的宽度
        saveable_columns = [2, 3, 4, 5, 6]  # 尺寸、大小、压缩率列（排除状态列）
        for i in saveable_columns:
            saved_width = self.settings.value(f"column_width_{i}", 0, int)
            if saved_width > 0:
                self.file_table.setColumnWidth(i, saved_width)
        
        # 状态列使用固定宽度30px
        self.file_table.setColumnWidth(7, 30)
    
    
    def create_settings_area(self):
        """创建设置区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("压缩设置")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # 创建设置选项卡
        tab_widget = QTabWidget()
        
        # 基本设置选项卡
        basic_tab = self.create_basic_settings_tab()
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 高级设置选项卡
        advanced_tab = self.create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "高级设置")
        
        layout.addWidget(tab_widget)
        
        # 进度显示
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        # 线程状态显示
        thread_status_layout = QHBoxLayout()
        thread_status_layout.addWidget(QLabel("当前线程数:"))
        self.thread_count_label = QLabel("0")
        self.thread_count_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        thread_status_layout.addWidget(self.thread_count_label)
        thread_status_layout.addStretch()
        progress_layout.addLayout(thread_status_layout)
        
        # 处理状态显示
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        return widget
    
    def create_basic_settings_tab(self):
        """创建基本设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 输出格式设置
        format_group = QGroupBox("输出格式")
        format_layout = QFormLayout(format_group)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WEBP"])
        format_layout.addRow("格式:", self.format_combo)
        
        layout.addWidget(format_group)
        
        # 质量设置
        quality_group = QGroupBox("压缩质量")
        quality_layout = QVBoxLayout(quality_group)
        
        quality_h_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(85)
        self.quality_slider.valueChanged.connect(self.update_quality_label)
        
        self.quality_label = QLabel("85")
        self.quality_label.setMinimumWidth(30)
        
        quality_h_layout.addWidget(self.quality_slider)
        quality_h_layout.addWidget(self.quality_label)
        quality_layout.addLayout(quality_h_layout)
        
        # 质量预设
        preset_layout = QHBoxLayout()
        low_btn = QPushButton("低质量(50)")
        low_btn.clicked.connect(lambda: self.quality_slider.setValue(50))
        preset_layout.addWidget(low_btn)
        
        medium_btn = QPushButton("中等(75)")
        medium_btn.clicked.connect(lambda: self.quality_slider.setValue(75))
        preset_layout.addWidget(medium_btn)
        
        high_btn = QPushButton("高质量(90)")
        high_btn.clicked.connect(lambda: self.quality_slider.setValue(90))
        preset_layout.addWidget(high_btn)
        
        quality_layout.addLayout(preset_layout)
        layout.addWidget(quality_group)
        
        # 尺寸设置
        size_group = QGroupBox("尺寸调整")
        size_layout = QVBoxLayout(size_group)
        
        self.resize_checkbox = QCheckBox("启用尺寸调整")
        size_layout.addWidget(self.resize_checkbox)
        
        # 调整模式
        mode_layout = QHBoxLayout()
        self.resize_mode_combo = QComboBox()
        self.resize_mode_combo.addItems(["按百分比", "按像素"])
        mode_layout.addWidget(QLabel("模式:"))
        mode_layout.addWidget(self.resize_mode_combo)
        size_layout.addLayout(mode_layout)
        
        # 百分比设置
        percentage_layout = QHBoxLayout()
        self.percentage_spinbox = QSpinBox()
        self.percentage_spinbox.setRange(1, 200)
        self.percentage_spinbox.setValue(80)
        self.percentage_spinbox.setSuffix("%")
        percentage_layout.addWidget(QLabel("百分比:"))
        percentage_layout.addWidget(self.percentage_spinbox)
        percentage_layout.addStretch()
        size_layout.addLayout(percentage_layout)
        
        # 像素设置
        pixel_layout = QGridLayout()
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 10000)
        self.width_spinbox.setValue(1920)
        
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 10000)
        self.height_spinbox.setValue(1080)
        
        pixel_layout.addWidget(QLabel("宽度:"), 0, 0)
        pixel_layout.addWidget(self.width_spinbox, 0, 1)
        pixel_layout.addWidget(QLabel("高度:"), 1, 0)
        pixel_layout.addWidget(self.height_spinbox, 1, 1)
        
        size_layout.addLayout(pixel_layout)
        layout.addWidget(size_group)
        
        layout.addStretch()
        return widget
    
    def create_advanced_settings_tab(self):
        """创建高级设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 输出目录设置
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout(output_group)
        
        dir_layout = QHBoxLayout()
        self.output_dir_line = QLineEdit()
        self.output_dir_line.setPlaceholderText("留空使用源文件目录")
        dir_layout.addWidget(QLabel("输出目录:"))
        dir_layout.addWidget(self.output_dir_line)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(browse_btn)
        
        output_layout.addLayout(dir_layout)
        layout.addWidget(output_group)
        
        # 其他选项
        options_group = QGroupBox("其他选项")
        options_layout = QVBoxLayout(options_group)
        
        self.keep_exif_checkbox = QCheckBox("保留EXIF信息")
        self.keep_exif_checkbox.setChecked(True)
        options_layout.addWidget(self.keep_exif_checkbox)
        
        self.backup_original_checkbox = QCheckBox("备份原文件")
        options_layout.addWidget(self.backup_original_checkbox)
        
        layout.addWidget(options_group)
        
        layout.addStretch()
        return widget
    
    
    def update_quality_label(self, value):
        """更新质量标签"""
        self.quality_label.setText(str(value))
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_line.setText(dir_path)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                files.append(file_path)
            elif os.path.isdir(file_path):
                # 处理文件夹
                for ext in ALL_EXTENSIONS:
                    files.extend(Path(file_path).rglob(f"*{ext}"))
                    files.extend(Path(file_path).rglob(f"*{ext.upper()}"))
        
        self.add_files_to_list([str(f) for f in files])
        event.acceptProposedAction()
    
    def add_files(self):
        """添加文件"""
        file_filter = "图片文件 ("
        for exts in SUPPORTED_FORMATS.values():
            for ext in exts:
                file_filter += f"*{ext} "
        file_filter += ");; 所有文件 (*.*)"
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "", file_filter
        )
        
        if files:
            self.add_files_to_list(files)
    
    def add_folder(self):
        """添加文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self._load_images_from_folder(folder_path)
    
    def set_image_list(self, image_list):
        """设置图片列表
        
        Args:
            image_list: 可以是文件路径列表或文件夹路径列表
                - 文件路径列表: ['/path/to/image1.jpg', '/path/to/image2.png', ...]
                - 文件夹路径列表: ['/path/to/folder1', '/path/to/folder2', ...]
                - 混合列表: ['/path/to/image1.jpg', '/path/to/folder1', ...]
        """
        # 清空当前列表
        self.clear_file_list()
        
        if not image_list:
            return
        
        # 处理每个路径
        for path in image_list:
            if os.path.isfile(path):
                # 单个文件，直接添加到列表
                self.add_files_to_list([path])
            elif os.path.isdir(path):
                # 文件夹，加载文件夹内的所有图片
                self._load_images_from_folder(path)
            else:
                print(f"路径不存在或不是有效的文件/文件夹: {path}")
    
    def _load_images_from_folder(self, folder_path):
        """从文件夹加载图片文件"""
        try:
            files = []
            for ext in ALL_EXTENSIONS:
                # 搜索小写扩展名
                files.extend(Path(folder_path).rglob(f"*{ext}"))
                # 搜索大写扩展名（如果与小写不同）
                if ext != ext.upper():
                    files.extend(Path(folder_path).rglob(f"*{ext.upper()}"))
            
            # 去重处理，避免重复文件
            unique_files = list(set(files))
            
            if unique_files:
                self.add_files_to_list([str(f) for f in unique_files])
                print(f"从文件夹 {folder_path} 加载了 {len(unique_files)} 个图片文件")
            else:
                print(f"文件夹 {folder_path} 中没有找到支持的图片文件")
        except Exception as e:
            print(f"加载文件夹 {folder_path} 失败: {e}")
    
    def demo_set_image_list(self):
        """演示如何使用set_image_list函数"""
        # 示例1: 文件路径列表
        file_list = [
            "C:/Users/username/Pictures/image1.jpg",
            "C:/Users/username/Pictures/image2.png",
            "C:/Users/username/Pictures/image3.webp"
        ]
        self.set_image_list(file_list)
        
        # 示例2: 文件夹路径列表
        folder_list = [
            "C:/Users/username/Pictures/Photos",
            "C:/Users/username/Pictures/Screenshots"
        ]
        self.set_image_list(folder_list)
        
        # 示例3: 混合列表（文件和文件夹）
        mixed_list = [
            "C:/Users/username/Pictures/image1.jpg",  # 单个文件
            "C:/Users/username/Pictures/Photos",      # 文件夹
            "C:/Users/username/Pictures/image2.png"   # 单个文件
        ]
        self.set_image_list(mixed_list)

    def add_files_to_list(self, file_paths):
        """添加文件到列表"""
        for file_path in file_paths:
            if not os.path.isfile(file_path):
                continue
            
            # 检查是否已存在
            if any(f['path'] == file_path for f in self.file_list):
                continue
            
            # 检查文件格式
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ALL_EXTENSIONS:
                continue
            
            try:
                # 获取文件信息
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                
                # 获取图片尺寸
                try:
                    with Image.open(file_path) as image:
                        dimensions = f"{image.width}×{image.height}"
                except:
                    dimensions = "未知"
                
                file_info = {
                    'path': file_path,
                    'name': os.path.basename(file_path),
                    'size': file_size,
                    'dimensions': dimensions,
                    'status': '待处理'
                }
                
                self.file_list.append(file_info)
                
                # 使用新的添加方法
                self._add_file_to_table(file_info)
                
            except Exception as e:
                print(f"添加文件失败 {file_path}: {e}")
    
    def remove_file(self, row):
        """移除文件"""
        if 0 <= row < len(self.file_list):
            self.file_list.pop(row)
            self.file_table.removeRow(row)
    
    def clear_file_list(self):
        """清空文件列表"""
        self.file_list.clear()
        self.file_table.setRowCount(0)
    
    def preview_image(self, item):
        """预览图片"""
        row = item.row()
        if 0 <= row < len(self.file_list):
            file_path = self.file_list[row]['path']
            self.preview_image_by_path(file_path)
    
    def preview_image_by_path(self, file_path):
        """通过路径预览图片"""
        dialog = ImagePreviewDialog(file_path, self)
        dialog.exec_()
    
    def start_compression(self):
        """开始压缩"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先添加要压缩的图片文件")
            return
        
        # 获取设置
        settings = self.get_compression_settings()
        
        # 添加水印设置
        settings['watermark'] = self.watermark_settings
        
        # 重置统计信息
        self.processing_stats = {
            'total_files': len(self.file_list),
            'success_count': 0,
            'error_count': 0,
            'total_original_size': sum(os.path.getsize(f['path']) for f in self.file_list),
            'total_compressed_size': 0,
            'processing_time': 0,
            'start_time': time.time()
        }
        
        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 重置状态
        for i in range(len(self.file_list)):
            self.file_table.setItem(i, 7, QTableWidgetItem("处理中..."))
        
        # 获取线程数设置
        thread_count = settings.get('thread_count', 4)
        thread_count = min(thread_count, len(self.file_list))  # 不超过文件数量
        
        # 清理之前的线程
        if hasattr(self, 'compression_workers'):
            self.compression_workers = []
        
        # 如果只有一个线程，使用单线程模式
        if thread_count == 1:
            self.compression_worker = ImageCompressionWorker(self.file_list.copy(), settings)
            self.compression_worker.progress_updated.connect(self.update_progress)
            self.compression_worker.file_processed.connect(self.update_file_status)
            self.compression_worker.finished.connect(self.compression_finished)
            self.compression_worker.file_stats_updated.connect(self.update_processing_stats)
            self.compression_worker.file_info_updated.connect(self.update_file_info)
            self.compression_worker.start()
            
            # 更新线程数和状态显示
            self.active_thread_count = 1
            self.update_thread_count_display()
            self.update_status_display("压缩中...")
        else:
            # 多线程模式
            self.compression_workers = []
            self.compression_thread_count = thread_count
            self.finished_thread_count = 0
            
            # 创建多个工作线程
            for i in range(thread_count):
                worker = MultiThreadImageCompressionWorker(
                    self.file_list.copy(), settings, i, thread_count
                )
                worker.file_processed.connect(self.update_file_status)
                worker.file_stats_updated.connect(self.update_processing_stats)
                worker.file_info_updated.connect(self.update_file_info)
                worker.thread_finished.connect(self.on_compression_thread_finished)
                
                self.compression_workers.append(worker)
                worker.start()
            
            # 更新线程数和状态显示
            self.active_thread_count = thread_count
            self.update_thread_count_display()
            self.update_status_display(f"压缩中... ({thread_count}个线程)")
            
            # 启动进度更新定时器
            self.start_compression_progress_timer()
    
    def on_compression_thread_finished(self):
        """单个压缩线程完成"""
        self.finished_thread_count += 1
        
        # 检查是否所有线程都完成了
        if self.finished_thread_count >= self.compression_thread_count:
            self.compression_finished()
    
    def start_compression_progress_timer(self):
        """启动压缩进度更新定时器"""
        from PyQt5.QtCore import QTimer
        self.compression_progress_timer = QTimer()
        self.compression_progress_timer.timeout.connect(self.update_multi_thread_compression_progress)
        self.compression_progress_timer.start(500)  # 每500ms更新一次进度
    
    def update_multi_thread_compression_progress(self):
        """更新多线程压缩进度"""
        if not hasattr(self, 'compression_workers') or not self.compression_workers:
            return
        
        # 检查是否所有线程都已完成
        if self.finished_thread_count >= self.compression_thread_count:
            # 所有线程完成，设置进度为100%
            self.progress_bar.setValue(100)
        else:
            # 计算总体进度
            total_files = len(self.file_list)
            completed_files = self.processing_stats.get('success_count', 0) + self.processing_stats.get('error_count', 0)
            
            if total_files > 0:
                progress = int((completed_files * 100) / total_files)
                self.progress_bar.setValue(progress)
    
    def stop_compression(self):
        """停止压缩或转换"""
        if self.compression_worker:
            self.compression_worker.stop()
            # 使用异步方式等待线程结束，避免UI阻塞
            self.async_wait_for_worker(self.compression_worker, 'compression')
            self.update_status_display("正在停止压缩...")
        elif hasattr(self, 'compression_workers') and self.compression_workers:
            # 停止所有压缩线程
            for worker in self.compression_workers:
                worker.stop()
            # 使用异步方式等待所有线程结束
            self.async_wait_for_compression_workers(self.compression_workers)
            self.update_status_display("正在停止压缩...")
        elif self.conversion_worker:
            self.conversion_worker.stop()
            # 使用异步方式等待线程结束，避免UI阻塞
            self.async_wait_for_worker(self.conversion_worker, 'conversion')
            self.update_status_display("正在停止转换...")
        elif hasattr(self, 'conversion_workers') and self.conversion_workers:
            # 停止所有转换线程
            for worker in self.conversion_workers:
                worker.stop()
            # 使用异步方式等待所有线程结束
            self.async_wait_for_workers(self.conversion_workers)
            self.update_status_display("正在停止转换...")
    
    def async_wait_for_worker(self, worker, worker_type):
        """异步等待单个工作线程结束"""
        from PyQt5.QtCore import QTimer
        
        def check_worker():
            if not worker.isRunning():
                if worker_type == 'compression':
                    self.compression_worker = None
                    self.update_status_display("压缩已停止")
                elif worker_type == 'conversion':
                    self.conversion_worker = None
                    self.update_status_display("转换已停止")
                # 更新线程数显示
                self.active_thread_count = 0
                self.update_thread_count_display()
                timer.stop()
            else:
                # 如果线程还在运行，继续检查
                timer.start(50)  # 50ms后再次检查
        
        timer = QTimer()
        timer.timeout.connect(check_worker)
        timer.start(50)  # 立即开始检查
    
    def async_wait_for_workers(self, workers):
        """异步等待多个工作线程结束"""
        from PyQt5.QtCore import QTimer
        
        def check_workers():
            running_workers = [w for w in workers if w.isRunning()]
            if not running_workers:
                # 所有线程都已结束
                # 更新状态为暂停
                for i in range(len(self.file_list)):
                    current_status = self.file_table.item(i, 7)
                    if current_status and current_status.text() == "转换中...":
                        self.file_table.setItem(i, 7, QTableWidgetItem("暂停"))
                
                # 清理线程列表
                self.conversion_workers = []
                # 更新线程数和状态显示
                self.active_thread_count = 0
                self.update_thread_count_display()
                self.update_status_display("转换已停止")
                timer.stop()
            else:
                # 还有线程在运行，继续检查
                timer.start(50)  # 50ms后再次检查
        
        timer = QTimer()
        timer.timeout.connect(check_workers)
        timer.start(50)  # 立即开始检查
    
    def async_wait_for_compression_workers(self, workers):
        """异步等待多个压缩工作线程结束"""
        from PyQt5.QtCore import QTimer
        
        def check_workers():
            running_workers = [w for w in workers if w.isRunning()]
            if not running_workers:
                # 所有线程都已结束
                # 更新状态为暂停
                for i in range(len(self.file_list)):
                    current_status = self.file_table.item(i, 7)
                    if current_status and current_status.text() == "处理中...":
                        self.file_table.setItem(i, 7, QTableWidgetItem("暂停"))
                
                # 清理线程列表
                self.compression_workers = []
                # 更新线程数和状态显示
                self.active_thread_count = 0
                self.update_thread_count_display()
                self.update_status_display("压缩已停止")
                timer.stop()
            else:
                # 还有线程在运行，继续检查
                timer.start(50)  # 50ms后再次检查
        
        timer = QTimer()
        timer.timeout.connect(check_workers)
        timer.start(50)  # 立即开始检查
    
    def update_thread_count_display(self):
        """更新线程数显示"""
        if hasattr(self, 'thread_count_label'):
            self.thread_count_label.setText(str(self.active_thread_count))
    
    def update_status_display(self, status):
        """更新状态显示"""
        if hasattr(self, 'status_label'):
            self.status_label.setText(status)
            # 根据状态设置不同的颜色
            if "处理中" in status or "转换中" in status:
                self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            elif "完成" in status or "就绪" in status:
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif "错误" in status or "失败" in status:
                self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            else:
                self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
    
    def compression_finished(self):
        """压缩完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # 停止压缩进度定时器
        if hasattr(self, 'compression_progress_timer'):
            self.compression_progress_timer.stop()
        
        # 确保进度条显示100%
        self.progress_bar.setValue(100)
        
        # 计算处理时间
        if 'start_time' in self.processing_stats:
            self.processing_stats['processing_time'] = time.time() - self.processing_stats['start_time']
        
        # 显示处理统计
        if self.processing_stats['total_files'] > 0:
            self.show_stats_dialog(self.processing_stats)
        
        # 更新线程数和状态显示
        self.active_thread_count = 0
        self.update_thread_count_display()
        self.update_status_display("压缩完成")
        
        # 清理线程
        self.compression_worker = None
        if hasattr(self, 'compression_workers'):
            self.compression_workers = []
        self.compression_thread_count = 0
        self.finished_thread_count = 0
    
    def get_compression_settings(self):
        """获取压缩设置"""
        # 获取线程数设置
        thread_count = self.settings.value("thread_count", 4, int)
        thread_count = min(thread_count, len(self.file_list)) if self.file_list else thread_count
        
        settings = {
            'quality': self.quality_slider.value(),
            'output_format': self.format_combo.currentText(),
            'resize_enabled': self.resize_checkbox.isChecked(),
            'resize_mode': 'percentage' if self.resize_mode_combo.currentText() == '按百分比' else 'pixel',
            'resize_percentage': self.percentage_spinbox.value(),
            'resize_width': self.width_spinbox.value(),
            'resize_height': self.height_spinbox.value(),
            'keep_exif': self.keep_exif_checkbox.isChecked(),
            'output_dir': self.output_dir_line.text().strip() or None,
            'thread_count': thread_count
        }
        return settings
    
    def update_progress(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def update_file_status(self, row, status, message):
        """更新文件状态"""
        if 0 <= row < self.file_table.rowCount():
            # 状态列只显示完成/失败
            if status == "完成":
                self.file_table.setItem(row, 7, QTableWidgetItem("完成"))
            elif status == "错误":
                self.file_table.setItem(row, 7, QTableWidgetItem("失败"))
            else:
                self.file_table.setItem(row, 7, QTableWidgetItem("处理中..."))
            
            
            # 如果压缩完成，更新压缩信息
            if status == "完成" and row < len(self.file_list):
                file_info = self.file_list[row]
                if 'compressed_size' in file_info:
                    # 更新压缩大小
                    if self.column_settings.get(4, True):
                        compressed_size_mb = file_info['compressed_size'] / (1024 * 1024)
                        self.file_table.setItem(row, 4, QTableWidgetItem(f"{compressed_size_mb:.2f} MB"))
                    
                    # 更新保存空间
                    if self.column_settings.get(5, True) and 'saved_space' in file_info:
                        saved_space_mb = file_info['saved_space'] / (1024 * 1024)
                        self.file_table.setItem(row, 5, QTableWidgetItem(f"{saved_space_mb:.2f} MB"))
                    
                    # 更新压缩率
                    if self.column_settings.get(6, True) and 'compression_ratio' in file_info:
                        compression_ratio = file_info['compression_ratio']
                        ratio_item = QTableWidgetItem()
                        ratio_item.setText(f"{compression_ratio:.1f}%")
                        ratio_item.setData(Qt.UserRole, compression_ratio)
                        self.file_table.setItem(row, 6, ratio_item)
    
    def update_processing_stats(self, success, compressed_size):
        """更新处理统计"""
        if success:
            self.processing_stats['success_count'] += 1
            self.processing_stats['total_compressed_size'] += compressed_size
        else:
            self.processing_stats['error_count'] += 1
    
    def update_file_info(self, row, file_info):
        """更新文件信息"""
        if 0 <= row < len(self.file_list):
            # 更新主文件列表中的信息
            self.file_list[row].update(file_info)
            
            # 更新表格显示
            if 'compressed_size' in file_info:
                # 更新输出文件名
                if self.column_settings.get(1, True) and 'output_filename' in file_info:
                    self.file_table.setItem(row, 1, QTableWidgetItem(file_info['output_filename']))
                
                # 更新压缩大小
                if self.column_settings.get(4, True):
                    compressed_size_mb = file_info['compressed_size'] / (1024 * 1024)
                    self.file_table.setItem(row, 4, QTableWidgetItem(f"{compressed_size_mb:.2f} MB"))
                
                # 更新保存空间
                if self.column_settings.get(5, True):
                    saved_space_mb = file_info['saved_space'] / (1024 * 1024)
                    self.file_table.setItem(row, 5, QTableWidgetItem(f"{saved_space_mb:.2f} MB"))
                
                # 更新压缩率
                if self.column_settings.get(6, True):
                    compression_ratio = file_info['compression_ratio']
                    ratio_item = QTableWidgetItem()
                    ratio_item.setText(f"{compression_ratio:.1f}%")
                    ratio_item.setData(Qt.UserRole, compression_ratio)
                    self.file_table.setItem(row, 6, ratio_item)
    
    
    def show_advanced_settings(self):
        """显示高级设置"""
        dialog = SettingsDialog(self)
        dialog.exec_()
    
    def show_watermark_dialog(self):
        """显示水印设置对话框"""
        dialog = WatermarkDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.watermark_settings = dialog.get_watermark_settings()
    
    def show_batch_rename_dialog(self):
        """显示批量重命名对话框"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先添加文件再进行批量重命名")
            return
        
        dialog = BatchRenameDialog(self.file_list, self)
        if dialog.exec_() == QDialog.Accepted:
            rename_settings = dialog.get_rename_settings()
            self.apply_batch_rename(rename_settings)
    
    def show_batch_format_convert_dialog(self):
        """显示批量格式转换对话框"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先添加文件再进行格式转换")
            return
        
        dialog = BatchFormatConvertDialog(self.file_list, self)
        if dialog.exec_() == QDialog.Accepted:
            conversion_settings = dialog.get_conversion_settings()
            self.start_format_conversion(conversion_settings)
    
    def apply_batch_rename(self, settings):
        """应用批量重命名"""
        try:
            for i, file_info in enumerate(self.file_list):
                original_path = file_info['path']
                original_name = file_info['name']
                name_without_ext = os.path.splitext(original_name)[0]
                ext = os.path.splitext(original_name)[1]
                
                new_name = settings['prefix']
                if settings['use_numbering']:
                    new_name += f"{settings['start_number'] + i:04d}_"
                new_name += name_without_ext + settings['suffix'] + ext
                
                # 更新文件列表中的显示名称
                file_info['display_name'] = new_name
                self.file_table.setItem(i, 0, QTableWidgetItem(new_name))
            
            QMessageBox.information(self, "成功", "批量重命名规则已应用")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量重命名失败: {str(e)}")
    
    def start_format_conversion(self, settings):
        """开始格式转换"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先添加要转换的图片文件")
            return
        
        # 获取线程数设置
        thread_count = self.settings.value("thread_count", 4, int)
        thread_count = min(thread_count, len(self.file_list))  # 不超过文件数量
        
        # 重置统计信息
        self.processing_stats = {
            'total_files': len(self.file_list),
            'success_count': 0,
            'error_count': 0,
            'total_original_size': sum(os.path.getsize(f['path']) for f in self.file_list),
            'total_compressed_size': 0,
            'processing_time': 0,
            'start_time': time.time()
        }
        
        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 重置状态
        for i in range(len(self.file_list)):
            self.file_table.setItem(i, 7, QTableWidgetItem("转换中..."))
        
        # 清理之前的线程
        if hasattr(self, 'conversion_workers'):
            self.conversion_workers = []
        
        # 如果只有一个线程，使用单线程模式
        if thread_count == 1:
            self.conversion_worker = ImageFormatConvertWorker(self.file_list.copy(), settings)
            self.conversion_worker.progress_updated.connect(self.update_progress)
            self.conversion_worker.file_processed.connect(self.update_file_status)
            self.conversion_worker.finished.connect(self.conversion_finished)
            self.conversion_worker.file_stats_updated.connect(self.update_processing_stats)
            self.conversion_worker.file_info_updated.connect(self.update_file_info)
            self.conversion_worker.start()
            
            # 更新线程数和状态显示
            self.active_thread_count = 1
            self.update_thread_count_display()
            self.update_status_display("转换中...")
        else:
            # 多线程模式
            self.conversion_workers = []
            self.conversion_thread_count = thread_count
            self.finished_thread_count = 0
            
            # 创建多个工作线程
            for i in range(thread_count):
                worker = MultiThreadFormatConvertWorker(
                    self.file_list.copy(), settings, i, thread_count
                )
                worker.file_processed.connect(self.update_file_status)
                worker.file_stats_updated.connect(self.update_processing_stats)
                worker.file_info_updated.connect(self.update_file_info)
                worker.thread_finished.connect(self.on_conversion_thread_finished)
                
                self.conversion_workers.append(worker)
                worker.start()
            
            # 更新线程数和状态显示
            self.active_thread_count = thread_count
            self.update_thread_count_display()
            self.update_status_display(f"转换中... ({thread_count}个线程)")
            
            # 启动进度更新定时器
            self.start_progress_timer()
    
    def on_conversion_thread_finished(self):
        """单个转换线程完成"""
        self.finished_thread_count += 1
        
        # 检查是否所有线程都完成了
        if self.finished_thread_count >= self.conversion_thread_count:
            self.conversion_finished()
    
    def start_progress_timer(self):
        """启动进度更新定时器"""
        from PyQt5.QtCore import QTimer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_multi_thread_progress)
        self.progress_timer.start(500)  # 每500ms更新一次进度
    
    def update_multi_thread_progress(self):
        """更新多线程进度"""
        if not hasattr(self, 'conversion_workers') or not self.conversion_workers:
            return
        
        # 检查是否所有线程都已完成
        if self.finished_thread_count >= self.conversion_thread_count:
            # 所有线程完成，设置进度为100%
            self.progress_bar.setValue(100)
        else:
            # 计算总体进度
            total_files = len(self.file_list)
            completed_files = self.processing_stats.get('success_count', 0) + self.processing_stats.get('error_count', 0)
            
            if total_files > 0:
                progress = int((completed_files * 100) / total_files)
                self.progress_bar.setValue(progress)
    
    def conversion_finished(self):
        """格式转换完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # 停止进度定时器
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        
        # 确保进度条显示100%
        self.progress_bar.setValue(100)
        
        # 计算处理时间
        if 'start_time' in self.processing_stats:
            self.processing_stats['processing_time'] = time.time() - self.processing_stats['start_time']
        
        # 显示处理统计
        if self.processing_stats['total_files'] > 0:
            self.show_stats_dialog(self.processing_stats)
        
        # 更新线程数和状态显示
        self.active_thread_count = 0
        self.update_thread_count_display()
        self.update_status_display("转换完成")
        
        # 清理线程
        self.conversion_worker = None
        if hasattr(self, 'conversion_workers'):
            self.conversion_workers = []
        self.conversion_thread_count = 0
        self.finished_thread_count = 0
    
    def apply_preset(self, preset_type):
        """应用压缩预设"""
        presets = {
            'web': {
                'quality': 60,
                'resize_enabled': True,
                'resize_mode': 'pixel',
                'resize_width': 800,
                'resize_height': 600,
                'format': 'JPEG'
            },
            'print': {
                'quality': 90,
                'resize_enabled': False,
                'format': 'JPEG'
            },
            'mobile': {
                'quality': 75,
                'resize_enabled': True,
                'resize_mode': 'pixel',
                'resize_width': 1080,
                'resize_height': 1920,
                'format': 'JPEG'
            },
            'extreme': {
                'quality': 30,
                'resize_enabled': True,
                'resize_mode': 'percentage',
                'resize_percentage': 70,
                'format': 'JPEG'
            }
        }
        
        if preset_type in presets:
            preset = presets[preset_type]
            
            # 应用质量设置
            self.quality_slider.setValue(preset['quality'])
            
            # 应用格式设置
            self.format_combo.setCurrentText(preset['format'])
            
            # 应用尺寸设置
            self.resize_checkbox.setChecked(preset.get('resize_enabled', False))
            
            if preset.get('resize_enabled'):
                if preset.get('resize_mode') == 'pixel':
                    self.resize_mode_combo.setCurrentText('按像素')
                    self.width_spinbox.setValue(preset.get('resize_width', 1920))
                    self.height_spinbox.setValue(preset.get('resize_height', 1080))
                elif preset.get('resize_mode') == 'percentage':
                    self.resize_mode_combo.setCurrentText('按百分比')
                    self.percentage_spinbox.setValue(preset.get('resize_percentage', 80))
            
            # 重置预设选择器
            self.preset_combo.setCurrentIndex(0)
            
    
    def on_preset_changed(self, preset_name):
        """预设改变时的处理"""
        if preset_name == "网络优化 (60%质量)":
            self.apply_preset('web')
        elif preset_name == "打印优化 (90%质量)":
            self.apply_preset('print')
        elif preset_name == "移动设备 (75%质量)":
            self.apply_preset('mobile')
        elif preset_name == "极限压缩 (30%质量)":
            self.apply_preset('extreme')
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        if self.file_table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        
        # 预览选中文件
        preview_action = QAction("预览", self)
        preview_action.triggered.connect(self.preview_selected_image)
        menu.addAction(preview_action)
        
        menu.addSeparator()
        
        # 删除选中文件
        delete_selected_action = QAction("删除选中文件", self)
        delete_selected_action.triggered.connect(self.delete_selected_files)
        menu.addAction(delete_selected_action)
        
        # 删除全部文件
        delete_all_action = QAction("删除全部文件", self)
        delete_all_action.triggered.connect(self.delete_all_files)
        menu.addAction(delete_all_action)
        
        menu.addSeparator()
        
        # 压缩选中文件
        compress_selected_action = QAction("压缩选中文件", self)
        compress_selected_action.triggered.connect(self.compress_selected_files)
        menu.addAction(compress_selected_action)
        
        # 转换选中文件格式
        convert_selected_action = QAction("转换选中文件格式", self)
        convert_selected_action.triggered.connect(self.convert_selected_files)
        menu.addAction(convert_selected_action)
        
        menu.addSeparator()
        
        # 列设置
        column_settings_action = QAction("列设置", self)
        column_settings_action.triggered.connect(self.show_column_settings)
        menu.addAction(column_settings_action)
        
        # 显示菜单
        menu.exec_(self.file_table.mapToGlobal(position))
    
    def show_column_settings(self):
        """显示列设置对话框"""
        dialog = ColumnSettingsDialog(self.column_settings, self)
        if dialog.exec_() == QDialog.Accepted:
            self.column_settings = dialog.get_column_settings()
            self.apply_column_settings()
            self.refresh_file_list()
    
    def apply_column_settings(self):
        """应用列显示设置"""
        for col_index, visible in self.column_settings.items():
            self.file_table.setColumnHidden(col_index, not visible)
    
    def refresh_file_list(self):
        """刷新文件列表显示"""
        # 清空表格
        self.file_table.setRowCount(0)
        
        # 重新添加所有文件
        for file_info in self.file_list:
            self._add_file_to_table(file_info)
    
    def _add_file_to_table(self, file_info):
        """将文件信息添加到表格中"""
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        
        # 只在可见列中添加内容
        if self.column_settings.get(0, True):  # 文件名
            self.file_table.setItem(row, 0, QTableWidgetItem(file_info['name']))
        
        if self.column_settings.get(1, True):  # 输出文件名
            output_filename = file_info.get('output_filename', '-')
            self.file_table.setItem(row, 1, QTableWidgetItem(output_filename))
        
        if self.column_settings.get(2, True):  # 尺寸
            dimensions = file_info.get('dimensions', '未知')
            self.file_table.setItem(row, 2, QTableWidgetItem(dimensions))
        
        if self.column_settings.get(3, True):  # 原始大小
            original_size_mb = file_info['size']
            self.file_table.setItem(row, 3, QTableWidgetItem(f"{original_size_mb:.2f} MB"))
        
        if self.column_settings.get(4, True):  # 压缩大小
            compressed_size = file_info.get('compressed_size', 0)
            if compressed_size > 0:
                compressed_size_mb = compressed_size / (1024 * 1024)
                self.file_table.setItem(row, 4, QTableWidgetItem(f"{compressed_size_mb:.2f} MB"))
            else:
                self.file_table.setItem(row, 4, QTableWidgetItem("-"))
        
        if self.column_settings.get(5, True):  # 保存空间
            saved_space = file_info.get('saved_space', 0)
            if saved_space > 0:
                saved_space_mb = saved_space / (1024 * 1024)
                self.file_table.setItem(row, 5, QTableWidgetItem(f"{saved_space_mb:.2f} MB"))
            else:
                self.file_table.setItem(row, 5, QTableWidgetItem("-"))
        
        if self.column_settings.get(6, True):  # 压缩率
            compression_ratio = file_info.get('compression_ratio', 0)
            if compression_ratio > 0:
                # 创建带可视化进度条的压缩率显示
                ratio_item = QTableWidgetItem()
                ratio_item.setText(f"{compression_ratio:.1f}%")
                
                # 设置进度条样式
                ratio_item.setData(Qt.UserRole, compression_ratio)
                self.file_table.setItem(row, 6, ratio_item)
            else:
                self.file_table.setItem(row, 6, QTableWidgetItem("-"))
        
        if self.column_settings.get(7, True):  # 状态
            self.file_table.setItem(row, 7, QTableWidgetItem(file_info['status']))
    
    def preview_selected_image(self):
        """预览选中的图片"""
        current_row = self.file_table.currentRow()
        if 0 <= current_row < len(self.file_list):
            file_path = self.file_list[current_row]['path']
            self.preview_image_by_path(file_path)
    
    def delete_selected_files(self):
        """删除选中的文件"""
        selected_rows = set()
        for item in self.file_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要删除的文件")
            return
        
        # 按行号倒序排列，从后往前删除
        sorted_rows = sorted(selected_rows, reverse=True)
        
        for row in sorted_rows:
            if 0 <= row < len(self.file_list):
                self.file_list.pop(row)
                self.file_table.removeRow(row)
    
    def delete_all_files(self):
        """删除全部文件"""
        if not self.file_list:
            QMessageBox.information(self, "提示", "文件列表为空")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除全部 {len(self.file_list)} 个文件吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.clear_file_list()
    
    def compress_selected_files(self):
        """压缩选中的文件"""
        selected_rows = set()
        for item in self.file_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要压缩的文件")
            return
        
        # 创建选中文件的临时列表
        selected_files = []
        for row in sorted(selected_rows):
            if 0 <= row < len(self.file_list):
                selected_files.append(self.file_list[row])
        
        if not selected_files:
            return
        
        # 临时替换文件列表
        original_file_list = self.file_list.copy()
        self.file_list = selected_files
        
        # 开始压缩
        self.start_compression()
        
        # 恢复原始文件列表
        self.file_list = original_file_list
    
    def convert_selected_files(self):
        """转换选中的文件格式"""
        selected_rows = set()
        for item in self.file_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要转换格式的文件")
            return
        
        # 创建选中文件的临时列表
        selected_files = []
        for row in sorted(selected_rows):
            if 0 <= row < len(self.file_list):
                selected_files.append(self.file_list[row])
        
        if not selected_files:
            return
        
        # 显示格式转换对话框
        dialog = BatchFormatConvertDialog(selected_files, self)
        if dialog.exec_() == QDialog.Accepted:
            conversion_settings = dialog.get_conversion_settings()
            
            # 临时替换文件列表
            original_file_list = self.file_list.copy()
            self.file_list = selected_files
            
            # 开始转换
            self.start_format_conversion(conversion_settings)
            
            # 恢复原始文件列表
            self.file_list = original_file_list
    
    def show_stats_dialog(self, stats_data):
        """显示处理统计对话框"""
        dialog = StatsDialog(stats_data, self)
        dialog.exec_()
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(
            self, 
            "关于图片压缩工具", 
            "🖼️ 图片压缩工具 v1.0\n\n"
            "使用PyQt5和Pyvips实现的高效图片压缩工具\n"
            "支持多种图片格式的压缩和尺寸调整\n\n"
            "🌟 功能特色:\n"
            "• 支持JPEG、PNG、WEBP、HEIC等格式\n"
            "• 批量处理和拖拽操作\n"
            "• 灵活的压缩和尺寸设置\n"
            "• 实时预览和进度显示\n"
            "• 水印添加功能\n"
            "• 批量重命名\n"
            "• 快速预设模式\n"
            "• EXIF信息处理\n"
            "• 详细处理统计\n\n"
            "💡 使用技巧:\n"
            "• 直接拖拽文件到界面快速添加\n"
            "• 双击文件可预览图片\n"
            "• 使用快速预设可一键应用常用设置\n"
            "• 支持Ctrl+O快速添加文件"
        )
    
    def load_settings(self):
        """加载设置"""
        self.quality_slider.setValue(self.settings.value("quality", 85, int))
        self.format_combo.setCurrentText(self.settings.value("format", "JPEG"))
        self.resize_checkbox.setChecked(self.settings.value("resize_enabled", False, bool))
        self.percentage_spinbox.setValue(self.settings.value("resize_percentage", 80, int))
        self.width_spinbox.setValue(self.settings.value("resize_width", 1920, int))
        self.height_spinbox.setValue(self.settings.value("resize_height", 1080, int))
        self.keep_exif_checkbox.setChecked(self.settings.value("keep_exif", True, bool))
        self.output_dir_line.setText(self.settings.value("output_dir", ""))
        
        # 加载列显示设置
        for i in range(8):
            self.column_settings[i] = self.settings.value(f"column_{i}", True, bool)
        
        # 加载列宽设置
        self.load_column_widths()
        
        # 加载线程数设置（用于格式转换）
        # 注意：这个设置会在start_format_conversion中读取
    
    def closeEvent(self, event):
        """关闭事件"""
        # 保存设置
        self.settings.setValue("quality", self.quality_slider.value())
        self.settings.setValue("format", self.format_combo.currentText())
        self.settings.setValue("resize_enabled", self.resize_checkbox.isChecked())
        self.settings.setValue("resize_percentage", self.percentage_spinbox.value())
        self.settings.setValue("resize_width", self.width_spinbox.value())
        self.settings.setValue("resize_height", self.height_spinbox.value())
        self.settings.setValue("keep_exif", self.keep_exif_checkbox.isChecked())
        self.settings.setValue("output_dir", self.output_dir_line.text())
        
        # 保存列显示设置
        for i, visible in self.column_settings.items():
            self.settings.setValue(f"column_{i}", visible)
        
        # 保存列宽设置
        self.save_column_widths()
        
        # 停止压缩和转换线程
        if self.compression_worker:
            self.compression_worker.stop()
            self.compression_worker.wait()
        if hasattr(self, 'compression_workers') and self.compression_workers:
            for worker in self.compression_workers:
                worker.stop()
            for worker in self.compression_workers:
                worker.wait()
        if self.conversion_worker:
            self.conversion_worker.stop()
            self.conversion_worker.wait()
        if hasattr(self, 'conversion_workers') and self.conversion_workers:
            for worker in self.conversion_workers:
                worker.stop()
            for worker in self.conversion_workers:
                worker.wait()
        # 停止进度定时器
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        if hasattr(self, 'compression_progress_timer'):
            self.compression_progress_timer.stop()
        
        event.accept()




if __name__ == '__main__':
    # image_list  = [r"D:\o19\image\0616\0616 O19国际二供FT1原图\0616 O19国际二供FT1原图\HDR\N12]
    app = QApplication(sys.argv)
    window = PicZipMainWindow()
    window.show()
    sys.exit(app.exec_())
