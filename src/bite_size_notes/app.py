"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from bite_size_notes.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bite-Size Notes")
    app.setOrganizationName("BiteSize")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
