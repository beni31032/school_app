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
    QLineEdit,
    QFrame,
    QFormLayout,
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.finance.add_salary_payment_dialog import AddSalaryPaymentDialog
from ui.finance.generate_salary_obligations_dialog import GenerateSalaryObligationsDialog
from ui.finance.generate_staff_salary_obligations_dialog import GenerateStaffSalaryObligationsDialog
from ui.finance.salary_details_dialog import SalaryDetailsDialog
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
        self.search_input = QLineEdit()
        self.establishment_filter = QComboBox()
        self.person_type_filter = QComboBox()
        self.status_filter = QComboBox()
        self.month_filter = QComboBox()
        self.year_filter = QComboBox()

        self.search_input.setPlaceholderText("Rechercher personne ou notes")

        self.person_type_filter.addItem("Tous", None)
        self.person_type_filter.addItem("Enseignants", "TEACHER")
        self.person_type_filter.addItem("Employés", "STAFF")

        self.status_filter.addItem("Tous", "ALL")
        self.status_filter.addItem("Impayés", "UNPAID")
        self.status_filter.addItem("Partiels", "PARTIAL")
        self.status_filter.addItem("Soldés", "PAID")

        self.month_filter.addItem("Tous", None)
        for month_number, label in MONTH_LABELS.items():
            self.month_filter.addItem(label, month_number)

        self.year_filter.addItem("Toutes", None)
        for year in range(2024, 2036):
            self.year_filter.addItem(str(year), year)

        filters.addWidget(QLabel("Recherche"))
        filters.addWidget(self.search_input)
        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Type"))
        filters.addWidget(self.person_type_filter)
        filters.addWidget(QLabel("Statut"))
        filters.addWidget(self.status_filter)
        filters.addWidget(QLabel("Mois"))
        filters.addWidget(self.month_filter)
        filters.addWidget(QLabel("Année"))
        filters.addWidget(self.year_filter)

        btns = QHBoxLayout()
        self.gen_teachers_btn = QPushButton("Générer obligations enseignants")
        self.gen_staff_btn = QPushButton("Générer obligations employés")
        self.add_payment_btn = QPushButton("Enregistrer paiement")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")
        btns.addWidget(self.gen_teachers_btn)
        btns.addWidget(self.gen_staff_btn)
        btns.addWidget(self.add_payment_btn)
        btns.addWidget(self.details_btn)
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

        self.details_card = QFrame()
        self.details_card.setObjectName("salaryDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_person = QLabel("-")
        self.d_type = QLabel("-")
        self.d_period = QLabel("-")
        self.d_due = QLabel("-")
        self.d_paid = QLabel("-")
        self.d_remaining = QLabel("-")
        self.d_status = QLabel("-")
        self.d_establishment = QLabel("-")
        self.d_notes = QLabel("-")
        self.d_notes.setWordWrap(True)

        details_layout.addRow("Personne :", self.d_person)
        details_layout.addRow("Type :", self.d_type)
        details_layout.addRow("Période :", self.d_period)
        details_layout.addRow("Montant dû :", self.d_due)
        details_layout.addRow("Montant payé :", self.d_paid)
        details_layout.addRow("Reste :", self.d_remaining)
        details_layout.addRow("Statut :", self.d_status)
        details_layout.addRow("Établissement :", self.d_establishment)
        details_layout.addRow("Notes :", self.d_notes)

        layout.addLayout(filters)
        layout.addLayout(btns)
        layout.addWidget(self.table)
        layout.addWidget(self.details_card)
        self.setLayout(layout)
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QLineEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QComboBox {
                background-color: #303030;
                color: #ffffff;
                border: 1px solid #525252;
                border-radius: 4px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }
            QFrame#salaryDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.gen_teachers_btn.clicked.connect(self.open_generate_teacher_obligations)
        self.gen_staff_btn.clicked.connect(self.open_generate_staff_obligations)
        self.add_payment_btn.clicked.connect(self.open_add_payment)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_rows)
        self.search_input.textChanged.connect(self.load_rows)
        self.establishment_filter.currentIndexChanged.connect(self.load_rows)
        self.person_type_filter.currentIndexChanged.connect(self.load_rows)
        self.status_filter.currentIndexChanged.connect(self.load_rows)
        self.month_filter.currentIndexChanged.connect(self.load_rows)
        self.year_filter.currentIndexChanged.connect(self.load_rows)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

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
        month_filter = self.month_filter.currentData()
        year_filter = self.year_filter.currentData()
        search = f"%{self.search_input.text().strip()}%"

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

            if month_filter is not None:
                where.append("so.period_month = %s")
                params.append(month_filter)

            if year_filter is not None:
                where.append("so.period_year = %s")
                params.append(year_filter)

            where.append(
                """(
                    CASE
                        WHEN so.person_type='TEACHER' THEN COALESCE(t.last_name || ' ' || t.first_name, '')
                        ELSE COALESCE(sm.last_name || ' ' || sm.first_name, '')
                    END ILIKE %s
                    OR COALESCE(so.notes, '') ILIKE %s
                )"""
            )
            params.extend([search, search])

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
                    item = QTableWidgetItem(txt)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, j, item)

            if filtered:
                self.table.selectRow(0)
            else:
                self.clear_details()
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

    def clear_details(self):
        self.d_person.setText("-")
        self.d_type.setText("-")
        self.d_period.setText("-")
        self.d_due.setText("-")
        self.d_paid.setText("-")
        self.d_remaining.setText("-")
        self.d_status.setText("-")
        self.d_establishment.setText("-")
        self.d_notes.setText("-")

    def load_selected_details(self):
        row = self.table.currentRow()
        if row == -1:
            self.clear_details()
            return

        obligation_id_item = self.table.item(row, 0)
        if not obligation_id_item:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cur = conn.cursor()
            sql = """
                SELECT
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
                    COALESCE(so.notes, '')
                FROM salary_obligations so
                LEFT JOIN teachers t ON t.id = so.teacher_id
                LEFT JOIN staff_members sm ON sm.id = so.staff_member_id
                LEFT JOIN salary_payments sp ON sp.obligation_id = so.id
                JOIN establishments e ON e.id = so.establishment_id
                WHERE so.id = %s
            """
            params = [int(obligation_id_item.text())]
            if not self.is_global_admin:
                sql += " AND so.establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            sql += """
                GROUP BY so.person_type, t.last_name, t.first_name, sm.last_name, sm.first_name,
                         so.period_month, so.period_year, so.amount_due, e.name, so.notes
            """
            cur.execute(sql, params)
            row_data = cur.fetchone()
            if not row_data:
                self.clear_details()
                return

            person_type, person_name, month, year, due, paid, establishment_name, notes = row_data
            remaining = float(due or 0) - float(paid or 0)
            if remaining <= 0.0001:
                status = "Soldé"
            elif float(paid or 0) <= 0.0001:
                status = "Impayé"
            else:
                status = "Partiel"

            self.d_person.setText(person_name or "-")
            self.d_type.setText("Enseignant" if person_type == "TEACHER" else "Employé")
            self.d_period.setText(f"{MONTH_LABELS.get(int(month), month)} {year}")
            self.d_due.setText(f"{float(due or 0):,.0f} FCFA")
            self.d_paid.setText(f"{float(paid or 0):,.0f} FCFA")
            self.d_remaining.setText(f"{remaining:,.0f} FCFA")
            self.d_status.setText(status)
            self.d_establishment.setText(establishment_name or "-")
            self.d_notes.setText(notes or "-")
        finally:
            conn.close()

    def open_details_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez une obligation")
            return

        obligation_id_item = self.table.item(row, 0)
        if not obligation_id_item:
            QMessageBox.warning(self, "Validation", "Obligation invalide")
            return

        dialog = SalaryDetailsDialog(
            obligation_id=int(obligation_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()
