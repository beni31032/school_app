from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.finance.add_discount_dialog import AddDiscountDialog
from ui.finance.discount_details_dialog import DiscountDetailsDialog
from utils.table_style import setup_table


class DiscountsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par élève ou type de frais")
        filters_layout = QHBoxLayout()
        self.establishment_filter = QComboBox()
        self.fee_filter = QComboBox()

        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Frais"))
        filters_layout.addWidget(self.fee_filter)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter réduction")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.details_btn)
        btn_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Élève",
            "Frais",
            "Montant",
            "Motif",
            "Date"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)
        self.details_card = QFrame()
        self.details_card.setObjectName("discountDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_student = QLabel("-")
        self.d_fee = QLabel("-")
        self.d_amount = QLabel("-")
        self.d_reason = QLabel("-")
        self.d_date = QLabel("-")
        self.d_reason.setWordWrap(True)

        details_layout.addRow("Élève :", self.d_student)
        details_layout.addRow("Frais :", self.d_fee)
        details_layout.addRow("Montant :", self.d_amount)
        details_layout.addRow("Motif :", self.d_reason)
        details_layout.addRow("Date :", self.d_date)

        layout.addWidget(QLabel("Réductions"))
        layout.addWidget(self.search_input)
        layout.addLayout(filters_layout)
        layout.addLayout(btn_layout)
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
            QFrame#discountDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_discounts)
        self.search_input.textChanged.connect(self.load_discounts)
        self.establishment_filter.currentIndexChanged.connect(self.load_discounts)
        self.fee_filter.currentIndexChanged.connect(self.load_discounts)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_establishments()
        self.load_fees()
        self.load_discounts()

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

    def load_fees(self):
        self.fee_filter.clear()
        self.fee_filter.addItem("Tous", None)
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM fees ORDER BY name")
            for fee_id, name in cursor.fetchall():
                self.fee_filter.addItem(name, fee_id)
        finally:
            conn.close()

    def load_discounts(self):
        conn = get_connection()
        if not conn:
            return

        search = f"%{self.search_input.text()}%"
        establishment_id = self.establishment_filter.currentData()
        fee_id = self.fee_filter.currentData()

        try:
            cursor = conn.cursor()
            filters = [
                "(s.first_name ILIKE %s OR s.last_name ILIKE %s OR COALESCE(s.matricule,'') ILIKE %s OR f.name ILIKE %s OR COALESCE(d.reason,'') ILIKE %s)"
            ]
            params = [search, search, search, search, search]

            if self.is_global_admin:
                if establishment_id is not None:
                    filters.append("s.establishment_id = %s")
                    params.append(establishment_id)
            else:
                filters.append("s.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if fee_id is not None:
                filters.append("d.fee_id = %s")
                params.append(fee_id)

            where_sql = " AND ".join(filters)
            cursor.execute(
                f"""
                SELECT
                    d.id,
                    s.last_name || ' ' || s.first_name,
                    f.name,
                    d.amount,
                    COALESCE(d.reason, ''),
                    d.created_at
                FROM student_discounts d
                JOIN students s ON s.id = d.student_id
                JOIN fees f ON f.id = d.fee_id
                WHERE {where_sql}
                ORDER BY d.created_at DESC
                """,
                params
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    item = QTableWidgetItem("" if val is None else str(val))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, j, item)

            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddDiscountDialog(self.current_user, self)

        if dialog.exec():
            self.load_discounts()

    def clear_details(self):
        self.d_student.setText("-")
        self.d_fee.setText("-")
        self.d_amount.setText("-")
        self.d_reason.setText("-")
        self.d_date.setText("-")

    def load_selected_details(self):
        row = self.table.currentRow()
        if row == -1:
            self.clear_details()
            return

        discount_id_item = self.table.item(row, 0)
        if not discount_id_item:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    s.last_name || ' ' || s.first_name,
                    f.name,
                    d.amount,
                    COALESCE(d.reason, ''),
                    d.created_at
                FROM student_discounts d
                JOIN students s ON s.id = d.student_id
                JOIN fees f ON f.id = d.fee_id
                WHERE d.id = %s
            """
            params = [int(discount_id_item.text())]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            student_name, fee_name, amount, reason, created_at = row
            self.d_student.setText(student_name or "-")
            self.d_fee.setText(fee_name or "-")
            self.d_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.d_reason.setText(reason or "-")
            self.d_date.setText("" if created_at is None else str(created_at))
        finally:
            conn.close()

    def open_details_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une réduction")
            return

        discount_id_item = self.table.item(row, 0)
        if not discount_id_item:
            QMessageBox.warning(self, "Erreur", "Réduction invalide")
            return

        dialog = DiscountDetailsDialog(
            discount_id=int(discount_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()
