import os
import shutil
from uuid import uuid4

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QFileDialog, QMessageBox, QDateEdit, QLabel
)
from PyQt6.QtCore import QDate

from database.connection import get_connection


class AddStudentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Ajouter un élève")
        self.setFixedWidth(400)

        self.photo_source_path = None
        self.saved_photo_path = None

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.matricule_input = QLineEdit()
        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()

        self.birth_date_input = QDateEdit()
        self.birth_date_input.setCalendarPopup(True)
        self.birth_date_input.setDate(QDate.currentDate())

        self.gender_input = QComboBox()
        self.gender_input.addItems(["Masculin", "Féminin"])

        self.establishment_input = QComboBox()
        self.class_input = QComboBox()

        self.photo_label = QLabel("Aucune photo sélectionnée")
        self.photo_button = QPushButton("Choisir une photo")
        self.photo_button.clicked.connect(self.choose_photo)

        self.save_button = QPushButton("Enregistrer")
        self.save_button.clicked.connect(self.save_student)

        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.reject)

        self.form_layout.addRow("Matricule :", self.matricule_input)
        self.form_layout.addRow("Prénom :", self.first_name_input)
        self.form_layout.addRow("Nom :", self.last_name_input)
        self.form_layout.addRow("Date de naissance :", self.birth_date_input)
        self.form_layout.addRow("Sexe :", self.gender_input)
        self.form_layout.addRow("Établissement :", self.establishment_input)
        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow(self.photo_button, self.photo_label)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.cancel_button)

        self.setLayout(self.layout)

        self.load_establishments()
        self.establishment_input.currentIndexChanged.connect(self.load_classes)
        self.load_classes()

    def load_establishments(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM establishments ORDER BY name")
        rows = cursor.fetchall()
        conn.close()

        self.establishment_input.clear()
        for est_id, name in rows:
            self.establishment_input.addItem(name, est_id)

    def load_classes(self):
        self.class_input.clear()

        establishment_id = self.establishment_input.currentData()
        if establishment_id is None:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

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
        conn.close()

        for class_id, name in rows:
            self.class_input.addItem(name, class_id)

    def choose_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une photo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            self.photo_source_path = file_path
            self.photo_label.setText(os.path.basename(file_path))

    def save_photo(self):
        if not self.photo_source_path:
            return None

        os.makedirs("assets/photos", exist_ok=True)

        ext = os.path.splitext(self.photo_source_path)[1]
        new_name = f"{uuid4().hex}{ext}"
        destination = os.path.join("assets/photos", new_name)

        shutil.copy(self.photo_source_path, destination)
        return destination.replace("\\", "/")

    def save_student(self):
        matricule = self.matricule_input.text().strip()
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        birth_date = self.birth_date_input.date().toString("yyyy-MM-dd")
        gender = self.gender_input.currentText()
        establishment_id = self.establishment_input.currentData()
        class_id = self.class_input.currentData()

        if not matricule or not first_name or not last_name:
            QMessageBox.warning(self, "Validation", "Matricule, prénom et nom sont obligatoires.")
            return

        if establishment_id is None or class_id is None:
            QMessageBox.warning(self, "Validation", "Établissement et classe sont obligatoires.")
            return

        photo_path = self.save_photo()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO students (
                    matricule, first_name, last_name, birth_date,
                    gender, establishment_id, photo_path
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    matricule, first_name, last_name, birth_date,
                    gender, establishment_id, photo_path
                )
            )

            student_id = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT id
                FROM school_years
                ORDER BY id DESC
                LIMIT 1
                """
            )
            year_row = cursor.fetchone()

            if year_row is None:
                conn.rollback()
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Aucune année scolaire définie. Crée d'abord une année scolaire."
                )
                return

            school_year_id = year_row[0]

            cursor.execute(
                """
                INSERT INTO enrollments (student_id, class_id, school_year_id)
                VALUES (%s, %s, %s)
                """,
                (student_id, class_id, school_year_id)
            )

            conn.commit()
            QMessageBox.information(self, "Succès", "Élève enregistré avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()