import os
import sys
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout,
    QMessageBox, QLineEdit, QLabel, QComboBox, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.payments.add_payment_dialog import AddPaymentDialog
from ui.payments.payment_details_dialog import PaymentDetailsDialog
from utils.receipt_generator import generate_receipt
from utils.table_style import setup_table


class PaymentsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Rechercher par élève, numéro de reçu ou type de frais"
        )
        filters_layout = QHBoxLayout()
        self.establishment_filter = QComboBox()
        self.fee_filter = QComboBox()

        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Frais"))
        filters_layout.addWidget(self.fee_filter)

        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter paiement")
        self.details_btn = QPushButton("Voir fiche complète")
        self.reprint_btn = QPushButton("Réimprimer reçu")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.reprint_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Reçu",
            "Élève",
            "Classe",
            "Frais",
            "Montant",
            "Date",
            "Saisi par"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("paymentDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_receipt = QLabel("-")
        self.d_student = QLabel("-")
        self.d_class = QLabel("-")
        self.d_fee = QLabel("-")
        self.d_amount = QLabel("-")
        self.d_date = QLabel("-")
        self.d_created_by = QLabel("-")

        details_layout.addRow("Reçu :", self.d_receipt)
        details_layout.addRow("Élève :", self.d_student)
        details_layout.addRow("Classe :", self.d_class)
        details_layout.addRow("Frais :", self.d_fee)
        details_layout.addRow("Montant :", self.d_amount)
        details_layout.addRow("Date :", self.d_date)
        details_layout.addRow("Saisi par :", self.d_created_by)

        layout.addWidget(QLabel("Recherche"))
        layout.addWidget(self.search_input)
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
            QFrame#paymentDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.reprint_btn.clicked.connect(self.reprint_receipt)
        self.refresh_btn.clicked.connect(self.load_payments)
        self.search_input.textChanged.connect(self.load_payments)
        self.establishment_filter.currentIndexChanged.connect(self.load_payments)
        self.fee_filter.currentIndexChanged.connect(self.load_payments)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_establishments()
        self.load_fees()
        self.load_payments()

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

    def load_payments(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search_text = self.search_input.text().strip()
        search_pattern = f"%{search_text}%"
        establishment_id = self.establishment_filter.currentData()
        fee_id = self.fee_filter.currentData()

        try:
            cursor = conn.cursor()
            filters = [
                """(
                    p.receipt_number ILIKE %s
                    OR s.first_name ILIKE %s
                    OR s.last_name ILIKE %s
                    OR COALESCE(fcf.name, ffallback.name) ILIKE %s
                )"""
            ]
            params = [search_pattern, search_pattern, search_pattern, search_pattern]

            if self.is_global_admin:
                if establishment_id is not None:
                    filters.append("s.establishment_id = %s")
                    params.append(establishment_id)
            else:
                filters.append("s.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if fee_id is not None:
                filters.append("COALESCE(fcf.id, ffallback.id) = %s")
                params.append(fee_id)

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    p.id,
                    p.receipt_number,
                    s.last_name || ' ' || s.first_name AS student_name,
                    c.name AS class_name,
                    COALESCE(fcf.name, ffallback.name) AS fee_name,
                    p.amount,
                    p.payment_date,
                    u.username
                FROM payments p
                JOIN students s ON s.id = p.student_id
                JOIN users u ON u.id = p.created_by
                LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                LEFT JOIN fees fcf ON fcf.id = cf.fee_id
                LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
                LEFT JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = (
                        SELECT id
                        FROM school_years
                        ORDER BY id DESC
                        LIMIT 1
                   )
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE {where_sql}
                ORDER BY p.payment_date DESC, p.id DESC
                """,
                params
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_index, col_index, item)

            self.table.resizeColumnsToContents()
            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddPaymentDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_payments()

    def clear_details(self):
        self.d_receipt.setText("-")
        self.d_student.setText("-")
        self.d_class.setText("-")
        self.d_fee.setText("-")
        self.d_amount.setText("-")
        self.d_date.setText("-")
        self.d_created_by.setText("-")

    def load_selected_details(self):
        selected = self.table.currentRow()
        if selected == -1:
            self.clear_details()
            return

        payment_id_item = self.table.item(selected, 0)
        if not payment_id_item:
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
                    p.receipt_number,
                    s.last_name || ' ' || s.first_name AS student_name,
                    COALESCE(c.name, '-'),
                    COALESCE(fcf.name, ffallback.name),
                    p.amount,
                    p.payment_date,
                    u.username
                FROM payments p
                JOIN students s ON s.id = p.student_id
                JOIN users u ON u.id = p.created_by
                LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                LEFT JOIN fees fcf ON fcf.id = cf.fee_id
                LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
                LEFT JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = (
                        SELECT id FROM school_years ORDER BY id DESC LIMIT 1
                   )
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE p.id = %s
            """
            params = [int(payment_id_item.text())]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            receipt, student, class_name, fee_name, amount, payment_date, username = row
            self.d_receipt.setText(receipt or "-")
            self.d_student.setText(student or "-")
            self.d_class.setText(class_name or "-")
            self.d_fee.setText(fee_name or "-")
            self.d_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.d_date.setText("" if payment_date is None else str(payment_date))
            self.d_created_by.setText(username or "-")
        finally:
            conn.close()

    def open_details_dialog(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un paiement")
            return

        payment_id_item = self.table.item(selected, 0)
        if not payment_id_item:
            QMessageBox.warning(self, "Erreur", "Paiement invalide")
            return

        dialog = PaymentDetailsDialog(
            payment_id=int(payment_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()

    def open_pdf(self, filepath):
        try:
            if sys.platform.startswith("win"):
                os.startfile(filepath)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", filepath], check=False)
            else:
                subprocess.run(["xdg-open", filepath], check=False)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Reçu régénéré, mais impossible de l'ouvrir : {e}"
            )

    def reprint_receipt(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un paiement")
            return

        payment_id_item = self.table.item(selected, 0)
        if not payment_id_item:
            QMessageBox.warning(self, "Erreur", "Paiement invalide")
            return

        payment_id = int(payment_id_item.text())

        try:
            pdf_path = generate_receipt(payment_id)
            self.open_pdf(pdf_path)

            QMessageBox.information(
                self,
                "Succès",
                f"Reçu régénéré : {pdf_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Réimpression impossible : {e}")
