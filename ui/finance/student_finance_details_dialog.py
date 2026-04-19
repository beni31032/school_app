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


class StudentFinanceDetailsDialog(QDialog):
    def __init__(self, student_id: int, current_user: dict, current_school_year_id: int, parent=None):
        super().__init__(parent)
        self.student_id = int(student_id)
        self.current_user = current_user
        self.current_school_year_id = current_school_year_id
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète situation élève")
        self.resize(760, 520)

        root = QVBoxLayout()

        title = QLabel("Fiche complète situation élève")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_student = QLabel("-")
        self.v_matricule = QLabel("-")
        self.v_class = QLabel("-")
        self.v_establishment = QLabel("-")
        self.v_expected = QLabel("0 FCFA")
        self.v_discount = QLabel("0 FCFA")
        self.v_paid = QLabel("0 FCFA")
        self.v_remaining = QLabel("0 FCFA")

        form.addRow("Élève :", self.v_student)
        form.addRow("Matricule :", self.v_matricule)
        form.addRow("Classe :", self.v_class)
        form.addRow("Établissement :", self.v_establishment)
        form.addRow("Montant prévu :", self.v_expected)
        form.addRow("Réduction :", self.v_discount)
        form.addRow("Payé :", self.v_paid)
        form.addRow("Reste :", self.v_remaining)

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
            student_sql = """
                SELECT
                    s.last_name || ' ' || s.first_name,
                    COALESCE(s.matricule, '-'),
                    COALESCE(c.name, '-'),
                    COALESCE(es.name, '-')
                FROM students s
                LEFT JOIN establishments es ON es.id = s.establishment_id
                LEFT JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = %s
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE s.id = %s
            """
            params = [self.current_school_year_id, self.student_id]
            if not self.is_global_admin:
                student_sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            cursor.execute(student_sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Élève introuvable.")
                return

            self.v_student.setText(row[0] or "-")
            self.v_matricule.setText(row[1] or "-")
            self.v_class.setText(row[2] or "-")
            self.v_establishment.setText(row[3] or "-")

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(cf.amount), 0) AS expected_total,
                    COALESCE((
                        SELECT SUM(sd.amount)
                        FROM student_discounts sd
                        WHERE sd.student_id = %s
                    ), 0) AS discount_total,
                    COALESCE((
                        SELECT SUM(p.amount)
                        FROM payments p
                        WHERE p.student_id = %s
                    ), 0) AS paid_total
                FROM class_fees cf
                JOIN enrollments e ON e.class_id = cf.class_id
                WHERE e.student_id = %s
                  AND e.school_year_id = %s
                  AND cf.school_year_id = %s
                """,
                (
                    self.student_id,
                    self.student_id,
                    self.student_id,
                    self.current_school_year_id,
                    self.current_school_year_id,
                ),
            )
            totals = cursor.fetchone() or (0, 0, 0)
            expected_total = float(totals[0] or 0)
            discount_total = float(totals[1] or 0)
            paid_total = float(totals[2] or 0)
            remaining_total = max(expected_total - discount_total - paid_total, 0)

            self.v_expected.setText(f"{expected_total:,.0f} FCFA")
            self.v_discount.setText(f"{discount_total:,.0f} FCFA")
            self.v_paid.setText(f"{paid_total:,.0f} FCFA")
            self.v_remaining.setText(f"{remaining_total:,.0f} FCFA")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
