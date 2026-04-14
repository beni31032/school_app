from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from database.connection import get_connection
from utils.salary_service import ensure_salary_table


class AddStaffDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user

        self.setWindowTitle("Ajouter un employé")
        self.setFixedWidth(420)

        ensure_salary_table()

        layout = QVBoxLayout()
        form = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.role_title_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.hire_date_input = QDateEdit()
        self.hire_date_input.setCalendarPopup(True)
        self.hire_date_input.setDate(QDate.currentDate())

        form.addRow("Prénom :", self.first_name_input)
        form.addRow("Nom :", self.last_name_input)
        form.addRow("Poste :", self.role_title_input)
        form.addRow("Téléphone :", self.phone_input)
        form.addRow("Email :", self.email_input)
        form.addRow("Date d'embauche :", self.hire_date_input)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")
        self.save_btn.clicked.connect(self.save_staff)
        self.cancel_btn.clicked.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)

    def save_staff(self):
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        role_title = self.role_title_input.text().strip()
        phone = self.phone_input.text().strip() or None
        email = self.email_input.text().strip() or None
        hire_date = self.hire_date_input.date().toString("yyyy-MM-dd")

        if not first_name or not last_name or not role_title:
            QMessageBox.warning(self, "Validation", "Prénom, nom et poste sont obligatoires.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            est_id = self.current_user.get("establishment_id")
            if self.current_user.get("role") == "ADMIN_GLOBAL" and est_id is None:
                cursor.execute("SELECT id FROM establishments ORDER BY id LIMIT 1")
                row = cursor.fetchone()
                est_id = row[0] if row else None

            if not est_id:
                QMessageBox.warning(self, "Validation", "Aucun établissement disponible.")
                return

            if phone:
                cursor.execute(
                    """
                    SELECT 1 FROM staff_members
                    WHERE establishment_id = %s AND phone = %s
                    LIMIT 1
                    """,
                    (est_id, phone),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Téléphone déjà utilisé.")
                    return

            if email:
                cursor.execute(
                    """
                    SELECT 1 FROM staff_members
                    WHERE establishment_id = %s AND LOWER(email) = LOWER(%s)
                    LIMIT 1
                    """,
                    (est_id, email),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Email déjà utilisé.")
                    return

            cursor.execute(
                """
                INSERT INTO staff_members (
                    establishment_id, first_name, last_name, role_title, phone, email, hire_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (est_id, first_name, last_name, role_title, phone, email, hire_date),
            )
            conn.commit()
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()
