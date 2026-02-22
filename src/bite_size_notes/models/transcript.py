"""Transcript data model and session management."""

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TranscriptSegment:
    """A single transcribed segment of audio."""

    text: str
    source: str  # "mic" or "loopback"
    timestamp: float  # seconds from recording start
    speaker_label: str = ""  # "Me" or "Others"

    @property
    def label(self) -> str:
        return self.speaker_label or self.source

    @property
    def time_str(self) -> str:
        minutes = int(self.timestamp // 60)
        seconds = int(self.timestamp % 60)
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class TranscriptSession:
    """A complete recording session with transcript segments."""

    segments: list[TranscriptSegment] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)

    def add_segment(self, segment: TranscriptSegment):
        self.segments.append(segment)

    def clear(self):
        self.segments.clear()
        self.start_time = datetime.now()

    def to_text(self) -> str:
        lines = []
        for seg in self.segments:
            lines.append(f"[{seg.time_str}] {seg.label}: {seg.text}")
        return "\n".join(lines)

    def to_srt(self) -> str:
        lines = []
        for i, seg in enumerate(self.segments, 1):
            start_s = seg.timestamp
            # Estimate end as start + 5s or next segment's start
            if i < len(self.segments):
                end_s = self.segments[i].timestamp
            else:
                end_s = start_s + 5.0

            lines.append(str(i))
            lines.append(f"{_srt_time(start_s)} --> {_srt_time(end_s)}")
            lines.append(f"{seg.label}: {seg.text}")
            lines.append("")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = [
            f"# Meeting Transcript",
            f"**Date**: {self.start_time.strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
        ]
        for seg in self.segments:
            lines.append(f"**[{seg.time_str}] {seg.label}**: {seg.text}")
            lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        data = {
            "start_time": self.start_time.isoformat(),
            "segments": [
                {
                    "text": seg.text,
                    "source": seg.source,
                    "timestamp": seg.timestamp,
                    "speaker_label": seg.label,
                    "time_str": seg.time_str,
                }
                for seg in self.segments
            ],
        }
        return json.dumps(data, indent=2)


def _srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
