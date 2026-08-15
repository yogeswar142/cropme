import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # Make sure we can run from anywhere by adding the app's parent folder to sys.path if needed
    # But since main.py is run directly, standard Python relative imports work inside the packages
    app_dir = os.path.dirname(os.path.abspath(__file__))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
        
    app = QApplication(sys.argv)
    app.setApplicationName("CropMe")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
