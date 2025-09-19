#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File         :hiviewer.py
@Time         :2025/06/04
@Author       :diamond_cz@163.com
@Version      :release-v3.5.1
@Description  :hiviewer看图子界面
'''

"""导入python内置模块"""
import re
import os
import io
import gc
import sys
import time
import json
import threading
from pathlib import Path 
from multiprocessing import cpu_count
from concurrent.futures import ThreadPoolExecutor

"""导入python第三方模块"""
import cv2
import piexif
import numpy as np
import matplotlib.pyplot as plt
from lxml import etree as ETT
from PIL import Image, ImageOps
from PyQt5.QtGui import QIcon, QColor, QPixmap, QKeySequence, QPainter, QCursor, QTransform, QImage, QPen, QBrush
from PyQt5.QtCore import Qt, QTimer, QEvent, pyqtSignal, QThreadPool, QRunnable
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QHeaderView, QShortcut, QGraphicsView, QAction,
    QGraphicsScene, QGraphicsPixmapItem, QMessageBox, QProgressBar, QGraphicsRectItem, QMenu,
    QGraphicsItem, QDialog)

"""导入自定义模块"""
from src.components.ui_sub_image import Ui_MainWindow                   # 看图子界面，导入界面UI
from src.components.custom_qMbox_showinfo import show_message_box       # 导入消息框类
from src.components.custom_qdialog_problems import ProblemsDialog       # 导入问题对话框类
from src.common.manager_color_exif import load_exif_settings            # 导入json配置模块
from src.common.manager_color_exif import load_color_settings
from src.common.font import JetBrainsMonoLoader                         # 看图子界面，导入字体管理器                   
from src.utils.ai_tips import CustomLLM_Siliconflow                     # 看图子界面，AI提示看图复选框功能模块
from src.utils.hisnot import WScreenshot                                # 看图子界面，导入自定义截图的类
from src.utils.aebox_link import check_process_running, get_api_data    # 导入与AEBOX通信的模块函数
from src.utils.heic import extract_jpg_from_heic                        # 导入heic图片转换为jpg图片的模块
from src.utils.p3_converter import ColorSpaceConverter                  # 导入色彩空间转换配置类
from src.common.decorator import CC_TimeDec                             # 导入自定义装饰器
from src.common.progress_round import RoundProgress                     # 导入自定义进度条

"""设置本项目的入口路径,全局变量BasePath"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))    

"""
设置全局函数区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

def convert_to_dict(exif_string):
    """
    将EXIF字符串转换为字典格式。
    Args:
        exif_string (str): 输入的EXIF字符串，格式为 "key: value" 的多行文本。
        
    Returns:
        dict: 转换后的字典数据。
        
    Raises:
        ValueError: 当输入参数不是字符串类型时。
        Exception: 当正则表达式匹配失败时。
    """
    try:
        # 输入类型检查
        if not isinstance(exif_string, str):
            raise ValueError("输入参数必须是字符串类型")
            
        # 检查输入是否为空
        if not exif_string.strip():
            return {}
            
        # 使用正则表达式匹配键值对
        pattern = r'([^:]+): ([^\n]+)'
        matches = re.findall(pattern, exif_string)
        
        # 检查是否成功匹配到数据
        if not matches:
            raise ValueError("未能从输入字符串中提取到任何键值对")

        # 返回转换后的字典
        return {key.strip(): value.strip() for key, value in matches}
                
    except Exception as e:
        print(f"[convert_to_dict]-->error: 转换过程中发生错误: {str(e)}")
        return {}


def pil_to_pixmap(pil_image):
    """
    将PIL Image转换为QPixmap，并自动处理图像方向信息
    
    Args:
        pil_image (PIL.Image): PIL图像对象
        
    Returns:
        QPixmap: 转换后的QPixmap对象，如果转换失败则返回None
        
    Raises:
        ValueError: 当输入不是PIL.Image对象时
    """
    try:
        # 参数检查
        if not pil_image:
            raise ValueError(f"传入的参数为None")

        # 判断传入的数据类型
        if not isinstance(pil_image, Image.Image):
            raise ValueError(f"不支持传入的类型: {type(pil_image)},只支持传入PIL.Image类型")
            
        # 使用ImageOps.exif_transpose自动处理EXIF方向信息
        pil_image = ImageOps.exif_transpose(pil_image)

        # 确保图像是RGB格式
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # 将PIL图像转换为numpy数组
        image_array = np.array(pil_image)

        # 创建QImage
        qimage = QImage(
            image_array.data,
            pil_image.width,
            pil_image.height,
            image_array.strides[0],  # 每行的字节数
            QImage.Format_RGB888
        )
             
        # 获取pixmap
        pixmap = QPixmap.fromImage(qimage)

        return pixmap
    except Exception as e:
        print(f"[pil_to_pixmap]-->error: PIL图像转换为QPixmap失败: {str(e)}")
        return None


def rgb_str_to_qcolor(rgb_str):
    """将 'rgb(r,g,b)' 格式的字符串转换为 QColor"""
    # 提取RGB值
    rgb = rgb_str.strip('rgb()')  # 移除 'rgb()' 
    r, g, b = map(int, rgb.split(','))  # 分割并转换为整数
    return QColor(r, g, b)


# @CC_TimeDec(tips="sucess")
def calculate_image_stats(image_input, resize_factor=1):
    """
    该函数主要是实现了获取图片的亮度、RGB、LAB和对比度的功能.
    Args:
        image_input (str/Image.Image/np.ndarray): 支持传入文件路径、PIL图像、cv图像
    Returns:
        dict: 返回特定格式的字典数据.
        {
            'width': 宽度
            'height': 高度
            'avg_brightness': 亮度,
            'contrast': 对比度指标
            'avg_rgb': RGB,
            'avg_lab': LAB,
            'R_G': R/G计算结果
            'B_G': B/G计算结果
        }
    """
    try:
        # 类型判断分支处理，支持传入文件路径、PIL图像、cv图像
        if isinstance(image_input, str):  # 处理文件路径
            with open(image_input, 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        elif isinstance(image_input, Image.Image):  # 处理PIL图像对象
            img = np.array(image_input.convert('RGB'))[:, :, ::-1].copy()
        elif isinstance(image_input, np.ndarray):  # 处理opencv图像对象
            img = image_input
        else:
            raise FileNotFoundError(f"无法识别的图像格式:{type(image_input)}")

        # 缩小图片
        height, width = img.shape[:2]
        new_size = (int(width * resize_factor), int(height * resize_factor))
        img = cv2.resize(img, new_size, interpolation=cv2.INTER_LANCZOS4)

        # 将BGR转换为RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 将RGB转换为LAB
        img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        
        # 计算RGB和LAB平均值
        avg_rgb = np.mean(img_rgb, axis=(0, 1))
        avg_lab = np.mean(img_lab, axis=(0, 1))

        # 将LAB值调整到标准范围
        avg_lab = (
            avg_lab[0] * (100 / 255),   # L: [0, 255] -> [0, 100]
            avg_lab[1] - 128,           # A: [0, 255] -> [-127, 127]
            avg_lab[2] - 128            # B: [0, 255] -> [-127, 127]
        )

        # 计算R/G和B/G
        R_G = avg_rgb[0] / avg_rgb[1] if avg_rgb[1] != 0 else float('inf')  # 避免除以零
        B_G = avg_rgb[2] / avg_rgb[1] if avg_rgb[1] != 0 else float('inf')  # 避免除以零

        # 计算亮度（直接使用RGB值）
        avg_brightness = 0.299 * avg_rgb[0] + 0.587 * avg_rgb[1] + 0.114 * avg_rgb[2]
        
        # 计算全局对比度（使用LAB的L通道标准差）
        l_channel = img_lab[:, :, 0].astype(np.float32) * (100 / 255)  # 转换为标准L范围[0,100]
        contrast = np.std(l_channel)  # 标准差作为对比度指标

        # 格式化输出
        return {
            'width': new_size[0],   # 新增区域宽度
            'height': new_size[1],  # 新增区域高度
            'avg_brightness': round(float(avg_brightness), 1),
            'contrast': round(float(contrast), 1),  # 新增对比度指标
            'avg_rgb': tuple(round(float(x), 1) for x in avg_rgb),
            'avg_lab': tuple(round(float(x), 1) for x in avg_lab),
            'R_G': round(float(R_G), 5),  # 新增R/G计算结果
            'B_G': round(float(B_G), 5)   # 新增B/G计算结果
        }
        
    except Exception as e:
        print(f"[calculate_image_stats]-->error: 计算图片统计信息失败, 错误: {e}")
        return None

 

def load_xml_data(xml_path):
    """(高通平台)加载XML文件并提取Lux值和DRCgain值等EXIF信息"""
    try:
        # 加载xml文件 
        tree = ETT.parse(xml_path)
        root = tree.getroot()

        # 定义需要提取的标签, tag:name
        XPATHS = {
            'Lux': ETT.XPath('lux_index'),
            'DRCgain': ETT.XPath('DRCgain'),
            'Safe_gain': ETT.XPath('safe_gain'),
            'Short_gain': ETT.XPath('short_gain'),
            'Long_gain': ETT.XPath('long_gain'),
            'CCT': ETT.XPath('CCT'),
            'R_gain': ETT.XPath('r_gain'),
            'B_gain': ETT.XPath('b_gain'),
            'Awb_sa': ETT.XPath('awb_sa'),
            'Triangle_index': ETT.XPath('triangle_index'),
            'FaceSA': ETT.XPath('.//SA/FaceSA')
        }

        # ETT.XPath('lux_index')(root)[0].text
        # 提取值并拼接
        qualcom_exif_info, extracted_values, luma_frame_ev = '', [], False
        for name, tag  in XPATHS.items():
            value = tag(root)
            if name  != 'FaceSA':
                if value and value[0].text:
                    extracted_values.append(f"\n{name}: {value[0].text}")
            else: # 解析人脸SA的相关value
                if value:
                    # 获取FrameSA的luma值
                    luma_frame = ETT.XPath('.//SA/FrameSA/luma')(root)
                    luma_frame_ev = ETT.XPath('.//SA/EVFrameSA/luma')(root)
                    frame_luma = luma_frame[0].text if luma_frame and luma_frame[0].text else luma_frame_ev[0].text if luma_frame_ev and luma_frame_ev[0].text else 0.0001
                    
                    # 获取FaceSA的luma值
                    luma_face = ETT.XPath('.//SA/FaceSA/luma')(root)
                    face_luma = luma_face[0].text if luma_face and luma_face[0].text else 0.0001

                    # 计算背光值
                    backlight = float(face_luma)/float(frame_luma) if frame_luma and face_luma else 0.0
                    
                    # 获取FaceSA的target值
                    target = ETT.XPath('.//SA/FaceSA/target/start')(root)
                    if target and target[0].text:
                        extracted_values.append(f"\n{name}: {target[0].text}(target) & {backlight:.4f}(backlight)")
                else:
                    extracted_values.append(f"\n{name}: 未识别人脸")

        # 汇总字符串    
        qualcom_exif_info = ''.join(extracted_values)
        return qualcom_exif_info, bool(luma_frame_ev)

    except Exception as e:
        print(f"解析XML失败{xml_path}:\n报错信息: {e}")
        return '', False

def load_exif_data(exif_path):
    """(展锐平台)加载txt文件并提取Bv值和EVD值等EXIF信息
    返回: (汇总字符串, 是否存在EVFrameSA信息)
    """
    try:
        # 判断文件是否存在
        if not exif_path or not os.path.isfile(exif_path):
            return "", False

        # 读取txt文件
        text_norm = ""
        with open(exif_path, "r", encoding="utf-8", errors="ignore") as f:
            text_norm = f.read()

        # 关键字段查找
        patterns = {
            "Lux": "AE_TAG_REALBVX1000|AE_TAG_HSV4P0_STS_EVD|AE_TAG_HS_EVD|AE_TAG_FLT_DR",
            "CWV": "AE_TAG_CWV_FINAL_TARGET",
        }


        # 定义提取关键字函数
        def extract_value_pat(pat, text_norm):
            try:
                value = 0
                format = rf'{re.escape(pat)}\s*:\s*([-+]?\d+(?:\.\d+)?)'
                match = re.search(format, text_norm)
                if match:
                    value = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
                return value if value else 0
            except Exception as e:
                print(f"extract_value_pat解析exif失败{exif_path}:\n报错信息: {e}")
                return 0
  
        # 查找关键字数值并拼接, 先定义基础变量
        unisoc_exif_info, extracted_values, value = '', [], 0
        for key,pat in patterns.items():
            if key == "Lux":
                bv = extract_value_pat(pat.split("|")[0], text_norm)
                evd1 = extract_value_pat(pat.split("|")[1], text_norm)
                evd2 = extract_value_pat(pat.split("|")[2], text_norm)
                evd = evd1 if evd1 else evd2
                dr = extract_value_pat(pat.split("|")[3], text_norm)

                # 打印相关信息
                value = f"NULL" if not bv and not evd and not dr else f"bv[{bv}] evd[{evd}] dr[{dr}]"
                
                
                extracted_values.append(f"\n{key}: {value}")
                
            else: # 剩余关键字数值提取
                if (value := extract_value_pat(pat, text_norm)):
                    extracted_values.append(f"\n{key}: {value}")
        

        unisoc_exif_info = ''.join(extracted_values)
        return unisoc_exif_info, False

    except Exception as e:
        print(f"解析TXT失败{exif_path}:\n报错信息: {e}")
        return '', False


def load_txt_data(txt_path):
    """(展锐平台)加载txt文件并提取Bv值和EVD值等EXIF信息
    返回: (汇总字符串, 是否存在EVFrameSA信息)
    """
    try:
        # 判断文件是否存在
        if not txt_path or not os.path.isfile(txt_path):
            return "", False

        # 读取txt文件
        text_norm = ""
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text_norm = f.read()

        # 关键字段查找
        patterns = {
            "Lux": "AE-cur_bv|AE-hm-hm_evd|AE-face-calc_fd_param-calc_face_luma-face_backlight|AE-ae_stable",
            "Mulaes":"AE-mulae_target|AE-mulae-mulae_thd|AE-mulae-mulae_y|AE-mulae-cur_lum",
            "HM":("AE-short_hm_target|AE-safe_hm_target|"
                  "AE-hm-short_hm-hm_final_target_min|AE-hm-short_hm-hm_final_target_max|"
                  "AE-hm-safe_hm-hm_final_target_min|AE-hm-safe_hm-hm_final_target_max|"
                  "AE-hm-short_hm-hm_bt_target|AE-hm-short_hm-hm_aftaoe_target|AE-hm-short_hm-hm_aftcoe_target|AE-hm-short_hm-hm_dt_target|"
                  "AE-hm-short_hm-hm_dt_target_min|AE-hm-short_hm-hm_dt_target_max|"
                  "AE-hm-safe_hm-hm_bt_target|AE-hm-safe_hm-hm_aftaoe_target|AE-hm-safe_hm-hm_aftcoe_target|AE-hm-safe_hm-hm_dt_target|"
                  "AE-hm-safe_hm-hm_dt_target_min|AE-hm-safe_hm-hm_dt_target_max"
                 ),
            "Face":("AE-face-face_num|AE-face-calc_fd_param-face_target-short_face_thd|AE-face-calc_fd_param-face_target-safe_face_thd|"
                    "AE-face-calc_fd_param-face_target-short_final_face_luma|AE-face-calc_fd_param-face_target-safe_final_face_luma|"
                    "AE-face-cur_lum|AE-short_face_target|AE-safe_face_target|AE-face-calc_fd_param-face_target-min_facelum_protection_target|"
                    "AE-face-calc_fd_param-face_target-short_down_limit|AE-face-calc_fd_param-face_target-safe_down_limit|"
                    "AE-face-calc_fd_param-face_target-short_up_limit|AE-face-calc_fd_param-face_target-safe_up_limit|"
                    "AE-face-calc_fd_param-face_target-short_face_target_before_mflumtype1|AE-face-calc_fd_param-face_target-safe_face_target_before_mflumtype2"
                 ),
            "LCG": "AE-safe_final_target_lum|AE-short_final_target_lum|AE-ae_lcg|AE-ae_lcg_down_limit|AE-ae_lcg_up_limit",
        }


        # 定义提取关键字函数
        def extract_value_pat(pat, text_norm):
            try:
                value = 0
                format = rf'{re.escape(pat)}\s*:\s*([-+]?\d+(?:\.\d+)?)'
                match = re.search(format, text_norm)
                if match:
                    value = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
                return value if value else 0
            except Exception as e:
                print(f"extract_value_pat解析TXT失败{txt_path}:\n报错信息: {e}")
                return 0
  
        # 查找关键字数值并拼接, 先定义基础变量
        unisoc_exif_info, extracted_values, value = '', [], 0
        for key,pat in patterns.items():
            if key == "Lux":
                bv = extract_value_pat(pat.split("|")[0], text_norm)
                evd = extract_value_pat(pat.split("|")[1], text_norm)
                bl = extract_value_pat(pat.split("|")[2], text_norm)
                stb = extract_value_pat(pat.split("|")[3], text_norm)

                value_ = f"bv[{int(bv)}] evd[{int(evd)}] bl[{bl}] stb[{stb}]"
                extracted_values.append(f"\n{key}: {value_}")

            elif key == "Mulaes":
                target = extract_value_pat(pat.split("|")[0], text_norm)
                thd = extract_value_pat(pat.split("|")[1], text_norm)
                _y = extract_value_pat(pat.split("|")[2], text_norm)
                cur_lum = extract_value_pat(pat.split("|")[3], text_norm)

                value_ = f"tar[{int(target)}] calc[{int(thd)}/{int(_y)}*{int(cur_lum)}]"
                extracted_values.append(f"\n{key}: {value_}")
     

            elif key == "HM":
                short_target = extract_value_pat(pat.split("|")[0], text_norm)
                safe_target = extract_value_pat(pat.split("|")[1], text_norm)
                short_min = extract_value_pat(pat.split("|")[2], text_norm)
                short_max = extract_value_pat(pat.split("|")[3], text_norm)
                safe_min = extract_value_pat(pat.split("|")[4], text_norm)
                safe_max = extract_value_pat(pat.split("|")[5], text_norm)
                short_bt = extract_value_pat(pat.split("|")[6], text_norm)
                short_aoe = extract_value_pat(pat.split("|")[7], text_norm)
                short_coe = extract_value_pat(pat.split("|")[8], text_norm)
                short_dt = extract_value_pat(pat.split("|")[9], text_norm)
                short_dt_min = extract_value_pat(pat.split("|")[10], text_norm)
                short_dt_max = extract_value_pat(pat.split("|")[11], text_norm)
                safe_bt = extract_value_pat(pat.split("|")[12], text_norm)
                safe_aoe = extract_value_pat(pat.split("|")[13], text_norm)
                safe_coe = extract_value_pat(pat.split("|")[14], text_norm)
                safe_dt = extract_value_pat(pat.split("|")[15], text_norm)
                safe_dt_min = extract_value_pat(pat.split("|")[16], text_norm)
                safe_dt_max = extract_value_pat(pat.split("|")[17], text_norm)

                value_ = (f"tar[{int(short_min)}<{int(short_target)}>{int(short_max)},{int(safe_min)}<{int(safe_target)}>{int(safe_max)}] " 
                          f"calc[{int(short_bt)}->{int(short_aoe)}->{int(short_coe)}|{int(short_dt)}, {int(safe_bt)}->{int(safe_aoe)}->{int(safe_coe)}|{int(safe_dt)}] "
                          f"dt[{int(short_dt_min)}<{int(short_dt)}>{int(short_dt_max)},{int(safe_dt_min)}<{int(safe_dt)}>{int(safe_dt_max)}]" 
                        )

                extracted_values.append(f"\n{key}: {value_}")
            
            elif key == "Face":
                num = extract_value_pat(pat.split("|")[0], text_norm)
                short_thd = extract_value_pat(pat.split("|")[1], text_norm)
                safe_thd = extract_value_pat(pat.split("|")[2], text_norm)
                short_luma = extract_value_pat(pat.split("|")[3], text_norm)
                safe_luma = extract_value_pat(pat.split("|")[4], text_norm)
                cur_luma = extract_value_pat(pat.split("|")[5], text_norm)
                short_target = extract_value_pat(pat.split("|")[6], text_norm)
                safe_target = extract_value_pat(pat.split("|")[7], text_norm)
                mfl_target = extract_value_pat(pat.split("|")[8], text_norm)
                short_down = extract_value_pat(pat.split("|")[9], text_norm)
                safe_down = extract_value_pat(pat.split("|")[10], text_norm)
                short_up = extract_value_pat(pat.split("|")[11], text_norm)
                safe_up = extract_value_pat(pat.split("|")[12], text_norm)
                short_before_limit = extract_value_pat(pat.split("|")[13], text_norm)
                safe_before_limit = extract_value_pat(pat.split("|")[14], text_norm)

                value_ = (f"num[{num}] tar[{int(short_down)}<{int(short_target)}>{int(short_up)},{int(safe_down)}<{int(safe_target)}>{int(safe_up)}] " 
                          f"mft[{int(mfl_target)}] "
                          f"calc[{int(cur_luma)}*({int(short_thd)}/{int(short_luma)})[{int(short_before_limit)},{int(safe_before_limit)}]({int(safe_thd)}/{int(safe_luma)})*{int(cur_luma)}]" 
                        )

                extracted_values.append(f"\n{key}: {value_}")

            elif key == "LCG":
                safe = extract_value_pat(pat.split("|")[0], text_norm)
                short = extract_value_pat(pat.split("|")[1], text_norm)
                lcg = extract_value_pat(pat.split("|")[2], text_norm)
                down = extract_value_pat(pat.split("|")[3], text_norm)
                up = extract_value_pat(pat.split("|")[4], text_norm)

                value_ = f"lcg[{down}<{lcg}>{up}] tar[{int(short)},{int(safe)}]"
                extracted_values.append(f"\n{key}: {value_}")

            else: # 剩余关键字数值提取
                if (value := extract_value_pat(pat, text_norm)):
                    extracted_values.append(f"\n{key}: {value}")

        unisoc_exif_info = ''.join(extracted_values)
        return unisoc_exif_info, False

    except Exception as e:
        print(f"解析TXT失败{txt_path}:\n报错信息: {e}")
        return '', False


"""
设置全局函数区域结束线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""


"""
设置独立封装类区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""


""""继承 QGraphicsRectItem 并重写 itemChange 方法来实现对矩形框变化的监听"""
class CustomGraphicsRectItem(QGraphicsRectItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.change_callback = None

    def set_change_callback(self, callback):
        """设置变化回调函数"""
        self.change_callback = callback

    def itemChange(self, change, value):
        """重写itemChange方法，监听矩形框变化"""
        if self.change_callback and change in [QGraphicsItem.ItemPositionHasChanged, 
                                             QGraphicsItem.ItemTransformHasChanged]:
            # 使用QTimer.singleShot延迟回调，确保矩形框位置更新完成
            QTimer.singleShot(0, self.change_callback)
        return super().itemChange(change, value)
    


""""后台线程计算矩形框亮度等统计信息, 使用线程池管理"""
class StatsTask(QRunnable):
    def __init__(self, roi, callback):
        super().__init__()
        self.roi = roi
        self.callback = callback

    def run(self):
        """线程执行函数，计算统计信息"""
        try:
            stats = calculate_image_stats(self.roi, resize_factor=1)
            self.callback(stats)
        except Exception as e:
            print(f"计算统计信息时出错: {e}")
            self.callback({})


"""图片视图类"""
class MyGraphicsView(QGraphicsView):
    def __init__(self, scene, exif_text=None, stats_text=None, *args, **kwargs):
        super(MyGraphicsView, self).__init__(scene, *args, **kwargs)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)  # 重要！确保及时更新
        
        # 设置顶层窗口，方便调用类SubMainWindow中的函数与变量
        self.parent_SubMainWindow = self.window()

        # 初始化字体管理器
        self.font_manager_view = JetBrainsMonoLoader.font(11) 

        # 初始化基本信息(exif信息, stats信息, 控制exif显示, stats显示, 直方图, 控制直方图显示)
        self.exif_text = exif_text
        self.stats_text = stats_text
        self.show_exif = True if exif_text else False
        self.stats_visible = True if stats_text else False
        self.histogram = None
        self.show_histogram = False

        # 添加 QLabel 显示 EXIF 信息
        self.exif_label = QLabel(self)
        self.exif_label.setText(self.exif_text if self.exif_text else "解析不出exif信息!")
        self.exif_label.setStyleSheet("color: white; background-color: transparent;")
        self.exif_label.setFont(self.font_manager_view)
        self.exif_label.setVisible(self.show_exif)
        self.exif_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 添加新的QLabel用于显示直方图信息
        self.histogram_label = QLabel(self)
        self.histogram_label.setStyleSheet("border: none;")
        self.histogram_label.setFixedSize(150, 100)
        self.histogram_label.setVisible(self.show_histogram)
        self.histogram_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 添加新的QLabel用于显示亮度、RGB、LAB的统计信息
        self.stats_label = QLabel(self)
        self.stats_label.setText(self.stats_text if self.stats_text else "不存在亮度统计信息!")
        self.stats_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 0.7); padding: 2px;")
        self.stats_label.setFont(self.font_manager_view)
        self.stats_label.setVisible(self.stats_visible)
        self.stats_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 添加ROI矩形框相关属性
        self.selection_rect = None
        self.original_image = None  # 存储原始OpenCV图像数据
        self.selection_visible = False
        self.last_pos = None  # 记录鼠标右键拖动的起始位置
        self.move_step = 1.0  # 动态设置矩形框跟随鼠标移动步长

        # 初始化线程池，用于计算ROI矩形框的统计信息
        self.thread_pool = QThreadPool.globalInstance()

        # 初始更新标签位置
        self.update_labels_position()
        

    def set_cv_image(self, cv_img):
        """设置原始OpenCV图像用于统计计算"""
        self.original_image = cv_img

    def toggle_selection_rect(self, visible):
        """切换选择框的显示状态"""
        self.selection_visible = visible
        if visible: 
            if not self.selection_rect:
                
                self.selection_rect = CustomGraphicsRectItem()
                self.selection_rect.setPen(QPen(QColor(0, 255, 0, 255), 15))
                self.selection_rect.setFlag(QGraphicsItem.ItemIsMovable)
                self.selection_rect.setFlag(QGraphicsItem.ItemIsSelectable)
                self.selection_rect.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

                """ 设置变化回调函数_统计矩形框内的亮度等信息"""
                self.selection_rect.set_change_callback(self.update_roi_stats)
                
                # 将矩形项添加到场景中
                self.scene().addItem(self.selection_rect)
                # 将矩形项添加到视图的viewport中
                
                
                # 设置初始大小和位置
                scene_rect = self.scene().sceneRect()
                size = min(scene_rect.width(), scene_rect.height()) / 10
                # size = 100
                self.selection_rect.setRect(
                    scene_rect.center().x() - size/2,
                    scene_rect.center().y() - size/2,
                    size, size
                )
                
            # 显示ROI矩形框
            self.selection_rect.show()

            # 初始更新统计信息
            self.update_roi_stats()
        else:
            if self.selection_rect:
                self.selection_rect.hide()
                # 清除ROI统计信息
                if hasattr(self, 'stats_label'):
                    self.set_stats_data(self.stats_text if self.stats_text else "")


    def update_roi_stats(self):
        """更新ROI区域的统计信息"""
        if not self.selection_rect or self.original_image is None:
            print("update_roi_stats error!")
            return
        # 使用 QTimer 延迟调用，避免频繁计算
        QTimer.singleShot(100, self._calculate_roi_stats)


    def _calculate_roi_stats(self):
        """提取 ROI 区域并启动线程计算统计信息"""
        try:
            if not self.selection_rect or self.original_image is None:
                return

            # 获取选择框在场景中的位置和大小
            scene_rect = self.selection_rect.sceneBoundingRect()
            
            # 获取原始图像尺寸
            img_h, img_w = self.original_image.shape[:2]
            
            # 转换场景坐标到图像坐标
            x1 = max(0, min(img_w-1, int(scene_rect.left())))
            y1 = max(0, min(img_h-1, int(scene_rect.top())))
            x2 = max(0, min(img_w, int(scene_rect.right())))
            y2 = max(0, min(img_h, int(scene_rect.bottom())))
            
            # 确保有效的 ROI 区域
            if x2 > x1 and y2 > y1:
                # 提取 ROI 区域
                roi = self.original_image[y1:y2, x1:x2]
                
                # 创建并启动新的任务
                task = StatsTask(roi, self._update_stats_display)

                self.thread_pool.start(task)
        except Exception as e:
            print(f"提取 ROI 区域时出错: {e}")

    def _update_stats_display(self, stats):
        """更新统计信息显示"""
        if not stats:
            return

        # 格式化 ROI 统计信息
        roi_stats = (
            f"--- ROI统计信息 ---\n"
            # f"ROI: {stats['width']}x{stats['height']}\n"
            f"亮度: {stats['avg_brightness']:.1f}\n"
            f"对比度: {stats['contrast']:.1f}\n"
            f"LAB均值: {stats['avg_lab']}\n"
            f"RGB均值: {stats['avg_rgb']}\n"
            f"(R/G:{stats['R_G']} B/G: {stats['B_G']})\n"
            f"(roi:{stats['width']}x{stats['height']})"
            # f"区域大小: {stats['width']}x{stats['height']}"
        )
        self.set_stats_data(roi_stats)


    def adjust_roi_size(self, delta, anchor_point=None):
        """调整ROI选择框大小（基于变换矩阵）"""
        if not self.selection_rect:
            return

        try:
            # 设置调整步长
            scale_factor = 1.15 if delta > 0 else 0.955
            
            # 获取当前矩形的位置和尺寸
            current_rect = self.selection_rect.rect()
            scene_rect = self.scene().sceneRect()
            
            # 计算新的尺寸
            new_width = max(50, min(current_rect.width() * scale_factor, scene_rect.width()))
            new_height = max(50, min(current_rect.height() * scale_factor, scene_rect.height()))
            
            # 计算缩放比例
            width_scale = new_width / current_rect.width()
            height_scale = new_height / current_rect.height()
            
            # 创建变换矩阵
            transform = QTransform()
            
            # 如果有锚点，则以锚点为中心进行缩放
            if anchor_point:
                # 将锚点转换为局部坐标系
                local_anchor = self.selection_rect.mapFromScene(anchor_point)
                # 以锚点为中心进行缩放
                transform.translate(local_anchor.x(), local_anchor.y())
                transform.scale(width_scale, height_scale)
                transform.translate(-local_anchor.x(), -local_anchor.y())
            else:
                # 以中心点进行缩放
                center = current_rect.center()
                transform.translate(center.x(), center.y())
                transform.scale(width_scale, height_scale)
                transform.translate(-center.x(), -center.y())
            
            # 应用变换
            self.selection_rect.setTransform(transform, True)
            
            # 确保ROI不会超出场景边界
            new_rect = self.selection_rect.sceneBoundingRect()
            if new_rect.left() < scene_rect.left():
                self.selection_rect.setX(scene_rect.left())
            if new_rect.top() < scene_rect.top():
                self.selection_rect.setY(scene_rect.top())
            if new_rect.right() > scene_rect.right():
                self.selection_rect.setX(scene_rect.right() - new_rect.width())
            if new_rect.bottom() > scene_rect.bottom():
                self.selection_rect.setY(scene_rect.bottom() - new_rect.height())
            
            # 同步其他视图的ROI大小和位置
            main_window = self.window()
            if isinstance(main_window, SubMainWindow):
                for view in main_window.graphics_views:
                    if view and view != self and view.selection_rect:
                        view.selection_rect.setTransform(transform, True)
                        view.update_roi_stats()
            
            # 更新当前视图的ROI统计信息
            self.update_roi_stats()
            
        except Exception as e:
            print(f"adjust_roi_size error: {str(e)}")


    def update_labels_position(self):
        """更新标签位置"""
        padding = 5  # 边距
        
        # 更新统计信息标签位置（左下角）
        if self.stats_label:
            self.stats_label.move(padding, self.height() - self.stats_label.height() - padding)
            self.stats_label.adjustSize()  # 根据内容调整大小
        

        if self.show_histogram and self.show_exif:
            # 两个标签都显示时，直方图在上，EXIF在下
            self.histogram_label.move(padding, padding)
            self.exif_label.move(padding, padding + self.histogram_label.height() + padding)
        else:
            # 只显示其中一个时，都显示在左上角
            if self.show_histogram:
                self.histogram_label.move(padding, padding)
            if self.show_exif:
                self.exif_label.move(padding, padding)


    def set_histogram_data(self, histogram):
        """设置直方图数据"""
        if histogram is None:
            self.histogram_label.setText("无直方图数据")
            return
        # 使用 matplotlib 生成直方图图像
        try:
            plt.figure(figsize=(3, 2), dpi=100, facecolor='none', edgecolor='none')  # 设置背景透明
            ax = plt.gca()
            # 计算相对频率
            total_pixels = sum(histogram)
            relative_frequency = [count / total_pixels for count in histogram]
            ax.plot(range(len(relative_frequency)), relative_frequency, color='skyblue', linewidth=1)
            ax.fill_between(range(len(relative_frequency)), relative_frequency, color='skyblue', alpha=0.7)            
            ax.set_xlim(0, 255)
            ax.set_ylim(0, max(relative_frequency)*1.1)
            ax.yaxis.set_visible(False)  # 隐藏 Y 轴
            ax.xaxis.set_tick_params(labelsize=8)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='PNG', transparent=True, bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            plt.close()

            histogram_pixmap = QPixmap()
            histogram_pixmap.loadFromData(buf.getvalue(), 'PNG')
            buf.close()

            # 缩放直方图图像以适应 QLabel
            self.histogram_label.setPixmap(histogram_pixmap.scaled(
                self.histogram_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            print(f"生成直方图图像失败: {e}")
            self.histogram_label.setText("无法生成直方图")


    def set_histogram_visibility(self, visible: bool):
        """设置直方图可见性"""
        self.show_histogram = visible
        self.histogram_label.setVisible(visible)

        self.update_labels_position()


    def set_exif_visibility(self, visible: bool, font_color: str):
        """设置EXIF信息可见性"""
        self.show_exif = visible
        self.exif_label.setVisible(visible)
        self.exif_label.setStyleSheet(f"color: {font_color}; background-color: transparent; font-weight: 400;")

        self.update_labels_position()


    def set_stats_visibility(self, visible: bool):
        """设置亮度统计信息的可见性"""
        self.stats_visible = visible
        self.stats_label.adjustSize()  # 根据内容调整大小
        self.stats_label.setVisible(visible)

        self.update_labels_position()


    def set_stats_data(self, text: str = ""):
        """设置亮度统计信息的数据"""
        self.stats_label.setText(text)
        self.stats_label.adjustSize()  # 根据内容调整大小
    
        self.update_labels_position()

    
    # 窗口尺寸改变事件函数
    def resizeEvent(self, event):
        """重写调整大小事件"""
        super(MyGraphicsView, self).resizeEvent(event)
        self.update_labels_position()
    

    # 鼠标滚轮事件函数
    def wheelEvent(self, event):
        """重写鼠标滚轮事件"""
        try:
            # 控制ROI信息显示的变量 self.parent_SubMainWindow.stats_visible 
            # 控制矩形框显示的变量 self.parent_SubMainWindow.roi_selection_active
            # if event.modifiers() & Qt.AltModifier:
            if self.parent_SubMainWindow.roi_selection_active:
                # Alt + 滚轮调整ROI大小 
                if self.selection_rect:
                    # 获取鼠标在场景中的位置 视图位置 event.pos()
                    mouse_scene_pos = self.mapToScene(event.pos())
                            
                    # 调整ROI大小，并保持鼠标位置相对ROI的位置不变
                    self.adjust_roi_size(event.angleDelta().y(), mouse_scene_pos)

                    # 添加调试信息
                    # print(f"MyGraphicsView - 当前滚轮数值: {event.angleDelta()}")

                    # 事件已处理，阻止进一步传递
                    event.accept()
                    return  
                
            # 如果没有Alt键，调用父类的wheelEvent（确保父类是SubMainWindow）
            elif isinstance(self.parent_SubMainWindow, SubMainWindow):
                self.parent_SubMainWindow.wheelEvent(event)
                
            else:
                # 如果父类不是SubMainWindow，直接调用QGraphicsView的默认实现
                super().wheelEvent(event)

        except Exception as e:
            print(f"MyGraphicsView - wheelEvent error: {str(e)}")


    # 鼠标按压事件函数
    def mousePressEvent(self, event):
        try:

            # 动态计算self.move_step的值,确保移动ROI矩形框的时候不卡顿
            base_scales = self.parent_SubMainWindow.base_scales
            if base_scales:
               self.move_step = 1.0 / max(base_scales)
               # 确保结果在 [1, 4] 之间
               self.move_step = max(1, min(4, self.move_step))

            if event.button() == Qt.LeftButton:
                # 左键按下，记录起始位置
                self.last_pos = event.pos()
                # event.accept()

                # 如果在矩形框控制模式下，直接将矩形框移动到鼠标位置
                if self.parent_SubMainWindow.roi_selection_active and self.selection_rect:
                    # 获取鼠标在场景中的位置
                    mouse_scene_pos = self.mapToScene(event.pos())
                    
                    # 计算矩形框的新位置
                    rect = self.selection_rect.rect()
                    new_pos = mouse_scene_pos - rect.center()
                    
                    # 移动当前视图的矩形框
                    self.selection_rect.setPos(new_pos)
                    
                    # 同步其他视图的矩形框位置
                    main_window = self.window()
                    if isinstance(main_window, SubMainWindow):
                        for view in main_window.graphics_views:
                            if view and view != self and view.selection_rect:
                                view.selection_rect.setPos(new_pos)
                                view.update_roi_stats()
                    
                    event.accept()
                    return


            elif event.button() == Qt.RightButton:
                # 右键按下，记录起始位置
                self.last_pos = event.pos()
                
                print(f"当前鼠标所在视图：视图尺寸：{self.width()}x{self.height()}--场景尺寸：{self.scene().sceneRect().width()}x{self.scene().sceneRect().height()}")

                event.accept()
            else:
                super().mousePressEvent(event)
        except Exception as e:
            print(f"鼠标事件处理错误: {e}")
            event.ignore()


    # 鼠标移动事件函数
    def mouseMoveEvent(self, event):
        try:
            
            if self.parent_SubMainWindow.roi_selection_active: # 矩形框控制模式
                # print(self.move_step)
                if event.buttons() & Qt.LeftButton and self.last_pos is not None:
                    # Alt+左键移动，同步所有视图的ROI矩形框
                    delta = (event.pos() - self.last_pos)*self.move_step
                    self.last_pos = event.pos()
                    main_window = self.window()
                    if isinstance(main_window, SubMainWindow):
                        for view in main_window.graphics_views:
                            if view and view.selection_rect:
                                view.selection_rect.moveBy(delta.x(), delta.y())
                    event.accept()
                elif event.buttons() & Qt.RightButton and self.last_pos is not None:
                    # Alt+右键移动，只移动当前视图的ROI矩形框
                    delta = (event.pos() - self.last_pos)*self.move_step
                    self.last_pos = event.pos()
                    if self.selection_rect:
                        self.selection_rect.moveBy(delta.x(), delta.y())
                    event.accept()
                else:
                    super().mouseMoveEvent(event)
            else:  # 正常模式
                if event.buttons() & Qt.LeftButton and self.last_pos is not None:
                    delta = event.pos() - self.last_pos
                    self.last_pos = event.pos()
                    main_window = self.window()
                    if isinstance(main_window, SubMainWindow):
                        for view in main_window.graphics_views:
                            view.horizontalScrollBar().setValue(
                                view.horizontalScrollBar().value() - delta.x())
                            view.verticalScrollBar().setValue(
                                view.verticalScrollBar().value() - delta.y())
                    event.accept()
                elif event.buttons() & Qt.RightButton and self.last_pos is not None:
                    delta = event.pos() - self.last_pos
                    self.last_pos = event.pos()
                    self.horizontalScrollBar().setValue(
                        self.horizontalScrollBar().value() - delta.x())
                    self.verticalScrollBar().setValue(
                        self.verticalScrollBar().value() - delta.y())
                    event.accept()
                else:
                    super().mouseMoveEvent(event)
        except Exception as e:
            print(f"在 mouseMoveEvent 中发生错误: {e}")


    # 鼠标释放事件函数
    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            # 左键或右键释放，重置位置
            self.last_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


"""
设置独立封装类区域结束线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""



"""
设置看图界面类区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""


class SubMainWindow(QMainWindow, Ui_MainWindow):
    """看图主界面类"""
    # 在类级别定义信号，通知主窗口子窗口已关闭，AI响应信号，进度条更新信号 
    closed = pyqtSignal()
    ai_response_signal = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, images_path_list, index_list=None, parent=None):
        super(SubMainWindow, self).__init__(parent)

        # 初始化UI
        self.setupUi(self) 
        
        # 初始化传入的images_path_list(图像路径列表)、index_list(当前索引)以及parent(主窗口的self)
        self.parent_window = parent
        self.images_path_list = images_path_list
        self.index_list = index_list

        # 初始化变量
        self.init_variables()

        # 加载之前的配置
        self.load_settings()

        # 设置窗口标题组件和样式表
        self.set_stylesheet()

        # 初始化图片视图，集成了看图子界面的主要功能
        self.set_images(self.images_path_list, self.index_list)

        # 设置快捷键和槽函数
        self.set_shortcut()

        # 显示窗口
        # self.showMaximized()
        # self.show()
        self.toggle_screen_display()
        
        # 更新颜色样式表，放到最后，确保生效
        self.update_ui_styles()


    def init_variables(self):
        """初始化相关类以及变量"""

        # 初始化p3_converter.py中的ColorSpaceConverter实例
        self.p3_converter = ColorSpaceConverter()

        # 初始化SubMainWindow类中的一些列表属性
        self.exif_texts = []
        self.histograms = []
        self.original_rotation = []
        self.graphics_views = []
        self.original_pixmaps = []
        self.rgb_pixmaps = []
        self.gray_pixmaps = []
        self.p3_pixmaps = []
        self.cv_imgs = []
        self.pil_imgs = []
        self.base_scales = []
        self._scales_min = []

        # 设置表格的宽高初始大小
        self.table_width_heigth_default = [2534,1376]

        # 初始化roi亮度等信息统计框标志位；看图界面更新状态标志位; 看图界面标题显示开关
        self.roi_selection_active = False 
        self.is_updating = False        
        self.is_title_on = False

        # 初始化看图界面尺寸显示变量  
        self.is_fullscreen = False      
        self.is_norscreen = False
        self.is_maxscreen = False

        # 初始化颜色空间相关变量，默认设置sRGB优先
        self.auto_color_space = False  
        self.srgb_color_space = False  
        self.p3_color_space = False   
        self.gray_color_space = False

        # 设置rgb颜色值字典；exif信息可见性字典; exif信息可见性字典,解析后的Str信息; 均在函数load_settings中配置
        self.color_rgb_settings = {}
        self.dict_exif_info_visibility = {} 
        self.dict_label_info_visibility = {}

        # 字体设置
        self.font_manager_j12 = JetBrainsMonoLoader.font(12)
        self.font_manager_j11 = JetBrainsMonoLoader.font(11)
        self.font_manager_j10 = JetBrainsMonoLoader.font(11)




    def set_shortcut(self):
        """设置快捷键和槽函数"""

        """1. 设置快捷键"""
        # 创建快捷键，按住Esc键退出整个界面
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.Escape_close)

        # 创建快捷键，F11 全屏
        fullscreen_shortcut = QShortcut(QKeySequence('F11'), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        
        # 添加Ctrl+A和Ctrl+D快捷键
        self.shortcut_rotate_left = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut_rotate_left.activated.connect(self.rotate_left)
        self.shortcut_rotate_right = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut_rotate_right.activated.connect(self.rotate_right)

        # 添加空格键和B键的快捷键
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_space.activated.connect(self.on_space_pressed)
        self.shortcut_b = QShortcut(QKeySequence('b'), self)
        self.shortcut_b.activated.connect(self.on_b_pressed)

        # 添加P键的快捷键
        self.shortcut_p = QShortcut(QKeySequence('p'), self)
        self.shortcut_p.activated.connect(self.on_p_pressed)

        # 添加I键的快捷键,打开设置界面(第一次打开，第二次关闭)
        self.shortcut_p = QShortcut(QKeySequence('i'), self)
        self.shortcut_p.activated.connect(self.open_settings_window)

        # 添加V键的快捷键,细粒度缩小图片
        self.shortcut_v = QShortcut(QKeySequence('v'), self)
        self.shortcut_v.activated.connect(self.on_v_pressed)
        # 添加N键的快捷键，细粒度放大图片
        self.shortcut_v = QShortcut(QKeySequence('n'), self)
        self.shortcut_v.activated.connect(self.on_n_pressed)

        # 添加T键的快捷键,实现截图功能
        self.shortcut_t = QShortcut(QKeySequence('t'), self)
        self.shortcut_t.activated.connect(self.on_t_pressed)
        # 添加Ctrl+T键的快捷键,实现评测问题点描述
        self.shortcut_rotate_left = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_rotate_left.activated.connect(self.on_ctrl_t_pressed)

        """2. 连接复选框信号到槽函数"""
        # 连接复选框信号到槽函数
        self.checkBox_1.stateChanged.connect(self.toggle_histogram_info)  # 新增直方图显示
        self.checkBox_2.stateChanged.connect(self.toggle_exif_info)       # 新增EXIF信息显示
        self.checkBox_3.stateChanged.connect(self.roi_stats_checkbox)     # 新增ROI信息
        self.checkBox_4.stateChanged.connect(self.ai_tips_info)           # 新增AI提示看图
        
        # 连接下拉列表信号到槽函数
        self.comboBox_1.activated.connect(self.show_menu_combox1)          # 连接 QComboBox 的点击事件到显示菜单，self.on_comboBox_1_changed
        self.comboBox_2.activated.connect(self.on_comboBox_2_changed)      # 连接 QComboBox 的点击事件到显示菜单，self.on_comboBox_2_changed

        # 连接底部状态栏按钮信号到槽函数
        self.statusbar_left_button.clicked.connect(self.open_settings_window)
        self.statusbar_button1.clicked.connect(self.on_b_pressed)
        self.statusbar_button2.clicked.connect(self.on_space_pressed)

        # 连接AI响应信号到槽函数
        self.ai_response_signal.connect(self.update_ai_response)

        # 连接进度条更新信号到槽函数
        if hasattr(self, 'progress_updated'):
            self.progress_updated.connect(self.update_progress)
        
            
    def set_stylesheet(self):
        """设置窗口标题组件和样式表"""
        """窗口组件概览
        第一排, self.label_0, self.comboBox_1, self.comboBox_2, self.checkBox_1, self.checkBox_2, self.checkBox_3
        第二排, self.tableWidget_medium
        第三排, self.label_bottom
        """
        # 设置主界面图标以及标题
        icon_path = Path(BasePath, "resource", "icons", "viewer.ico").as_posix()
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("图片对比界面")

        """获取鼠标所在屏幕，并根据当前屏幕计算界面大小与居中位置，调整大小并移动到该位置
        x, y, w, h = self.__get_screen_geometry()
        self.resize(int(w * 0.8), int(h * 0.65))
        self.move(x, y)
        """

        # 设置第一排标签
        self.label_0.setText("提示:鼠标左键拖动所有图像,滚轮控制放大/缩小;按住Ctrl+滚轮或者鼠标右键操作单独图像")
        self.label_0.setFont(self.font_manager_j11)

        # 设置下拉框选项,会自动进入槽函数self.show_menu_combox1-->on_comboBox_1_changed
        self.comboBox_1.clear()  # 清除已有项
        self.comboBox_1.addItems(["✅颜色设置", "⭕一键重置", "🔽背景颜色>>", "🔽表格填充颜色>>", "🔽字体颜色>>", "🔽exif字体颜色>>"])  # 添加主选项
        self.comboBox_1.setEditable(False)  # 设置 QComboBox 不可编辑
        self.comboBox_1.setCurrentIndex(0)  # 设置默认显示索引为0
        self.comboBox_1.setFont(self.font_manager_j12)

        # 设置下拉框self.comboBox_2选项（优化版）
        color_space_list = [self.auto_color_space, self.srgb_color_space, self.gray_color_space, self.p3_color_space]  # 列表中存放三个颜色空间显示标志位
        # 使用列表推导生成选项文本, 并设置默认显示索引为当前激活的颜色空间; 清除self.comboBox_2历史显示内容并添加选项
        options = [f"{'✅' if state else ''}{name}" for state, name in zip(color_space_list, ["AUTO", "sRGB色域", "sGray色域", "Display-P3色域"])]
        self.comboBox_2.clear(); self.comboBox_2.addItems(options)
        # 设置默认显示索引为当前激活的颜色空间, 并设置自定义字体
        self.comboBox_2.setCurrentIndex(next(i for i, state in enumerate(color_space_list) if state))
        self.comboBox_2.setFont(self.font_manager_j12)

        # 设置复选框
        for checkbox in [self.checkBox_1, self.checkBox_2, self.checkBox_3, self.checkBox_4]:
            checkbox.setFont(self.font_manager_j12)
        self.checkBox_1.setText("直方图")
        self.checkBox_2.setText("EXIF信息")
        self.checkBox_3.setText("ROI信息")
        self.checkBox_4.setText("AI提示看图")   

        # 根据self.dict_label_info_visibility设置复选框状态--> 配置在函数load_settings()
        self.checkBox_1.setChecked(self.dict_label_info_visibility.get("histogram_info", False))
        self.checkBox_2.setChecked(self.dict_label_info_visibility.get("exif_info", False))
        self.checkBox_3.setChecked(self.dict_label_info_visibility.get("roi_info", False))
        self.checkBox_4.setChecked(self.dict_label_info_visibility.get("ai_tips", False))
        

        # 设置表格列和行自动调整
        header = self.tableWidget_medium.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget_medium.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget_medium.verticalHeader().setVisible(False)
        self.tableWidget_medium.verticalHeader().setDefaultSectionSize(0)
        # self.tableWidget_medium.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # 设置表格列宽自适应
        header.setFont(self.font_manager_j12)

        # 设置底部状态栏组件文本显示
        # self.statusbar_left_button # 设置按钮
        self.label_bottom.setText("📢:选中ROI信息复选框选后, 按下P键即可调出矩形框(矩形框移动逻辑同图片移动逻辑); 选中AI提示看图复选框选后, 按下P键即可发起请求(仅支持两张图); ")
        self.statusbar_button1.setText("(prev)🔼")
        self.statusbar_button2.setText("🔽(next)")


    def update_ui_styles(self):
        """更新所有UI组件的样式"""
        # 更新底部状态栏样式表
        statusbar_style = f"""
            QStatusBar {{
                background-color: {self.background_color_default};
                color: {self.font_color_default};
            }}
        """
        self.statusbar.setStyleSheet(statusbar_style)
        
        # 更新标签样式
        label_style = f"background-color: {self.background_color_default}; color: {self.font_color_default}; text-align: center; border-radius:10px;"
        self.label_0.setStyleSheet(label_style)
        statusbar_label_style = f"""
            color: {self.font_color_default}; 
            text-align: center;
            font-family: "{self.font_manager_j11.family()}";
            font-size: {self.font_manager_j11.pointSize()}pt;
        """
        self.label_bottom.setStyleSheet(statusbar_label_style)

        # 更新按钮样式
        statusbar_button_style = f"""
            QPushButton {{
                color: {self.font_color_default};
                text-align: center;
                font-family: "{self.font_manager_j11.family()}";
                font-size: {self.font_manager_j11.pointSize()}pt;
            }}
            QPushButton:hover {{
                background-color: {self.background_color_table};
                color: {self.font_color_default};
            }}
        """
        statusbar_left_button_style = f"""
            QPushButton {{
                border: none;
                color: {self.font_color_default};
                text-align: center;
                font-family: "{self.font_manager_j11.family()}";
                font-size: {self.font_manager_j11.pointSize()}pt;
            }}
            QPushButton:hover {{
                background-color: {self.background_color_table};
                color: {self.font_color_default};
            }}
        """
        self.statusbar_button1.setStyleSheet(statusbar_button_style)
        self.statusbar_button2.setStyleSheet(statusbar_button_style)
        self.statusbar_left_button.setStyleSheet(statusbar_left_button_style)

        # 更新复选框样式
        checkbox_style = f"""
        QCheckBox {{
            color: {self.font_color_default}; 
            font-weight: bold;
        }}"""
        for checkbox in [self.checkBox_1, self.checkBox_2, self.checkBox_3, self.checkBox_4]:
            checkbox.setStyleSheet(checkbox_style)

        # 更新下拉列表样式
        combobox_style = f"""
            QComboBox {{
                /* 下拉框本体样式*/
                color: {self.font_color_default};                             /* 前景字体颜色 */
                selection-background-color: {self.background_color_default};  /* 选中时背景色 */
                selection-color: {self.font_color_default};                   /* 选中时字体颜色 */
                min-height: 30px;                                             /* 最小高度 */
            }}
            /* 下拉框本体悬停样式*/
            QComboBox::hover {{
                background-color: {self.background_color_default};
                color: {self.font_color_default};
            }}   
            /* 下拉列表项样式*/
            QComboBox::item {{
                background-color: {self.background_color_default};
                color: {self.font_color_default};
            }}  
            /* 下拉列表样式*/
            QComboBox QAbstractItemView {{
                color: {self.font_color_default};              /* 字体颜色 */
                background-color: white;                       /* 背景色 */
                selection-color: {self.font_color_default};    /* 选中时字体颜色 */
                selection-background-color: {self.background_color_default}; /* 选中时背景色 */
            }}
            /* 下拉框列表项悬停样式*/
            QComboBox QAbstractItemView::item:hover {{
                background-color: {self.background_color_default};
                color: {self.font_color_default};
            }}
        """
       

        self.comboBox_1.setStyleSheet(combobox_style)
        self.comboBox_2.setStyleSheet(combobox_style)

        # 更新表格样式
        table_style = f"""
            QTableWidget {{
                background-color: {self.background_color_table};
                border: 1px solid black;
            }}
            QHeaderView::section {{
                background-color: {self.background_color_default};
                color: {self.font_color_default};
                text-align: center; 
                border-radius:10px;
            }}
        """
        self.tableWidget_medium.setStyleSheet(table_style)
        self.tableWidget_medium.horizontalHeader().setStyleSheet(table_style)

        # 更新所有图形视图的场景背景色和EXIF标签
        self.update_exif_show()


    def update_exif_show(self):
        """更新所有图形视图的场景背景色和EXIF标签
        self.graphics_views
        self.exif_texts
        """
        for index, view in enumerate(self.graphics_views):
            if view and view.scene():
                # 更新场景背景色
                qcolor = rgb_str_to_qcolor(self.background_color_table)
                view.scene().setBackgroundBrush(QBrush(qcolor))
                
                # 更新EXIF标签
                if hasattr(view, 'exif_label') and self.checkBox_2.isChecked():
                    exif_info = self.process_exif_info(self.dict_exif_info_visibility, self.exif_texts[index], False)
                    view.exif_label.setVisible(False)
                    view.exif_label.setText(exif_info if exif_info else "解析不出exif信息!")
                    view.exif_label.setVisible(True)
                    view.exif_label.setStyleSheet(f"color: {self.font_color_exif}; background-color: transparent; font-weight: 400;")
                    

    def set_progress_bar(self):
        """设置进度条"""
        
        # 添加进度条并设置进度条位置为窗口中心
        self.progress_bar = QProgressBar(self)
        self.update_progress_bar_position()

        # 设置进度条样式
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #e3ebff;
                border-radius: 0px;
                text-align: center;
                font-family: "微软雅黑";
                font-size: 11pt;
                color: black;
                height: 40px;
                margin: 0px;
                padding: 0px;
                background-clip: content-box;
            }
            QProgressBar::chunk {
                border-radius: 0px;
                margin: 0px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #36D1DC, stop:1 #5B86E5);
            }
        """)
  
        # 设置进度条基本属性(窗口背景透明、文字居中、最大值、初始值、默认隐藏、重绘)
        # self.progress_bar.setAttribute(Qt.WA_TranslucentBackground)
        self.progress_bar.setAlignment(Qt.AlignCenter) 
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.repaint()  
        # QApplication.processEvents()
        

    def update_progress_bar_position(self):
        """更新进度条位置，确保其始终在窗口中心"""
        self.progress_bar.setGeometry(
            (self.width() - self.progress_bar.width()) // 2,
            (self.height() - self.progress_bar.height()) // 2,
            600, 50
        )

    def open_settings_window(self):
        """打开设置窗口"""
        print("打开设置窗口...")
        from src.view.sub_setting_view import setting_Window
        self.setting_window = setting_Window(self)
        
        # 设置窗口标志，确保设置窗口显示在最顶层
        self.setting_window.setWindowFlags(
            Qt.Window |  # 独立窗口
            Qt.WindowStaysOnTopHint |  # 保持在最顶层
            Qt.WindowCloseButtonHint |  # 显示关闭按钮
            Qt.WindowMinimizeButtonHint |  # 显示最小化按钮
            Qt.WindowMaximizeButtonHint  # 显示最大化按钮
        )
        
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
            

    def update_progress(self, value):
        """更新进度条数值"""
        # print("进度条--更新进度条数值")
        if hasattr(self, 'progress_bar'):
            # 设置进度条数值
            self.progress_bar.setValue(value)
            self.progress_bar.repaint()
            # QApplication.processEvents()


    def resizeEvent(self, event):
        """窗口大小改变时更新进度条位置"""
        if hasattr(self, 'progress_bar'):
            self.update_progress_bar_position()

        # 获取表格的尺寸信息 print("table_width_heigth_default:", self.table_width_heigth_default)
        self.table_width_heigth_default = [self.tableWidget_medium.width(), self.tableWidget_medium.height()]

        super(SubMainWindow, self).resizeEvent(event)


    """怎么优化函数，加快处理速度，优化内存占用"""
    def set_images(self, image_paths, index_list):
        """更新图片显示"""
        try:
            # 记录开始时间
            start_time_set_images = time.time()

            # 判断形参是否有效
            if not image_paths or not index_list:
                print("[set_images]-->waring:主界面传入到看图子界面的图片路径和图片索引为None")
                return False

            # 设置正在更新标志位，设置传入的图片数量
            print("开始更新图片...")
            self.is_updating, num_images = True, len(image_paths)
             
            # 更新当前显示的图片路径列表
            self.images_path_list, self.index_list = image_paths, index_list
            
            # 设置进度条初始化, 如果进度条不存在，则创建进度条
            if not hasattr(self, 'progress_bar'):
                self.set_progress_bar()
            # 若存在进度条，则启动进度条显示, 并发送进度条更新信号
            self.progress_bar.setVisible(True)
            self.progress_updated.emit(0)


            # 调用封装后的函数,将看图界面图片索引发送到aebox中,(注意：会拿主界面中的复选框使能来判断是否发送图片索引)
            self.sync_image_index_with_aebox(self.images_path_list, self.index_list) if self.parent_window.statusbar_checkbox.isChecked() else 0

            try:
                # 先禁用表格自动刷新，确保表格可见，然后释放之前的表格显示等资源
                self.tableWidget_medium.setUpdatesEnabled(False) 
                self.tableWidget_medium.show()
                self.cleanup()

                # 1. 预先分配数据结构, 发送进度条更新信号
                self.exif_texts = [None] * num_images
                self.histograms = [None] * num_images
                self.original_rotation = [None] * num_images
                self.graphics_views = [None] * num_images
                self.original_pixmaps = [None] * num_images  
                self.rgb_pixmaps = [None] * num_images
                self.gray_pixmaps = [None] * num_images  
                self.p3_pixmaps = [None] * num_images
                self.cv_imgs = [None] * num_images 
                self.pil_imgs = [None] * num_images 
                self.base_scales = [None] * num_images
                self._scales_min = [None] * num_images


                # 2. 设置表头行列结构以及单元格内容（文件夹名或文件名） 
                self.toggle_title_display(self.is_title_on) # 设置列表头是否显示和隐藏
                self.tableWidget_medium.setColumnCount(num_images)
                self.tableWidget_medium.setRowCount(1)
                folder_names = [os.path.basename(os.path.dirname(path)) for path in image_paths]
                if len(set(folder_names)) == 1: # 如果图片路径都在同一个文件夹下，则将文件夹名作为表头
                    _tmp = folder_names[0]
                    folder_names = [_tmp + ":" + os.path.basename(path) for path in image_paths]
                self.tableWidget_medium.setHorizontalHeaderLabels(folder_names)
                


                # 3. 使用线程池并行处理图片
                self.progress_updated.emit(50)
                # 使用并行解析图片的pil格式图、cv_img、histogram、pixmap、gray_pixmap、p3_pixmap以及exif等信息
                with ThreadPoolExecutor(max_workers=min(len(image_paths), cpu_count() - 2)) as executor:
                    futures = list(executor.map(self._process_image, enumerate(image_paths)))

                # 4. 计算目标尺寸
                target_width, target_height, avg_aspect_ratio = self._calculate_target_dimensions(futures)
                

                # 5. 批量更新UI, 更新进度条
                self.progress_updated.emit(100)
                for index, result in enumerate(futures):
                    if result and result[1]:
                        # 获取图片处理结果
                        data = result[1]

                        # 根据下拉框索引判断pixmap类型(0:原始图、1:RGB色域图、2:gray色域图 3:p3色域图)
                        pixmap = data['pixmap']
                        if self.comboBox_2.currentIndex() == 1:
                            pixmap = data['rgb_pixmap']
                        if self.comboBox_2.currentIndex() == 2:
                            pixmap = data['gray_pixmap']
                        if self.comboBox_2.currentIndex() == 3:
                            pixmap = data['p3_pixmap']

                        # 创建并设置场景，设置场景颜色为读取的背景色
                        scene = QGraphicsScene(self)
                        qcolor = rgb_str_to_qcolor(self.background_color_table)
                        scene.setBackgroundBrush(QBrush(qcolor)) 

                        # 创建图片项
                        pixmap_item = QGraphicsPixmapItem(pixmap)
                        pixmap_item.setTransformOriginPoint(pixmap.rect().center())
                        scene.addItem(pixmap_item)
                        
                        # 处理EXIF可见性字典和亮度统计信息
                        exif_info = self.process_exif_info(self.dict_exif_info_visibility, data['exif_info'], data['hdr'])
                        stats_info = data['stats'] if data['cv_img'] is not None else "None"
                        
                        # 创建并设置视图
                        view = MyGraphicsView(scene, exif_info, stats_info, self)
                        view.pixmap_items = [pixmap_item]
                        
                        # 设置视图的缩放，先计算基础缩放比例，再计算最终缩放比例，最后应用缩放
                        w, h = pixmap.width(), pixmap.height()
                        final_scale = min(target_width / w, target_height / h) * self.set_zoom_scale(avg_aspect_ratio, target_width, target_height)
                        view.scale(final_scale, final_scale)
                        
                        # 设置直方图、EXIF、亮度统计信息、cv_img
                        view.set_histogram_visibility(self.checkBox_1.isChecked())
                        view.set_exif_visibility(self.checkBox_2.isChecked(), self.font_color_exif)
                        view.set_stats_visibility(self.stats_visible) 
                        view.set_histogram_data(data['histogram']) if data['histogram'] is not None else ...
                        view.set_cv_image(data['cv_img']) if data['cv_img'] is not None else ...

                        # 保存数据
                        self.graphics_views[index] = view
                        self.original_rotation[index] = pixmap_item.rotation()
                        self.original_pixmaps[index] = data['pixmap']
                        self.rgb_pixmaps[index] = data['rgb_pixmap']
                        self.gray_pixmaps[index] = data['gray_pixmap']
                        self.p3_pixmaps[index] = data['p3_pixmap']
                        self.cv_imgs[index] = data['cv_img']
                        self.pil_imgs[index] = data['pil_image']
                        self.exif_texts[index] = data['exif_info']
                        self.histograms[index] = data['histogram']
                        self.base_scales[index] = final_scale
                        self._scales_min[index] = final_scale

                        # 更新表格
                        # self.tableWidget_medium.setCellWidget(0, index, view)

                # 启动表格自动刷新，批量更新表格内容
                self.tableWidget_medium.setUpdatesEnabled(True)
                for index, view in enumerate(self.graphics_views):
                    if view is not None:
                        self.tableWidget_medium.setCellWidget(0, index, view)

                return True
            except Exception as e:
                print(f"更新图片时发生错误: {e}")
                return False
            finally:
                # 完成后恢复确定模式
                self.progress_bar.setVisible(False)  # 隐藏进度条
                self.is_updating = False

                # 释放futures
                futures = None

                # 记录结束时间并计算耗时
                print(f"处理图片总耗时: {(time.time() - start_time_set_images):.2f} 秒")

        except Exception as e:
            print(f"❌ [set_images]-->处理图片时发生错误: {e}")
            return False

    def _calculate_target_dimensions(self, futures, aspect_threshold=1.2):
        """
        计算多张图片的目标尺寸

        Args:
            futures: 包含图片处理结果的future列表
            aspect_threshold: 宽高比阈值, 默认1.2

        Returns:
            tuple: (target_width, target_height, avg_aspect_ratio) 目标宽度、高度和平均宽高比

        Raises:
            ValueError: 当输入数据无效时抛出
            ZeroDivisionError: 当计算比例时出现除零错误
            Exception: 其他未预期的错误
        """
        try:
            # 使用列表推导获取有效的宽高数据，同时进行数据验证
            dimensions = []
            for result in futures:
                if not result or not result[1] or not result[1].get('pixmap'):
                    continue
                try:
                    width = result[1]['pixmap'].width()
                    height = result[1]['pixmap'].height()
                    if width <= 0 or height <= 0:
                        continue
                    dimensions.append((width, height))
                except (AttributeError, KeyError):
                    continue

            if not dimensions:
                raise ValueError("没有有效的图片尺寸数据")

            # 使用zip和map优化计算
            widths, heights = zip(*dimensions)
            max_width, max_height = max(widths), max(heights)

            # 使用map和zip优化面积计算
            areas = list(map(lambda x: x[0] * x[1], dimensions))
            total_area = sum(areas)

            if total_area == 0:
                raise ZeroDivisionError("总面积为0，无法计算平均宽高比")

            # 优化宽高比计算
            aspect_ratios = map(lambda d: d[0]/d[1], dimensions)
            weighted_ratios = map(lambda r, a: r * a, aspect_ratios, areas)
            avg_aspect_ratio = sum(weighted_ratios) / total_area

            # 根据宽高比确定目标尺寸
            if avg_aspect_ratio > aspect_threshold:
                # 横向图片
                target_width = max_width
                target_height = int(target_width / avg_aspect_ratio)
            elif avg_aspect_ratio < 1/aspect_threshold:
                # 纵向图片
                target_height = max_height
                target_width = int(target_height * avg_aspect_ratio)
            else:
                # 接近方形
                target_width = int((max_width + max_height * avg_aspect_ratio) / 2.0)
                target_height = int((max_height + max_width / avg_aspect_ratio) / 2.0)

            # 确保尺寸有效
            target_width = max(1, target_width)
            target_height = max(1, target_height)

            return target_width, target_height, avg_aspect_ratio

        except ValueError as ve:
            print(f"计算目标尺寸时出现值错误: {ve}")
            return 1, 1, 1.0
        except ZeroDivisionError as ze:
            print(f"计算目标尺寸时出现除零错误: {ze}")
            return 1, 1, 1.0
        except Exception as e:
            print(f"计算目标尺寸时出现未预期错误: {e}")
            return 1, 1, 1.0

    def _process_image(self, args):
        """
        该函数主要是实现了图片基础信息提取功能.
        Args:
            args: 包含 (index, path) 的元组
        Returns:
            index, {
                'pil_image': img,            # PIL图像
                'cv_img': cv_img,            # OpenCV图像
                'histogram': histogram,      # 直方图信息
                'pixmap': pixmap,            # 原始pixmap格式图
                'rgb_pixmap': rgb_pixmap,    # pixmap格式RGB色域图
                'gray_pixmap': gray_pixmap,  # pixmap格式灰度图
                'p3_pixmap': p3_pixmap,      # pixmap格式p3色域图
                'exif_info': exif_info,      # exif信息
                'stats': stats_text,         # 添加亮度/RGB/LAB等信息
            }
        Note:
            注意事项，列出任何重要的假设、限制或前置条件.
        """
        # 记录开始时间
        start_time_process_image = time.time()  
        index, path = args
        try:
            # 如果图片是heic格式，则转换为jpg格式
            if path.endswith(".heic"):
                if new_path := extract_jpg_from_heic(path):
                    path = new_path

            # 如果图片不存在，则抛出异常
            if not os.path.exists(path):
                raise FileNotFoundError(f"❌ 图片不存在: {path}")

            # 使用PIL获取所需的图像信息
            with Image.open(path) as img:
                """1. 获取pil_img的格式,确保函数get_exif_info能正确加载信息; 生成sRGB色域的pil_img和pixmap--------------------------------"""
                img_format = img.format
                pixmap = pil_to_pixmap((img := self.p3_converter.get_pilimg_auto(img)))

                """2. 使用线程池并行生成，获取histogram, cv_img, stats, gray_pixmap, p3_pixmap等图像信息---------------------------------"""
                histogram, cv_img, stats, rgb_pixmap, gray_pixmap, p3_pixmap = self._generate_pixmaps_parallel(img)
                # print(f"色域转换耗时: {(time.time() - start_time_process_image):.2f} 秒")

            """3. EXIF信息提取-------------------------------------------------------------------------------------------------------""" 
            # 提取图片的基础信息
            basic_info = self.get_pic_basic_info(path, img, pixmap, self.index_list[index])

            # piexf解析曝光时间光圈值ISO等复杂的EXIF信息
            exif_info = self.get_exif_info(path, img_format) + basic_info

            # （高通平台）检测是否存在同图片路径的xml文件  将lux_index、DRCgain写入到exif信息中去
            hdr_flag, xml_path = False, Path(path).with_suffix("").as_posix() + "_new.xml"
            if os.path.exists(xml_path):
                # 提取xml中lux_index、cct、drcgain等关键信息，拼接到exif_info
                exif_info_qpm, hdr_flag = load_xml_data(xml_path)
                exif_info += exif_info_qpm
                
            # （MTK平台）检测是否存在同图片路径的xml文件  将lux_index、DRCgain写入到exif信息中去
            exif_path = path + ".exif"
            if os.path.exists(exif_path):
                # 提取xml中lux_index、cct、drcgain等关键信息，拼接到exif_info
                exif_info_mtk, hdr_flag = load_exif_data(exif_path)
                exif_info += exif_info_mtk
                
            # （展锐平台）检测是否存在同图片路径的xml文件  将lux_index、DRCgain写入到exif信息中去
            txt_path = Path(path).with_suffix("").as_posix() + ".txt"
            if os.path.exists(txt_path):
                # 提取xml中lux_index、cct、drcgain等关键信息，拼接到exif_info
                exif_info_unisoc, hdr_flag = load_txt_data(txt_path)
                exif_info += exif_info_unisoc  
                
            # 处理EXIF信息，根据可见性字典更新
            # self.str_exif_info = exif_info
            # exif_info = self.process_exif_info(self.dict_exif_info_visibility, exif_info, hdr_flag)

            # 拼接亮度统计信息，计算亮度统计信息方法calculate_image_stats放到并行函数_generate_pixmaps_parallel中执行
            stats_text = f"亮度: {stats['avg_brightness']}\n对比度(L值标准差): {stats['contrast']}" \
            f"\nLAB: {stats['avg_lab']}\nRGB: {stats['avg_rgb']}\nR/G: {stats['R_G']}  B/G: {stats['B_G']}"

            return index, {
                'pil_image': img,            # PIL图像
                'cv_img': cv_img,            # OpenCV图像
                'histogram': histogram,      # 直方图信息
                'pixmap': pixmap,            # 原始pixmap格式图
                'rgb_pixmap': rgb_pixmap,    # pixmap格式RGB色域图
                'gray_pixmap': gray_pixmap,  # pixmap格式灰度图
                'p3_pixmap': p3_pixmap,      # pixmap格式p3色域图
                'exif_info': exif_info,      # exif信息
                'hdr': hdr_flag,             # 添加亮度/RGB/LAB等信息
                'stats': stats_text,         # 添加亮度/RGB/LAB等信息
                
            }
        except Exception as e:
            print(f"[process_image]-->error: 处理图片失败 {path}: {e}")
            return index, None
        finally:
            # 记录结束时间并计算耗时
            print(f"处理图片{index}_{os.path.basename(path)} 耗时: {(time.time() - start_time_process_image):.2f} 秒")


    def _generate_pixmaps_parallel(self, img):
        """
        该函数主要是实现了一个线程池并行生成不同色域的pixmap.
        Args:
            img (Image.Image): PIL Image.
        Returns:
            histogram, cv_img, stats, gray_pixmap, p3_pixmap.
        Note:
            # 获取cv_img
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            # 获取亮度统计信息
            stats = calculate_image_stats(cv_img, resize_factor=0.1)
            # 获取直方图
            histogram = self.calculate_brightness_histogram(img) 
            # 获取sRGB色域图
            gray_image = img.convert('L')
            gray_pixmap = pil_to_pixmap(gray_image)
            # 获取display-p3色域图
            p3_image = self.p3_converter.convert_color_space(img, "Display-P3", intent="Relative Colorimetric")
            p3_pixmap = pil_to_pixmap(p3_image)
        """
        
        """并行生成不同色域的pixmap"""
        def generate_rgb():
            try:
                rgb_image = self.p3_converter.get_pilimg_sRGB(img)
                return pil_to_pixmap(rgb_image)
            except Exception as e:
                print(f"sGray转换失败: {str(e)}")
                return pil_to_pixmap(img)

        def generate_gray():
            try:
                # 先转换为灰度区间pil_img，然后转换为pixmap
                pil_img = img if img.mode == "L" else img.convert('L')
                gray_pixmap = pil_to_pixmap(pil_img)

                return gray_pixmap
            except Exception as e:
                print(f"sGray转换失败: {str(e)}")
                return pil_to_pixmap(img)
            
        def generate_p3():
            try:
                p3_image = self.p3_converter.convert_color_space(img, "Display-P3", intent="Relative Colorimetric")
                return pil_to_pixmap(p3_image)
            except Exception as e:
                print(f"display-p3转换失败: {str(e)}")
                return pil_to_pixmap(img)

        def generate_cv_img():
            try:
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                stats = calculate_image_stats(cv_img, resize_factor=0.1)
                return cv_img, stats
            except Exception as e:
                print(f"cv_img转换失败: {str(e)}")
                return None, None

        def generate_histogram():
            try:
                return self.calculate_brightness_histogram(img)
            except Exception as e:
                print(f"cv_img转换失败: {str(e)}")
                return None
            
        # 使用线程池并行处理 min(4, cpu_count()) ，设置最大线程数
        with ThreadPoolExecutor(max_workers=min(5, cpu_count())) as executor:
            # 提交所有任务
            rgb_future = executor.submit(generate_rgb)
            gray_future = executor.submit(generate_gray)
            p3_future = executor.submit(generate_p3)
            cv_future = executor.submit(generate_cv_img)
            histogram_future = executor.submit(generate_histogram)

            # 获取结果
            rgb_pixmap = rgb_future.result()
            gray_pixmap = gray_future.result()
            p3_pixmap = p3_future.result()
            cv_img, stats =  cv_future.result()
            histogram =  histogram_future.result()

        return histogram, cv_img, stats, rgb_pixmap, gray_pixmap, p3_pixmap

    def sync_image_index_with_aebox(self, images_path_list, index_list):
        """同步当前图片索引到aebox应用,与aebox的基础通信协议如下:
        主要使用函数get_api_data进行fast api通信
        1. 直接发送指定索引0,get_api_data(url=http://127.0.0.1:8000/select_image/0, timeout=2)
        2. 获取aebox当前选中的图片信息,get_api_data(url=http://127.0.0.1:8000/current_image, timeout=2)
        3. 获取aebox当前图片数据列表,get_api_data(url=http://127.0.0.1:8000/image_list, timeout=2)
        """
        try:
            # 1. 预检查程序aebox是否启动
            if not check_process_running("aebox"):
                print("❌ [sync_image_index_with_aebox]-->无法同步索引到[aebox]")
                return False

        
            # 2. 读取配置文件,获取当前fast api的地址和端口；一般默认设置为 http://127.0.0.1:8000
            host = ( 
                f"http://{self.parent_window.fast_api_host}:{self.parent_window.fast_api_port}" 
                if self.parent_window and self.parent_window.fast_api_host and self.parent_window.fast_api_port else
                "http://127.0.0.1:8000"
            )

            # 3. 获取当前看图子界面打开的图片名称列表
            set_hiviewer_images = set([os.path.basename(path) for path in images_path_list])


            # 4. 使用fast api 获取到当前aebox图片列表信息；返回列表数据 list_aebox_images
            list_aebox_images = json.loads(get_api_data(
                url=f"{host}/image_list",
                timeout=3) or '{}'
            ).get('filenames', [])

            # 5. 使用集合提高查找效率,得到匹配index并发送到aebox
            if list_aebox_images:
                matching_indices = [i for i, name in enumerate(list_aebox_images) if name in set_hiviewer_images]

            if len(matching_indices) == 1:
                new_index = matching_indices[0] + 1
                if get_api_data(f"{host}/select_image/{new_index}", timeout=2):
                    print(f"✅ [sync_image_index_with_aebox]-->成功同步图片到aebox: {list_aebox_images[matching_indices[0]]}")
                    return True
            else:
                print("⭕ [sync_image_index_with_aebox]-->aebox中未找到唯一匹配的图片")
                return False

        except Exception as e:
            print(f"❌ [sync_image_index_with_aebox]-->error: 同步索引异常: {str(e)}")
            return False


    def process_exif_info(self, visibility_dict, exif_info, hdr_flag):
        """处理EXIF信息，将其转换为字典并根据可见性字典更新"""
        try:
            # 将 exif_info 转换为字典
            exif_dict = convert_to_dict(exif_info)

            # HDR标签为auto且存在Lux时，如果hdr_flag为True，则设置为auto-on，否则设置为auto-off
            # hdr_flag 是读取xml文件时，是否存在EVFrameSA标签判断
            if exif_dict.get("HDR", "") == 'auto' and  exif_dict.get("Lux", ""):
                exif_dict['HDR'] = 'auto_(ON)' if hdr_flag else 'auto_(OFF)'
            
            # 根据字典中的键值对，更新 exif_dict 中的可见性值
            for key, value in visibility_dict.items():
                if not value and key in exif_dict:  # 仅在键存在时才删除
                    exif_dict.pop(key)

            # 按照 visibility_dict 的顺序生成字符串
            result = []
            for key in visibility_dict.keys():
                if key in exif_dict:  # 仅添加存在于 exif_dict 中的键
                    result.append(f"{key}: {exif_dict[key]}")

            return '\n'.join(result)

        except Exception as e:
            print(f"❌ [process_exif_info]-->处理EXIF信息时发生错误: {e}")
            return ""  # 返回空字符串或其他适当的默认值


    def set_zoom_scale(self, avg_aspect_ratio,target_width,target_height):
        """
        该函数主要是实现了根据图片数量、平均宽高比、目标宽度和目标高度计算真实的缩放因子.
        Args:
            avg_aspect_ratio (float): 平均宽高比
            target_width (int): 目标宽度
            target_height (int): 目标高度
        Returns:
            float: 缩放因子
        """
        
        # 计算表格中单个单元格的宽度和高度
        if self.is_title_on:
            sigle_table_w = (self.table_width_heigth_default[0]-18) / len(self.images_path_list)
            sigle_table_h = self.table_width_heigth_default[1]-55
        else:
            sigle_table_w = (self.table_width_heigth_default[0]-5) / len(self.images_path_list)
            sigle_table_h = self.table_width_heigth_default[1]-5

        if avg_aspect_ratio > 1: #横向图片
            zoom_scale = sigle_table_w/target_width
            while ((zoom_scale*target_height) >= sigle_table_h):
                zoom_scale *= 0.995
        else: #纵向图片
            zoom_scale = sigle_table_h/target_height
            while ((zoom_scale*target_width) >= sigle_table_w):
                zoom_scale *= 0.995

        # 更新当前缩放因子, zoom_scale < 0 时 直接设置为 1.0不缩放
        zoom_scale = zoom_scale if zoom_scale > 0 else 1.0


        return zoom_scale
    

    def cleanup(self):
        """清理所有资源"""
        try:
            # 清理表格
            self.tableWidget_medium.clearContents()
            self.tableWidget_medium.setRowCount(0)
            self.tableWidget_medium.setColumnCount(0)
            
            # 清理场景和视图
            for view in self.graphics_views:
                if view:
                    if view.scene():
                        view.scene().clear()
                    view.setScene(None)

            if self.roi_selection_active: # 切换图片自动清除ROI信息框
                self.roi_selection_active = False
            

            # 清理所有列表
            self.exif_texts.clear()
            self.histograms.clear()
            self.original_rotation.clear()
            self.graphics_views.clear()
            self.original_pixmaps.clear()
            self.rgb_pixmaps.clear()
            self.gray_pixmaps.clear()
            self.p3_pixmaps.clear()
            self.cv_imgs.clear()
            self.pil_imgs.clear()
            self.base_scales.clear()
            self._scales_min.clear()

            # 清理线程池
            if hasattr(self, 'thread_pool'):
                self.thread_pool.clear()

            # 强制垃圾回收
            gc.collect()
            
        except Exception as e:
            print(f"❌ [cleanup]-->清理资源时发生错误: {e}")


    def show_menu_combox1(self, index):
        """下拉框self.comboBox_1中显示多级菜单项
        下拉框1的主选项如下:
            ["📌颜色设置", "🔁一键重置", "🔽背景颜色", "🔽表格填充颜色", "🔽字体颜色", "🔽exif字体颜色"]
        """
        try:
            if not index:     # index == 0 颜色设置，不做任何操作
                print("[show_menu_combox1]-->看图子界面--点击了颜色配置选项")
                # 从json文件加载配置, 更新样式表
                self.load_settings()
                self.update_ui_styles()
            elif index == 1:  # index == 1 一键重置
                self.background_color_default = "rgb(173,216,230)" # 背景默认色_好蓝
                self.background_color_table = "rgb(127,127,127)"   # 表格填充背景色_18度灰
                self.font_color_default = "rgb(0,0,0)"           # 字体默认颜色_纯黑色
                self.font_color_exif = "rgb(255,255,255)"          # exif字体默认颜色_纯白色
                self.comboBox_1.setCurrentIndex(0)                 # 设置默认显示索引为0
                # 更新样式表
                self.update_ui_styles()
            else: 
                # 创建菜单
                self.menu_1 = QMenu(self)

                # 设置菜单项悬停样式
                hover_bg = self.background_color_default  # 背景颜色
                hover_text = self.font_color_default      # 字体颜色
                self.menu_1.setStyleSheet(f"""
                    QMenu::item:selected {{
                        background-color: {hover_bg};
                        color: {hover_text};
                    }}
                    QMenu::item:hover {{
                        background-color: {hover_bg};
                        color: {hover_text};
                    }}
                """)

                # 定义颜色选项 从self.color_rgb_settings中获取
                # color_options = ['18度灰', '石榴红', '乌漆嘛黑', '铅白', '水色', '石青', '茶色', '天际', '晴空', '苍穹', 
                # '湖光', '曜石', '天际黑', '晴空黑', '苍穹黑', '湖光黑', '曜石黑']
                color_options = list(self.color_rgb_settings.keys())

                # 添加颜色选项到菜单
                for color in color_options:
                    action = QAction(color, self)
                    # 传递 color 和 index
                    action.triggered.connect(lambda checked, color=color, index=index: self.on_comboBox_1_changed(color, index))  
                    self.menu_1.addAction(action)
                self.menu_1.setFont(self.font_manager_j12)

                # 获取 QComboBox 顶部的矩形区域
                rect = self.comboBox_1.rect()
                global_pos = self.comboBox_1.mapToGlobal(rect.bottomLeft())

                # 弹出 QMenu
                self.menu_1.exec_(global_pos)
        except Exception as e:
            print(f"❌ [show_menu_combox1]-->处理下拉框选项时发生未知错误: {e}")
        

    def on_comboBox_1_changed(self, color, index):
        """颜色设置二级菜单触发事件"""
        """优化方案说明：
        1. 使用字典映射替代多个if-elif分支，提高可维护性
        2. 使用海象运算符(walrus operator)合并条件判断使用setattr动态设置属性，避免重复代码
        4. 将关联操作集中到单个条件判断中，逻辑更紧凑保持原有功能不变，但代码行数减少50%
        6. 更易于扩展新的颜色配置项，只需更新index_map字典即可
        """
        if True: # 优化方案
            # 使用字典映射索引与属性名的关系
            index_map = {
                2: 'background_color_default',
                3: 'background_color_table', 
                4: 'font_color_default',
                5: 'font_color_exif'
            }
            
            if color_rgb := self.color_rgb_settings.get(color):
                if prop_name := index_map.get(index):
                    setattr(self, prop_name, color_rgb)
                    self.update_ui_styles()
                    self.comboBox_1.setCurrentIndex(0)
        if False:  # 原始方案
            # 根据选择的color颜色从color_rgb_settings中获取rgb
            color_rgb = self.color_rgb_settings.get(color, "")
            if color_rgb:
                if index==2:
                    self.background_color_default = color_rgb
                elif index ==3:
                    self.background_color_table = color_rgb
                elif index ==4:
                    self.font_color_default = color_rgb
                elif index ==5:
                    self.font_color_exif = color_rgb
            # 更新样式表
            self.update_ui_styles()
            # 设置默认显示索引为0
            self.comboBox_1.setCurrentIndex(0)                 
            # print(f"Selected color: {color}, Index: {index}")
        

    def update_comboBox2(self):
        """更新下拉框self.comboBox_2的显示"""
        # 定义颜色空间状态列表
        color_spaces = [
            (self.auto_color_space, "AUTO"),
            (self.srgb_color_space, "sRGB色域"),
            (self.gray_color_space, "sGray色域"), 
            (self.p3_color_space, "Display-P3色域")
        ]
        
        # 使用列表推导生成选项文本
        options = [f"{'✅' if state else ''}{label}" for state, label in color_spaces]
        
        # 批量更新下拉框选项
        for i, text in enumerate(options):
            self.comboBox_2.setItemText(i, text)
    

    def clean_color_space(self,):
        """清除颜色空间的显示标志位"""
        self.auto_color_space = False
        self.srgb_color_space = False
        self.gray_color_space = False
        self.p3_color_space = False


    def on_comboBox_2_changed(self, index):
        """图像色彩显示空间下拉框self.comboBox_2内容改变时触发事件
        ["✅AUTO","✅sRGB色域", "✅sGray色域", "✅Display-P3色域"]
        """
        # 更新所有图形视图的场景视图
        for i, view in enumerate(self.graphics_views):
            if view and view.scene() :
                try:
                    original_pixmap = self.original_pixmaps[i]
                    current_rotation = view.pixmap_items[0].rotation() if view.pixmap_items else 0

                    if index == 0 :  # AUTO档，自动检测加载色域
                        # 设置当前启用的图像色彩显示空间
                        self.clean_color_space()
                        self.auto_color_space = True
                        self.update_comboBox2()

                        # 调用列表self.original_pixmaps[i]中存储的原始图pixmap
                        converted_pixmap = original_pixmap

                    # 根据选择的色彩空间转换图像
                    elif index == 1 and self.rgb_pixmaps[i] is not None:  # sRGB色域
                        # 设置当前启用的图像色彩显示空间
                        self.clean_color_space()
                        self.srgb_color_space = True
                        self.update_comboBox2()

                        # 调用列表self.rgb_pixmaps[i]中存储的sRGB色域图pixmap
                        converted_pixmap = self.rgb_pixmaps[i]
                    elif index == 2 and self.gray_pixmaps[i] is not None:  # 灰度图色域
                        # 设置当前启用的图像色彩显示空间
                        self.clean_color_space()
                        self.gray_color_space = True
                        self.update_comboBox2()

                        # 调用列表self.gray_pixmaps[i]中存储的灰度图pixmap
                        converted_pixmap = self.gray_pixmaps[i]
                    elif index == 3 and self.p3_pixmaps[i] is not None:  # p3色域
                        # 设置当前启用的图像色彩显示空间
                        self.clean_color_space()
                        self.p3_color_space = True
                        self.update_comboBox2()

                        # 调用列表self.p3_pixmaps[i]中存储的p3色域图pixmap
                        converted_pixmap = self.p3_pixmaps[i]

                    # 更新视图显示
                    view.pixmap_items[0].setPixmap(converted_pixmap)
                    view.pixmap_items[0].setRotation(current_rotation)
                    view.centerOn(view.mapToScene(view.viewport().rect().center()))
                    
                    # 更新场景背景色
                    qcolor = rgb_str_to_qcolor(self.background_color_table)
                    view.scene().setBackgroundBrush(QBrush(qcolor))
                    
                except Exception as e:
                    print(f"❌ [on_comboBox_2_changed]-->色彩空间转换失败: {str(e)}")
        # 更新UI
        self.update()
        QApplication.processEvents() 
                

    def toggle_title_display(self, state):
        """切换看图界面表格组件列表头的显示和隐藏"""
        try:
            self.is_title_on = state
            self.tableWidget_medium.horizontalHeader().setVisible(self.is_title_on)  
        except Exception as e:
            print(f"❌ [toggle_title_display]-->处理toggle_title_display函数时发生错误: {e}")


    def toggle_exif_info(self, state):
        print(f"[toggle_exif_info]-->切换 EXIF 信息: {'显示' if state == Qt.Checked else '隐藏'}")
        try:
            for view, exif_text in zip(self.graphics_views, self.exif_texts):
                if exif_text:
                    # 传入字体颜色参数
                    view.set_exif_visibility(state == Qt.Checked, self.font_color_exif)
        except Exception as e:
            print(f"❌ [toggle_exif_info]-->处理toggle_exif_info函数时发生错误: {e}")


    def toggle_histogram_info(self, state):
        print(f"[toggle_histogram_info]-->看图界面切换直方图信息: {'显示' if state == Qt.Checked else '隐藏'}")
        try:
            for view, histogram in zip(self.graphics_views, self.histograms):
                if histogram:
                    view.set_histogram_visibility(state == Qt.Checked)
        except Exception as e:
            print(f"❌ [toggle_histogram_info]-->处理toggle_histogram_info函数时发生错误: {e}")


    def roi_stats_checkbox(self, state):
        try:
            self.stats_visible = not self.stats_visible # 控制显示开关
            for view in self.graphics_views:
                if view:
                    view.set_stats_visibility(state == Qt.Checked)

        except Exception as e:
            print(f"❌ [roi_stats_checkbox]-->显示图片统计信息时发生错误: {e}")
        finally:
            # 延时1秒后更新is_updating为False
            QTimer.singleShot(1000, lambda: setattr(self, 'is_updating', False))

    def ai_tips_info(self, state):
        try:    
            if state == Qt.Checked:
                self.ai_tips_flag = True
                self.is_updating = False
                self.label_bottom.setText(f"📢:开启AI提示看图复选框提示, 按下快捷键P发起请求(仅支持两张图). 另: 关闭AI提示看图复选框, 打开ROI信息复选框的状态下, 按P键才会调出矩形框")
            else:
                self.ai_tips_flag = False
                self.is_updating = False
                self.label_bottom.setText(f"📢:选中ROI信息复选框选后, 按下P键即可调出矩形框(矩形框移动逻辑同图片移动逻辑); 选中AI提示看图复选框选后, 按下P键即可发起请求(仅支持两张图);")
        except Exception as e:
            print(f"❌ [ai_tips_info]-->处理ai_tips_info函数时发生错误: {e}")

    def calculate_brightness_histogram(self, img):
        """传入PIL图像img,将其转换为灰度图, 输出直方图和灰度pixmap"""
        try:
            # 处理PIL图像对象
            if isinstance(img, Image.Image):  
                # 转换为灰度图
                gray_img = img.convert('L')
                
                # 将灰度图转换为RGB模式（QPixmap需要RGB格式）
                # gray_rgb = gray_img.convert('RGB')
                
                # 转换为pixmap
                # gray_pixmap = pil_to_pixmap(gray_rgb)
                
                # 使用numpy计算直方图
                histogram = np.array(gray_img).flatten()
                _hist_counts = np.bincount(histogram, minlength=256)
                histogram = _hist_counts.tolist()

                return histogram
            else:
                print(f"❌ [calculate_brightness_histogram]-->无法加载图像")
                return None, None

        except Exception as e:
            print(f"❌ [calculate_brightness_histogram]-->计算直方图失败\n错误: {e}")
            return None, None
        
    
    def get_pic_basic_info(self, path, pil_img, pixmap, index):
        """
        该函数主要是实现了提取图片基础的exif信息的功能.
        Args:
            param1 (type): Description of param1.
            param2 (type): Description of param2.
        Returns:
            type: Description of the return value.
        """
        try:
            # 图片名称
            pic_name = os.path.basename(path)

            # 图片大小
            file_size = os.path.getsize(path)  # 文件大小（字节）
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 ** 2:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size / (1024 ** 2):.2f} MB"

            # 图片尺寸，pixmap是旋转后的图像，尺寸会更准确
            width, height = pixmap.width(), pixmap.height()

            basic_info = f"图片名称: {pic_name}\n图片大小: {size_str}\n图片尺寸: {width} x {height}\n图片张数: {index}"

            # 针对小米相机拍图会写入hdr和zoom增加额外信息
            ultra_info = ''  # 初始化空字符串
            if pil_img and (exif_dict := pil_img.getexif()) is not None and (info := exif_dict.get(39321,None)) is not None:
                if info and isinstance(info,str):
                    # 使用json将字符串解析为字典，提取hdr和zoom字段
                    data = json.loads(info)
                    hdr_value = data.get("Hdr", "Null")  
                    zoom_value = data.get("zoomMultiple", "Null")
                    # 拼接HDR等信息            
                    ultra_info = f"\nHDR: {hdr_value}\nZoom: {zoom_value}"
                
            return basic_info + ultra_info
        except Exception as e:
            return f"❌ [get_pic_basic_info]-->无法获取图片{os.path.basename(path)}的基础信息:\n报错信息: {e}"
    
    
    def get_exif_info(self, path, image_format):
        """
        函数功能： 使用piexif解析特定格式（"JPEG", "TIFF", "MPO"）图片的曝光时间、光圈、ISO等详细信息
        输入： path 图片文件路径, image_format图片文件的PIL_image 格式
        输出： exif_info 解析出来的详细信息（exif_tags_id）
        """
        try:
            # 检查文件格式
            
            if image_format not in ["JPEG", "TIFF", "MPO"]:
                return ""

            # 直接使用 piexif库加载exif信息
            exif_info = "" 
            if (exif_dict := piexif.load(path)) and "0th" in exif_dict:
                
                # 设置检索关键字; exif_dict["0th"]; 测光模式，需要单独处理
                exif_tags_id = {
                    "271": "品牌",  
                    "272": "型号",  
                    "33434": "曝光时间",
                    "33437": "光圈值",
                    "34855": "ISO值",
                    "36867": "原始时间",
                    "37383": "测光模式", 
                }
                
                # 测光模式映射
                metering_mode_mapping = {
                    0: "未知",
                    1: "平均测光",
                    2: "中央重点测光",
                    3: "点测光",
                    4: "多点测光",
                    5: "多区域测光",
                    6: "部分测光",
                    255: "其他"
                }
                # 存储解析exif_dict["Exif"]，exif_dict["0th"]得到的数据
                # 图像旋转信息 exif_dict["0th"][274]
                exif_info_list = []
                for tag_id, tag_cn in exif_tags_id.items():
                    
                    # 将字符串类型转换为整型, 首先根据标签id获取相应数据并解析成需要的数据形式
                    tag_id = int(tag_id) 

                    # 解析Exif
                    if tag_id in exif_dict["Exif"]:
                        value = exif_dict["Exif"][tag_id]
                        if value:
                            # 字节类型处理
                            if isinstance(value, bytes): 
                                value = value.decode('utf-8')
                            # 曝光时间处理
                            if tag_id == 33434: 
                                exp_s = (value[0]/value[1])*1000000
                                # 设置保留小数点后两位
                                exp_s = round(exp_s, 2)
                                exp_s = f"{exp_s}ms"
                                if value[0] == 1:
                                    value = f"{value[0]}/{value[1]}_({exp_s})"
                                else: # 处理曝光时间分子不为1的情况
                                    value = int(value[1]/value[0])
                                    value = f"1/{value}_({exp_s})"
                            # 光圈值处理
                            if tag_id == 33437: 
                                value = value[0]/value[1]
                                value = round(value, 2)
                            # 测光模式处理
                            if tag_id == 37383: 
                                value = metering_mode_mapping.get(value, "其他")
                            exif_info_list.append(f"{tag_cn}: {value}")

                    # 解析0th
                    elif tag_id in exif_dict["0th"]:
                        value = exif_dict["0th"][tag_id]
                        if value:
                            if isinstance(value, bytes):
                                value = value.decode('utf-8')
                            exif_info_list.append(f"{tag_cn}: {value}")
                        
                exif_info = "\n".join(exif_info_list)
            
            exif_info = exif_info + '\n' if exif_info else ""

            return exif_info
        except Exception as e:
            print(f"❌ [get_exif_info]-->error: 读取图片{os.path.basename(path)}EXIF信息发生错误:\n报错信息: {e}")
            return ""

    def wheelEvent(self, event: QEvent):
        """鼠标滚轮事件"""
        try:
            # 图片还在更新中，不触发鼠标滚轮事件
            if self.is_updating:
                print("[wheelEvent]-->图片还在更新中,请稍等...") 
                return

            # 确保视图中有值&存在基准缩放比例
            if not self.graphics_views or not self.base_scales:
                print("[wheelEvent]-->无效的视图或基准缩放比例")
                return

            # 确保 self._scales_min 中没有 None 值
            if None in self._scales_min:
                print("[wheelEvent]-->缩放最小值包含None，重新初始化")
                # 使用默认值替换None
                self._scales_min = [0.2 if x is None else x for x in self._scales_min]

            # 计算新的缩放因子
            zoom_step = 1.15 if event.angleDelta().y() > 0 else 0.9
            
            # 更新基准尺寸信息,并限制缩放范围（0.08<0.5*0.20>~130<800*0.20>）
            self.base_scales = [
                max(0.5 * self._scales_min[i], min(scale * zoom_step, 800 * self._scales_min[i])) 
                for i, scale in enumerate(self.base_scales) if scale is not None
            ]

            # 如果按下了Ctrl键，则仅缩放鼠标所在的视图,否则同步缩放所有视图
            if event.modifiers() & Qt.ControlModifier:
                # 仅缩放鼠标所在的视图
                pos = self.mapFromGlobal(event.globalPos())
                for i, view in enumerate(self.graphics_views):
                    if view and view.rect().contains(view.mapFromParent(pos)) and i < len(self.base_scales):
                        view_new = self._apply_scale_to_view(view, self.base_scales[i])
                        self.graphics_views[i] = view_new
                        break    
            else:
                # 同步缩放所有视图
                for i, view in enumerate(self.graphics_views):
                    if view and i < len(self.base_scales):
                        view_new = self._apply_scale_to_view(view, self.base_scales[i])
                        self.graphics_views[i] = view_new

        except Exception as e:
            print(f"❌ [wheelEvent]-->处理滚轮事件时发生错误: {e}")
      

    def _apply_scale_to_view(self, view, zoom_step):
        """应用缩放到指定视图"""
        try:
            if not view.pixmap_items:
                return

            # 获取当前视图中心
            center = view.mapToScene(view.viewport().rect().center())
            
            # 计算并应用新的变换
            new_transform = QTransform()
            
            # 设置新的变换矩阵
            new_transform.scale(zoom_step, zoom_step)
            
            # 应用变换
            view.setTransform(new_transform)
            
            # 保持视图中心
            view.centerOn(center)
            
        except Exception as e:
            print(f"❌ [_apply_scale_to_view]-->应用缩放时发生错误: {e}")
        finally:
            return view
        

    def toggle_fullscreen(self):
        """F11全屏快键键, 切换全屏"""
        self.is_fullscreen = not self.is_fullscreen
        try:
            if self.is_fullscreen:
                # 设置全屏，隐藏右上角组件
                self.showFullScreen()
                self.is_maxscreen = False
                self.is_norscreen = False  

                # 隐藏相关组件
                self.label_bottom.setVisible(False)
                for i in range(self.hl_top.count()):
                    item = self.hl_top.itemAt(i)
                    if item.widget():
                        item.widget().setVisible(False)
                
                
            else:
                # 退出全屏模式，恢复Normal常规尺寸显示
                self.showNormal()

                _, _, w, h = self.__get_screen_geometry()
                self.resize(int(w * 0.8), int(h * 0.70))

                x, y, _, _ = self.__get_screen_geometry()
                self.move(x, y)

                self.is_norscreen = True
                self.is_maxscreen = False
                self.is_fullscreen = False

                # 显示相关组件
                self.label_bottom.setVisible(True)
                for i in range(self.hl_top.count()):
                    item = self.hl_top.itemAt(i)
                    if item.widget():
                        item.widget().setVisible(True)

        except Exception as e:
            print(f"❌ [toggle_fullscreen]-->应用F11切换全屏时发生错误: {e}")



    def toggle_screen_display(self):
        """提供接口给设置界面使用, 切换屏幕各种尺寸显示功能"""
        try:
            if self.is_fullscreen:
                # 隐藏相关组件
                self.label_bottom.setVisible(False)
                for i in range(self.hl_top.count()):
                    item = self.hl_top.itemAt(i)
                    if item.widget():
                        item.widget().setVisible(False)
                # 设置全屏，隐藏右上角组件
                self.showFullScreen()  
                
            elif self.is_norscreen:
                # 退出全屏模式
                self.showNormal()

                # 手动设置看图界面尺寸同主界面；
                self.resize(int(self.parent_window.width()), int(self.parent_window.height()))

                # 显示相关组件
                self.label_bottom.setVisible(True)
                for i in range(self.hl_top.count()):
                    item = self.hl_top.itemAt(i)
                    if item.widget():
                        item.widget().setVisible(True)
                
            elif self.is_maxscreen:
                # 退出全屏模式，先恢复Normal再最大化，减少闪烁
                self.setUpdatesEnabled(False)  # 暂停界面刷新
                self.showMaximized()
                self.setUpdatesEnabled(True)   # 恢复界面刷新
                
                # 显示相关组件
                self.label_bottom.setVisible(True)
                for i in range(self.hl_top.count()):
                    item = self.hl_top.itemAt(i)
                    if item.widget():
                        item.widget().setVisible(True)
                
        except Exception as e:
            print(f"❌ [toggle_screen_display]-->应用屏幕显示切换时发生错误: {e}")

    def rotate_left(self):
        try:
            self.rotate_image(-90)
        except Exception as e:
            print(f"❌ [rotate_left]-->旋转图片时发生错误: {e}")

    def rotate_right(self):
        try:
            self.rotate_image(90)
        except Exception as e:
            print(f"❌ [rotate_right]-->旋转图片时发生错误: {e}")

    def rotate_image(self, angle):
        """旋转图片函数，接受角度进行旋转图片"""
        # 获取鼠标的全局位置
        cursor_pos = QCursor.pos()
        # 将全局位置转换为窗口内的位置
        pos = self.mapFromGlobal(cursor_pos)
        
        for i, view in enumerate(self.graphics_views):
            if view is None:
                continue
            
            # 将全局坐标转换为view的本地坐标
            local_pos = view.mapFromParent(pos)
            if view.rect().contains(local_pos):
                # 获取当前视图中的图片项
                pixmap_item = view.pixmap_items[0] if view.pixmap_items else None
                if pixmap_item:
                    # 获取当前图片的原始尺寸
                    original_rect = pixmap_item.boundingRect()
                    
                    # 保存当前变换状态
                    current_transform = pixmap_item.transform()
                    current_scale = current_transform.m11()
                    current_rotation = pixmap_item.rotation()
                    
                    # 设置新的旋转角度
                    new_rotation = current_rotation + angle
                    
                    # 重置变换
                    pixmap_item.setTransform(QTransform())
                    
                    # 设置旋转中心点
                    pixmap_item.setTransformOriginPoint(original_rect.center())
                    
                    # 应用新的旋转角度
                    pixmap_item.setRotation(new_rotation)
                    
                    # 重新应用缩放
                    pixmap_item.setScale(current_scale)

                    # 计算旋转后的边界
                    rotated_rect = pixmap_item.mapRectToScene(pixmap_item.boundingRect())
                    
                    # 更新场景边界
                    view.scene().setSceneRect(rotated_rect)
                    
                    # 确保图片保持在视图中心
                    view.centerOn(pixmap_item)

                    # 保存当前旋转角度
                    self.original_rotation[i] = pixmap_item.rotation()

                break


    def keyPressEvent(self, event):
        if event.isAutoRepeat():  # 忽略按键重复
            event.accept()
            return

        if event.key() == Qt.Key_Q:
            self.handle_overlay('q')
        elif event.key() == Qt.Key_W:
            self.handle_overlay('w')


    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            event.accept()
            return  # 忽略自动重复事件

        if event.key() == Qt.Key_Q:
            self.restore_images('q')
        elif event.key() == Qt.Key_W:
            self.restore_images('w')


    def handle_overlay(self, key):
        """按压的动作函数"""
        if len(self.images_path_list) != 2:
            QMessageBox.warning(self, "警告", "只有两张图片时才能使用覆盖比较功能。")
            return
        
        try:    
            def create_unified_overlay(source_view, target_view):
                """创建统一尺寸的覆盖图像(以目标项当前pixmap像素尺寸缩放)"""
                try:
                    source_pixmap_item = source_view.pixmap_items[0]
                    target_item = target_view.pixmap_items[0]
                    source_pixmap = source_pixmap_item.pixmap()
                    target_size_px = target_item.pixmap().size()
                    return source_pixmap.scaled(
                        target_size_px,
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation
                    )
                except Exception as e:
                    print(f"❌ [create_unified_overlay]-->创建统一覆盖图像失败: {str(e)}")
                    return None

            # 懒初始化覆盖图元数组
            if not hasattr(self, 'overlay_items'):
                self.overlay_items = [None, None]

            if key == 'q':
                source_index = 1
                target_index = 0
            elif key == 'w':
                source_index = 0
                target_index = 1
            else:
                return

            source_view = self.graphics_views[source_index]
            target_view = self.graphics_views[target_index]

            if not (source_view and target_view and source_view.pixmap_items and target_view.pixmap_items):
                return

            # 若已有覆盖，先清理
            if self.overlay_items[target_index] is not None:
                try:
                    target_view.scene().removeItem(self.overlay_items[target_index])
                except Exception:
                    pass
                self.overlay_items[target_index] = None

            # 创建覆盖pixmap并添加为临时图元
            scaled = create_unified_overlay(source_view, target_view)
            if scaled is None:
                return

            overlay_item = QGraphicsPixmapItem(scaled)
            overlay_item.setZValue(9999)
            # 变换中心设为图像中心
            overlay_item.setTransformOriginPoint(scaled.rect().center())

            # 对齐到目标项位置与旋转
            target_item = target_view.pixmap_items[0]
            overlay_item.setPos(target_item.pos())
            if source_index == 1:
                overlay_item.setRotation(self.original_rotation[1])
            else:
                overlay_item.setRotation(self.original_rotation[0])

            # 添加到场景并记录
            target_view.scene().addItem(overlay_item)
            self.overlay_items[target_index] = overlay_item

        except Exception as e:
            print(f"❌ [handle_overlay]-->覆盖操作失败: {e}")
            

    def restore_images(self, key):
        """释放动作的函数"""
        if len(self.images_path_list) != 2:
            return

        try:
            if key == 'q':
                target_index = 0
            elif key == 'w':
                target_index = 1
            else:
                return

            if not hasattr(self, 'overlay_items'):
                return

            target_view = self.graphics_views[target_index]
            if not target_view:
                return

            # 仅移除覆盖图元，不修改原图元
            overlay = self.overlay_items[target_index]
            if overlay is not None:
                try:
                    target_view.scene().removeItem(overlay)
                except Exception:
                    pass
                self.overlay_items[target_index] = None
        except Exception as e:
            print(f"❌ [restore_images]-->恢复图片失败: {e}")

            
    def on_v_pressed(self):
        """处理V键事件"""
        print("[on_v_pressed]-->按下了v键")

        if False:                            
            # 打印表格的实际尺寸
            table_width = self.tableWidget_medium.width()
            table_height = self.tableWidget_medium.height()
            table_columns = self.tableWidget_medium.columnCount()
            target_width = table_width/table_columns
            target_height = table_height/table_columns
            print(f"表格的实际尺寸: {table_width}x{table_height}，列数: {table_columns}")  # 添加调试信息

        try:
            # 设置缩放因子为0.995
            zoom_step = 0.995
            # 更新基准尺寸信息,并限制缩放范围（0.08<0.5*0.16>~130<800*0.16>） 使用self._scales_min限制是由于适应不同尺寸的图片
            self.base_scales = [max(0.5*self._scales_min[i], min(scale * zoom_step, 800*self._scales_min[i])) for i, scale in enumerate(self.base_scales)]

            # 应用缩放到所有视图
            for i, view in enumerate(self.graphics_views):
                if view:
                    self._apply_scale_to_view(view, self.base_scales[i])
            # print(f"新的缩放因子: {self.base_scales}")  # 添加调试信息

        except Exception as e:
            print(f"❌ [on_v_pressed]-->处理V键事件时发生错误: {e}")


    def on_n_pressed(self):
        """处理N键事件"""
        print("[on_n_pressed]-->按下了n键")

        try:
            # 设置放大因子为1.005
            zoom_step = 1.005
            # 更新基准尺寸信息,并限制缩放范围（0.08<0.5*0.16>~130<800*0.16>） 使用self._scales_min限制是由于适应不同尺寸的图片
            self.base_scales = [max(0.5*self._scales_min[i], min(scale * zoom_step, 800*self._scales_min[i])) for i, scale in enumerate(self.base_scales)]

            # 应用缩放到所有视图
            for i, view in enumerate(self.graphics_views):
                if view:
                    self._apply_scale_to_view(view, self.base_scales[i])
            
            # print(f"新的缩放因子: {self.base_scales}")  # 添加调试信息
        except Exception as e:
            print(f"❌ [on_n_pressed]-->处理N键事件时发生错误: {e}")

    def on_t_pressed(self):
        """处理T键事件"""
        print("[on_t_pressed]-->按下了t键,创建并显示自定义问题点对话框")

        try:
            # 创建并显示自定义问题点对话框,传入图片列表和父窗口
            dialog = ProblemsDialog(self.images_path_list, self)

            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 写入问题点到表格中
                dialog.write_data()
                # data = dialog.get_data()
                # print(f"用户输入的文字信息: {data}")
            
            # 无论对话框是接受还是取消，都手动销毁对话框
            dialog.deleteLater()
            dialog = None
        except Exception as e:
            print(f"❌ [on_ctrl_t_pressed]-->处理Ctrl+T键事件失败:{e}")

    def on_ctrl_t_pressed(self):
        """处理Ctrl+T键事件"""
        print("[on_ctrl_t_pressed]-->按下了ctrl+t键,调用截屏工具")
        try:
            WScreenshot.run()
        except Exception as e:
            print(f"❌ [on_ctrl_t_pressed]-->处理Ctrl+T键事件失败:{e}")


    def on_p_pressed(self):  ## 会导致窗口闪退，当前策略是使用标志位self.is_updating锁定界面不退出
        """处理P键事件"""
        self.is_updating = True
        
        if self.ai_tips_flag:
            try:
                # 检查图片数量
                if len(self.images_path_list) != 2:
                    show_message_box("当前AI提示支持两张图比较，请选择两张图片进行比较！", "提示", 1000)
                    # 延时1秒后更新is_updatng为False
                    QTimer.singleShot(1000, lambda: setattr(self, 'is_updating', False))
                    return

                # 调用AI提示函数
                show_message_box("按下了p键,正在发起ai请求...", "提示", 500)
                # 更新底部信息提示栏
                self.label_bottom.setText(f"📢:按下了p键,正在发起ai请求...")

                def run_ai():
                    try:
                        llm = CustomLLM_Siliconflow()
                        tips = """假如你是一名专业的影像画质评测工程师,
                        请从亮度、对比度、清晰度、色调等专业角度比较两张图片差异, 用中文回复,
                        一句话总结概括内容, 不要换行，不要超过100字。"""
                        model = "Pro/OpenGVLab/InternVL2-8B"
                        response = llm(select_model=model, prompt=tips, image_path_list=self.images_path_list)
                        # 使用信号机制更新UI，避免跨线程直接操作UI
                        self.ai_response_signal.emit(response)
                    except Exception as e:
                        print(f"AI请求失败: {e}")
                        self.ai_response_signal.emit("AI请求失败，请检查网络连接或模型配置")
                        # 更新底部信息提示栏
                        self.label_bottom.setText(f"📢:AI请求失败，请检查网络连接或模型配置")

                # 创建并启动子线程
                tcp_thread = threading.Thread(target=run_ai)
                tcp_thread.daemon = True
                tcp_thread.start()

            except Exception as e:
                print(f"❌ [on_p_pressed]-->处理P键时发生错误: {e}")
                self.is_updating = False
                show_message_box("处理P键时发生错误，请重试", "错误", 1000)
        
        elif self.stats_visible:
            try:
                # 设置 P 键来打开ROI信息统计框
                self.roi_selection_active = not self.roi_selection_active
                for view in self.graphics_views:
                    if view:
                        view.toggle_selection_rect(self.roi_selection_active)

            except Exception as e:
                print(f"❌ [on_p_pressed]-->显示图片统计信息时发生错误: {e}")
            finally:
                # 延时0.01秒后更新is_updating为False
                QTimer.singleShot(10, lambda: setattr(self, 'is_updating', False))
        else:
            # 没有标志位的情况下按 P键不显示
            show_message_box("请勾选 ROI信息复选框 或者 AI提示看图复选框后, \n按P键发出相应请求!", "提示",1500)
            # 延时0.01秒后更新is_updating为False
            QTimer.singleShot(10, lambda: setattr(self, 'is_updating', False))
            pass

    def on_space_pressed(self):
        """处理看图子界面空格键事件"""
        try:
            # 预检查当前状态
            if self.is_updating:
                print("[on_space_pressed]-->正在更新图片，请稍后...")
                return
            if not self.parent_window:
                print("[on_space_pressed]-->未找到父窗口，无法获取下一组图片")
                return
            # 切换图片自动清除ROI信息框
            if self.roi_selection_active: 
                self.roi_selection_active = False

            # 设置更新标志
            self.is_updating = True
            # 开始获取下一组文件
            next_images, next_indexs = self.get_next_images()
            if not next_images:
                raise ValueError(f"无效获下一组文件")
            
            # 获取所有文件的扩展名并去重，判断这一组文件的格式，纯图片，纯视频，图片+视频
            is_video, is_image = False, False
            file_extensions = {os.path.splitext(path)[1].lower() for path in next_images}
            if not file_extensions:
                raise ValueError(f"无效的扩展名")
            for file_extension in list(file_extensions):
                if file_extension.endswith(self.parent_window.VIDEO_FORMATS):
                    is_video = True
                if file_extension.endswith(self.parent_window.IMAGE_FORMATS):
                    is_image = True

            # 根据当前组文件的格式选择调用子界面
            if is_image and not is_video:   # 调用图片显示
                # 先更新表格尺寸后再调用图片显示
                self.table_width_heigth_default = [self.tableWidget_medium.width(), self.tableWidget_medium.height()]
                self.set_images(next_images, next_indexs)
                
            elif is_video and not is_image: # 调用视频显示
                self.parent_window.create_video_player(next_images, next_indexs)   
                raise ValueError(f"看图子界面调用视频子界面，主动抛出异常关闭当前看图子界面")             
            elif is_image and is_video:
                # 提示信息框
                show_message_box("🔉: 这组文件同时包含图片和视频文件，无法调出子界面，返回主界面", "提示",1500)
                # 抛出异常，退出当前子界面
                raise ValueError(f"这组文件同时包含图片和视频文件，无法调出子界面，获取的文件如下：\n{next_images}")
            else:
                # 提示信息框
                show_message_box("🔉: 这组文件没有包含图片和视频文件，无法调出子界面，返回主界面", "提示",1500)
                # 抛出异常，退出当前子界面
                raise ValueError(f"这组文件没有包含图片和视频文件，无法调出子界面，获取的文件如下：\n{next_images}")

        except Exception as e:
            print(f"❌ [on_space_pressed]-->处理空格键时发生错误: {e}")
            # 退出看图界面
            self.is_updating = False
            self.Escape_close()
            
    def on_b_pressed(self):
        """处理B键事件"""
        try:
            # 预检查当前状态
            if self.is_updating:
                print("[on_b_pressed]-->正在更新图片，请稍后...")
                return
            if not self.parent_window:
                print("[on_b_pressed]-->未找到父窗口，无法获取下一组图片")
                return
            # 切换图片自动清除ROI信息框
            if self.roi_selection_active: 
                self.roi_selection_active = False

            # 设置更新标志
            self.is_updating = True
            # 开始获取上一组文件
            prev_images, prev_indexs = self.get_prev_images()
            if not prev_images:
                raise ValueError(f"无法获取上一组图片")
            
            # 获取所有文件的扩展名并去重，判断这一组文件的格式，纯图片，纯视频，图片+视频
            is_image, is_video = False, False
            file_extensions = {os.path.splitext(path)[1].lower() for path in prev_images}
            if not file_extensions:
                raise ValueError(f"无效的扩展名")
            for file_extension in list(file_extensions):
                if file_extension.endswith(self.parent_window.VIDEO_FORMATS):
                    is_video = True
                if file_extension.endswith(self.parent_window.IMAGE_FORMATS):
                    is_image = True

            # 根据当前组文件的格式选择调用子界面
            if is_image and not is_video:   # 调用图片显示
                # 先更新表格尺寸后再调用图片显示
                self.table_width_heigth_default = [self.tableWidget_medium.width(), self.tableWidget_medium.height()]
                self.set_images(prev_images, prev_indexs)
            elif is_video and not is_image: # 调用视频显示
                self.parent_window.create_video_player(prev_images, prev_indexs)   
                raise ValueError(f"看图子界面调用视频子界面，主动抛出异常关闭当前看图子界面")             
            elif is_image and is_video:
                # 提示信息框
                show_message_box("🔉: 这组文件同时包含图片和视频文件，无法调出子界面，返回主界面", "提示",1500)
                # 抛出异常，退出当前子界面
                raise ValueError(f"这组文件同时包含图片和视频文件，无法调出子界面，获取的文件如下：\n{prev_images}")
            else:
                # 提示信息框
                show_message_box("🔉: 这组文件没有包含图片和视频文件，无法调出子界面，返回主界面", "提示",1500)
                # 抛出异常，退出当前子界面
                raise ValueError(f"这组文件没有包含图片和视频文件，无法调出子界面，获取的文件如下：\n{prev_images}")

        except Exception as e:
            print(f"❌ [on_b_pressed]-->处理B键时发生错误: {e}")
            self.is_updating = False
            self.Escape_close()
            
    
    def get_next_images(self):
        """获取下一组图片"""
        try:
            if self.parent_window:
                next_images, next_indexs = self.parent_window.press_space_or_b_get_selected_file_list('space')
                if next_images and isinstance(next_images, list) and len(next_images) > 0:
                    return next_images, next_indexs
                else:
                    print("[get_next_images]-->获取到的下一组图片无效")
                    return None, None
        except Exception as e:
            print(f"❌ [get_next_images]-->获取下一组图片时发生错误: {e}")
            return None, None
        return None, None
    
    def get_prev_images(self):
        """获取上一组图片"""
        try:
            if self.parent_window:
                prev_images, prev_indexs = self.parent_window.press_space_or_b_get_selected_file_list('b')
                if prev_images and isinstance(prev_images, list) and len(prev_images) > 0:
                    return prev_images, prev_indexs
                else:
                    print("[get_prev_images]-->获取到的上一组图片无效")
                    return None, None
        except Exception as e:
            print(f"❌ [get_prev_images]-->获取上一组图片时发生错误: {e}")
            return None, None
        return None, None

    def closeEvent(self, event):
        """重写关闭事件处理"""
        # 检查是否应该忽略关闭事件
        print("[closeEvent]-->看图子界面-->触发窗口关闭事件")
        if self.is_updating:
            print("⭕[closeEvent]-->看图子界面-->warning: 看图子界面正在更新图片，忽略关闭事件")
            event.ignore()
            return
        try:
            self.save_settings()         # 保存设置
            self.setting_window_closed() # 关闭设置子窗口
            self.cleanup()               # 清理资源
            self.closed.emit()           # 发送关闭信号
            self.closed.disconnect()     # 发送后立即断开连接
            event.accept()               # 只调用一次 accept
        except Exception as e:
            print(f"❌[closeEvent]-->看图子界面-->关闭时发生错误: {e}")
            event.accept()               # 即使出错也接受关闭事件

    def Escape_close(self):
        """统一处理窗口关闭逻辑"""
        try:
            if self.is_updating:
                print("⭕[Escape_close]-->看图子界面-->warning: 正在更新图片，忽略关闭请求")
                return
            super().close()     # 调用父类的close方法
        except Exception as e:
            print(f"❌[Escape_close]-->看图子界面-->warning: 关闭窗口时发生错误: {e}")
            super().close()


    def load_settings(self):
        """加载颜色、exif等设置"""
        try:
            # 加载保存的颜色设置 basic_color_settings、basic_color_settings
            ColorSettings = load_color_settings()
            color_settings = ColorSettings.get("basic_color_settings",{})
            rgb_settings = ColorSettings.get("rgb_color_settings",{})
            # 加载保存的EXIF信息设置
            ExifSettings = load_exif_settings()
            label_visable = ExifSettings.get("label_visable_settings",{})   # label具体项显示的标志位
            exif_visable = ExifSettings.get("exif_visable_setting",{})      # exif具体项显示的标志位

            # 从颜色配置中读取基础颜色
            self.font_color_default = color_settings.get("font_color_default", "rgb(0,0,0)")                  # 默认字体颜色_纯黑色
            self.font_color_exif = color_settings.get("font_color_exif", "rgb(255,255,255)")                  # Exif字体颜色_纯白色
            self.background_color_default = color_settings.get("background_color_default", "rgb(173,216,230)")  # 深色背景色_好蓝
            self.background_color_table = color_settings.get("background_color_table", "rgb(127,127,127)")    # 表格背景色_18度灰

            # 读取rgb颜色配置
            self.color_rgb_settings = rgb_settings
            # 初始化exif信息可见性字典，支持用户在json配置文件中调整顺序以及是否显示该项
            self.dict_exif_info_visibility = exif_visable

            # 初始化label显示字典，并初始化相关变量
            self.dict_label_info_visibility = label_visable
            # 读取图像颜色空间显示设置, 默认选择auto档
            self.p3_color_space = self.dict_label_info_visibility.get("p3_color_space", False)     
            self.gray_color_space = self.dict_label_info_visibility.get("gray_color_space", False) 
            self.srgb_color_space = self.dict_label_info_visibility.get("srgb_color_space", False) 
            self.auto_color_space = self.dict_label_info_visibility.get("auto_color_space", True) 
            # 读取看图界面显示尺寸设置, 默认选择显示最大化尺寸
            self.is_fullscreen = self.dict_label_info_visibility.get("is_fullscreen", False)     
            self.is_norscreen = self.dict_label_info_visibility.get("is_norscreen", False) 
            self.is_maxscreen = self.dict_label_info_visibility.get("is_maxscreen", True) 
            # 设置亮度统计信息的标志位；初始化ai提示标注位为False 
            self.stats_visible = self.dict_label_info_visibility.get("roi_info", False)         
            self.ai_tips_flag = self.dict_label_info_visibility.get("ai_tips", False)  
            # 读取标题显示开关, 默认选择开启
            self.is_title_on = self.dict_label_info_visibility.get("is_title_on", True)
                 

        except Exception as e:
            print(f"❌[load_settings]-->error: 加载设置失败: {e}")
        

    def save_settings(self):
        """
        该函数主要是实现保存颜色设置, exif设置到配置文件的功能.
        
        """
        try:
            # 确保config目录存在
            config_dir = Path("./config")
            config_dir.mkdir(parents=True, exist_ok=True)

            # 1. 保存颜色配置文件
            settings_color_file = config_dir / "color_setting.json"
            basic_color_settings ={
                "background_color_default": self.background_color_default,
                "background_color_table": self.background_color_table,
                "font_color_default": self.font_color_default,
                "font_color_exif": self.font_color_exif,
            }
            setting = {
                "basic_color_settings": basic_color_settings,
                "rgb_color_settings": self.color_rgb_settings   # 默认使用配置中读取的配置
            }
            # 保存setting到配置文件config_dir / "color_setting.json"
            with open(settings_color_file, 'w', encoding='utf-8', errors='ignore') as f:
                json.dump(setting, f, indent=4, ensure_ascii=False)

            # 2. 保存exif配置文件
            settings_exif_file = config_dir / "exif_setting.json"
            label_visable_settings = {
                # label显示相关
                "histogram_info": self.checkBox_1.isChecked(),
                "exif_info": self.checkBox_2.isChecked(),
                "roi_info": self.checkBox_3.isChecked(),
                "ai_tips": self.checkBox_4.isChecked(),

                # 色彩空间相关
                "auto_color_space":self.auto_color_space,
                "srgb_color_space":self.srgb_color_space,
                "p3_color_space":self.p3_color_space,
                "gray_color_space":self.gray_color_space,

                # 屏幕显示尺寸相关
                "is_fullscreen":self.is_fullscreen,
                "is_norscreen":self.is_norscreen,
                "is_maxscreen":self.is_maxscreen,

                # 标题显示开关
                "is_title_on":self.is_title_on,
                

            }
            setting = {
                "label_visable_settings": label_visable_settings,
                "exif_visable_setting": self.dict_exif_info_visibility  # 默认使用配置中读取的配置
            }
            # 保存setting到配置文件config_dir / "exif_setting.json"
            with open(settings_exif_file, 'w', encoding='utf-8', errors='ignore') as f:
                json.dump(setting, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"❌[save_settings]-->error: 保存设置失败: {e}")


    def update_ai_response(self, response):
        """更新AI响应结果"""
        self.label_bottom.setText(f"📢:AI提示结果:{response}")
        # 延时1秒后更新is_updating为False
        QTimer.singleShot(1000, lambda: setattr(self, 'is_updating', False))

    def __get_screen_geometry(self)->tuple:
        """
        该函数主要是实现了获取当前鼠标所在屏幕的几何信息的功能.
        Args:
            self (object): 当前对象
        Returns:
            x (int): 当前屏幕中心的x坐标
            y (int): 当前屏幕中心的y坐标
            w (int): 当前屏幕的宽度
            h (int): 当前屏幕的高度
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
            print(f"❌[__get_screen_geometry]-->error: 获取屏幕几何信息失败: {e}")
            return 0, 0, 0, 0



"""
设置看图界面类区域结束线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""


"""
设置看图界面功能测试区域开始线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

one_pic = ['D:/Tuning/M5151/0_picture/20241209_FT/1209-C3N后置GL四供第三轮FT（小米园区）/photo\\四供\\四供_IMG_20241209_081113.jpg']
two_pic = ['D:/Tuning/M5151/0_picture/20241209_FT/1209-C3N后置GL四供第三轮FT（小米园区）/photo\\四供\\四供_IMG_20241209_081126.jpg', 'D:/Tuning/M5151/0_picture/20241209_FT/1209-C3N后置GL四供第三轮FT（小米园区）/photo\\四供\\四供_IMG_20241209_081300.jpg']
three_pic = ['D:/Tuning/M5151/0_picture/20241209_FT/1209-C3N后置GL四供第三轮FT（小米园区）/photo\\四供\\四供_IMG_20241209_081113.jpg', 'D:/Tuning/M5151/0_picture/20241209_FT/1209-C3N后置GL四供第三轮FT（小米园区）/photo\\四供\\四供_IMG_20241209_081124.jpg', 'D:/Tuning/M5151/0_picture/20241209_FT/1209-C3N后置GL四供第三轮FT（小米园区）/photo\\四供\\四供_IMG_20241209_081126.jpg']
two_pics = ['D:/Tuning/M5151/0_picture/20241224_FT/1224_第四轮FT问题截图（米家+小米园区）\\Photo\\10、小米之家 ISO 53，AWB 略偏黄绿.png', 'D:/Tuning/M5151/0_picture/20241224_FT/1224_第四轮FT问题截图（米家+小米园区）\\Photo\\111、小米园区 ISO 50,AWB 偏黄，ISP 涂抹重，细节清晰度不佳.png']
two_index = ['1/1', '1/1']



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SubMainWindow(two_pic, two_index)
    # 不需要额外的 show() 调用，因为在初始化时已经调用了 showMaximized()
    sys.exit(app.exec_())

"""
设置看图界面功能测试区域结束线
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""