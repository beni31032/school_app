from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
)

from database.connection import get_connection
from utils.subject_service import ensure_subject_schema


class AddSubjectDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"
        ensure_subject_schema()

        self.setWindowTitle("Ajouter une matiere")
        self.setFixedWidth(380)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_input = QLineEdit()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_subject)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Nom de la matiere :", self.name_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)

        self.setLayout(self.layout)
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
            QLineEdit {
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

    def save_subject(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "Le nom de la matiere est obligatoire.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            est_id = self.current_user.get("establishment_id")
            if self.is_global_admin and est_id is None:
                cursor.execute("SELECT id FROM establishments ORDER BY id LIMIT 1")
                row = cursor.fetchone()
                est_id = row[0] if row else None

            if not est_id:
                QMessageBox.warning(self, "Validation", "Aucun etablissement disponible.")
                return

            cursor.execute(
                """
                SELECT 1
                FROM subjects
                WHERE LOWER(name) = LOWER(%s)
                  AND establishment_id = %s
                LIMIT 1
                """,
                (name, est_id),
            )
            if cursor.fetchone():
                QMessageBox.warning(self, "Validation", "Cette matiere existe deja dans cet etablissement.")
                return

            cursor.execute(
                """
                INSERT INTO subjects (name, establishment_id)
                VALUES (%s, %s)
                """,
                (name, est_id)
            )
            conn.commit()

            QMessageBox.information(self, "Succes", "Matiere enregistree avec succes.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()
