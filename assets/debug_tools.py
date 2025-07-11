from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

class DevToolsWindow(QMainWindow):
    """
    A simple window to host the QWebEngineView for the developer tools.
    """
    def __init__(self, page_to_inspect: QWebEnginePage, parent=None):
        """
        Initializes the developer tools window.

        Args:
            page_to_inspect (QWebEnginePage): The web page to inspect.
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Developer Tools")
        self.setGeometry(150, 150, 1024, 768)

        # --- FIX: Assign the view and page to instance attributes (self) ---
        # This prevents them from being prematurely garbage-collected by Python,
        # which would result in a blank window.
        self.dev_tools_view = QWebEngineView()
        self.dev_tools_page = page_to_inspect.devToolsPage()

        # Set the special developer tools page on our new view
        self.dev_tools_view.setPage(self.dev_tools_page)
        
        self.setCentralWidget(self.dev_tools_view)
