"""Application entry point."""

import logging
import os
import sys
from pathlib import Path


def _assets_dir() -> Path:
    """Return the assets directory, handling PyInstaller frozen bundles."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).parent / "assets"


def _main_inner():
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication, QSplashScreen

    from bite_size_notes.gui.main_window import MainWindow
    from bite_size_notes.gui.themes import build_stylesheet, get_palette
    from bite_size_notes.utils.config import AppConfig

    app = QApplication(sys.argv)
    app.setApplicationName("Bite-Size Notes")
    app.setOrganizationName("pcphil")

    # Apply theme
    config = AppConfig()
    app.setStyleSheet(build_stylesheet(get_palette(config.theme)))

    logo_path = _assets_dir() / "logo.ico"
    app.setWindowIcon(QIcon(str(logo_path)))

    # Show splash screen
    splash = QSplashScreen(QPixmap(str(logo_path)))
    splash.show()
    app.processEvents()

    window = MainWindow(app=app)
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


def _setup_logging():
    """Configure logging to app.log and stderr."""
    log_dir = Path(os.environ.get("APPDATA", Path.home())) / "Bite-Size Notes"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(fmt))

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter(fmt))

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stderr_handler])


def main():
    _setup_logging()
    try:
        _main_inner()
    except Exception:
        import traceback

        msg = traceback.format_exc()
        # Always write crash log to disk (visible even in windowed mode)
        try:
            log_dir = Path(os.environ.get("APPDATA", Path.home())) / "Bite-Size Notes"
            log_dir.mkdir(exist_ok=True)
            crash_log = log_dir / "crash.log"
            crash_log.write_text(msg, encoding="utf-8")
        except Exception:
            pass  # If we can't write the log, still try to show the dialog
        # Try Qt dialog first, fall back to native Windows MessageBox
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Bite-Size Notes \u2013 Fatal Error", msg)
        except Exception:
            if sys.platform == "win32":
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0, msg, "Bite-Size Notes \u2013 Fatal Error", 0x10
                )
        # Keep console open in debug/frozen builds so the error is readable
        if getattr(sys, "frozen", False):
            print(f"\n{msg}")
            input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
