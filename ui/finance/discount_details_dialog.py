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


class DiscountDetailsDialog(QDialog):
    def __init__(self, discount_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.discount_id = int(discount_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète réduction")
        self.resize(760, 460)

        root = QVBoxLayout()

        title = QLabel("Fiche complète réduction")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_student = QLabel("-")
        self.v_matricule = QLabel("-")
        self.v_class = QLabel("-")
        self.v_fee = QLabel("-")
        self.v_amount = QLabel("-")
        self.v_reason = QLabel("-")
        self.v_date = QLabel("-")

        self.v_reason.setWordWrap(True)

        form.addRow("ID :", self.v_id)
        form.addRow("Élève :", self.v_student)
        form.addRow("Matricule :", self.v_matricule)
        form.addRow("Classe actuelle :", self.v_class)
        form.addRow("Type de frais :", self.v_fee)
        form.addRow("Montant :", self.v_amount)
        form.addRow("Motif :", self.v_reason)
        form.addRow("Date :", self.v_date)

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
                    d.id,
                    s.last_name || ' ' || s.first_name AS student_name,
                    COALESCE(s.matricule, ''),
                    COALESCE(c.name, ''),
                    f.name,
                    d.amount,
                    COALESCE(d.reason, ''),
                    d.created_at
                FROM student_discounts d
                JOIN students s ON s.id = d.student_id
                JOIN fees f ON f.id = d.fee_id
                LEFT JOIN enrollments e ON e.student_id = s.id
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE d.id = %s
            """
            params = [self.discount_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))
            sql += " ORDER BY e.id DESC LIMIT 1"

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Réduction introuvable.")
                return

            discount_id, student_name, matricule, class_name, fee_name, amount, reason, created_at = row
            self.v_id.setText(str(discount_id))
            self.v_student.setText(student_name or "-")
            self.v_matricule.setText(matricule or "-")
            self.v_class.setText(class_name or "-")
            self.v_fee.setText(fee_name or "-")
            self.v_amount.setText(f"{float(amount or 0):,.0f} FCFA")
            self.v_reason.setText(reason or "-")
            self.v_date.setText("" if created_at is None else str(created_at))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
