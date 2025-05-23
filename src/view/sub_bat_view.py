# -*- coding: utf-8 -*-
"""导入python内置模块"""
import os
import sys
import json
import threading
import subprocess

"""导入python三方模块"""
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QMetaObject, Qt, pyqtSlot,pyqtSignal
from PyQt5.QtWidgets import (QApplication, QWidget, QCheckBox, QGridLayout, QTextEdit, 
                             QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QLabel, QMenu, 
                             QInputDialog, QSplitter, QDialog, QLineEdit, QTextEdit, QDialogButtonBox)


"""设置本项目的入口路径,全局变量BasePath"""
# 方法一：手动找寻上级目录，获取项目入口路径，支持单独运行该模块
if False:
    BasePath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 方法二：直接读取主函数的路径，获取项目入口目录,只适用于hiviewer.py同级目录下的py文件调用
if False: # 暂时禁用，不支持单独运行该模块
    BasePath = os.path.dirname(os.path.abspath(sys.argv[0]))  

class LogVerboseMaskApp(QWidget):
	# 将命令保存到commands.json文件中，放到cache目录下
    cache_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "cache")
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)  # 创建 cache 目录
    COMMANDS_FILE = os.path.join(cache_path, "commands.json")
    # 创建关闭信号
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.specific_commands = self.load_commands()
        self.initUI()
        self.setup_logging()

    def load_commands(self):
        """从文件加载命令"""
        if os.path.exists(self.COMMANDS_FILE):
            with open(self.COMMANDS_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            # 如果文件不存在，使用默认命令
            return {
                "HDR": [
                    'adb shell setenforce 0',
                    'adb shell "mkdir /data/local/tmp/morpho/image_refiner/dump -p"',
                    'adb shell "chmod 777 /data/local/tmp/morpho/image_refiner/dump"',
                    'adb shell setprop debug.morpho.image_refiner.enable 1',
                    'adb shell setprop debug.morpho.image_refiner.dump 3',
                    'adb shell setprop debug.morpho.image_refiner.dump_path /data/local/tmp/morpho/image_refiner/dump',
                    'adb shell setprop debug.morpho.image_refiner.enable 1',
                    'adb shell setprop debug.morpho.image_refiner.draw_logo 1'
                ],
                "超夜": [
                    'adb shell setprop persist.vendor.camera.siq.dump 1',
                    'adb shell setprop vendor.camera.siq.dump_input_output 1'
                ],
                "Kill": [
                    'adb shell input keyevent 3',
                    'adb shell "for pid in $(ps -A | grep vendor.qti.camera.provider@2.7-service_64 | awk \'{print $2}\'); do kill $pid; done"',
                    'adb shell "for pid in $(ps -A | grep android.hardware.camera.provider@2.4-service_64 | awk \'{print $2}\'); do kill $pid; done"',
                    'adb shell "for pid in $(ps -A | grep cameraserver | awk \'{print $2}\'); do kill $pid; done"',
                    'adb shell "for pid in $(ps -A | grep com.android.camera | awk \'{print $2}\'); do kill $pid; done"',
                    'adb shell "kill $(pidof camerahalserver)"',
                    'adb shell "kill $(pidof cameraserver)"',
                    'adb shell pkill camera*'
                ],
                "3A": [
                    'adb shell "echo enable3ADebugData=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo enableTuningMetadata=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo dumpSensorEEPROMData=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo logCoreCfgMask=0x2780ba >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo reprocessDump=TRUE >> /vendor/etc/camera/camxoverridesettings.txt"'
                ],
                "离线log": [
                    'adb shell "echo enableAsciiLogging=1 >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo logWarningMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo logVerboseMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo logInfoMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo logConfigMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"',
                    'adb shell "echo logEntryExitMask=0x10080  >> /vendor/etc/camera/camxoverridesettings.txt"'
                ]
            }

    def save_commands(self):
        """将命令保存到文件"""
        with open(self.COMMANDS_FILE, 'w', encoding='utf-8') as file:
            json.dump(self.specific_commands, file, ensure_ascii=False, indent=4)

    def initUI(self):
        self.setWindowTitle('Bat脚本执行')
        self.resize(1000, 600)
        self.mask_value = 0x00000000

        # 创建主布局
        main_layout = QVBoxLayout()

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
        run_button = QPushButton('运行')
        run_button.clicked.connect(self.execute_adb_commands)
        button_layout.addWidget(run_button)

        # 创建新增按钮
        add_button = QPushButton('新增')
        add_button.clicked.connect(self.add_new_script)
        button_layout.addWidget(add_button)

        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)

        # 创建复选框布局
        grid_layout = QGridLayout()

        # 添加第一个标签
        script_label = QLabel("相关脚本：")
        grid_layout.addWidget(script_label, 0, 0, 1, 4)

        # 初始化脚本复选框列表
        self.script_checkboxes = []

        # 添加脚本复选框
        script_labels = [
            "Sensor", "Application", "IQ module", "IFace", "Utilities", "LMME",
            "ISP", "Sync", "NCS", "Post Processor", "MemSpy", "Metadata",
            "Image Lib", "Asserts", "AEC", "CPP", "Core", "AWB", "HAL", "HWI", "AF",
            "JPEG", "CHI", "DRQ", "Stats", "FD", "CSL", "FD"
        ]
        for i, label in enumerate(script_labels):
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(self.update_script_mask)
            row = (i // 4) + 1  # 从第1行开始
            col = i % 4
            grid_layout.addWidget(checkbox, row, col)
            self.script_checkboxes.append(checkbox)

        # 添加第二个标签
        command_label = QLabel("相关命令：")
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
            checkbox.customContextMenuRequested.connect(lambda pos, cb=checkbox: self.show_context_menu(pos, cb))
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
            0x00000002, 0x00000800, 0x00200000, 0x00000004, 0x00001000, 0x00400000,
            0x00000008, 0x00002000, 0x00800000, 0x00000010, 0x00004000, 0x01000000,
            0x00000020, 0x00008000, 0x02000000, 0x00000040, 0x00010000, 0x04000000,
            0x00000080, 0x00020000, 0x08000000, 0x00000100, 0x00040000, 0x00080000,
            0x00000200, 0x00100000, 0x00000400, 0x00100000
        ]
        current_text = self.mask_display.toPlainText().split('\n')
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
        self.mask_display.setText('\n'.join(current_text + commands))

    def update_command_mask(self):
        """更新 command_label 下的复选框"""
        commands = []
        current_text = self.mask_display.toPlainText().split('\n')
        current_text = [line for line in current_text if line.strip()]  # 移除空行
        for checkbox in self.command_checkboxes:
            command_list = self.specific_commands.get(checkbox.text(), [])
            if checkbox.isChecked():
                for command in command_list:
                    if command not in current_text:
                        commands.append(command)
            else:
                for command in command_list:
                    if command in current_text:
                        current_text.remove(command)
        self.mask_display.setText('\n'.join(current_text + commands))

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
        def run_adb_command(command):
            """运行单个 ADB 命令"""
            try:
                result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
                if command:
                    print(f"Command: {command}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                if result.stdout:
                    print(f"Output: {result.stdout}")
                if result.returncode:
                    print(f"Return Code: {result.returncode}")
            except subprocess.CalledProcessError as e:
                if e.cmd:
                    print(f"Command: {e.cmd}")
                if e.stderr:
                    print(f"Error: {e.stderr}")
                

        def execute_specific_commands(command_key):
            """执行特定命令"""
            specific_commands = self.specific_commands.get(command_key, [])
            for command in specific_commands:
                run_adb_command(command)
                # 移除日志记录
                # self.logger.info(f"Executed command for {command_key}: {command}")

        def run_commands_in_thread():
            # ADB 初始化
            adb_init_commands = [
                'adb root',
                'adb remount',
                'adb wait-for-device'
            ]
            for command in adb_init_commands:
                run_adb_command(command)

            # 创建目录和删除文件
            run_adb_command('adb shell "mkdir -p vendor/etc/camera && rm -f vendor/etc/camera/camxoverridesettings.txt"')

            # 从 QTextEdit 中获取命令并合成一个命令执行
            text_edit_commands = self.mask_display.toPlainText().split('\n')
            text_edit_commands = [cmd for cmd in text_edit_commands if isinstance(cmd, str)]
            combined_command = ' && '.join(text_edit_commands)
            if combined_command.strip():
                run_adb_command(combined_command)

            run_adb_command('adb shell cat /vendor/etc/camera/camxoverridesettings.txt')

            # 执行特定命令
            for checkbox in self.command_checkboxes:
                if checkbox.isChecked() and checkbox.text() in self.specific_commands:
                    execute_specific_commands(checkbox.text())

            # 在主线程中显示成功提示框
            QMetaObject.invokeMethod(self, "show_success_message", Qt.QueuedConnection)

        # 创建并启动线程
        thread = threading.Thread(target=run_commands_in_thread)
        thread.start()

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
            current_commands = '\n'.join(current_commands)
        new_commands, ok = QInputDialog.getMultiLineText(self, "编辑命令", f"修改 {command_key} 的命令:", current_commands)
        if ok:
            self.specific_commands[command_key] = new_commands.split('\n')
            self.save_commands()

    def rename_command(self, checkbox):
        """重命名选中的命令复选框"""
        old_name = checkbox.text()
        new_name, ok = QInputDialog.getText(self, "重命名脚本", "输入新的脚本名称：", text=old_name)
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
                self.specific_commands[script_name] = script_content.split('\n')
                self.save_commands()
                # 创建新的复选框
                new_checkbox = QCheckBox(script_name)
                new_checkbox.stateChanged.connect(self.update_command_mask)  # 确保连接到 update_command_mask
                new_checkbox.setContextMenuPolicy(Qt.CustomContextMenu)
                new_checkbox.customContextMenuRequested.connect(lambda pos, cb=new_checkbox: self.show_context_menu(pos, cb))
                self.command_checkboxes.append(new_checkbox)  # 添加到命令复选框列表
    
                # 获取网格布局（索引应为2）
                grid_layout = self.layout().itemAt(2).layout()
                if isinstance(grid_layout, QGridLayout):
                    columns = 4
                    total_checkboxes = len(self.command_checkboxes)
                    # 计算命令区域的起始行
                    command_start_row = (len([
                        cb for cb in self.script_checkboxes
                    ]) // 4) + 2  # 调整行号以适应脚本部分
                    row = command_start_row + (total_checkboxes - 1) // columns  # 行号从命令起始行开始
                    col = (total_checkboxes - 1) % columns
                    grid_layout.addWidget(new_checkbox, row, col)
                else:
                    # 如果不是 QGridLayout，直接添加到布局中
                    self.layout().addWidget(new_checkbox)

    def delete_command(self, checkbox):
        command_key = checkbox.text()
        # 移除命令
        if command_key in self.specific_commands:
            del self.specific_commands[command_key]
            self.save_commands()
        # 从界面移除复选框
        self.layout().itemAt(2).layout().removeWidget(checkbox)
        checkbox.deleteLater()
        # 从命令复选框列表中移除
        self.command_checkboxes.remove(checkbox)
        # 重新排列命令复选框
        self.rearrange_command_checkboxes()
        # 更新 mask
        self.update_script_mask()

    def rearrange_command_checkboxes(self):
        """重新排列 command_label 下的命令复选框"""
        grid_layout = self.layout().itemAt(2).layout()
        if isinstance(grid_layout, QGridLayout):
            # 清除当前布局中的所有命令复选框
            for i in reversed(range(grid_layout.count())):
                widget = grid_layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox) and widget in self.command_checkboxes:
                    grid_layout.removeWidget(widget)
            
            # 重新添加命令复选框
            columns = 4
            command_start_row = (len(self.script_checkboxes) // 4) + 2
            for index, checkbox in enumerate(self.command_checkboxes):
                row = command_start_row + index // columns
                col = index % columns
                grid_layout.addWidget(checkbox, row, col)

    def keyPressEvent(self, event):
        """按下 Esc 键关闭窗口"""
        if event.key() == Qt.Key_Escape:
            self.close()
            self.closed.emit()   # 发送关闭信号 
            event.accept()       # 接受事件
    
    def closeEvent(self, event):
        """重写关闭事件"""
        # self.close()
        self.closed.emit()
        event.accept()
			

class ScriptInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增脚本")
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建输入框
        self.script_name_input = QLineEdit(self)
        self.script_name_input.setPlaceholderText("输入脚本名")
        layout.addWidget(self.script_name_input)
        
        self.script_content_input = QTextEdit(self)
        self.script_content_input.setPlaceholderText("输入脚本内容")
        layout.addWidget(self.script_content_input)
        
        # 创建按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def get_inputs(self):
        return self.script_name_input.text(), self.script_content_input.toPlainText()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LogVerboseMaskApp()
    ex.show()
    sys.exit(app.exec_())
