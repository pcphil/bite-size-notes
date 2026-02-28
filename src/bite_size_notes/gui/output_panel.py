"""Right-side output panel for displaying generated content."""

from PySide6.QtCore import Qt, Signal
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

    bite_size_clicked = Signal()
    notes_toggled = Signal()
    export_output_clicked = Signal()
    collapse_toggled = Signal(bool)  # emits True when collapsed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self.setMinimumWidth(180)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top button row
        self._btn_row = QHBoxLayout()
        self._btn_row.setSpacing(4)
        self._btn_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._bite_size_btn = QPushButton("Bite Size It")
        self._bite_size_btn.setFixedHeight(28)
        self._btn_row.addWidget(self._bite_size_btn)
        self._bite_size_btn.clicked.connect(self.bite_size_clicked.emit)

        self._copy_btn = QPushButton("\U0001f4cb")
        self._copy_btn.setObjectName("iconBtn")
        self._copy_btn.setFixedSize(28, 28)
        self._copy_btn.setToolTip("Copy")
        self._btn_row.addWidget(self._copy_btn)

        self._export_btn = QPushButton("\U0001f4e5")
        self._export_btn.setObjectName("iconBtn")
        self._export_btn.setFixedSize(28, 28)
        self._export_btn.setToolTip("Export output")
        self._export_btn.clicked.connect(self.export_output_clicked.emit)
        self._btn_row.addWidget(self._export_btn)

        self._btn_row.addStretch()

        self._collapse_btn = QPushButton("\u00bb")
        self._collapse_btn.setObjectName("iconBtn")
        self._collapse_btn.setFixedSize(28, 28)
        self._collapse_btn.setToolTip("Collapse panel")
        self._collapse_btn.clicked.connect(self.toggle_collapse)
        self._btn_row.addWidget(self._collapse_btn)

        layout.addLayout(self._btn_row)

        # Text area
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlaceholderText("Output will appear here...")
        self._text_edit.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self._text_edit)

        # Bottom row with notes button right-aligned
        self._bottom_row = QHBoxLayout()
        self._bottom_row.setContentsMargins(0, 0, 0, 0)
        self._bottom_row.addStretch()
        self._notes_btn = QPushButton("\U0001f4dd")
        self._notes_btn.setObjectName("iconBtn")
        self._notes_btn.setFixedSize(28, 28)
        self._notes_btn.setToolTip("Toggle notes")
        self._notes_btn.clicked.connect(self.notes_toggled.emit)
        self._bottom_row.addWidget(self._notes_btn)
        layout.addLayout(self._bottom_row)

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._bite_size_btn.hide()
            self._copy_btn.hide()
            self._export_btn.hide()
            self._text_edit.hide()
            self._notes_btn.hide()
            self._collapse_btn.setText("\u00ab")
            self._collapse_btn.setToolTip("Expand panel")
            self.setMinimumWidth(40)
            self.setMaximumWidth(40)
        else:
            self._bite_size_btn.show()
            self._copy_btn.show()
            self._export_btn.show()
            self._text_edit.show()
            self._notes_btn.show()
            self._collapse_btn.setText("\u00bb")
            self._collapse_btn.setToolTip("Collapse panel")
            self.setMinimumWidth(180)
            self.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
        self.collapse_toggled.emit(self._collapsed)

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    def append_text(self, text: str):
        self._text_edit.appendPlainText(text)

    def set_text(self, text: str):
        self._text_edit.setPlainText(text)

    def text(self) -> str:
        return self._text_edit.toPlainText()

    def clear(self):
        self._text_edit.clear()
