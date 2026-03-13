from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox
)

from database.connection import get_connection


class AddSubjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Ajouter une matière")
        self.setFixedWidth(350)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_input = QLineEdit()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_subject)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Nom de la matière :", self.name_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

    def save_subject(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "Le nom de la matière est obligatoire.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO subjects (name)
                VALUES (%s)
                """,
                (name,)
            )
            conn.commit()

            QMessageBox.information(self, "Succès", "Matière enregistrée avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()