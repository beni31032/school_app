from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from database.connection import get_connection
from utils.table_style import setup_table


class CollegeGradesPage(QWidget):
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
            QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        # Header : forçage visuel
        self.table.horizontalHeader().setVisible(True)
        self.table.horizontalHeader().setMinimumHeight(38)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.horizontalHeader().setHighlightSections(False)

        # Style direct table + header
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                gridline-color: #d1d5db;
                color: #111827;
                font-size: 13px;
            }

            QTableWidget::item {
                padding: 4px;
            }

            QTableWidget::item:selected {
                background-color: #bfdbfe;
                color: #111827;
            }

            QHeaderView::section {
                background-color: #2563eb;
                color: white;
                border: 1px solid #1d4ed8;
                padding: 6px;
                font-weight: bold;
            }
        """)

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

    # =========================
    # CHARGEMENTS
    # =========================
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
                    WHERE cy.name = 'Collège'
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
                      AND cy.name = 'Collège'
                    ORDER BY c.name
                    """,
                    (self.current_user["establishment_id"],)
                )

            for class_id, label in cursor.fetchall():
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

            for term_id, name in cursor.fetchall():
                self.term_input.addItem(name, term_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement trimestres impossible : {e}")
        finally:
            conn.close()

    # =========================
    # CHARGER LA GRILLE
    # =========================
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
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Trimestre invalide.")
                return

            school_year_id = row[0]

            # Matières de la classe
            cursor.execute(
                """
                SELECT
                    cs.subject_id,
                    s.name,
                    COALESCE(cs.coefficient, 1)
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
                ORDER BY s.name
                """,
                (class_id,)
            )
            self.subjects = cursor.fetchall()

            # Élèves
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

            # Notes existantes
            cursor.execute(
                """
                SELECT
                    g.student_id,
                    g.subject_id,
                    g.grade_type,
                    g.value
                FROM grades g
                WHERE g.term_id = %s
                  AND g.grade_type IN ('classe', 'compo')
                  AND g.student_id IN (
                      SELECT e.student_id
                      FROM enrollments e
                      WHERE e.class_id = %s
                        AND e.school_year_id = %s
                  )
                """,
                (term_id, class_id, school_year_id)
            )

            grades_map = {}
            for student_id, subject_id, grade_type, value in cursor.fetchall():
                grades_map[(student_id, subject_id, grade_type)] = value

            headers = ["ID", "Élève"]
            for _, subject_name, _coefficient in self.subjects:
                short_name = subject_name[:12]
                headers.append(f"{short_name} C/20")
                headers.append(f"{short_name} P/20")

            self.table.clearContents()
            self.table.setRowCount(0)
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setColumnHidden(0, True)
            self.table.setRowCount(len(students))

            # Forcer le style des items d'en-tête
            for col, label in enumerate(headers):
                item = self.table.horizontalHeaderItem(col)
                if item is None:
                    item = QTableWidgetItem(label)
                    self.table.setHorizontalHeaderItem(col, item)

                item.setText(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QBrush(QColor("white")))
                item.setBackground(QBrush(QColor("#2563eb")))

            for row_index, (student_id, student_name) in enumerate(students):
                id_item = QTableWidgetItem(str(student_id))
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, 0, id_item)

                name_item = QTableWidgetItem(student_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, 1, name_item)

                col = 2
                for subject_id, _, _coefficient in self.subjects:
                    classe_val = grades_map.get((student_id, subject_id, "classe"), "")
                    compo_val = grades_map.get((student_id, subject_id, "compo"), "")

                    classe_item = QTableWidgetItem("" if classe_val == "" else str(classe_val))
                    classe_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row_index, col, classe_item)

                    compo_item = QTableWidgetItem("" if compo_val == "" else str(compo_val))
                    compo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row_index, col + 1, compo_item)

                    col += 2

            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

            for i in range(2, len(headers)):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

            self.table.resizeRowsToContents()
            for row in range(self.table.rowCount()):
                self.table.setRowHeight(row, 30)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement grille impossible : {e}")
        finally:
            conn.close()

    # =========================
    # SAUVEGARDE
    # =========================
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
                col = 2

                for subject_id, subject_name, _coefficient in self.subjects:
                    for grade_type, label in [("classe", "Classe"), ("compo", "Composition")]:
                        item = self.table.item(row, col)
                        raw_value = item.text().strip() if item else ""

                        if raw_value == "":
                            cursor.execute(
                                """
                                DELETE FROM grades
                                WHERE student_id = %s
                                  AND subject_id = %s
                                  AND term_id = %s
                                  AND grade_type = %s
                                """,
                                (student_id, subject_id, term_id, grade_type)
                            )
                            col += 1
                            continue

                        try:
                            value = float(raw_value.replace(",", "."))
                        except ValueError:
                            QMessageBox.warning(
                                self,
                                "Validation",
                                f"Note invalide ({label}) pour {subject_name}, ligne {row + 1}."
                            )
                            conn.rollback()
                            return

                        if value < 0 or value > 20:
                            QMessageBox.warning(
                                self,
                                "Validation",
                                f"La note ({label}) doit être entre 0 et 20 pour {subject_name}, ligne {row + 1}."
                            )
                            conn.rollback()
                            return

                        cursor.execute(
                            """
                            INSERT INTO grades (
                                student_id,
                                subject_id,
                                term_id,
                                grade_type,
                                value,
                                max_score,
                                created_by
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (student_id, subject_id, term_id, grade_type)
                            DO UPDATE SET
                                value = EXCLUDED.value,
                                max_score = EXCLUDED.max_score,
                                created_by = EXCLUDED.created_by
                            """,
                            (
                                student_id,
                                subject_id,
                                term_id,
                                grade_type,
                                value,
                                20,
                                self.current_user["id"]
                            )
                        )

                        col += 1

            conn.commit()
            QMessageBox.information(self, "Succès", "Notes collège enregistrées avec succès.")

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()
