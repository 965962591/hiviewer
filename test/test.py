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


# 创建一个Munch对象, 并判断是否是dict对象
profile = Munch()
print(isinstance(profile, dict))


# 定义一个字典
profile = {"name": "John", "age": 25, "city": "New York"}
# 使用Munch对象包装字典
profile = Munch(profile)
# 访问字典中的元素
print(profile.name, profile.age, profile.city)  # 输出: John




def test_munch():
    """
    @Description :
    @Param:
    @Returns     :
    """
    
    pass



# 程序入口路径
if __name__ == "__main__":
    pass