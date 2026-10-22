"""
IDM-Grade Site Logins & Password Manager Dialog for P-Downloader.
Allows configuring domain-level credentials, HTTP Basic/Digest authentication,
and Bearer tokens for premium hosters and private servers.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDialogButtonBox, QWidget
)
from PyQt6.QtCore import Qt
from core.credentials_manager import CredentialsManager

class SiteLoginEditDialog(QDialog):
    def __init__(self, parent=None, domain="", username="", password="", auth_type="basic", token=""):
        super().__init__(parent)
        self.setWindowTitle("Site Credential Entry")
        self.resize(400, 260)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2430;
                color: #e2e8f0;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8fafc;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #10b981;
            }
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #10b981;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("<b>Server / Host Domain:</b> (e.g. rapidgator.net, dl.site.com)"))
        self.edit_domain = QLineEdit(domain)
        layout.addWidget(self.edit_domain)

        layout.addWidget(QLabel("<b>Authentication Type:</b>"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Basic Authentication (User/Password)", "Bearer Token"])
        if auth_type == "bearer":
            self.combo_type.setCurrentIndex(1)
        self.combo_type.currentIndexChanged.connect(self._toggle_auth_fields)
        layout.addWidget(self.combo_type)

        self.widget_basic = QWidget()
        v_basic = QVBoxLayout(self.widget_basic)
        v_basic.setContentsMargins(0, 0, 0, 0)
        v_basic.addWidget(QLabel("<b>Username:</b>"))
        self.edit_user = QLineEdit(username)
        v_basic.addWidget(self.edit_user)
        v_basic.addWidget(QLabel("<b>Password:</b>"))
        self.edit_pass = QLineEdit(password)
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        v_basic.addWidget(self.edit_pass)
        layout.addWidget(self.widget_basic)

        self.widget_bearer = QWidget()
        v_bearer = QVBoxLayout(self.widget_bearer)
        v_bearer.setContentsMargins(0, 0, 0, 0)
        v_bearer.addWidget(QLabel("<b>API / Bearer Token:</b>"))
        self.edit_token = QLineEdit(token)
        v_bearer.addWidget(self.edit_token)
        layout.addWidget(self.widget_bearer)

        self._toggle_auth_fields()

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setStyleSheet("background-color: #334155;")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_save = QPushButton("Save Credential", self)
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        layout.addLayout(btns)

    def _toggle_auth_fields(self):
        is_bearer = (self.combo_type.currentIndex() == 1)
        self.widget_basic.setVisible(not is_bearer)
        self.widget_bearer.setVisible(is_bearer)

    def _save(self):
        domain = self.edit_domain.text().strip()
        if not domain:
            QMessageBox.warning(self, "Invalid Domain", "Please enter a valid domain name.")
            return
        self.accept()

    def get_data(self):
        is_bearer = (self.combo_type.currentIndex() == 1)
        return {
            "domain": self.edit_domain.text().strip(),
            "auth_type": "bearer" if is_bearer else "basic",
            "username": self.edit_user.text().strip(),
            "password": self.edit_pass.text(),
            "token": self.edit_token.text().strip()
        }

class SiteLoginsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = CredentialsManager()
        self.setWindowTitle("Site Logins & Authentication Manager")
        self.resize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2430;
                color: #e2e8f0;
            }
            QTableWidget {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                gridline-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 6px;
                border: 1px solid #334155;
                font-weight: 600;
            }
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #10b981;
            }
            QPushButton#btnSecondary {
                background-color: #334155;
                color: #e2e8f0;
            }
            QPushButton#btnSecondary:hover {
                background-color: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        desc = QLabel(
            "Configure authentication credentials for sites that require logins (e.g. premium hosts, private clouds). "
            "P-Downloader automatically supplies these credentials when downloading from matching domains."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(desc)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Domain / Server", "Auth Type", "Username / Token"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        btn_bar = QHBoxLayout()
        self.btn_add = QPushButton("➕ Add Site...")
        self.btn_add.clicked.connect(self._add_site)
        btn_bar.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ Edit...")
        self.btn_edit.setObjectName("btnSecondary")
        self.btn_edit.clicked.connect(self._edit_site)
        btn_bar.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("🗑️ Remove")
        self.btn_delete.setObjectName("btnSecondary")
        self.btn_delete.clicked.connect(self._delete_site)
        btn_bar.addWidget(self.btn_delete)

        btn_bar.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("btnSecondary")
        self.btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(self.btn_close)

        layout.addLayout(btn_bar)

        self._refresh_list()

    def _refresh_list(self):
        logins = self.manager.get_all_logins()
        self.table.setRowCount(len(logins))
        for row, item in enumerate(logins):
            self.table.setItem(row, 0, QTableWidgetItem(item.get("domain", "")))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("auth_type", "basic").upper()))
            detail = item.get("username", "") if item.get("auth_type") != "bearer" else "•••••••• (Bearer Token)"
            self.table.setItem(row, 2, QTableWidgetItem(detail))

    def _add_site(self):
        dlg = SiteLoginEditDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            self.manager.set_login(
                domain=data["domain"],
                username=data["username"],
                password=data["password"],
                auth_type=data["auth_type"],
                token=data["token"]
            )
            self._refresh_list()

    def _edit_site(self):
        row = self.table.currentRow()
        if row < 0:
            return
        domain = self.table.item(row, 0).text()
        cred = self.manager.get_login(domain)
        if cred:
            dlg = SiteLoginEditDialog(
                self,
                domain=cred.get("domain", ""),
                username=cred.get("username", ""),
                password=cred.get("password", ""),
                auth_type=cred.get("auth_type", "basic"),
                token=cred.get("token", "")
            )
            if dlg.exec():
                data = dlg.get_data()
                self.manager.set_login(
                    domain=data["domain"],
                    username=data["username"],
                    password=data["password"],
                    auth_type=data["auth_type"],
                    token=data["token"]
                )
                self._refresh_list()

    def _delete_site(self):
        row = self.table.currentRow()
        if row < 0:
            return
        domain = self.table.item(row, 0).text()
        c = QMessageBox.question(self, "Confirm Delete", f"Remove saved credentials for '{domain}'?")
        if c == QMessageBox.StandardButton.Yes:
            self.manager.delete_login(domain)
            self._refresh_list()
