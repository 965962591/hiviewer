from src.api.fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import uvicorn
from typing import Optional, Generator, List
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, QObject
# 导入 Pydantic 模型
# from pydantic import BaseModel, Field
# 导入 URL 解码库
import urllib.parse
import tempfile
import os
import pandas as pd
import xml.etree.ElementTree as ET

app = FastAPI()

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 全局变量存储ImageViewer实例
viewer_instance = None

def init_api(viewer):
    """初始化API，存储ImageViewer实例"""
    global viewer_instance
    viewer_instance = viewer
    
def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """启动FastAPI服务器"""
    uvicorn.run(app, host=host, port=port)

@app.get("/select_image/{index}")
async def select_image(index: int):
    """
    根据索引选择图片列表中的项目并显示
    
    参数:
        index: 要选择的图片索引（从1开始）
        
    返回:
        dict: 包含操作状态和消息的字典
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")
        
    try:
        # 确保索引在有效范围内
        if 1 <= index <= viewer_instance.image_list.count():
            # 在主线程中执行UI操作
            QMetaObject.invokeMethod(
                viewer_instance,
                "select_and_display_image",
                Qt.QueuedConnection,
                Q_ARG(int, index)
            )
            
            return {
                "status": "success", 
                "message": f"已选择并显示第 {index} 张图片",
                "total_images": viewer_instance.image_list.count()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"索引 {index} 超出范围 (总图片数: {viewer_instance.image_list.count()})"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/select_image_by_name/{filename}")
async def select_image_by_name(filename: str):
    """
    根据图片名称选择图片列表中的项目并显示
    
    参数:
        filename: 要选择的图片文件名
        
    返回:
        dict: 包含操作状态和消息的字典
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")
        
    try:
        # 在图片列表中查找指定文件名的项目
        found = False
        for index in range(viewer_instance.image_list.count()):
            item = viewer_instance.image_list.item(index)
            if item and item.text() == filename:
                # 在主线程中执行UI操作
                QMetaObject.invokeMethod(
                    viewer_instance,
                    "select_and_display_image",
                    Qt.QueuedConnection,
                    Q_ARG(int, index + 1)  # 转换为从1开始的索引
                )
                
                return {
                    "status": "success", 
                    "message": f"已选择并显示图片: {filename}",
                    "index": index + 1,
                    "total_images": viewer_instance.image_list.count()
                }
        
        # 如果没有找到指定文件名的图片
        raise HTTPException(
            status_code=404,
            detail=f"在图片列表中找不到图片: {filename}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/current_image")
async def get_current_image():
    """
    获取当前选中的图片信息
    
    返回:
        dict: 包含当前选中图片的信息
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")
        
    try:
        current_item = viewer_instance.image_list.currentItem()
        if current_item:
            current_index = viewer_instance.image_list.row(current_item) + 1  # 转换为从1开始的索引
            return {
                "status": "success",
                "current_index": current_index,
                "filename": current_item.text(),
                "total_images": viewer_instance.image_list.count()
            }
        else:
            return {
                "status": "no_selection",
                "current_index": -1,
                "filename": None,
                "total_images": viewer_instance.image_list.count()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 修改后的 API 端点 ---

@app.get("/set_c7_path/{path:path}")
async def set_c7_path_api(path: str):
    """
    通过 URL 路径参数设置 Chromatix.exe 的路径

    参数:
        path: URL编码后的 Chromatix.exe 完整路径
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")

    try:
        # 对路径进行 URL 解码
        decoded_path = urllib.parse.unquote(path)
        QMetaObject.invokeMethod(
            viewer_instance,
            "set_c7_path",
            Qt.QueuedConnection,
            Q_ARG(str, decoded_path)
        )
        return {"status": "success", "message": f"Chromatix 路径设置请求已发送: {decoded_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置 C7 路径时出错: {str(e)}")

@app.get("/set_image_folder/{folder_path:path}")
async def set_image_folder_api(folder_path: str):
    """
    通过 URL 路径参数设置并加载图片文件夹

    参数:
        folder_path: URL编码后的图片文件夹路径
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")

    try:
        # 对路径进行 URL 解码
        decoded_folder_path = urllib.parse.unquote(folder_path)
        QMetaObject.invokeMethod(
            viewer_instance,
            "set_image_folder",
            Qt.QueuedConnection,
            Q_ARG(str, decoded_folder_path)
        )
        return {"status": "success", "message": f"图片文件夹设置请求已发送: {decoded_folder_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置图片文件夹时出错: {str(e)}")

@app.get("/trigger_parse")
async def trigger_parse_api():
    """
    通过 GET 请求触发解析元数据和生成XML的过程
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")

    try:
        QMetaObject.invokeMethod(
            viewer_instance,
            "trigger_parse_and_generate",
            Qt.QueuedConnection
        )
        return {"status": "success", "message": "解析和生成XML请求已发送"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发解析时出错: {str(e)}")

@app.get("/image_list")
async def get_image_list():
    """
    获取当前图片列表中的所有文件名

    返回:
        dict: 包含所有图片文件名的列表
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")

    try:
        image_filenames = []
        for index in range(viewer_instance.image_list.count()):
            item = viewer_instance.image_list.item(index)
            if item:
                image_filenames.append(item.text())

        return {
            "status": "success",
            "filenames": image_filenames,
            "total_images": len(image_filenames)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片列表时出错: {str(e)}")

# --- API 端点结束 --- 

@app.get("/download/{filename}")
async def download_image(filename: str):
    """
    下载指定文件名的原始图片
    
    参数:
        filename: 要下载的图片文件名
        
    返回:
        FileResponse: 图片文件的二进制流
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")
        
    try:
        if filename in viewer_instance.image_paths:
            image_path = viewer_instance.image_paths[filename]
            return FileResponse(
                path=image_path,
                filename=filename,
                media_type="image/jpeg"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"找不到图片: {filename}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate_isp_data/{folder_path:path}")
async def generate_isp_data(folder_path: str):
    """
    遍历指定文件夹中的所有_new.xml文件，提取相关数据并生成Excel文件
    
    参数:
        folder_path: URL编码后的文件夹路径
        
    返回:
        FileResponse: 生成的Excel文件
    """
    try:
        # URL解码文件夹路径
        decoded_folder_path = urllib.parse.unquote(folder_path)
        
        # 检查文件夹是否存在
        if not os.path.exists(decoded_folder_path):
            raise HTTPException(status_code=404, detail=f"文件夹不存在: {decoded_folder_path}")
            
        # 准备数据列表
        data = []
        
        # 遍历文件夹中的所有文件
        for filename in os.listdir(decoded_folder_path):
            if filename.endswith("_new.xml"):
                xml_path = os.path.join(decoded_folder_path, filename)
                try:
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    
                    # 提取所需数据
                    short_gain = root.find("short_gain")
                    long_gain = root.find("long_gain")
                    safe_gain = root.find("safe_gain")
                    lux_index = root.find("lux_index")
                    
                    # 获取原始图片文件名（去掉_new.xml后缀）
                    image_filename = filename.replace("_new.xml", ".jpg")
                    
                    # 计算ADRC gain
                    try:
                        adrc_gain = round(float(safe_gain.text) / float(short_gain.text), 2) if short_gain is not None and safe_gain is not None else None
                    except (ValueError, ZeroDivisionError):
                        adrc_gain = None
                    
                    # 将数据添加到列表
                    data.append({
                        "文件名": image_filename,
                        "Lux": float(lux_index.text) if lux_index is not None else None,
                        "Short Gain": float(short_gain.text) if short_gain is not None else None,
                        "Long Gain": float(long_gain.text) if long_gain is not None else None,
                        "Safe Gain": float(safe_gain.text) if safe_gain is not None else None,
                        "ADRC Gain": adrc_gain
                    })
                    
                except Exception as e:
                    print(f"处理文件 {filename} 时出错: {str(e)}")
                    continue
        
        # 如果没有找到任何数据
        if not data:
            raise HTTPException(status_code=404, detail="未找到任何有效的XML文件")
            
        # 创建DataFrame并按Lux值排序
        df = pd.DataFrame(data)
        df = df.sort_values(by="Lux")
        
        # 创建一个临时文件来保存Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            # 将DataFrame保存为Excel文件
            df.to_excel(tmp.name, index=False, engine="openpyxl")
            
            # 返回生成的Excel文件
            return FileResponse(
                path=tmp.name,
                filename="isp_data.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成Excel文件时出错: {str(e)}")

# 添加主线程运行函数的装饰器
def run_in_main_thread(func):
    """装饰器，确保函数在主线程中运行"""
    def wrapper(*args, **kwargs):
        app = QObject.sender() if QObject.sender() else None
        if app and app.thread() != QObject.thread(app):
            # 如果当前线程不是主线程，使用信号-槽机制转到主线程
            future_result = []
            def slot_func():
                try:
                    result = func(*args, **kwargs)
                    future_result.append(result)
                except Exception as e:
                    future_result.append(e)
            
            QMetaObject.invokeMethod(app, slot_func, Qt.QueuedConnection)
            # 等待结果（注意：这在实际应用中可能会阻塞）
            while not future_result:
                pass
            
            result = future_result[0]
            if isinstance(result, Exception):
                raise result
            return result
        else:
            # 如果已经在主线程中，直接调用
            return func(*args, **kwargs)
    return wrapper

@app.get("/sort_images_by_filename/{order}")
async def sort_images_by_filename(order: str):
    """
    按照文件名对图片列表进行排序
    
    参数:
        order: 排序顺序，"asc"为升序，"desc"为降序
        
    返回:
        dict: 包含操作状态和排序后的图片列表
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")
        
    try:
        if order not in ["asc", "desc"]:
            raise HTTPException(status_code=400, detail="排序参数必须为'asc'或'desc'")
            
        # 直接调用图像查看器的排序方法
        viewer_instance.file_sort(order == "asc")
        
        # 获取排序后的图片文件名列表
        image_filenames = []
        for index in range(viewer_instance.image_list.count()):
            item = viewer_instance.image_list.item(index)
            if item:
                image_filenames.append(item.text())
        
        return {
            "status": "success",
            "message": f"图片列表已按文件名{'升序' if order == 'asc' else '降序'}排序",
            "sorted_filenames": image_filenames
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sort_images_by_lux/{order}")
async def sort_images_by_lux(order: str):
    """
    按照Lux值对图片列表进行排序
    
    参数:
        order: 排序顺序，"asc"为升序，"desc"为降序
        
    返回:
        dict: 包含操作状态和排序后的图片列表
    """
    if not viewer_instance:
        raise HTTPException(status_code=500, detail="ImageViewer实例未初始化")
        
    try:
        if order not in ["asc", "desc"]:
            raise HTTPException(status_code=400, detail="排序参数必须为'asc'或'desc'")
            
        # 直接调用图像查看器的排序方法
        viewer_instance.lux_sort(order == "asc")
        
        # 获取排序后的图片文件名列表
        image_filenames = []
        for index in range(viewer_instance.image_list.count()):
            item = viewer_instance.image_list.item(index)
            if item:
                image_filenames.append(item.text())
        
        return {
            "status": "success",
            "message": f"图片列表已按Lux值{'升序' if order == 'asc' else '降序'}排序",
            "sorted_filenames": image_filenames
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    