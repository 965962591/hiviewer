# -*- encoding: utf-8 -*-
'''
@File         :hiviewer.py
@Time         :2025/06/04
@Author       :diamond_cz@163.com
@Version      :release-v3.5.2
@Description  :处理图片, 获取基础的exif信息
'''

from PIL import Image
from pathlib import Path
from fractions import Fraction
from typing import Optional, Dict, Any

# 设置视频首帧图缓存路径
BASEICONPATH = Path(__file__).parent.parent.parent

class ImageProcessor:
    """图片处理类，用于处理图片的EXIF信息和基本属性。
    
    Attributes:
        image_path (str): 图片文件路径
        image (Image): PIL Image对象
        exif_data (dict): 图片的EXIF数据
        width (int): 图片宽度
        height (int): 图片高度
        exposure_time (str): 曝光时间
        iso (int): ISO值
    """
    
    def __init__(self, image_path: str) -> None:
        """初始化ImageProcessor类。
        
        Args:
            image_path (str): 图片文件路径
            
        Raises:
            FileNotFoundError: 当图片文件不存在时
            ValueError: 当图片文件无法打开时
        """
        self.image_path = image_path
        self.image = Image.open(image_path)
        self.exif_data = self.image._getexif()
        self.width, self.height = self.image.size
        self.exposure_time = self.get_image_exposure_time()
        self.iso = self.get_image_iso()

    def get_image_exposure_time(self) -> Optional[str]:
        """获取图片的曝光时间。
        
        Returns:
            Optional[str]: 曝光时间，格式为"1/分母"，如果无法获取则返回None
        """
        if not self.exif_data:
            return None
            
        exposure_time = self.exif_data.get(33434)  # 曝光时间
        if exposure_time is None:
            return None
            
        try:
            # 处理元组类型 (分子, 分母)
            if isinstance(exposure_time, tuple) and len(exposure_time) == 2:
                if exposure_time[1] != 0 and exposure_time[0] != 0:
                    # 计算新的分母：原始分母除以原始分子
                    new_denominator = exposure_time[1] // exposure_time[0]
                    return f"1/{new_denominator}"
                    
            # 处理数值类型
            elif isinstance(exposure_time, (int, float)):
                if exposure_time != 0:
                    # 对于整数或浮点数，计算分母
                    denominator = int(1 / exposure_time)
                    return f"1/{denominator}"
                
            # 处理分数类型
            elif hasattr(exposure_time, 'numerator') and hasattr(exposure_time, 'denominator'):
                if exposure_time.numerator != 0:
                    # 计算新的分母
                    new_denominator = exposure_time.denominator // exposure_time.numerator
                    return f"1/{new_denominator}"
                
            # 处理字符串类型
            elif isinstance(exposure_time, str):
                try:
                    # 尝试将字符串转换为分数
                    fraction = Fraction(exposure_time)
                    if fraction.numerator != 0:
                        new_denominator = fraction.denominator // fraction.numerator
                        return f"1/{new_denominator}"
                except ValueError:
                    # 如果无法转换为分数，尝试直接使用
                    try:
                        value = float(exposure_time)
                        if value != 0:
                            denominator = int(1 / value)
                            return f"1/{denominator}"
                    except ValueError:
                        return None
                        
        except Exception:
            return None
            
        return None

    def get_image_iso(self) -> Optional[int]:
        """获取图片的ISO值。
        
        Returns:
            Optional[int]: ISO值，如果无法获取则返回None
        """
        try:
            return self.exif_data.get(34855) if self.exif_data else None
        except Exception:
            return None
            
    def get_image_info(self) -> Dict[str, Any]:
        """获取图片的基本信息。
        
        Returns:
            Dict[str, Any]: 包含图片基本信息的字典
        """
        return {
            'path': self.image_path,
            'size': (self.width, self.height),
            'exposure_time': self.exposure_time,
            'iso': self.iso,
            'format': self.image.format,
            'mode': self.image.mode
        }
        
    def resize(self, width: int, height: int) -> Image.Image:
        """调整图片大小。
        
        Args:
            width (int): 目标宽度
            height (int): 目标高度
            
        Returns:
            Image.Image: 调整大小后的图片对象
        """
        return self.image.resize((width, height), Image.Resampling.LANCZOS)
        
    def rotate(self, angle: float) -> Image.Image:
        """旋转图片。
        
        Args:
            angle (float): 旋转角度
            
        Returns:
            Image.Image: 旋转后的图片对象
        """
        return self.image.rotate(angle, expand=True)
            
    def close(self) -> None:
        """关闭图片文件。"""
        if hasattr(self, 'image'):
            self.image.close()
            
    def __enter__(self):
        """上下文管理器入口。"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""
        self.close()
        
    def __del__(self):
        """析构函数，确保资源被释放。"""
        self.close()