from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox
)

from database.connection import get_connection


class EditSubjectDialog(QDialog):
    def __init__(self, subject_id, parent=None):
        super().__init__(parent)

        self.subject_id = int(subject_id)

        self.setWindowTitle("Modifier une matière")
        self.setFixedWidth(350)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_input = QLineEdit()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_subject)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Nom de la matière :", self.name_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

        self.load_subject()

    def load_subject(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name
                FROM subjects
                WHERE id = %s
                """,
                (self.subject_id,)
            )
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Matière introuvable.")
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
                UPDATE subjects
                SET name = %s
                WHERE id = %s
                """,
                (name, self.subject_id)
            )
            conn.commit()

            QMessageBox.information(self, "Succès", "Matière modifiée avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()