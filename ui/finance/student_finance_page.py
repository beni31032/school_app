from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView, QHBoxLayout, QComboBox, QPushButton, QFrame
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.finance.student_finance_details_dialog import StudentFinanceDetailsDialog
from utils.table_style import setup_table


class StudentFinancePage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.current_school_year_id = None
        self.selected_student_id = None
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        layout = QVBoxLayout()
        form = QFormLayout()
        filters_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un élève par nom, prénom ou matricule")
        self.establishment_filter = QComboBox()
        self.class_filter = QComboBox()
        self.details_btn = QPushButton("Voir fiche complète")

        form.addRow("Recherche élève :", self.search_input)
        layout.addLayout(form)

        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Classe"))
        filters_layout.addWidget(self.class_filter)
        layout.addLayout(filters_layout)

        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.students_table = QTableWidget()
        self.students_table.setColumnCount(3)
        self.students_table.setHorizontalHeaderLabels(["ID", "Élève", "Classe"])
        self.students_table.setColumnHidden(0, True)
        self.students_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.students_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(QLabel("Élèves"))
        layout.addWidget(self.students_table)

        self.details_card = QFrame()
        self.details_card.setObjectName("studentFinanceDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_student = QLabel("-")
        self.d_matricule = QLabel("-")
        self.d_class = QLabel("-")
        self.d_expected = QLabel("0 FCFA")
        self.d_discount = QLabel("0 FCFA")
        self.d_paid = QLabel("0 FCFA")
        self.d_remaining = QLabel("0 FCFA")

        details_layout.addRow("Élève :", self.d_student)
        details_layout.addRow("Matricule :", self.d_matricule)
        details_layout.addRow("Classe :", self.d_class)
        details_layout.addRow("Montant prévu :", self.d_expected)
        details_layout.addRow("Réduction :", self.d_discount)
        details_layout.addRow("Payé :", self.d_paid)
        details_layout.addRow("Reste :", self.d_remaining)
        layout.addWidget(self.details_card)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(5)
        self.summary_table.setHorizontalHeaderLabels([
            "Frais",
            "Montant prévu",
            "Réduction",
            "Payé",
            "Reste"
        ])
        setup_table(self.summary_table)
        
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(QLabel("Résumé financier"))
        layout.addWidget(self.summary_table)

        layout.addWidget(QLabel("Total restant :"))
        self.total_remaining_label = QLabel("0.00")
        layout.addWidget(self.total_remaining_label)

        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels([
            "Reçu",
            "Frais",
            "Montant",
            "Date",
            "Saisi par"
        ])
        setup_table(self.payments_table)
        
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(QLabel("Historique des paiements"))
        layout.addWidget(self.payments_table)

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
            QFrame#studentFinanceDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.search_input.textChanged.connect(self.load_students)
        self.establishment_filter.currentIndexChanged.connect(self.on_establishment_changed)
        self.class_filter.currentIndexChanged.connect(self.load_students)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.students_table.itemSelectionChanged.connect(self.on_student_selected)

        self.load_current_school_year()
        self.load_establishments()
        self.load_classes()
        self.load_students()

    def load_current_school_year(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id
                FROM school_years
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

            if row:
                self.current_school_year_id = row[0]

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement année scolaire impossible : {e}")
        finally:
            conn.close()

    def load_establishments(self):
        self.establishment_filter.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cursor.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
                    (self.current_user["establishment_id"],),
                )
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def on_establishment_changed(self):
        self.load_classes()
        self.load_students()

    def load_classes(self):
        self.class_filter.clear()
        self.class_filter.addItem("Toutes", None)
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            params = [self.current_school_year_id]
            sql = """
                SELECT DISTINCT c.id, c.name
                FROM classes c
                JOIN enrollments e ON e.class_id = c.id
                JOIN students s ON s.id = e.student_id
                WHERE e.school_year_id = %s
            """
            if self.is_global_admin:
                est_id = self.establishment_filter.currentData()
                if est_id is not None:
                    sql += " AND s.establishment_id = %s"
                    params.append(est_id)
            else:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            sql += " ORDER BY c.name"
            cursor.execute(sql, params)
            for class_id, name in cursor.fetchall():
                self.class_filter.addItem(name, class_id)
        finally:
            conn.close()

    def load_students(self):
        self.students_table.setRowCount(0)
        self.summary_table.setRowCount(0)
        self.payments_table.setRowCount(0)
        self.total_remaining_label.setText("0.00")
        self.selected_student_id = None
        self.clear_details()

        conn = get_connection()
        if not conn or self.current_school_year_id is None:
            return

        search_text = self.search_input.text().strip()
        search_pattern = f"%{search_text}%"
        class_id = self.class_filter.currentData()
        establishment_id = self.establishment_filter.currentData()

        try:
            cursor = conn.cursor()
            filters = [
                "e.school_year_id = %s",
                "s.is_active = TRUE",
                """(
                    s.first_name ILIKE %s
                    OR s.last_name ILIKE %s
                    OR s.matricule ILIKE %s
                )""",
            ]
            params = [self.current_school_year_id, search_pattern, search_pattern, search_pattern]

            if self.is_global_admin:
                if establishment_id is not None:
                    filters.append("s.establishment_id = %s")
                    params.append(establishment_id)
            else:
                filters.append("s.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if class_id is not None:
                filters.append("c.id = %s")
                params.append(class_id)

            where_sql = " AND ".join(filters)
            cursor.execute(
                f"""
                SELECT
                    s.id,
                    s.last_name || ' ' || s.first_name AS student_name,
                    c.name AS class_name
                FROM students s
                JOIN enrollments e ON e.student_id = s.id
                JOIN classes c ON c.id = e.class_id
                WHERE {where_sql}
                ORDER BY s.last_name, s.first_name
                """,
                params
            )

            rows = cursor.fetchall()

            self.students_table.setRowCount(len(rows))

            for i, (student_id, student_name, class_name) in enumerate(rows):
                for j, value in enumerate((student_id, student_name, class_name)):
                    item = QTableWidgetItem("" if value is None else str(value))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.students_table.setItem(i, j, item)

            self.students_table.resizeColumnsToContents()

            if rows:
                self.students_table.selectRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement élèves impossible : {e}")
        finally:
            conn.close()

    def on_student_selected(self):
        selected_row = self.students_table.currentRow()

        if selected_row == -1:
            self.selected_student_id = None
            self.summary_table.setRowCount(0)
            self.payments_table.setRowCount(0)
            self.total_remaining_label.setText("0.00")
            self.clear_details()
            return

        student_id_item = self.students_table.item(selected_row, 0)
        if not student_id_item:
            return

        self.selected_student_id = int(student_id_item.text())
        self.load_student_details()
        self.load_financial_summary()
        self.load_payment_history()

    def clear_details(self):
        self.d_student.setText("-")
        self.d_matricule.setText("-")
        self.d_class.setText("-")
        self.d_expected.setText("0 FCFA")
        self.d_discount.setText("0 FCFA")
        self.d_paid.setText("0 FCFA")
        self.d_remaining.setText("0 FCFA")

    def load_student_details(self):
        if self.selected_student_id is None:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    s.last_name || ' ' || s.first_name AS student_name,
                    COALESCE(s.matricule, '-'),
                    COALESCE(c.name, '-')
                FROM students s
                LEFT JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = %s
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE s.id = %s
                """,
                (self.current_school_year_id, self.selected_student_id),
            )
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return
            self.d_student.setText(row[0] or "-")
            self.d_matricule.setText(row[1] or "-")
            self.d_class.setText(row[2] or "-")
        finally:
            conn.close()

    def load_financial_summary(self):
        self.summary_table.setRowCount(0)
        self.total_remaining_label.setText("0.00")

        if self.selected_student_id is None or self.current_school_year_id is None:
            return

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    f.name,
                    cf.amount,
                    COALESCE((
                        SELECT SUM(sd.amount)
                        FROM student_discounts sd
                        WHERE sd.student_id = %s
                          AND sd.fee_id = f.id
                    ), 0) AS discount,
                    COALESCE((
                        SELECT SUM(p.amount)
                        FROM payments p
                        WHERE p.student_id = %s
                          AND p.class_fee_id = cf.id
                    ), 0) AS paid
                FROM class_fees cf
                JOIN fees f ON f.id = cf.fee_id
                JOIN enrollments e ON e.class_id = cf.class_id
                WHERE e.student_id = %s
                  AND e.school_year_id = %s
                  AND cf.school_year_id = %s
                ORDER BY f.name
                """,
                (
                    self.selected_student_id,
                    self.selected_student_id,
                    self.selected_student_id,
                    self.current_school_year_id,
                    self.current_school_year_id
                )
            )

            rows = cursor.fetchall()

            self.summary_table.setRowCount(len(rows))
            total_remaining = 0.0
            total_expected = 0.0
            total_discount = 0.0
            total_paid = 0.0

            for i, row in enumerate(rows):
                fee_name, expected, discount, paid = row

                expected = float(expected or 0)
                discount = float(discount or 0)
                paid = float(paid or 0)
                remaining = max((expected - discount) - paid, 0)

                total_remaining += remaining
                total_expected += expected
                total_discount += discount
                total_paid += paid

                values = [
                    fee_name,
                    f"{expected:.2f}",
                    f"{discount:.2f}",
                    f"{paid:.2f}",
                    f"{remaining:.2f}"
                ]

                for j, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.summary_table.setItem(i, j, item)

            self.total_remaining_label.setText(f"{total_remaining:.2f}")
            self.d_expected.setText(f"{total_expected:,.0f} FCFA")
            self.d_discount.setText(f"{total_discount:,.0f} FCFA")
            self.d_paid.setText(f"{total_paid:,.0f} FCFA")
            self.d_remaining.setText(f"{total_remaining:,.0f} FCFA")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement résumé financier impossible : {e}")
        finally:
            conn.close()

    def load_payment_history(self):
        self.payments_table.setRowCount(0)

        if self.selected_student_id is None:
            return

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    p.receipt_number,
                    COALESCE(fcf.name, ffallback.name) AS fee_name,
                    p.amount,
                    p.payment_date,
                    u.username
                FROM payments p
                JOIN users u ON u.id = p.created_by
                LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                LEFT JOIN fees fcf ON fcf.id = cf.fee_id
                LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
                WHERE p.student_id = %s
                ORDER BY p.payment_date DESC, p.id DESC
                """,
                (self.selected_student_id,)
            )

            rows = cursor.fetchall()
            self.payments_table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                receipt_number, fee_name, amount, payment_date, username = row

                values = [
                    receipt_number or "",
                    fee_name or "",
                    f"{float(amount or 0):.2f}",
                    str(payment_date) if payment_date else "",
                    username or ""
                ]

                for j, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.payments_table.setItem(i, j, item)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement historique paiements impossible : {e}")
        finally:
            conn.close()

    def open_details_dialog(self):
        if self.selected_student_id is None:
            QMessageBox.warning(self, "Validation", "Sélectionnez un élève")
            return

        dialog = StudentFinanceDetailsDialog(
            student_id=self.selected_student_id,
            current_user=self.current_user,
            current_school_year_id=self.current_school_year_id,
            parent=self,
        )
        dialog.exec()
