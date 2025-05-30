# -*- coding: utf-8 -*-
"""创建该模块的目的：
1. 在./config/路径下配置保存一些颜色信息设置、exif显示信息设置
2. 后续计划支持可视化界面调节这些配置信息
"""
"""导入python内置模块"""
import json
import pathlib


def load_exif_settings():
        """加载EXIF信息配置"""
        try:
            # 确保配置文件config目录存在
            config_dir = pathlib.Path("./config")
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # 加载EXIF设置json文件
            exif_settings_file = config_dir / "exif_setting.json"
            if exif_settings_file.exists():
                with open(exif_settings_file, 'r', encoding='utf-8', errors='ignore') as f:
                    return json.load(f)
            else:

                label_visable_setting = {
                    "histogram_info": bool(1),
                    "exif_info": bool(1),
                    "roi_info": bool(1),
                    "ai_tips": bool(0),
                    "p3_color_space": bool(0),
                    "gray_color_space": bool(0),
                    "srgb_color_space": bool(1),
                }

                exif_visable_setting = {
                    "图片名称": bool(1),
                    "品牌": bool(1),
                    "型号": bool(1),
                    "图片大小": bool(1),
                    "图片尺寸": bool(1),
                    "图片张数": bool(1),
                    "曝光时间": bool(1),
                    "光圈值": bool(1),
                    "ISO值": bool(1),
                    "原始时间": bool(1),
                    "测光模式": bool(1),
                    "HDR": bool(1),
                    "Zoom": bool(1),
                    "Lux": bool(1),
                    "CCT": bool(1),
                    "FaceSA": bool(1),
                    "DRCgain": bool(1),
                    "Awb_sa": bool(1),
                    "Triangle_index": bool(1),
                    "R_gain": bool(1),
                    "B_gain": bool(1),
                    "Safe_gain": bool(1),
                    "Short_gain": bool(1),
                    "Long_gain": bool(1)
                }

                settings = {
                    "label_visable_settings":label_visable_setting,
                    "exif_visable_setting":exif_visable_setting
                }
                # 写到到对应的json配置文件中
                with open(exif_settings_file, 'w', encoding='utf-8', errors='ignore') as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                    return settings

        except Exception as e:
            print(f"[load_exif_settings]-->加载EXIF信息配置失败: {e}, 使用默认配置")
            return settings


def load_color_settings():
    """加载颜色设置"""
    try:
        # 确保cache目录存在
        config_dir = pathlib.Path("./config")
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "color_setting.json"

        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8', errors='ignore') as f:
                return json.load(f)
        # 设置默认颜色设置
        else: 
            print(f"[load_color_settings]-->warning: 颜色设置文件{settings_file}不存在, 设置默认颜色设置")
            
            # 基础颜色设置
            basic_color_settings = {
                "background_color_default": "rgb(173,216,230)",   # 深色背景色_好蓝
                "background_color_table": "rgb(127, 127, 127)",   # 表格背景色_18度灰
                "font_color_default": "rgb(0, 0, 0)",             # 默认字体颜色_纯黑色
                "font_color_exif": "rgb(255, 255, 255)"           # Exif字体颜色_纯白色
            }

            # 设置rgb颜色值
            rgb_color_settings = {
                "18度灰": "rgb(127,127,127)",
                "石榴红": "rgb(242,12,0)",
                "乌漆嘛黑": "rgb(22, 24, 35)",
                "铅白": "rgb(240,240,244)", 
                "水色": "rgb(136,173,166)",   
                "石青": "rgb(123,207,166)",           
                "茶色": "rgb(242,12,0)",
                "天际": "rgb(236,237,236)",   
                "晴空": "rgb(234,243,244)",  
                "苍穹": "rgb(220,230,247)", 
                "湖光": "rgb(74,116,171)", 
                "曜石": "rgb(84, 99,125)", 
                "天际黑": "rgb(8,8,6)",   
                "晴空黑": "rgb(45,53,60)",  
                "苍穹黑": "rgb(47,51,68)", 
                "湖光黑": "rgb(49,69,96)", 
                "曜石黑": "rgb(57,63,78)", 
            }

            settings = {
                "basic_color_settings":basic_color_settings,
                "rgb_color_settings":rgb_color_settings
            }

            # 写入到json文件中
            with open(settings_file, 'w', encoding='utf-8', errors='ignore') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
                return settings
            
    except Exception as e:
        print(f"[load_color_settings]-->error: 加载颜色设置失败: {e}, 使用默认颜色配置")
    return settings
