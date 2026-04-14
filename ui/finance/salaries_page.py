from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QComboBox,
    QLabel,
)

from database.connection import get_connection
from ui.finance.add_salary_payment_dialog import AddSalaryPaymentDialog
from ui.finance.generate_salary_obligations_dialog import GenerateSalaryObligationsDialog
from ui.finance.generate_staff_salary_obligations_dialog import GenerateStaffSalaryObligationsDialog
from utils.salary_service import ensure_salary_table
from utils.table_style import setup_table


MONTH_LABELS = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}


class SalariesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_salary_table()

        layout = QVBoxLayout()

        filters = QHBoxLayout()
        self.establishment_filter = QComboBox()
        self.person_type_filter = QComboBox()
        self.status_filter = QComboBox()

        self.person_type_filter.addItem("Tous", None)
        self.person_type_filter.addItem("Enseignants", "TEACHER")
        self.person_type_filter.addItem("Employés", "STAFF")

        self.status_filter.addItem("Tous", "ALL")
        self.status_filter.addItem("Impayés", "UNPAID")
        self.status_filter.addItem("Partiels", "PARTIAL")
        self.status_filter.addItem("Soldés", "PAID")

        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Type"))
        filters.addWidget(self.person_type_filter)
        filters.addWidget(QLabel("Statut"))
        filters.addWidget(self.status_filter)

        btns = QHBoxLayout()
        self.gen_teachers_btn = QPushButton("Générer obligations enseignants")
        self.gen_staff_btn = QPushButton("Générer obligations employés")
        self.add_payment_btn = QPushButton("Enregistrer paiement")
        self.refresh_btn = QPushButton("Actualiser")
        btns.addWidget(self.gen_teachers_btn)
        btns.addWidget(self.gen_staff_btn)
        btns.addWidget(self.add_payment_btn)
        btns.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Type",
                "Personne",
                "Période",
                "Montant dû",
                "Montant payé",
                "Reste",
                "Statut",
                "Établissement",
                "Créé le",
                "Notes",
            ]
        )
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        layout.addLayout(filters)
        layout.addLayout(btns)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.setStyleSheet("QLabel { color: #111827; font-weight: 600; }")

        self.gen_teachers_btn.clicked.connect(self.open_generate_teacher_obligations)
        self.gen_staff_btn.clicked.connect(self.open_generate_staff_obligations)
        self.add_payment_btn.clicked.connect(self.open_add_payment)
        self.refresh_btn.clicked.connect(self.load_rows)
        self.establishment_filter.currentIndexChanged.connect(self.load_rows)
        self.person_type_filter.currentIndexChanged.connect(self.load_rows)
        self.status_filter.currentIndexChanged.connect(self.load_rows)

        self.load_establishment_filter()
        self.load_rows()

    def load_establishment_filter(self):
        self.establishment_filter.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cur.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cur.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                est_id = self.current_user["establishment_id"]
                cur.execute("SELECT id, name FROM establishments WHERE id = %s", (est_id,))
                row = cur.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def load_rows(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        est_id = self.establishment_filter.currentData()
        person_type = self.person_type_filter.currentData()
        status_mode = self.status_filter.currentData()

        try:
            cur = conn.cursor()
            where = []
            params = []

            if self.is_global_admin:
                if est_id is not None:
                    where.append("so.establishment_id = %s")
                    params.append(est_id)
            else:
                where.append("so.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if person_type is not None:
                where.append("so.person_type = %s")
                params.append(person_type)

            where_sql = " WHERE " + " AND ".join(where) if where else ""

            cur.execute(
                f"""
                SELECT
                    so.id,
                    so.person_type,
                    CASE
                        WHEN so.person_type='TEACHER' THEN COALESCE(t.last_name || ' ' || t.first_name, '-')
                        ELSE COALESCE(sm.last_name || ' ' || sm.first_name, '-')
                    END AS person_name,
                    so.period_month,
                    so.period_year,
                    so.amount_due,
                    COALESCE(SUM(sp.amount), 0) AS paid_total,
                    e.name,
                    so.created_at,
                    COALESCE(so.notes, '')
                FROM salary_obligations so
                LEFT JOIN teachers t ON t.id = so.teacher_id
                LEFT JOIN staff_members sm ON sm.id = so.staff_member_id
                LEFT JOIN salary_payments sp ON sp.obligation_id = so.id
                JOIN establishments e ON e.id = so.establishment_id
                {where_sql}
                GROUP BY so.id, so.person_type, t.last_name, t.first_name,
                         sm.last_name, sm.first_name, so.period_month, so.period_year,
                         so.amount_due, e.name, so.created_at, so.notes
                ORDER BY so.period_year DESC, so.period_month DESC, person_name
                """,
                params,
            )
            rows = cur.fetchall()

            filtered = []
            for row in rows:
                (
                    obligation_id,
                    ptype,
                    person_name,
                    month,
                    year,
                    due,
                    paid,
                    est_name,
                    created_at,
                    notes,
                ) = row
                due = float(due or 0)
                paid = float(paid or 0)
                remaining = due - paid

                if remaining <= 0.0001:
                    status = "Soldé"
                    status_key = "PAID"
                elif paid <= 0.0001:
                    status = "Impayé"
                    status_key = "UNPAID"
                else:
                    status = "Partiel"
                    status_key = "PARTIAL"

                if status_mode != "ALL" and status_mode != status_key:
                    continue

                filtered.append(
                    (
                        obligation_id,
                        "Enseignant" if ptype == "TEACHER" else "Employé",
                        person_name,
                        f"{MONTH_LABELS.get(int(month), month)} {year}",
                        due,
                        paid,
                        remaining,
                        status,
                        est_name,
                        created_at,
                        notes,
                    )
                )

            self.table.setRowCount(len(filtered))
            for i, row in enumerate(filtered):
                for j, val in enumerate(row):
                    if j in (4, 5, 6):
                        txt = f"{float(val):,.0f}"
                    else:
                        txt = "" if val is None else str(val)
                    self.table.setItem(i, j, QTableWidgetItem(txt))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_generate_teacher_obligations(self):
        dialog = GenerateSalaryObligationsDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_rows()

    def open_generate_staff_obligations(self):
        dialog = GenerateStaffSalaryObligationsDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_rows()

    def open_add_payment(self):
        row = self.table.currentRow()
        obligation_id = None
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                obligation_id = item.text()

        dialog = AddSalaryPaymentDialog(current_user=self.current_user, obligation_id=obligation_id, parent=self)
        if dialog.exec():
            self.load_rows()
