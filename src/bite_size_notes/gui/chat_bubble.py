"""Transcript line widget for displaying a single transcript segment."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextOption
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

from bite_size_notes.models.transcript import TranscriptSegment


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
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)

    def _adjust_height(self):
        doc_height = int(self.document().size().height())
        margins = self.contentsMargins()
        height = doc_height + margins.top() + margins.bottom() + 4
        self.setFixedHeight(max(height, 28))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_height()

    def showEvent(self, event):
        super().showEvent(event)
        self._adjust_height()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focus_lost.emit()


class TranscriptLineWidget(QFrame):
    """A single plain-text line representing one transcript segment."""

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

        self.setObjectName("transcriptLine")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        inner = QVBoxLayout(self)
        inner.setContentsMargins(10, 6, 10, 6)
        inner.setSpacing(2)

        # Header row: timestamp + speaker + delete button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        header = QLabel(f"[{segment.time_str}] {speaker}")
        header.setObjectName("speakerMe" if is_me else "speakerOthers")
        header.setFont(QFont("Consolas", 9))
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

        self.setContentsMargins(8, 2, 8, 2)

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
