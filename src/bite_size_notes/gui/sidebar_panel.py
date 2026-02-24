"""Left sidebar panel with session list and settings access."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SidebarPanel(QWidget):
    """Collapsible left panel showing session history and settings access."""

    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # --- Sessions header + new button ---
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        sessions_label = QLabel("Sessions")
        sessions_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sessions_label.setStyleSheet("color: #d4d4d4; background: transparent;")
        header_row.addWidget(sessions_label)
        header_row.addStretch()

        new_btn = QPushButton("+")
        new_btn.setFixedSize(28, 28)
        new_btn.setToolTip("New session")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        header_row.addWidget(new_btn)

        layout.addLayout(header_row)

        # --- Session list ---
        self._session_list = QListWidget()
        self._session_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 6px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #37373d;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
        """)

        # Placeholder sessions
        for text in ["Current Session"]:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self._session_list.addItem(item)
        self._session_list.setCurrentRow(0)

        layout.addWidget(self._session_list, 1)

        # --- Settings button ---
        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(settings_btn)

        # Panel background
        self.setStyleSheet("""
            SidebarPanel {
                background-color: #1e1e1e;
                border-right: 1px solid #333;
            }
        """)
