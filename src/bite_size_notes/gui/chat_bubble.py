"""Chat-bubble widget for displaying a single transcript segment."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bite_size_notes.gui.themes import get_palette
from bite_size_notes.models.transcript import TranscriptSegment
from bite_size_notes.utils.config import AppConfig


def _current_palette():
    config = AppConfig()
    return get_palette(config.theme)


class _AutoResizePlainTextEdit(QPlainTextEdit):
    """A QPlainTextEdit that auto-sizes its height to fit content."""

    focus_lost = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.document().documentLayout().documentSizeChanged.connect(
            self._adjust_height
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _adjust_height(self):
        doc_height = int(self.document().size().height())
        margins = self.contentsMargins()
        height = doc_height + margins.top() + margins.bottom() + 4
        self.setFixedHeight(max(height, 28))

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_lost.emit()


class ChatBubbleWidget(QFrame):
    """A single chat-bubble representing one transcript segment."""

    text_edited = Signal(int, str)  # (segment_index, new_text)
    delete_requested = Signal(int)  # segment_index

    def __init__(
        self,
        segment: TranscriptSegment,
        segment_index: int,
        editable: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._segment_index = segment_index
        self._original_text = segment.text

        speaker = segment.speaker_label or segment.source
        is_me = speaker == "Me"

        p = _current_palette()
        bg = p["bubble_me_bg"] if is_me else p["bubble_others_bg"]
        color = p["bubble_me_color"] if is_me else p["bubble_others_color"]

        # Frame styling — dynamic per bubble
        self.setObjectName("chatBubble")
        self.setStyleSheet(f"""
            #chatBubble {{
                background-color: {bg};
                border-radius: 12px;
                padding: 4px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Layout inside bubble
        inner = QVBoxLayout(self)
        inner.setContentsMargins(10, 6, 10, 6)
        inner.setSpacing(2)

        # Header row: timestamp + speaker + delete button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        header = QLabel(f"[{segment.time_str}] {speaker}")
        header.setFont(QFont("Consolas", 9))
        header.setStyleSheet(f"color: {color}; background: transparent;")
        header_row.addWidget(header)
        header_row.addStretch()

        self._delete_btn = QPushButton("\u00d7")
        self._delete_btn.setFixedSize(20, 20)
        self._delete_btn.setToolTip("Delete this segment")
        self._delete_btn.clicked.connect(
            lambda: self.delete_requested.emit(self._segment_index)
        )
        self._delete_btn.setVisible(editable)
        header_row.addWidget(self._delete_btn)

        inner.addLayout(header_row)

        # Text body
        self._text_edit = _AutoResizePlainTextEdit()
        self._text_edit.setPlainText(segment.text)
        self._text_edit.setReadOnly(not editable)
        self._text_edit.setFont(QFont("Segoe UI", 11))
        self._text_edit.focus_lost.connect(self._on_focus_lost)
        inner.addWidget(self._text_edit)

        # Alignment via margins: "Me" pushed right, "Others" pushed left
        if is_me:
            self.setContentsMargins(120, 2, 8, 2)
        else:
            self.setContentsMargins(8, 2, 120, 2)

    def set_editable(self, editable: bool):
        self._text_edit.setReadOnly(not editable)
        self._delete_btn.setVisible(editable)
        if editable:
            self._text_edit.setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self._text_edit.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_focus_lost(self):
        new_text = self._text_edit.toPlainText().strip()
        if new_text != self._original_text:
            self._original_text = new_text
            self.text_edited.emit(self._segment_index, new_text)
