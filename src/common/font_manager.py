# -*- coding: utf-8 -*-
import os
import sys
from PyQt5.QtGui import  QFontDatabase, QFont

# 导入自定义装饰器
from src.utils.decorator import CC_TimeDec


"""设置根目录"""
# 通过当前py文件来定位项目主入口路径，向上找两层父文件夹
if True:
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 通过主函数hiviewer.py文件来定位项目主入口路径
if False:
    BASE_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
    


class SingleFontManager:
    """单个字体管理类（支持传入字体路径）"""
    _instance = None
    _font = None
    _initialized = False

    @classmethod
    @CC_TimeDec(tips="SingleFontManager初始化字体管理器")
    def initialize(cls, font_path=None):
        """初始化字体管理器，支持传入字体路径"""
        if not cls._initialized or font_path is not None:
            try:
                if font_path is None:
                    font_path = os.path.join(BASE_PATH, "resource", "fonts", "xialu_wenkai.ttf")
                if not os.path.exists(font_path):
                    print(f"[initialize]-->字体管理类SingleFontManager中: {font_path}不存在,请检查字体文件是否存在")
                    
                font_db = QFontDatabase()
                font_id = font_db.addApplicationFont(font_path)
                if font_id != -1:
                    font_family = font_db.applicationFontFamilies(font_id)[0]
                    cls._font = QFont(font_family)
                    cls._initialized = True
                else:
                    print("[initialize]-->字体加载失败，使用系统默认字体")
                    cls._font = QFont()
            except Exception as e:
                print(f"[initialize]-->字体初始化错误: {e}")
                cls._font = QFont()
                cls._initialized = True

    @classmethod
    def get_font(cls, size=12, font_path=None):
        """获取指定大小的字体"""
        if not cls._initialized or font_path is not None:
            cls.initialize(font_path)
        font = QFont(cls._font)
        font.setPointSize(size)
        return font


class MultiFontManager:
    """多个字体管理类（支持传入多个字体路径）"""
    _fonts = {}  # 存储字体及其大小
    _initialized = {}
    _default_font_paths = []  # 存储多个默认字体路径

    @classmethod
    @CC_TimeDec(tips="MultiFontManager初始化字体管理器")
    def initialize(cls, font_paths):
        """初始化字体管理器，支持传入多个字体路径"""
        for font_path in font_paths:
            if font_path and (font_path not in cls._default_font_paths or not cls._initialized.get(font_path, False)):
                try:
                    if not os.path.exists(font_path):
                        print(f"[initialize]-->字体管理类MultiFontManager中: {font_path} 不存在, 请检查字体文件是否存在")
                        continue
                    
                    font_db = QFontDatabase()
                    font_id = font_db.addApplicationFont(font_path)
                    if font_id != -1:
                        font_family = font_db.applicationFontFamilies(font_id)[0]
                        # print(f"字体管理类FontManager中: {font_family} 字体加载成功")
                        cls._fonts[font_family] = {}
                        cls._default_font_paths.append(font_path)
                        cls._initialized[font_path] = True
                    else:
                        print("[initialize]-->字体加载失败，使用系统默认字体")
                except Exception as e:
                    print(f"[initialize]-->字体初始化错误: {e}")
                    cls._initialized[font_path] = True
        # print("[initialize]-->多字体类-MultiFontManager--初始化成功")

    @classmethod
    def get_font(cls, font_family, size=12):
        """获取指定字体及大小的字体"""
        if font_family not in cls._fonts:
            raise ValueError(f"字体 {font_family} 未初始化，请先调用 initialize() 方法传入字体路径")
        
        if size not in cls._fonts[font_family]:
            cls._fonts[font_family][size] = QFont(font_family)
            cls._fonts[font_family][size].setPointSize(size)
        
        return cls._fonts[font_family][size]