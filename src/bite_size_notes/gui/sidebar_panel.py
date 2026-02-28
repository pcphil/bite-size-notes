"""Left sidebar panel with session list and settings access."""

from PySide6.QtCore import QSize, Qt, Signal
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

from bite_size_notes.models.session_store import SessionStore

_ROLE_SESSION_ID = Qt.ItemDataRole.UserRole


class _SessionItemWidget(QWidget):
    """Custom widget for a session list item with title, date, and action buttons."""

    delete_clicked = Signal(str)  # session_id
    rename_clicked = Signal(str)  # session_id

    def __init__(self, session_id: str, title: str, start_time_str: str, parent=None):
        super().__init__(parent)
        self._session_id = session_id

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(0)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10))
        info.addWidget(title_label)

        date_label = QLabel(start_time_str)
        date_label.setObjectName("sessionDate")
        date_label.setFont(QFont("Segoe UI", 8))
        info.addWidget(date_label)

        layout.addLayout(info, 1)

        rename_btn = QPushButton("\u270f")
        rename_btn.setFixedSize(20, 20)
        rename_btn.setToolTip("Rename session")
        rename_btn.clicked.connect(lambda: self.rename_clicked.emit(self._session_id))
        layout.addWidget(rename_btn)

        delete_btn = QPushButton("\u00d7")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setToolTip("Delete session")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._session_id))
        layout.addWidget(delete_btn)


class SidebarPanel(QWidget):
    """Left panel showing session history and settings access."""

    settings_requested = Signal()
    session_selected = Signal(str)  # session id
    new_session_requested = Signal()
    delete_session_requested = Signal(str)  # session id
    rename_session_requested = Signal(str)  # session id

    def __init__(self, store: SessionStore, parent=None):
        super().__init__(parent)
        self._store = store
        self._active_session_id: str | None = None
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
        self._new_btn.clicked.connect(self.new_session_requested.emit)
        header_row.addWidget(self._new_btn)

        layout.addLayout(header_row)

        # --- Session list ---
        self._session_list = QListWidget()
        self._session_list.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self._session_list, 1)

        # --- Settings button ---
        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self._settings_btn)

    def refresh_sessions(self, active_id: str | None = None):
        """Repopulate the session list from the store."""
        self._session_list.blockSignals(True)
        self._session_list.clear()

        sessions = self._store.list_sessions()
        select_row = -1

        for i, meta in enumerate(sessions):
            sid = meta["id"]
            item = QListWidgetItem()
            item.setData(_ROLE_SESSION_ID, sid)
            item.setSizeHint(QSize(200, 44))
            self._session_list.addItem(item)

            widget = _SessionItemWidget(
                session_id=sid,
                title=meta["title"],
                start_time_str=meta["start_time"].strftime("%Y-%m-%d %H:%M"),
            )
            widget.delete_clicked.connect(self.delete_session_requested.emit)
            widget.rename_clicked.connect(self.rename_session_requested.emit)
            self._session_list.setItemWidget(item, widget)

            if sid == (active_id or self._active_session_id):
                select_row = i

        self._session_list.blockSignals(False)

        if select_row >= 0:
            self._session_list.setCurrentRow(select_row)

    def set_active_session(self, session_id: str):
        """Highlight the given session in the list."""
        self._active_session_id = session_id
        for i in range(self._session_list.count()):
            item = self._session_list.item(i)
            if item.data(_ROLE_SESSION_ID) == session_id:
                self._session_list.blockSignals(True)
                self._session_list.setCurrentRow(i)
                self._session_list.blockSignals(False)
                return

    def _on_item_changed(self, current: QListWidgetItem | None, _prev):
        if current is None:
            return
        sid = current.data(_ROLE_SESSION_ID)
        if sid and sid != self._active_session_id:
            self._active_session_id = sid
            self.session_selected.emit(sid)

