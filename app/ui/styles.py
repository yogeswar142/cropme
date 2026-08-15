DARK_STYLESHEET = """
/* Global Window Styles */
QMainWindow {
    background-color: #121214;
    color: #f4f4f7;
    font-family: "Segoe UI", "Segoe WP", "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
}

/* ScrollBar Styling */
QScrollBar:vertical {
    border: none;
    background: #18181b;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #3f3f46;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #52525b;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #18181b;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #3f3f46;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #52525b;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Toolbar styling */
QToolBar {
    background-color: #1a1a1e;
    border-bottom: 1px solid #2a2a30;
    spacing: 12px;
    padding: 6px 12px;
}

/* Input Fields styling (Width, Height) */
QLineEdit {
    background-color: #222226;
    color: #f4f4f7;
    border: 1px solid #3a3a42;
    border-radius: 6px;
    padding: 6px 8px;
    min-width: 60px;
    max-width: 80px;
    font-weight: bold;
    selection-background-color: #00f0ff;
    selection-color: #121214;
}
QLineEdit:focus {
    border: 1px solid #00f0ff;
    background-color: #1e1e22;
}

/* ComboBox/Dropdown styling */
QComboBox {
    background-color: #222226;
    color: #f4f4f7;
    border: 1px solid #3a3a42;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 100px;
}
QComboBox:hover {
    border-color: #52525b;
}
QComboBox:focus {
    border: 1px solid #00f0ff;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #a1a1aa;
    margin-right: 6px;
}
QComboBox::down-arrow:hover {
    border-top-color: #00f0ff;
}
QComboBox QAbstractItemView {
    background-color: #1a1a1e;
    color: #f4f4f7;
    border: 1px solid #2a2a30;
    selection-background-color: #00f0ff;
    selection-color: #121214;
    outline: none;
    padding: 4px;
}

/* Button styling */
QPushButton {
    background-color: #222226;
    color: #f4f4f7;
    border: 1px solid #3a3a42;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2e2e36;
    border-color: #52525b;
}
QPushButton:pressed {
    background-color: #1c1c20;
}

/* Special Button States */
QPushButton#accentButton {
    background-color: #004d54;
    color: #00f0ff;
    border: 1px solid #00c0d0;
}
QPushButton#accentButton:hover {
    background-color: #00606a;
    border-color: #00f0ff;
}

QPushButton#primaryAction {
    background-color: #00f0ff;
    color: #121214;
    border: 1px solid #00c0d0;
    font-weight: bold;
}
QPushButton#primaryAction:hover {
    background-color: #33f3ff;
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

/* Segmented / Toggle Button active states */
QPushButton[active="true"] {
    background-color: #00f0ff;
    color: #121214;
    border: 1px solid #00f0ff;
    font-weight: bold;
}

/* Labels styling */
QLabel {
    color: #a1a1aa;
}
QLabel#titleLabel {
    color: #f4f4f7;
    font-weight: bold;
}
QLabel#statusInfo {
    color: #00f0ff;
}

/* Sidebars and List widgets */
QListWidget {
    background-color: #16161a;
    border-right: 1px solid #2a2a30;
    border-top: none;
    border-left: none;
    border-bottom: none;
    color: #e4e4e7;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    border-radius: 6px;
    padding: 8px 12px;
    margin: 2px 4px;
}
QListWidget::item:hover {
    background-color: #222226;
    color: #ffffff;
}
QListWidget::item:selected {
    background-color: #27272a;
    color: #00f0ff;
    border-left: 3px solid #00f0ff;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
}

/* Checkbox and Toggles styling */
QCheckBox {
    spacing: 8px;
    color: #a1a1aa;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3a3a42;
    border-radius: 4px;
    background-color: #222226;
}
QCheckBox::indicator:hover {
    border-color: #00f0ff;
}
QCheckBox::indicator:checked {
    background-color: #00f0ff;
    border-color: #00f0ff;
    image: url(none); /* In Qt, we can draw a custom mark or let standard handle it */
}
/* We can style indicator:checked with custom drawing or unicode if needed,
   but a simple colored block works or background fill is very clean. */

/* Sidebar Layout container */
QFrame#sidebarContainer {
    background-color: #16161a;
    border-right: 1px solid #2a2a30;
}

/* Bottom status bar bar styling */
QStatusBar {
    background-color: #1a1a1e;
    border-top: 1px solid #2a2a30;
    color: #71717a;
    padding: 4px;
}
QStatusBar QLabel {
    color: #71717a;
}

/* Bottom Thumbnail Strip Container */
#thumbnailStrip {
    background-color: #0f0f11;
    border-top: 1px solid #222226;
}

/* Individual Thumbnail Cards */
#thumbnailCard {
    background-color: #161619;
    border: 2px solid #222226;
    border-radius: 8px;
}
#thumbnailCard:hover {
    border-color: #52525b;
    background-color: #1a1a20;
}
#thumbnailCard[current="true"] {
    border-color: #00f0ff;
    background-color: #161a22;
}
#thumbnailCard[disabled="true"] {
    background-color: #0d0d0f;
    border-color: #131315;
    opacity: 0.3;
}
"""
