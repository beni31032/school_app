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


MONTH_LABELS = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}


class SalaryDetailsDialog(QDialog):
    def __init__(self, obligation_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.obligation_id = int(obligation_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète obligation salariale")
        self.resize(760, 500)

        root = QVBoxLayout()

        title = QLabel("Fiche complète obligation salariale")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_person = QLabel("-")
        self.v_type = QLabel("-")
        self.v_period = QLabel("-")
        self.v_due = QLabel("-")
        self.v_paid = QLabel("-")
        self.v_remaining = QLabel("-")
        self.v_status = QLabel("-")
        self.v_establishment = QLabel("-")
        self.v_created_at = QLabel("-")
        self.v_notes = QLabel("-")
        self.v_notes.setWordWrap(True)

        form.addRow("ID :", self.v_id)
        form.addRow("Personne :", self.v_person)
        form.addRow("Type :", self.v_type)
        form.addRow("Période :", self.v_period)
        form.addRow("Montant dû :", self.v_due)
        form.addRow("Montant payé :", self.v_paid)
        form.addRow("Reste :", self.v_remaining)
        form.addRow("Statut :", self.v_status)
        form.addRow("Établissement :", self.v_establishment)
        form.addRow("Créé le :", self.v_created_at)
        form.addRow("Notes :", self.v_notes)

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
                    so.id,
                    so.person_type,
                    CASE
                        WHEN so.person_type='TEACHER' THEN COALESCE(t.last_name || ' ' || t.first_name, '-')
                        ELSE COALESCE(sm.last_name || ' ' || sm.first_name, '-')
                    END AS person_name,
                    so.period_month,
                    so.period_year,
                    so.amount_due,
                    COALESCE(SUM(sp.amount), 0) AS paid_total,
                    e.name,
                    so.created_at,
                    COALESCE(so.notes, '')
                FROM salary_obligations so
                LEFT JOIN teachers t ON t.id = so.teacher_id
                LEFT JOIN staff_members sm ON sm.id = so.staff_member_id
                LEFT JOIN salary_payments sp ON sp.obligation_id = so.id
                JOIN establishments e ON e.id = so.establishment_id
                WHERE so.id = %s
            """
            params = [self.obligation_id]
            if not self.is_global_admin:
                sql += " AND so.establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            sql += """
                GROUP BY so.id, so.person_type, t.last_name, t.first_name, sm.last_name, sm.first_name,
                         so.period_month, so.period_year, so.amount_due, e.name, so.created_at, so.notes
            """

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Obligation introuvable.")
                return

            obligation_id, person_type, person_name, month, year, due, paid, establishment, created_at, notes = row
            remaining = float(due or 0) - float(paid or 0)
            if remaining <= 0.0001:
                status = "Soldé"
            elif float(paid or 0) <= 0.0001:
                status = "Impayé"
            else:
                status = "Partiel"

            self.v_id.setText(str(obligation_id))
            self.v_person.setText(person_name or "-")
            self.v_type.setText("Enseignant" if person_type == "TEACHER" else "Employé")
            self.v_period.setText(f"{MONTH_LABELS.get(int(month), month)} {year}")
            self.v_due.setText(f"{float(due or 0):,.0f} FCFA")
            self.v_paid.setText(f"{float(paid or 0):,.0f} FCFA")
            self.v_remaining.setText(f"{remaining:,.0f} FCFA")
            self.v_status.setText(status)
            self.v_establishment.setText(establishment or "-")
            self.v_created_at.setText("" if created_at is None else str(created_at))
            self.v_notes.setText(notes or "-")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
