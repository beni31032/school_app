from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QPushButton, QMessageBox
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

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

        self.load_fee()

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