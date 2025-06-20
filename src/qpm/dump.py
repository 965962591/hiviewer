import os
import subprocess
import multiprocessing
import shutil


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
    在测试文件夹中新建4个文件夹, 将图片平均复制到其中,
    使用4进程同时处理,
    完成后将.xml文件复制回测试文件夹并删除临时文件夹。
    """
    # 使用4进程同时处理,
    num_processes = 4
    if not os.path.isfile(dptool_exe):
        print(f"错误: 可执行文件未找到 {dptool_exe}")
        return
    if not os.path.isdir(folder_path):
        print(f"错误: 目录未找到 {folder_path}")
        return

    # 筛选出没有对应 .xml 文件的文件
    files_in_folder = os.listdir(folder_path)
    xml_files = {
        os.path.splitext(f)[0] for f in files_in_folder if f.lower().endswith(".xml")
    }
    files_to_process = [
        f
        for f in files_in_folder
        if os.path.isfile(os.path.join(folder_path, f))
        and not f.lower().endswith(".xml")
        and os.path.splitext(f)[0] not in xml_files
    ]

    if not files_to_process:
        print(f"文件夹 {folder_path} 中没有新的文件可处理。")
        return

    batch_folders = [
        os.path.join(folder_path, f"batch_{i}") for i in range(num_processes)
    ]
    for folder in batch_folders:
        os.makedirs(folder, exist_ok=True)

    for i, filename in enumerate(files_to_process):
        shutil.copy(
            os.path.join(folder_path, filename),
            os.path.join(batch_folders[i % num_processes], filename),
        )

    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.starmap(run_dptool, [(dptool_exe, folder) for folder in batch_folders])

    print("所有进程处理完毕，开始清理...")

    # 首先，将所有 .xml 文件复制出来
    for folder in batch_folders:
        if os.path.isdir(folder):
            for filename in os.listdir(folder):
                if filename.lower().endswith(".xml"):
                    shutil.copy(os.path.join(folder, filename), folder_path)
    
    # 然后，删除所有临时文件夹
    for folder in batch_folders:
        if os.path.isdir(folder):
            try:
                shutil.rmtree(folder)
            except OSError as e:
                print(f"删除文件夹 {folder} 时出错: {e}")
    print("清理完成。")


# 示例调用
if __name__ == "__main__":
    dptool_exe = r"C:/Qualcomm/Chromatix7/7.3.01.36/Chromatix.exe"
    folder_path = r"D:/Tuning/O19/0_pic/02_IN_pic/2025.6.19-IN-一供验证 ISP/NOMAL/O19"
    process_images_in_folder(dptool_exe, folder_path)
