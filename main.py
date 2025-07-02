import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from vdm.app import MainWindow
from vdm.logic.utils import resource_path

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('icon.ico')))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 