from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox,
    QLineEdit, QLabel, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.fees.add_fee_dialog import AddFeeDialog
from ui.fees.fee_details_dialog import FeeDetailsDialog
from ui.fees.edit_fee_dialog import EditFeeDialog
from utils.table_style import setup_table


class FeesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        layout = QVBoxLayout()
        filters_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un type de frais...")

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Nom", "Description"])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("feeDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_name = QLabel("-")
        self.d_description = QLabel("-")
        self.d_class_count = QLabel("0")
        self.d_payments_count = QLabel("0")
        self.d_discounts_count = QLabel("0")
        self.d_description.setWordWrap(True)

        details_layout.addRow("Nom :", self.d_name)
        details_layout.addRow("Description :", self.d_description)
        details_layout.addRow("Classes configurées :", self.d_class_count)
        details_layout.addRow("Paiements liés :", self.d_payments_count)
        details_layout.addRow("Réductions liées :", self.d_discounts_count)

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
            QFrame#feeDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_fees)
        self.search_input.textChanged.connect(self.load_fees)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_fees()

    def load_fees(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            search = f"%{self.search_input.text().strip()}%"
            cursor.execute(
                """
                SELECT id, name, description
                FROM fees
                WHERE name ILIKE %s OR COALESCE(description, '') ILIKE %s
                ORDER BY name
                """,
                (search, search),
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
        dialog = AddFeeDialog(parent=self)
        if dialog.exec():
            self.load_fees()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un type de frais")
            return

        fee_id_item = self.table.item(selected, 0)
        if not fee_id_item:
            QMessageBox.warning(self, "Erreur", "Frais invalide")
            return

        fee_id = fee_id_item.text()

        dialog = EditFeeDialog(fee_id=fee_id, parent=self)
        if dialog.exec():
            self.load_fees()

    def clear_details(self):
        self.d_name.setText("-")
        self.d_description.setText("-")
        self.d_class_count.setText("0")
        self.d_payments_count.setText("0")
        self.d_discounts_count.setText("0")

    def load_selected_details(self):
        selected = self.table.currentRow()
        if selected == -1:
            self.clear_details()
            return

        fee_id_item = self.table.item(selected, 0)
        if not fee_id_item:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cursor = conn.cursor()
            fee_id = int(fee_id_item.text())
            cursor.execute(
                """
                SELECT name, COALESCE(description, '')
                FROM fees
                WHERE id = %s
                """,
                (fee_id,),
            )
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            cursor.execute("SELECT COUNT(*) FROM class_fees WHERE fee_id = %s", (fee_id,))
            class_count = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM payments WHERE fee_id = %s", (fee_id,))
            payments_count = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM student_discounts WHERE fee_id = %s", (fee_id,))
            discounts_count = cursor.fetchone()[0] or 0

            self.d_name.setText(row[0] or "-")
            self.d_description.setText(row[1] or "-")
            self.d_class_count.setText(str(class_count))
            self.d_payments_count.setText(str(payments_count))
            self.d_discounts_count.setText(str(discounts_count))
        finally:
            conn.close()

    def open_details_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un type de frais")
            return

        fee_id_item = self.table.item(selected, 0)
        if not fee_id_item:
            QMessageBox.warning(self, "Erreur", "Frais invalide")
            return

        dialog = FeeDetailsDialog(fee_id=int(fee_id_item.text()), parent=self)
        dialog.exec()
