import os
import sys

"""
优先使用nuitka打包本项目为可执行程序hiviewer.exe

"""
# 打包windows可执行程序
if sys.platform == "win32": 
    args = [
        'nuitka',
        '--standalone',
        '--lto=yes',
        '--jobs=10' ,
        '--mingw64',
        '--show-progress',
        '--show-memory',              
        '--mingw64',              
        '--show-memory' ,
        '--enable-plugin=pyqt5,numpy' ,
        '--windows-icon-from-ico=icons/viewer_3.ico',
        '--windows-disable-console',
        '--output-dir=dist',
        'hiviewer.py',
    ]
# 打包macos可执行程序
elif sys.platform == "darwin": 
    args = [
        'python3 -m nuitka',
        '--standalone',
        '--plugin-enable=pyqt5,numpy',
        '--show-memory',
        '--show-progress',
        "--macos-create-app-bundle",
        "--macos-disable-console",
        "--macos-app-name=hiviewer",
        "--macos-app-icon=icons/viewer_3.ico",
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
