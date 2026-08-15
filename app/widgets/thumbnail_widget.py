import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame
from PySide6.QtGui import QPixmap, QImage

class ThumbnailWidget(QFrame):
    """Clickable card displaying role label, scaled image preview, and truncated filename."""
    clicked = Signal()
    
    def __init__(self, role_label="", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setObjectName("thumbnailCard")
        self.setCursor(Qt.PointingHandCursor)
        
        self.role_label = role_label
        self.filepath = None
        
        # Build widget layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        # Label indicating relation to current image (PREV, CURRENT, NEXT)
        self.lbl_role = QLabel(role_label)
        self.lbl_role.setAlignment(Qt.AlignCenter)
        self.lbl_role.setStyleSheet("font-size: 9px; font-weight: bold; color: #a1a1aa; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_role)
        
        # Scale-fitted image preview label
        self.lbl_pixmap = QLabel()
        self.lbl_pixmap.setAlignment(Qt.AlignCenter)
        self.lbl_pixmap.setFixedSize(140, 80)
        self.lbl_pixmap.setStyleSheet("background-color: #0b0b0c; border-radius: 4px; border: 1px solid #1a1a1c;")
        layout.addWidget(self.lbl_pixmap)
        
        # Base filename display
        self.lbl_name = QLabel("None")
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setStyleSheet("font-size: 10px; color: #71717a; font-weight: 500;")
        self.lbl_name.setFixedWidth(140)
        layout.addWidget(self.lbl_name)
        
        self.setFixedSize(152, 120)
        
    def set_image(self, filepath, qimage=None):
        """Sets the image preview pixmap, truncating the filename nicely."""
        self.filepath = filepath
        if not filepath:
            self.lbl_name.setText("Queue Boundary" if self.role_label != "CURRENT" else "No Image")
            self.lbl_pixmap.setPixmap(QPixmap())
            self.lbl_pixmap.setText("—")
            self.lbl_pixmap.setStyleSheet("background-color: #0b0b0c; border-radius: 4px; border: 1px solid #1a1a1c; color: #3f3f46; font-size: 14px; font-weight: bold;")
            self.setEnabled(False)
            self.setProperty("disabled", True)
            self.style().unpolish(self)
            self.style().polish(self)
            return
            
        self.setEnabled(True)
        self.setProperty("disabled", False)
        basename = os.path.basename(filepath)
        
        # Truncate filename if it is too long to fit
        if len(basename) > 18:
            basename = basename[:15] + "..."
        self.lbl_name.setText(basename)
        
        if qimage and not qimage.isNull():
            pixmap = QPixmap.fromImage(qimage)
            # Safe crop scaling within fixed label boundaries
            scaled = pixmap.scaled(self.lbl_pixmap.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_pixmap.setPixmap(scaled)
            self.lbl_pixmap.setText("")
        else:
            self.lbl_pixmap.setText("⌛ Preloading...")
            self.lbl_pixmap.setStyleSheet("background-color: #0b0b0c; border-radius: 4px; border: 1px solid #1a1a1c; color: #52525b; font-size: 9px;")
            
        self.style().unpolish(self)
        self.style().polish(self)
            
    def mousePressEvent(self, event):
        """Intercepts clicks to emit clicked signal."""
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.clicked.emit()
        else:
            super().mousePressEvent(event)


class ThumbnailStrip(QWidget):
    """Horizontal container managing Previous, Current, and Next image cards."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("thumbnailStrip")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)
        
        self.prev_thumb = ThumbnailWidget("PREVIOUS", self)
        self.curr_thumb = ThumbnailWidget("CURRENT", self)
        self.next_thumb = ThumbnailWidget("NEXT", self)
        
        # Apply current highlight to active card
        self.curr_thumb.setProperty("current", True)
        
        layout.addWidget(self.prev_thumb)
        layout.addWidget(self.curr_thumb)
        layout.addWidget(self.next_thumb)
        
        # Border top to separate from the graphics view beautifully
        self.setStyleSheet("background-color: #0f0f11; border-top: 1px solid #222226;")
