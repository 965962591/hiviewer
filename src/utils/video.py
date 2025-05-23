# -*- coding: utf-8 -*-
import cv2
import time
from pathlib import Path

# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    # 设置视频首帧图缓存路径
    BASEICONPATH = Path(__file__).parent.parent.parent
    


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

        # 创建目录
        video_frame_img_dir = BASEICONPATH / "cache" / "videos" / "video_preview_frame.jpg"
        video_frame_img_dir.parent.mkdir(parents=True, exist_ok=True)

        # 保存视频帧到本地,若存在会自动覆盖
        cv2.imwrite(video_frame_img_dir, frame)

        return str(video_frame_img_dir)

    except Exception as e:
        print(f"提取视频首帧图失败: {e}")
        return None


def extract_first_frame_from_video(video_path):
    """读取视频文件首帧，保存到本地"""
    try:
        # 尝试打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")
            
        # 读取第一帧，设置超时机制, 最多等待2秒
        start_time = time.time()
        while time.time() - start_time < 2:
            ret, frame = cap.read()
            if ret:
                break
        cap.release()
        
        if not ret:
            raise ValueError("无法读取视频帧")
            
        # 转换颜色空间从 BGR 到 RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return frame

    except Exception as e:
        print(f"从视频文件中提取first frame失败: {e}")
        return None