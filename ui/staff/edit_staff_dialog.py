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


class EditStaffDialog(QDialog):
    def __init__(self, staff_id, current_user, parent=None):
        super().__init__(parent)
        self.staff_id = int(staff_id)
        self.current_user = current_user

        self.setWindowTitle("Modifier un employé")
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

        form.addRow("Prénom :", self.first_name_input)
        form.addRow("Nom :", self.last_name_input)
        form.addRow("Poste :", self.role_title_input)
        form.addRow("Téléphone :", self.phone_input)
        form.addRow("Email :", self.email_input)
        form.addRow("Date d'embauche :", self.hire_date_input)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")
        self.save_btn.clicked.connect(self.update_staff)
        self.cancel_btn.clicked.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)

        self.load_staff()

    def load_staff(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT first_name, last_name, role_title, phone, email, hire_date
                    FROM staff_members
                    WHERE id = %s
                    """,
                    (self.staff_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT first_name, last_name, role_title, phone, email, hire_date
                    FROM staff_members
                    WHERE id = %s AND establishment_id = %s
                    """,
                    (self.staff_id, self.current_user["establishment_id"]),
                )
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Employé introuvable.")
                self.reject()
                return

            first_name, last_name, role_title, phone, email, hire_date = row
            self.first_name_input.setText(first_name or "")
            self.last_name_input.setText(last_name or "")
            self.role_title_input.setText(role_title or "")
            self.phone_input.setText(phone or "")
            self.email_input.setText(email or "")
            if hire_date:
                self.hire_date_input.setDate(QDate.fromString(str(hire_date), "yyyy-MM-dd"))
            else:
                self.hire_date_input.setDate(QDate.currentDate())
        finally:
            conn.close()

    def update_staff(self):
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
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute("SELECT establishment_id FROM staff_members WHERE id = %s", (self.staff_id,))
            else:
                cursor.execute(
                    "SELECT establishment_id FROM staff_members WHERE id = %s AND establishment_id = %s",
                    (self.staff_id, self.current_user["establishment_id"]),
                )
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Employé introuvable.")
                return
            est_id = row[0]

            if phone:
                cursor.execute(
                    """
                    SELECT 1 FROM staff_members
                    WHERE establishment_id = %s AND phone = %s AND id <> %s
                    LIMIT 1
                    """,
                    (est_id, phone, self.staff_id),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Téléphone déjà utilisé.")
                    return

            if email:
                cursor.execute(
                    """
                    SELECT 1 FROM staff_members
                    WHERE establishment_id = %s AND LOWER(email) = LOWER(%s) AND id <> %s
                    LIMIT 1
                    """,
                    (est_id, email, self.staff_id),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Email déjà utilisé.")
                    return

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    UPDATE staff_members
                    SET first_name=%s, last_name=%s, role_title=%s, phone=%s, email=%s, hire_date=%s
                    WHERE id=%s
                    """,
                    (first_name, last_name, role_title, phone, email, hire_date, self.staff_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE staff_members
                    SET first_name=%s, last_name=%s, role_title=%s, phone=%s, email=%s, hire_date=%s
                    WHERE id=%s AND establishment_id=%s
                    """,
                    (first_name, last_name, role_title, phone, email, hire_date, self.staff_id, self.current_user["establishment_id"]),
                )

            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Mise à jour impossible : {e}")
        finally:
            conn.close()
