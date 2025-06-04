# -*- encoding: utf-8 -*-
'''
@File         :p3_converter.py
@Time         :2025/06/04 09:47:18
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :
'''


from PIL import ImageCms
from pathlib import Path


if True:
    BASEICONPATH = Path(__file__).parent.parent.parent


class ColorSpaceConverter:
    def __init__(self):
        # 初始化变量
        self.current_profile = "sRGB"
        self.rendering_intent = "Perceptual"
        
        # 设置配置文件路径
        self.base_path = BASEICONPATH
        self.icc_paths = {
            "DCI-P3": [
                self.base_path / "resource" / "icc" / "DCI-P3-v4.icc"
            ],
            "Display P3": [
                self.base_path / "resource" / "icc" / "DisplayP3-v4.icc"
            ],
            "Rec2020": [
                self.base_path / "resource" / "icc" / "Rec2020-v4.icc"
            ]
        }
        
        # 实际使用的ICC文件路径
        self.icc_files = {}
        
        # 检查LittleCMS支持
        self.check_lcms_support()
        
        # 检查并初始化ICC配置文件
        self.initialize_icc_profiles()

    def initialize_icc_profiles(self):
        """初始化并验证ICC配置文件"""
        for profile_name, paths in self.icc_paths.items():
            self.icc_files[profile_name] = None
            for path in paths:
                if path.exists():
                    self.icc_files[profile_name] = path
                    print(f"成功加载 {profile_name} ICC文件: {path}")
                    break
            
            if self.icc_files[profile_name] is None:
                print(f"警告: 未能找到 {profile_name} 的ICC文件")
                print(f"已尝试以下路径:")
                for path in paths:
                    print(f"- {path}")

    def check_lcms_support(self):
        """检查LittleCMS支持情况"""
        try:
            ImageCms.createProfile("sRGB")
            print("LittleCMS库已成功加载，支持色彩管理")
        except Exception as e:
            print(f"错误: LittleCMS初始化失败 - {str(e)}")
            print("请确保已正确安装Pillow和littlecms库")
            
    def convert_color_space(self, pil_image, target_profile, intent="Perceptual"):
        """
        转换图像色彩空间
        Args:
            pil_image (PIL_image): PIL打开的图像
            target_profile (str): 目标色域名称
            intent (str): 渲染意图
        Returns:
            QPixmap: 转换后的图像
        """
        intent_map = {
            "Perceptual": ImageCms.Intent.PERCEPTUAL, # 感知，最常用的渲染意图，保持图像的视觉平衡
            "Relative Colorimetric": ImageCms.Intent.RELATIVE_COLORIMETRIC, # 相对色度，保持图像的视觉平衡，但更注重颜色的准确性
            "Saturation": ImageCms.Intent.SATURATION, # 饱和度，增强图像的饱和度，使颜色更鲜艳
            "Absolute Colorimetric": ImageCms.Intent.ABSOLUTE_COLORIMETRIC # 绝对色度，保持图像的视觉平衡，但更注重颜色的准确性
        }
        
        try:
            # 获取源配置文件（假设为sRGB）
            src_profile = ImageCms.createProfile("sRGB")
            
            # 检查目标配置文件是否可用
            if target_profile not in self.icc_files or self.icc_files[target_profile] is None:
                raise FileNotFoundError(f"未找到{target_profile}的ICC配置文件")
            
            # 获取目标配置文件
            icc_path = self.icc_files[target_profile].as_posix()
            dst_profile = ImageCms.getOpenProfile(icc_path)
            
            # 创建转换
            transform = ImageCms.buildTransform(
                src_profile, dst_profile,
                "RGB", "RGB",
                intent_map[intent]
            )
            
            # 应用转换
            converted_image = ImageCms.applyTransform(pil_image, transform)
            
            # 转换为pixmap
            return converted_image
            
        except FileNotFoundError as e:
            print(f"ICC配置文件错误: {str(e)}")
            return pil_image  # 返回原图
        except Exception as e:
            print(f"色彩空间转换失败: {str(e)}")
            return pil_image  # 返回原图


        
        