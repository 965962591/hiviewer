#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File         :test_munch.py
@Time         :2025/05/28 11:39:18
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :测试三方包munch的使用, munch是一个可以直接使用.访问和操作字典的黑魔法库

文件头注释关键字: cc
函数头注释关键字: func
'''
from munch import Munch
import time
import sys

# 创建一个Munch对象, 并判断是否是dict对象
profile = Munch()
print(isinstance(profile, dict))


# 定义一个字典
profile = {"name": "John", "age": 25, "city": "New York"}
# 使用Munch对象包装字典
profile = Munch(profile)
# 访问字典中的元素
print(profile.name, profile.age, profile.city)  # 输出: John





def animated_progress_bar(total):
    """
    该函数主要是实现了一个动态进度条显示功能.

    """
    animation = "|/-\\"
    idx = 0
    for i in range(total + 1):
        percent = 100 * i / total
        sys.stdout.write(f"\rProgress: [{animation[idx]}] {percent:.2f}%")
        idx = (idx + 1) % len(animation)
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\n")





# 程序入口路径
if __name__ == "__main__":

    animated_progress_bar(100)

    ...