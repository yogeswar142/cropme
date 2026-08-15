import os
import re
from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QFileDialog, QListWidget, QListWidgetItem, QStatusBar, QMessageBox,
    QToolBar, QFrame
)
from PySide6.QtGui import QIntValidator, QIcon, QImage
from PIL import Image

from core.settings import AppSettings
from core.image_loader import ImageLoader, SUPPORTED_EXTENSIONS
from widgets import GraphicsView, ThumbnailStrip
from ui.styles import DARK_STYLESHEET

class MainWindow(QMainWindow):
    """The central main window combining toolbar, image list, cropping canvas, bottom thumbnail strip, and shortcuts."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CropMe — Fast Repetitive Image Cropper")
        self.resize(1300, 850)
        self.setStyleSheet(DARK_STYLESHEET)
        
        # Enable drag and drop on the main window
        self.setAcceptDrops(True)
        
        # Core Managers
        self.settings = AppSettings()
        self.image_loader = ImageLoader()
        
        # Aspect Ratio Tracking
        self.active_ratio = 1.0
        self.is_updating_dimensions = False
        
        # Session State & Undo Stack
        self.undo_stack = []
        self.pending_restore_state = None
        
        # Set up UI Components
        self.setup_ui()
        
        # Load and Apply Saved Settings (including fullscreen state)
        self.load_app_settings()
        
        # Signals & Slot connections
        self.connect_signals()
        
        # Auto-load last folder if it exists
        last_input = self.settings.get("input_folder")
        last_output = self.settings.get("output_folder")
        if last_input and os.path.exists(last_input):
            self.statusBar().showMessage(f"Loading last opened folder: {last_input}", 3000)
            self.image_loader.scan_folder(last_input, last_output)
            self.populate_sidebar()
            
            # Restore last image index if valid
            last_idx = self.settings.get("last_image_index", 0)
            if 0 <= last_idx < len(self.image_loader.images):
                self.image_loader.set_index(last_idx)
            elif self.image_loader.images:
                self.image_loader.set_index(0)
        else:
            self.statusBar().showMessage("Welcome! Open a folder containing images to start.", 5000)

    def setup_ui(self):
        """Builds the main window visual tree and layout."""
        # --- 1. Top Toolbar ---
        self.toolbar = QToolBar("Main Controls", self)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        # Folder buttons
        self.btn_open_input = QPushButton("📂 Open Folder")
        self.btn_open_input.setObjectName("accentButton")
        self.toolbar.addWidget(self.btn_open_input)
        
        self.btn_open_output = QPushButton("💾 Output Folder")
        self.toolbar.addWidget(self.btn_open_output)
        
        self.btn_crop = QPushButton("⚡ Crop & Save")
        self.btn_crop.setObjectName("accentButton")
        self.btn_crop.setToolTip("Crop and save the active image [Enter]")
        self.toolbar.addWidget(self.btn_crop)
        
        self.toolbar.addSeparator()
        
        # Crop Dimensions
        self.toolbar.addWidget(QLabel("Export: "))
        
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("Width")
        self.width_input.setValidator(QIntValidator(1, 20000, self))
        self.toolbar.addWidget(self.width_input)
        
        self.toolbar.addWidget(QLabel("x"))
        
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("Height")
        self.height_input.setValidator(QIntValidator(1, 20000, self))
        self.toolbar.addWidget(self.height_input)
        
        # Aspect Ratio Controls
        self.lock_ratio_checkbox = QCheckBox("Lock Aspect")
        self.toolbar.addWidget(self.lock_ratio_checkbox)
        
        self.toolbar.addWidget(QLabel("Ratio: "))
        self.preset_dropdown = QComboBox()
        self.preset_dropdown.addItems(["Custom", "1:1", "2:3", "16:9"])
        self.toolbar.addWidget(self.preset_dropdown)
        
        self.toolbar.addSeparator()
        
        # Quick Size Preset Buttons (Cards, Square, Banner)
        self.toolbar.addWidget(QLabel("Presets: "))
        self.btn_preset_cards = QPushButton("Cards (200x300)")
        self.btn_preset_cards.setToolTip("Quick Card Preset: 200 x 300")
        self.toolbar.addWidget(self.btn_preset_cards)
        
        self.btn_preset_square = QPushButton("Square (512x512)")
        self.btn_preset_square.setToolTip("Quick Square Preset: 512 x 512")
        self.toolbar.addWidget(self.btn_preset_square)
        
        self.btn_preset_banner = QPushButton("Banner (1280x720)")
        self.btn_preset_banner.setToolTip("Quick Banner Preset: 1280 x 720")
        self.toolbar.addWidget(self.btn_preset_banner)
        
        self.toolbar.addSeparator()
        
        # Toggle Rules of Thirds
        self.thirds_checkbox = QCheckBox("Grid")
        self.toolbar.addWidget(self.thirds_checkbox)
        
        self.toolbar.addSeparator()
        
        # Zoom indicator & reset
        self.zoom_label = QLabel("Zoom: 100%")
        self.toolbar.addWidget(self.zoom_label)
        
        self.btn_reset_view = QPushButton("Reset [R]")
        self.toolbar.addWidget(self.btn_reset_view)
        
        # --- 2. Central Splitter (Sidebar + Canvas Container) ---
        self.main_splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(self.main_splitter)
        
        # Left Sidebar container
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebarContainer")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Sidebar Header
        header_container = QWidget()
        header_container.setStyleSheet("background-color: #1a1a1e; border-bottom: 1px solid #2a2a30;")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(12, 10, 12, 10)
        
        self.sidebar_title = QLabel("IMAGES")
        self.sidebar_title.setObjectName("titleLabel")
        header_layout.addWidget(self.sidebar_title)
        
        header_layout.addStretch()
        
        self.counter_label = QLabel("0 / 0")
        self.counter_label.setObjectName("statusInfo")
        header_layout.addWidget(self.counter_label)
        
        sidebar_layout.addWidget(header_container)
        
        # Sidebar List
        self.file_list = QListWidget()
        sidebar_layout.addWidget(self.file_list)
        
        self.main_splitter.addWidget(self.sidebar)
        
        # Right Canvas Viewer Pane (Canvas + Bottom Thumbnail strip)
        self.right_pane_widget = QWidget()
        self.right_pane_widget.setStyleSheet("background-color: #121214;")
        right_layout = QVBoxLayout(self.right_pane_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.graphics_view = GraphicsView(self)
        right_layout.addWidget(self.graphics_view)
        
        # bottom thumbnail strip strip
        self.thumbnail_strip = ThumbnailStrip(self)
        right_layout.addWidget(self.thumbnail_strip)
        
        self.main_splitter.addWidget(self.right_pane_widget)
        
        # Set initial sizes for splitter (25% sidebar, 75% viewer)
        self.main_splitter.setSizes([300, 1000])
        
        # --- 3. Bottom Status Bar ---
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready")
        
        # Permanent status bar widget for next filename preview
        self.filename_preview_label = QLabel("Saving as: select output folder")
        self.filename_preview_label.setStyleSheet("font-weight: 500; font-size: 11px; margin-right: 12px;")
        self.statusBar().addPermanentWidget(self.filename_preview_label)

    def load_app_settings(self):
        """Applies configured settings back into the UI controls and window states."""
        self.is_updating_dimensions = True
        
        # Rule of thirds
        show_thirds = self.settings.get("show_rule_of_thirds")
        self.thirds_checkbox.setChecked(show_thirds)
        self.graphics_view.set_show_rule_of_thirds(show_thirds)
        
        # Dimensions
        w = self.settings.get("crop_width")
        h = self.settings.get("crop_height")
        self.width_input.setText(str(w))
        self.height_input.setText(str(h))
        
        # Presets & Locks
        preset = self.settings.get("aspect_ratio_preset")
        idx = self.preset_dropdown.findText(preset)
        if idx >= 0:
            self.preset_dropdown.setCurrentIndex(idx)
            
        locked = self.settings.get("lock_aspect_ratio")
        self.lock_ratio_checkbox.setChecked(locked)
        
        self.active_ratio = w / h if h > 0 else 1.0
        
        # Highlight active presets initially
        self.update_preset_buttons(w, h)
        
        # Update Canvas Crop dimensions
        self.graphics_view.set_crop_dimensions(w, h)
        
        # Restore Fullscreen State
        fullscreen = self.settings.get("fullscreen_state", False)
        if fullscreen:
            self.showFullScreen()
            
        self.is_updating_dimensions = False
        self.update_filename_preview()

    def connect_signals(self):
        """Binds button actions, line edits, dropdowns, and managers."""
        # Folder Scanning & Action Buttons
        self.btn_open_input.clicked.connect(self.select_input_folder)
        self.btn_open_output.clicked.connect(self.select_output_folder)
        self.btn_crop.clicked.connect(self.crop_and_save)
        self.btn_reset_view.clicked.connect(self.graphics_view.reset_view)
        
        # Quick Dimensions presets
        self.btn_preset_cards.clicked.connect(lambda: self.set_preset_dimensions(200, 300))
        self.btn_preset_square.clicked.connect(lambda: self.set_preset_dimensions(512, 512))
        self.btn_preset_banner.clicked.connect(lambda: self.set_preset_dimensions(1280, 720))
        
        # Dimensions inputs
        self.width_input.textChanged.connect(self.on_dimensions_changed)
        self.height_input.textChanged.connect(self.on_dimensions_changed)
        self.lock_ratio_checkbox.toggled.connect(self.on_lock_changed)
        self.preset_dropdown.currentTextChanged.connect(self.on_preset_changed)
        
        # Rule of Thirds
        self.thirds_checkbox.toggled.connect(self.on_thirds_changed)
        
        # List selection
        self.file_list.currentRowChanged.connect(self.on_sidebar_selection_changed)
        
        # Clickable thumbnails strip navigation
        self.thumbnail_strip.prev_thumb.clicked.connect(self.image_loader.prev_image)
        self.thumbnail_strip.next_thumb.clicked.connect(self.image_loader.next_image)
        
        # Image Loader & Canvas Events
        self.image_loader.image_changed.connect(self.on_image_changed)
        self.image_loader.preload_complete.connect(self.on_preload_complete)
        self.graphics_view.zoom_changed.connect(self.on_zoom_changed)
        self.graphics_view.crop_requested.connect(self.crop_and_save)

    # --- Slots / Events ---
    
    def select_output_folder(self):
        """Triggers FileDialog to select where crops are saved."""
        default_dir = self.settings.get("output_folder") or self.settings.get("input_folder") or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder for Crops", default_dir)
        if folder:
            self.settings.set("output_folder", folder)
            self.statusBar().showMessage(f"Output folder saved: {folder}", 4000)
            self.update_filename_preview()
            
            # Re-scan the input folder to filter out images already present in the new output folder
            input_folder = self.settings.get("input_folder")
            if input_folder and os.path.exists(input_folder):
                curr_path = self.image_loader.get_current_path()
                self.image_loader.scan_folder(input_folder, folder)
                self.populate_sidebar()
                
                # Restore selection to same image if it still exists in the filtered list
                if curr_path and curr_path in self.image_loader.images:
                    new_idx = self.image_loader.images.index(curr_path)
                    self.image_loader.set_index(new_idx)
                elif self.image_loader.images:
                    self.image_loader.set_index(0)
                else:
                    self.image_loader.current_index = -1
                    self.graphics_view.set_image(None)
                    self.update_thumbnails()

    def set_preset_dimensions(self, w, h):
        """Programmatically configures crop dimensions, bypassing signal locks."""
        self.is_updating_dimensions = True
        
        self.width_input.setText(str(w))
        self.height_input.setText(str(h))
        self.settings.set("crop_width", w)
        self.settings.set("crop_height", h)
        
        self.active_ratio = w / h
        self.graphics_view.set_crop_dimensions(w, h)
        
        # Unhighlight default aspect dropdown presets
        self.preset_dropdown.blockSignals(True)
        self.preset_dropdown.setCurrentText("Custom")
        self.preset_dropdown.blockSignals(False)
        self.settings.set("aspect_ratio_preset", "Custom")
        
        self.is_updating_dimensions = False
        
        self.update_preset_buttons(w, h)

    def update_preset_buttons(self, w, h):
        """Checks if active dimensions match any specific quick preset button and updates stylesheets."""
        is_cards = (w == 200 and h == 300)
        is_square = (w == 512 and h == 512)
        is_banner = (w == 1280 and h == 720)
        
        self.btn_preset_cards.setProperty("active", is_cards)
        self.btn_preset_square.setProperty("active", is_square)
        self.btn_preset_banner.setProperty("active", is_banner)
        
        # Reload styles for dynamic selector highlighting
        for btn in [self.btn_preset_cards, self.btn_preset_square, self.btn_preset_banner]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def on_dimensions_changed(self):
        """Handles manual width/height changes, maintaining locked ratio constraints."""
        if self.is_updating_dimensions:
            return
            
        self.is_updating_dimensions = True
        sender = self.sender()
        
        try:
            w = int(self.width_input.text() or 0)
            h = int(self.height_input.text() or 0)
        except ValueError:
            self.is_updating_dimensions = False
            return
            
        if w <= 0 or h <= 0:
            self.is_updating_dimensions = False
            return
            
        # If lock ratio is active, adjust counterpart field based on active_ratio
        if self.lock_ratio_checkbox.isChecked():
            if sender == self.width_input and self.active_ratio:
                h = int(w / self.active_ratio)
                self.height_input.setText(str(max(1, h)))
            elif sender == self.height_input and self.active_ratio:
                w = int(h * self.active_ratio)
                self.width_input.setText(str(max(1, w)))
        else:
            # If unlocked, update the active ratio dynamically as dimensions change
            self.active_ratio = w / h
            
        # Update settings
        self.settings.set("crop_width", w)
        self.settings.set("crop_height", h)
        
        # Update Canvas Frame Overlay
        self.graphics_view.set_crop_dimensions(w, h)
        
        self.is_updating_dimensions = False
        
        # Trigger dynamic preset buttons refresh
        self.update_preset_buttons(w, h)

    def on_lock_changed(self, checked):
        """Triggers ratio locks based on current settings."""
        self.settings.set("lock_aspect_ratio", checked)
        if checked:
            try:
                w = int(self.width_input.text() or 0)
                h = int(self.height_input.text() or 0)
                if w > 0 and h > 0:
                    self.active_ratio = w / h
            except ValueError:
                pass
        else:
            # If unlocking while preset was selected, switch to Custom preset
            if self.preset_dropdown.currentText() != "Custom":
                self.preset_dropdown.blockSignals(True)
                self.preset_dropdown.setCurrentText("Custom")
                self.preset_dropdown.blockSignals(False)
                self.settings.set("aspect_ratio_preset", "Custom")

    def on_preset_changed(self, text):
        """Handles aspect ratio presets dropdown items selection."""
        self.settings.set("aspect_ratio_preset", text)
        
        if text == "Custom":
            return
            
        # Parse active preset ratios
        if text == "1:1":
            self.active_ratio = 1.0
        elif text == "2:3":
            self.active_ratio = 2.0 / 3.0
        elif text == "16:9":
            self.active_ratio = 16.0 / 9.0
            
        self.is_updating_dimensions = True
        self.lock_ratio_checkbox.setChecked(True)
        self.settings.set("lock_aspect_ratio", True)
        
        try:
            w = int(self.width_input.text() or 0)
            if w > 0:
                h = int(w / self.active_ratio)
                self.height_input.setText(str(max(1, h)))
                self.settings.set("crop_width", w)
                self.settings.set("crop_height", h)
                self.graphics_view.set_crop_dimensions(w, h)
                self.update_preset_buttons(w, h)
        except ValueError:
            pass
            
        self.is_updating_dimensions = False

    def on_thirds_changed(self, checked):
        """Toggles guidelines visibility."""
        self.settings.set("show_rule_of_thirds", checked)
        self.graphics_view.set_show_rule_of_thirds(checked)

    def on_sidebar_selection_changed(self, row):
        """Handles row selection changes inside the sidebar."""
        if row >= 0 and row != self.image_loader.current_index:
            self.image_loader.set_index(row)

    def on_image_changed(self, index, path):
        """Triggered when loading a new image onto the canvas."""
        if index == -1 or not path:
            self.file_list.blockSignals(True)
            self.file_list.setCurrentRow(-1)
            self.file_list.blockSignals(False)
            self.counter_label.setText("0 / 0")
            self.statusBar().showMessage("No images to display.")
            self.graphics_view.set_image(None)
            self.update_thumbnails()
            self.update_filename_preview()
            return

        # 1. Update list selection without infinite recursion
        self.file_list.blockSignals(True)
        self.file_list.setCurrentRow(index)
        self.file_list.blockSignals(False)
        
        # 2. Update status info
        count = len(self.image_loader.images)
        self.counter_label.setText(f"{index + 1} / {count}")
        basename = os.path.basename(path)
        self.statusBar().showMessage(f"Viewing: {basename}")
        
        # Save session current index
        self.settings.set("last_image_index", index)
        
        # 3. Load from cache (or file if missing) and set on view
        image = self.image_loader.get_current_image()
        if image:
            self.graphics_view.set_image(image)
            
            # Hook to restore exact viewport position for undoing operations safely
            if self.pending_restore_state:
                rel_x = self.pending_restore_state.get("rel_x", 0.0)
                rel_y = self.pending_restore_state.get("rel_y", 0.0)
                rel_w = self.pending_restore_state.get("rel_w", 1.0)
                rel_h = self.pending_restore_state.get("rel_h", 1.0)
                self.pending_restore_state = None
                
                self.graphics_view.overlay.rel_x = rel_x
                self.graphics_view.overlay.rel_y = rel_y
                self.graphics_view.overlay.rel_w = rel_w
                self.graphics_view.overlay.rel_h = rel_h
                self.graphics_view.overlay.update_crop_rect()
                
                # Emit zoom relative to cover scale
                if self.graphics_view.overlay.rel_w > 0:
                    zoom_rel = self.graphics_view.overlay.initial_max_rel_w / self.graphics_view.overlay.rel_w
                    self.graphics_view.zoom_changed.emit(zoom_rel)
        else:
            self.statusBar().showMessage(f"Failed to load image: {basename}", 4000)
            
        # Refresh bottom thumbnail strip and next increment filename preview
        self.update_thumbnails()
        self.update_filename_preview()

    def on_preload_complete(self, filepath):
        """Silent callback triggering updates for preloaded thumbnail cards."""
        self.update_thumbnails()

    def on_zoom_changed(self, zoom):
        """Displays visual zoom percentages on toolbar label."""
        self.zoom_label.setText(f"Zoom: {int(zoom * 100)}%")

    def crop_and_save(self):
        """
        Coordinates original-resolution crop calculation, captures undo state,
        exports with high-quality, fires visual overlays, and advances.
        """
        # Ensure we have an active image loaded
        curr_path = self.image_loader.get_current_path()
        if not curr_path or not self.graphics_view.image_item:
            self.statusBar().showMessage("Error: No image loaded to crop!", 4000)
            return
            
        # Ensure output folder is selected
        out_dir = self.settings.get("output_folder")
        if not out_dir or not os.path.exists(out_dir):
            out_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder for Crops", "")
            if out_dir:
                self.settings.set("output_folder", out_dir)
            else:
                self.statusBar().showMessage("Saving Aborted: No output folder selected.", 4000)
                return
                
        # 1. Map overlay coordinate boundaries back to original image space
        visual_rect = self.graphics_view.overlay.crop_rect
        scene_rect = self.graphics_view.get_crop_scene_rect(visual_rect)
        
        # Get actual image dimensions
        img_w = self.graphics_view.image_item.pixmap().width()
        img_h = self.graphics_view.image_item.pixmap().height()
        
        # Convert floating boundaries to integer pixel ranges on original image
        left = int(max(0, min(img_w, scene_rect.x())))
        upper = int(max(0, min(img_h, scene_rect.y())))
        right = int(max(0, min(img_w, scene_rect.x() + scene_rect.width())))
        lower = int(max(0, min(img_h, scene_rect.y() + scene_rect.height())))
        
        if right <= left or lower <= upper:
            self.statusBar().showMessage("Error: Invalid crop coordinates mapped.", 4000)
            return
            
        # Save crop under the same filename in the output directory
        export_path = self.get_export_path(out_dir)
        if not export_path:
            self.statusBar().showMessage("Error: No image loaded to crop!", 4000)
            return
        
        # Capture Undo State representation
        undo_state = {
            "image_index": self.image_loader.current_index,
            "image_path": curr_path,
            "export_path": export_path,
            "rel_x": self.graphics_view.overlay.rel_x,
            "rel_y": self.graphics_view.overlay.rel_y,
            "rel_w": self.graphics_view.overlay.rel_w,
            "rel_h": self.graphics_view.overlay.rel_h,
        }
        
        # 2. Perform PIL high-quality crop
        try:
            with Image.open(curr_path) as img:
                cropped_img = img.crop((left, upper, right, lower))
                
                # Fetch target export dimensions
                target_w = self.settings.get("crop_width")
                target_h = self.settings.get("crop_height")
                
                # Resize cropped piece to exactly match dimensions using LANCZOS filter
                resized_img = cropped_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                # Format preservation
                format_name = img.format if img.format else "PNG"
                
                # Ultimate quality parameters
                save_args = {}
                
                # Preserving ICC profiles and metadata
                icc_profile = img.info.get("icc_profile")
                if icc_profile:
                    save_args["icc_profile"] = icc_profile
                    
                exif = img.info.get("exif")
                if exif:
                    save_args["exif"] = exif
                
                if format_name in ("JPEG", "MPO"):
                    # JPEGs do not support alpha channel
                    if resized_img.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", resized_img.size, (255, 255, 255))
                        bg.paste(resized_img, mask=resized_img.split()[3] if resized_img.mode == "RGBA" else None)
                        resized_img = bg
                    elif resized_img.mode != "RGB":
                        resized_img = resized_img.convert("RGB")
                    
                    save_args["quality"] = 98
                    save_args["subsampling"] = 0  # 4:4:4 chroma subsampling for best quality/sharpness
                    save_args["optimize"] = True
                elif format_name == "WEBP":
                    save_args["quality"] = 98
                    save_args["method"] = 6
                elif format_name == "PNG":
                    save_args["optimize"] = True
                
                # Save cropped image using correct format and arguments
                resized_img.save(export_path, format=format_name, **save_args)
                
                # Save state for undoing
                self.undo_stack.append(undo_state)
                
                # Trigger Overlay Flash animation & Fading Toast notification
                self.graphics_view.overlay.trigger_crop_animation()
                saved_filename = os.path.basename(export_path)
                self.graphics_view.overlay.show_toast(f"Saved: {saved_filename}")
                
                self.statusBar().showMessage(f"Successfully saved {saved_filename}! Auto-advancing...", 3000)
                
                # Remove the cropped image from the image loader list
                self.image_loader.remove_image_at_index(self.image_loader.current_index)
                
                # Refresh sidebar to reflect the removed image
                self.populate_sidebar()
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to crop or save the image:\n{e}")
            self.statusBar().showMessage(f"Export Error: {e}", 5000)

    def undo(self):
        """Restores the session to the previous state, deleting the last crop file completely."""
        if not self.undo_stack:
            self.statusBar().showMessage("Nothing to undo.", 3000)
            return
            
        state = self.undo_stack.pop()
        export_path = state["export_path"]
        
        # 1. Delete generated crop from disk
        if os.path.exists(export_path):
            try:
                os.remove(export_path)
                self.statusBar().showMessage(f"Undo: Deleted last crop {os.path.basename(export_path)}", 3000)
            except Exception as e:
                self.statusBar().showMessage(f"Undo: Failed to delete last crop file: {e}", 4000)
                
        # 2. Prepare restore state hook
        self.pending_restore_state = {
            "rel_x": state.get("rel_x", 0.0),
            "rel_y": state.get("rel_y", 0.0),
            "rel_w": state.get("rel_w", 1.0),
            "rel_h": state.get("rel_h", 1.0)
        }
        
        # 3. Reload image and restore the uncropped file to the list
        input_folder = self.settings.get("input_folder")
        output_folder = self.settings.get("output_folder")
        self.image_loader.scan_folder(input_folder, output_folder)
        self.populate_sidebar()
        
        self.image_loader.set_index(state["image_index"])

    def toggle_fullscreen(self):
        """Toggles fullscreen state safely, updating persist settings."""
        if self.isFullScreen():
            self.showNormal()
            self.settings.set("fullscreen_state", False)
            self.statusBar().showMessage("Normal mode.", 2000)
        else:
            self.showFullScreen()
            self.settings.set("fullscreen_state", True)
            self.statusBar().showMessage("Fullscreen mode activated.", 2000)

    def get_export_path(self, out_dir):
        """Returns the export path in the output directory with the same filename as the current image."""
        curr_path = self.image_loader.get_current_path()
        if not curr_path:
            return ""
        return os.path.join(out_dir, os.path.basename(curr_path))

    def update_filename_preview(self):
        """Updates the right-aligned bottom live preview showing next generated filename."""
        out_dir = self.settings.get("output_folder")
        if out_dir and os.path.exists(out_dir):
            next_path = self.get_export_path(out_dir)
            if next_path:
                next_filename = os.path.basename(next_path)
                self.filename_preview_label.setText(f"Saving as: <b style='color: #00f0ff;'>{next_filename}</b>")
            else:
                self.filename_preview_label.setText("Saving as: <i>No image loaded</i>")
        else:
            self.filename_preview_label.setText("Saving as: <i>Select output folder</i>")

    # --- Sidebar Populator ---
    
    def populate_sidebar(self):
        """Populates the list widget with base filenames of loaded images."""
        self.file_list.blockSignals(True)
        self.file_list.clear()
        
        for path in self.image_loader.images:
            name = os.path.basename(path)
            item = QListWidgetItem(name)
            item.setToolTip(path)
            self.file_list.addItem(item)
            
        # Select active row
        if self.image_loader.current_index >= 0:
            self.file_list.setCurrentRow(self.image_loader.current_index)
            
        self.file_list.blockSignals(False)

    # --- Bottom Thumbnails Strip Updates ---
    
    def update_thumbnails(self):
        """Updates the bottom Previous, Current, Next thumbnail cards safely using cached QImage items."""
        loader = self.image_loader
        n = len(loader.images)
        if n == 0:
            self.thumbnail_strip.prev_thumb.set_image(None)
            self.thumbnail_strip.curr_thumb.set_image(None)
            self.thumbnail_strip.next_thumb.set_image(None)
            return
            
        curr_idx = loader.current_index
        
        # 1. Previous image thumb
        if n > 1:
            prev_idx = (curr_idx - 1) % n
            prev_path = loader.images[prev_idx]
            prev_img = loader.cache.get(prev_path)
            self.thumbnail_strip.prev_thumb.set_image(prev_path, prev_img)
        else:
            self.thumbnail_strip.prev_thumb.set_image(None)
            
        # 2. Current image thumb
        curr_path = loader.images[curr_idx]
        curr_img = loader.cache.get(curr_path)
        self.thumbnail_strip.curr_thumb.set_image(curr_path, curr_img)
        
        # 3. Next image thumb
        if n > 1:
            next_idx = (curr_idx + 1) % n
            next_path = loader.images[next_idx]
            next_img = loader.cache.get(next_path)
            self.thumbnail_strip.next_thumb.set_image(next_path, next_img)
        else:
            self.thumbnail_strip.next_thumb.set_image(None)

    # --- Drag and Drop Folder Handlers ---
    
    def dragEnterEvent(self, event):
        """Accepts drags containing file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dropEvent(self, event):
        """Unpacks dropped elements, loading folders or files dynamically."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            folders = []
            files = []
            
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folders.append(path)
                elif os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        files.append(path)
            
            if folders:
                target_folder = folders[0]
                self.statusBar().showMessage(f"Loading dropped folder: {target_folder}", 3000)
                self.load_folder(target_folder)
            elif files:
                first_file = files[0]
                target_folder = os.path.dirname(first_file)
                self.statusBar().showMessage(f"Loading folder from dropped files: {target_folder}", 3000)
                self.load_folder(target_folder)
                # Auto select the specific dropped file
                if first_file in self.image_loader.images:
                    idx = self.image_loader.images.index(first_file)
                    self.image_loader.set_index(idx)
                    
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def load_folder(self, folder):
        """Updates settings with input folder, triggers scanning, and repopulates visual components."""
        self.settings.set("input_folder", folder)
        self.settings.set("last_image_index", 0)
        output_folder = self.settings.get("output_folder")
        self.image_loader.scan_folder(folder, output_folder)
        self.populate_sidebar()
        self.update_filename_preview()

    # --- Override Scanner Updates ---
    
    def on_image_list_scanned(self):
        """Event called after scanning a folder to repopulate lists."""
        self.populate_sidebar()
        count = len(self.image_loader.images)
        self.counter_label.setText(f"0 / {count}" if count == 0 else f"1 / {count}")
        self.update_thumbnails()
        self.update_filename_preview()
        
    def select_input_folder(self):
        """Override select input folder to additionally trigger sidebar refresh."""
        default_dir = self.settings.get("input_folder") or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images", default_dir)
        if folder:
            self.load_folder(folder)

    # --- Keyboard Shortcuts Routing ---
    
    def keyPressEvent(self, event):
        """Routes keyboard hotkeys A, D, Enter, R, F, and Ctrl+Z Undo."""
        key = event.key()
        modifiers = event.modifiers()
        
        # 1. Global Undo routing (Ctrl + Z) active regardless of focus to ensure seamless workflow
        if key == Qt.Key_Z and (modifiers & Qt.ControlModifier):
            self.undo()
            event.accept()
            return
            
        # Route keys if inputs don't currently have active focus to avoid writing characters inside widths, etc.
        focused_widget = self.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            super().keyPressEvent(event)
            return
            
        if key == Qt.Key_A:
            self.image_loader.prev_image()
        elif key == Qt.Key_D:
            self.image_loader.next_image()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self.crop_and_save()
        elif key == Qt.Key_R:
            self.graphics_view.reset_view()
        elif key == Qt.Key_F:
            self.toggle_fullscreen()
            event.accept()
        else:
            super().keyPressEvent(event)
