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


class ClassFeeDetailsDialog(QDialog):
    def __init__(self, class_fee_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.class_fee_id = int(class_fee_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète frais par classe")
        self.resize(760, 460)

        root = QVBoxLayout()

        title = QLabel("Fiche complète frais par classe")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_est = QLabel("-")
        self.v_class = QLabel("-")
        self.v_fee = QLabel("-")
        self.v_amount = QLabel("-")
        self.v_year = QLabel("-")
        self.v_payments = QLabel("0")

        form.addRow("ID :", self.v_id)
        form.addRow("Établissement :", self.v_est)
        form.addRow("Classe :", self.v_class)
        form.addRow("Type de frais :", self.v_fee)
        form.addRow("Montant :", self.v_amount)
        form.addRow("Année scolaire :", self.v_year)
        form.addRow("Paiements liés :", self.v_payments)

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
                    cf.id,
                    e.name,
                    c.name,
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
            params = [self.class_fee_id]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Enregistrement introuvable.")
                return

            class_fee_id, establishment_name, class_name, fee_name, amount, school_year_name = row

            cursor.execute("SELECT COUNT(*) FROM payments WHERE class_fee_id = %s", (class_fee_id,))
            payments_count = cursor.fetchone()[0] or 0

            self.v_id.setText(str(class_fee_id))
            self.v_est.setText(establishment_name or "-")
            self.v_class.setText(class_name or "-")
            self.v_fee.setText(fee_name or "-")
            self.v_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.v_year.setText(school_year_name or "-")
            self.v_payments.setText(str(payments_count))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
