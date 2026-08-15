from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPainter, QPixmap

from .overlay import CropOverlayWidget

class GraphicsView(QGraphicsView):
    """
    Custom QGraphicsView for image cropping.

    Behavior matching BIRME:
    - Main image is aspect-fitted and static (no panning or zooming of the image itself).
    - Image is fit to screen with a clean padding of 40 pixels.
    - Dragging the crop frame overlay moves the crop box on top of the image.
    - Scroll wheel scales the crop box size relative to the image (clamped to max image boundaries and min 50px).
    """
    crop_requested = Signal()
    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.image_item = None
        self.current_zoom = 1.0
        self.current_scene_center = QPointF(0, 0)

        # Left drag crop frame support state
        self._left_dragging = False
        self._left_drag_start_pos = QPointF()

        # Configure view settings
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)

        # Hide scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Dark background
        self.setStyleSheet("background-color: #121214; border: none;")

        # Overlay for the crop frame
        self.overlay = CropOverlayWidget(self.viewport())
        self.overlay.setGeometry(self.viewport().rect())

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    # ─── Image Loading ────────────────────────────────────────────────

    def set_image(self, qimage):
        """Sets the image in the scene, preserving its original resolution."""
        self.scene.clear()
        self.image_item = None
        self.current_zoom = 1.0
        self.current_scene_center = QPointF(0, 0)
        self.resetTransform()

        if not qimage or qimage.isNull():
            # Clear the overlay's image rect when no image
            self.overlay.img_vp_w = 0.0
            self.overlay.img_vp_h = 0.0
            self.overlay.crop_rect = QRectF()
            self.overlay.update()
            return

        pixmap = QPixmap.fromImage(qimage)
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)

        img_w = pixmap.width()
        img_h = pixmap.height()
        self.setSceneRect(0, 0, img_w, img_h)

        self.fit_image_in_view()

    # ─── View Fitting & Mathematical Clamping ──────────────────────────

    def fit_image_in_view(self):
        """
        Scales the image to fit fully inside the canvas viewport statically,
        centered with a clean padding of 40 pixels.
        """
        if not self.image_item or not hasattr(self, 'overlay') or not self.overlay:
            return

        # Ensure correct parent and viewport alignment
        if self.overlay.parentWidget() != self.viewport():
            self.overlay.setParent(self.viewport())
            self.overlay.show()
        
        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        self.overlay.setGeometry(0, 0, vp_w, vp_h)

        img_w = self.image_item.pixmap().width()
        img_h = self.image_item.pixmap().height()
        if img_w <= 0 or img_h <= 0:
            return

        # Scale to fit fully inside viewport with a padding of 40px on all sides
        # (Total padding in width is 80px, in height is 80px)
        zoom = min(max(10.0, vp_w - 80) / img_w, max(10.0, vp_h - 80) / img_h)
        self.current_zoom = zoom

        # Center in scene coords
        self.current_scene_center = QPointF(img_w / 2.0, img_h / 2.0)

        # Update QGraphicsView transformation matrix
        self.resetTransform()
        self.scale(zoom, zoom)
        self.centerOn(self.current_scene_center)

        # Compute exact screen viewport bounds of the static image
        img_vp_w = img_w * zoom
        img_vp_h = img_h * zoom
        img_vp_x = (vp_w - img_vp_w) / 2.0
        img_vp_y = (vp_h - img_vp_h) / 2.0

        # Update overlay's relative boundary system
        self.overlay.set_image_bounds(img_vp_x, img_vp_y, img_vp_w, img_vp_h, img_w, img_h)

        # Emit initial relative zoom level (100% since rel_w is at max initial)
        if self.overlay.rel_w > 0:
            zoom_rel = self.overlay.initial_max_rel_w / self.overlay.rel_w
            self.zoom_changed.emit(zoom_rel)
        else:
            self.zoom_changed.emit(1.0)

    def _get_min_zoom(self):
        """Compatibility helper returning the main view scale factor."""
        return self.current_zoom

    def update_view(self, new_scene_center, new_zoom):
        """Compatibility helper, does nothing as the image is static."""
        pass

    def clamp_crop_to_image(self):
        """Compatibility helper."""
        pass

    def clamp_view_to_boundaries(self):
        """Compatibility helper."""
        pass

    # ─── Wheel Zoom ───────────────────────────────────────────────────

    def wheelEvent(self, event):
        """Scroll wheel scrolling scales the crop box size relative to the image."""
        if not self.image_item or not self.overlay:
            return

        delta = event.angleDelta().y()
        # Scroll up (delta > 0) shrinks the crop box (zoom in)
        # Scroll down (delta < 0) expands the crop box (zoom out)
        factor = 0.90 if delta > 0 else (1.0 / 0.90)

        self.overlay.scale_crop_box(factor)

        # Calculate current zoom relative to starting maximum cover scale
        if self.overlay.rel_w > 0:
            zoom_rel = self.overlay.initial_max_rel_w / self.overlay.rel_w
            self.zoom_changed.emit(zoom_rel)

    # ─── Mouse Events ─────────────────────────────────────────────────

    def mousePressEvent(self, event):
        """Left-click starts dragging the crop box."""
        if event.button() == Qt.LeftButton:
            pos = event.position() if hasattr(event, 'position') else event.localPos()
            self._left_dragging = True
            self._left_drag_start_pos = pos
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Left-drag: moves the crop box, constrained inside the static image boundaries."""
        pos = event.position() if hasattr(event, 'position') else event.localPos()
        
        # Interactive hover styling for overlay if mouse is inside the crop rect
        if self.overlay and not self.overlay.crop_rect.isEmpty():
            in_crop = self.overlay.crop_rect.contains(pos)
            if self.overlay.hovered != in_crop:
                self.overlay.hovered = in_crop
                self.overlay.update()

        if self._left_dragging:
            delta = pos - self._left_drag_start_pos
            self._left_drag_start_pos = pos

            self.overlay.drag_crop_box(delta.x(), delta.y())
            
            # Emit live zoom change (in case scaling and drag interact)
            if self.overlay.rel_w > 0:
                zoom_rel = self.overlay.initial_max_rel_w / self.overlay.rel_w
                self.zoom_changed.emit(zoom_rel)
                
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handles drag release for left-click."""
        if event.button() == Qt.LeftButton:
            if self._left_dragging:
                self._left_dragging = False
                self.unsetCursor()
            event.accept()
        elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double right-click to instantly crop and save."""
        if event.button() == Qt.RightButton:
            self.crop_requested.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    # ─── Utility Methods ──────────────────────────────────────────────

    def reset_view(self):
        """Resets the view transform and defaults the crop box size to full cover."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.current_aspect = None
        self.fit_image_in_view()

    def get_crop_scene_rect(self, visual_crop_rect=None):
        """
        Maps the relative crop overlay coordinates to original image pixels.
        Returns a QRectF in original image space.
        """
        if not self.image_item or not self.overlay:
            return QRectF()

        sx = self.overlay.rel_x * self.overlay.img_w
        sy = self.overlay.rel_y * self.overlay.img_h
        sw = self.overlay.rel_w * self.overlay.img_w
        sh = self.overlay.rel_h * self.overlay.img_h
        return QRectF(sx, sy, sw, sh)

    def resizeEvent(self, event):
        """Ensures the overlay covers the viewport and fits the image when resized."""
        super().resizeEvent(event)
        if hasattr(self, 'overlay') and self.overlay:
            if self.overlay.parentWidget() != self.viewport():
                self.overlay.setParent(self.viewport())
                self.overlay.show()
            self.overlay.setGeometry(0, 0, self.viewport().width(), self.viewport().height())
        self.fit_image_in_view()

    def set_crop_dimensions(self, w, h):
        """Sets crop dimensions on the overlay and fits the image."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.set_crop_dimensions(w, h)
            self.fit_image_in_view()

    def set_show_rule_of_thirds(self, show):
        """Configures rule of thirds on overlay."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.set_show_rule_of_thirds(show)
