from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QComboBox, QPushButton, QMessageBox, QHBoxLayout
)

from database.connection import get_connection


class EditTeacherAssignmentDialog(QDialog):
    def __init__(self, assignment_id, current_user, parent=None):
        super().__init__(parent)

        self.assignment_id = int(assignment_id)
        self.current_user = current_user

        self.current_class_id = None
        self.current_establishment_id = None

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

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.apply_local_styles()

        self.load_school_years()
        self.load_data()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 135px;
            }
            QComboBox {
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

    def load_teachers(self, selected_teacher_id=None):
        self.teacher_input.clear()

        if self.current_establishment_id is None:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, last_name || ' ' || first_name
                FROM teachers
                WHERE establishment_id = %s
                  AND COALESCE(is_active, TRUE) = TRUE
                ORDER BY last_name, first_name
                """,
                (self.current_establishment_id,),
            )
            rows = cursor.fetchall()

            selected_index = 0
            for index, (teacher_id, full_name) in enumerate(rows):
                self.teacher_input.addItem(full_name, teacher_id)
                if selected_teacher_id is not None and teacher_id == selected_teacher_id:
                    selected_index = index

            if self.teacher_input.count() > 0:
                self.teacher_input.setCurrentIndex(selected_index)

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
                        c.establishment_id,
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
                        c.establishment_id,
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

            (
                teacher_id,
                subject_id,
                school_year_id,
                class_id,
                class_name,
                establishment_id,
                establishment_name,
            ) = row

            self.current_class_id = class_id
            self.current_establishment_id = establishment_id
            self.class_label.setText(class_name or "-")
            self.establishment_label.setText(establishment_name or "-")

            self.load_teachers(selected_teacher_id=teacher_id)
            self.load_subjects_for_class(selected_subject_id=subject_id)

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

            cursor.execute(
                """
                SELECT 1
                FROM teacher_assignments
                WHERE teacher_id = %s
                  AND subject_id = %s
                  AND class_id = %s
                  AND school_year_id = %s
                  AND id <> %s
                """,
                (
                    teacher_id,
                    subject_id,
                    self.current_class_id,
                    school_year_id,
                    self.assignment_id,
                ),
            )
            if cursor.fetchone():
                QMessageBox.warning(self, "Validation", "Cette affectation existe déjà.")
                return

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
