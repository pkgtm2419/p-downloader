"""
Batch Add Downloads Dialog (IDM Feature).
Allows entering multiple download URLs at once to enqueue in batch.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QSpinBox, QGroupBox, QGridLayout, QMessageBox
)
from core.categories import CATEGORY_EXTENSIONS

class BatchDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Batch Downloads (Multiple URLs)")
        self.resize(600, 450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # URLs text area
        grp_urls = QGroupBox("Enter URLs (one address per line)")
        vbox_urls = QVBoxLayout(grp_urls)
        
        self.txt_urls = QTextEdit()
        self.txt_urls.setPlaceholderText(
            "https://example.com/file1.zip\n"
            "https://example.com/file2.mp4\n"
            "https://example.com/file3.pdf"
        )
        vbox_urls.addWidget(self.txt_urls)
        layout.addWidget(grp_urls)

        # Configuration
        grp_cfg = QGroupBox("Batch Options")
        grid = QGridLayout(grp_cfg)

        grid.addWidget(QLabel("Default Category:"), 0, 0)
        self.cmb_cat = QComboBox()
        self.cmb_cat.addItems(["Auto-Detect"] + list(CATEGORY_EXTENSIONS.keys()) + ["General"])
        grid.addWidget(self.cmb_cat, 0, 1)

        grid.addWidget(QLabel("Connections per Download:"), 1, 0)
        self.spin_conns = QSpinBox()
        self.spin_conns.setRange(1, 32)
        self.spin_conns.setValue(8)
        grid.addWidget(self.spin_conns, 1, 1)

        layout.addWidget(grp_cfg)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start All Now")
        self.btn_start.clicked.connect(lambda: self._submit(auto_start=True))

        self.btn_queue = QPushButton("Add to Queue (Start Later)")
        self.btn_queue.setObjectName("secondaryBtn")
        self.btn_queue.clicked.connect(lambda: self._submit(auto_start=False))

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_queue)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.urls = []
        self.auto_start = True

    def _submit(self, auto_start: bool):
        raw_text = self.txt_urls.toPlainText().strip()
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        valid_urls = [u for u in lines if u.startswith("http://") or u.startswith("https://") or u.startswith("ftp://")]

        if not valid_urls:
            QMessageBox.warning(self, "No Valid URLs", "Please enter at least one valid HTTP/HTTPS URL.")
            return

        self.urls = valid_urls
        self.auto_start = auto_start
        self.accept()

    def get_result(self) -> dict:
        cat = self.cmb_cat.currentText()
        return {
            "urls": self.urls,
            "category": None if cat == "Auto-Detect" else cat,
            "connections": self.spin_conns.value(),
            "auto_start": self.auto_start
        }
