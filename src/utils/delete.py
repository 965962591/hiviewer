# -*- coding: utf-8 -*-
import os
import ctypes

def force_delete_folder(folder_path, suffix='.zip'):
    """强制删除文件夹内指定后缀文件"""
    try:
        for file in os.listdir(folder_path):
            if file.endswith(suffix):
                force_delete_file(os.path.join(folder_path, file))
    except Exception as e:
        print(f"强制删除文件夹失败: {e}")  


def force_delete_file(file_path):
    """强制删除指定文件"""
    try:
        os.remove(file_path)
    except PermissionError:
        # 如果文件被占用，尝试强制删除
        try:
            # 使用Windows API强制删除文件
            ctypes.windll.kernel32.DeleteFileW(file_path)
        except Exception as e:
            print(f"强制删除文件失败: {e}")