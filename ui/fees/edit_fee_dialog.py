from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QPushButton, QMessageBox, QHBoxLayout
)

from database.connection import get_connection


class EditFeeDialog(QDialog):
    def __init__(self, fee_id, parent=None):
        super().__init__(parent)

        self.fee_id = int(fee_id)

        self.setWindowTitle("Modifier un type de frais")
        self.setFixedWidth(400)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(100)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_fee)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Nom :", self.name_input)
        self.form_layout.addRow("Description :", self.description_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)

        self.setLayout(self.layout)
        self.apply_local_styles()

        self.load_fee()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 130px;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            """
        )

    def load_fee(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name, description
                FROM fees
                WHERE id = %s
                """,
                (self.fee_id,)
            )
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Type de frais introuvable.")
                self.reject()
                return

            name, description = row
            self.name_input.setText(name or "")
            self.description_input.setPlainText(description or "")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def update_fee(self):
        name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "Le nom du frais est obligatoire.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 1
                FROM fees
                WHERE LOWER(name) = LOWER(%s)
                  AND id <> %s
                """,
                (name, self.fee_id)
            )
            exists = cursor.fetchone()

            if exists:
                QMessageBox.warning(self, "Validation", "Ce type de frais existe déjà.")
                return

            cursor.execute(
                """
                UPDATE fees
                SET name = %s,
                    description = %s
                WHERE id = %s
                """,
                (name, description, self.fee_id)
            )
            conn.commit()

            QMessageBox.information(self, "Succès", "Type de frais modifié avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()
