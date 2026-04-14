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
)

from database.connection import get_connection
from ui.finance.add_expense_dialog import AddExpenseDialog
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

        filters.addWidget(QLabel("Recherche"))
        filters.addWidget(self.search_input)
        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter dépense")
        self.delete_btn = QPushButton("Supprimer")
        self.refresh_btn = QPushButton("Actualiser")
        btns.addWidget(self.add_btn)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Date", "Catégorie", "Montant", "Description", "Établissement", "Saisi par"])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        layout.addLayout(filters)
        layout.addLayout(btns)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.setStyleSheet("QLabel { color: #111827; font-weight: 600; }")

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.refresh_btn.clicked.connect(self.load_rows)
        self.search_input.textChanged.connect(self.load_rows)
        self.establishment_filter.currentIndexChanged.connect(self.load_rows)

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
                cur.execute("SELECT id, name FROM establishments WHERE id=%s", (est_id,))
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

        search = f"%{self.search_input.text().strip()}%"
        est_id = self.establishment_filter.currentData()

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
                    self.table.setItem(i, j, QTableWidgetItem(txt))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddExpenseDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_rows()

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
