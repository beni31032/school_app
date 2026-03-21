from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox
)

from database.connection import get_connection
from ui.finance.add_discount_dialog import AddDiscountDialog
from utils.table_style import setup_table


class DiscountsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par élève ou type de frais")

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter réduction")
        self.refresh_btn = QPushButton("Actualiser")

        btn_layout.addWidget(self.add_btn)
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
        layout.addWidget(QLabel("Réductions"))
        layout.addWidget(self.search_input)
        layout.addLayout(btn_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.refresh_btn.clicked.connect(self.load_discounts)
        self.search_input.textChanged.connect(self.load_discounts)

        self.load_discounts()

    def load_discounts(self):
        conn = get_connection()
        if not conn:
            return

        search = f"%{self.search_input.text()}%"

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
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
                WHERE
                    s.first_name ILIKE %s
                    OR s.last_name ILIKE %s
                    OR f.name ILIKE %s
                ORDER BY d.created_at DESC
                """,
                (search, search, search)
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem(str(val)))

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddDiscountDialog(self.current_user, self)

        if dialog.exec():
            self.load_discounts()