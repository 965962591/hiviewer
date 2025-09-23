# -*- coding: utf-8 -*-
import cv2
import time
from pathlib import Path

# 设置视频首帧图临时存放路径
BASEICONPATH = Path(__file__).parent.parent.parent / "cache" / "videos" / "video_preview_frame.jpg"
BASEICONPATH.parent.mkdir(parents=True, exist_ok=True)

def _apply_video_rotation_fix(cap, frame):
    """
    应用视频旋转修正，解决Python 3.12中OpenCV不自动处理视频旋转元数据的问题
    
    Args:
        cap: cv2.VideoCapture对象
        frame: 视频帧
    
    Returns:
        numpy.ndarray: 旋转修正后的视频帧
    """
    try:
        rotation_angle = 0
        
        # 方法1: 尝试从多个可能的OpenCV属性获取旋转信息
        rotation_properties = [
            'CAP_PROP_ORIENTATION_META',  # 较新版本OpenCV
            'CAP_PROP_ORIENTATION_AUTO',  # 自动方向
        ]
        
        for prop_name in rotation_properties:
            if hasattr(cv2, prop_name):
                try:
                    prop_value = getattr(cv2, prop_name)
                    angle = cap.get(prop_value)
                    if angle and angle != 0:
                        rotation_angle = angle
                        break
                except:
                    continue
        
        # 应用旋转修正
        if rotation_angle != 0:
            # print(f"应用视频旋转修正: {rotation_angle}度")
            frame = _rotate_frame(frame, rotation_angle)
            
    except Exception as e:
        # 如果旋转处理失败，返回原始帧
        print(f"[_apply_video_rotation_fix]-->视频旋转修正处理失败: {e}")
        pass
    
    return frame


def _rotate_frame(frame, angle):
    """
    根据角度旋转视频帧
    
    Args:
        frame: 视频帧
        angle: 旋转角度 (0, 90, 180, 270)
    
    Returns:
        numpy.ndarray: 旋转后的视频帧
    """
    if angle == 0:
        return frame
    elif angle == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        # 对于任意角度，使用仿射变换
        height, width = frame.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(frame, rotation_matrix, (width, height))

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

        # 获取视频旋转信息并应用旋转修正（修复Python 3.12兼容性问题）
        frame = _apply_video_rotation_fix(cap, frame)

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
        start_time = time.time()
        while time.time() - start_time < 2:
            ret, frame = cap.read()
            if ret:
                break
        if not ret:
            raise ValueError("无法读取视频帧")

        # 获取视频旋转信息并应用旋转修正（修复Python 3.12兼容性问题）
        frame = _apply_video_rotation_fix(cap, frame)
        cap.release()

        # 转换颜色空间从 BGR 到 RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return frame
    except Exception as e:
        print(f"从视频文件中提取first frame失败: {e}")
        return None