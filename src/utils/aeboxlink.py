# -*- coding: utf-8 -*-
import os
import time
import requests
import urllib.parse
import subprocess
import platform
import psutil  # 使用跨平台进程检查库

def urlencode_folder_path(folder_path):
    """
    对文件夹路径进行URL编码处理
    参数：
        folder_path (str): 要编码的文件夹路径（支持Windows/Linux格式）
    返回：
        str: URL编码后的路径字符串
    示例：
        >>> urlencode_folder_path('D:/我的文档/测试')
        'D%3A/%E6%88%91%E7%9A%84%E6%96%87%E6%A1%A3/%E6%B5%8B%E8%AF%95'
    """
    # 标准化路径并统一斜杠方向
    normalized = os.path.normpath(folder_path).replace('\\', '/')
    

    # 对路径进行URL编码，保留斜杠作为路径分隔符
    return urllib.parse.quote(normalized, safe='/')



def get_api_data(url='https://api.example.com/data', timeout=5):
    """
    获取API数据并处理异常
    参数：
        url (str): 请求地址，默认示例API
        timeout (int/float): 超时时间（秒），默认5秒
    返回：
        str/None: 成功返回响应内容，失败返回None
    """
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            # print("请求成功！")
            return response.text
        else:
            print(f"[get_api_data]-->请求失败，状态码：{response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print("[get_api_data]-->请求超时！")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[get_api_data]-->请求失败：{e}")
        return None


def check_process_running(process_name: str) -> bool:
    """
    检查指定进程是否正在运行（支持进程名称或完整路径）
    
    参数：
        process_name (str): 要检查的进程名称或完整路径
    返回：
        bool: 进程是否在运行
    
    更新说明：
    - 新增路径检查功能
    - 智能识别输入类型（路径/进程名）
    - 增加路径规范化处理
    """
    try:
        # 判断输入是否是有效文件路径
        is_path = os.path.isfile(process_name)
        
        # 路径规范化处理
        target_process_name = os.path.basename(aebox_path).lower() if is_path else process_name.lower()

        if any(p.name().lower() == target_process_name for p in psutil.process_iter()):
            print(f"✅ [check_process_running]-->{target_process_name} 进程已在运行")
            return True
        else:
            print(f"❌ [check_process_running]-->未找到运行中的进程 [{process_name}]")
            return False

    except (psutil.NoSuchProcess, PermissionError):
        return False
    except Exception as e:
        print(f"❌ [check_process_running]-->进程检查异常: {str(e)}")
        return False


def test_aebox_link(api_endpoints: list = None, process_name: str = "aebox.exe") -> bool:
    """
    测试与AEBOX软件的通信连接，新增完整功能检查
    
    参数：
        api_endpoints (list): 需要测试的API端点列表（默认包含基础测试项）
        process_name (str): AEBOX进程名称（默认'aebox.exe'）
    
    返回：
        bool: 所有检查项是否通过
    
    优化内容：
    1. 增加跨平台进程检查
    2. 支持多个API端点测试
    3. 添加详细结果输出
    4. 改进错误分类处理
    """
    try:
        # 检查进程运行状态
        if not check_process_running(process_name):
            return False

        # 默认测试项
        default_endpoints = [
            r"http://127.0.0.1:8000/set_c7_path/C%3a%5cQualcomm%5cChromatix7%5c7.3.01.36%5cChromatix.exe",
        ]
        test_urls = api_endpoints or default_endpoints

        # 执行API测试
        all_success = True
        for idx, url in enumerate(test_urls, 1):
            print(f"🔍 正在测试接口 {idx}/{len(test_urls)}: {url}")
            
            try:
                response = get_api_data(url=url, timeout=3)
                if response is None:
                    all_success = False
                    print(f"❌ 接口测试失败：{url}")
                else:
                    print(f"✅ 接口响应成功 | 返回内容：{response}")
                    time.sleep(1)  # 等待1秒后载执行
            except Exception as e:
                all_success = False
                print(f"⚠️ 测试异常: {str(e)}")

        # 最终结果汇总
        print("\n" + "="*40)
        if all_success:
            print("🎉 所有测试项通过！AEBOX连接正常")
        else:
            print("⚠️  部分测试未通过，请检查以下内容：")
            print("- 确认AEBOX软件已启动并开启API服务")
            print("- 检查网络连接和防火墙设置")
            print("- 验证API端点地址是否正确")

        return all_success
    except ImportError:
        print("请先安装psutil库：pip install psutil")
        return False


def launch_aebox(aebox_path: str) -> bool:
    """
    启动AEBOX软件并验证是否成功运行
    
    参数：
        aebox_path (str): AEBOX可执行文件的完整路径（支持带空格的路径）
    
    返回：
        bool: 是否成功启动
    
    功能说明：
        1. 自动处理路径中的空格和特殊字符
        2. 支持跨平台操作（Windows/macOS/Linux）
        3. 验证进程是否真正启动
        4. 自动识别系统类型执行对应启动命令
        5. 启动前自动检查进程是否已运行
    """
    try:
        # 检查进程运行状态
        process_name = os.path.basename(aebox_path).lower() 
        if check_process_running(process_name):
            return True

        # 验证路径有效性
        if not os.path.exists(aebox_path):
            print(f"❌ 路径不存在：{aebox_path}")
            return False
        if not os.path.isfile(aebox_path):
            print(f"❌ 不是有效文件：{aebox_path}")
            return False

        # 根据系统类型执行不同启动命令

        system = platform.system()
        if system == "Windows":
            print(f"检测当前系统为window,尝试启动程序：{aebox_path}")
            # 使用start命令避免阻塞且处理空格路径
            subprocess.Popen(['start', '', aebox_path], 
                            shell=True,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        elif system == "Darwin":  # macOS
            subprocess.Popen(['open', aebox_path],
                            start_new_session=True)
        else:  # Linux/Unix
            subprocess.Popen([aebox_path],
                            start_new_session=True)

        # 等待3秒后验证进程是否启动
        time.sleep(5)
        running = any(p.name().lower() == process_name 
                     for p in psutil.process_iter())
        
        if running:
            print(f"✅ 成功启动 {os.path.basename(aebox_path)}")
            return True
        else:
            print(f"⚠️ 进程未检测到，可能启动失败")
            return False

    except Exception as e:
        print(f"❌ 启动失败：{str(e)}")
        return False

if __name__ == '__main__':

    # 1、设置C7工具路径
    cus_url = r"http://127.0.0.1:8000/set_c7_path/C%3a%5cQualcomm%5cChromatix7%5c7.3.01.36%5cChromatix.exe"

    # 2、设置图片路径,D%3a%5co19%5cimage%5c0416%5co19·1 为图片完整路径的url编码
    cus_url_2 = r"http://127.0.0.1:8000/set_image_folder/D%3a%5co19%5cimage%5c0416%5co19·1"

    # 3、开启meta和xml解析
    cus_url = r"http://127.0.0.1:8000/trigger_parse" 

    # 4、查看当前图片和的总数，图片列表选中项，和文件名
    cus_url_4 = r"http://127.0.0.1:8000/current_image" 

    # 5、设置图片列表选中的项
    cus_url = r"http://127.0.0.1:8000/select_image/10" 

    # 6、查看当前图片列表中全部的图片名
    cus_url = r"http://127.0.0.1:8000//image_list" 

    
    # 拼接文件夹路径设置AEBOX传入的图片文件夹
    image_path = r"D:\Tuning\O19\0_pic\0418\O19"
    encoded_image_path = urlencode_folder_path(image_path)
    set_image_folder_url = f"http://127.0.0.1:8000/set_image_folder/{encoded_image_path}"

    # 传入自定义参数，设置当前图片文件夹
    # data = get_api_data(url=set_image_folder_url, timeout=10)
    # print(data)


    # 启动AEBOX软件
    aebox_path = r"D:\Image_process\aebox_utrl\aebox\aebox.exe"
    launch_aebox(aebox_path)

    # 测试程序是否在运行
    # check_process_running(aebox_path)

    # 测试与aebox的连接
    status = test_aebox_link()

    
