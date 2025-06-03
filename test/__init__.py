# -*- encoding: utf-8 -*-
'''
@File         :__init__.py
@Time         :2025/06/03 15:09:05
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  : 测试文件

usercustomize.py 在python启动时执行, 可以修改python启动时的行为, 比如念一段平安经
打印用户环境目录:
    python -c "import site;print(site.getusersitepackages())"
需要放置在用户环境位置: 
    windows: C:\Users\用户名\AppData\Roaming\Python\Python310\site-packages\usercustomize.py
    linux: ~/.local/lib/python3.10/site-packages/usercustomize.py
当前使用的是win下的anaconda虚拟环境hi, 放置在:
    D:\Tool_ml\Anaconda\envs\hi\Lib\site-packages\usercustomize.py


'''