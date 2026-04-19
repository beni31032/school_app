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


class EditSubjectDialog(QDialog):
    def __init__(self, subject_id, current_user, parent=None):
        super().__init__(parent)

        self.subject_id = int(subject_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"
        ensure_subject_schema()

        self.setWindowTitle("Modifier une matiere")
        self.setFixedWidth(380)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_input = QLineEdit()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_subject)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Nom de la matiere :", self.name_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)

        self.setLayout(self.layout)
        self.apply_local_styles()

        self.load_subject()

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

    def load_subject(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT name
                FROM subjects
                WHERE id = %s
            """
            params = [self.subject_id]
            if not self.is_global_admin:
                sql += " AND establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Matiere introuvable.")
                self.reject()
                return

            self.name_input.setText(row[0] or "")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def update_subject(self):
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

            if self.is_global_admin:
                cursor.execute("SELECT establishment_id FROM subjects WHERE id = %s", (self.subject_id,))
            else:
                cursor.execute(
                    "SELECT establishment_id FROM subjects WHERE id = %s AND establishment_id = %s",
                    (self.subject_id, self.current_user.get("establishment_id")),
                )
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Matiere introuvable.")
                return
            est_id = row[0]

            cursor.execute(
                """
                SELECT 1
                FROM subjects
                WHERE LOWER(name) = LOWER(%s)
                  AND establishment_id = %s
                  AND id <> %s
                LIMIT 1
                """,
                (name, est_id, self.subject_id)
            )
            if cursor.fetchone():
                QMessageBox.warning(self, "Validation", "Cette matiere existe deja dans cet etablissement.")
                return

            if self.is_global_admin:
                cursor.execute(
                    """
                    UPDATE subjects
                    SET name = %s
                    WHERE id = %s
                    """,
                    (name, self.subject_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE subjects
                    SET name = %s
                    WHERE id = %s
                      AND establishment_id = %s
                    """,
                    (name, self.subject_id, est_id)
                )
            conn.commit()

            QMessageBox.information(self, "Succes", "Matiere modifiee avec succes.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()
