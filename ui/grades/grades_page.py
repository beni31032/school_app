from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

from database.connection import get_connection


class GradesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.current_school_year_id = None

        self.main_layout = QVBoxLayout()
        self.filters_layout = QFormLayout()
        self.buttons_layout = QHBoxLayout()

        self.class_input = QComboBox()
        self.subject_input = QComboBox()
        self.term_input = QComboBox()

        self.load_btn = QPushButton("Charger")
        self.save_btn = QPushButton("Enregistrer les notes")

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID Élève", "Élève", "Note"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.filters_layout.addRow("Classe :", self.class_input)
        self.filters_layout.addRow("Matière :", self.subject_input)
        self.filters_layout.addRow("Trimestre :", self.term_input)

        self.buttons_layout.addWidget(self.load_btn)
        self.buttons_layout.addWidget(self.save_btn)

        self.main_layout.addLayout(self.filters_layout)
        self.main_layout.addLayout(self.buttons_layout)
        self.main_layout.addWidget(self.table)

        self.setLayout(self.main_layout)

        self.class_input.currentIndexChanged.connect(self.load_subjects_for_class)
        self.load_btn.clicked.connect(self.load_students_for_grading)
        self.save_btn.clicked.connect(self.save_grades)

        self.load_current_school_year()
        self.load_classes()
        self.load_terms()

    def load_current_school_year(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id
                FROM school_years
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Validation", "Aucune année scolaire trouvée.")
                return

            self.current_school_year_id = row[0]

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement année scolaire impossible : {e}")
        finally:
            conn.close()

    def load_classes(self):
        self.class_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT c.id, e.name || ' - ' || c.name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    ORDER BY e.name, c.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name
                    FROM classes
                    WHERE establishment_id = %s
                    ORDER BY name
                    """,
                    (self.current_user["establishment_id"],)
                )

            rows = cursor.fetchall()

            for class_id, label in rows:
                self.class_input.addItem(label, class_id)

            self.load_subjects_for_class()

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

    def load_terms(self):
        self.term_input.clear()

        if self.current_school_year_id is None:
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
                FROM terms
                WHERE school_year_id = %s
                ORDER BY id
                """,
                (self.current_school_year_id,)
            )
            rows = cursor.fetchall()

            for term_id, name in rows:
                self.term_input.addItem(name, term_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement trimestres impossible : {e}")
        finally:
            conn.close()

    def get_teacher_for_assignment(self, class_id, subject_id):
        conn = get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT teacher_id
                FROM teacher_assignments
                WHERE class_id = %s
                  AND subject_id = %s
                  AND school_year_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (class_id, subject_id, self.current_school_year_id)
            )
            row = cursor.fetchone()
            return row[0] if row else None

        except Exception:
            return None
        finally:
            conn.close()

    def load_students_for_grading(self):
        class_id = self.class_input.currentData()
        subject_id = self.subject_input.currentData()
        term_id = self.term_input.currentData()

        if None in (class_id, subject_id, term_id):
            QMessageBox.warning(self, "Validation", "Classe, matière et trimestre sont obligatoires.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.last_name || ' ' || s.first_name AS student_name,
                    g.value
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                LEFT JOIN grades g
                    ON g.student_id = s.id
                   AND g.subject_id = %s
                   AND g.term_id = %s
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND s.is_active = TRUE
                ORDER BY s.last_name, s.first_name
                """,
                (subject_id, term_id, class_id, self.current_school_year_id)
            )
            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))

            for row_index, (student_id, student_name, grade_value) in enumerate(rows):
                self.table.setItem(row_index, 0, QTableWidgetItem(str(student_id)))
                self.table.setItem(row_index, 1, QTableWidgetItem(student_name))

                grade_item = QTableWidgetItem("" if grade_value is None else str(grade_value))
                grade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_index, 2, grade_item)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement élèves impossible : {e}")
        finally:
            conn.close()

    def save_grades(self):
        class_id = self.class_input.currentData()
        subject_id = self.subject_input.currentData()
        term_id = self.term_input.currentData()

        if None in (class_id, subject_id, term_id):
            QMessageBox.warning(self, "Validation", "Classe, matière et trimestre sont obligatoires.")
            return

        teacher_id = self.get_teacher_for_assignment(class_id, subject_id)

        if teacher_id is None:
            QMessageBox.warning(
                self,
                "Validation",
                "Aucun enseignant n'est affecté à cette matière pour cette classe et cette année."
            )
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            for row in range(self.table.rowCount()):
                student_id_item = self.table.item(row, 0)
                grade_item = self.table.item(row, 2)

                if not student_id_item:
                    continue

                student_id = int(student_id_item.text())
                raw_value = grade_item.text().strip() if grade_item else ""

                if raw_value == "":
                    continue

                try:
                    value = float(raw_value)
                except ValueError:
                    conn.rollback()
                    QMessageBox.warning(
                        self,
                        "Validation",
                        f"Note invalide à la ligne {row + 1}."
                    )
                    return

                if value < 0 or value > 20:
                    conn.rollback()
                    QMessageBox.warning(
                        self,
                        "Validation",
                        f"La note doit être comprise entre 0 et 20 (ligne {row + 1})."
                    )
                    return

                cursor.execute(
                    """
                    SELECT id
                    FROM grades
                    WHERE student_id = %s
                      AND subject_id = %s
                      AND term_id = %s
                    """,
                    (student_id, subject_id, term_id)
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE grades
                        SET value = %s,
                            teacher_id = %s,
                            created_by = %s
                        WHERE id = %s
                        """,
                        (value, teacher_id, self.current_user["id"], existing[0])
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO grades (
                            student_id, subject_id, teacher_id, term_id, value, created_by
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (student_id, subject_id, teacher_id, term_id, value, self.current_user["id"])
                    )

            conn.commit()
            QMessageBox.information(self, "Succès", "Notes enregistrées avec succès.")

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()