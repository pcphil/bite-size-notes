"""Live transcript display as a scrollable list of chat bubbles."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from bite_size_notes.gui.chat_bubble import ChatBubbleWidget
from bite_size_notes.models.transcript import TranscriptSegment


class TranscriptView(QScrollArea):
    """Scrollable container of chat-bubble widgets, one per transcript segment."""

    text_edited = Signal(int, str)  # (segment_index, new_text)
    delete_requested = Signal(int)  # segment_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background-color: #1e1e1e;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.addStretch()

        self.setWidget(self._container)

        self._bubbles: list[ChatBubbleWidget] = []
        self._editable = False

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
        self._layout.insertWidget(self._layout.count() - 1, bubble)
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
            self._layout.removeWidget(bubble)
            bubble.deleteLater()
        self._bubbles.clear()

    def _on_delete_requested(self, index: int):
        """Remove a bubble and re-index the remaining ones."""
        if index < 0 or index >= len(self._bubbles):
            return
        bubble = self._bubbles.pop(index)
        self._layout.removeWidget(bubble)
        bubble.deleteLater()

        # Re-index remaining bubbles so signals carry correct indices
        for i, b in enumerate(self._bubbles):
            b._segment_index = i

        self.delete_requested.emit(index)

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
