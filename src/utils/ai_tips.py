
# -*- coding: utf-8 -*-
"""导入python内置库"""
import os
import base64
from io import BytesIO

"""导入python第三方库"""
from PIL import Image
from openai import OpenAI

# 设置API密钥
API_KEY = "sk-bbokuaxjdsshoqtibaikradapkbhqgcsetdyjyvtheldbwbr"

# 设置test_image_path
one_pic = [
    'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/photo\C3N\IMG_20241105_081924.jpg'
]
two_pic = [
    'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/photo\C3N\IMG_20241105_133126.jpg',
    'D:/Tuning/M5151/0_picture/20241105_FT/1105-C3N后置GL四供第一轮FT（宜家+日月光）/photo\一供\IMG_20241105_192629.jpg'
]

# 自定义硅基流动大模型类
class CustomLLM_Siliconflow:
    """针对硅基流动大模型进行封装，并提供调用接口，适用于视觉理解"""
    def __call__(self,select_model="Qwen/Qwen2-VL-72B-Instruct", prompt="描述图片内容", image_path_list=[]):

        # 预处理所有图片
        print("预处理...")
        base64_images = []
        for path in image_path_list:
            base64_str = get_image_base64(path)
            if base64_str:
                base64_images.append(base64_str)
            else:
                print(f"图片 {path} 处理失败")
                return None
            
        # 初始化OpenAI客户端
        client = OpenAI(api_key=API_KEY, base_url="https://api.siliconflow.cn/v1")
        
        # 构造消息时使用预处理后的base64
        response_messages = [{
            "role": "user",
            "content": []
        }]

        for base64_str in base64_images:
            response_messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_str}",
                    # "detail": "low"  # 强制使用低细节模式减少数据量
                }
            })

        response_messages[0]["content"].append({
            "type": "text",
            "text": prompt
        })

        # 发送请求（保持原有逻辑）
        print("请求中...")
        response = client.chat.completions.create(
            model=select_model,
            messages=response_messages
        )


        # 打印响应结构，以便调试
        # print("Response structure:", response)

        # 收集所有响应内容
        content = ""
        if hasattr(response, 'choices') and response.choices:
            for choice in response.choices:
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    chunk_content = choice.message.content
                    # print(chunk_content, end='')  # 可选：打印内容
                    content += chunk_content  # 

        return content  # 返回最终的响应内容

    
    def get_image_base64_basic(image_path):
        """获取图片base64编码,不带压缩功能的基础版"""
        try:
            # 打开图像文件
            with open(image_path, 'rb') as image_file:
                # 读取图像数据
                image_data = image_file.read()
                # 将图像数据编码为Base64字符串
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return base64_data
        except Exception as e:
            print(f"Error: {e}")
            return None

    def get_image_base64(image_path):
        """获取图片base64编码,带压缩功能"""
        try:
            # 先压缩图片
            compressed_data = compress_image(image_path)
            if not compressed_data:
                return None
                
            # 检查压缩后大小
            if len(compressed_data) > 4*1024*1024:  # 4MB二进制 ≈ 5.3MB base64
                print(f"警告: 图片 {os.path.basename(image_path)} 压缩后仍较大 ({len(compressed_data)/1024/1024:.2f}MB)")
                
            base64_data = base64.b64encode(compressed_data).decode('utf-8')
            return base64_data
        except Exception as e:
            print(f"Error: {e}")
            return None

"""硅基流动支持的对话模型
Deepseek 系列：
deepseek-ai/DeepSeek-V2.5
deepseek-ai/DeepSeek-V3 响应时间略慢于v2.5,但是效果更好

书生系列：响应比较快的
internlm/internlm2_5-20b-chat
internlm/internlm2_5-7b-chat
Pro/internlm/internlm2_5-7b-chat

Qwen系列: 响应比较快的
Qwen/Qwen2.5-72B-Instruct
Qwen/Qwen2.5-32B-Instruct
Qwen/Qwen2.5-14B-Instruct
Qwen/Qwen2.5-7B-Instruct
Pro/Qwen/Qwen2.5-7B-Instruct

GLM 系列：
THUDM/glm-4-9b-chat
Pro/THUDM/glm-4-9b-chat

模型微调，对话模型已支持：
Qwen/Qwen2.5-7B-Instruct
Qwen/Qwen2.5-14B-Instruct
Qwen/Qwen2.5-32B-Instruct
Qwen/Qwen2.5-72B-Instruct
meta-llama/Meta-Llama-3.1-8B-Instruct
"""
# chat_model对话模型
def get_siliconflow_chat_response(select_model="deepseek-ai/DeepSeek-V2.5", prompt="请详细介绍一下你自己"):
    try:
        # 发送请求
        print("请求中...")
        
        # 创建OpenAI客户端
        client = OpenAI(api_key="sk-bbokuaxjdsshoqtibaikradapkbhqgcsetdyjyvtheldbwbr", base_url="https://api.siliconflow.cn/v1")
        response = client.chat.completions.create(
            model = select_model,
            messages=[
                {'role': 'user', 
                'content': prompt}
            ],
            stream=True # 设置为True以启用流式传输
        )

        # 打印响应内容
        for chunk in response:
            print(chunk.choices[0].delta.content, end='',flush=True)
    except Exception as e:
        print(f"Error: {e}")
        return None 



"""硅基流动支持的推理模型
deepseek-ai/DeepSeek-R1
Pro/deepseek-ai/DeepSeek-R1
deepseek-ai/DeepSeek-R1-Distill-Llama-70B
deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
deepseek-ai/DeepSeek-R1-Distill-Llama-8B
deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
Pro/deepseek-ai/DeepSeek-R1-Distill-Llama-8B
Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
"""

# 推理模型
def get_siliconflowe_inference_respons(select_model="deepseek-ai/DeepSeek-R1", prompt="奥运会的传奇名将有哪些？"):
    try:
        # 发送请求
        print("请求中...")

        # 创建OpenAI客户端
        url = 'https://api.siliconflow.cn/v1/'
        api_key = 'sk-bbokuaxjdsshoqtibaikradapkbhqgcsetdyjyvtheldbwbr'

        client = OpenAI(
            base_url=url,
            api_key=api_key
        )

        # 发送带有流式输出的请求
        content = ""
        reasoning_content=""
        messages = [
            {"role": "user", "content": prompt}
        ]
        response = client.chat.completions.create(
            model=select_model,
            messages=messages,
            stream=True,  # 启用流式输出
            max_tokens=4096
        )
        # 逐步接收并处理响应
        flag_one = True
        flag_two = True
        for chunk in response:
            if chunk.choices[0].delta.reasoning_content:
                if flag_one:
                    print("思维链内容输出：\n")
                    flag_one = False
                print(chunk.choices[0].delta.reasoning_content, end='',flush=True)
                reasoning_content += chunk.choices[0].delta.reasoning_content
                # print(f"正式回答：{reasoning_content}", end='',flush=True)
            if chunk.choices[0].delta.content:
                if flag_two:
                    print("\n最终回答：")
                    flag_two = False
                print(chunk.choices[0].delta.content, end='',flush=True)
                content += chunk.choices[0].delta.content
                # print(f"思考内容：{content}", end='',flush=True)

        # Round 2
        messages.append({"role": "assistant", "content": content})
        messages.append({'role': 'user', 'content': "继续"})
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1",
            messages=messages,
            stream=True
        )
    # 逐步接收并处理响应

    except Exception as e:
        print(f"Error: {e}")
        return None 





"""硅基流动支持的视觉理解模型
Qwen 系列：
Qwen/Qwen2-VL-72B-Instruct
Pro/Qwen/Qwen2-VL-7B-Instruct
Qwen/QVQ-72B-Preview
InternVL 系列：
OpenGVLab/InternVL2-Llama3-76B  NO used
OpenGVLab/InternVL2-26B
Pro/OpenGVLab/InternVL2-8B
DeepseekVL2 系列：
deepseek-ai/deepseek-vl2
"""
def compress_image(image_path, max_size=3800, quality=85):
    """压缩图片尺寸和质量"""
    try:
        img = Image.open(image_path)
        
        # 调整尺寸
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0]*ratio), int(img.size[1]*ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # 转换格式并压缩质量
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()
    except Exception as e:
        print(f"压缩图片出错: {e}")
        return None

def get_image_base64_basic(image_path):
    """获取图片base64编码,不带压缩功能的基础版"""
    try:
        # 打开图像文件
        with open(image_path, 'rb') as image_file:
            # 读取图像数据
            image_data = image_file.read()
            # 将图像数据编码为Base64字符串
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return base64_data
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_image_base64(image_path):
    """获取图片base64编码,带压缩功能"""
    try:
        # 先压缩图片
        compressed_data = compress_image(image_path)
        if not compressed_data:
            return None
            
        # 检查压缩后大小
        if len(compressed_data) > 4*1024*1024:  # 4MB二进制 ≈ 5.3MB base64
            print(f"警告: 图片 {os.path.basename(image_path)} 压缩后仍较大 ({len(compressed_data)/1024/1024:.2f}MB)")
            
        base64_data = base64.b64encode(compressed_data).decode('utf-8')
        return base64_data
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_siliconflow_vision_cc_response(select_model="Qwen/Qwen2-VL-72B-Instruct", prompt="描述图片内容", image_path_list=[]):
    try:
        # 预处理所有图片
        base64_images = []
        for path in image_path_list:
            base64_str = get_image_base64(path)
            if base64_str:
                base64_images.append(base64_str)
            else:
                print(f"图片 {path} 处理失败")
                return None

        # 创建OpenAI客户端
        client = OpenAI(
            api_key="sk-bbokuaxjdsshoqtibaikradapkbhqgcsetdyjyvtheldbwbr",
            base_url="https://api.siliconflow.cn/v1"
        )

        # 构造消息时使用预处理后的base64
        response_messages = [{
            "role": "user",
            "content": []
        }]

        for base64_str in base64_images:
            response_messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_str}",
                    # "detail": "low"  # 强制使用低细节模式减少数据量
                }
            })

        response_messages[0]["content"].append({
            "type": "text",
            "text": prompt
        })

        # 发送请求（保持原有逻辑）
        print("请求中...")
        response = client.chat.completions.create(
            model=select_model,
            messages=response_messages,
            stream=True
        )

        # 处理响应（保持原有逻辑）
        for chunk in response:
            chunk_message = chunk.choices[0].delta.content
            print(chunk_message, end='', flush=True)
            # chunk_messages += chunk.choices[0].delta.reasoning_content
        # return chunk_messages
    except Exception as e:
        print(f"Error: {e}")
        return None




if __name__ == "__main__":

    # 调用对话模型
    if False:
        get_siliconflow_chat_response(select_model="THUDM/glm-4-9b-chat",prompt="你好,帮我找一下openai的官网")
    

    # 调用推理模型
    if  False:  
        get_siliconflowe_inference_respons(select_model="deepseek-ai/DeepSeek-R1", prompt="奥运会的传奇名将有哪些？")

    # 调用视觉理解模型，
    # Pro/Qwen/Qwen2-VL-7B-Instruct表述较好能识别出是宜家地点，响应与deepseek-ai/deepseek-vl2、Pro/OpenGVLab/InternVL2-8B一样比较快
    # Qwen/QVQ-72B-Preview模型表述内容更详细，但是响应速度较慢
    # OpenGVLab/InternVL2-26B会根据需求分条列举
    # print(get_image_base64(two_pic[0]))
    if False:
        tips = "描述图片内容："
        get_siliconflow_vision_cc_response(select_model="Pro/OpenGVLab/InternVL2-8B", prompt=tips, image_path_list=one_pic)
    
    if False:
        tips = """假如你是一名专业的影像画质评测工程师,
            请从亮度、对比度、清晰度、色调等专业角度比较两张图片差异, 用中文回复,
            一句话总结概括内容, 不要换行，不要超过100字。"""

        get_siliconflow_vision_cc_response(select_model="OpenGVLab/InternVL2-26B", prompt=tips, image_path_list=two_pic)
    
    # 调用视觉理解模型，以类的形式调用
    if True:
        llm = CustomLLM_Siliconflow()
        tips = """假如你是一名专业的影像画质评测工程师,
        请从亮度、对比度、清晰度、色调等专业角度比较两张图片差异, 用中文回复,
        一句话总结概括内容, 不要换行，不要超过100字。"""
        model = "Pro/OpenGVLab/InternVL2-8B"
        response = llm(select_model=model, prompt=tips, image_path_list=two_pic)
        print(response)


    
