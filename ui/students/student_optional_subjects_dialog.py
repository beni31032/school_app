from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QFrame,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)

from database.connection import get_connection
from utils.subject_service import ensure_subject_schema
from utils.table_style import setup_table


def _readonly_item(value: str) -> QTableWidgetItem:
    item = QTableWidgetItem(value)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class StudentOptionalSubjectsDialog(QDialog):
    def __init__(self, student_id: int, school_year_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.student_id = int(student_id)
        self.school_year_id = int(school_year_id)
        self.current_user = current_user
        self.is_global_admin = current_user.get("role") == "ADMIN_GLOBAL"
        ensure_subject_schema()

        self.setWindowTitle("Options matières élève")
        self.resize(760, 520)

        root = QVBoxLayout()

        title = QLabel("Options matières élève")
        title.setObjectName("dialogTitle")

        self.info_card = QFrame()
        self.info_card.setObjectName("infoCard")
        info_form = QFormLayout(self.info_card)
        info_form.setContentsMargins(14, 14, 14, 14)
        info_form.setVerticalSpacing(8)

        self.v_student = QLabel("-")
        self.v_class = QLabel("-")
        self.v_level = QLabel("-")
        self.v_mode = QLabel("-")

        info_form.addRow("Élève :", self.v_student)
        info_form.addRow("Classe :", self.v_class)
        info_form.addRow("Niveau :", self.v_level)
        info_form.addRow("Gestion des facultatives :", self.v_mode)

        self.help_label = QLabel("")
        self.help_label.setWordWrap(True)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Matière", "Coefficient", "Choisie"])
        self.table.setColumnHidden(0, True)
        setup_table(self.table, stretch=True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.save_btn)
        actions.addWidget(self.cancel_btn)

        root.addWidget(title)
        root.addWidget(self.info_card)
        root.addWidget(self.help_label)
        root.addWidget(self.table)
        root.addLayout(actions)
        self.setLayout(root)

        self.setStyleSheet(
            """
            QDialog { background-color: #f1f5f9; }
            QLabel#dialogTitle {
                color: #111827;
                font-size: 22px;
                font-weight: 800;
            }
            QFrame#infoCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            QLabel {
                color: #111827;
                font-weight: 600;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 8px;
                font-weight: 700;
                padding: 8px 14px;
            }
            QPushButton:first-of-type {
                background-color: #2563eb;
                color: white;
                border: none;
            }
            QPushButton:last-of-type {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
            }
            """
        )

        self.save_btn.clicked.connect(self.save_choices)
        self.cancel_btn.clicked.connect(self.reject)

        self.load_data()

    def _level_is_student_based(self, level_name: str) -> bool:
        normalized = (level_name or "").strip().lower()
        aliases = ("3eme", "3ème", "seconde", "2nde", "premiere", "première", "1ere", "1ère", "terminale", "tle")
        return any(alias in normalized for alias in aliases)

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            self.reject()
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    s.first_name,
                    s.last_name,
                    c.id,
                    c.name,
                    COALESCE(c.level, '')
                FROM students s
                JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = %s
                JOIN classes c ON c.id = e.class_id
                WHERE s.id = %s
            """
            params = [self.school_year_id, self.student_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))
            cursor.execute(sql, params)
            student_row = cursor.fetchone()
            if not student_row:
                QMessageBox.warning(self, "Validation", "Élève introuvable pour cette année scolaire.")
                self.reject()
                return

            first_name, last_name, class_id, class_name, level_name = student_row
            self.class_id = int(class_id)
            self.v_student.setText(f"{last_name} {first_name}".strip() or "-")
            self.v_class.setText(class_name or "-")
            self.v_level.setText(level_name or "-")

            student_based = self._level_is_student_based(level_name)
            if student_based:
                self.v_mode.setText("Par élève")
                self.help_label.setText(
                    "Sélectionne ici les matières facultatives effectivement choisies par cet élève pour cette année."
                )
                self.table.setEnabled(True)
                self.save_btn.setEnabled(True)
            else:
                self.v_mode.setText("Par classe")
                self.help_label.setText(
                    "Pour ce niveau, les matières facultatives s'appliquent à toute la classe. Aucun choix individuel n'est nécessaire."
                )
                self.table.setEnabled(False)
                self.save_btn.setEnabled(False)

            cursor.execute(
                """
                SELECT
                    cs.id,
                    s.name,
                    COALESCE(cs.coefficient, 1),
                    EXISTS (
                        SELECT 1
                        FROM student_optional_subjects sos
                        WHERE sos.student_id = %s
                          AND sos.class_subject_id = cs.id
                          AND sos.school_year_id = %s
                    ) AS is_selected
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
                  AND COALESCE(cs.subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'
                ORDER BY s.name
                """,
                (self.student_id, self.school_year_id, self.class_id),
            )
            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, (class_subject_id, subject_name, coefficient, is_selected) in enumerate(rows):
                self.table.setItem(row_index, 0, _readonly_item(str(class_subject_id)))
                self.table.setItem(row_index, 1, _readonly_item(subject_name or "-"))
                self.table.setItem(row_index, 2, _readonly_item(str(coefficient or 1)))
                selected_item = QTableWidgetItem("")
                selected_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsSelectable
                )
                selected_item.setCheckState(
                    Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked
                )
                self.table.setItem(row_index, 3, selected_item)

            if not rows:
                self.help_label.setText("Aucune matière facultative n'est encore définie pour cette classe.")
                self.save_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def save_choices(self):
        if not self.table.isEnabled():
            self.accept()
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM student_optional_subjects
                WHERE student_id = %s
                  AND school_year_id = %s
                  AND class_subject_id IN (
                      SELECT id
                      FROM class_subjects
                      WHERE class_id = %s
                        AND COALESCE(subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'
                  )
                """,
                (self.student_id, self.school_year_id, self.class_id),
            )

            created = 0
            for row in range(self.table.rowCount()):
                selected_item = self.table.item(row, 3)
                id_item = self.table.item(row, 0)
                if not selected_item or not id_item:
                    continue
                if selected_item.checkState() != Qt.CheckState.Checked:
                    continue
                cursor.execute(
                    """
                    INSERT INTO student_optional_subjects (student_id, class_subject_id, school_year_id)
                    VALUES (%s, %s, %s)
                    """,
                    (self.student_id, int(id_item.text()), self.school_year_id),
                )
                created += 1

            conn.commit()
            QMessageBox.information(
                self,
                "Succès",
                f"Options matières enregistrées avec succès.\nChoix enregistrés : {created}",
            )
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()
