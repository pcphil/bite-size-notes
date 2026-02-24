"""Application entry point."""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from bite_size_notes.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bite-Size Notes")
    app.setOrganizationName("BiteSize")

    logo_path = Path(__file__).parent / "assets" / "logo.png"
    app.setWindowIcon(QIcon(str(logo_path)))

    # Show splash screen
    splash = QSplashScreen(QPixmap(str(logo_path)))
    splash.show()
    app.processEvents()

    window = MainWindow()
    window.show()
    splash.finish(window)

    sys.exit(app.exec())
