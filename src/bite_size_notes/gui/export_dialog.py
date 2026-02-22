"""Export dialog for saving transcripts."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from bite_size_notes.models.transcript import TranscriptSession

EXPORT_FILTERS = {
    "Plain Text (*.txt)": "txt",
    "SRT Subtitles (*.srt)": "srt",
    "Markdown (*.md)": "md",
    "JSON (*.json)": "json",
}


def export_transcript(session: TranscriptSession, parent: QWidget | None = None):
    """Show a file save dialog and export the transcript."""
    if not session.segments:
        QMessageBox.information(parent, "Export", "No transcript to export.")
        return

    filter_str = ";;".join(EXPORT_FILTERS.keys())
    file_path, selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Export Transcript",
        f"transcript_{session.start_time.strftime('%Y%m%d_%H%M')}",
        filter_str,
    )

    if not file_path:
        return

    ext = EXPORT_FILTERS.get(selected_filter, "txt")
    path = Path(file_path)
    if not path.suffix:
        path = path.with_suffix(f".{ext}")

    exporters = {
        "txt": session.to_text,
        "srt": session.to_srt,
        "md": session.to_markdown,
        "json": session.to_json,
    }

    content = exporters.get(ext, session.to_text)()
    path.write_text(content, encoding="utf-8")

    QMessageBox.information(
        parent, "Export", f"Transcript exported to:\n{path}"
    )
