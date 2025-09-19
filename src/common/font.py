# -*- coding: utf-8 -*-
"""
单文件 JetBrainsMonoLoader —— 仅依赖 JetBrainsMapleMono-Regular.ttf
利用 Qt 合成粗体 / 斜体，保持外部接口不变。
"""
import sys
from pathlib import Path
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtCore import Qt

# 字体文件路径
FONTPATH = Path(sys.argv[0]).parent / "resource" / "fonts" / "JetBrainsMapleMono-Regular.ttf"

class JetBrainsMonoLoader:
    """一键加载 JetBrains Mono 完整字体族（单文件版）"""
    _family: str = ""
    # 缓存 (size, bold, italic) -> QFont
    _cache: dict[tuple[int, bool, bool], QFont] = {}

    # ---------- 内部：真正加载 ----------
    @classmethod
    def _ensure_loaded(cls) -> str:
        # 已加载直接返回
        if cls._family:                       
            return cls._family

        if not FONTPATH.exists():
            print(f"[JetBrainsMonoLoader] error: {FONTPATH} 不存在，将使用系统默认字体")
            # 标记为系统默认
            cls._family = ""                  
            return cls._family

        font_id = QFontDatabase.addApplicationFont(str(FONTPATH))
        if font_id == -1:
            print("[JetBrainsMonoLoader] error: 字体加载失败，将使用系统默认字体")
            cls._family = ""
        else:
            cls._family = QFontDatabase.applicationFontFamilies(font_id)[0]
            print(f"[JetBrainsMonoLoader] info: 字体族已加载: {cls._family}")
        return cls._family

    # ---------- 外部：取族名 ----------
    @classmethod
    def load(cls) -> str:
        return cls._ensure_loaded()

    # ---------- 外部：取字体（带缓存） ----------
    @classmethod
    def font(cls, point_size: int = 12, bold: bool = False, italic: bool = False) -> QFont:
        family = cls._ensure_loaded()
        key = (point_size, bold, italic)
        if key not in cls._cache:
            # 用 Qt 合成粗/斜
            weight = QFont.Bold if bold else QFont.Normal
            style = QFont.StyleItalic if italic else QFont.StyleNormal
            f = QFont(family or QFont().defaultFamily(), point_size, weight, style)
            # 强制走轮廓算法，合成效果更平滑
            f.setStyleStrategy(QFont.PreferOutline | QFont.ForceOutline)
            cls._cache[key] = f
        return cls._cache[key]