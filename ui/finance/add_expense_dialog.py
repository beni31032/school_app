from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from database.connection import get_connection
from utils.expense_service import ensure_expenses_table


class AddExpenseDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setWindowTitle("Ajouter dépense")
        self.setFixedWidth(420)

        ensure_expenses_table()

        layout = QVBoxLayout()
        form = QFormLayout()

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("ex: 150000")
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("ex: Fournitures")
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Description optionnelle")
        self.description_input.setFixedHeight(80)

        form.addRow("Montant :", self.amount_input)
        form.addRow("Catégorie :", self.category_input)
        form.addRow("Date :", self.date_input)
        form.addRow("Description :", self.description_input)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        layout.addLayout(form)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)

        self.save_btn.clicked.connect(self.save_expense)
        self.cancel_btn.clicked.connect(self.reject)

    def save_expense(self):
        try:
            amount = float(self.amount_input.text().strip().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Validation", "Montant invalide")
            return

        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Le montant doit être positif")
            return

        category = self.category_input.text().strip()
        if not category:
            QMessageBox.warning(self, "Validation", "Catégorie obligatoire")
            return

        expense_date = self.date_input.date().toString("yyyy-MM-dd")
        description = self.description_input.toPlainText().strip() or None

        est_id = self.current_user.get("establishment_id")
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()
            if self.current_user.get("role") == "ADMIN_GLOBAL" and est_id is None:
                cur.execute("SELECT id FROM establishments ORDER BY id LIMIT 1")
                row = cur.fetchone()
                est_id = row[0] if row else None

            if not est_id:
                QMessageBox.warning(self, "Validation", "Aucun établissement disponible")
                return

            cur.execute(
                """
                INSERT INTO expenses (
                    establishment_id, amount, category, expense_date, description, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (est_id, amount, category, expense_date, description, self.current_user.get("id")),
            )
            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()
