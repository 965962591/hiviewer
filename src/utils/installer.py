import os
import time
import zipfile
import shutil
import hashlib
import psutil
import argparse    
import subprocess 
from pathlib import Path


class UpdateInstaller:
    def __init__(self, zip_path):
        # 初始化传入的压缩包路径
        self.zip_path = zip_path
        # 根据传入的压缩包路径初始化解压安装的其他路径
        self.download_path = os.path.dirname(self.zip_path)
        self.install_path = os.path.dirname(self.download_path)
        self.version_file = os.path.join(self.install_path, "config", "version.ini")  # 添加版本文件路径
        self.main_executable = "hiviewer.exe"  # 添加主程序可执行文件名
        self.latest_version = "release-v1.0.0"  # 初始化当前最新版本
        pass
        # 检查文件是否存在，如果不存在则创建并写入默认版本号

    def _update_version_file(self, new_version):
        """更新version.ini文件中的版本号"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                f.write(new_version)
            print(f"✅版本文件已更新为: {new_version}")
        except Exception as e:
            print(f"❌更新版本文件失败: {e}")

    def _read_version(self, version_file_path):
        """从version.ini文件读取版本号"""
        try:
            if os.path.exists(version_file_path):
                with open(version_file_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return "release-v1.0.0"  # 默认版本号
        except Exception as e:
            print(f"❌读取版本文件失败: {e}")
            return "release-v1.0.0"  # 读取失败时返回默认版本

    def is_program_running(self):
        """检查程序是否正在运行"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.main_executable:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def start_program_subprocess(self):
        """启动主程序"""
        try:
            program_path = os.path.join(self.install_path, self.main_executable)
            if os.path.exists(program_path):
                # 添加工作目录和shell参数
                subprocess.Popen(
                    program_path,
                    cwd=self.install_path,  # 设置工作目录
                    shell=True  # 使用shell执行
                )
            
                print(f"✅已启动程序: {self.main_executable}")
                return True
            else:
                print(f"❌程序文件不存在: {program_path}")
                return False
        except Exception as e:
            print(f"❌启动程序失败: {e}")
            return False
        
    def start_program(self):
        """启动主程序，os.startfile()是Windows特有的方法，如果需要在跨平台环境下运行，建议保留原来的subprocess.Popen方案"""
        try:
            program_path = os.path.join(self.install_path, self.main_executable)
            if os.path.exists(program_path):
                
                # 使用os.startfile启动程序
                os.startfile(program_path)
                
                # 等待5秒确保程序启动
                time.sleep(5)  
                print(f"✅已启动程序: {self.main_executable}")
                
                return True
            else:
                print(f"❌程序文件不存在: {program_path}")
                return False
        except Exception as e:
            print(f"❌启动程序失败: {e}")
            return False

    def force_close_program(self):
        """强制关闭正在运行的程序"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == self.main_executable:
                        proc.kill()  # 强制终止进程
                        print(f"✔️已强制关闭 {self.main_executable}")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            print(f"❌强制关闭程序失败: {e}")
            return False

    def install_update(self):
        """解压并安装更新"""
        try:

            if not os.path.exists(self.zip_path):
                print(f"❌没有可更新的安装包：{self.zip_path}")
                return False

            # 检查程序是否在运行，若在运行则强制关闭
            if self.is_program_running():
                # 尝试强制关闭程序
                if not self.force_close_program():
                    return "PROGRAM_RUNNING"
                
                # 等待进程完全退出
                time.sleep(1)  # 等待1秒确保进程完全退出

                # 如果程序仍在运行，返回错误
                if self.is_program_running():
                    print("❌无法强制关闭程序hiviewer.exe,请手动关闭后重试")
                    return "PROGRAM_RUNNING"

            # 创建临时解压目录
            temp_dir = os.path.join(self.download_path, "temp")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # 解压文件
            print(f"正在解压压缩包{self.zip_path}......")
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 获取解压后的主目录
            extracted_dir = next(Path(temp_dir).iterdir())
            
            # 获取解压后的版本路径,读取最新的版本号
            version_file_path = str(Path(str(extracted_dir)) / "config" / "version.ini")
            self.latest_version = self._read_version(version_file_path)
            print(f"✔️压缩包解压成功！")
            print(f"开始更新版本......")
            # 复制新文件到安装目录
            self._copy_tree(str(extracted_dir), self.install_path)
            # 更新版本文件
            self._update_version_file(self.latest_version)  

            # 更新成功后才完全清理并更新版本文件
            self._cleanup(force=False) # True

            return True
        
        except Exception as e:
            print(f"❌安装更新失败: {e}")
            # 发生错误时只清理临时解压目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return False

    def _copy_tree(self, src, dst):
        """递归复制文件树，实现智能增量更新
        - 通过MD5比较确定文件是否需要更新
        - 保留本地独有文件
        - 复制新增文件
        """
        def get_file_md5(filepath):
            """计算文件的MD5值"""
            md5 = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5.update(chunk)
            return md5.hexdigest()

        # 获取源目录和目标目录中的所有文件
        src_files = set(os.listdir(src.encode('utf-8').decode('utf-8')))
        dst_files = set(os.listdir(dst.encode('utf-8').decode('utf-8'))) if os.path.exists(dst) else set()

        # 处理源目录中的文件和目录
        for item in src_files:
            src_path = os.path.join(src.encode('utf-8').decode('utf-8'), item.encode('utf-8').decode('utf-8'))
            dst_path = os.path.join(dst.encode('utf-8').decode('utf-8'), item.encode('utf-8').decode('utf-8'))

            if os.path.isdir(src_path):
                # 如果是目录，递归处理
                if not os.path.exists(dst_path):
                    os.makedirs(dst_path.encode('utf-8').decode('utf-8'))
                self._copy_tree(src_path, dst_path)
            else:
                # 如果是文件，检查是否需要更新
                if not os.path.exists(dst_path):
                    # 目标文件不存在，直接复制
                    print(f"🚩新增文件: {dst_path}")
                    shutil.copy2(src_path, dst_path)
                else:
                    # 文件都存在，比较MD5
                    src_md5 = get_file_md5(src_path)
                    dst_md5 = get_file_md5(dst_path)
                    if src_md5 != dst_md5:
                        print(f"📍更新文件: {dst_path}")
                        shutil.copy2(src_path, dst_path)
                    else:
                        print(f"文件未变更: {dst_path}")

        # 保留目标目录中独有的文件
        for item in dst_files - src_files:
            dst_path = os.path.join(dst.encode('utf-8').decode('utf-8'), item.encode('utf-8').decode('utf-8'))
            print(f"⭕保留本地文件: {dst_path}")

    def _cleanup(self, force=False):
        """清理下载的文件和临时目录
        Args:
            force (bool): 如果为True，强制删除所有临时文件，包括下载的zip文件
        """
        try:
            if force and os.path.exists(self.download_path):
                shutil.rmtree(self.download_path)
            else:
                # 只清理临时解压目录
                temp_dir = os.path.join(self.download_path, "temp")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"❌清理临时文件失败: {e}")


"""全局函数"""

def start_program_subprocess(program_path=None, work_path=None, args=None):
    """启动主程序
    Args:
        program_path (str): 要启动的程序路径
        work_path (str): 工作目录
        args (list): 要传递给主程序的参数列表
    """
    try:
        if not program_path or not os.path.exists(program_path):
            print(f"❌程序文件不存在: {program_path}")
            return False
            
        # 构建命令列表
        command = program_path
        if args:
            # 确保args是列表类型，并正确处理字符串参数
            if isinstance(args, str):
                args = args.split()
            command = f"{command} {' '.join(args)}"
        
        process = subprocess.run(
            f'start /wait cmd /c {command}',  # /wait 等待新窗口关闭
            shell=True,
            text=True  # 将输出解码为字符串
        )


        print(f"✔️已启动程序: {program_path} 参数: {args}")
        return process  # 返回进程对象以便后续控制
    except Exception as e:
        print(f"❌启动程序失败: {e}")
        return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="-------------------------HiViewer 更新安装程序-------------------------",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  installer.exe -z latest.zip\n  installer.exe -c 1\n  installer.exe --help"
    )
    
    parser.add_argument(
        '-z', '--zip',
        dest='zip_path',
        required=False,  # 可填True强制必需
        type=str,        # 明确指定参数类型
        help='指定更新包路径（必需）'
    )

    parser.add_argument(
        '-c', '--console',
        dest='cmd_enable',
        type=int,  # 明确指定参数类型为整数
        choices=[0, 1],  # 限制输入值为0或1
        default=0,  # 默认值为0
        help='是否等待用户输入后退出黑窗口（0：不等待，1：等待）'
    )
    
    return parser.parse_args()

# 主函数
def installer(zip_path=None):
    """检查更新的主函数，供主程序调用"""
    try:
        
        if zip_path is None:
            args = parse_arguments()
            zip_path = args.zip_path
        
        # 安装更新
        updater = UpdateInstaller(zip_path) # 创建UpdateInstaller实例
        install_result = updater.install_update()

        if install_result == "PROGRAM_RUNNING":
            print("❗检测到hiviewer.exe 程序正在运行中,需要手动关闭")
            
        elif install_result:

            print("✔️安装包更新成功, 正在启动程序请稍后......")
            
            # 更新成功后启动程序
            updater.start_program()
            
        else:
            print("安装包更新失败")

    except Exception as e:
        print(f"安装过程中发生错误: {str(e)}")


def show_info():
    """在线生成ASCII码艺术字__https://www.bejson.com/text/ascii_art/"""
    print(f"""
     -----------------------------------------------------------.
    |    _   _   _                                              |
    |   | | | | (_) __   __ (_)   ___  __      __   ___   _ __  |
    |   | |_| | | | \ \ / / | |  / _ \ \ \ /\ / /  / _ \ | '__| |
    |   |  _  | | |  \ V /  | | |  __/  \ V  V /  |  __/ | |    |     
    |   |_| |_| |_|   \_/   |_|  \___|   \_/\_/    \___| |_|    |  
    |                                                           |                  
---------------------📍HiViewer 更新版本安装程序📍----------------------
✅程序正在执行中......
    """)



if __name__ == "__main__":
    """将该程序打包成exe可执行文件以供主函数调用"""

    # test
    if False:
        program_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"tools","installer.exe")
        work_path = os.path.dirname(os.path.abspath(__file__))
        zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"downloads","latest.zip")
        start_program_subprocess(program_path, work_path, f"-z {zip_path} -c 1")

    # 打印初始信息的ASCII艺术字
    show_info()

    if True:
        args = parse_arguments()
        zip_path_ = args.zip_path
        cmd_enable_ = args.cmd_enable

        if zip_path_ and os.path.exists(zip_path_):
            installer(zip_path_)
            if cmd_enable_:
                input("按 Enter 键退出...")  # 暂停黑窗口
        else:
            # 什么参数都不传的时候,默认使用当前项目文件下的相对路径安装包
            zip_path = os.path.join(".", "downloads", "latest.zip")
            installer(zip_path)
            input("按 Enter 键退出...")  # 暂停黑窗口
        


   
    
    
