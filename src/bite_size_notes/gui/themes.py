"""Centralized theme palettes and stylesheet generation."""

from __future__ import annotations

from typing import Any

DARK: dict[str, Any] = {
    "bg_primary": "#1e1e1e",
    "bg_secondary": "#252526",
    "text": "#d4d4d4",
    "border": "#333",
    "border_light": "#555",
    "btn_bg": "#333",
    "btn_hover": "#444",
    "splitter_handle": "#333",
    "selected_bg": "#37373d",
    "item_hover_bg": "#2a2d2e",
    "bubble_me_bg": "#1a3a5c",
    "bubble_me_color": "#2196F3",
    "bubble_others_bg": "#1c3d2a",
    "bubble_others_color": "#4CAF50",
    "delete_hover": "#ff5555",
    "muted_text": "#888",
    "link_color": "#3794ff",
    "status_green": "green",
    "status_orange": "orange",
    "status_red": "red",
    "status_gray": "gray",
}

LIGHT: dict[str, Any] = {
    "bg_primary": "#f5f5f5",
    "bg_secondary": "#ffffff",
    "text": "#1e1e1e",
    "border": "#ccc",
    "border_light": "#bbb",
    "btn_bg": "#e8e8e8",
    "btn_hover": "#d0d0d0",
    "splitter_handle": "#ccc",
    "selected_bg": "#d6d6d6",
    "item_hover_bg": "#e8e8e8",
    "bubble_me_bg": "#d4e8fc",
    "bubble_me_color": "#1565C0",
    "bubble_others_bg": "#d4f0de",
    "bubble_others_color": "#2E7D32",
    "delete_hover": "#d32f2f",
    "muted_text": "#888",
    "link_color": "#0066cc",
    "status_green": "green",
    "status_orange": "orange",
    "status_red": "red",
    "status_gray": "gray",
}


def get_palette(theme: str) -> dict[str, Any]:
    """Return the color palette for the given theme name."""
    if theme == "light":
        return LIGHT
    if theme == "dark":
        return DARK
    # "system" — auto-detect from OS
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            hints = app.styleHints()
            scheme = hints.colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return LIGHT
    except Exception:
        pass
    return DARK


def build_stylesheet(p: dict[str, Any]) -> str:
    """Build a full application QSS string from a color palette dict."""
    return f"""
    /* === Global === */
    * {{
        color: {p["text"]};
    }}
    QMainWindow, QWidget#centralWidget {{
        background-color: {p["bg_primary"]};
    }}
    QWidget {{
        background-color: {p["bg_primary"]};
        color: {p["text"]};
    }}
    QLabel {{
        color: {p["text"]};
        background: transparent;
    }}
    QSplitter::handle {{
        background-color: {p["splitter_handle"]};
        width: 1px;
    }}

    /* === Progress bar (audio level meters) === */
    QProgressBar {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 4px;
        text-align: center;
        font-size: 10px;
    }}
    QProgressBar::chunk {{
        background-color: {p["bubble_me_color"]};
        border-radius: 3px;
    }}

    /* === Scrollbar === */
    QScrollBar:vertical {{
        background: {p["bg_primary"]};
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {p["border_light"]};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p["muted_text"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: {p["bg_primary"]};
        height: 10px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {p["border_light"]};
        min-width: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p["muted_text"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* === Message box === */
    QMessageBox {{
        background-color: {p["bg_primary"]};
        color: {p["text"]};
    }}
    QMessageBox QLabel {{
        color: {p["text"]};
    }}
    QMessageBox QPushButton {{
        background-color: {p["btn_bg"]};
        color: {p["text"]};
        border: 1px solid {p["border_light"]};
        border-radius: 4px;
        padding: 6px 16px;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {p["btn_hover"]};
    }}

    /* === Tooltip === */
    QToolTip {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        padding: 4px;
    }}

    /* === Menu (context menus, combo dropdowns) === */
    QMenu {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
    }}
    QMenu::item:selected {{
        background-color: {p["selected_bg"]};
    }}
    QComboBox QAbstractItemView {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        selection-background-color: {p["selected_bg"]};
        border: 1px solid {p["border"]};
    }}

    /* === Sidebar === */
    SidebarPanel {{
        background-color: {p["bg_primary"]};
        border-right: 1px solid {p["border"]};
    }}
    SidebarPanel QLabel {{
        color: {p["text"]};
        background: transparent;
    }}
    SidebarPanel QPushButton {{
        background-color: {p["btn_bg"]};
        color: {p["text"]};
        border: 1px solid {p["border_light"]};
        border-radius: 4px;
        font-size: 16px;
        font-weight: bold;
    }}
    SidebarPanel QPushButton:hover {{
        background-color: {p["btn_hover"]};
    }}
    SidebarPanel QPushButton#settingsBtn {{
        border-radius: 6px;
        padding: 8px;
        font-size: 13px;
        font-weight: normal;
    }}
    SidebarPanel QListWidget {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        padding: 4px;
        font-size: 13px;
    }}
    SidebarPanel QListWidget::item {{
        padding: 8px 6px;
        border-radius: 4px;
    }}
    SidebarPanel QListWidget::item:selected {{
        background-color: {p["selected_bg"]};
    }}
    SidebarPanel QListWidget::item:hover {{
        background-color: {p["item_hover_bg"]};
    }}

    /* === Output panel === */
    OutputPanel {{
        background-color: {p["bg_primary"]};
        border-left: 1px solid {p["border"]};
    }}
    OutputPanel QPushButton {{
        background-color: {p["btn_bg"]};
        color: {p["text"]};
        border: 1px solid {p["border_light"]};
        border-radius: 10px;
        padding: 4px 10px;
        font-size: 12px;
    }}
    OutputPanel QPushButton:hover {{
        background-color: {p["btn_hover"]};
    }}
    OutputPanel QPlainTextEdit {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        padding: 8px;
    }}

    /* === Transcript view === */
    TranscriptView {{
        background-color: {p["bg_primary"]};
        border: none;
    }}
    TranscriptView QScrollArea {{
        background-color: {p["bg_primary"]};
        border: none;
    }}
    TranscriptView QWidget#transcriptContainer {{
        background-color: {p["bg_primary"]};
    }}
    TranscriptView QPushButton {{
        background-color: {p["btn_bg"]};
        color: {p["text"]};
        border: 1px solid {p["border_light"]};
        border-radius: 6px;
        font-size: 16px;
    }}
    TranscriptView QPushButton:hover {{
        background-color: {p["btn_hover"]};
    }}

    /* === Chat bubble text === */
    #chatBubble QPlainTextEdit {{
        background: transparent;
        color: {p["text"]};
        border: none;
        padding: 0px;
    }}
    #chatBubble QPushButton {{
        background: transparent;
        color: {p["muted_text"]};
        border: none;
        font-size: 14px;
        font-weight: bold;
    }}
    #chatBubble QPushButton:hover {{
        color: {p["delete_hover"]};
    }}

    /* === Notes panel === */
    NotesPanel {{
        background-color: {p["bg_primary"]};
        border: 1px solid {p["border_light"]};
        border-radius: 8px;
    }}
    NotesPanel QLabel {{
        color: {p["text"]};
        background: transparent;
    }}
    NotesPanel QPushButton {{
        background-color: transparent;
        color: {p["text"]};
        border: none;
        font-size: 14px;
    }}
    NotesPanel QPushButton:hover {{
        background-color: {p["btn_bg"]};
        border-radius: 4px;
    }}
    NotesPanel QPlainTextEdit {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        padding: 8px;
    }}

    /* === Status bar === */
    QStatusBar {{
        background-color: {p["bg_primary"]};
        color: {p["text"]};
    }}
    QStatusBar QLabel {{
        color: {p["text"]};
    }}

    /* === Settings dialog === */
    QDialog {{
        background-color: {p["bg_primary"]};
        color: {p["text"]};
    }}
    QDialog QGroupBox {{
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 12px;
    }}
    QDialog QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
    QDialog QLabel {{
        color: {p["text"]};
    }}
    QDialog QComboBox {{
        background-color: {p["bg_secondary"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QDialog QPushButton {{
        background-color: {p["btn_bg"]};
        color: {p["text"]};
        border: 1px solid {p["border_light"]};
        border-radius: 4px;
        padding: 6px 16px;
    }}
    QDialog QPushButton:hover {{
        background-color: {p["btn_hover"]};
    }}
    QDialog QDialogButtonBox QPushButton {{
        min-width: 70px;
    }}

    /* === Splash screen === */
    QSplashScreen {{
        background-color: {p["bg_primary"]};
        color: {p["text"]};
    }}
"""
