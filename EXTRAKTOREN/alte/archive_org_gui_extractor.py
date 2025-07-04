import sys
import requests
import json
import os
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar, QTextEdit, QMessageBox,
    QFormLayout, QComboBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QCoreApplication

# --- Extraktionslogik für Archive.org ---

class ArchiveOrgExtractorWorker(QObject):
    """
    Die Worker-Klasse, die die eigentliche Extraktionslogik für Archive.org enthält.
    Sie läuft in einem separaten QThread.
    """
    progress_update = pyqtSignal(int, str)
    extraction_finished = pyqtSignal(list, str, str, str) # data, query, media_type, filename_suffix
    extraction_error = pyqtSignal(str)

    def __init__(self, query: str, media_type: str, num_results: int, parent=None):
        super().__init__(parent)
        self.query = query
        self.media_type = media_type
        self.num_results = num_results
        self.BASE_URL = "https://archive.org/advancedsearch.php"
        self.session = requests.Session()
        self.setObjectName("ArchiveOrgWorker")

    def do_extraction(self):
        """
        Führt die Suche auf Archive.org durch und extrahiert Metadaten.
        """
        try:
            self.progress_update.emit(0, f"Starte Suche auf Archive.org nach '{self.query}' (Typ: {self.media_type})...")
            
            fields = [
                'identifier',
                'title',
                'description',
                'creator',
                'publicdate',
                'subject',
                'language',
                'item_size',
                'url' # NEU: URL des Items hinzufügen
            ]

            params = {
                'q': f'({self.query}) AND mediatype:{self.media_type}',
                'fl[]': fields,
                'rows': self.num_results,
                'page': 1,
                'output': 'json'
            }

            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            extracted_docs = []
            if 'response' in data and 'docs' in data['response']:
                docs = data['response']['docs']
                self.progress_update.emit(50, f"Gefunden: {len(docs)} Dokumente. Verarbeite Details...")
                
                for i, doc in enumerate(docs):
                    # Konstruiere die Item-URL, da 'url' nicht immer direkt in fl[] ist
                    item_url = f"https://archive.org/details/{doc.get('identifier')}" if doc.get('identifier') else None

                    extracted_docs.append({
                        "identifier": doc.get('identifier'),
                        "title": doc.get('title'),
                        "description": doc.get('description'),
                        "creator": doc.get('creator'),
                        "publicdate": doc.get('publicdate'),
                        "subject": doc.get('subject'),
                        "language": doc.get('language'),
                        "item_size": doc.get('item_size'),
                        "url": item_url # Hinzugefügte URL
                    })
                    self.progress_update.emit(50 + int(50 * (i / len(docs))), f"Verarbeite Dokument {i+1}/{len(docs)}: {doc.get('title')[:50]}...")

                self.progress_update.emit(100, f"Extraktion abgeschlossen. {len(extracted_docs)} Einträge gefunden.")
                self.extraction_finished.emit(extracted_docs, self.query, self.media_type, "archive_org")
            else:
                self.progress_update.emit(100, "Keine Dokumente gefunden oder unerwartete API-Antwortstruktur.")
                self.extraction_finished.emit([], self.query, self.media_type, "archive_org")

        except requests.exceptions.RequestException as e:
            self.extraction_error.emit(f"Netzwerkfehler oder API-Problem: {e}\n{traceback.format_exc()}")
            self.progress_update.emit(0, "Fehler: Netzwerkproblem.")
        except json.JSONDecodeError as e:
            self.extraction_error.emit(f"Fehler beim Parsen der JSON-Antwort von Archive.org: {e}\n{traceback.format_exc()}")
            self.progress_update.emit(0, "Fehler: JSON-Parsing-Fehler.")
        except Exception as e:
            self.extraction_error.emit(f"Ein unerwarteter Fehler ist aufgetreten: {e}\n{traceback.format_exc()}")
            self.progress_update.emit(0, "Fehler: Unerwarteter Fehler.")

# --- Debug-Fenster (Wiederverwendung aus gui_extractor.py) ---

class DebugWindow(QDialog):
    """
    Ein separates Fenster zur Anzeige detaillierter Debug-Informationen.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Debug-Konsole (Archive.org)")
        self.setGeometry(200, 200, 700, 500)

        layout = QVBoxLayout(self)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFontPointSize(9)
        layout.addWidget(self.log_display)

        clear_button = QPushButton("Log leeren")
        clear_button.clicked.connect(self.log_display.clear)
        layout.addWidget(clear_button)

    def log_message(self, message: str):
        """Fügt eine Nachricht zur Debug-Konsole hinzu."""
        self.log_display.append(message)
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())

# --- GUI-Anwendung ---

class ArchiveOrgExtractorGUI(QWidget):
    """
    Die Haupt-GUI-Anwendung für den Archive.org-Extraktor.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Archive.org Extractor")
        self.setGeometry(100, 100, 650, 500)

        self.extractor_thread = None
        self.extractor_worker = None

        self.debug_window = DebugWindow(self)
        QApplication.instance().aboutToQuit.connect(self.debug_window.close)

        self._original_excepthook = sys.excepthook
        sys.excepthook = self._custom_excepthook

        self.init_ui()
        self.add_log("Bereit zur Extraktion von Archive.org.")

    def _custom_excepthook(self, exc_type, exc_value, exc_traceback):
        """
        Benutzerdefinierter Exception-Hook, der unhandled Exceptions abfängt
        und in die Log-Konsolen schreibt.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        error_message = f"Unhandled Exception: {exc_type.__name__}: {exc_value}\n"
        error_message += "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        self.add_log(f"FEHLER (Unhandled): {error_message}")
        QMessageBox.critical(self, "Unerwarteter Fehler", "Ein unerwarteter Fehler ist aufgetreten. Details finden Sie in der Debug-Konsole.")
        
        self.start_button.setEnabled(True)
        self.extractor_worker = None
        self.extractor_thread = None

    def init_ui(self):
        """
        Initialisiert die Benutzeroberfläche der Anwendung.
        """
        main_layout = QVBoxLayout(self)

        input_form_layout = QFormLayout()
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("z.B. keltische Münzfunde, römische Kastelle")
        input_form_layout.addRow("Suchanfrage:", self.query_input)

        self.media_type_selector = QComboBox()
        self.media_type_selector.addItems(["texts", "audio", "movies", "images", "software", "web", "collection"])
        input_form_layout.addRow("Medientyp:", self.media_type_selector)

        self.num_results_input = QLineEdit("50")
        self.num_results_input.setPlaceholderText("Anzahl der Ergebnisse (Standard: 50)")
        input_form_layout.addRow("Max. Ergebnisse:", self.num_results_input)

        main_layout.addLayout(input_form_layout)

        self.start_button = QPushButton("Extraktion starten")
        self.start_button.clicked.connect(self.start_extraction)
        main_layout.addWidget(self.start_button)

        self.debug_button = QPushButton("Debug-Fenster öffnen")
        self.debug_button.clicked.connect(self.debug_window.show)
        main_layout.addWidget(self.debug_button)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(150)
        main_layout.addWidget(self.log_console)

        # Beispiel-Buttons
        example_label = QLabel("Beispiele:")
        main_layout.addWidget(example_label)

        examples_layout = QHBoxLayout()
        example_button_kelten_muenzfunde = QPushButton("Kelten Münzfunde (Texte)")
        example_button_kelten_muenzfunde.clicked.connect(
            lambda: self.load_example("keltische Münzfunde", "texts", "50")
        )
        examples_layout.addWidget(example_button_kelten_muenzfunde)

        example_button_roemer_kastelle = QPushButton("Römer Kastelle (Texte)")
        example_button_roemer_kastelle.clicked.connect(
            lambda: self.load_example("römische Kastelle", "texts", "50")
        )
        examples_layout.addWidget(example_button_roemer_kastelle)
        
        example_button_hist_maps = QPushButton("Historische Karten (Bilder)")
        example_button_hist_maps.clicked.connect(
            lambda: self.load_example("historische Karten Europa", "images", "20")
        )
        examples_layout.addWidget(example_button_hist_maps)

        main_layout.addLayout(examples_layout)

    def load_example(self, query, media_type, num_results):
        """Lädt Beispielwerte in die Eingabefelder."""
        self.query_input.setText(query)
        self.media_type_selector.setCurrentText(media_type)
        self.num_results_input.setText(num_results)
        self.add_log(f"Beispiel '{query}' ({media_type}) geladen.")

    def add_log(self, message: str):
        """
        Fügt eine Nachricht zur Haupt-Log-Konsole und zur Debug-Konsole hinzu.
        """
        self.log_console.append(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())
        self.debug_window.log_message(f"[{QThread.currentThread().objectName() or 'MainThread'}] {message}")

    def start_extraction(self):
        """
        Startet den Extraktionsprozess in einem separaten Thread.
        """
        query = self.query_input.text().strip()
        media_type = self.media_type_selector.currentText()
        num_results_str = self.num_results_input.text().strip()

        if not query:
            QMessageBox.warning(self, "Eingabefehler", "Bitte geben Sie eine Suchanfrage ein.")
            return
        
        try:
            num_results = int(num_results_str)
            if num_results <= 0:
                raise ValueError("Anzahl der Ergebnisse muss positiv sein.")
        except ValueError:
            QMessageBox.warning(self, "Eingabefehler", "Bitte geben Sie eine gültige Zahl für 'Max. Ergebnisse' ein.")
            return

        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.add_log(f"Starte Extraktion für: Anfrage='{query}', Typ='{media_type}', Ergebnisse='{num_results}'")

        self.extractor_thread = QThread()
        self.extractor_thread.setObjectName("ArchiveOrgExtractorThread")
        self.extractor_worker = ArchiveOrgExtractorWorker(query, media_type, num_results)
        self.extractor_worker.setObjectName("ArchiveOrgWorker")
        
        self.extractor_worker.moveToThread(self.extractor_thread)

        self.extractor_thread.started.connect(self.extractor_worker.do_extraction)
        
        self.extractor_worker.progress_update.connect(self.update_progress)
        self.extractor_worker.extraction_finished.connect(self.handle_extraction_finished, Qt.ConnectionType.QueuedConnection)
        self.extractor_worker.extraction_error.connect(self.handle_extraction_error, Qt.ConnectionType.QueuedConnection)
        
        self.extractor_worker.extraction_finished.connect(self.extractor_thread.quit)
        self.extractor_worker.extraction_error.connect(self.extractor_thread.quit)
        
        self.extractor_thread.finished.connect(self.extractor_worker.deleteLater)
        self.extractor_thread.finished.connect(self.extractor_thread.deleteLater)
        
        self.extractor_thread.start()

    def update_progress(self, value: int, message: str):
        """Aktualisiert den Fortschrittsbalken und die Log-Konsole."""
        self.progress_bar.setValue(value)
        self.add_log(message)

    def handle_extraction_finished(self, data: list, query: str, media_type: str, filename_suffix: str):
        """
        Wird aufgerufen, wenn die Extraktion abgeschlossen ist.
        Speichert die Daten und reaktiviert den Start-Button.
        """
        self.add_log(f"Extraktion abgeschlossen. {len(data)} Einträge gefunden.")
        if data:
            self.save_to_json(data, query, media_type, filename_suffix)
        else:
            self.add_log("Keine Daten zum Speichern vorhanden.")
        
        self.start_button.setEnabled(True)

    def handle_extraction_error(self, error_message: str):
        """
        Wird aufgerufen, wenn ein Fehler während der Extraktion auftritt.
        Zeigt eine Fehlermeldung an und reaktiviert den Start-Button.
        """
        self.add_log(f"Fehler bei der Extraktion: {error_message}")
        QMessageBox.critical(self, "Extraktionsfehler", error_message)
        
        self.start_button.setEnabled(True)

    def save_to_json(self, daten: list, query: str, media_type: str, filename_suffix: str):
        """
        Speichert die extrahierten Daten in einer JSON-Datei.
        """
        # Dateiname basierend auf Anfrage und Medientyp
        clean_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        filename = f"{clean_query.replace(' ', '_').lower()}_{media_type}_{filename_suffix}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(daten, f, indent=4, ensure_ascii=False)
            self.add_log(f"Daten erfolgreich in '{filename}' gespeichert.")
        except IOError as e:
            self.add_log(f"Fehler beim Speichern der Daten in '{filename}': {e}")
            QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der Daten: {e}")

# --- Hauptausführung ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArchiveOrgExtractorGUI()
    window.show()
    sys.exit(app.exec())
