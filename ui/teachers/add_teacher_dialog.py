from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox, QDateEdit
)
from PyQt6.QtCore import QDate

from database.connection import get_connection


class AddTeacherDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Ajouter un enseignant")
        self.setFixedWidth(400)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()

        self.hire_date_input = QDateEdit()
        self.hire_date_input.setCalendarPopup(True)
        self.hire_date_input.setDate(QDate.currentDate())

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_teacher)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Prénom :", self.first_name_input)
        self.form_layout.addRow("Nom :", self.last_name_input)
        self.form_layout.addRow("Téléphone :", self.phone_input)
        self.form_layout.addRow("Email :", self.email_input)
        self.form_layout.addRow("Date d'embauche :", self.hire_date_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

    def save_teacher(self):
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        hire_date = self.hire_date_input.date().toString("yyyy-MM-dd")

        if not first_name or not last_name:
            QMessageBox.warning(self, "Validation", "Prénom et nom sont obligatoires.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO teachers (first_name, last_name, phone, email, hire_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (first_name, last_name, phone, email, hire_date)
            )
            conn.commit()

            QMessageBox.information(self, "Succès", "Enseignant enregistré avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()