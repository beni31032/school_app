from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView,QAbstractItemView
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from utils.table_style import setup_table


class PrimaryGradesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.subjects = []

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.class_input = QComboBox()
        self.term_input = QComboBox()

        self.load_btn = QPushButton("Charger")
        self.save_btn = QPushButton("Enregistrer")

        self.table = QTableWidget()
        setup_table(self.table, stretch=True)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked |
            QAbstractItemView.EditTrigger.EditKeyPressed)

        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Trimestre :", self.term_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.load_btn)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.save_btn)

        self.setLayout(self.layout)

        self.load_btn.clicked.connect(self.load_grid)
        self.save_btn.clicked.connect(self.save_grades)

        self.load_classes()
        self.load_terms()

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
                    SELECT
                        c.id,
                        e.name || ' - ' || c.name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN cycles cy ON cy.id = c.cycle_id
                    WHERE cy.name = 'Primaire'
                    ORDER BY e.name, c.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        c.id,
                        c.name
                    FROM classes c
                    JOIN cycles cy ON cy.id = c.cycle_id
                    WHERE c.establishment_id = %s
                      AND cy.name = 'Primaire'
                    ORDER BY c.name
                    """,
                    (self.current_user["establishment_id"],)
                )

            rows = cursor.fetchall()

            for class_id, label in rows:
                self.class_input.addItem(label, class_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement classes impossible : {e}")
        finally:
            conn.close()

    def load_terms(self):
        self.term_input.clear()

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
                ORDER BY id
                """
            )

            rows = cursor.fetchall()

            for term_id, name in rows:
                self.term_input.addItem(name, term_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement trimestres impossible : {e}")
        finally:
            conn.close()

    def load_grid(self):
        class_id = self.class_input.currentData()
        term_id = self.term_input.currentData()

        if class_id is None or term_id is None:
            QMessageBox.warning(self, "Validation", "Classe et trimestre obligatoires.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT school_year_id
                FROM terms
                WHERE id = %s
                """,
                (term_id,)
            )
            year_row = cursor.fetchone()

            if not year_row:
                QMessageBox.warning(self, "Erreur", "Trimestre invalide.")
                return

            school_year_id = year_row[0]

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
            self.subjects = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.last_name || ' ' || s.first_name AS student_name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND s.is_active = TRUE
                ORDER BY s.last_name, s.first_name
                """,
                (class_id, school_year_id)
            )
            students = cursor.fetchall()

            cursor.execute(
                """
                SELECT student_id, subject_id, value
                FROM grades
                WHERE term_id = %s
                  AND student_id IN (
                      SELECT s.id
                      FROM enrollments e
                      JOIN students s ON s.id = e.student_id
                      WHERE e.class_id = %s
                        AND e.school_year_id = %s
                  )
                """,
                (term_id, class_id, school_year_id)
            )

            grades_map = {}
            for student_id, subject_id, value in cursor.fetchall():
                grades_map[(student_id, subject_id)] = value

            headers = ["ID", "Élève"] + [name for _, name in self.subjects]
            self.table.clear()
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setColumnHidden(0, True)
            self.table.setRowCount(len(students))

            for row_index, (student_id, student_name) in enumerate(students):
                self.table.setItem(row_index, 0, QTableWidgetItem(str(student_id)))
                self.table.setItem(row_index, 1, QTableWidgetItem(student_name))

                for col_index, (subject_id, subject_name) in enumerate(self.subjects, start=2):
                    value = grades_map.get((student_id, subject_id), "")
                    item = QTableWidgetItem("" if value == "" else str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row_index, col_index, item)

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement grille impossible : {e}")
        finally:
            conn.close()

    def save_grades(self):
        class_id = self.class_input.currentData()
        term_id = self.term_input.currentData()

        if class_id is None or term_id is None:
            QMessageBox.warning(self, "Validation", "Classe et trimestre obligatoires.")
            return

        if not self.subjects:
            QMessageBox.warning(self, "Validation", "Chargez d'abord la grille.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            for row in range(self.table.rowCount()):
                student_id_item = self.table.item(row, 0)
                if not student_id_item:
                    continue

                student_id = int(student_id_item.text())

                for col_index, (subject_id, subject_name) in enumerate(self.subjects, start=2):
                    item = self.table.item(row, col_index)
                    raw_value = item.text().strip() if item else ""

                    if raw_value == "":
                        continue

                    try:
                        value = float(raw_value)
                    except ValueError:
                        QMessageBox.warning(
                            self,
                            "Validation",
                            f"Note invalide pour {subject_name}, ligne {row + 1}."
                        )
                        conn.rollback()
                        return

                    if value < 0 or value > 10:
                        QMessageBox.warning(
                            self,
                            "Validation",
                            f"La note doit être entre 0 et 10 pour {subject_name}, ligne {row + 1}."
                        )
                        conn.rollback()
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
                                max_score = %s,
                                created_by = %s
                            WHERE id = %s
                            """,
                            (value, 10, self.current_user["id"], existing[0])
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO grades (
                                student_id, subject_id, term_id, value, max_score, created_by
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (student_id, subject_id, term_id, value, 10, self.current_user["id"])
                        )

            conn.commit()
            QMessageBox.information(self, "Succès", "Notes enregistrées avec succès.")

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()