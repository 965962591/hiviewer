# -*- coding: utf-8 -*-
import time
import logging
from pathlib import Path

# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    # 设置视频首帧图缓存路径
    BASEICONPATH = Path(__file__).parent.parent.parent
    

"""设置自定义的装饰器"""


# 自定义的装饰器，用于计算函数执行时间
def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__}()--耗时: {(end_time - start_time):.6f} 秒")
        return result
    return wrapper


# 自定义的装饰器，用于记录日志
def log_decorator(func):
    def wrapper(*args, **kwargs):
        logging.info(f"{func.__name__}()--开始执行, with arguments {args} and {kwargs}")
        result = func(*args, **kwargs)
        logging.info(f"{func.__name__}()--执行结束, returned {result}")
        return result
    return wrapper


@timing_decorator
@log_decorator
def compute_sum(n):
    return sum(range(n))

# 配置日志
logging.basicConfig(level=logging.INFO)
compute_sum(1000000)

