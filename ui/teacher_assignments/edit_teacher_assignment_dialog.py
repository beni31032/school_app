from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QComboBox, QPushButton, QMessageBox
)

from database.connection import get_connection


class EditTeacherAssignmentDialog(QDialog):
    def __init__(self, assignment_id, current_user, parent=None):
        super().__init__(parent)

        self.assignment_id = int(assignment_id)
        self.current_user = current_user

        self.current_class_id = None

        self.setWindowTitle("Modifier une affectation")
        self.setFixedWidth(450)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.class_label = QLabel("-")
        self.establishment_label = QLabel("-")
        self.subject_input = QComboBox()
        self.teacher_input = QComboBox()
        self.school_year_input = QComboBox()

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Établissement :", self.establishment_label)
        self.form_layout.addRow("Classe :", self.class_label)
        self.form_layout.addRow("Matière :", self.subject_input)
        self.form_layout.addRow("Enseignant :", self.teacher_input)
        self.form_layout.addRow("Année scolaire :", self.school_year_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)
        self.setLayout(self.layout)

        self.load_teachers()
        self.load_school_years()
        self.load_data()

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

    def load_subjects_for_class(self, selected_subject_id=None):
        self.subject_input.clear()

        if self.current_class_id is None:
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
                (self.current_class_id,)
            )
            rows = cursor.fetchall()

            selected_index = 0
            for index, (subject_id, name) in enumerate(rows):
                self.subject_input.addItem(name, subject_id)
                if selected_subject_id is not None and subject_id == selected_subject_id:
                    selected_index = index

            if self.subject_input.count() > 0:
                self.subject_input.setCurrentIndex(selected_index)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement matières impossible : {e}")
        finally:
            conn.close()

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        ta.teacher_id,
                        ta.subject_id,
                        ta.school_year_id,
                        c.id,
                        c.name,
                        e.name
                    FROM teacher_assignments ta
                    JOIN classes c ON c.id = ta.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    WHERE ta.id = %s
                    """,
                    (self.assignment_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        ta.teacher_id,
                        ta.subject_id,
                        ta.school_year_id,
                        c.id,
                        c.name,
                        e.name
                    FROM teacher_assignments ta
                    JOIN classes c ON c.id = ta.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    WHERE ta.id = %s
                      AND c.establishment_id = %s
                    """,
                    (self.assignment_id, self.current_user["establishment_id"])
                )

            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Affectation introuvable ou non autorisée.")
                self.reject()
                return

            teacher_id, subject_id, school_year_id, class_id, class_name, establishment_name = row

            self.current_class_id = class_id
            self.class_label.setText(class_name or "-")
            self.establishment_label.setText(establishment_name or "-")

            self.load_subjects_for_class(selected_subject_id=subject_id)

            teacher_index = self.teacher_input.findData(teacher_id)
            if teacher_index >= 0:
                self.teacher_input.setCurrentIndex(teacher_index)

            year_index = self.school_year_input.findData(school_year_id)
            if year_index >= 0:
                self.school_year_input.setCurrentIndex(year_index)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def update_data(self):
        teacher_id = self.teacher_input.currentData()
        subject_id = self.subject_input.currentData()
        school_year_id = self.school_year_input.currentData()

        if None in (teacher_id, subject_id, school_year_id):
            QMessageBox.warning(self, "Validation", "Tous les champs sont obligatoires.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    UPDATE teacher_assignments
                    SET teacher_id = %s,
                        subject_id = %s,
                        school_year_id = %s
                    WHERE id = %s
                    """,
                    (teacher_id, subject_id, school_year_id, self.assignment_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE teacher_assignments ta
                    SET teacher_id = %s,
                        subject_id = %s,
                        school_year_id = %s
                    FROM classes c
                    WHERE ta.id = %s
                      AND c.id = ta.class_id
                      AND c.establishment_id = %s
                    """,
                    (
                        teacher_id,
                        subject_id,
                        school_year_id,
                        self.assignment_id,
                        self.current_user["establishment_id"]
                    )
                )

            conn.commit()
            QMessageBox.information(self, "Succès", "Affectation modifiée avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()