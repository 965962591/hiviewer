# -*- coding: utf-8 -*-
import os
import shutil
import stat
import ctypes
import logging
from pathlib import Path

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

def force_delete_folder(folder_path, suffix='.zip'):
    """强制删除文件夹内指定后缀文件"""
    try:
        for file in os.listdir(folder_path):
            if file.endswith(suffix):
                force_delete_file(os.path.join(folder_path, file))
    except Exception as e:
        print(f"强制删除文件夹失败: {e}")  


def force_delete_directory(folder_path):
    """强制删除指定文件夹及其所有内容"""
    try:
        if not os.path.exists(folder_path):
            print(f"[force_delete_directory]-->强制删除文件夹--目标不存在: {folder_path}")
            return True

        def _on_rm_error(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception as inner_e:
                print(f"[force_delete_directory]-->强制删除文件夹--处理失败 {path}: {inner_e}")

        shutil.rmtree(folder_path, onerror=_on_rm_error)
        print(f"[force_delete_directory]-->强制删除文件夹--完成: {folder_path}")
        return True
    except Exception as e:
        print(f"[force_delete_directory]-->强制删除文件夹失败: {e}")
        return False


def close_log_handlers():
    """关闭所有活动的日志处理器"""
    try:
        # 获取根日志记录器
        root_logger = logging.getLogger()
        
        # 关闭并移除所有处理器
        for handler in root_logger.handlers[:]:  # 使用切片创建副本，避免在迭代时修改列表
            try:
                handler.close()
                root_logger.removeHandler(handler)
                print(f"[close_log_handlers]--已关闭日志处理器: {type(handler).__name__}")
            except Exception as e:
                print(f"[close_log_handlers]--关闭日志处理器失败: {e}")
        
        # 也检查主日志记录器
        main_logger = logging.getLogger('hiviewer')
        for handler in main_logger.handlers[:]:
            try:
                handler.close()
                main_logger.removeHandler(handler)
                print(f"[close_log_handlers]--已关闭主日志处理器: {type(handler).__name__}")
            except Exception as e:
                print(f"[close_log_handlers]--关闭主日志处理器失败: {e}")
                
    except Exception as e:
        print(f"[close_log_handlers]--关闭日志处理器时出错: {e}")


def clear_log_files(base_path=None):
    """清除所有日志文件
    
    Args:
        base_path: 项目根目录路径，如果为None则自动检测
    """
    try:
        # 自动检测项目根目录
        if base_path is None: 
            base_path = Path(__file__).parent.parent.parent
        log_dir = os.path.join(base_path, "cache", "logs")
        if not os.path.exists(log_dir):
            print("[clear_log_files]--日志目录不存在")
            return False
        
        # 首先关闭所有活动的日志处理器
        close_log_handlers()
            
        # 删除日志相关文件    
        deleted_count = 0
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                try:
                    force_delete_file(file_path)
                    print(f"[clear_log_files]--已删除日志文件: {file}")
                    deleted_count += 1
                except Exception as e:
                    print(f"[clear_log_files]--删除日志文件失败 {file}: {e}")
        
        print(f"[clear_log_files]--日志文件清理完成，共删除 {deleted_count} 个文件")
        return True
        
    except Exception as e:
        print(f"[clear_log_files]--清除日志文件失败: {e}")
        return False


def clear_cache_files(base_path=None, file_types=None):
    """清除缓存文件
    
    Args:
        base_path: 项目根目录路径，如果为None则自动检测
        file_types: 要删除的文件类型列表，默认为['.zip']，不包含.log文件
    """
    try:
        if base_path is None:
            # 自动检测项目根目录
            import sys
            from pathlib import Path
            base_path = Path(__file__).parent.parent.parent
        
        if file_types is None:
            file_types = ['.zip']  # 默认不包含.log文件，避免与clear_log_files重复
            
        cache_dir = os.path.join(base_path, "cache")
        
        if not os.path.exists(cache_dir):
            print("[clear_cache_files]--缓存目录不存在")
            return False
            
        deleted_count = 0
        # 遍历缓存目录及其子目录
        for root, dirs, files in os.walk(cache_dir):
            for file in files:
                if any(file.endswith(ft) for ft in file_types):
                    file_path = os.path.join(root, file)
                    try:
                        force_delete_file(file_path)
                        print(f"[clear_cache_files]--已删除缓存文件: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"[clear_cache_files]--删除缓存文件失败 {file}: {e}")
        
        print(f"[clear_cache_files]--缓存文件清理完成，共删除 {deleted_count} 个文件")
        return True
        
    except Exception as e:
        print(f"[clear_cache_files]--清除缓存文件失败: {e}")
        return False