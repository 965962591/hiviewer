
import os

def print_directory_structure(start_path, padding="", exclude_extensions=None, exclude_folders=None):
    """
    打印指定文件夹的目录结构，可以选择排除特定文件格式和文件夹
    :param start_path: 起始文件夹路径
    :param padding: 用于缩进的字符串
    :param exclude_extensions: 要排除的文件扩展名列表（如 ['.txt', '.jpg']）
    :param exclude_folders: 要排除的文件夹名列表（如 ['subfolder1', 'subfolder2']）
    """
    # 获取当前目录下的所有文件和文件夹
    entries = sorted(os.listdir(start_path))
    

    for i, entry in enumerate(entries):
        # 构造完整的路径
        full_path = os.path.join(start_path, entry)
        
        # 检查是否在排除的文件夹列表中
        if exclude_folders and entry in exclude_folders:
            continue
        
        # 判断是否是文件夹
        if os.path.isdir(full_path):
            # 判断是否是最后一个条目
            is_last = i == len(entries) - 1
            
            # 打印文件夹
            print(f"{padding}{'└──> ' if is_last else '├──> '}{entry}")

            
            # 递归打印子文件夹的内容
            new_padding = padding + "│    "
            print_directory_structure(full_path, new_padding, exclude_extensions, exclude_folders)
        else:
            # 如果是文件，检查扩展名是否符合过滤条件
            if exclude_extensions and any(full_path.endswith(ext) for ext in exclude_extensions):
                continue
            
            # 判断是否是最后一个条目
            is_last = i == len(entries) - 1
            
            # 打印文件
            print(f"{padding}{'└── ' if is_last else '├── '}{entry}")



def print_directory_structure_plus(start_path, padding="", exclude_extensions=None, exclude_folders=None):
    """
    打印指定文件夹的目录结构，可以选择排除特定文件格式和文件夹
    :param start_path: 起始文件夹路径
    :param padding: 用于缩进的字符串
    :param exclude_extensions: 要排除的文件扩展名列表（如 ['.txt', '.jpg']）
    :param exclude_folders: 要排除的文件夹名列表（如 ['subfolder1', 'subfolder2']）
    """
    # 获取当前目录下的所有文件和文件夹
    entries = sorted(os.listdir(start_path))
    
    # 分离文件夹和文件
    folders = [entry for entry in entries if os.path.isdir(os.path.join(start_path, entry))]
    files = [entry for entry in entries if os.path.isfile(os.path.join(start_path, entry))]

    # 先打印文件夹
    for i, folder in enumerate(folders):
        full_path = os.path.join(start_path, folder)
        
        # 检查是否在排除的文件夹列表中
        if exclude_folders and folder in exclude_folders[0]:
            continue
        
        # 判断是否是最后一个条目
        is_last = i == len(folders) - 1
        
        # 打印文件夹
        print(f"{padding}{'├──> ' if is_last else '├──> '}{folder}")
        
        # 递归打印子文件夹的内容
        new_padding = padding + "│    "
        print_directory_structure(full_path, new_padding, exclude_extensions[1], exclude_folders[1])

    # 后打印文件
    for i, file in enumerate(files):
        full_path = os.path.join(start_path, file)
        
        # 检查扩展名是否符合过滤条件
        if exclude_extensions[0] and any(full_path.endswith(ext) for ext in exclude_extensions[0]):
            continue
        
        # 判断是否是最后一个条目
        is_last = i == len(files) - 1

        # 打印文件
        print(f"{padding}{'└── ' if is_last else '├── '}{file}")
        


# 打印指定文件夹的目录结构
if __name__ == "__main__":
    # exclude_extensions_input = input("请输入文件夹路径: ")
    exclude_extensions_input = "D:\Image_process\hiviewer"
    exclude_files = [".py", ".md", ".ini", ".png", ".json", "icon", ".exe", ".lng", ".db", ".dll",".ico",".jpg",".svg",".gif",".ttf"]   # 二级目录排除的文件
    exclude_files_plus = [".png", ".json", "icon", ".exe", ".lng", ".db", ".dll",".ico",".jpg",".svg",".gif",".ttf"]     # 一级目录要排除的文件
    exclude_folders_plus = ["__pycache__",".git","jpegr_lossless_rotator","hiviewer.egg-info"]
    exclude_folders = ["__pycache__", ".git", "jpegr_lossless_rotator", "hiviewer.egg-info","pic","output"] 

    print(f"\nhiviewer")
    print_directory_structure_plus(exclude_extensions_input, exclude_extensions=[exclude_files_plus,exclude_files], exclude_folders=[exclude_folders_plus,exclude_folders])

