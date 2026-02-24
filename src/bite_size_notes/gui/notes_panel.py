"""Floating notes panel for freeform note-taking during meetings."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class NotesPanel(QFrame):
    """Floating pop-in panel for taking notes alongside the transcript."""

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 250)
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            NotesPanel {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header row with title and close button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Notes")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #d4d4d4; background: transparent;")
        header_row.addWidget(header)
        header_row.addStretch()

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip("Close notes")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #d4d4d4;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #333;
                border-radius: 4px;
            }
        """)
        close_btn.clicked.connect(self.close_requested.emit)
        header_row.addWidget(close_btn)

        layout.addLayout(header_row)

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

    def get_text(self) -> str:
        return self._text_edit.toPlainText()

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)

    def clear(self):
        self._text_edit.clear()
