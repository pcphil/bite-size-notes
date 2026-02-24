"""Right-side output panel for displaying generated content."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OutputPanel(QWidget):
    """Panel for displaying output content alongside the transcript."""

    notes_toggled = Signal()
    export_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Button row instead of header
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        notes_btn = QPushButton("\U0001f4dd")
        notes_btn.setToolTip("Toggle notes")
        notes_btn.clicked.connect(self.notes_toggled.emit)
        btn_row.addWidget(notes_btn)

        for label in ("Bite Size It", "Tone", "Model"):
            btn = QPushButton(label)
            btn_row.addWidget(btn)

        copy_btn = QPushButton("\U0001f4cb")
        copy_btn.setToolTip("Copy")
        btn_row.addWidget(copy_btn)

        export_btn = QPushButton("\U0001f4e5")
        export_btn.setToolTip("Export")
        export_btn.clicked.connect(self.export_clicked.emit)
        btn_row.addWidget(export_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlaceholderText("Output will appear here...")
        self._text_edit.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self._text_edit)

    def append_text(self, text: str):
        self._text_edit.appendPlainText(text)

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)

    def clear(self):
        self._text_edit.clear()
