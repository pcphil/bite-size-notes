"""Live transcript display widget."""

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from bite_size_notes.models.transcript import TranscriptSegment

SOURCE_COLORS = {
    "Me": QColor("#2196F3"),  # Blue
    "Others": QColor("#4CAF50"),  # Green
    "mic": QColor("#2196F3"),
    "loopback": QColor("#4CAF50"),
}

TIMESTAMP_COLOR = QColor("#9E9E9E")  # Grey


class TranscriptView(QTextEdit):
    """Read-only text widget that displays color-coded transcript segments."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Segoe UI", 11))
        self.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 8px;
            }
        """
        )

    def append_segment(self, segment: TranscriptSegment):
        """Append a new transcript segment with formatting."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Timestamp
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(TIMESTAMP_COLOR)
        ts_fmt.setFont(QFont("Consolas", 10))
        cursor.insertText(f"[{segment.time_str}] ", ts_fmt)

        # Speaker label
        label = segment.speaker_label or segment.source
        label_fmt = QTextCharFormat()
        label_fmt.setForeground(SOURCE_COLORS.get(label, QColor("#d4d4d4")))
        label_fmt.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(f"{label}: ", label_fmt)

        # Text
        text_fmt = QTextCharFormat()
        text_fmt.setForeground(QColor("#d4d4d4"))
        cursor.insertText(f"{segment.text}\n", text_fmt)

        # Auto-scroll
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_transcript(self):
        """Clear all transcript text."""
        self.clear()
