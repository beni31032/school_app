# utils/primary_grades_page.py


from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QHBoxLayout, QLabel, QFrame
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
        self.buttons_layout = QHBoxLayout()

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

        self.summary_card = QFrame()
        self.summary_card.setObjectName("gradesSummaryCard")
        summary_layout = QFormLayout(self.summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setVerticalSpacing(6)
        self.info_class = QLabel("-")
        self.info_term = QLabel("-")
        self.info_students = QLabel("0")
        self.info_subjects = QLabel("0")
        self.info_scale = QLabel("/10")
        summary_layout.addRow("Classe :", self.info_class)
        summary_layout.addRow("Trimestre :", self.info_term)
        summary_layout.addRow("Élèves :", self.info_students)
        summary_layout.addRow("Matières :", self.info_subjects)
        summary_layout.addRow("Barème :", self.info_scale)

        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Trimestre :", self.term_input)

        self.layout.addLayout(self.form_layout)
        self.buttons_layout.addWidget(self.load_btn)
        self.buttons_layout.addWidget(self.save_btn)
        self.buttons_layout.addStretch()
        self.layout.addLayout(self.buttons_layout)
        self.layout.addWidget(self.summary_card)
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#gradesSummaryCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

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
                id_item = QTableWidgetItem(str(student_id))
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, 0, id_item)

                name_item = QTableWidgetItem(student_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, 1, name_item)

                for col_index, (subject_id, subject_name) in enumerate(self.subjects, start=2):
                    value = grades_map.get((student_id, subject_id), "")
                    item = QTableWidgetItem("" if value == "" else str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row_index, col_index, item)

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.update_summary(len(students))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement grille impossible : {e}")
        finally:
            conn.close()

    def update_summary(self, student_count: int = 0):
        self.info_class.setText(self.class_input.currentText() or "-")
        self.info_term.setText(self.term_input.currentText() or "-")
        self.info_students.setText(str(student_count))
        self.info_subjects.setText(str(len(self.subjects)))
        self.info_scale.setText("/10")

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
                        cursor.execute(
                            """
                            DELETE FROM grades
                            WHERE student_id = %s
                              AND subject_id = %s
                              AND term_id = %s
                            """,
                            (student_id, subject_id, term_id)
                        )
                        continue

                    try:
                        value = float(raw_value.replace(",", "."))
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
