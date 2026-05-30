import os
import shutil
from uuid import uuid4

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QDateEdit, QLabel, QHBoxLayout, QFileDialog
)
from PyQt6.QtCore import QDate

from database.connection import get_connection


class EditStudentDialog(QDialog):
    def __init__(self, student_id, current_user, parent=None):
        super().__init__(parent)

        self.student_id = int(student_id)
        self.current_user = current_user

        self.current_school_year_id = None
        self.current_enrollment_id = None
        self.current_establishment_id = None
        self.current_photo_path = None
        self.photo_source_path = None

        self.setWindowTitle("Modifier élève")
        self.setFixedWidth(420)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.matricule_input = QLineEdit()
        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()

        self.birth_date_input = QDateEdit()
        self.birth_date_input.setCalendarPopup(True)
        self.birth_date_input.setDate(QDate.currentDate())
        self.birth_date_input.setDisplayFormat("yyyy-MM-dd")

        self.gender_input = QComboBox()
        self.gender_input.addItems(["Masculin", "Féminin"])

        self.establishment_label = QLabel("-")
        self.class_input = QComboBox()
        self.photo_label = QLabel("Aucune photo sélectionnée")
        self.photo_button = QPushButton("Choisir une photo")
        self.photo_button.clicked.connect(self.choose_photo)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_student)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Matricule :", self.matricule_input)
        self.form_layout.addRow("Prénom :", self.first_name_input)
        self.form_layout.addRow("Nom :", self.last_name_input)
        self.form_layout.addRow("Date de naissance :", self.birth_date_input)
        self.form_layout.addRow("Sexe :", self.gender_input)
        self.form_layout.addRow("Établissement :", self.establishment_label)
        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow(self.photo_button, self.photo_label)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)

        self.setLayout(self.layout)
        self.apply_local_styles()

        self.load_current_school_year()
        self.load_student()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 130px;
            }
            QLineEdit, QDateEdit, QComboBox {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                selection-background-color: #2563eb;
                selection-color: white;
                outline: none;
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

    def show_message(self, icon, title, text):
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.setStyleSheet(
            """
            QLabel {
                min-width: 360px;
                color: #111827;
            }
            """
        )
        box.exec()

    def load_current_school_year(self):
        conn = get_connection()
        if not conn:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM school_years
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

            if row:
                self.current_school_year_id = row[0]
            else:
                self.show_message(
                    QMessageBox.Icon.Warning,
                    "Validation",
                    "Aucune année scolaire n'existe dans la base."
                )
        except Exception as e:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", f"Chargement année scolaire impossible : {e}")
        finally:
            conn.close()

    def load_classes(self, establishment_id, selected_class_id=None):
        self.class_input.clear()

        conn = get_connection()
        if not conn:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", "Connexion base impossible")
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

            selected_index = 0
            for index, (class_id, name) in enumerate(rows):
                self.class_input.addItem(name, class_id)
                if selected_class_id is not None and class_id == selected_class_id:
                    selected_index = index

            if self.class_input.count() > 0:
                self.class_input.setCurrentIndex(selected_index)

        except Exception as e:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", f"Chargement classes impossible : {e}")
        finally:
            conn.close()

    def load_student(self):
        if self.current_school_year_id is None:
            return

        conn = get_connection()
        if not conn:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    s.matricule,
                    s.first_name,
                    s.last_name,
                    s.birth_date,
                    s.gender,
                    s.photo_path,
                    s.establishment_id,
                    est.name,
                    e.id AS enrollment_id,
                    e.class_id
                FROM students s
                LEFT JOIN establishments est ON est.id = s.establishment_id
                LEFT JOIN enrollments e
                    ON e.student_id = s.id
                    AND e.school_year_id = %s
                WHERE s.id = %s
                """,
                (self.current_school_year_id, self.student_id)
            )

            row = cursor.fetchone()

            if not row:
                self.show_message(QMessageBox.Icon.Warning, "Erreur", "Élève introuvable.")
                self.reject()
                return

            (
                matricule,
                first_name,
                last_name,
                birth_date,
                gender,
                photo_path,
                establishment_id,
                establishment_name,
                enrollment_id,
                class_id
            ) = row

            if self.current_user["role"] != "ADMIN_GLOBAL":
                if establishment_id != self.current_user["establishment_id"]:
                    self.show_message(QMessageBox.Icon.Critical, "Sécurité", "Action non autorisée.")
                    self.reject()
                    return

            self.current_establishment_id = establishment_id
            self.current_enrollment_id = enrollment_id

            self.matricule_input.setText(matricule or "")
            self.first_name_input.setText(first_name or "")
            self.last_name_input.setText(last_name or "")

            if birth_date:
                self.birth_date_input.setDate(QDate(birth_date.year, birth_date.month, birth_date.day))

            if gender:
                self.gender_input.setCurrentText(gender)

            self.establishment_label.setText(establishment_name or "-")
            self.current_photo_path = photo_path
            if photo_path:
                self.photo_label.setText(os.path.basename(photo_path))
            else:
                self.photo_label.setText("Aucune photo sélectionnée")

            self.load_classes(establishment_id, class_id)

        except Exception as e:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", f"Chargement élève impossible : {e}")
            self.reject()
        finally:
            conn.close()

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
            return self.current_photo_path

        os.makedirs("assets/photos", exist_ok=True)

        ext = os.path.splitext(self.photo_source_path)[1]
        new_name = f"{uuid4().hex}{ext}"
        destination = os.path.join("assets/photos", new_name)

        shutil.copy(self.photo_source_path, destination)
        return destination.replace("\\", "/")

    def update_student(self):
        matricule = self.matricule_input.text().strip()
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        birth_date = self.birth_date_input.date().toString("yyyy-MM-dd")
        gender = self.gender_input.currentText()
        class_id = self.class_input.currentData()
        photo_path = self.save_photo()

        if not matricule or not first_name or not last_name:
            self.show_message(QMessageBox.Icon.Warning, "Validation", "Matricule, prénom et nom sont obligatoires.")
            return

        if class_id is None:
            self.show_message(QMessageBox.Icon.Warning, "Validation", "Veuillez sélectionner une classe.")
            return

        conn = get_connection()
        if not conn:
            self.show_message(QMessageBox.Icon.Critical, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT establishment_id
                FROM classes
                WHERE id = %s
                """,
                (class_id,)
            )
            class_row = cursor.fetchone()

            if not class_row:
                conn.rollback()
                self.show_message(QMessageBox.Icon.Warning, "Validation", "Classe invalide.")
                return

            class_establishment_id = class_row[0]

            if class_establishment_id != self.current_establishment_id:
                conn.rollback()
                self.show_message(
                    QMessageBox.Icon.Warning,
                    "Validation",
                    "La classe choisie n'appartient pas à l'établissement de l'élève."
                )
                return

            cursor.execute(
                """
                UPDATE students
                SET matricule = %s,
                    first_name = %s,
                    last_name = %s,
                    birth_date = %s,
                    gender = %s,
                    photo_path = %s
                WHERE id = %s
                """,
                (
                    matricule,
                    first_name,
                    last_name,
                    birth_date,
                    gender,
                    photo_path,
                    self.student_id
                )
            )

            if self.current_enrollment_id is not None:
                cursor.execute(
                    """
                    UPDATE enrollments
                    SET class_id = %s
                    WHERE id = %s
                    """,
                    (class_id, self.current_enrollment_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO enrollments (student_id, class_id, school_year_id)
                    VALUES (%s, %s, %s)
                    """,
                    (self.student_id, class_id, self.current_school_year_id)
                )

            conn.commit()
            self.show_message(QMessageBox.Icon.Information, "Succès", "Élève modifié avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            self.show_message(QMessageBox.Icon.Critical, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()
