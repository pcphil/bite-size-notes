"""Persistent storage for transcript sessions as individual JSON files."""

import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from bite_size_notes.models.transcript import TranscriptSession


class SessionStore:
    """Manages a directory of session JSON files."""

    def __init__(self):
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        self._dir = Path(app_data) / "sessions"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._migrate_from_old_org()

    def list_sessions(self) -> list[dict]:
        """Return [{id, title, start_time}, ...] sorted by start_time descending."""
        sessions = []
        for path in self._dir.glob("*.json"):
            try:
                session = TranscriptSession.load(path)
                sessions.append(
                    {
                        "id": session.id,
                        "title": session.title,
                        "start_time": session.start_time,
                    }
                )
            except Exception:
                continue
        sessions.sort(key=lambda s: s["start_time"], reverse=True)
        return sessions

    def save_session(self, session: TranscriptSession) -> None:
        """Save a session to {id}.json."""
        session.save(self._dir / f"{session.id}.json")

    def load_session(self, session_id: str) -> TranscriptSession:
        """Load a full session by ID."""
        path = self._dir / f"{session_id}.json"
        return TranscriptSession.load(path)

    def delete_session(self, session_id: str) -> None:
        """Delete the JSON file for the given session ID."""
        path = self._dir / f"{session_id}.json"
        if path.exists():
            path.unlink()

    def _migrate_from_old_org(self):
        """One-time migration of session files from the old 'BiteSize' org dir."""
        if sys.platform == "win32":
            old_dir = Path.home() / "AppData/Local/BiteSize/Bite-Size-Notes/sessions"
        elif sys.platform == "darwin":
            old_dir = (
                Path.home()
                / "Library/Application Support/BiteSize/Bite-Size-Notes/sessions"
            )
        else:
            old_dir = Path.home() / ".local/share/BiteSize/Bite-Size-Notes/sessions"

        if not old_dir.is_dir():
            return

        for src in old_dir.glob("*.json"):
            dst = self._dir / src.name
            if not dst.exists():
                shutil.move(str(src), str(dst))
