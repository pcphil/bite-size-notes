"""Live transcript display as a scrollable list of chat bubbles."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bite_size_notes.gui.chat_bubble import ChatBubbleWidget
from bite_size_notes.models.transcript import TranscriptSegment


class TranscriptView(QWidget):
    """Center panel with control buttons and scrollable chat bubbles."""

    text_edited = Signal(int, str)  # (segment_index, new_text)
    delete_requested = Signal(int)  # segment_index
    record_clicked = Signal()
    clear_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Button row ---
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 6, 8, 6)
        btn_row.setSpacing(6)

        self._record_btn = QPushButton("\u25b6")  # ▶ play icon
        self._record_btn.setToolTip("Record (Ctrl+R)")
        self._record_btn.setFixedSize(32, 32)
        self._record_btn.clicked.connect(self.record_clicked.emit)
        btn_row.addWidget(self._record_btn)

        self._clear_btn = QPushButton("\U0001f5d1")  # 🗑 trash icon
        self._clear_btn.setToolTip("Clear")
        self._clear_btn.setFixedSize(32, 32)
        self._clear_btn.clicked.connect(self.clear_clicked.emit)
        btn_row.addWidget(self._clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # --- Scrollable transcript area ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._container = QWidget()
        self._container.setObjectName("transcriptContainer")
        self._inner_layout = QVBoxLayout(self._container)
        self._inner_layout.setContentsMargins(0, 8, 0, 8)
        self._inner_layout.setSpacing(4)
        self._inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._inner_layout.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        self._bubbles: list[ChatBubbleWidget] = []
        self._editable = False

    def set_recording(self, recording: bool):
        """Toggle the record button icon between stop and play."""
        if recording:
            self._record_btn.setText("\u23f9")  # ⏹ stop icon
            self._record_btn.setToolTip("Stop (Ctrl+R)")
        else:
            self._record_btn.setText("\u25b6")  # ▶ play icon
            self._record_btn.setToolTip("Record (Ctrl+R)")

    def append_segment(self, segment: TranscriptSegment):
        """Add a new chat bubble for a transcript segment."""
        bubble = ChatBubbleWidget(
            segment=segment,
            segment_index=len(self._bubbles),
            editable=self._editable,
        )
        bubble.text_edited.connect(self.text_edited)
        bubble.delete_requested.connect(self._on_delete_requested)

        # Insert before the trailing stretch
        self._inner_layout.insertWidget(self._inner_layout.count() - 1, bubble)
        self._bubbles.append(bubble)

        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def set_editable(self, editable: bool):
        """Toggle edit mode on all bubbles."""
        self._editable = editable
        for bubble in self._bubbles:
            bubble.set_editable(editable)

    def clear_transcript(self):
        """Remove all chat bubbles."""
        for bubble in self._bubbles:
            self._inner_layout.removeWidget(bubble)
            bubble.deleteLater()
        self._bubbles.clear()

    def _on_delete_requested(self, index: int):
        """Remove a bubble and re-index the remaining ones."""
        if index < 0 or index >= len(self._bubbles):
            return
        bubble = self._bubbles.pop(index)
        self._inner_layout.removeWidget(bubble)
        bubble.deleteLater()

        # Re-index remaining bubbles so signals carry correct indices
        for i, b in enumerate(self._bubbles):
            b._segment_index = i

        self.delete_requested.emit(index)

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
