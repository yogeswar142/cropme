import os
import json

class AppSettings:
    """Manages application settings saved in settings.json."""
    
    DEFAULT_SETTINGS = {
        "input_folder": "",
        "output_folder": "",
        "crop_width": 800,
        "crop_height": 600,
        "lock_aspect_ratio": True,
        "aspect_ratio_preset": "Custom",
        "show_rule_of_thirds": True,
        "last_image_index": 0,
        "fullscreen_state": False,
        "last_opened_folders": []
    }
    
    def __init__(self, filepath="settings.json"):
        # Make the settings path relative to main.py's directory if it is just a filename
        if not os.path.isabs(filepath):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.filepath = os.path.join(base_dir, filepath)
        else:
            self.filepath = filepath
            
        self.data = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Loads settings from settings.json, falling back to defaults if not found or corrupt."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    # Merge loaded data with defaults to ensure all keys exist
                    for k, v in self.DEFAULT_SETTINGS.items():
                        self.data[k] = loaded_data.get(k, v)
            else:
                self.save()
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.data = self.DEFAULT_SETTINGS.copy()

    def save(self):
        """Saves current settings to settings.json."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        """Gets a configuration setting."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Sets a configuration setting and saves it."""
        self.data[key] = value
        self.save()
