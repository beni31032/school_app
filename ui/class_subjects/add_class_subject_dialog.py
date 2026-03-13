from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QSpinBox
)

from database.connection import get_connection


class AddClassSubjectDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user

        self.setWindowTitle("Ajouter une matière à une classe")
        self.setFixedWidth(420)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.establishment_input = QComboBox()
        self.class_input = QComboBox()
        self.subject_input = QComboBox()

        self.coefficient_input = QSpinBox()
        self.coefficient_input.setMinimum(1)
        self.coefficient_input.setMaximum(20)
        self.coefficient_input.setValue(1)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Établissement :", self.establishment_input)
        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Matière :", self.subject_input)
        self.form_layout.addRow("Coefficient :", self.coefficient_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)
        self.setLayout(self.layout)

        self.load_establishments()
        self.load_subjects()

        self.establishment_input.currentIndexChanged.connect(self.load_classes)
        self.load_classes()

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
                    "SELECT id, name FROM establishments ORDER BY name"
                )
            else:
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
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

    def load_classes(self):
        self.class_input.clear()

        establishment_id = self.establishment_input.currentData()
        if establishment_id is None:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM classes
                WHERE establishment_id = %s
                ORDER BY name
                """,
                (establishment_id,)
            )
            rows = cursor.fetchall()

            for class_id, name in rows:
                self.class_input.addItem(name, class_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement classes impossible : {e}")
        finally:
            conn.close()

    def load_subjects(self):
        self.subject_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM subjects
                ORDER BY name
                """
            )
            rows = cursor.fetchall()

            for subject_id, name in rows:
                self.subject_input.addItem(name, subject_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement matières impossible : {e}")
        finally:
            conn.close()

    def save_data(self):
        class_id = self.class_input.currentData()
        subject_id = self.subject_input.currentData()
        coefficient = self.coefficient_input.value()

        if class_id is None or subject_id is None:
            QMessageBox.warning(self, "Validation", "Classe et matière sont obligatoires.")
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
                FROM class_subjects
                WHERE class_id = %s AND subject_id = %s
                """,
                (class_id, subject_id)
            )
            exists = cursor.fetchone()

            if exists:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Cette matière est déjà affectée à cette classe."
                )
                return

            cursor.execute(
                """
                INSERT INTO class_subjects (class_id, subject_id, coefficient)
                VALUES (%s, %s, %s)
                """,
                (class_id, subject_id, coefficient)
            )

            conn.commit()
            QMessageBox.information(self, "Succès", "Affectation enregistrée avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()