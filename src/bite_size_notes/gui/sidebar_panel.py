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

        # --- Sessions header + collapse/new buttons ---
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self._sessions_label = QLabel("Sessions")
        self._sessions_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_row.addWidget(self._sessions_label)
        header_row.addStretch()

        self._new_btn = QPushButton("+")
        self._new_btn.setFixedSize(28, 28)
        self._new_btn.setToolTip("New session")
        header_row.addWidget(self._new_btn)

        self._collapse_btn = QPushButton("\u00ab")
        self._collapse_btn.setFixedSize(28, 28)
        self._collapse_btn.setToolTip("Collapse sidebar")
        self._collapse_btn.clicked.connect(self.toggle_collapse)
        header_row.addWidget(self._collapse_btn)

        layout.addLayout(header_row)

        # --- Session list ---
        self._session_list = QListWidget()

        # Placeholder sessions
        for text in ["Current Session"]:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self._session_list.addItem(item)
        self._session_list.setCurrentRow(0)

        layout.addWidget(self._session_list, 1)

        # --- Settings button ---
        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self._settings_btn)

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._sessions_label.hide()
            self._new_btn.hide()
            self._session_list.hide()
            self._settings_btn.hide()
            self._collapse_btn.setText("\u00bb")
            self._collapse_btn.setToolTip("Expand sidebar")
            self.setMinimumWidth(40)
            self.setMaximumWidth(40)
        else:
            self._sessions_label.show()
            self._new_btn.show()
            self._session_list.show()
            self._settings_btn.show()
            self._collapse_btn.setText("\u00ab")
            self._collapse_btn.setToolTip("Collapse sidebar")
            self.setMinimumWidth(180)
            self.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
        self.collapse_toggled.emit(self._collapsed)

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed
