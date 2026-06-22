"""
Apple-inspired theme system with Light and Dark modes.
Colors sourced from Apple Human Interface Guidelines (iOS/macOS system palette).
"""

LIGHT = {
    "name": "light",
    # Backgrounds
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F5F5F7",
    "bg_tertiary": "#ECECEE",
    "bg_window": "#FAFAFA",
    # Text
    "text_primary": "#1D1D1F",
    "text_secondary": "#6E6E73",
    "text_tertiary": "#AEAEB2",
    # Borders
    "border": "#E5E5EA",
    "border_light": "#F0F0F0",
    # Accent (Apple Blue)
    "accent": "#007AFF",
    "accent_hover": "#0066D6",
    "accent_bg": "rgba(0,122,255,0.08)",
    # Semantic
    "success": "#34C759",
    "success_bg": "rgba(52,199,89,0.10)",
    "success_text": "#1B7D34",
    "warning": "#FF9500",
    "warning_bg": "rgba(255,149,0,0.10)",
    "warning_text": "#8A5100",
    "danger": "#FF3B30",
    # Module accent colors
    "mod_clearance": "#FF6B35",
    "mod_missed": "#007AFF",
    "mod_movement": "#AF52DE",
    "mod_price": "#FF9500",
    "mod_shipping": "#34C759",
    # Tinted button backgrounds (very subtle)
    "tint_clearance": "rgba(255,107,53,0.10)",
    "tint_missed": "rgba(0,122,255,0.10)",
    "tint_movement": "rgba(175,82,222,0.10)",
    "tint_price": "rgba(255,149,0,0.10)",
    "tint_shipping": "rgba(52,199,89,0.10)",
    # Sidebar
    "sidebar_bg": "#F5F5F7",
    # Card
    "card_bg": "#FFFFFF",
    "card_border": "#E5E5EA",
    "card_hover": "#F0F0F2",
    # Drop zone
    "drop_border": "#D1D1D6",
    "drop_bg": "#FAFAFA",
    "drop_filled_border": "#34C759",
    "drop_filled_bg": "rgba(52,199,89,0.06)",
}

DARK = {
    "name": "dark",
    "bg_primary": "#1C1C1E",
    "bg_secondary": "#2C2C2E",
    "bg_tertiary": "#3A3A3C",
    "bg_window": "#161618",
    "text_primary": "#F5F5F7",
    "text_secondary": "#AEAEB2",
    "text_tertiary": "#636366",
    "border": "#38383A",
    "border_light": "#2C2C2E",
    "accent": "#0A84FF",
    "accent_hover": "#409CFF",
    "accent_bg": "rgba(10,132,255,0.15)",
    "success": "#30D158",
    "success_bg": "rgba(48,209,88,0.12)",
    "success_text": "#30D158",
    "warning": "#FF9F0A",
    "warning_bg": "rgba(255,159,10,0.12)",
    "warning_text": "#FF9F0A",
    "danger": "#FF453A",
    "mod_clearance": "#FF8F61",
    "mod_missed": "#64D2FF",
    "mod_movement": "#BF5AF2",
    "mod_price": "#FFD60A",
    "mod_shipping": "#30D158",
    "tint_clearance": "rgba(255,143,97,0.15)",
    "tint_missed": "rgba(100,210,255,0.15)",
    "tint_movement": "rgba(191,90,242,0.15)",
    "tint_price": "rgba(255,214,10,0.15)",
    "tint_shipping": "rgba(48,209,88,0.15)",
    "sidebar_bg": "#1C1C1E",
    "card_bg": "#1C1C1E",
    "card_border": "#38383A",
    "card_hover": "#2C2C2E",
    "drop_border": "#48484A",
    "drop_bg": "#1C1C1E",
    "drop_filled_border": "#30D158",
    "drop_filled_bg": "rgba(48,209,88,0.08)",
}


def build_stylesheet(t):
    """Build a complete QSS stylesheet from a theme dict."""
    return f"""
    /* ---- Global ---- */
    QMainWindow, QWidget#central {{
        background-color: {t['bg_window']};
    }}

    QLabel {{
        color: {t['text_primary']};
        background: transparent;
    }}
    QLabel[class="secondary"] {{
        color: {t['text_secondary']};
    }}
    QLabel[class="tertiary"] {{
        color: {t['text_tertiary']};
    }}
    QLabel[class="title"] {{
        font-size: 24px;
        font-weight: 500;
    }}
    QLabel[class="subtitle"] {{
        font-size: 14px;
        color: {t['text_secondary']};
    }}
    QLabel[class="section"] {{
        font-size: 12px;
        font-weight: 600;
        color: {t['text_tertiary']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ---- Scroll Area ---- */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ---- Push Button ---- */
    QPushButton {{
        background-color: {t['bg_tertiary']};
        color: {t['text_primary']};
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {t['border']};
    }}
    QPushButton:pressed {{
        background-color: {t['bg_tertiary']};
    }}
    QPushButton:disabled {{
        background-color: {t['bg_tertiary']};
        color: {t['text_tertiary']};
    }}
    QPushButton[class="accent"] {{
        background-color: {t['accent']};
        color: white;
    }}
    QPushButton[class="accent"]:hover {{
        background-color: {t['accent_hover']};
    }}
    QPushButton[class="accent"]:disabled {{
        background-color: {t['bg_tertiary']};
        color: {t['text_tertiary']};
    }}

    /* ---- Combo Box ---- */
    QComboBox {{
        background-color: {t['bg_tertiary']};
        color: {t['text_primary']};
        border: 0.5px solid {t['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
        min-height: 20px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t['bg_secondary']};
        color: {t['text_primary']};
        border: 0.5px solid {t['border']};
        border-radius: 8px;
        selection-background-color: {t['accent_bg']};
        selection-color: {t['accent']};
    }}

    /* ---- Line Edit ---- */
    QLineEdit {{
        background-color: {t['bg_tertiary']};
        color: {t['text_primary']};
        border: 0.5px solid {t['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border: 1.5px solid {t['accent']};
    }}
    """
