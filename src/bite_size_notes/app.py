"""Application entry point."""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from bite_size_notes.gui.main_window import MainWindow
from bite_size_notes.gui.themes import build_stylesheet, get_palette
from bite_size_notes.utils.config import AppConfig


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bite-Size Notes")
    app.setOrganizationName("BiteSize")

    # Apply theme
    config = AppConfig()
    app.setStyleSheet(build_stylesheet(get_palette(config.theme)))

    logo_path = Path(__file__).parent / "assets" / "logo.png"
    app.setWindowIcon(QIcon(str(logo_path)))

    # Show splash screen
    splash = QSplashScreen(QPixmap(str(logo_path)))
    splash.show()
    app.processEvents()

    window = MainWindow(app=app)
    window.show()
    splash.finish(window)

    sys.exit(app.exec())
