import cv2
from pathlib import Path

# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    # 设置视频首帧图缓存路径
    BASEICONPATH = Path(__file__).parent.parent.parent
    video_frame_img_dir = BASEICONPATH / "cache" / "videos" / "video_preview_frame.jpg"


def extract_video_first_frame(video_path):
    """读取视频文件首帧，保存到本地"""
    try:
        # 使用OpenCV读取视频首帧
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")
        
        # 读取第一帧并转换颜色空间
        ret, frame = cap.read()
        if not ret:
            raise ValueError("无法读取视频帧")
        
        # 释放资源
        cap.release()

        # 如果文件存在，则删除
        # if video_frame_img_dir.exists():
        #     video_frame_img_dir.unlink()

        # 创建目录
        video_frame_img_dir.parent.mkdir(parents=True, exist_ok=True)

        # 保存视频帧到本地
        cv2.imwrite(video_frame_img_dir, frame)

        return str(video_frame_img_dir)

    except Exception as e:
        print(f"提取视频首帧图失败: {e}")
        return None
