#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File         :decorator.py
@Time         :2025/05/28 13:52:20
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :装饰器的常规使用


*args 和 **kwargs这两个特殊语法的用处
*args: 用于接收任意数量的位置参数,存储为元组。exp:
def func(*args):    
    print(args)

func(1, 2, 3) # 输出: (1, 2, 3)

**kwargs: 用于接收任意数量的关键字参数, 存储为字典。
exp:
def func(**kwargs):
    print(kwargs)

func(a=1, b=2, c=3) # 输出: {'a': 1, 'b': 2, 'c': 3}


实际应用:

1.解包:
*args: 将元组中的元素解包为位置参数。
**kwargs: 将字典中的键值对解包为关键字参数。
# exp:
def func(a, b):
    return a + b

# 解包元组:
args = (1, 2)
func(*args) # 输出: 3

# 解包字典:   
kwargs = {'a': 1, 'b': 2}
func(**kwargs) # 输出: 3


2.装饰器:
*args: 用于接收任意数量的位置参数。
**kwargs: 用于接收任意数量的关键字参数。
exp:
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("装饰器开始")
        result = func(*args, **kwargs)
        print("装饰器结束")
        return result
    return wrapper

@my_decorator
def my_function(a, b):
    return a + b

my_function(1, 2) # 输出: 装饰器开始 3 装饰器结束

3.通用函数参数:
*args: 用于接收任意数量的位置参数。
**kwargs: 用于接收任意数量的关键字参数。   
exp:
def func(*args, **kwargs):
    print(args)
    print(kwargs)

func(1, 2, 3, a=1, b=2, c=3) # 输出: (1, 2, 3) {'a': 1, 'b': 2, 'c': 3}

python中函数的参数分类:
(1) 默认参数(Default Arguments): 函数定义时, 参数的默认值
exp:
def func(a=1, b=2):
    print(a, b)
func() # 输出: 1 2
func(3, 4) # 输出: 3 4

(2) 位置参数(Positional Arguments): 按顺序传递给函数的参数
exp:
def func(a, b):
    print(a, b)
func(1, 2) # 输出: 1 2

(3) 可变位置参数(*args): 接收任意数量的位置参数, 存储为元组
exp:
def func(*args):
    print(args)
func(1, 2, 3) # 输出: (1, 2, 3)

(4) 关键字参数(Keyword Arguments): 按名称传递给函数的参数
exp:
def add(a, b):
    return a + b

result = add(a=3, b=5)  # 使用关键字参数
print(result)  # 输出: 8

(5) 可变关键字参数(**kwargs): 接收任意数量的关键字参数, 存储为字典
exp:
def func(**kwargs):
    print(kwargs)
func(a=1, b=2, c=3) # 输出: {'a': 1, 'b': 2, 'c': 3}


参数组合使用的顺序:
(1) 位置参数
(2) 默认参数
(3) *args
(4) **kwargs
def my_function(a, b, c=10, *args, **kwargs):
    print(f"Positional arguments: a={a}, b={b}")
    print(f"Default argument: c={c}")
    print(f"Variable positional arguments: {args}")
    print(f"Variable keyword arguments: {kwargs}")

my_function(1, 2, 3, 4, 5, name="Alice", age=25)
# 输出：
# Positional arguments: a=1, b=2
# Default argument: c=3
# Variable positional arguments: (4, 5)
# Variable keyword arguments: {'name': 'Alice', 'age': 25}

匿名函数:
lambda 参数1, 参数2, ...: 表达式
exp: 两数求和
add = lambda a, b: a + b
result = add(3, 5)  # 输出: 8

exp: 两数交换
swap = lambda a, b: (b, a)
a, b = 3, 5
a, b = swap(a, b)  # 输出: a=5, b=3 

lambda常用来作为高阶函数的参数, 比如sorted()、map()、filter()等函数

'''


import time
import logging
from pathlib import Path
from functools import wraps

# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    # 设置视频首帧图缓存路径
    BASEICONPATH = Path(__file__).parent.parent.parent
    

"""设置自定义的装饰器"""


# 自定义的装饰器，用于计算函数执行时间, 最简单的装饰器
def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__}()--耗时: {(end_time - start_time):.6f} 秒")
        return result
    return wrapper


# (优化版)用于计算函数执行时间, 支持传入参数和捕获异常
def CC_TimeDec(tips="success", show_time=True, show_args=False):
    """
    时间计算装饰器
    :param show_time: 是否显示执行时间
    :param tips: 成功提示信息
    :param show_args: 是否显示函数参数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # 构建输出信息
                output = [f"[{func.__name__}]-->{tips}"]
                if show_args and (args or kwargs):
                    args_str = ", ".join([str(arg) for arg in args])
                    kwargs_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                    params = ", ".join(filter(None, [args_str, kwargs_str]))
                    output.append(f"参数: [{params}]")
                
                if show_time:
                    output.append(f", 耗时: {(end_time - start_time):.6f} 秒")
                
                if tips:
                    print("".join(output))
                
                return result
            except Exception as e:
                print(f"[{func.__name__}] 执行失败 - {str(e)}")
                raise e
        return wrapper
    return decorator


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
# logging.basicConfig(level=logging.INFO)
# compute_sum(1000000)


