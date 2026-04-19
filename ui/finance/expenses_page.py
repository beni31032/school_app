from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QLabel,
    QComboBox,
    QFrame,
    QFormLayout,
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.finance.add_expense_dialog import AddExpenseDialog
from ui.finance.expense_details_dialog import ExpenseDetailsDialog
from utils.expense_service import ensure_expenses_table
from utils.table_style import setup_table


class ExpensesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_expenses_table()

        layout = QVBoxLayout()
        filters = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher catégorie/description")
        self.establishment_filter = QComboBox()
        self.category_filter = QComboBox()

        filters.addWidget(QLabel("Recherche"))
        filters.addWidget(self.search_input)
        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Catégorie"))
        filters.addWidget(self.category_filter)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter dépense")
        self.details_btn = QPushButton("Voir fiche complète")
        self.delete_btn = QPushButton("Supprimer")
        self.refresh_btn = QPushButton("Actualiser")
        btns.addWidget(self.add_btn)
        btns.addWidget(self.details_btn)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Date", "Catégorie", "Montant", "Description", "Établissement", "Saisi par"])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("expenseDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_date = QLabel("-")
        self.d_category = QLabel("-")
        self.d_amount = QLabel("-")
        self.d_establishment = QLabel("-")
        self.d_created_by = QLabel("-")
        self.d_description = QLabel("-")
        self.d_description.setWordWrap(True)

        details_layout.addRow("Date :", self.d_date)
        details_layout.addRow("Catégorie :", self.d_category)
        details_layout.addRow("Montant :", self.d_amount)
        details_layout.addRow("Établissement :", self.d_establishment)
        details_layout.addRow("Saisi par :", self.d_created_by)
        details_layout.addRow("Description :", self.d_description)

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
            QFrame#expenseDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.refresh_btn.clicked.connect(self.load_rows)
        self.search_input.textChanged.connect(self.load_rows)
        self.establishment_filter.currentIndexChanged.connect(self.load_rows)
        self.category_filter.currentIndexChanged.connect(self.load_rows)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_establishment_filter()
        self.load_category_filter()
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
                cur.execute("SELECT id, name FROM establishments WHERE id=%s", (est_id,))
                row = cur.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def load_category_filter(self):
        self.category_filter.clear()
        self.category_filter.addItem("Toutes", None)
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            params = []
            sql = "SELECT DISTINCT category FROM expenses"
            if not self.is_global_admin:
                sql += " WHERE establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            sql += " ORDER BY category"
            cur.execute(sql, params)
            for (category,) in cur.fetchall():
                if category:
                    self.category_filter.addItem(category, category)
        finally:
            conn.close()

    def load_rows(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        est_id = self.establishment_filter.currentData()
        category = self.category_filter.currentData()

        try:
            cur = conn.cursor()
            where = "WHERE (e.category ILIKE %s OR COALESCE(e.description,'') ILIKE %s)"
            params = [search, search]

            if self.is_global_admin:
                if est_id is not None:
                    where += " AND e.establishment_id = %s"
                    params.append(est_id)
            else:
                where += " AND e.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            if category is not None:
                where += " AND e.category = %s"
                params.append(category)

            cur.execute(
                f"""
                SELECT
                    e.id,
                    e.expense_date,
                    e.category,
                    e.amount,
                    COALESCE(e.description, ''),
                    es.name,
                    COALESCE(u.username, '-')
                FROM expenses e
                JOIN establishments es ON es.id = e.establishment_id
                LEFT JOIN users u ON u.id = e.created_by
                {where}
                ORDER BY e.expense_date DESC, e.id DESC
                """,
                params,
            )
            rows = cur.fetchall()
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    if j == 3 and val is not None:
                        txt = f"{float(val):,.0f}"
                    else:
                        txt = "" if val is None else str(val)
                    item = QTableWidgetItem(txt)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, j, item)

            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddExpenseDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_category_filter()
            self.load_rows()

    def clear_details(self):
        self.d_date.setText("-")
        self.d_category.setText("-")
        self.d_amount.setText("-")
        self.d_establishment.setText("-")
        self.d_created_by.setText("-")
        self.d_description.setText("-")

    def load_selected_details(self):
        row = self.table.currentRow()
        if row == -1:
            self.clear_details()
            return

        expense_id_item = self.table.item(row, 0)
        if not expense_id_item:
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
                    e.expense_date,
                    e.category,
                    e.amount,
                    COALESCE(e.description, ''),
                    es.name,
                    COALESCE(u.username, '-')
                FROM expenses e
                JOIN establishments es ON es.id = e.establishment_id
                LEFT JOIN users u ON u.id = e.created_by
                WHERE e.id = %s
            """
            params = [int(expense_id_item.text())]
            if not self.is_global_admin:
                sql += " AND e.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cur.execute(sql, params)
            row_data = cur.fetchone()
            if not row_data:
                self.clear_details()
                return

            expense_date, category, amount, description, establishment_name, username = row_data
            self.d_date.setText("" if expense_date is None else str(expense_date))
            self.d_category.setText(category or "-")
            self.d_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.d_establishment.setText(establishment_name or "-")
            self.d_created_by.setText(username or "-")
            self.d_description.setText(description or "-")
        finally:
            conn.close()

    def open_details_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez une dépense")
            return

        expense_id_item = self.table.item(row, 0)
        if not expense_id_item:
            QMessageBox.warning(self, "Validation", "Dépense invalide")
            return

        dialog = ExpenseDetailsDialog(
            expense_id=int(expense_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()

    def delete_selected(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez une dépense")
            return
        expense_id_item = self.table.item(row, 0)
        if not expense_id_item:
            return

        if QMessageBox.question(
            self,
            "Confirmation",
            "Supprimer cette dépense ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()
            if self.is_global_admin:
                cur.execute("DELETE FROM expenses WHERE id = %s", (int(expense_id_item.text()),))
            else:
                cur.execute(
                    "DELETE FROM expenses WHERE id = %s AND establishment_id = %s",
                    (int(expense_id_item.text()), self.current_user["establishment_id"]),
                )
            conn.commit()
            self.load_rows()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Suppression impossible : {e}")
        finally:
            conn.close()
