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
)

from database.connection import get_connection
from utils.salary_service import ensure_salary_table


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

        self.setWindowTitle("Générer obligations salaires employés")
        self.setFixedWidth(520)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.establishment_input = QComboBox()
        self.staff_input = QComboBox()
        self.month_input = QComboBox()
        self.year_input = QComboBox()
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 999999999)
        self.amount_input.setDecimals(2)
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

        form.addRow("Établissement :", self.establishment_input)
        form.addRow("Employé :", self.staff_input)
        form.addRow("Mois :", self.month_input)
        form.addRow("Année :", self.year_input)
        form.addRow("Montant (par employé / fallback):", self.amount_input)
        form.addRow("Notes :", self.notes_input)

        self.generate_btn = QPushButton("Générer")
        self.cancel_btn = QPushButton("Annuler")

        layout.addLayout(form)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)

        self.generate_btn.clicked.connect(self.generate_obligations)
        self.cancel_btn.clicked.connect(self.reject)
        self.establishment_input.currentIndexChanged.connect(self.load_staff)

        self.load_establishments()

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

    def generate_obligations(self):
        est_id = self.establishment_input.currentData()
        staff_id = self.staff_input.currentData()
        month = self.month_input.currentData()
        year = self.year_input.currentData()
        amount = float(self.amount_input.value())
        notes = self.notes_input.toPlainText().strip() or None

        if not est_id:
            QMessageBox.warning(self, "Validation", "Établissement obligatoire")
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

            inserted = 0
            for s_id in staff_ids:
                cur.execute(
                    """
                    INSERT INTO salary_obligations (
                        establishment_id, staff_member_id, person_type, person_id,
                        period_month, period_year, amount_due, notes, created_by
                    ) VALUES (%s, %s, 'STAFF', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (establishment_id, person_type, person_id, period_month, period_year)
                    DO UPDATE SET amount_due = EXCLUDED.amount_due,
                                  notes = EXCLUDED.notes,
                                  created_by = EXCLUDED.created_by
                    """,
                    (est_id, s_id, s_id, month, year, amount, notes, self.current_user.get("id")),
                )
                inserted += 1

            conn.commit()
            QMessageBox.information(self, "Succès", f"Obligations employés générées: {inserted}")
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Génération impossible : {e}")
