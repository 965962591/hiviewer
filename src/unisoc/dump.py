import os
import subprocess


def run_iqttool(iqttool_exe, folder_path):
    """
    在单个文件夹上运行 iqttool.exe。
    """
    command = [
        iqttool_exe,
        "-cmd", 
        "EXIFTXT",
        "-path",
        folder_path,
    ]
    print(f"正在为文件夹 {folder_path} 运行命令...")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"成功处理文件夹: {folder_path}")
    except subprocess.CalledProcessError as e:
        print(f"处理文件夹 {folder_path} 时出错: {e.stderr}")
    except FileNotFoundError:
        print(f"错误: 找不到可执行文件 {dptool_exe}")






# 示例调用
if __name__ == "__main__":
    dptool_exe = r"D:/Tuning/01_Unisoc/ViviMagic_TOOL_V1.5_R1.W25.2502/plugins/3aTool/IQT.exe"
    folder_path = r"D:/Tuning/C3Z/03_pic/20250819_20.18.11"
    
    run_iqttool(dptool_exe, folder_path)

