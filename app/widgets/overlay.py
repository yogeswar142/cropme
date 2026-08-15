from PySide6.QtCore import Qt, QRectF, QPointF, QVariantAnimation
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath

class CropOverlayWidget(QWidget):
    """
    Transparent overlay widget that draws the crop frame, dark outer mask,
    rule-of-thirds grid, and successful crop animation flashes.
    Mouse events pass through it to the view underneath.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Pass mouse events through to widgets underneath
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        # Target crop dimensions (in export pixels)
        self.target_width = 800
        self.target_height = 600
        
        # Rule of thirds visibility
        self.show_rule_of_thirds = True
        
        # Current visual crop frame rectangle (in viewport/screen pixels)
        self.crop_rect = QRectF()
        
        # Image bounds on screen (in viewport/screen pixels)
        self.img_vp_x = 0.0
        self.img_vp_y = 0.0
        self.img_vp_w = 0.0
        self.img_vp_h = 0.0
        
        # Original image dimensions
        self.img_w = 1.0
        self.img_h = 1.0
        
        # Relative crop box coordinates on the image directly (from 0.0 to 1.0)
        self.rel_x = 0.0
        self.rel_y = 0.0
        self.rel_w = 1.0
        self.rel_h = 1.0
        
        # Initial maximum relative dimensions that fit target aspect ratio
        self.initial_max_rel_w = 1.0
        self.initial_max_rel_h = 1.0
        
        # Success animation flash opacity
        self.flash_opacity = 0.0
        self.anim = None
        
        # Animated top-right toast notification properties
        self.toast_opacity = 0.0
        self.toast_text = ""
        self.toast_fade_anim = None
        self._toast_timer_id = None
        
        # Hover states
        self.hovered = False

    def set_image_bounds(self, x, y, w, h, img_w, img_h):
        """Sets the image's viewport rectangle and reinitializes crop proportions."""
        self.img_vp_x = x
        self.img_vp_y = y
        self.img_vp_w = w
        self.img_vp_h = h
        self.img_w = img_w
        self.img_h = img_h
        
        # Calculate maximum initial relative dimensions to fit crop aspect ratio inside image aspect ratio
        aspect = self.target_width / self.target_height
        img_aspect = img_w / img_h
        
        if img_aspect > aspect:
            # Image is wider than crop box aspect ratio. Height is 100%.
            self.initial_max_rel_h = 1.0
            self.initial_max_rel_w = aspect / img_aspect
        else:
            # Image is narrower than crop box aspect ratio. Width is 100%.
            self.initial_max_rel_w = 1.0
            self.initial_max_rel_h = img_aspect / aspect
            
        # If this is the first load or aspect ratio has changed, initialize rel coordinates to center
        if not hasattr(self, 'current_aspect') or self.current_aspect != aspect:
            self.current_aspect = aspect
            self.rel_w = self.initial_max_rel_w
            self.rel_h = self.initial_max_rel_h
            self.rel_x = (1.0 - self.rel_w) / 2.0
            self.rel_y = (1.0 - self.rel_h) / 2.0
            
        self.update_crop_rect()

    def set_crop_dimensions(self, width, height):
        """Updates the crop aspect ratio and recalculates visual dimensions."""
        if width > 0 and height > 0:
            self.target_width = width
            self.target_height = height
            # Force re-initialization of aspect ratio on next image bounds update
            self.current_aspect = None
            if self.img_vp_w > 0:
                self.set_image_bounds(self.img_vp_x, self.img_vp_y, self.img_vp_w, self.img_vp_h, self.img_w, self.img_h)

    def drag_crop_box(self, dx_vp, dy_vp):
        """Drags the crop box by viewport delta pixels, constrained to the image."""
        if self.img_vp_w <= 0 or self.img_vp_h <= 0:
            return
            
        dx_rel = dx_vp / self.img_vp_w
        dy_rel = dy_vp / self.img_vp_h
        
        self.rel_x = max(0.0, min(self.rel_x + dx_rel, 1.0 - self.rel_w))
        self.rel_y = max(0.0, min(self.rel_y + dy_rel, 1.0 - self.rel_h))
        
        self.update_crop_rect()

    def scale_crop_box(self, factor):
        """Scales the crop box size relative to the image, keeping it centered and constrained."""
        if self.img_vp_w <= 0 or self.img_vp_h <= 0:
            return
            
        new_rel_w = self.rel_w * factor
        new_rel_h = self.rel_h * factor
        
        # Clamp to max size (initial cover size)
        if new_rel_w > self.initial_max_rel_w or new_rel_h > self.initial_max_rel_h:
            new_rel_w = self.initial_max_rel_w
            new_rel_h = self.initial_max_rel_h
            
        # Clamp to min size (e.g. 50 pixels on screen)
        min_w_rel = 50.0 / self.img_vp_w
        min_h_rel = 50.0 / self.img_vp_h
        if new_rel_w < min_w_rel or new_rel_h < min_h_rel:
            ratio = self.rel_w / self.rel_h
            if min_w_rel / min_h_rel > ratio:
                new_rel_w = min_w_rel
                new_rel_h = min_w_rel / ratio
            else:
                new_rel_h = min_h_rel
                new_rel_w = min_h_rel * ratio
                
        # Keep center of the crop box at the same place
        c_x = self.rel_x + self.rel_w / 2.0
        c_y = self.rel_y + self.rel_h / 2.0
        
        self.rel_w = new_rel_w
        self.rel_h = new_rel_h
        self.rel_x = max(0.0, min(c_x - new_rel_w / 2.0, 1.0 - new_rel_w))
        self.rel_y = max(0.0, min(c_y - new_rel_h / 2.0, 1.0 - new_rel_h))
        
        self.update_crop_rect()

    def set_show_rule_of_thirds(self, show):
        """Shows or hides the rule of thirds grid."""
        self.show_rule_of_thirds = show
        self.update()

    def resizeEvent(self, event):
        """Recalculates the crop rectangle when the overlay is resized."""
        super().resizeEvent(event)
        self.update_crop_rect()

    def update_crop_rect(self):
        """Calculates the crop_rect in viewport coordinates using parent bounds."""
        if self.img_vp_w <= 0 or self.img_vp_h <= 0:
            return
            
        crop_w = self.rel_w * self.img_vp_w
        crop_h = self.rel_h * self.img_vp_h
        crop_x = self.img_vp_x + self.rel_x * self.img_vp_w
        crop_y = self.img_vp_y + self.rel_y * self.img_vp_h
        
        self.crop_rect = QRectF(crop_x, crop_y, crop_w, crop_h)
        self.update()

    def trigger_crop_animation(self):
        """Triggers a premium crop save flash and pill animation in the center of the crop frame."""
        self.flash_opacity = 1.0
        self.update()
        
        if self.anim is not None:
            self.anim.stop()
            
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setDuration(400)
        self.anim.valueChanged.connect(self._update_flash_opacity)
        self.anim.start()
        
    def _update_flash_opacity(self, value):
        self.flash_opacity = value
        self.update()

    def show_toast(self, text):
        """Displays a beautiful top-right animated toast notification."""
        self.toast_text = text
        self.toast_opacity = 1.0
        self.update()
        
        if self._toast_timer_id is not None:
            self.killTimer(self._toast_timer_id)
            self._toast_timer_id = None
            
        if self.toast_fade_anim is not None:
            self.toast_fade_anim.stop()
            
        self._toast_timer_id = self.startTimer(2000)

    def timerEvent(self, event):
        """Timer callback to fade out the toast notification."""
        if self._toast_timer_id is not None and event.timerId() == self._toast_timer_id:
            self.killTimer(self._toast_timer_id)
            self._toast_timer_id = None
            
            self.toast_fade_anim = QVariantAnimation(self)
            self.toast_fade_anim.setStartValue(1.0)
            self.toast_fade_anim.setEndValue(0.0)
            self.toast_fade_anim.setDuration(500)
            self.toast_fade_anim.valueChanged.connect(self._update_toast_opacity)
            self.toast_fade_anim.start()
            
        super().timerEvent(event)
        
    def _update_toast_opacity(self, value):
        self.toast_opacity = value
        self.update()

    def paintEvent(self, event):
        """Paints the dark transparent mask, boundary, rule-of-thirds grids, and feedback animations."""
        if self.crop_rect.isEmpty():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 1. Draw the outside semi-transparent dark mask
        mask_path = QPainterPath()
        mask_path.addRect(QRectF(self.rect()))
        mask_path.addRect(self.crop_rect)
        
        painter.setPen(Qt.NoPen)
        # Modern translucent dark mask: 70% opacity (180/255)
        painter.setBrush(QColor(10, 10, 12, 180))
        painter.drawPath(mask_path)
        
        # 2. Draw the sleek crop frame border with premium glow on hover
        if getattr(self, "hovered", False):
            glow_pen = QPen(QColor(0, 240, 255, 60), 4)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.crop_rect)
            
            border_pen = QPen(QColor(80, 245, 255), 2)
        else:
            border_pen = QPen(QColor(0, 240, 255), 2)
            
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.crop_rect)
        
        # 3. Draw thin rule-of-thirds guides inside the crop frame if enabled
        if self.show_rule_of_thirds:
            grid_pen = QPen(QColor(255, 255, 255, 60), 1, Qt.DashLine)
            painter.setPen(grid_pen)
            
            x = self.crop_rect.x()
            y = self.crop_rect.y()
            w = self.crop_rect.width()
            h = self.crop_rect.height()
            
            # Vertical guides
            painter.drawLine(x + w / 3, y, x + w / 3, y + h)
            painter.drawLine(x + 2 * w / 3, y, x + 2 * w / 3, y + h)
            
            # Horizontal guides
            painter.drawLine(x, y + h / 3, x + w, y + h / 3)
            painter.drawLine(x, y + 2 * h / 3, x + w, y + 2 * h / 3)
            
        # 4. Draw Crop Success Animation Overlay
        if self.flash_opacity > 0.0:
            flash_color = QColor(0, 240, 255, int(self.flash_opacity * 70))
            painter.setPen(Qt.NoPen)
            painter.setBrush(flash_color)
            painter.drawRect(self.crop_rect)
            
            pill_w = 120
            pill_h = 36
            cx = self.crop_rect.center().x()
            cy = self.crop_rect.center().y()
            pill_rect = QRectF(cx - pill_w / 2, cy - pill_h / 2, pill_w, pill_h)
            
            pill_bg = QColor(10, 10, 12, int(self.flash_opacity * 230))
            pill_border = QColor(0, 240, 255, int(self.flash_opacity * 255))
            
            painter.setBrush(pill_bg)
            painter.setPen(QPen(pill_border, 1.5))
            painter.drawRoundedRect(pill_rect, 6, 6)
            
            font = painter.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor(244, 244, 247, int(self.flash_opacity * 255)))
            painter.drawText(pill_rect, Qt.AlignCenter, "✓  SAVED")
            
        # 5. Draw sleek Top-Right Animated Toast Notification
        if self.toast_opacity > 0.0:
            toast_w = 220
            toast_h = 42
            padding = 16
            tx = self.width() - toast_w - padding
            ty = padding
            
            toast_rect = QRectF(tx, ty, toast_w, toast_h)
            
            bg_color = QColor(10, 10, 12, int(self.toast_opacity * 240))
            border_color = QColor(0, 240, 255, int(self.toast_opacity * 255))
            
            painter.setBrush(bg_color)
            painter.setPen(QPen(border_color, 1.5))
            painter.drawRoundedRect(toast_rect, 8, 8)
            
            font = painter.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            
            painter.setPen(QColor(0, 240, 255, int(self.toast_opacity * 255)))
            painter.drawText(toast_rect, Qt.AlignCenter, f"✓  {self.toast_text}")
            
        painter.end()
