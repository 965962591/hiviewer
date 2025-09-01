import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QCheckBox,
    QGridLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QLabel,
    QMenu,
    QInputDialog,
    QSplitter,
    QDialog,
    QLineEdit,
    QTextEdit,
    QDialogButtonBox,
    QComboBox,
    QHBoxLayout,
)
import subprocess
from PyQt5.QtGui import QIcon
import threading
from PyQt5.QtCore import QMetaObject, Qt, pyqtSignal, pyqtSlot, Q_ARG
import json
import os

icon_abs = False  # 全局标志位，控制路径类型

# 全局变量定义缓存目录
APP_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "cache")

class LogVerboseMaskApp(QWidget):
    # 创建关闭信号
    closed = pyqtSignal()
    COMMANDS_FILE = os.path.join(APP_CACHE_DIR, "commands.json")

    def __init__(self):
        super().__init__()
        # 确保缓存目录存在
        os.makedirs(APP_CACHE_DIR, exist_ok=True)
        self.specific_commands = self.load_commands()
        self.initUI()
        self.setup_logging()
        self.refresh_devices()  # 初始化时刷新设备列表

    def load_commands(self):
        """从文件加载命令"""
        # 确保缓存目录存在
        os.makedirs(APP_CACHE_DIR, exist_ok=True)
        if os.path.exists(self.COMMANDS_FILE):
            try: # 添加 try-except 块处理可能的 JSONDecodeError
                with open(self.COMMANDS_FILE, "r", encoding="utf-8") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                print(f"警告：无法解析 {self.COMMANDS_FILE}，将使用默认命令。")
                return self.get_default_commands() # 返回默认命令
        else:
            # 如果文件不存在，使用默认命令
            return self.get_default_commands() # 返回默认命令

    def get_default_commands(self): # 新增一个方法来返回默认命令
        """返回默认命令字典"""
        return {
            "HDR": [
                "adb shell setenforce 0",
                'adb shell "mkdir /data/local/tmp/morpho/image_refiner/dump -p"',
                'adb shell "chmod 777 /data/local/tmp/morpho/image_refiner/dump"',
                "adb shell setprop debug.morpho.image_refiner.enable 1",
                "adb shell setprop debug.morpho.image_refiner.dump 3",
                "adb shell setprop debug.morpho.image_refiner.dump_path /data/local/tmp/morpho/image_refiner/dump",
                "adb shell setprop debug.morpho.image_refiner.enable 1",
                "adb shell setprop debug.morpho.image_refiner.draw_logo 1",
            ],
            "超夜": [
                "adb shell setprop persist.vendor.camera.siq.dump 1",
                "adb shell setprop vendor.camera.siq.dump_input_output 1",
            ],
            "Kill": [
                "adb shell input keyevent 3",
                "adb shell \"for pid in $(ps -A | grep vendor.qti.camera.provider@2.7-service_64 | awk '{print $2}'); do kill $pid; done\"",
                "adb shell \"for pid in $(ps -A | grep android.hardware.camera.provider@2.4-service_64 | awk '{print $2}'); do kill $pid; done\"",
                "adb shell \"for pid in $(ps -A | grep cameraserver | awk '{print $2}'); do kill $pid; done\"",
                "adb shell \"for pid in $(ps -A | grep com.android.camera | awk '{print $2}'); do kill $pid; done\"",
                'adb shell "kill $(pidof camerahalserver)"',
                'adb shell "kill $(pidof cameraserver)"',
                "adb shell pkill camera*",
            ],
            "3A": [
                'adb shell "echo enable3ADebugData=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo enableTuningMetadata=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo dumpSensorEEPROMData=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo logCoreCfgMask=0x2780ba >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo reprocessDump=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
            ],
            "离线log": [
                'adb shell "echo enableAsciiLogging=1 >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo logWarningMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo logVerboseMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo logInfoMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo logConfigMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                'adb shell "echo logEntryExitMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
            ],
        }

    def save_commands(self):
        """将命令保存到文件"""
        # 确保缓存目录存在
        os.makedirs(APP_CACHE_DIR, exist_ok=True)
        try: # 添加 try-except 块处理可能的写入错误
            with open(self.COMMANDS_FILE, "w", encoding="utf-8") as file:
                json.dump(self.specific_commands, file, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"错误：无法写入配置文件 {self.COMMANDS_FILE}: {e}")
            QMessageBox.warning(self, "保存错误", f"""无法保存命令配置到:{self.COMMANDS_FILE}错误: {e}""")

    def refresh_devices(self):
        """刷新ADB设备列表"""
        try:
            # 使用 startupinfo 来隐藏命令行窗口
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ['adb', 'devices'], 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题
                devices = []
                for line in lines:
                    if line.strip() and '\t' in line:
                        device_id, status = line.strip().split('\t')
                        if status == 'device':  # 只添加已连接的设备
                            devices.append(device_id)
                            print(f"获取到设备: {device_id}")
                
                # 更新设备下拉列表
                self.device_combo.clear()
                if devices:
                    for device in devices:
                        self.device_combo.addItem(device)
                    self.device_combo.setCurrentIndex(0)
                    self.device_combo.setEnabled(True)  # 确保有设备时启用下拉列表
                else:
                    self.device_combo.addItem("未检测到设备")
                    self.device_combo.setEnabled(False)
            else:
                self.device_combo.clear()
                self.device_combo.addItem("ADB命令执行失败")
                self.device_combo.setEnabled(False)
        except Exception as e:
            self.device_combo.clear()
            self.device_combo.addItem(f"错误: {str(e)}")
            self.device_combo.setEnabled(False)

    def get_selected_device(self):
        """获取当前选中的设备ID"""
        current_text = self.device_combo.currentText()
        is_enabled = self.device_combo.isEnabled()
        print(f"当前选中的设备: '{current_text}', 下拉列表是否启用: {is_enabled}")
        
        if current_text in ["未检测到设备", "ADB命令执行失败"] or not is_enabled:
            print(f"设备选择无效，返回None")
            return None
        print(f"返回选中的设备: {current_text}")
        return current_text

    def switch_usb_mode(self, mode_name, usb_function):
        """切换USB模式"""
        selected_device = self.get_selected_device()
        if not selected_device:
            QMessageBox.warning(self, "设备错误", "请先选择有效的ADB设备！")
            return
        
        try:
            if usb_function:
                # 有USB功能参数的情况（文件传输或传输照片）
                command = f"adb -s {selected_device} shell svc usb setFunctions {usb_function}"
            else:
                # 仅充电模式（无参数）
                command = f"adb -s {selected_device} shell svc usb setFunctions"
            
            print(f"执行USB模式切换命令: {command}")
            
            # 执行命令
            # 使用 startupinfo 来隐藏命令行窗口
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                QMessageBox.information(self, "成功", f"USB模式已切换到: {mode_name}")
                print(f"USB模式切换成功: {mode_name}")
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                QMessageBox.warning(self, "执行失败", f"切换USB模式失败: {error_msg}")
                print(f"USB模式切换失败: {error_msg}")
                
        except Exception as e:
            error_msg = f"执行USB模式切换时出错: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            print(error_msg)

    def initUI(self):
        self.setWindowTitle("Bat脚本执行")
        self.resize(1200, 900)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon", "bat.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.mask_value = 0x00000000

        # 创建主布局
        main_layout = QVBoxLayout()

        # 创建设备选择区域
        device_layout = QHBoxLayout()
        device_label = QLabel("选择设备:")
        self.device_combo = QComboBox()
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_devices)
        
        # 添加USB功能切换按钮
        usb_label = QLabel("USB模式:")
        only_charge_button = QPushButton("仅充电")
        file_transfer_button = QPushButton("文件传输")
        photo_transfer_button = QPushButton("传输照片")
        
        # 连接按钮信号
        only_charge_button.clicked.connect(lambda: self.switch_usb_mode("仅充电", ""))
        file_transfer_button.clicked.connect(lambda: self.switch_usb_mode("文件传输", "mtp"))
        photo_transfer_button.clicked.connect(lambda: self.switch_usb_mode("传输照片", "ptp"))
        
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(refresh_button)
        device_layout.addWidget(usb_label)
        device_layout.addWidget(only_charge_button)
        device_layout.addWidget(file_transfer_button)
        device_layout.addWidget(photo_transfer_button)
        device_layout.addStretch()  # 添加弹性空间
        
        main_layout.addLayout(device_layout)

        # 创建 QSplitter
        splitter = QSplitter(Qt.Horizontal)

        # 创建显示数值的文本框
        self.mask_display = QTextEdit()
        splitter.addWidget(self.mask_display)

        # 将 QSplitter 添加到主布局
        main_layout.addWidget(splitter)

        # 创建水平布局以在同一行显示按钮
        button_layout = QHBoxLayout()

        # 创建运行按钮
        run_button = QPushButton("运行")
        run_button.clicked.connect(self.execute_adb_commands)
        button_layout.addWidget(run_button)

        # 创建批量执行按钮
        batch_run_button = QPushButton("批量执行")
        batch_run_button.clicked.connect(self.batch_execute_adb_commands)
        button_layout.addWidget(batch_run_button)

        # 创建新增按钮
        add_button = QPushButton("新增")
        add_button.clicked.connect(self.add_new_script)
        button_layout.addWidget(add_button)
        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)

        # 创建复选框布局
        grid_layout = QGridLayout()

        # 添加第一个标签
        script_label = QLabel("高通脚本：")
        grid_layout.addWidget(script_label, 0, 0, 1, 4)

        # 初始化脚本复选框列表
        self.script_checkboxes = []

        # 添加脚本复选框
        script_labels = [
            "Sensor",
            "Application",
            "IQ module",
            "IFace",
            "Utilities",
            "LMME",
            "ISP",
            "Sync",
            "NCS",
            "Post Processor",
            "MemSpy",
            "Metadata",
            "Image Lib",
            "Asserts",
            "AEC",
            "CPP",
            "Core",
            "AWB",
            "HAL",
            "HWI",
            "AF",
            "JPEG",
            "CHI",
            "DRQ",
            "Stats",
            "FD",
            "CSL",
            "FD",
        ]
        for i, label in enumerate(script_labels):
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(self.update_script_mask)
            row = (i // 4) + 1  # 从第1行开始
            col = i % 4
            grid_layout.addWidget(checkbox, row, col)
            self.script_checkboxes.append(checkbox)

        # 添加第二个标签
        command_label = QLabel("自定义脚本：")
        command_start_row = (len(script_labels) // 4) + 1
        grid_layout.addWidget(command_label, command_start_row, 0, 1, 4)  # 占据一整行

        # 初始化命令复选框列表
        self.command_checkboxes = []

        # 动态添加命令复选框
        command_checkboxes = list(self.specific_commands.keys())  # 从加载的命令中获取键
        for i, label in enumerate(command_checkboxes):
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(self.update_command_mask)
            checkbox.setContextMenuPolicy(Qt.CustomContextMenu)
            checkbox.customContextMenuRequested.connect(
                lambda pos, cb=checkbox: self.show_context_menu(pos, cb)
            )
            row = command_start_row + 1 + (i // 4)  # 从命令标签的下一行开始
            col = i % 4
            grid_layout.addWidget(checkbox, row, col)
            self.command_checkboxes.append(checkbox)

        main_layout.addLayout(grid_layout)
        self.setLayout(main_layout)

    def update_script_mask(self):
        """更新 script_label 下的复选框"""
        self.mask_value = 0x00000000
        commands = []
        # 定义每个标签对应的指令值
        command_values = [
            0x00000002,
            0x00000800,
            0x00200000,
            0x00000004,
            0x00001000,
            0x00400000,
            0x00000008,
            0x00002000,
            0x00800000,
            0x00000010,
            0x00004000,
            0x01000000,
            0x00000020,
            0x00008000,
            0x02000000,
            0x00000040,
            0x00010000,
            0x04000000,
            0x00000080,
            0x00020000,
            0x08000000,
            0x00000100,
            0x00040000,
            0x00080000,
            0x00000200,
            0x00100000,
            0x00000400,
            0x00100000,
        ]
        current_text = self.mask_display.toPlainText().split("\n")
        current_text = [line for line in current_text if line.strip()]  # 移除空行
        for i, checkbox in enumerate(self.script_checkboxes):
            command = f'adb shell "echo logVerboseMask=0x{command_values[i]:08X} >> /vendor/etc/camera/camxoverridesettings.txt"'
            if checkbox.isChecked():
                if i < len(command_values):
                    self.mask_value |= command_values[i]
                    if command not in current_text:
                        commands.append(command)
            else:
                if command in current_text:
                    current_text.remove(command)
        self.mask_display.setText("\n".join(current_text + commands))

    def update_command_mask(self):
        """更新 command_label 下的复选框"""
        commands = []
        current_text = self.mask_display.toPlainText().split("\n")
        current_text = [line for line in current_text if line.strip()]  # 移除空行
        # print(f"update_command_mask - 当前文本框内容: {current_text}")
        
        for checkbox in self.command_checkboxes:
            command_list = self.specific_commands.get(checkbox.text(), [])
            # print(f"update_command_mask - 复选框 '{checkbox.text()}' 状态: {checkbox.isChecked()}")
            # print(f"update_command_mask - 复选框 '{checkbox.text()}' 命令列表: {command_list}")
            
            if checkbox.isChecked():
                for command in command_list:
                    if command not in current_text:
                        # print(f"update_command_mask - 添加命令: {command}")

                        commands.append(command)
                    else:
                        print(f"update_command_mask - 命令已存在，跳过: {command}")
            else:
                for command in command_list:
                    if command in current_text:
                        # print(f"update_command_mask - 移除命令: {command}")
                        current_text.remove(command)
        
        final_commands = current_text + commands
        # print(f"update_command_mask - 最终命令列表: {final_commands}")
        self.mask_display.setText("\n".join(final_commands))

    @pyqtSlot()
    def show_success_message(self):
        QMessageBox.information(self, "成功", "脚本执行成功！")

    def setup_logging(self):
        """移除日志记录设置"""
        pass

    def write(self, message):
        """移除日志消息写入"""
        pass

    def execute_adb_commands(self):
        # 首先检查设备连接状态
        selected_device = self.get_selected_device()
        print(f"execute_adb_commands - 选中的设备: {selected_device}")
        if not selected_device:
            QMessageBox.warning(self, "设备错误", "请先选择有效的ADB设备！")
            return
        
        # 检查设备是否仍然连接
        try:
            # 使用 startupinfo 来隐藏命令行窗口
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ['adb', 'devices'], 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                devices = []
                for line in lines:
                    if line.strip() and '\t' in line:
                        device_id, status = line.strip().split('\t')
                        if status == 'device':
                            devices.append(device_id)
                
                if selected_device not in devices:
                    QMessageBox.warning(self, "设备错误", f"设备 {selected_device} 已断开连接，请重新选择设备！")
                    self.refresh_devices()
                    return
            else:
                QMessageBox.warning(self, "ADB错误", "无法获取设备列表，请检查ADB连接！")
                return
        except Exception as e:
            QMessageBox.warning(self, "ADB错误", f"检查设备状态时出错: {str(e)}")
            return

        def create_temp_bat(commands):
            """创建临时bat文件"""
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".bat", encoding="gbk"
            ) as f:
                f.write("@echo off\n")
                f.write("echo [INFO] 开始执行脚本...\n")
                f.write(f"echo [INFO] 目标设备: {selected_device}\n")
                f.write("\n".join(commands))
                f.write("\necho [INFO] 执行完成!\n")
                return f.name.replace("/", "\\")  # 确保Windows路径格式

        def run_commands_in_thread():
            # print(f"run_commands_in_thread - 开始收集命令，目标设备: {selected_device}")
            # 收集所有要执行的命令
            all_commands = []

            # ADB初始化命令（指定设备）
            all_commands.extend([
                f"adb -s {selected_device} root", 
                f"adb -s {selected_device} remount", 
                f"adb -s {selected_device} wait-for-device"
            ])

            # 添加文本框中的命令（指定设备）
            text_edit_commands = self.mask_display.toPlainText().split("\n")
            # print(f"run_commands_in_thread - 文本框中的命令: {text_edit_commands}")
            for cmd in text_edit_commands:
                if cmd.strip():
                    if cmd.startswith("adb shell"):
                        # 将 "adb shell" 替换为 "adb -s {selected_device} shell"
                        new_cmd = cmd.replace("adb shell", f"adb -s {selected_device} shell")
                        print(f"run_commands_in_thread - 替换命令: {cmd} -> {new_cmd}")
                        all_commands.append(new_cmd)
                    elif cmd.startswith("adb "):
                        # 对所有其他 adb 命令添加设备号
                        new_cmd = cmd.replace("adb ", f"adb -s {selected_device} ", 1)
                        print(f"run_commands_in_thread - 替换adb命令: {cmd} -> {new_cmd}")
                        all_commands.append(new_cmd)
                    else:
                        print(f"run_commands_in_thread - 直接添加命令: {cmd}")
                        all_commands.append(cmd)

            # 添加特定命令（指定设备）
            for checkbox in self.command_checkboxes:
                if checkbox.isChecked() and checkbox.text() in self.specific_commands:
                    # print(f"处理复选框 '{checkbox.text()}' 的命令")
                    for cmd in self.specific_commands[checkbox.text()]:
                        # print(f"原始命令: {cmd}")
                        if cmd.startswith("adb shell"):
                            # 将 "adb shell" 替换为 "adb -s {selected_device} shell"
                            new_cmd = cmd.replace("adb shell", f"adb -s {selected_device} shell")
                            # print(f"替换后命令: {new_cmd}")
                            all_commands.append(new_cmd)
                        elif cmd.startswith("adb "):
                            # 对所有其他 adb 命令添加设备号
                            new_cmd = cmd.replace("adb ", f"adb -s {selected_device} ", 1)
                            # print(f"替换adb命令: {cmd} -> {new_cmd}")
                            all_commands.append(new_cmd)
                        else:
                            # print(f"非adb命令，直接添加: {cmd}")
                            all_commands.append(cmd)

            # 添加查看配置文件的命令（指定设备）
            all_commands.append(
                f"adb -s {selected_device} shell cat /vendor/etc/camera/camxoverridesettings.txt"
            )

            # 生成临时bat文件
            # print(f"run_commands_in_thread - 最终命令列表: {all_commands}")
            bat_path = create_temp_bat(all_commands)

            try:
                # 执行bat文件
                # 使用 startupinfo 来隐藏命令行窗口
                startupinfo = None
                if hasattr(subprocess, 'STARTUPINFO'):
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                subprocess.run(
                    f'cmd /c "{bat_path}"', 
                    shell=True,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            finally:
                # 删除临时文件
                import os

                os.remove(bat_path)

            # 显示成功提示
            QMetaObject.invokeMethod(self, "show_success_message", Qt.QueuedConnection)

        # 创建并启动线程
        thread = threading.Thread(target=run_commands_in_thread)
        thread.start()

    def batch_execute_adb_commands(self):
        """批量执行ADB命令到所有连接的设备"""
        # 先刷新设备列表
        self.refresh_devices()
        
        # 获取当前连接的设备列表
        try:
            # 使用 startupinfo 来隐藏命令行窗口
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ['adb', 'devices'], 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                devices = []
                for line in lines:
                    if line.strip() and '\t' in line:
                        device_id, status = line.strip().split('\t')
                        if status == 'device':  # 只添加已连接的设备
                            devices.append(device_id)
                
                if not devices:
                    QMessageBox.warning(self, "设备错误", "未检测到任何已连接的ADB设备！")
                    return
                
                # 显示确认对话框
                device_list = "\n".join([f"• {device}" for device in devices])
                reply = QMessageBox.question(
                    self, 
                    "批量执行确认", 
                    f"检测到 {len(devices)} 台设备:\n{device_list}\n\n确定要在所有设备上执行脚本吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # 开始批量执行
                    self.start_batch_execution(devices)
                else:
                    print("用户取消了批量执行")
                    
            else:
                QMessageBox.warning(self, "ADB错误", "无法获取设备列表，请检查ADB连接！")
                return
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取设备列表时出错: {str(e)}")
            return

    def start_batch_execution(self, devices):
        """开始批量执行到多个设备"""
        def batch_execute_in_thread():
            total_devices = len(devices)
            success_count = 0
            failed_devices = []
            
            for i, device in enumerate(devices, 1):
                try:
                    print(f"[{i}/{total_devices}] 正在设备 {device} 上执行脚本...")
                    
                    # 收集要执行的命令
                    all_commands = []
                    
                    # ADB初始化命令（指定设备）
                    all_commands.extend([
                        f"adb -s {device} root", 
                        f"adb -s {device} remount", 
                        f"adb -s {device} wait-for-device"
                    ])

                    # 添加文本框中的命令（指定设备）
                    text_edit_commands = self.mask_display.toPlainText().split("\n")
                    for cmd in text_edit_commands:
                        if cmd.strip():
                            if cmd.startswith("adb shell"):
                                # 将 "adb shell" 替换为 "adb -s {device} shell"
                                new_cmd = cmd.replace("adb shell", f"adb -s {device} shell")
                                all_commands.append(new_cmd)
                            elif cmd.startswith("adb "):
                                # 对所有其他 adb 命令添加设备号
                                new_cmd = cmd.replace("adb ", f"adb -s {device} ", 1)
                                all_commands.append(new_cmd)
                            else:
                                all_commands.append(cmd)

                    # 添加特定命令（指定设备）
                    for checkbox in self.command_checkboxes:
                        if checkbox.isChecked() and checkbox.text() in self.specific_commands:
                            # print(f"批量执行 - 处理复选框 '{checkbox.text()}' 的命令")
                            for cmd in self.specific_commands[checkbox.text()]:
                                print(f"批量执行 - 原始命令: {cmd}")
                                if cmd.startswith("adb shell"):
                                    # 将 "adb shell" 替换为 "adb -s {device} shell"
                                    new_cmd = cmd.replace("adb shell", f"adb -s {device} shell")
                                    # print(f"批量执行 - 替换后命令: {new_cmd}")
                                    all_commands.append(new_cmd)
                                elif cmd.startswith("adb "):
                                    # 对所有其他 adb 命令添加设备号
                                    new_cmd = cmd.replace("adb ", f"adb -s {device} ", 1)
                                    # print(f"批量执行 - 替换adb命令: {cmd} -> {new_cmd}")
                                    all_commands.append(new_cmd)
                                else:
                                    # print(f"批量执行 - 非adb命令，直接添加: {cmd}")
                                    all_commands.append(cmd)

                    # 添加查看配置文件的命令（指定设备）
                    all_commands.append(
                        f"adb -s {device} shell cat /vendor/etc/camera/camxoverridesettings.txt"
                    )

                    # 创建临时bat文件
                    bat_path = self.create_temp_bat_for_device(all_commands, device)
                    
                    try:
                        # 执行bat文件
                        # 使用 startupinfo 来隐藏命令行窗口
                        startupinfo = None
                        if hasattr(subprocess, 'STARTUPINFO'):
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            startupinfo.wShowWindow = subprocess.SW_HIDE
                        
                        result = subprocess.run(
                            f'cmd /c "{bat_path}"', 
                            shell=True, 
                            capture_output=True, 
                            text=True, 
                            encoding='gbk',
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        if result.returncode == 0:
                            print(f"设备 {device} 执行成功")
                            success_count += 1
                        else:
                            print(f"设备 {device} 执行失败: {result.stderr}")
                            failed_devices.append(device)
                    finally:
                        # 删除临时文件
                        import os
                        if os.path.exists(bat_path):
                            os.remove(bat_path)
                            
                except Exception as e:
                    print(f"设备 {device} 执行出错: {str(e)}")
                    failed_devices.append(device)
            
            # 显示批量执行结果
            QMetaObject.invokeMethod(self, "show_batch_execution_result", Qt.QueuedConnection,
                                   Q_ARG(int, success_count), 
                                   Q_ARG(int, total_devices), 
                                   Q_ARG(list, failed_devices))

        # 创建并启动线程
        thread = threading.Thread(target=batch_execute_in_thread)
        thread.start()

    def create_temp_bat_for_device(self, commands, device):
        """为指定设备创建临时bat文件"""
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".bat", encoding="gbk"
        ) as f:
            f.write("@echo off\n")
            f.write(f"echo [INFO] 开始执行脚本到设备: {device}\n")
            f.write("echo [INFO] 开始执行脚本...\n")
            f.write("\n".join(commands))
            f.write(f"\necho [INFO] 设备 {device} 执行完成!\n")
            return f.name.replace("/", "\\")  # 确保Windows路径格式

    @pyqtSlot(int, int, list)
    def show_batch_execution_result(self, success_count, total_count, failed_devices):
        """显示批量执行结果"""
        if failed_devices:
            failed_list = "\n".join([f"• {device}" for device in failed_devices])
            message = f"批量执行完成！\n\n成功: {success_count}/{total_count}\n\n失败的设备:\n{failed_list}"
            QMetaObject.invokeMethod(self, "show_batch_result_dialog", Qt.QueuedConnection, 
                                   Q_ARG(str, message), Q_ARG(bool, True))
        else:
            message = f"批量执行完成！\n\n所有 {total_count} 台设备都执行成功！"
            QMetaObject.invokeMethod(self, "show_batch_result_dialog", Qt.QueuedConnection, 
                                   Q_ARG(str, message), Q_ARG(bool, False))

    @pyqtSlot(str, bool)
    def show_batch_result_dialog(self, message, has_failures):
        """在主线程中显示批量执行结果对话框"""
        if has_failures:
            QMessageBox.information(self, "批量执行结果", message)
        else:
            QMessageBox.information(self, "批量执行结果", message)

    def show_context_menu(self, pos, checkbox):
        menu = QMenu(self)
        edit_action = menu.addAction("编辑命令")
        delete_action = menu.addAction("删除")
        rename_action = menu.addAction("重命名")
        action = menu.exec_(checkbox.mapToGlobal(pos))
        if action == edit_action:
            self.edit_command(checkbox.text())
        elif action == delete_action:
            self.delete_command(checkbox)
        elif action == rename_action:
            self.rename_command(checkbox)

    def edit_command(self, command_key):
        current_commands = self.specific_commands.get(command_key, [])
        if isinstance(current_commands, list):
            current_commands = "\n".join(current_commands)
        
        # 创建自定义编辑对话框
        dialog = ScriptEditDialog(self, command_key, current_commands)
        if dialog.exec_() == QDialog.Accepted:
            new_commands = dialog.get_content()
            if new_commands:
                self.specific_commands[command_key] = new_commands.split("\n")
                self.save_commands()

    def rename_command(self, checkbox):
        """重命名选中的命令复选框"""
        old_name = checkbox.text()
        new_name, ok = QInputDialog.getText(
            self, "重命名脚本", "输入新的脚本名称：", text=old_name
        )
        if ok and new_name:
            if new_name in self.specific_commands:
                QMessageBox.warning(self, "错误", "脚本名称已存在。")
                return
            # 更新 specific_commands 字典
            self.specific_commands[new_name] = self.specific_commands.pop(old_name)
            self.save_commands()
            # 更新复选框标签
            checkbox.setText(new_name)

    def add_new_script(self):
        dialog = ScriptInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            script_name, script_content = dialog.get_inputs()
            if script_name and script_content:
                self.specific_commands[script_name] = script_content.split("\n")
                self.save_commands()
                # 创建新的复选框
                new_checkbox = QCheckBox(script_name)
                new_checkbox.stateChanged.connect(
                    self.update_command_mask
                )  # 确保连接到 update_command_mask
                new_checkbox.setContextMenuPolicy(Qt.CustomContextMenu)
                new_checkbox.customContextMenuRequested.connect(
                    lambda pos, cb=new_checkbox: self.show_context_menu(pos, cb)
                )
                self.command_checkboxes.append(new_checkbox)  # 添加到命令复选框列表
                self.layout().addWidget(new_checkbox)
                # 重新排列命令复选框
                self.rearrange_command_checkboxes()

    def delete_command(self, checkbox):
        command_key = checkbox.text()
        # 移除命令
        if command_key in self.specific_commands:
            del self.specific_commands[command_key]
            self.save_commands()
        
        # 从界面移除复选框
        # 查找正确的网格布局
        grid_layout = None
        main_layout = self.layout()
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item.layout():
                if isinstance(item.layout(), QGridLayout):
                    grid_layout = item.layout()
                    break
        
        if grid_layout:
            grid_layout.removeWidget(checkbox)
        checkbox.deleteLater()
        
        # 从命令复选框列表中移除
        self.command_checkboxes.remove(checkbox)
        # 重新排列命令复选框
        self.rearrange_command_checkboxes()
        # 更新 mask
        self.update_script_mask()

    def rearrange_command_checkboxes(self):
        """重新排列 command_label 下的命令复选框"""
        # 查找正确的网格布局
        grid_layout = None
        main_layout = self.layout()
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item.layout():
                if isinstance(item.layout(), QGridLayout):
                    grid_layout = item.layout()
                    break
        
        if grid_layout:
            # 清除当前布局中的所有命令复选框
            for i in reversed(range(grid_layout.count())):
                widget = grid_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget in self.command_checkboxes:
                    grid_layout.removeWidget(widget)

            # 重新添加命令复选框
            columns = 4
            command_start_row = (len(self.script_checkboxes) // 4) + 2
            for index, checkbox in enumerate(self.command_checkboxes):
                row = command_start_row + 1 + (index // columns)
                col = index % columns
                grid_layout.addWidget(checkbox, row, col)
            
            # 强制更新界面
            grid_layout.update()
            self.update()
            self.repaint()
        else:
            print("错误：未找到网格布局")

    def keyPressEvent(self, event):
        """按下 Esc 键关闭窗口"""
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        """重写关闭事件"""
        # self.close()
        self.closed.emit()
        event.accept()
			

class ScriptInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增脚本")
        
        # 设置对话框大小
        self.resize(900, 600)
        self.setMinimumSize(500, 400)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 创建脚本名称标签和输入框
        name_label = QLabel("输入脚本名:")
        layout.addWidget(name_label)
        
        self.script_name_input = QLineEdit(self)
        self.script_name_input.setPlaceholderText("请输入脚本名称")
        self.script_name_input.setMinimumHeight(30)
        layout.addWidget(self.script_name_input)

        # 创建脚本内容标签和输入框
        content_label = QLabel("输入脚本内容:")
        layout.addWidget(content_label)
        
        self.script_content_input = QTextEdit(self)
        self.script_content_input.setPlaceholderText("请输入脚本内容，每行一个命令")
        self.script_content_input.setMinimumHeight(300)
        layout.addWidget(self.script_content_input)

        # 创建按钮
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_inputs(self):
        return self.script_name_input.text(), self.script_content_input.toPlainText()


class ScriptEditDialog(QDialog):
    def __init__(self, parent=None, script_name="", script_content=""):
        super().__init__(parent)
        self.setWindowTitle(f"编辑脚本 - {script_name}")
        
        # 设置对话框大小
        self.resize(900, 600)
        self.setMinimumSize(500, 400)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 创建脚本名称标签（只读显示）
        name_label = QLabel(f"脚本名称: {script_name}")
        name_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(name_label)

        # 创建脚本内容标签和输入框
        content_label = QLabel("脚本内容:")
        layout.addWidget(content_label)
        
        self.script_content_input = QTextEdit(self)
        self.script_content_input.setPlaceholderText("请输入脚本内容，每行一个命令")
        self.script_content_input.setMinimumHeight(400)
        self.script_content_input.setText(script_content)
        layout.addWidget(self.script_content_input)

        # 创建按钮
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_content(self):
        return self.script_content_input.toPlainText()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = LogVerboseMaskApp()
    ex.show()
    sys.exit(app.exec_())
