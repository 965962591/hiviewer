import os
import subprocess
import multiprocessing
import shutil
import configparser
from pathlib import Path
PARSE_CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "parse.ini"

def get_process_counts():
    config_path = PARSE_CONFIG_FILE.as_posix()
    config = configparser.ConfigParser()
    dump_processes = 1

    config_dir = os.path.dirname(config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    if not os.path.exists(config_path):
        config["settings"] = {
            "dump_processes": str(dump_processes)
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

    config.read(config_path, encoding="utf-8")
    dump_processes = config.getint("settings", "dump_processes", fallback=4)

    return dump_processes


def run_dptool(dptool_exe, folder_path):
    """
    在单个文件夹上运行 dptool.exe。
    """
    command = [
        dptool_exe,
        "-DbgDataDump",
        "-inputFolder",
        folder_path,
        "-outputFolder",
        folder_path,
        "-format",
        "xml",
    ]
    print(f"正在为文件夹 {folder_path} 运行命令...")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"成功处理文件夹: {folder_path}")
    except subprocess.CalledProcessError as e:
        print(f"处理文件夹 {folder_path} 时出错: {e.stderr}")
    except FileNotFoundError:
        print(f"错误: 找不到可执行文件 {dptool_exe}")


def process_images_in_folder(dptool_exe, folder_path):
    """
    在测试文件夹中新建文件夹, 将图片平均复制到其中,
    使用多进程同时处理,
    完成后将.xml文件复制回测试文件夹并删除临时文件夹。
    """
    if not os.path.isfile(dptool_exe):
        print(f"错误: 可执行文件未找到 {dptool_exe}")
        return
    if not os.path.isdir(folder_path):
        print(f"错误: 目录未找到 {folder_path}")
        return

    # --- 1. 整合之前运行留下的状态 ---
    print("正在检查并整合之前运行的状态...")
    existing_batch_folders = [
        os.path.join(folder_path, d)
        for d in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, d)) and d.startswith("batch_")
    ]

    if existing_batch_folders:
        for folder in existing_batch_folders:
            print(f"正在处理旧的批处理文件夹: {os.path.basename(folder)}")
            for filename in os.listdir(folder):
                if filename.lower().endswith(".xml"):
                    source_path = os.path.join(folder, filename)
                    dest_path = os.path.join(folder_path, filename)
                    try:
                        # 移动XML文件回主文件夹，如果已存在则覆盖
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        shutil.move(source_path, dest_path)
                        print(f"  已将 {filename} 移回主文件夹。")
                    except Exception as e:
                        print(f"  移动 {filename} 时出错: {e}")
            
            # 移动完XML后，删除整个旧的批处理文件夹
            try:
                shutil.rmtree(folder)
                print(f"  已删除旧的批处理文件夹: {os.path.basename(folder)}")
            except OSError as e:
                print(f"  删除文件夹 {folder} 时出错: {e}")
    print("状态整合完成。")

    # --- 2. 基于当前状态确定需要处理的文件 ---
    num_processes = get_process_counts()
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.heic', '.heif']
    
    other_files = {}
    xml_basenames = set()
    for f in os.listdir(folder_path):
        if not os.path.isfile(os.path.join(folder_path, f)):
            continue
        
        basename, ext = os.path.splitext(f)
        if ext.lower() == ".xml":
            xml_basenames.add(basename)
        elif ext.lower() in image_extensions:
            other_files[basename] = f
            
    files_to_process = [
        filename
        for basename, filename in other_files.items()
        if basename not in xml_basenames
    ]

    if not files_to_process:
        print(f"文件夹 {folder_path} 中没有新的图片文件可处理。")
        return

    # --- 3. 分配任务并执行 ---
    # 如果图片数量小于配置的进程数，则使用图片数量作为进程数
    actual_processes = min(num_processes, len(files_to_process))
    print(f"找到 {len(files_to_process)} 个新文件，将使用 {actual_processes} 个进程处理。")
    batch_folders = [os.path.join(folder_path, f"batch_{i}") for i in range(actual_processes)]
    for folder in batch_folders:
        os.makedirs(folder, exist_ok=True)

    for i, filename in enumerate(files_to_process):
        shutil.copy(
            os.path.join(folder_path, filename),
            os.path.join(batch_folders[i % actual_processes], filename),
        )

    with multiprocessing.Pool(processes=actual_processes) as pool:
        pool.starmap(run_dptool, [(dptool_exe, folder) for folder in batch_folders])

    # --- 4. 清理本次运行的临时文件 ---
    print("所有进程处理完毕，开始清理...")
    for folder in batch_folders:
        if os.path.isdir(folder):
            for filename in os.listdir(folder):
                if filename.lower().endswith(".xml"):
                    source_path = os.path.join(folder, filename)
                    dest_path = os.path.join(folder_path, filename)
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    shutil.move(source_path, dest_path)
            try:
                shutil.rmtree(folder)
            except OSError as e:
                print(f"删除文件夹 {folder} 时出错: {e}")
    print("清理完成。")


# 示例调用
if __name__ == "__main__":
    dptool_exe = r"C:/Qualcomm/Chromatix7/7.3.01.36/Chromatix.exe"
    folder_path = r"D:/Tuning/O19/0_pic/02_IN_pic/2025.6.18自测图/O19_改后"
    process_images_in_folder(dptool_exe, folder_path)
