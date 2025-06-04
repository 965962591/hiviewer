# -*- coding: utf-8 -*-
import os
import sys

"""
优先使用nuitka打包本项目为可执行程序hiviewer.exe
备选方案：使用 PyInstaller 打包
"""
# 打包windows可执行程序，清理缓存 ccache -C
if sys.platform == "win32": 
    # Nuitka 打包配置, 稳定可用版本
    nuitka_args = [
        'nuitka',
        '--mingw64',                            # windows平台使用的基于gcc的mingw64编译器
        '--show-memory',                        # 显示内存使用情况
        '--standalone',                         # 独立打包，不依赖python环境
        '--lto=yes',                           # 启用链接时优化,比lto=yes节省编译时间
        '--jobs=10' ,                           # 使用10个线程进行编译
        '--show-progress',                      # 显示编译进度
        '--enable-plugin=pyqt5,upx' ,           # 启用pyqt5插件
        '--windows-console-mode=disable',       # 禁用windows控制台
        '--include-data-dir=./resource=resource',               # 将resource目录下的资源文件包含到exe中
        '--include-data-dir=./config=config',                   # 将config目录下的资源文件包含到exe中
        '--windows-icon-from-ico=resource/icons/viewer_3.ico',  # 使用ico图标作为windows应用图标
        '--output-dir=dist',                    # 输出目录
        '--remove-output',                      # 删除输出目录
        'hiviewer.py',                          # 主程序文件
    ]
    
    # 优化版本配置
    nuitka_args_sample = [
        'nuitka',
        '--mingw64',
        '--standalone',
        '--show-progress',
        '--show-memory',
        '--nofollow-import-to=numpy,scipy,cv2,lxml,matplotlib,openpyxl,piexif,PIL,psutil,pywin32', 
        '--follow-import-to=src',
        '--enable-plugin=pyqt5,upx' ,
        '--windows-icon-from-ico=resource/icons/viewer_3.ico',
        '--output-dir=dist',       
        '--remove-output',                     
        'hiviewer.py',                          
    ]
    
    nuitka_module = [
        'nuitka',
        '--module',                     
        'hiviewer.py',                          
    ]

    # PyInstaller 打包配置
    pyinstaller_args = [
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--windowed',
        '--icon=resource/icons/viewer_3.ico',
        '--add-data=resource;resource',
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--name=hiviewer',
        'hiviewer.py'
    ]
    
    # 选择打包工具
    args = nuitka_args
    # args = nuitka_args_sample
    # args = pyinstaller_args

# 打包macos可执行程序
elif sys.platform == "darwin": 
    args = [
        'python3 -m nuitka',
        '--standalone',
        '--plugin-enable=pyqt5',
        '--show-memory',
        '--show-progress',
        "--macos-create-app-bundle",
        "--macos-disable-console",
        "--macos-app-name=hiviewer",
        "--macos-app-icon=resource/icons/viewer_3.ico",
        "--copyright=diamond_cz",
        '--output-dir=dist',
        'hiviewer.py',
    ]
else:
    args = [
        'pyinstaller',
        '-w',
        'hiviewer.py',
    ]

os.system(' '.join(args))
