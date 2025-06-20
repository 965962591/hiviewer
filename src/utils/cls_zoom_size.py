# -*- encoding: utf-8 -*-
'''
@File         :cls_zoom.py
@Time         :2025/06/20 17:34:01
@Author       :diamond_cz@163.com
@Version      :1.0
@Description  :根据zoom值和图片尺寸分类图片到子文件夹

文件头注释关键字: cc
函数头注释关键字: func
'''


def classify_images_by_zoom(source_folder):
    """
    根据zoom值分类图片到子文件夹
    Args:
        source_folder (str): 要处理的图片文件夹路径
    """
    import os
    import json
    import shutil
    import threading
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor
    from tqdm import tqdm

    # 创建统计字典和线程锁
    zoom_stats = {}
    lock = threading.Lock()

    def process_file(filename):
        nonlocal zoom_stats
        file_path = os.path.join(source_folder, filename)
        
        try:
            # 读取EXIF信息
            with Image.open(file_path) as pil_img:
                exif_dict = pil_img.getexif()
                info = exif_dict.get(39321, None) if exif_dict else None
                
                if info and isinstance(info, str):
                    data = json.loads(info)
                    zoom = data.get("zoomMultiple", "unknown")
                else:
                    zoom = "no_zoom_info"

            # 创建目标文件夹
            zoom_folder = os.path.join(source_folder, f"zoom_{zoom}")
            os.makedirs(zoom_folder, exist_ok=True)
            
            # 移动文件
            dest_path = os.path.join(zoom_folder, filename)
            shutil.move(file_path, dest_path)
            
            # 更新统计信息
            with lock:
                zoom_stats[zoom] = zoom_stats.get(zoom, 0) + 1

        except Exception as e:
            print(f"\n❌ 处理文件 {filename} 失败: {str(e)}")

    # 预过滤图片文件
    files = [f for f in os.listdir(source_folder) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # 使用多线程处理
    with ThreadPoolExecutor(max_workers=min(32, os.cpu_count() * 4)) as executor:
        list(tqdm(
            executor.map(process_file, files),
            total=len(files),
            desc="📁 正在处理图片",
            unit="file",
            ncols=100
        ))

    # 打印统计结果
    print("\n✅ 分类完成，统计信息：")
    for zoom, count in sorted(zoom_stats.items(), key=lambda x: x[0]):
        print(f"🔍 Zoom {zoom}: {count} 张图片")


def classify_images_by_size(source_folder):
    """
    根据图片尺寸分类到子文件夹
    Args:
        source_folder (str): 要处理的图片文件夹路径
    """
    import os
    import shutil
    import threading
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor
    from tqdm import tqdm

    # 创建统计字典和线程锁
    size_stats = {}
    lock = threading.Lock()

    def process_file(filename):
        nonlocal size_stats
        file_path = os.path.join(source_folder, filename)
        
        try:
            # 获取图片尺寸
            with Image.open(file_path) as pil_img:
                width, height = pil_img.size
                size_key = f"{width}x{height}"

            # 创建目标文件夹
            size_folder = os.path.join(source_folder, f"size_{size_key}")
            os.makedirs(size_folder, exist_ok=True)
            
            # 移动文件
            dest_path = os.path.join(size_folder, filename)
            shutil.move(file_path, dest_path)
            
            # 更新统计信息
            with lock:
                size_stats[size_key] = size_stats.get(size_key, 0) + 1

        except Exception as e:
            print(f"\n❌ 处理文件 {filename} 失败: {str(e)}")

    # 预过滤图片文件
    files = [f for f in os.listdir(source_folder) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # 使用多线程处理
    with ThreadPoolExecutor(max_workers=min(32, os.cpu_count() * 4)) as executor:
        list(tqdm(
            executor.map(process_file, files),
            total=len(files),
            desc="📏 正在按尺寸分类",
            unit="file",
            ncols=100
        ))

    # 打印统计结果
    print("\n✅ 尺寸分类完成，统计信息：")
    for size, count in sorted(size_stats.items(), 
                            key=lambda x: x[1], 
                            reverse=True):
        print(f"📐 尺寸 {size}: {count} 张图片")


if __name__ == "__main__":
    print(f"✅ 开始分类图片....")
    
    # 要处理的图片文件夹路径
    folder =  r"C:\Users\caozhen\Downloads\1"
    
    # 根据zoom值分类
    classify_images_by_zoom(folder)
    
    # 图片尺寸分类
    classify_images_by_size(folder)
    print("✅ 分类完成！请检查目标文件夹中的分类结果")