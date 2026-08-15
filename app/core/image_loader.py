import os
import glob
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtGui import QImage

SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')

class PreloadWorker(QThread):
    """Background worker thread to load an image into a QImage to avoid GUI lag."""
    loaded = Signal(str, QImage)  # Emits (filepath, QImage)
    
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        
    def run(self):
        try:
            image = QImage(self.filepath)
            if not image.isNull():
                self.loaded.emit(self.filepath, image)
        except Exception as e:
            print(f"Error preloading {self.filepath}: {e}")


class ImageLoader(QObject):
    """Manages directory scanning, image list, current index, and background preloading cache."""
    image_changed = Signal(int, str)  # Emits (current_index, current_filepath)
    preload_complete = Signal(str)     # Emits (filepath) when an image is cached
    
    def __init__(self):
        super().__init__()
        self.folder_path = ""
        self.output_folder = ""
        self.images = []
        self.current_index = -1
        
        # Cache for preloaded QImage objects: {filepath: QImage}
        self.cache = {}
        self.max_cache_size = 5
        self.preload_threads = []

    def scan_folder(self, folder_path, output_folder=None):
        """Scans the folder for supported image files and resets state."""
        self.folder_path = folder_path
        self.output_folder = output_folder
        self.images = []
        self.current_index = -1
        self.clear_cache()
        
        if not folder_path or not os.path.exists(folder_path):
            return
            
        try:
            # Gather base names of images already in output directory (case-insensitive)
            output_basenames = set()
            if self.output_folder and os.path.exists(self.output_folder):
                try:
                    for out_f in os.listdir(self.output_folder):
                        out_ext = os.path.splitext(out_f)[1].lower()
                        if out_ext in SUPPORTED_EXTENSIONS:
                            output_basenames.add(os.path.splitext(out_f)[0].lower())
                except Exception as e:
                    print(f"Error scanning output folder {self.output_folder}: {e}")

            # Find all files with supported extensions (case-insensitive)
            all_files = os.listdir(folder_path)
            for f in sorted(all_files):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    base = os.path.splitext(f)[0].lower()
                    if base in output_basenames:
                        continue
                    full_path = os.path.abspath(os.path.join(folder_path, f))
                    self.images.append(full_path)
            
            if self.images:
                self.current_index = 0
                
        except Exception as e:
            print(f"Error scanning folder {folder_path}: {e}")
            
        # Emit changes if images were found or even if empty (to reset state)
        if self.current_index != -1:
            self.image_changed.emit(self.current_index, self.get_current_path())
            self.trigger_preloads()
        else:
            self.image_changed.emit(-1, None)

    def remove_image_at_index(self, index):
        """Removes the image at the specified index (e.g. after cropping) and updates state."""
        if 0 <= index < len(self.images):
            self.images.pop(index)
            self.clear_cache()
            
            if not self.images:
                self.current_index = -1
                self.image_changed.emit(-1, None)
            else:
                # If index was the last element, wrap around or clamp
                if index >= len(self.images):
                    self.current_index = 0
                else:
                    self.current_index = index
                    
                self.image_changed.emit(self.current_index, self.get_current_path())
                self.trigger_preloads()

    def get_current_path(self):
        """Returns the filepath of the current image, or None if no images."""
        if 0 <= self.current_index < len(self.images):
            return self.images[self.current_index]
        return None

    def get_current_image(self):
        """Returns the current QImage (sync loads if not in cache)."""
        path = self.get_current_path()
        if not path:
            return None
            
        # If cached, return it
        if path in self.cache:
            return self.cache[path]
            
        # Otherwise, load synchronously
        image = QImage(path)
        if not image.isNull():
            self.cache[path] = image
            return image
        return None

    def next_image(self):
        """Advances to the next image if possible."""
        if len(self.images) > 0:
            self.current_index = (self.current_index + 1) % len(self.images)
            self.image_changed.emit(self.current_index, self.get_current_path())
            self.trigger_preloads()

    def prev_image(self):
        """Moves to the previous image if possible."""
        if len(self.images) > 0:
            self.current_index = (self.current_index - 1) % len(self.images)
            self.image_changed.emit(self.current_index, self.get_current_path())
            self.trigger_preloads()

    def set_index(self, index):
        """Sets the active index directly."""
        if 0 <= index < len(self.images):
            self.current_index = index
            self.image_changed.emit(self.current_index, self.get_current_path())
            self.trigger_preloads()

    def clear_cache(self):
        """Clears the preload cache and stops pending threads."""
        for thread in self.preload_threads:
            if thread.isRunning():
                thread.terminate()
                thread.wait()
        self.preload_threads.clear()
        self.cache.clear()

    def trigger_preloads(self):
        """Spawns background preload threads for adjacent images."""
        if not self.images:
            return
            
        # Determine paths we want to preload: current, next 2, previous 1
        desired_paths = []
        n = len(self.images)
        
        # We want to prioritize: current, next, next-next, prev
        offsets = [0, 1, 2, -1]
        for offset in offsets:
            idx = (self.current_index + offset) % n
            path = self.images[idx]
            if path not in desired_paths:
                desired_paths.append(path)
                
        # Evict paths that are no longer needed from the cache
        keys_to_remove = [k for k in self.cache.keys() if k not in desired_paths]
        for k in keys_to_remove:
            del self.cache[k]
            
        # Clean finished preloader threads
        self.preload_threads = [t for t in self.preload_threads if t.isRunning()]
        
        # Start preloading for paths that are not yet in cache
        for path in desired_paths:
            if path not in self.cache:
                # Check if we already have an active preloader thread for this path
                already_preloading = any(t.filepath == path for t in self.preload_threads)
                if not already_preloading:
                    worker = PreloadWorker(path)
                    worker.loaded.connect(self._on_image_preloaded)
                    self.preload_threads.append(worker)
                    worker.start()

    def _on_image_preloaded(self, filepath, qimage):
        """Callback when background preloading of an image is complete."""
        self.cache[filepath] = qimage
        self.preload_complete.emit(filepath)
