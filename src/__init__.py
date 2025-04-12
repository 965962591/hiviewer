""" 项目结构
hiviewer_root/
├── src/
│   ├── __init__.py
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── sub_bat.py
│   │   ├── sub_compare_image_view.py
│   │   ├── sub_compare_video_view.py
│   │   ├── sub_image_process.py
│   │   ├── sub_image_size_reduce.py
│   │   └── sub_rename_view.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_ui.py
│   │   └── sub_ui.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── about.py
│       ├── AI_tips.py
│       ├── Custom_dialog_class.py
│       ├── Custom_Font_class.py
│       ├── hisnot.py
│       ├── installer.py
│       ├── mipi2raw.py
│       └── update.py
│   
├── icons/
│   
├── docs/
│   
├── fonts/
│   
├── tools/
│   
├── .gitignore
│   
├── README.md
│   
├── requirements.txt
│   
└── hiviewer.py 主函数


"""


import os
import sys

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 将项目根目录添加到系统路径
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 导出根目录常量
__all__ = ['BASE_DIR']