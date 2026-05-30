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
from utils.salary_service import ensure_salary_table, get_school_year_months


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class GenerateStaffSalaryObligationsDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_salary_table()

        self.setWindowTitle("Générer les salaires employés sur l'année scolaire")
        self.setFixedWidth(520)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.establishment_input = QComboBox()
        self.staff_input = QComboBox()
        self.school_year_input = QComboBox()
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 999999999)
        self.amount_input.setDecimals(2)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes optionnelles")
        self.notes_input.setFixedHeight(80)

        form.addRow("Établissement :", self.establishment_input)
        form.addRow("Employé :", self.staff_input)
        form.addRow("Année scolaire :", self.school_year_input)
        form.addRow("Montant (par employé / fallback):", self.amount_input)
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
            QComboBox QAbstractItemView {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                selection-background-color: #2563eb;
                selection-color: white;
                outline: none;
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

        self.generate_btn.clicked.connect(self.generate_obligations)
        self.cancel_btn.clicked.connect(self.reject)
        self.establishment_input.currentIndexChanged.connect(self.load_staff)

        self.load_establishments()
        self.load_school_years()

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

            self.load_staff()
        finally:
            conn.close()

    def load_staff(self):
        est_id = self.establishment_input.currentData()
        if est_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.staff_input.clear()
            self.staff_input.addItem("Tous les employés", None)
            cur.execute(
                """
                SELECT id, last_name || ' ' || first_name
                FROM staff_members
                WHERE establishment_id=%s AND COALESCE(is_active, TRUE) = TRUE
                ORDER BY last_name, first_name
                """,
                (est_id,),
            )
            for staff_id, fullname in cur.fetchall():
                self.staff_input.addItem(fullname, staff_id)
        finally:
            conn.close()

    def load_school_years(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.school_year_input.clear()
            cur.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for school_year_id, name in cur.fetchall():
                self.school_year_input.addItem(name, school_year_id)
        finally:
            conn.close()

    def generate_obligations(self):
        est_id = self.establishment_input.currentData()
        staff_id = self.staff_input.currentData()
        school_year_id = self.school_year_input.currentData()
        amount = float(self.amount_input.value())
        notes = self.notes_input.toPlainText().strip() or None

        if not est_id:
            QMessageBox.warning(self, "Validation", "Établissement obligatoire")
            return
        if not school_year_id:
            QMessageBox.warning(self, "Validation", "Année scolaire obligatoire")
            return
        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Montant obligatoire")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()
            school_year_months = get_school_year_months(cur, int(school_year_id))
            if not school_year_months:
                QMessageBox.warning(self, "Validation", "Les dates de l'année scolaire sont invalides.")
                return

            if staff_id is None:
                cur.execute(
                    """
                    SELECT id
                    FROM staff_members
                    WHERE establishment_id=%s AND COALESCE(is_active, TRUE) = TRUE
                    ORDER BY last_name, first_name
                    """,
                    (est_id,),
                )
                staff_ids = [r[0] for r in cur.fetchall()]
            else:
                staff_ids = [staff_id]

            generated = 0
            for s_id in staff_ids:
                for month, year in school_year_months:
                    cur.execute(
                        """
                        SELECT id
                        FROM salary_obligations
                        WHERE establishment_id = %s
                          AND person_type = 'STAFF'
                          AND person_id = %s
                          AND period_month = %s
                          AND period_year = %s
                        """,
                        (est_id, s_id, month, year),
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            """
                            UPDATE salary_obligations
                            SET staff_member_id = %s,
                                amount_due = %s,
                                notes = %s,
                                created_by = %s
                            WHERE id = %s
                            """,
                            (s_id, amount, notes, self.current_user.get("id"), existing[0]),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO salary_obligations (
                                establishment_id, staff_member_id, person_type, person_id,
                                period_month, period_year, amount_due, notes, created_by
                            ) VALUES (%s, %s, 'STAFF', %s, %s, %s, %s, %s, %s)
                            """,
                            (est_id, s_id, s_id, month, year, amount, notes, self.current_user.get("id")),
                        )
                    generated += 1

            conn.commit()
            QMessageBox.information(
                self,
                "Succès",
                f"Obligations employés générées pour {self.school_year_input.currentText()} : {generated}",
            )
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Génération impossible : {e}")
