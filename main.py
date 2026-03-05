import sys
from PyQt5.QtWidgets import QApplication
from main_window import ARIAWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ARIAWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()