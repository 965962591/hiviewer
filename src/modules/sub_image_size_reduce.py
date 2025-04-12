import os
import sys
import subprocess
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QWidget, QFileDialog, QComboBox
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QHeaderView

# 全局标志位，控制路径类型
icon_abs = False
def compress_jpg_with_jpegoptim(files, quality=85):
    try:
        # 构建jpegoptim的完整路径
        jpegoptim_path = os.path.join(os.path.dirname(__file__), 'tools', 'jpegoptim.exe')
        
        # 获取第一个文件的目录作为压缩文件夹的基准
        file_dir = os.path.dirname(files[0])
        # 定义压缩文件夹路径
        compressed_dir = os.path.join(file_dir, 'compressed')
        
        # 如果压缩文件夹不存在，则创建
        os.makedirs(compressed_dir, exist_ok=True)
        
        # 复制所有原始文件到压缩文件夹
        for input_file in files:
            original_file_path = os.path.join(compressed_dir, os.path.basename(input_file))
            shutil.copy(input_file, original_file_path)
        
        # 构建jpegoptim命令
        command = [jpegoptim_path, '--max=' + str(quality), '--strip-all']
        command.extend([os.path.join(compressed_dir, os.path.basename(f)) for f in files])
        
        # 调用jpegoptim命令
        subprocess.run(command, check=True)
        
        print("Images compressed and saved to:", compressed_dir)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

class CompressionThread(QThread):
    # 定义一个信号，用于在压缩完成后更新UI
    compression_done = pyqtSignal()

    def __init__(self, files, quality):
        super().__init__()
        self.files = files
        self.quality = quality

    def run(self):
        compress_jpg_with_jpegoptim(self.files, quality=self.quality)
        # 发射信号，通知主线程压缩已完成
        self.compression_done.emit()

class ImageCompressorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片体积压缩工具")
        self.setFixedSize(1000, 800)
        icon_path = r"D:\Image_process\hiviewer-master\images\image_size_reduce_ico_96x96.ico" if icon_abs else os.path.join(os.path.dirname(__file__), "icons", "image_size_reduce_ico_96x96.ico")
        self.setWindowIcon(QIcon(icon_path))        
        # 主窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 主布局
        self.layout = QVBoxLayout(self.central_widget)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["文件名", "压缩状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # 动态调整列宽
        self.layout.addWidget(self.table)
        
        # 按钮布局
        self.button_layout = QHBoxLayout()
        
        # 导入按钮
        self.import_button = QPushButton("导入图片")
        self.import_button.clicked.connect(self.import_images)
        self.button_layout.addWidget(self.import_button)


        # 添加下拉框，用于选择压缩质量
        self.quality_combo = QComboBox()
        self.quality_combo.setEditable(True)  # 设置 QComboBox 为可编辑状态
        self.quality_combo.addItems(["85","65", "50", "35", ])  # 添加压缩质量选项
        self.quality_combo.setToolTip("选择图片的压缩质量")  # 添加悬浮信息提示
        self.button_layout.addWidget(self.quality_combo)

        # 开始按钮
        self.start_button = QPushButton("开始压缩")
        self.start_button.clicked.connect(self.start_compression)
        self.button_layout.addWidget(self.start_button)

        # 添加快捷键ESC退出程序
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.close)
        
        # 将按钮布局添加到主布局
        self.layout.addLayout(self.button_layout)
        
        # 图片文件列表
        self.image_files = []
        self.threads = []  # 用于存储线程对象

    def import_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.jpg *.jpeg *.png)")
        if files:
            self.image_files = files
            self.table.setRowCount(len(files))
            for i, file in enumerate(files):
                file_name = os.path.basename(file)  # 提取文件名
                self.table.setItem(i, 0, QTableWidgetItem(file_name))
                self.table.setItem(i, 1, QTableWidgetItem("未开始"))

    def start_compression(self):
        # 获取self.quality_combo的值
        quality = int(self.quality_combo.currentText())
        if quality < 0 or quality > 100: # 检查quality是否在0到100之间
            # print("Invalid quality value. Please choose a value between 0 and 100.")
            quality = 85
        print(f"Quality: {quality}")
        if self.image_files and quality:
            thread = CompressionThread(self.image_files, quality)
            thread.compression_done.connect(self.update_table)
            self.threads.append(thread)
            thread.start()

    def update_table(self):
        for i in range(len(self.image_files)):
            self.table.setItem(i, 1, QTableWidgetItem("已完成"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageCompressorApp()
    window.show()
    sys.exit(app.exec_())