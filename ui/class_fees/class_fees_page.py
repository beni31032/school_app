from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox,
    QLineEdit, QLabel, QComboBox, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.class_fees.add_class_fee_dialog import AddClassFeeDialog
from ui.class_fees.class_fee_details_dialog import ClassFeeDetailsDialog
from ui.class_fees.edit_class_fee_dialog import EditClassFeeDialog
from utils.table_style import setup_table


class ClassFeesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        layout = QVBoxLayout()
        filters_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher classe, frais, établissement...")
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Année scolaire"))
        filters_layout.addWidget(self.school_year_filter)

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Établissement",
            "Frais",
            "Montant",
            "Année scolaire"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("classFeeDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_class = QLabel("-")
        self.d_est = QLabel("-")
        self.d_fee = QLabel("-")
        self.d_amount = QLabel("-")
        self.d_year = QLabel("-")
        self.d_payments = QLabel("0")

        details_layout.addRow("Classe :", self.d_class)
        details_layout.addRow("Établissement :", self.d_est)
        details_layout.addRow("Type de frais :", self.d_fee)
        details_layout.addRow("Montant :", self.d_amount)
        details_layout.addRow("Année scolaire :", self.d_year)
        details_layout.addRow("Paiements liés :", self.d_payments)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
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
            QFrame#classFeeDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_data)
        self.search_input.textChanged.connect(self.load_data)
        self.establishment_filter.currentIndexChanged.connect(self.load_data)
        self.school_year_filter.currentIndexChanged.connect(self.load_data)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_establishment_filter()
        self.load_school_year_filter()
        self.load_data()

    def load_establishment_filter(self):
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

    def load_school_year_filter(self):
        self.school_year_filter.clear()
        self.school_year_filter.addItem("Toutes", None)

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for school_year_id, name in cursor.fetchall():
                self.school_year_filter.addItem(name, school_year_id)
        finally:
            conn.close()

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            search = f"%{self.search_input.text().strip()}%"
            establishment_id = self.establishment_filter.currentData()
            school_year_id = self.school_year_filter.currentData()

            filters = [
                "(c.name ILIKE %s OR e.name ILIKE %s OR f.name ILIKE %s OR sy.name ILIKE %s)"
            ]
            params = [search, search, search, search]

            if self.is_global_admin:
                if establishment_id is not None:
                    filters.append("c.establishment_id = %s")
                    params.append(establishment_id)
            else:
                filters.append("c.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if school_year_id is not None:
                filters.append("cf.school_year_id = %s")
                params.append(school_year_id)

            where_sql = " AND ".join(filters)
            cursor.execute(
                f"""
                SELECT
                    cf.id,
                    c.name AS class_name,
                    e.name AS establishment_name,
                    f.name AS fee_name,
                    cf.amount,
                    sy.name AS school_year_name
                FROM class_fees cf
                JOIN classes c ON c.id = cf.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN fees f ON f.id = cf.fee_id
                JOIN school_years sy ON sy.id = cf.school_year_id
                WHERE {where_sql}
                ORDER BY sy.name DESC, e.name, c.name, f.name
                """,
                params,
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_index, col_index, item)

            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddClassFeeDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        class_fee_id_item = self.table.item(selected, 0)
        if not class_fee_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide")
            return

        class_fee_id = class_fee_id_item.text()

        dialog = EditClassFeeDialog(
            class_fee_id=class_fee_id,
            current_user=self.current_user,
            parent=self
        )
        if dialog.exec():
            self.load_data()

    def clear_details(self):
        self.d_class.setText("-")
        self.d_est.setText("-")
        self.d_fee.setText("-")
        self.d_amount.setText("-")
        self.d_year.setText("-")
        self.d_payments.setText("0")

    def load_selected_details(self):
        selected = self.table.currentRow()
        if selected == -1:
            self.clear_details()
            return

        class_fee_id_item = self.table.item(selected, 0)
        if not class_fee_id_item:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cursor = conn.cursor()
            class_fee_id = int(class_fee_id_item.text())
            sql = """
                SELECT
                    c.name,
                    e.name,
                    f.name,
                    cf.amount,
                    sy.name
                FROM class_fees cf
                JOIN classes c ON c.id = cf.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN fees f ON f.id = cf.fee_id
                JOIN school_years sy ON sy.id = cf.school_year_id
                WHERE cf.id = %s
            """
            params = [class_fee_id]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            cursor.execute("SELECT COUNT(*) FROM payments WHERE class_fee_id = %s", (class_fee_id,))
            payments_count = cursor.fetchone()[0] or 0

            class_name, establishment_name, fee_name, amount, school_year_name = row
            self.d_class.setText(class_name or "-")
            self.d_est.setText(establishment_name or "-")
            self.d_fee.setText(fee_name or "-")
            self.d_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.d_year.setText(school_year_name or "-")
            self.d_payments.setText(str(payments_count))
        finally:
            conn.close()

    def open_details_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        class_fee_id_item = self.table.item(selected, 0)
        if not class_fee_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide")
            return

        dialog = ClassFeeDetailsDialog(
            class_fee_id=int(class_fee_id_item.text()),
            current_user=self.current_user,
            parent=self
        )
        dialog.exec()
