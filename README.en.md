<p align="right">
   <strong>Chinese</strong> | <a href="./README.en.md">English</a>
</p>

<div align="center">

# 📷 hiviewer

<img src="./resource/icons/viewer_3.ico" alt="XianyuBot Logo" width="180">

**hiviewer** is an **intelligent image viewer tool** that supports **image & video** comparison. This project is implemented using **Python + PyQt5**, providing users with a more convenient way to view images.

<p align="center">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python Version">
  </a>
  <a href="https://platform.openai.com/">
    <img src="https://img.shields.io/badge/PyQT5-5.15%2B-FF6F61" alt="PyQT5 Version">
  </a>
  <a href="https://raw.githubusercontent.com/yourusername/xianyubot/main/LICENSE">
    <img src="https://img.shields.io/badge/license-GPL 3.0-brightgreen" alt="license">
  </a>
</p>

</div>

## Project Structure

```

hiviewer/
├── resource/          
│   ├── icons/         
│   ├── docs/          
│   ├── fonts/         
│   ├── tools/         
│   └── installer.exe 
├── src/                
│   ├── __init__.py
│   ├── common/          
│   │   ├── __init__.py  
│   │   └── ...
│   ├── components/      
│   │   ├── __init__.py 
│   │   └── ... 
│   ├── utils/          
│   │   ├── __init__.py 
│   │   └── ...
│   └── view/         
│       ├── __init__.py 
│       └── ...  
├── test/              
│   ├── __init__.py
│   └── ...
├── .gitignore         
├── README.en.md       
├── README.md          
├── LICENSE            
├── requirements.txt    
├── generate_exe.py     
└── hiviewer.py         

```

## Usage Instructions

### Environment Setup

```bash
# Install dependencies
conda create -n hiviewer python=3.11
conda activate hiviewer
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Run the program
python hiviewer.py
```

### Download Installer

#### Windows Users

1. Download the "[latest.zip](https://github.com/diamond-cz/Hiviewer_releases/releases/)" archive
2. After extraction, double-click the "hiviewer.exe" program to run

#### macOS Users

Not currently maintained

### Demo

> New versions will have new changes. This is for reference only. For detailed usage instructions, please click [here](https://github.com/diamond-cz/hiviewer_releases). It's not a hassle `-_-)o`

**Main Interface Demo**

![Alt text](resource/images/Image_mainwindow.png)

![Alt text](resource/images/Image_mainwindow1.png)

**Image Viewing Interface Demo**

![Alt text](resource/images/Image_subwindow_pic.png)

**Video Playback Interface Demo**

![Alt text](resource/images/Image_video.png)

### Technical Implementation

![Alt text](resource/images/Image_pic.png)

## License

This project is licensed under **GPL 3.0** ([GNU General Public License](https://jxself.org/translations/gpl-3.zh.shtml)), allowing free use and modification, but the modified source code must be made public.
For more details, please refer to the [LICENSE](LICENSE) file.

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://jxself.org/translations/gpl-3.zh.shtml)
