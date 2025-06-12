# -*- coding: utf-8 -*-
import os
import numpy as np
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
from contextlib import contextmanager

@contextmanager
def image_resource_manager(images):
    """图片资源管理器"""
    try:
        yield
    finally:
        for img in images:
            try:
                img.close()
            except:
                pass

def load_and_convert_image(path):
    """加载并转换单张图片"""
    try:
        img = Image.open(path)
        # 移除ICC配置文件
        if 'icc_profile' in img.info:
            del img.info['icc_profile']
        return img.convert('RGB') if img.mode != 'RGB' else img
    except Exception as e:
        print(f"加载图片 {path} 失败: {str(e)}")
        return None

def resize_image(img, target_size):
    """调整单张图片大小"""
    return img.resize(target_size, Image.Resampling.LANCZOS)

def calculate_target_size(images, max_width, max_height):
    """计算目标尺寸"""
    aspect_ratios = np.array([img.width / img.height for img in images])
    avg_aspect_ratio = np.mean(aspect_ratios)
    
    height = int(max_width / (avg_aspect_ratio * len(images)))
    if height > max_height:
        return (int(max_height * avg_aspect_ratio), max_height)
    return (int(max_width / len(images)), height)

def load_font(font_path, font_size):
    """加载字体"""
    try:
        return ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
    except:
        return ImageFont.load_default()

def stitch_images(image_paths, output_path, font_path, max_width=1920, max_height=1080, font_size=20, num_workers=4):
    """
    将多张图片水平拼接成一张大图，并在每张图片上方显示文件名
    
    参数:
        image_paths: 图片路径列表
        output_path: 输出图片的保存路径
        font_path: 字体路径
        max_width: 最大宽度，默认1920像素
        max_height: 最大高度，默认1080像素
        font_size: 文件名文字大小，默认20像素
        num_workers: 并行处理的工作线程数，默认4
    """
    try:
        # 检查并创建输出路径
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 并行加载图片
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            images = list(filter(None, executor.map(load_and_convert_image, image_paths)))
        
        if not images:
            print("没有成功加载任何图片")
            return False

        # 使用资源管理器确保图片资源被正确释放
        with image_resource_manager(images):
            # 计算目标尺寸
            target_size = calculate_target_size(images, max_width, max_height)
            
            # 并行调整图片大小
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                resize_func = partial(resize_image, target_size=target_size)
                resized_images = list(executor.map(resize_func, images))
            
            # 计算画布尺寸
            text_height = font_size + 10
            total_width = target_size[0] * len(resized_images)
            total_height = target_size[1] + text_height
            
            # 创建画布和绘图对象
            result = Image.new('RGB', (total_width, total_height), 'white')
            draw = ImageDraw.Draw(result)
            
            # 加载字体
            font = load_font(font_path, font_size)
            
            # 拼接图片并添加文字
            x_offset = 0
            for img, path in zip(resized_images, image_paths):
                filename = f"{os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}"
                result.paste(img, (x_offset, text_height))
                draw.text((x_offset, 5), filename, fill='black', font=font)
                x_offset += target_size[0]
            
            # 保存结果，移除ICC配置文件
            if 'icc_profile' in result.info:
                del result.info['icc_profile']
            result.save(output_path, 
                       quality=100,
                       optimize=True,
                       subsampling=0)
            
            return True
            
    except Exception as e:
        print(f"拼接图片时发生错误: {str(e)}")
        return False