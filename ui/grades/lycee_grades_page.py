from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QHBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from database.connection import get_connection
from utils.subject_service import ensure_subject_schema
from utils.table_style import setup_table


class LyceeGradesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.subjects = []
        self.student_subject_access = {}
        ensure_subject_schema()

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

        self.summary_card = QFrame()
        self.summary_card.setObjectName("gradesSummaryCard")
        summary_layout = QFormLayout(self.summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setVerticalSpacing(6)
        self.info_class = QLabel("-")
        self.info_term = QLabel("-")
        self.info_students = QLabel("0")
        self.info_subjects = QLabel("0")
        self.info_scale = QLabel("/20")
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
        self.setStyleSheet(self.styleSheet() + """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#gradesSummaryCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
        """)

        self.load_btn.clicked.connect(self.load_grid)
        self.save_btn.clicked.connect(self.save_grades)

        self.load_classes()
        self.load_terms()

    def _level_is_student_based(self, level_name: str) -> bool:
        normalized = (level_name or "").strip().lower()
        aliases = ("3eme", "3ème", "seconde", "2nde", "premiere", "première", "1ere", "1ère", "terminale", "tle")
        return any(alias in normalized for alias in aliases)

    def _make_grade_item(self, value, enabled: bool) -> QTableWidgetItem:
        text = "" if value == "" else str(value)
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if enabled:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QBrush(QColor("white")))
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setText("")
            item.setBackground(QBrush(QColor("#e5e7eb")))
            item.setToolTip("Matière facultative non choisie par cet élève.")
        return item

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
                    WHERE cy.name = 'Lycée'
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
                      AND cy.name = 'Lycée'
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

            cursor.execute(
                """
                SELECT COALESCE(level, '')
                FROM classes
                WHERE id = %s
                """,
                (class_id,),
            )
            class_level_row = cursor.fetchone()
            class_level = class_level_row[0] if class_level_row else ""
            student_based_optional = self._level_is_student_based(class_level)

            # Matières de la classe
            cursor.execute(
                """
                SELECT
                    cs.subject_id,
                    s.name,
                    COALESCE(cs.coefficient, 1),
                    COALESCE(cs.subject_type, 'OBLIGATOIRE')
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

            optional_subject_choices = set()
            if student_based_optional:
                cursor.execute(
                    """
                    SELECT sos.student_id, cs.subject_id
                    FROM student_optional_subjects sos
                    JOIN class_subjects cs ON cs.id = sos.class_subject_id
                    WHERE sos.school_year_id = %s
                      AND cs.class_id = %s
                    """,
                    (school_year_id, class_id),
                )
                optional_subject_choices = {(student_id, subject_id) for student_id, subject_id in cursor.fetchall()}

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

            self.student_subject_access = {}
            for student_id, _student_name in students:
                for subject_id, _subject_name, _coefficient, subject_type in self.subjects:
                    allowed = True
                    if subject_type == "FACULTATIVE" and student_based_optional:
                        allowed = (student_id, subject_id) in optional_subject_choices
                    self.student_subject_access[(student_id, subject_id)] = allowed

            headers = ["ID", "Élève"]
            for _, subject_name, _coefficient, subject_type in self.subjects:
                short_name = subject_name[:12]
                suffix = " (F)" if subject_type == "FACULTATIVE" else ""
                headers.append(f"{short_name}{suffix} C/20")
                headers.append(f"{short_name}{suffix} P/20")

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
                for subject_id, _, _coefficient, _subject_type in self.subjects:
                    classe_val = grades_map.get((student_id, subject_id, "classe"), "")
                    compo_val = grades_map.get((student_id, subject_id, "compo"), "")

                    enabled = self.student_subject_access.get((student_id, subject_id), True)
                    classe_item = self._make_grade_item(classe_val, enabled)
                    self.table.setItem(row_index, col, classe_item)
                    compo_item = self._make_grade_item(compo_val, enabled)
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
        self.info_scale.setText("/20")

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

                for subject_id, subject_name, _coefficient, _subject_type in self.subjects:
                    if not self.student_subject_access.get((student_id, subject_id), True):
                        for grade_type in ("classe", "compo"):
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
                        col += 2
                        continue
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
