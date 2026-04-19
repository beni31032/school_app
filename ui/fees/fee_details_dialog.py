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


class FeeDetailsDialog(QDialog):
    def __init__(self, fee_id: int, parent=None):
        super().__init__(parent)
        self.fee_id = int(fee_id)

        self.setWindowTitle("Fiche complète type de frais")
        self.resize(700, 420)

        root = QVBoxLayout()

        title = QLabel("Fiche complète type de frais")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_name = QLabel("-")
        self.v_description = QLabel("-")
        self.v_class_count = QLabel("0")
        self.v_payments_count = QLabel("0")
        self.v_discounts_count = QLabel("0")

        self.v_description.setWordWrap(True)

        form.addRow("ID :", self.v_id)
        form.addRow("Nom :", self.v_name)
        form.addRow("Description :", self.v_description)
        form.addRow("Classes configurées :", self.v_class_count)
        form.addRow("Paiements liés :", self.v_payments_count)
        form.addRow("Réductions liées :", self.v_discounts_count)

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
            cursor.execute(
                """
                SELECT id, name, COALESCE(description, '')
                FROM fees
                WHERE id = %s
                """,
                (self.fee_id,),
            )
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Type de frais introuvable.")
                return

            fee_id, name, description = row

            cursor.execute("SELECT COUNT(*) FROM class_fees WHERE fee_id = %s", (fee_id,))
            class_count = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM payments WHERE fee_id = %s", (fee_id,))
            payments_count = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM student_discounts WHERE fee_id = %s", (fee_id,))
            discounts_count = cursor.fetchone()[0] or 0

            self.v_id.setText(str(fee_id))
            self.v_name.setText(name or "-")
            self.v_description.setText(description or "-")
            self.v_class_count.setText(str(class_count))
            self.v_payments_count.setText(str(payments_count))
            self.v_discounts_count.setText(str(discounts_count))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
