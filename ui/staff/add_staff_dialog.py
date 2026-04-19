from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
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
        self.hire_date_input.setDisplayFormat("yyyy-MM-dd")

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

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.apply_local_styles()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 130px;
            }
            QLineEdit, QDateEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
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
