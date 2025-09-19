# -*- coding: utf-8 -*-
import cv2
import time
from pathlib import Path

# 设置视频首帧图临时存放路径
BASEICONPATH = Path(__file__).parent.parent.parent / "cache" / "videos" / "video_preview_frame.jpg"
BASEICONPATH.parent.mkdir(parents=True, exist_ok=True)

def extract_video_first_frame(video_path):
    """读取视频文件首帧，保存到本地"""
    try:
        # 使用OpenCV读取视频首帧
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")
        
        # 1) 把方向提前置零 → 解码后就是正的
        # cap.set(cv2.CAP_PROP_ORIENTATION_META, 90)
        # 跳到第二帧
        # cap.set(cv2.CAP_PROP_POS_FRAMES, 1)

        # 读取第一帧并转换颜色空间
        ret, frame = cap.read()
        if not ret:
            raise ValueError("无法读取视频帧")
        cap.release()

        # 保存视频帧到本地,若存在会自动覆盖
        cv2.imwrite(str(BASEICONPATH), frame)

        return str(BASEICONPATH)
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
        # cap.set(cv2.CAP_PROP_POS_FRAMES, 1) # 跳到第二帧
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