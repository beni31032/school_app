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


class PaymentDetailsDialog(QDialog):
    def __init__(self, payment_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.payment_id = int(payment_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète paiement")
        self.resize(760, 480)

        root = QVBoxLayout()

        title = QLabel("Fiche complète paiement")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_receipt = QLabel("-")
        self.v_student = QLabel("-")
        self.v_class = QLabel("-")
        self.v_fee = QLabel("-")
        self.v_amount = QLabel("-")
        self.v_date = QLabel("-")
        self.v_created_by = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Reçu :", self.v_receipt)
        form.addRow("Élève :", self.v_student)
        form.addRow("Classe :", self.v_class)
        form.addRow("Frais :", self.v_fee)
        form.addRow("Montant :", self.v_amount)
        form.addRow("Date :", self.v_date)
        form.addRow("Saisi par :", self.v_created_by)

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
                    p.id,
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
            params = [self.payment_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Paiement introuvable.")
                return

            payment_id, receipt, student, class_name, fee_name, amount, payment_date, created_by = row
            self.v_id.setText(str(payment_id))
            self.v_receipt.setText(receipt or "-")
            self.v_student.setText(student or "-")
            self.v_class.setText(class_name or "-")
            self.v_fee.setText(fee_name or "-")
            self.v_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.v_date.setText("" if payment_date is None else str(payment_date))
            self.v_created_by.setText(created_by or "-")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
