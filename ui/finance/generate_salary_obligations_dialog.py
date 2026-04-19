from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QDoubleSpinBox,
    QHBoxLayout,
)

from database.connection import get_connection
from utils.salary_service import ensure_salary_table


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class GenerateSalaryObligationsDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_salary_table()

        self.setWindowTitle("Générer obligations de salaires")
        self.setFixedWidth(600)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.establishment_input = QComboBox()
        self.teacher_input = QComboBox()
        self.month_input = QComboBox()
        self.year_input = QComboBox()
        self.mode_input = QComboBox()

        self.amount_unique_input = QDoubleSpinBox()
        self.amount_unique_input.setRange(0, 999999999)
        self.amount_unique_input.setDecimals(2)

        self.amount_maternelle_input = QDoubleSpinBox(); self.amount_maternelle_input.setRange(0, 999999999); self.amount_maternelle_input.setDecimals(2)
        self.amount_primaire_input = QDoubleSpinBox(); self.amount_primaire_input.setRange(0, 999999999); self.amount_primaire_input.setDecimals(2)
        self.amount_college_input = QDoubleSpinBox(); self.amount_college_input.setRange(0, 999999999); self.amount_college_input.setDecimals(2)
        self.amount_lycee_input = QDoubleSpinBox(); self.amount_lycee_input.setRange(0, 999999999); self.amount_lycee_input.setDecimals(2)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes optionnelles")
        self.notes_input.setFixedHeight(80)

        today = QDate.currentDate()
        for idx, label in enumerate(MONTHS, start=1):
            self.month_input.addItem(label, idx)
        self.month_input.setCurrentIndex(today.month() - 1)
        for y in range(today.year() - 1, today.year() + 4):
            self.year_input.addItem(str(y), y)
        self.year_input.setCurrentText(str(today.year()))
        self.mode_input.addItem("Enseignants: montant unique", "UNIQUE")
        self.mode_input.addItem("Enseignants: par niveau", "BY_LEVEL")

        form.addRow("Établissement :", self.establishment_input)
        form.addRow("Enseignant :", self.teacher_input)
        form.addRow("Mode enseignants :", self.mode_input)
        form.addRow("Mois :", self.month_input)
        form.addRow("Année :", self.year_input)
        form.addRow("Montant enseignants (unique/fallback) :", self.amount_unique_input)
        form.addRow("Montant enseignants Maternelle :", self.amount_maternelle_input)
        form.addRow("Montant enseignants Primaire :", self.amount_primaire_input)
        form.addRow("Montant enseignants Collège :", self.amount_college_input)
        form.addRow("Montant enseignants Lycée :", self.amount_lycee_input)
        form.addRow("Notes :", self.notes_input)

        self.generate_btn = QPushButton("Générer")
        self.cancel_btn = QPushButton("Annuler")
        actions = QHBoxLayout()
        actions.addWidget(self.generate_btn)
        actions.addWidget(self.cancel_btn)

        layout.addLayout(form)
        layout.addLayout(actions)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel { color: #111827; font-weight: 600; }
            QComboBox, QTextEdit, QDoubleSpinBox {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 8px;
                font-weight: 700;
                padding: 6px 12px;
            }
            QPushButton:first-of-type {
                background-color: #2563eb;
                color: white;
                border: none;
            }
            QPushButton:first-of-type:hover { background-color: #1d4ed8; }
            QPushButton:last-of-type {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
            }
            """
        )

        self.mode_input.currentIndexChanged.connect(self.update_amount_mode)

        self.generate_btn.clicked.connect(self.generate_obligations)
        self.cancel_btn.clicked.connect(self.reject)
        self.establishment_input.currentIndexChanged.connect(self.load_teachers)

        self.load_establishments()
        self.update_amount_mode()

    def load_establishments(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.establishment_input.clear()
            if self.is_global_admin:
                cur.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cur.fetchall():
                    self.establishment_input.addItem(name, est_id)
            else:
                est_id = self.current_user["establishment_id"]
                cur.execute("SELECT id, name FROM establishments WHERE id=%s", (est_id,))
                row = cur.fetchone()
                if row:
                    self.establishment_input.addItem(row[1], row[0])
                self.establishment_input.setEnabled(False)

            self.load_teachers()
        finally:
            conn.close()

    def load_teachers(self):
        est_id = self.establishment_input.currentData()
        if est_id is None:
            return

        conn = get_connection()
        if not conn:
            return

        try:
            cur = conn.cursor()
            self.teacher_input.clear()
            self.teacher_input.addItem("Tous les enseignants", None)
            cur.execute(
                """
                SELECT id, last_name || ' ' || first_name
                FROM teachers
                WHERE establishment_id=%s
                ORDER BY last_name, first_name
                """,
                (est_id,),
            )
            for teacher_id, fullname in cur.fetchall():
                self.teacher_input.addItem(fullname, teacher_id)
        finally:
            conn.close()

    def _teaching_level_for_teacher(self, cursor, teacher_id):
        cursor.execute(
            """
            SELECT COALESCE(cy.name, '')
            FROM teacher_assignments ta
            JOIN classes c ON c.id = ta.class_id
            LEFT JOIN cycles cy ON cy.id = c.cycle_id
            WHERE ta.teacher_id = %s
            GROUP BY COALESCE(cy.name, '')
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """,
            (teacher_id,),
        )
        row = cursor.fetchone()
        return (row[0] or "").strip().lower() if row else ""

    def _amount_for_level(self, level: str) -> float:
        if self.mode_input.currentData() == "UNIQUE":
            return float(self.amount_unique_input.value())
        mapping = {
            "maternelle": float(self.amount_maternelle_input.value()),
            "primaire": float(self.amount_primaire_input.value()),
            "collège": float(self.amount_college_input.value()),
            "lycée": float(self.amount_lycee_input.value()),
            "college": float(self.amount_college_input.value()),
            "lycee": float(self.amount_lycee_input.value()),
        }
        level_amount = mapping.get(level, 0.0)
        return level_amount if level_amount > 0 else float(self.amount_unique_input.value())

    def update_amount_mode(self):
        by_level = self.mode_input.currentData() == "BY_LEVEL"
        self.amount_maternelle_input.setEnabled(by_level)
        self.amount_primaire_input.setEnabled(by_level)
        self.amount_college_input.setEnabled(by_level)
        self.amount_lycee_input.setEnabled(by_level)

    def generate_obligations(self):
        est_id = self.establishment_input.currentData()
        teacher_id = self.teacher_input.currentData()
        month = self.month_input.currentData()
        year = self.year_input.currentData()
        notes = self.notes_input.toPlainText().strip() or None

        if not est_id:
            QMessageBox.warning(self, "Validation", "Établissement obligatoire")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()
            if teacher_id is None:
                cur.execute(
                    """
                    SELECT id
                    FROM teachers
                    WHERE establishment_id=%s
                    ORDER BY last_name, first_name
                    """,
                    (est_id,),
                )
                teacher_ids = [r[0] for r in cur.fetchall()]
            else:
                teacher_ids = [teacher_id]

            inserted = 0
            for t_id in teacher_ids:
                level = self._teaching_level_for_teacher(cur, t_id)
                amount = self._amount_for_level(level)
                if amount <= 0:
                    continue

                cur.execute(
                    """
                    INSERT INTO salary_obligations (
                        establishment_id, teacher_id, person_type, person_id,
                        period_month, period_year, amount_due, notes, created_by
                    ) VALUES (%s, %s, 'TEACHER', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (establishment_id, person_type, person_id, period_month, period_year)
                    DO UPDATE SET amount_due = EXCLUDED.amount_due,
                                  notes = EXCLUDED.notes,
                                  created_by = EXCLUDED.created_by
                    """,
                    (est_id, t_id, t_id, month, year, amount, notes, self.current_user.get("id")),
                )
                inserted += 1

            conn.commit()
            QMessageBox.information(self, "Succès", f"Obligations enseignants générées: {inserted}")
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Génération impossible : {e}")
