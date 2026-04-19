from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QFormLayout,
    QPushButton,
    QMessageBox,
)

from database.connection import get_connection


class ExpenseDetailsDialog(QDialog):
    def __init__(self, expense_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.expense_id = int(expense_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète dépense")
        self.resize(720, 460)

        root = QVBoxLayout()

        title = QLabel("Fiche complète dépense")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_date = QLabel("-")
        self.v_category = QLabel("-")
        self.v_amount = QLabel("-")
        self.v_description = QLabel("-")
        self.v_establishment = QLabel("-")
        self.v_created_by = QLabel("-")
        self.v_created_at = QLabel("-")

        self.v_description.setWordWrap(True)

        form.addRow("ID :", self.v_id)
        form.addRow("Date :", self.v_date)
        form.addRow("Catégorie :", self.v_category)
        form.addRow("Montant :", self.v_amount)
        form.addRow("Description :", self.v_description)
        form.addRow("Établissement :", self.v_establishment)
        form.addRow("Saisi par :", self.v_created_by)
        form.addRow("Créé le :", self.v_created_at)

        actions = QHBoxLayout()
        actions.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)

        root.addWidget(title)
        root.addWidget(card)
        root.addLayout(actions)
        self.setLayout(root)

        self.setStyleSheet(
            """
            QDialog { background-color: #f1f5f9; }
            QLabel#dialogTitle {
                color: #111827;
                font-size: 22px;
                font-weight: 800;
                margin-bottom: 4px;
            }
            QFrame#detailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            QLabel {
                color: #111827;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            """
        )

        self.load_details()

    def load_details(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    e.id,
                    e.expense_date,
                    e.category,
                    e.amount,
                    COALESCE(e.description, ''),
                    es.name,
                    COALESCE(u.username, '-'),
                    e.created_at
                FROM expenses e
                JOIN establishments es ON es.id = e.establishment_id
                LEFT JOIN users u ON u.id = e.created_by
                WHERE e.id = %s
            """
            params = [self.expense_id]
            if not self.is_global_admin:
                sql += " AND e.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Dépense introuvable.")
                return

            expense_id, expense_date, category, amount, description, establishment, created_by, created_at = row

            self.v_id.setText(str(expense_id))
            self.v_date.setText("" if expense_date is None else str(expense_date))
            self.v_category.setText(category or "-")
            self.v_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.v_description.setText(description or "-")
            self.v_establishment.setText(establishment or "-")
            self.v_created_by.setText(created_by or "-")
            self.v_created_at.setText("" if created_at is None else str(created_at))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
