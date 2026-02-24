"""Right-side notes panel for freeform note-taking during meetings."""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class NotesPanel(QWidget):
    """Panel for taking notes alongside the transcript."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("Notes")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #d4d4d4; background: transparent;")
        layout.addWidget(header)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setPlaceholderText("Type your notes here...")
        self._text_edit.setFont(QFont("Segoe UI", 11))
        self._text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self._text_edit)

        self.setStyleSheet("""
            NotesPanel {
                background-color: #1e1e1e;
                border-left: 1px solid #333;
            }
        """)

    def get_text(self) -> str:
        return self._text_edit.toPlainText()

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)

    def clear(self):
        self._text_edit.clear()
