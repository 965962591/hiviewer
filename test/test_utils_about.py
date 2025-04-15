import os
import sys
from PyQt5.QtWidgets import QApplication

# 在运行测试文件前，将项目根目录添加到Python路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# 导入需要测试的自定义关于对话框
from src.utils.about import AboutDialog 



# 示例用法
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AboutDialog()
    dialog.show()
    sys.exit(app.exec_())