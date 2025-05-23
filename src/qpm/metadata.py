# -*- coding: utf-8 -*-
import os
import subprocess
import argparse 
from parse import parse_main
#批量解析函数
def process_images_in_folder(chromatix_exe, folder_path):
    # 检查文件和目录是否存在
    if not os.path.isfile(chromatix_exe):
        print(f"Error: Executable not found at {chromatix_exe}")
        return
    if not os.path.isdir(folder_path):
        print(f"Error: Directory not found at {folder_path}")
        return
    output_path = folder_path
    # 构建命令
    command = [
        chromatix_exe,
        "-DbgDataDump",
        "-inputFolder", folder_path,
        "-outputFolder", output_path,
        "-format", "xml"
    ]
    print(f"Running command: {command}")
    
    # 执行命令
    subprocess.run(command)


if __name__ == "__main__":
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='处理图片元数据')
    parser.add_argument('--chromatix', required=True, help='Chromatix工具的路径')
    parser.add_argument('--folder', required=True, help='要处理的图片文件夹路径')
    print("正在处理metadata数据，请稍等")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 从参数中获取路径
    chromatix_exe = args.chromatix
    folder_path = args.folder
    
    # 调用处理函数
    print("正在使用高通工具处理metadata数据，请稍等...")
    process_images_in_folder(chromatix_exe, folder_path)
    print("高通工具处理metadata数据完成，正在从metadata数据解析成提取关键信息，请稍等...")
    parse_main(folder_path)
    # input("按任意键继续...")