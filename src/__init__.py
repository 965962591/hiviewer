# -*- encoding: utf-8 -*-
'''
@File         :__init__.py
@Time         :2025/06/03 10:28:23
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :代码结构,python使用技巧

(1) 反斜杠 \ 续行符
(2) 链式比较 bool(5<b<10) 
(3) 列表推导式 [x**2 for x in range(10) if x % 2 == 0]
(4) 扁平化列表 [item for sublist in matrix for item in sublist]
(5) 小整数池 [-5,256] 为避免频繁创建和销毁整数对象, Python定义了小整数池, 范围为[-5,256],这些整数对象在程序运行期间一直存在, 不会被垃圾回收
(6) 字符串驻留机制(string interning),用于优化内存管理，提高性能, 相同字符串共享一个内存地址;手动intern机制, 使用sys.intern()函数
(7) 命令行测试运行效率, python -m timeit -n 1000000 -r 5 -v "dict()"   python -m timeit -n 1000000 -r 5 -v "x = 10; y = 20; result = x + y"
(8) try-except-else-finally结构中, try中的return语句不是函数的终点, 而是等finally块执行完后返回;如果finally块中没有return语句, 则返回try块中的return语句的值, 否则返回finally块中的return语句的值
(9) 使用with语句管理资源, 确保资源释放, 避免忘记关闭文件, 数据库连接等

(10) 高级函数处理列表的实用技巧：
(10.1) 使用enumerate()代替range()遍历列表, 可以同时获取索引和元素
(10.2) 使用any()和all()函数, any(iterable) 如果iterable的任何元素为True, 则返回True, 否则返回False; all(iterable) 如果iterable的所有元素为True, 则返回True, 否则返回False
(10.3) 使用zip()函数同时遍历多个列表, 可以同时获取多个列表的元素
(10.4) 使用map()函数处理列表中的每个元素, 可以避免显式使用for循环, map(function, iterable) 对iterable中的每个元素应用function, 返回一个结果列表
(10.5) 使用filter(None,['hello','','','world','',None,''])过滤空值
(10.6) 使用reduce()函数处理列表中的每个元素, 可以避免显式使用for循环, reduce(function, iterable) 对iterable中的每个元素应用function, 返回一个结果
(10.7) 使用sorted()函数对列表进行排序, 可以避免显式使用for循环, sorted(iterable, key=None, reverse=False) 返回一个新的排序后的列表
(10.8) 使用set()函数去重, 可以避免显式使用for循环, set(iterable) 返回一个新的去重后的列表

python命令行操作技巧: 
(11.1) 查看python包的搜索路径, python -c "print('\n'.join(__import__('sys').path))"
(11.2) 查看python包的搜索路径, python -m site , 更全面，包括标准库路径、用户环境目录；
    直接获取用户环境目录方法 python -c "import site;print(site.getusersitepackages())"
(11.3) 命令行执行python代码, python -c "print('hi,diamond_cz'); print('Hello, World!')"
(11.4) 快速搭建http服务器,实现目录共享, python -m http.server 8000, 在浏览器中访问 http://localhost:8000
(11.5) 快速构建离线html文档, 
    方法一, python -m pydoc -p 5200, 在浏览器中访问 http://localhost:5200
    方法二, python -m pydoc -w 模块名, 在当前目录生成模块的html文档


'''