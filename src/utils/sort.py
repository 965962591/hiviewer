# -*- coding: utf-8 -*-
import re
from pathlib import Path

# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    # 设置视频首帧图缓存路径
    BASEICONPATH = Path(__file__).parent.parent.parent
    


def natural_sort_key(s):
    """将字符串转换为自然排序的键值（优化版）"""
    # 预编译正则表达式，提高效率（针对实现类似widow的文件排名）
    _natural_sort_re = re.compile('([0-9]+)')
    return [int(text) if text.isdigit() else text.lower() for text in _natural_sort_re.split(s)]


def sort_by_custom(sort_option, files_and_dirs_with_mtime,simple_mode,selected_option):
    """根据自定义键值对文件列表进行排序"""

    # 升排序
    if sort_option == "按文件名称排序":  # 按文件名称排序，reverse=False 表示升序，即最小的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: natural_sort_key(x[0]), reverse=False)
    elif sort_option == "按创建时间排序":  # 按创建时间排序，reverse=False 表示升序，即最小的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[1], reverse=False)
    elif sort_option == "按修改时间排序":  # 按修改时间排序，reverse=False 表示升序，即最小的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[2], reverse=False)
    elif sort_option == "按文件大小排序":  # 按文件大小排序，reverse=False 表示升序，即最小的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[3], reverse=False)
    
    # 降排序
    elif sort_option == "按文件名称逆序排序":  # 按文件名称排序，reverse=True 表示降序，即最大的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: natural_sort_key(x[0]), reverse=True) 
    elif sort_option == "按创建时间逆序排序":  # 按创建时间排序，reverse=True 表示降序，即最大的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[1], reverse=True)
    elif sort_option == "按修改时间逆序排序":  # 按修改时间排序，reverse=True 表示降序，即最大的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[2], reverse=True)
    elif sort_option == "按文件大小逆序排序":  # 按文件大小排序，reverse=True 表示降序，即最大的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[3], reverse=True)

    # 极简模式下不使能曝光、ISO排序选项
    elif not simple_mode and sort_option == "按曝光时间排序" and selected_option == "显示图片文件":  # 按曝光时间排序，reverse=False 表示升序，即最小的在前面
        # 排序中若存在None,则提供默认值0  
        files_and_dirs_with_mtime.sort(key=lambda x: int(x[5].split('/')[1]) if x[5] is not None else 0, reverse=False)
    elif not simple_mode and sort_option == "按曝光时间逆序排序" and selected_option == "显示图片文件":  # 按曝光时间排序，reverse=True 表示降序，即最大的在前面
        # 排序中若存在None,则提供默认值0  
        files_and_dirs_with_mtime.sort(key=lambda x: int(x[5].split('/')[1]) if x[5] is not None else 0, reverse=True)
    elif not simple_mode and sort_option == "按ISO排序" and selected_option == "显示图片文件":  # 按ISO排序，reverse=False 表示升序，即最小的在前面
        # 排序中若存在None,则提供默认值0  
        files_and_dirs_with_mtime.sort(key=lambda x: x[6], reverse=False)
    elif not simple_mode and sort_option == "按ISO逆序排序" and selected_option == "显示图片文件":  # 按ISO排序，reverse=True 表示降序，即最大的在前面
        # 排序中若存在None,则提供默认值0  
        files_and_dirs_with_mtime.sort(key=lambda x: x[6], reverse=True) 
    else:  # 默认文件名称排序，reverse=False 表示升序，即最小的在前面
        files_and_dirs_with_mtime.sort(key=lambda x: x[0], reverse=False)

    return files_and_dirs_with_mtime




