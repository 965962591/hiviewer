# -*- coding: utf-8 -*-
import os
import sys
import time

# 导入自定义装饰器
from src.utils.decorator import CC_TimeDec



"""设置根目录"""
# 通过当前py文件来定位项目主入口路径，向上找两层父文件夹
if True:
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 通过主函数hiviewer.py文件来定位项目主入口路径
if False:
    BASE_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
    

@CC_TimeDec(tips="读取版本号")
def version_init(VERSION="release-v2.3.2"):
    """从配置文件中读取当前软件版本号"""
    _start_time = time.time()
    default_version_path = os.path.join(BASE_PATH, "config", "version.ini")
    try:
        # 检查文件是否存在，如果不存在则创建并写入默认版本号
        if not os.path.exists(default_version_path):
            # 确保cache目录存在
            os.makedirs(os.path.dirname(default_version_path), exist_ok=True)
            with open(default_version_path, 'w', encoding='utf-8') as f:
                f.write(VERSION)
            print(f"[version_init]-->找不到文件{default_version_path}，写入版本号{VERSION}, 耗时: {(time.time()-_start_time):.2f} 秒")
            return VERSION
        else:
            with open(default_version_path, 'r', encoding='utf-8') as f:
                VERSION = f.read().strip()
                return VERSION
    except Exception as e:
        print(f"[version_init]-->读取版本号失败: {str(e)}\n使用默认版本号{VERSION}")
        return VERSION