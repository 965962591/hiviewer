import os
import time
from src.utils.stitchimg import stitch_images

# 设置项目入口路径
BASEICONPATH = os.path.dirname(os.path.abspath(__file__))
 

# 使用示例
if __name__ == "__main__":
    # 设置图片路径
    image_paths = [
        f"{BASEICONPATH}/imgs/IMG_20250512_054012.jpg",
        f"{BASEICONPATH}/imgs/IMG_20250512_142009.jpg",
        f"{BASEICONPATH}/imgs/IMG_20240704_122721.jpg",
        f"{BASEICONPATH}/imgs/IMG_20250512_142023.jpg"
    ]
    # 设置字体路径
    font_path = f"{os.path.dirname(BASEICONPATH)}/resource/fonts/JetBrainsMapleMono_Regular.ttf"
    # 设置输出路径
    output_path = f"{BASEICONPATH}/imgs/stitched_image.jpg"
    # 拼接图片
    start_time = time.time()    
    success = stitch_images(image_paths, output_path, font_path)
    end_time = time.time()
    # 打印结果
    print(f"图片拼接成功！用时：{end_time - start_time}秒") if success else print("图片拼接失败！")
