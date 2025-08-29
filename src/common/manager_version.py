# -*- coding: utf-8 -*-
import time
from pathlib import Path
from src.common.decorator import CC_TimeDec, log_performance_decorator      # 导入自定义装饰器函数 

@CC_TimeDec(tips="读取版本号")
@log_performance_decorator(tips="读取版本号", log_args=False, log_result=False)
def version_init(VERSION="release-v2.3.2"):
    """从配置文件中读取当前软件版本号"""
    _start_time = time.time()
    BASE_PATH = Path(__file__).parent.parent.parent
    default_version_path = BASE_PATH / "config" / "version.ini"
    try:
        # 检查文件是否存在，如果不存在则创建并写入默认版本号
        if not default_version_path.exists():
            # 确保cache目录存在
            default_version_path.parent.mkdir(parents=True, exist_ok=True)
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

@CC_TimeDec(tips="读取fast api地址端口")
@log_performance_decorator(tips="读取fast api地址端口", log_args=False, log_result=False)
def fastapi_init(FASTAPI="[API]\nhost = 127.0.0.1\nport = 8000"):
    """从配置文件中读取Fast API的地址端口"""
    BASE_PATH = Path(__file__).parent.parent.parent
    default_version_path = BASE_PATH / "config" / "ipconfig.ini"
    try:
        host = "127.0.0.1"
        port = "8000"
        # 检查文件是否存在，如果不存在则创建并写入默认版本号
        if not default_version_path.exists():
            default_version_path.parent.mkdir(parents=True, exist_ok=True)
            with open(default_version_path, 'w', encoding='utf-8') as f:
                f.write(FASTAPI)
            print(f"[version_init]-->找不到文件{default_version_path},写入FastApi-->{host}:{port}")
        else:
            with open(default_version_path, 'r', encoding='utf-8') as f: 
                FASTAPI = f.read().strip()
                # 使用正则表达式获取host和port
                import re
                host_match = re.search(r'host\s*=\s*([^\n]+)', FASTAPI)
                port_match = re.search(r'port\s*=\s*([^\n]+)', FASTAPI)
                host = host_match.group(1).strip() if host_match else host
                port = port_match.group(1).strip() if port_match else port
        return host, port
    except Exception as e:
        print(f"[version_init]-->读取版本号失败: {str(e)}\n使用默认地址-->{host}:{port}")
        return host, port