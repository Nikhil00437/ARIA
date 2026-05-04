import sys, os
import warnings

# Suppress pynvml deprecation warning from torch.cuda
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.cuda")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from main_window import ARIAWindow

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("ARIA")
    app.setOrganizationName("ARIA Local")
    window = ARIAWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()