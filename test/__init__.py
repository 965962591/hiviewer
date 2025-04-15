""" 项目结构
hiviewer_root/
├── src/ 存在项目主要功能模块
│   ├── __init__.py
│   ├── modules/ 存放各个子界面功能模块
│   │   ├── __init__.py
│   │   ├── sub_bat.py
│   │   ├── sub_compare_image_view.py
│   │   ├── sub_compare_video_view.py
│   │   ├── sub_image_process.py
│   │   ├── sub_image_size_reduce.py
│   │   └── sub_rename_view.py
│   │
│   ├── ui/ 存在主界面和看图子界面的UI
│   │   ├── __init__.py
│   │   ├── main_ui.py
│   │   └── sub_ui.py
│   │
│   └── utils/ 存放自定义的功能模块
│       ├── __init__.py
│       ├── about.py
│       ├── AI_tips.py
│       ├── Custom_dialog_class.py
│       ├── Custom_Font_class.py
│       ├── hisnot.py
│       ├── installer.py
│       ├── mipi2raw.py
│       └── update.py
├── test/ 存在测试代码
│   ├── __init__.py
│   │
│   └── test_utils_about.py
│   
├── icons/ 存放ico图标
│   
├── docs/ 存放说明文档
│   
├── fonts/ 存放自定义字体
│   
├── tools/ 存放一些exe类工具
│   
├── .gitignore 忽略文件
│   
├── README.md 说明文档
│   
├── requirements.txt 三方库依赖
│   
└── hiviewer.py 项目主函数


"""