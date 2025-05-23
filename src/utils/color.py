# -*- coding: utf-8 -*-
from PyQt5.QtGui import QColor

def rgb_str_to_qcolor(rgb_str):
    """将 'rgb(r,g,b)' 格式的字符串转换为 QColor"""
    # 提取RGB值
    rgb = rgb_str.strip('rgb()')  # 移除 'rgb()' 
    r, g, b = map(int, rgb.split(','))  # 分割并转换为整数
    return QColor(r, g, b)