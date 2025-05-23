# -*- coding: utf-8 -*-
from PIL import Image
from pathlib import Path 
from pillow_heif import read_heif


# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BASEICONPATH = Path(__file__).parent.parent.parent

"""
[提示] 处理实况图的模块
1. 安卓手机jpg格式实况图可以转换成jpg+MP4视频
2. 苹果手机heic格式实况图可以转换成jpg
    - 暂时无法转换为mov视频,打包后非常大
    - 使用pillow_heif提取 HEIC格式图片
"""

def locate_video_google(data):
    # 小米手机用的是ftypmp42 
    # position - 4 表示MP4数据前有4字节的大小信息要去掉
    signatures = [b'ftypmp42', b'ftypisom', b'ftypiso2']
    for signature in signatures:
        position = data.find(signature)
        if position != -1:
            return position - 4
    return -1


def locate_video_samsumg(data):
    signature = b"MotionPhoto_Data"
    position = data.find(signature)
    if position != -1:
        return position + len(signature)
    return -1


def extract_mvimg(srcfile, photo_dir, video_dir):
    basefile = Path(srcfile).stem
    offset = None 

    with open(srcfile, 'rb') as file:
        data = file.read() 
        offset = locate_video_google(data) or locate_video_samsumg(data)
        
    if offset != -1:
        # 保存图片部分
        photo_dir.mkdir(parents=True, exist_ok=True)
        with open(photo_dir / f"{basefile}.jpg", 'wb') as jpgfile:
            jpgfile.write(data[:offset])

        # 保存视频部分
        video_dir.mkdir(parents=True, exist_ok=True)
        with open(video_dir / f"{basefile}.mp4", 'wb') as mp4file:
            mp4file.write(data[offset:])
    else:
        print(f"Can't find video data in {srcfile}; skipping...")



def extract_heic(srcfile, photo_dir, video_dir):
    basefile = Path(srcfile).stem
    
    # 使用pillow_heif提取 HEIC格式图片
    heif_file = read_heif(srcfile)
    image = Image.frombytes(mode=heif_file.mode, size=heif_file.size, data=heif_file.data)

    # 保存图片
    photo_dir.mkdir(parents=True, exist_ok=True)
    output_file = photo_dir / f"{basefile}.jpg"
    image.save(output_file, "JPEG")

    # 提取MOV视频，使用ffmpeg,有点问题，暂时不用
    # video_dir.mkdir(parents=True, exist_ok=True)
    # output_file = video_dir / f"{basefile}.mov"
    # extract_video_from_heic(srcfile, output_file)
    pass



# 提取HEIC图片为jpg，并保存到缓存目录中，返回缓存路径
def extract_jpg_from_heic(srcfile):
    """提取HEIC图片,返回缓存路径"""
    try:
        # 如果文件不存在，则返回None
        if not Path(srcfile).exists():
            raise FileNotFoundError(f"文件不存在: {srcfile}")
        
        # 构建提取的jpg图片路径,使用pathlib处理路径，更现代和高效
        tarfile = BASEICONPATH / "cache" / "photos" / Path(srcfile).name.replace(".heic", ".jpg")
        tarfile.parent.mkdir(parents=True, exist_ok=True)

        # 如果文件存在，则直接返回
        if tarfile.exists():
            return tarfile._str

        # 使用pillow_heif提取 HEIC格式图片
        heif_file = read_heif(srcfile)
        image = Image.frombytes(mode=heif_file.mode, size=heif_file.size, data=heif_file.data)
                
        # 保存图片
        image.save(tarfile, "JPEG", quality=100)
        return tarfile._str
    
    except Exception as e:
        print(f"提取HEIC图片失败: {e}")
        return None
    

# 提取HEIC图片为PIL.Image.Image对象
def extract_pil_image_from_heic(srcfile):
    """提取HEIC图片,返回PIL.Image.Image对象"""
    try:
        if not Path(srcfile).exists():
            print(f"文件不存在: {srcfile}")
            return False

        # 使用pillow_heif提取 HEIC格式图片
        heif_file = read_heif(srcfile)
        image = Image.frombytes(mode=heif_file.mode, size=heif_file.size, data=heif_file.data)
        
        return image
    except Exception as e:
        print(f"提取HEIC图片失败: {e}")
        return None


def extract_mov_from_heic(srcfile, video_dir):
    """提取HEIC图片中的MOV视频"""
    pass


# 提取MVIMG_*.jpg中的MP4视频
def extract_mp4_from_mvimg(srcfile):
    """提取MVIMG_*.jpg中的MP4视频"""
    try:
        if not Path(srcfile).exists():
            raise FileNotFoundError(f"文件不存在: {srcfile}")
        
        offset = None 
        with open(srcfile, 'rb') as file:
            data = file.read() 
            offset = locate_video_google(data) or locate_video_samsumg(data)
            
        if offset == -1:
            raise Exception(f"没有找到视频数据")
        
        # 保存视频部分
        video_dir = BASEICONPATH / "cache" / "videos" / Path(srcfile).name.replace(".jpg", ".mp4")
        video_dir.parent.mkdir(parents=True, exist_ok=True)
        with open(video_dir, 'wb') as mp4file:
            mp4file.write(data[offset:])

        return video_dir._str
    except Exception as e:
        print(f"提取实况图MVIMG_*.jpg中的MP4视频失败: {e}")
        return None


# 批量抽取
def process_directory(srcdir, photo_dir, video_dir):
    try:
        # files = [f for f in os.listdir(srcdir) if f.startswith("MVIMG_") and f.endswith(".jpg")]
        files = [f for f in Path(srcdir).iterdir() if f.suffix in [".jpg", ".heic"]]
        for filename in files:
            srcfile = srcdir / filename
            if filename.endswith(".jpg"):
                extract_mvimg(srcfile, photo_dir, video_dir)
            elif filename.endswith(".heic"):
                extract_heic(srcfile, photo_dir, video_dir)
        return len(files)
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0
        

if __name__ == "__main__":
    """支持将安卓手机jpg格式实况图转换成jpg+MP4视频"""
    """支持将苹果手机heic格式实况图转换成jpg，暂时无法转换为mov视频,打包后非常大"""
    
    base_path = Path(__file__).parent
    srcdir = base_path / "photos"                 # 包含实况图的目录
    photo_dir = base_path / "photos_extracted"    # 保存提取的图片的目录
    video_dir = base_path / "videos_extracted"    # 保存提取的视频的目录
    
    status_code = process_directory(srcdir, photo_dir, video_dir)

    print(f"Sucess! 共处理{status_code}张实况图-v-")

    input("按 Enter 键退出...")  # 暂停黑窗口