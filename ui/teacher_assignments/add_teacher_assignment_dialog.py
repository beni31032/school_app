from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox
)

from database.connection import get_connection


class AddTeacherAssignmentDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user

        self.setWindowTitle("Ajouter une affectation enseignant")
        self.setFixedWidth(450)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.establishment_input = QComboBox()
        self.class_input = QComboBox()
        self.subject_input = QComboBox()
        self.teacher_input = QComboBox()
        self.school_year_input = QComboBox()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Établissement :", self.establishment_input)
        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Matière :", self.subject_input)
        self.form_layout.addRow("Enseignant :", self.teacher_input)
        self.form_layout.addRow("Année scolaire :", self.school_year_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)
        self.setLayout(self.layout)

        self.load_establishments()
        self.load_teachers()
        self.load_school_years()

        self.establishment_input.currentIndexChanged.connect(self.load_classes)
        self.class_input.currentIndexChanged.connect(self.load_subjects_for_class)

        self.load_classes()
        self.load_subjects_for_class()

    def load_establishments(self):
        self.establishment_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
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

    def load_subjects_for_class(self):
        self.subject_input.clear()

        class_id = self.class_input.currentData()
        if class_id is None:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.name
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
                ORDER BY s.name
                """,
                (class_id,)
            )
            rows = cursor.fetchall()

            for subject_id, name in rows:
                self.subject_input.addItem(name, subject_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement matières impossible : {e}")
        finally:
            conn.close()

    def load_teachers(self):
        self.teacher_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, first_name || ' ' || last_name
                FROM teachers
                ORDER BY last_name, first_name
                """
            )
            rows = cursor.fetchall()

            for teacher_id, full_name in rows:
                self.teacher_input.addItem(full_name, teacher_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement enseignants impossible : {e}")
        finally:
            conn.close()

    def load_school_years(self):
        self.school_year_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM school_years
                ORDER BY id DESC
                """
            )
            rows = cursor.fetchall()

            for school_year_id, name in rows:
                self.school_year_input.addItem(name, school_year_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement années scolaires impossible : {e}")
        finally:
            conn.close()

    def save_data(self):
        teacher_id = self.teacher_input.currentData()
        subject_id = self.subject_input.currentData()
        class_id = self.class_input.currentData()
        school_year_id = self.school_year_input.currentData()

        if None in (teacher_id, subject_id, class_id, school_year_id):
            QMessageBox.warning(self, "Validation", "Tous les champs sont obligatoires.")
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
                FROM teacher_assignments
                WHERE teacher_id = %s
                  AND subject_id = %s
                  AND class_id = %s
                  AND school_year_id = %s
                """,
                (teacher_id, subject_id, class_id, school_year_id)
            )
            exists = cursor.fetchone()

            if exists:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Cette affectation existe déjà."
                )
                return

            cursor.execute(
                """
                INSERT INTO teacher_assignments (
                    teacher_id, subject_id, class_id, school_year_id
                )
                VALUES (%s, %s, %s, %s)
                """,
                (teacher_id, subject_id, class_id, school_year_id)
            )

            conn.commit()
            QMessageBox.information(self, "Succès", "Affectation enregistrée avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()