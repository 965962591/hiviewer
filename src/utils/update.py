# -*- coding: utf-8 -*-
import os
import sys
import psutil
import shutil
import hashlib
import zipfile
import requests
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMessageBox, QProgressDialog)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon, QCursor


"""设置本项目的入口路径,全局变量BasePath"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if True:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))  

# 更新类
class Updater:
    def __init__(self):
        self.proxy_prefix = "https://ghproxy.net/"
        self.github_url = "https://api.github.com/repos/diamond-cz/Hiviewer_releases/releases/latest"
        self.download_path = os.path.join(BasePath, "downloads")
        self.install_path = "."
        self.update_success = False
        self.version_file = os.path.join(BasePath, "config", "version.ini")  # 添加版本文件路径
        self.current_version = self._read_version()  # 从文件读取当前版本
        self.main_executable = "hiviewer.exe"  # 添加主程序可执行文件名
        # 检查文件是否存在，如果不存在则创建并写入默认版本号
        if not os.path.exists(self.version_file):
            with open(self.version_file, 'w') as f:
                f.write('release-v1.0.0')   
    def parse_version(self, version_str):
        """解析版本号字符串为可比较的元组"""
        # 移除 'release-v' 或 'release-' 前缀
        version_str = version_str.replace('release-v', '').replace('release-', '')
        # 分割版本号并转换为整数
        try:
            return tuple(map(int, version_str.split('.')))
        except ValueError:
            return (0, 0, 0)  # 解析失败时返回默认值

    def _read_version(self):
        """从version.ini文件读取版本号"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return "release-v1.0.0"  # 默认版本号
        except Exception as e:
            print(f"读取版本文件失败: {e}")
            return "release-v1.0.0"  # 读取失败时返回默认版本

    def _update_version_file(self, new_version):
        """更新version.ini文件中的版本号"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                f.write(new_version)
            print(f"版本文件已更新为: {new_version}")
        except Exception as e:
            print(f"更新版本文件失败: {e}")

    def check_for_updates(self):
        """检查GitHub上是否有新版本"""
        try:
            response = requests.get(self.github_url,timeout=5)
            response.raise_for_status()
            latest_release = response.json()
            self.latest_version = latest_release["tag_name"]  # 保存最新版本号
            
            # 比较版本号
            if self.parse_version(self.latest_version) > self.parse_version(self.current_version):
                # 修改这里：使用assets中的zip文件下载地址
                for asset in latest_release["assets"]:
                    if asset["name"].endswith(".zip"):
                        download_url = f"{self.proxy_prefix}{asset['browser_download_url']}"
                        return download_url, self.latest_version
                # 如果没有找到zip文件，返回None
                print("[check_for_updates]-->未找到可下载的zip文件")
                return None, None
            else:
                print("[check_for_updates]-->当前已是最新版本")
                return None, None
                
        except requests.RequestException as e:
            print(f"[check_for_updates]-->检查更新失败: {e}")
            return None, None

    def download_update(self, download_url):
        """下载最新版本的zip文件并显示进度"""
        try:
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)
            
            zip_path = os.path.join(self.download_path, "latest.zip")
            
            # 检查本地是否存在完整的zip文件
            if os.path.exists(zip_path):
                # 直接移除现有的安装包
                os.remove(zip_path)

            # 下载新的更新包
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            return zip_path, response, total_size
            
        except Exception as e:
            print(f"下载更新失败: {e}")
            return None, None, 0

    def is_program_running(self):
        """检查程序是否正在运行"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.main_executable:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def install_update(self, zip_path):
        """解压并安装更新"""
        try:
            # 创建临时解压目录
            temp_dir = os.path.join(self.download_path, "temp")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 获取解压后的主目录
            extracted_dir = next(Path(temp_dir).iterdir())
            
            # 检查程序是否在运行
            if self.is_program_running():
                # 只删除临时解压目录，保留下载的zip文件
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return "PROGRAM_RUNNING"
            
            # 复制新文件到安装目录
            self._copy_tree(str(extracted_dir), self.install_path)
            
            # 更新成功后才完全清理并更新版本文件
            self._cleanup(force=True)
            self.update_success = True
            self._update_version_file(self.latest_version)  # 更新版本文件
            return True
        except Exception as e:
            print(f"安装更新失败: {e}")
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
        src_files = set(os.listdir(src))
        dst_files = set(os.listdir(dst)) if os.path.exists(dst) else set()

        # 处理源目录中的文件和目录
        for item in src_files:
            src_path = os.path.join(src, item)
            dst_path = os.path.join(dst, item)

            if os.path.isdir(src_path):
                # 如果是目录，递归处理
                if not os.path.exists(dst_path):
                    os.makedirs(dst_path)
                self._copy_tree(src_path, dst_path)
            else:
                # 如果是文件，检查是否需要更新
                if not os.path.exists(dst_path):
                    # 目标文件不存在，直接复制
                    print(f"新增文件: {dst_path}")
                    shutil.copy2(src_path, dst_path)
                else:
                    # 文件都存在，比较MD5
                    src_md5 = get_file_md5(src_path)
                    dst_md5 = get_file_md5(dst_path)
                    if src_md5 != dst_md5:
                        print(f"更新文件: {dst_path}")
                        shutil.copy2(src_path, dst_path)
                    else:
                        print(f"文件未变更: {dst_path}")

        # 保留目标目录中独有的文件
        for item in dst_files - src_files:
            dst_path = os.path.join(dst, item)
            print(f"保留本地文件: {dst_path}")

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
            print(f"清理临时文件失败: {e}")


# 进度条显示
class UpdaterGUI:
    """GUI处理类，将界面逻辑从主业务逻辑中分离"""
    def __init__(self, app_icon_path, parent=None):
        self.app_icon = QIcon(app_icon_path)
        self.msg_box = QMessageBox()
        self.msg_box.setWindowIcon(self.app_icon)
        if parent:
            self.msg_box.setParent(parent)
        
    def show_message(self, title, text, icon_type=QMessageBox.Information, buttons=QMessageBox.Ok):
        """统一的消息框显示方法"""
        self.msg_box.setIcon(icon_type)
        self.msg_box.setWindowTitle(title)
        self.msg_box.setText(text)
        self.msg_box.setStandardButtons(buttons)
        return self.msg_box.exec_()

    def create_progress_dialog(self, title, text, cursor_pos, parent=None):
        """创建进度对话框"""
        progress = QProgressDialog(text, "取消", 0, 100, parent)
        progress.setWindowIcon(self.app_icon)
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.resize(400, 120)
        progress.move(cursor_pos.x() - 200, cursor_pos.y() - 60)
        progress.canceled.connect(progress.close)
        return progress


""" 全局函数区域
----------------------------------------------------------------------------------------------------
"""
def download_with_progress(zip_path, response, total_size, progress_dialog):
    """下载文件并显示进度"""
    try:
        with open(zip_path, 'wb') as f:
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=32768):
                if progress_dialog.wasCanceled():
                    return "canceled"
                    
                if chunk:
                    downloaded_size += len(chunk)
                    f.write(chunk)
                    progress_value = int((downloaded_size / total_size) * 100)
                    if progress_value % 2 == 0:
                        progress_dialog.setValue(progress_value)
                        QApplication.processEvents()
        return "success"
    except Exception as e:
        print(f"下载错误: {e}")
        return "error"

def pre_check_update():
    """预检查更新函数，供主程序调用"""
    try:
        print("[pre_check_update]-->开始检查更新...")
        updater = Updater()
        download_url, version = updater.check_for_updates()
        if download_url:
            return version
        else:
            return False
    except Exception as e:
        print(f"预检查更新发生错误: {str(e)}")
        return False

# 主函数
def check_update(parent_window=None):
    """检查更新的主函数，供主程序调用"""
    try:
        icon_path = os.path.join(BasePath, "icons", "viewer_3.ico")
        gui = UpdaterGUI(icon_path, parent_window)
        updater = Updater()
        cursor_pos = QPoint(QCursor.pos())
        
        print("check_update()--开始检查更新...")
        download_url, version = updater.check_for_updates()
        
        if not download_url:
            gui.show_message(
                "更新检查",
                "当前已是最新版本" if version is None else "检查更新失败"
            )
            return False
            
        reply = gui.show_message(
            "发现新版本",
            f"发现新版本 {version}，是否更新？",
            QMessageBox.Question,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return False

        # 更新版本
        zip_path, response, total_size = updater.download_update(download_url)

        if not zip_path:
            gui.show_message("更新失败", "下载更新失败", QMessageBox.Critical)
            return False
        
        """下载新版本的逻辑"""
        if response is not None:
            progress = gui.create_progress_dialog("下载进度", "正在下载更新...", cursor_pos, parent_window)
            try:
                download_result = download_with_progress(zip_path, response, total_size, progress)
                if download_result != "success":
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    if download_result == "canceled":
                        print("下载已取消")
                        progress.close()
                        gui.show_message("更新取消", "下载已取消")
                        return False
                    else:
                        gui.show_message("更新失败", "下载过程中出错", QMessageBox.Critical)
                        return False
            except Exception as e:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                progress.close()
                gui.show_message("更新失败", f"下载过程中出错: {str(e)}", QMessageBox.Critical)
                return False
            finally:
                progress.close()


        """ 安装更新_该段逻辑独立出来打包成exe(./tools/installer.exe)调用"""
        reply = gui.show_message(
            "更新提示",
            f"当前版本{version} 已下载完毕, \n是否启用自动安装程序？",
            QMessageBox.Warning,
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            # installer.exe放在，默认使用window系统打开exe，该方法不适用于mac/libux
            program_path_main = os.path.join(BasePath, "installer.exe")
            if os.path.exists(program_path_main):
                os.startfile(program_path_main)
                return True
            else:
                # 适用当前目录下没有installer.exe的情况
                program_path = os.path.join(BasePath, "resource", "installer.exe")
                if os.path.exists(program_path):
                    os.startfile(program_path)
                    return True
                else:
                    return False
        else:
            return False
    except Exception as e:
        print(f"更新过程中发生错误: {str(e)}")
        if 'gui' in locals():
            gui.show_message("错误", f"更新过程中发生错误: {str(e)}", QMessageBox.Critical)
        return False

if __name__ == "__main__":
    # 当作为独立程序运行时的入口
    app = QApplication(sys.argv)
    check_update()
    sys.exit(app.exec_())
