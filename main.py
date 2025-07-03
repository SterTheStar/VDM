import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from vdm.app import MainWindow
from vdm.logic.utils import resource_path

def apply_dark_theme(app):
    dark_stylesheet = """
    QMainWindow, QWidget, QDialog {
        background: #181a1b;
        color: #e0e0e0;
    }
    QLabel {
        color: #e0e0e0;
    }
    QPushButton, QToolButton {
        background: #232526;
        color: #e0e0e0;
        border: 1px solid #232526;
        border-radius: 6px;
        padding: 6px 12px;
    }
    QPushButton:hover, QToolButton:hover {
        background: #2d3133;
        border: 1px solid #3a8dde;
    }
    QPushButton:pressed, QToolButton:pressed {
        background: #1a1c1d;
        border: 1px solid #1976d2;
    }
    QTableWidget, QScrollArea, QAbstractItemView {
        background: #111112;
        color: #e0e0e0;
        border: none;
    }
    QHeaderView::section {
        background: #232526;
        color: #e0e0e0;
        border: none;
        font-weight: bold;
    }
    QProgressBar {
        background: #232526;
        border: 1px solid #232526;
        border-radius: 7px;
        text-align: center;
        color: #e0e0e0;
        height: 14px;
    }
    QProgressBar::chunk {
        background-color: #3a8dde;
        border-radius: 7px;
    }
    QComboBox {
        background: #232526;
        color: #e0e0e0;
        border: 1px solid #232526;
        border-radius: 6px;
        padding: 4px 8px;
    }
    QComboBox QAbstractItemView {
        background: #111112;
        color: #e0e0e0;
        selection-background-color: #3a8dde;
        selection-color: #fff;
    }
    QFrame {
        background: #232526;
        border-radius: 8px;
        border: none;
    }
    QDialog {
        background: #181a1b;
    }
    """
    app.setStyleSheet(dark_stylesheet)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    app.setWindowIcon(QIcon(resource_path('icon.ico')))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 