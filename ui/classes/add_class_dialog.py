from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox
)

from database.connection import get_connection


class AddClassDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user

        self.setWindowTitle("Ajouter une classe")
        self.setFixedWidth(400)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.level_input = QLineEdit()
        self.establishment_input = QComboBox()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_class)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Nom de la classe :", self.name_input)
        self.form_layout.addRow("Niveau :", self.level_input)
        self.form_layout.addRow("Établissement :", self.establishment_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)
        self.setLayout(self.layout)

        self.load_establishments()

    def load_establishments(self):
        self.establishment_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT id, name
                    FROM establishments
                    ORDER BY name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name
                    FROM establishments
                    WHERE id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )

            rows = cursor.fetchall()

            for est_id, name in rows:
                self.establishment_input.addItem(name, est_id)

            if self.current_user["role"] != "ADMIN_GLOBAL":
                self.establishment_input.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement établissements impossible : {e}")
        finally:
            conn.close()

    def save_class(self):
        name = self.name_input.text().strip()
        level = self.level_input.text().strip()
        establishment_id = self.establishment_input.currentData()

        if not name or not level:
            QMessageBox.warning(self, "Validation", "Nom de classe et niveau sont obligatoires.")
            return

        if establishment_id is None:
            QMessageBox.warning(self, "Validation", "Établissement invalide.")
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
                FROM classes
                WHERE name = %s
                  AND establishment_id = %s
                """,
                (name, establishment_id)
            )
            exists = cursor.fetchone()

            if exists:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Une classe avec ce nom existe déjà dans cet établissement."
                )
                return

            cursor.execute(
                """
                INSERT INTO classes (name, level, establishment_id)
                VALUES (%s, %s, %s)
                """,
                (name, level, establishment_id)
            )

            conn.commit()
            QMessageBox.information(self, "Succès", "Classe enregistrée avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()