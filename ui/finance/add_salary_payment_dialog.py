from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QDoubleSpinBox,
    QHBoxLayout,
)

from database.connection import get_connection
from utils.salary_service import ensure_salary_table
from utils.teacher_service import ensure_teacher_schema


class AddSalaryPaymentDialog(QDialog):
    def __init__(self, current_user, obligation_id=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.obligation_id = int(obligation_id) if obligation_id else None
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_salary_table()
        ensure_teacher_schema()

        self.setWindowTitle("Ajouter paiement salaire")
        self.setFixedWidth(520)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.establishment_input = QComboBox()
        self.person_type_input = QComboBox()
        self.person_type_input.addItem("Enseignant", "TEACHER")
        self.person_type_input.addItem("Employé", "STAFF")
        self.person_input = QComboBox()
        self.month_input = QComboBox()
        self.year_input = QComboBox()
        self.amount_input = QDoubleSpinBox(); self.amount_input.setRange(0, 999999999); self.amount_input.setDecimals(2)
        self.date_input = QDateEdit(); self.date_input.setCalendarPopup(True); self.date_input.setDate(QDate.currentDate()); self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.method_input = QLineEdit(); self.method_input.setPlaceholderText("Espèces / Virement / ...")
        self.reference_input = QLineEdit(); self.reference_input.setPlaceholderText("Référence optionnelle")
        self.notes_input = QTextEdit(); self.notes_input.setPlaceholderText("Notes optionnelles"); self.notes_input.setFixedHeight(80)

        for m in range(1, 13):
            self.month_input.addItem(str(m).zfill(2), m)
        current_year = QDate.currentDate().year()
        for y in range(current_year - 1, current_year + 4):
            self.year_input.addItem(str(y), y)
        self.month_input.setCurrentIndex(QDate.currentDate().month() - 1)
        self.year_input.setCurrentText(str(current_year))

        form.addRow("Établissement :", self.establishment_input)
        form.addRow("Type :", self.person_type_input)
        form.addRow("Personne :", self.person_input)
        form.addRow("Mois :", self.month_input)
        form.addRow("Année :", self.year_input)
        form.addRow("Montant payé :", self.amount_input)
        form.addRow("Date paiement :", self.date_input)
        form.addRow("Mode paiement :", self.method_input)
        form.addRow("Référence :", self.reference_input)
        form.addRow("Notes :", self.notes_input)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")
        actions = QHBoxLayout()
        actions.addWidget(self.save_btn)
        actions.addWidget(self.cancel_btn)

        layout.addLayout(form)
        layout.addLayout(actions)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel { color: #111827; font-weight: 600; }
            QLineEdit, QTextEdit, QDateEdit, QComboBox, QDoubleSpinBox {
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

        self.establishment_input.currentIndexChanged.connect(self.load_people)
        self.person_type_input.currentIndexChanged.connect(self.load_people)
        self.save_btn.clicked.connect(self.save_payment)
        self.cancel_btn.clicked.connect(self.reject)

        self.load_establishments()
        if self.obligation_id:
            self.prefill_from_obligation()

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
            self.load_people()
        finally:
            conn.close()

    def load_people(self):
        est_id = self.establishment_input.currentData()
        person_type = self.person_type_input.currentData()
        if est_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.person_input.clear()
            if person_type == "TEACHER":
                cur.execute(
                    "SELECT id, last_name || ' ' || first_name FROM teachers WHERE establishment_id=%s ORDER BY last_name, first_name",
                    (est_id,),
                )
            else:
                cur.execute(
                    "SELECT id, last_name || ' ' || first_name FROM staff_members WHERE establishment_id=%s ORDER BY last_name, first_name",
                    (est_id,),
                )
            for person_id, fullname in cur.fetchall():
                self.person_input.addItem(fullname, person_id)
        finally:
            conn.close()

    def prefill_from_obligation(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT establishment_id, person_type, person_id, period_month, period_year,
                       amount_due - COALESCE((
                           SELECT SUM(sp.amount) FROM salary_payments sp WHERE sp.obligation_id = so.id
                       ), 0) AS remaining
                FROM salary_obligations so
                WHERE id=%s
                """,
                (self.obligation_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            est_id, person_type, person_id, month, year, remaining = row

            self._select_combo_data(self.establishment_input, est_id)
            self._select_combo_data(self.person_type_input, person_type)
            self.load_people()
            self._select_combo_data(self.person_input, person_id)
            self._select_combo_data(self.month_input, month)
            self._select_combo_data(self.year_input, year)
            self.amount_input.setValue(max(0.0, float(remaining or 0)))
        finally:
            conn.close()

    def _select_combo_data(self, combo, data):
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    def save_payment(self):
        est_id = self.establishment_input.currentData()
        person_type = self.person_type_input.currentData()
        person_id = self.person_input.currentData()
        month = self.month_input.currentData()
        year = self.year_input.currentData()
        amount = float(self.amount_input.value())
        payment_date = self.date_input.date().toString("yyyy-MM-dd")
        method = self.method_input.text().strip() or None
        reference = self.reference_input.text().strip() or None
        notes = self.notes_input.toPlainText().strip() or None

        if not all([est_id, person_type, person_id, month, year]):
            QMessageBox.warning(self, "Validation", "Tous les champs obligatoires doivent être remplis")
            return
        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Montant invalide")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()
            obligation_id = self.obligation_id
            if not obligation_id:
                cur.execute(
                    """
                    SELECT id
                    FROM salary_obligations
                    WHERE establishment_id=%s AND person_type=%s AND person_id=%s
                      AND period_month=%s AND period_year=%s
                    """,
                    (est_id, person_type, person_id, month, year),
                )
                row = cur.fetchone()
                obligation_id = row[0] if row else None

            teacher_id = person_id if person_type == "TEACHER" else None
            staff_member_id = person_id if person_type == "STAFF" else None

            cur.execute(
                """
                INSERT INTO salary_payments (
                    establishment_id, teacher_id, staff_member_id, person_type, person_id,
                    period_month, period_year, amount, payment_date, payment_method,
                    reference, notes, obligation_id, created_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    est_id,
                    teacher_id,
                    staff_member_id,
                    person_type,
                    person_id,
                    month,
                    year,
                    amount,
                    payment_date,
                    method,
                    reference,
                    notes,
                    obligation_id,
                    self.current_user.get("id"),
                ),
            )
            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Paiement impossible : {e}")
        finally:
            conn.close()
