import os
import sys
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout,
    QMessageBox, QLineEdit, QLabel
)

from database.connection import get_connection
from ui.payments.add_payment_dialog import AddPaymentDialog
from utils.receipt_generator import generate_receipt
from utils.table_style import setup_table


class PaymentsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Rechercher par élève, numéro de reçu ou type de frais"
        )

        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter paiement")
        self.reprint_btn = QPushButton("Réimprimer reçu")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
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

        layout.addWidget(QLabel("Recherche"))
        layout.addWidget(self.search_input)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.reprint_btn.clicked.connect(self.reprint_receipt)
        self.refresh_btn.clicked.connect(self.load_payments)
        self.search_input.textChanged.connect(self.load_payments)

        self.load_payments()

    def load_payments(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search_text = self.search_input.text().strip()
        search_pattern = f"%{search_text}%"

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
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
                    WHERE (
                        p.receipt_number ILIKE %s
                        OR s.first_name ILIKE %s
                        OR s.last_name ILIKE %s
                        OR COALESCE(fcf.name, ffallback.name) ILIKE %s
                    )
                    ORDER BY p.payment_date DESC, p.id DESC
                    """,
                    (
                        search_pattern,
                        search_pattern,
                        search_pattern,
                        search_pattern
                    )
                )
            else:
                cursor.execute(
                    """
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
                    WHERE s.establishment_id = %s
                      AND (
                        p.receipt_number ILIKE %s
                        OR s.first_name ILIKE %s
                        OR s.last_name ILIKE %s
                        OR COALESCE(fcf.name, ffallback.name) ILIKE %s
                      )
                    ORDER BY p.payment_date DESC, p.id DESC
                    """,
                    (
                        self.current_user["establishment_id"],
                        search_pattern,
                        search_pattern,
                        search_pattern,
                        search_pattern
                    )
                )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    self.table.setItem(row_index, col_index, QTableWidgetItem(text))

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddPaymentDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_payments()

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