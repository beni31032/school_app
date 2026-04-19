from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QDateEdit,
    QHBoxLayout,
)
from PyQt6.QtCore import QDate

from database.connection import get_connection


class EditTeacherDialog(QDialog):
    def __init__(self, teacher_id, current_user, parent=None):
        super().__init__(parent)

        self.teacher_id = int(teacher_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Modifier un enseignant")
        self.setFixedWidth(430)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()

        self.hire_date_input = QDateEdit()
        self.hire_date_input.setCalendarPopup(True)
        self.hire_date_input.setDate(QDate.currentDate())
        self.hire_date_input.setDisplayFormat("yyyy-MM-dd")

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_teacher)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Prénom :", self.first_name_input)
        self.form_layout.addRow("Nom :", self.last_name_input)
        self.form_layout.addRow("Téléphone :", self.phone_input)
        self.form_layout.addRow("Email :", self.email_input)
        self.form_layout.addRow("Date d'embauche :", self.hire_date_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)

        self.setLayout(self.layout)
        self.apply_local_styles()

        self.load_teacher()

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

    def load_teacher(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                cursor.execute(
                    """
                    SELECT first_name, last_name, phone, email, hire_date
                    FROM teachers
                    WHERE id = %s
                    """,
                    (self.teacher_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT first_name, last_name, phone, email, hire_date
                    FROM teachers
                    WHERE id = %s AND establishment_id = %s
                    """,
                    (self.teacher_id, self.current_user.get("establishment_id")),
                )
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Enseignant introuvable.")
                self.reject()
                return

            first_name, last_name, phone, email, hire_date = row

            self.first_name_input.setText(first_name or "")
            self.last_name_input.setText(last_name or "")
            self.phone_input.setText(phone or "")
            self.email_input.setText(email or "")

            if hire_date:
                self.hire_date_input.setDate(QDate(hire_date.year, hire_date.month, hire_date.day))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def update_teacher(self):
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        phone = self.phone_input.text().strip() or None
        email = self.email_input.text().strip() or None
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

            if self.is_global_admin:
                cursor.execute("SELECT establishment_id FROM teachers WHERE id = %s", (self.teacher_id,))
            else:
                cursor.execute(
                    "SELECT establishment_id FROM teachers WHERE id = %s AND establishment_id = %s",
                    (self.teacher_id, self.current_user.get("establishment_id")),
                )
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Enseignant introuvable.")
                return
            est_id = row[0]

            if phone:
                cursor.execute(
                    """
                    SELECT 1 FROM teachers
                    WHERE establishment_id = %s AND phone = %s AND id <> %s
                    LIMIT 1
                    """,
                    (est_id, phone, self.teacher_id),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Téléphone déjà utilisé.")
                    return

            if email:
                cursor.execute(
                    """
                    SELECT 1 FROM teachers
                    WHERE establishment_id = %s AND LOWER(email) = LOWER(%s) AND id <> %s
                    LIMIT 1
                    """,
                    (est_id, email, self.teacher_id),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Email déjà utilisé.")
                    return

            if self.is_global_admin:
                cursor.execute(
                    """
                    UPDATE teachers
                    SET first_name = %s,
                        last_name = %s,
                        phone = %s,
                        email = %s,
                        hire_date = %s
                    WHERE id = %s
                    """,
                    (first_name, last_name, phone, email, hire_date, self.teacher_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE teachers
                    SET first_name = %s,
                        last_name = %s,
                        phone = %s,
                        email = %s,
                        hire_date = %s
                    WHERE id = %s AND establishment_id = %s
                    """,
                    (first_name, last_name, phone, email, hire_date, self.teacher_id, est_id),
                )

            conn.commit()
            QMessageBox.information(self, "Succès", "Enseignant modifié avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()
