import os
import sys

# 添加项目根目录到 Python 路径，以便进行绝对导入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import ( QWidget, QHBoxLayout, QVBoxLayout, QListWidget, 
                             QScrollArea, QLabel, QFrame, QListWidgetItem, QCheckBox, QDialog, QLineEdit, QSpinBox,  QPushButton, QMessageBox, QInputDialog, QComboBox, QTextBrowser, QApplication, QSplitter)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QIcon, QDesktopServices
from functools import partial

# 导入配置管理器
try:
    # 尝试相对导入（当作为模块运行时）
    from .manager_config import ConfigManager
except ImportError:
    # 尝试绝对导入（当直接运行时）
    from src.common.manager_config import ConfigManager

# 从version.ini文件中读取版本号
def get_version_from_ini():
    try:
        ini_path = os.path.join(os.path.dirname(__file__), "version.ini")
        if os.path.exists(ini_path):
            with open(ini_path, "r", encoding="utf-8") as f:
                version = f.read().strip()
                if version:
                    return version
        return "release-v3.6.6"  # 默认版本号
    except Exception as e:
        print(f"从ini文件读取版本号时出错: {e}")
        return "release-v3.6.6"

VERSION = get_version_from_ini()

class SettingsWindow(QDialog):
    theme_changed = pyqtSignal(str) # Signal to change theme in main app
    pic_settings_changed = pyqtSignal(str, bool)
    _instance = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(1000, 700)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.is_nav_collapsed = False
        self.setup_ui()

        # 加载初始设置
        self.load_settings()

    def setup_ui(self):
        # Use a splitter for resizable navigation
        self.splitter = QSplitter(Qt.Horizontal)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.splitter)

        # Left navigation panel
        self.nav_list = QListWidget()
        self.nav_list.itemClicked.connect(self.on_nav_item_clicked)
        self.nav_list.setIconSize(QSize(24, 24))
        
        # Right content area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        
        # Add widgets to splitter
        self.splitter.addWidget(self.nav_list)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setSizes([150, 850]) # Initial sizes
        self.splitter.setCollapsible(0, False) # Prevent complete collapse
        self.splitter.setCollapsible(1, False)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)

        # Add items to navigation and content
        add_setting_section_icon = os.path.join(os.path.dirname(__file__), "icon")
        self.add_setting_section("COLOR", add_setting_section_icon+"/new_start_256.ico", self.create_general_settings)
        self.add_setting_section("API", add_setting_section_icon+"/tcp.ico", self.create_network_settings)
        self.add_setting_section("PARSE", add_setting_section_icon+"/mcc.ico", self.create_parse_settings)
        self.add_setting_section("SVN", add_setting_section_icon+"/svn.ico", self.create_svn_settings)
        self.add_setting_section("RAW", add_setting_section_icon+"/raw.ico", self.create_raw_settings)
        self.add_setting_section("PIC", add_setting_section_icon+"/his.ico", self.create_pic_settings)
        self.add_setting_section("ABOUT", add_setting_section_icon+"/about.ico", self.create_about_section)
        self.add_setting_section("DOCS", add_setting_section_icon+"/help.ico", self.create_docs_section)
        self.add_setting_section("LOGS", add_setting_section_icon+"/log.ico", self.create_update_log_section)

        # Set initial selection to the first item
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)

        # Sync scrolling with navigation
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.setLayout(main_layout)

        # Store section widgets for scrolling
        self.section_widgets = []

    def on_splitter_moved(self, pos, index):
        if index == 1:
            nav_width = self.splitter.sizes()[0]
            self.update_nav_view(nav_width)

    def update_nav_view(self, width):
        collapse_threshold = 100

        # Collapse if width is small and it's not already collapsed
        if width < collapse_threshold and not self.is_nav_collapsed:
            self.is_nav_collapsed = True
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                item.setText("")

        # Expand if width is large and it's currently collapsed
        elif width >= collapse_threshold and self.is_nav_collapsed:
            self.is_nav_collapsed = False
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                item.setText(item.data(Qt.UserRole))

    def switch_to_section(self, name):
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            if item.text() == name:
                self.nav_list.setCurrentItem(item)
                self.on_nav_item_clicked(item)
                break

    @staticmethod
    def show_dialog(parent=None):
        if SettingsWindow._instance is None:
            SettingsWindow._instance = SettingsWindow(parent)
        SettingsWindow._instance.show()
        SettingsWindow._instance.activateWindow()
        SettingsWindow._instance.raise_()
        return SettingsWindow._instance

    def add_setting_section(self, name, icon_path, content_creation_func):
        # Navigation item
        icon = QIcon(icon_path)
        item = QListWidgetItem(icon, name)
        item.setData(Qt.UserRole, name) # Store the name for restoration
        item.setSizeHint(QSize(0, 40))
        self.nav_list.addItem(item)
        
        # Content section
        section_container = QWidget()
        section_layout = QVBoxLayout(section_container)
        section_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(f"<b>{name}</b>")
        title.setFixedHeight(40)
        section_layout.addWidget(title)
        
        content_widget = content_creation_func()
        section_layout.addWidget(content_widget)
        
        self.content_layout.addWidget(section_container)
        
        # Store for scroll syncing
        # A bit of a hack to get the widget later
        setattr(item, 'section_widget', section_container)

    def create_general_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        self.theme_buttons = []

        light_themes = [
            ("light_amber.xml", "#FFD54F"),
            ("light_blue.xml", "#4F83CC"),
            ("light_cyan.xml", "#4DD0E1"),
            ("light_cyan_500.xml", "#00BCD4"),
            ("light_lightgreen.xml", "#AED581"),
            ("light_lightgreen_500.xml","#8bc34a"),
            ("light_orange.xml","#ff3d00"),
            ("light_pink_500.xml","#e91e63"),
            ("light_pink.xml", "#F06292"),
            ("light_purple.xml", "#BA68C8"),
            ("light_purple_500.xml", "#9c27b0"),
            ("light_red.xml", "#E57373"),
            ("light_red_500.xml", "#f44336"),
            ("light_teal.xml", "#4DB6AC"),
            ("light_teal_500.xml", "#009688"),
            ("light_yellow.xml", "#FFF176"),
        ]
        dark_themes = [
            ("dark_amber.xml", "#FFD54F"),
            ("dark_blue.xml", "#4F83CC"),
            ("dark_cyan.xml", "#4DD0E1"),
            ("dark_lightgreen.xml", "#AED581"),
            ("dark_medical.xml", "#bed2ff"),
            ("dark_pink.xml", "#F06292"),
            ("dark_purple.xml", "#BA68C8"),
            ("dark_red.xml", "#E57373"),
            ("dark_teal.xml", "#4DB6AC"),
            ("dark_yellow.xml", "#FFF176"),
            ("dark_blue_diy1.xml", "#3f72af"),
            ("dark_blue_diy2.xml", "#00adb5"),
            ("dark_blue_diy3.xml", "#ff0097"),
            ("dark_blue_diy4.xml", "#87C4ED"),
            ("dark_blue_diy5.xml", "#75664d"),
            ("dark_blue_diy6.xml", "#005691"),
        ]

        # Light themes row
        light_theme_layout = QHBoxLayout()
        light_theme_layout.addWidget(QLabel("浅色:"))
        for theme_name, color in light_themes:
            btn = self._create_color_button(theme_name, color)
            light_theme_layout.addWidget(btn)
        light_theme_layout.addStretch()
        layout.addLayout(light_theme_layout)

        # Dark themes row
        dark_theme_layout = QHBoxLayout()
        dark_theme_layout.addWidget(QLabel("深色:"))
        for theme_name, color in dark_themes:
            btn = self._create_color_button(theme_name, color)
            dark_theme_layout.addWidget(btn)
        dark_theme_layout.addStretch()
        layout.addLayout(dark_theme_layout)

        layout.addStretch()
        return widget

    def _create_color_button(self, theme_name, color):
        btn = QPushButton()
        btn.setFixedSize(28, 28)
        btn.setProperty("theme_name", theme_name)
        btn.setProperty("color", color)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 14px;
            }}
            QPushButton:hover {{
                border: 2px solid #90CAF9;
            }}
        """)
        btn.clicked.connect(partial(self.select_theme, btn))
        self.theme_buttons.append(btn)
        return btn

    def select_theme(self, clicked_button):
        theme_name = clicked_button.property("theme_name")
        for btn in self.theme_buttons:
            style = btn.styleSheet()
            # Remove existing selection border
            style = style.replace("border: 2px solid #4F83CC;", "border: none;")
            btn.setStyleSheet(style)

        # Add border to clicked button
        new_style = clicked_button.styleSheet() + "border: 2px solid #4F83CC;"
        clicked_button.setStyleSheet(new_style)

        # Save and emit
        self.config_manager.set_setting('Appearance', 'Style', theme_name)
        self.theme_changed.emit(theme_name)

    def load_settings(self):
        # Load theme style
        saved_theme = self.config_manager.get_setting('Appearance', 'Style', default='dark_blue.xml')
        for btn in self.theme_buttons:
            if btn.property("theme_name") == saved_theme:
                self.select_theme(btn)
                break
        else: # if no theme is selected (e.g. first run)
            if self.theme_buttons:
                self.select_theme(self.theme_buttons[0])

        # Load Network settings
        if self.parent():
            self.ip_input.setText(self.parent().api_host)
            self.port_input.setText(str(self.parent().api_port))
        
        # Load Parse settings
        self.parse_processes_spinbox.setValue(int(self.config_manager.get_setting('settings', 'parse_processes', config_name='parse', default=8)))
        self.dump_processes_spinbox.setValue(int(self.config_manager.get_setting('settings', 'dump_processes', config_name='parse', default=4)))
        self.batch_spinbox.setValue(int(self.config_manager.get_setting('settings', 'bacth_size', config_name='parse', default=50)))
        
        # Load SVN settings
        self.svn_url_input.setText(self.config_manager.get_setting('svn', 'url', config_name='svn', default=''))
        self.svn_user_input.setText(self.config_manager.get_setting('svn', 'username', config_name='svn', default=''))
        self.svn_password_input.setText(self.config_manager.get_setting('svn', 'password', config_name='svn', default=''))

        # Load RAW settings
        self.raw_width_input.setText(self.config_manager.get_setting('raw_options', 'width', file_type='json', config_name='raw', default='3264'))
        self.raw_height_input.setText(self.config_manager.get_setting('raw_options', 'height', file_type='json', config_name='raw', default='2448'))
        self.raw_bit_depth_input.setText(self.config_manager.get_setting('raw_options', 'bit_depth', file_type='json', config_name='raw', default='10'))
        
        bayer_pattern = self.config_manager.get_setting('raw_options', 'bayer_pattern', file_type='json', config_name='raw', default='RGGB')
        if bayer_pattern in self.bayer_patterns:
            self.bayer_pattern_combo.setCurrentText(bayer_pattern)

        # Load Pic settings
        show_rgb_lab = self.config_manager.get_setting('settings', 'rgb_lab_enabled', config_name='pic', default=False)
        self.show_rgb_lab_checkbox.setChecked(show_rgb_lab)
        show_histogram = self.config_manager.get_setting('settings', 'histogram_enabled', config_name='pic', default=False)
        self.show_histogram_checkbox.setChecked(show_histogram)
        clear_cache = self.config_manager.get_setting('settings', 'clear_cache', config_name='pic', default=False)
        self.clear_cache_checkbox.setChecked(clear_cache)

    def on_theme_changed(self, theme):
        if not theme: return
        self.config_manager.set_setting('Appearance', 'Style', theme)
        self.theme_changed.emit(theme)

    def select_color(self, selected_swatch):
        for swatch in self.color_swatches:
            current_style = swatch.styleSheet()
            new_style = current_style.replace("border: 2px solid #ffffff;", "border: 2px solid transparent;")
            swatch.setStyleSheet(new_style)
        
        current_style = selected_swatch.styleSheet()
        if "border: 2px solid #ffffff;" not in current_style:
             new_style = current_style.replace("border: 2px solid transparent;", "border: 2px solid #ffffff;")
             selected_swatch.setStyleSheet(new_style)
        
        # Save selected color
        color_hex = selected_swatch.property("color_hex")
        if color_hex:
            self.config_manager.set_setting('ThemeColor', 'Color', color_hex)

    def create_network_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        ip_label = QLabel("IP地址:")
        self.ip_input = QLineEdit()
        
        port_label = QLabel("端口:")
        self.port_input = QLineEdit()

        save_button = QPushButton("保存")
        save_button.setFixedWidth(100)
        save_button.clicked.connect(self.save_and_restart_api)

        layout.addWidget(ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(port_label)
        layout.addWidget(self.port_input)
        layout.addSpacing(10)
        layout.addWidget(save_button)
        layout.addStretch()
        return widget

    def save_and_restart_api(self):
        from api.api_restart_edit import save_api_config, restart_api_service
        main_window = self.parent()
        if not main_window:
            return

        new_host = self.ip_input.text().strip()
        new_port_str = self.port_input.text().strip()

        if not new_host:
            QMessageBox.warning(self, "输入错误", "IP地址不能为空。")
            return
        
        if not new_port_str.isdigit():
            QMessageBox.warning(self, "输入错误", "端口号必须是数字。")
            return
        
        new_port = int(new_port_str)

        # Update values in main window
        main_window.api_host = new_host
        main_window.api_port = new_port

        # Save and restart
        save_api_config(main_window)
        if restart_api_service(main_window):
            QMessageBox.information(self, "成功", f"API服务已成功重启在 {main_window.api_host}:{main_window.api_port}")
        else:
            QMessageBox.warning(self, "警告", "API配置已保存，但重启服务失败。请检查配置是否正确。")

    def create_parse_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        try:
            max_processes = os.cpu_count()
        except NotImplementedError:
            max_processes = 16  # Fallback

        max_proc_label = QLabel(f"提示: 当前设备CPU最大支持进程数为 {max_processes}")
        layout.addWidget(max_proc_label)

        parse_proc_label = QLabel("解析(Parse)进程数量:")
        self.parse_processes_spinbox = QSpinBox()
        self.parse_processes_spinbox.setFixedWidth(100)
        self.parse_processes_spinbox.setRange(1, max_processes)
        self.parse_processes_spinbox.valueChanged.connect(
            lambda val: self.config_manager.set_setting('settings', 'parse_processes', val, config_name='parse')
        )

        dump_proc_label = QLabel("转储(Dump)进程数量:")
        self.dump_processes_spinbox = QSpinBox()
        self.dump_processes_spinbox.setFixedWidth(100)
        self.dump_processes_spinbox.setRange(1, max_processes)
        self.dump_processes_spinbox.valueChanged.connect(
            lambda val: self.config_manager.set_setting('settings', 'dump_processes', val, config_name='parse')
        )
        
        batch_label = QLabel("批处理大小:")
        self.batch_spinbox = QSpinBox()
        self.batch_spinbox.setFixedWidth(100)
        self.batch_spinbox.setRange(1, 1000)
        self.batch_spinbox.valueChanged.connect(
            lambda val: self.config_manager.set_setting('settings', 'bacth_size', val, config_name='parse')
        )
        
        layout.addWidget(parse_proc_label)
        layout.addWidget(self.parse_processes_spinbox)
        layout.addWidget(dump_proc_label)
        layout.addWidget(self.dump_processes_spinbox)
        layout.addWidget(batch_label)
        layout.addWidget(self.batch_spinbox)
        layout.addStretch()
        return widget

    def create_svn_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        url_label = QLabel("SVN URL:")
        self.svn_url_input = QLineEdit()
        
        user_label = QLabel("用户名:")
        self.svn_user_input = QLineEdit()

        password_label = QLabel("密码:")
        self.svn_password_input = QLineEdit()
        self.svn_password_input.setEchoMode(QLineEdit.Password)
        save_button = QPushButton("保存")
        save_button.setFixedWidth(100)
        save_button.clicked.connect(self.save_svn_settings)

        layout.addWidget(url_label)
        layout.addWidget(self.svn_url_input)
        layout.addWidget(user_label)
        layout.addWidget(self.svn_user_input)
        layout.addWidget(password_label)
        layout.addWidget(self.svn_password_input)
        layout.addSpacing(10)
        layout.addWidget(save_button)
        layout.addStretch()
        return widget

    def save_svn_settings(self):
        url = self.svn_url_input.text()
        user = self.svn_user_input.text()
        password = self.svn_password_input.text()

        self.config_manager.set_setting('svn', 'url', url, config_name='svn')
        self.config_manager.set_setting('svn', 'username', user, config_name='svn')
        self.config_manager.set_setting('svn', 'password', password, config_name='svn')

        QMessageBox.information(self, "成功", "SVN 设置已保存。")

    def create_raw_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Width
        width_label = QLabel("宽度:")
        self.raw_width_input = QLineEdit()
        self.raw_width_input.setFixedWidth(100)
        self.raw_width_input.textChanged.connect(
            lambda txt: self.config_manager.set_setting('raw_options', 'width', txt, file_type='json', config_name='raw')
        )
        
        # Height
        height_label = QLabel("高度:")
        self.raw_height_input = QLineEdit()
        self.raw_height_input.setFixedWidth(100)
        self.raw_height_input.textChanged.connect(
            lambda txt: self.config_manager.set_setting('raw_options', 'height', txt, file_type='json', config_name='raw')
        )

        # Bit Depth
        bit_depth_label = QLabel("位深:")
        self.raw_bit_depth_input = QLineEdit()
        self.raw_bit_depth_input.setFixedWidth(100)
        self.raw_bit_depth_input.textChanged.connect(
            lambda txt: self.config_manager.set_setting('raw_options', 'bit_depth', txt, file_type='json', config_name='raw')
        )

        # Bayer Pattern
        bayer_label = QLabel("Bayer Pattern:")
        self.bayer_pattern_combo = QComboBox()
        self.bayer_pattern_combo.setFixedWidth(100)
        self.bayer_patterns = ['RGGB', 'BGGR', 'GRBG', 'GBRG']
        self.bayer_pattern_combo.addItems(self.bayer_patterns)
        self.bayer_pattern_combo.currentTextChanged.connect(
            lambda txt: self.config_manager.set_setting('raw_options', 'bayer_pattern', txt, file_type='json', config_name='raw')
        )
        
        layout.addWidget(width_label)
        layout.addWidget(self.raw_width_input)
        layout.addWidget(height_label)
        layout.addWidget(self.raw_height_input)
        layout.addWidget(bit_depth_label)
        layout.addWidget(self.raw_bit_depth_input)
        layout.addWidget(bayer_label)
        layout.addWidget(self.bayer_pattern_combo)
        layout.addStretch()
        return widget

    def create_pic_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        self.show_rgb_lab_checkbox = QCheckBox("显示 RGB/LAB 和统计功能")
        self.show_rgb_lab_checkbox.toggled.connect(self.on_show_rgb_lab_toggled)

        self.show_histogram_checkbox = QCheckBox("显示亮度直方图")
        self.show_histogram_checkbox.toggled.connect(self.on_show_histogram_toggled)

        self.clear_cache_checkbox = QCheckBox("清除缓存")
        self.clear_cache_checkbox.toggled.connect(self.on_clear_cache_toggled)

        layout.addWidget(self.show_rgb_lab_checkbox)
        layout.addWidget(self.show_histogram_checkbox)
        layout.addWidget(self.clear_cache_checkbox)
        layout.addStretch()
        return widget

    def on_show_rgb_lab_toggled(self, state):
        self.config_manager.set_setting('settings', 'rgb_lab_enabled', state, config_name='pic')
        self.pic_settings_changed.emit('show_rgb_lab', state)

    def on_show_histogram_toggled(self, state):
        self.config_manager.set_setting('settings', 'histogram_enabled', state, config_name='pic')
        self.pic_settings_changed.emit('show_histogram', state)

    def on_clear_cache_toggled(self, state):
        self.config_manager.set_setting('settings', 'clear_cache', state, config_name='pic')
        self.pic_settings_changed.emit('clear_cache', state)

    def on_nav_item_clicked(self, item):
        # Disconnect signal to prevent loop, and reconnect in a finally block
        # to ensure it's always restored.
        try:
            self.scroll_area.verticalScrollBar().valueChanged.disconnect(self.on_scroll)
        except TypeError:
            pass  # Slot was not connected
        
        try:
            section_widget = getattr(item, 'section_widget', None)
            if section_widget:
                self.scroll_area.verticalScrollBar().setValue(section_widget.y())
        finally:
            self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)

    def on_scroll(self, value):
        # The connect/disconnect for itemClicked is not needed here because
        # setCurrentRow does not emit the itemClicked signal.
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        # If scrolled to the bottom, highlight the last item.
        if scroll_pos == scroll_bar.maximum():
            if self.nav_list.count() > 0:
                self.nav_list.setCurrentRow(self.nav_list.count() - 1)
        else:
            # Find which section is most visible
            current_row = -1
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                widget = getattr(item, 'section_widget', None)
                if widget:
                    # The active section is the last one whose top is at or above the viewport's top.
                    if widget.y() - 20 <= scroll_pos:
                        current_row = i
            
            if current_row != -1:
                self.nav_list.setCurrentRow(current_row)

    def create_about_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 版本和联系信息
        title_label = QLabel(f"AEBOX({VERSION})高通AEC辅助调试工具集")
        font = title_label.font()
        font.setPointSize(14)
        title_label.setFont(font)
        
        auter_description_label = QLabel("联系方式：<a href=\"https://github.com/965962591/aebox_releases\">barrymchen@gmail.com</a>")
        auter_description_label.setFont(font)
        auter_description_label.setOpenExternalLinks(True)
        
        layout.addWidget(title_label)
        layout.addWidget(auter_description_label)

        # 按钮
        button_layout = QHBoxLayout()
        check_update_button = QPushButton("使用文档")
        check_update_button.clicked.connect(self.open_doc)
        check_update_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.25);
                }
            """
        )
        homepage_button = QPushButton("github主页")
        homepage_button.clicked.connect(self.open_homepage_url)
        homepage_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.25);
                }
            """
        )
        feedback_button = QPushButton("建议反馈")
        feedback_button.clicked.connect(self.open_feedback_url)
        feedback_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.25);
                }
            """
        )
        faq_button = QPushButton("常见问题")
        faq_button.clicked.connect(self.open_faq_url)
        faq_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.25);
                }
            """
        )

        button_layout.addWidget(check_update_button)
        button_layout.addWidget(homepage_button)
        button_layout.addWidget(feedback_button)
        button_layout.addWidget(faq_button)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return widget

    def create_docs_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = QTextBrowser()
        browser.setFrameShape(QFrame.NoFrame)
        browser.setStyleSheet("QTextBrowser { background-color: transparent; border: none; }")
        
        readme_path = os.path.join(os.path.dirname(__file__), "README.md")
        content = self.read_markdown_file(readme_path)
        browser.setMarkdown(content)

        def update_height():
            browser.setMinimumHeight(int(browser.document().size().height()))

        browser.document().contentsChanged.connect(update_height)
        QTimer.singleShot(0, update_height)
        
        layout.addWidget(browser)
        return widget

    def create_update_log_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = QTextBrowser()
        browser.setFrameShape(QFrame.NoFrame)
        browser.setStyleSheet("QTextBrowser { background-color: transparent; border: none; }")

        log_path = os.path.join(os.path.dirname(__file__), "update_log.md")
        content = self.read_markdown_file(log_path)
        browser.setMarkdown(content)

        def update_height():
            browser.setMinimumHeight(int(browser.document().size().height()))
        
        browser.document().contentsChanged.connect(update_height)
        QTimer.singleShot(0, update_height)

        layout.addWidget(browser)
        return widget

    def read_markdown_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return f"# 错误\n无法找到文件: {os.path.basename(filepath)}"

    def open_doc(self):
        QDesktopServices.openUrl(
            QUrl("https://aebox-doc-965962591s-projects.vercel.app/#/")
        )

    def open_feedback_url(self):
        QDesktopServices.openUrl(QUrl("https://tally.so/r/w86ldl"))

    def open_homepage_url(self):
        QDesktopServices.openUrl(QUrl("https://github.com/965962591/aebox_releases"))

    def open_faq_url(self):
        QDesktopServices.openUrl(
            QUrl("https://github.com/965962591/aebox_releases/blob/main/README.md")
        )

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    settings_window = SettingsWindow()
    settings_window.show()
    sys.exit(app.exec_())