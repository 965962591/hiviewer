import cv2
import time
from pathlib import Path
from PIL import Image

# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    # 设置视频首帧图缓存路径
    BASEICONPATH = Path(__file__).parent.parent.parent
    
# 读取图片
def read_image(image_path):
    image = Image.open(image_path)
    return image

