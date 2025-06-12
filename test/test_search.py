"""
1、主界面aebox可以使用ctrl+f快捷键再图片列表内进行模糊搜素。
2、按下ctrl+f可以弹出一个如图的界面，输入后搜索框下面显示模糊匹配的图片名称。
3、支持模糊搜索，支持大小写，支持中文。
4、支持按esc键关闭搜索界面。
5、点击搜索到的项，可以跳转到对应的图片并显示相关信息。
"""
from PyQt5.QtWidgets import QLineEdit, QListWidget, QVBoxLayout, QHBoxLayout, QShortcut, QMainWindow, QWidget, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
import os
import xml.etree.ElementTree as ET

class SearchOverlay(QMainWindow):
    image_selected_from_search = pyqtSignal(str)

    def __init__(self, main_window, image_list_widget, image_paths_dict):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("图片搜索")
        self.image_list_widget = image_list_widget
        # 存储图片路径字典，而不是目录
        self.image_paths_dict = image_paths_dict  # 从主窗口传入的图片路径字典 {filename: filepath}
        self.image_info_dict = {}  # {filename: {lux: xxx, cct: xxx}}
        # 尝试获取图片目录
        self.image_dir = ""
        if image_paths_dict and len(image_paths_dict) > 0:
            # 从字典中获取第一个图片的路径，然后提取其目录
            first_path = next(iter(image_paths_dict.values()))
            if isinstance(first_path, str) and os.path.exists(first_path):
                self.image_dir = os.path.dirname(first_path)
        
        container_widget = QWidget()
        self.setCentralWidget(container_widget)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.search_layout = QVBoxLayout(container_widget)
        self.search_layout.setContentsMargins(10, 10, 10, 10)
        self.search_layout.setSpacing(5)

        # 新增：横向布局，放下拉框和搜索框
        self.top_row_layout = QHBoxLayout()
        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItems(["文件名", "lux", "cct"])
        self.search_mode_combo.setFixedWidth(100)
        self.top_row_layout.addWidget(self.search_mode_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("在此处键入以搜索...")
        self.top_row_layout.addWidget(self.search_input)

        self.search_layout.addLayout(self.top_row_layout)
        
        self.search_results_list = QListWidget()
        self.search_layout.addWidget(self.search_results_list)

        self.hide()

        self.search_input.textChanged.connect(self.update_search_results)
        self.search_results_list.itemClicked.connect(self.select_image_from_search)
        self.search_mode_combo.currentIndexChanged.connect(self.on_mode_changed)

        self.old_pos = None
        self.resize(800, 400)
        self.shortcut_escape = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_escape.activated.connect(self.hide_search_overlay)

    def on_mode_changed(self):
        mode = self.search_mode_combo.currentText()
        if mode == "文件名":
            self.search_input.setPlaceholderText("在此处键入以搜索文件名...")
        elif mode == "lux":
            self.search_input.setPlaceholderText("输入lux/lux_index值或范围，如50或200-300")
        elif mode == "cct":
            self.search_input.setPlaceholderText("输入cct/CCT值或范围，如1000或2000-3000")
        self.update_search_results(self.search_input.text())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.old_pos is not None:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None

    def toggle_search_overlay(self):
        if self.isHidden():
            self.show_search_overlay()
        else:
            self.hide_search_overlay()

    def show_search_overlay(self):
        # 生成 image_paths_dict
        self.generate_image_info_dict()
        main_window_rect = self.main_window.geometry()
        center_x = main_window_rect.center().x() - self.width() // 2
        center_y = main_window_rect.center().y() - self.height() // 2
        self.move(center_x, center_y)
        self.show()
        self.search_input.setFocus()
        self.update_search_results(self.search_input.text())

    def hide_search_overlay(self):
        self.hide()

    def generate_image_info_dict(self):
        """
        遍历图片列表，为每个图片查找同名_new.xml文件，解析lux和cct
        """
        self.image_info_dict = {}
        # 尝试列出目录中所有XML文件
        xml_files = []
        if self.image_dir and os.path.exists(self.image_dir):
            for file in os.listdir(self.image_dir):
                if file.endswith('.xml'):
                    xml_files.append(file)
        print(f"目录中XML文件数量: {len(xml_files)}")
        
        xml_found_count = 0
        for filename, filepath in self.image_paths_dict.items():
            name, ext = os.path.splitext(filename)
            
            # 尝试多种可能的XML文件命名模式
            xml_candidates = [
                os.path.join(os.path.dirname(filepath), f"{name}_new.xml"),  # 与图片同目录
            ]
            
            # 检查XML文件是否存在
            xml_path = None
            for candidate in xml_candidates:
                if os.path.exists(candidate):
                    xml_path = candidate
                    xml_found_count += 1
                    print(f"找到XML文件: {xml_path}")
                    break
            
            # 如果没有找到XML文件，检查是否可以匹配其他XML文件
            if xml_path is None and len(xml_files) > 0:
                # 尝试匹配名称相似的XML文件
                for xml_file in xml_files:
                    xml_name = os.path.splitext(xml_file)[0]
                    if name in xml_name or xml_name in name:
                        xml_path = os.path.join(self.image_dir, xml_file)
                        xml_found_count += 1
                        print(f"通过模糊匹配找到XML文件: {xml_path} 匹配图片: {filename}")
                        break
            
            info = {}
            if xml_path and os.path.exists(xml_path):
                try:
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    # 尝试读取不同格式的标签名
                    lux = None
                    cct = None
                    
                    # 方法1：直接查找标签
                    lux_direct =root.findtext("lux_index")
                    cct_direct =root.findtext("CCT")
                    
                    # # 方法2：遍历所有子节点查找
                    # for child in root:
                    #     if child.tag.lower() in ['lux', 'lux_index']:
                    #         lux = child.text
                    #     elif child.tag.lower() in ['cct', 'cct_index']:
                    #         cct = child.text
                    
                    # # 方法3：查找特定标签名（匹配您提供的XML格式）
                    # if lux is None and root.findtext("lux_index") is not None:
                    #     lux = root.findtext("lux_index")
                        
                    # if cct is None and root.findtext("CCT") is not None:
                    #     cct = root.findtext("CCT")
                    
                    # # 方法4：读取您提供的XML结构中的值
                    # if root.tag == "Analyzer":
                    #     lux_index_node = root.find("lux_index")
                    #     cct_node = root.find("CCT")
                        
                    #     if lux_index_node is not None and lux is None:
                    #         lux = lux_index_node.text
                            
                    #     if cct_node is not None and cct is None:
                    #         cct = cct_node.text

                    
                    # 使用找到的值
                    lux = lux_direct or lux
                    cct = cct_direct or cct
                    
                    
                    if lux is not None:
                        try:
                            info["lux"] = float(lux)
                        except ValueError:
                            print(f"lux值转换失败: {lux}")
                    if cct is not None:
                        try:
                            info["cct"] = float(cct)
                        except ValueError:
                            print(f"cct值转换失败: {cct}")
                except Exception as e:
                    print(f"解析XML出错: {xml_path}, 错误: {str(e)}")
            
            self.image_info_dict[filename] = info  # 始终存储字典，即使是空字典

    def update_search_results(self, query):
        self.search_results_list.clear()
        mode = self.search_mode_combo.currentText()
        if not query:
            for filename in self.image_info_dict.keys():
                self.search_results_list.addItem(filename)
            return

        if mode == "文件名":
            for filename in self.image_info_dict.keys():
                if query.lower() in filename.lower():
                    self.search_results_list.addItem(filename)
        else:
            # lux/cct搜索
            key = mode.lower()  # "lux"或"cct"
            try:
                if '-' in query:
                    start, end = map(float, query.split('-'))
                else:
                    value = float(query)
                    if key == "lux":
                        start, end = value - 20, value + 20
                    else:  # key == "cct"
                        start, end = value - 100, value + 100
            except ValueError:
                # 显示输入错误提示
                self.search_results_list.addItem(f"输入格式错误，请输入数字或范围(如: 100-200)")
                return

            # 调试信息
            debug_count = 0
            has_data_count = 0
            
            print(f"当前搜索: {mode}, 范围: {start}-{end}")
            print(f"图片信息字典: {self.image_info_dict}")
            
            for filename, info in self.image_info_dict.items():
                debug_count += 1
                if not isinstance(info, dict):
                    print(f"跳过非字典项: {filename}, 类型: {type(info)}")
                    continue
                    
                # 打印当前图片的信息
                print(f"检查图片: {filename}, 信息: {info}")
                
                val = info.get(key)
                if val is not None:
                    has_data_count += 1
                    print(f"找到{key}值: {val}, 判断是否在范围 {start}-{end} 内")
                    if start <= val <= end:
                        print(f"添加到结果: {filename}")
                        self.search_results_list.addItem(filename)
            
            # 如果没有找到任何结果，显示提示信息
            if self.search_results_list.count() == 0:
                if has_data_count == 0:
                    self.search_results_list.addItem(f"没有找到包含{mode}数据的图片")
                else:
                    self.search_results_list.addItem(f"没有找到{mode}值在{start}-{end}范围内的图片")
                self.search_results_list.addItem(f"图片总数: {debug_count}, 包含{mode}值的图片: {has_data_count}")

    def select_image_from_search(self, item):
        filename = item.text()
        self.image_selected_from_search.emit(filename)
        self.hide_search_overlay()