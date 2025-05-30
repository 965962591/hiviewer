# -*- encoding: utf-8 -*-
'''
@File         :__init__.py
@Time         :2025/05/30 14:06:00
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :


列表推导式通常比等效的循环更快，因为它们在内部进行了优化
列表推导式 [expression for item in iterable if condition]
expression: 对每个元素进行的操作。
item: 迭代器中的每个元素。
iterable: 可迭代对象。
condition: 可选，用于过滤元素。

# 生成一个包含 0 到 9 中偶数的平方的列表
even_squares = [x**2 for x in range(10) if x % 2 == 0]
print(even_squares)  # 输出: [0, 4, 16, 36, 64]

嵌套列表推导式
# 生成一个二维列表
matrix = [[x * y for y in range(1, 4)] for x in range(1, 4)]
print(matrix)  # 输出: [[1, 2, 3], [2, 4, 6], [3, 6, 9]]

# 扁平化一个二维列表
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flattened = [item for sublist in matrix for item in sublist]
print(flattened)  # 输出: [1, 2, 3, 4, 5, 6, 7, 8, 9]


代码续行符：\
# 在单行字符串中使用续行符
text = "This is a long string that spans multiple lines. \
It can be written in a single line, but it's easier to read when written on multiple lines."   

# 在多行字符串中使用续行符
text = """
This is a long string that spans multiple lines.
It can be written in a single line, but it's easier to read
when written on multiple lines.
""" 


'''

