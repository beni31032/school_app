from PyQt6.QtCore import Qt
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


class StaffDetailsDialog(QDialog):
    def __init__(self, staff_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.staff_id = int(staff_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète employé")
        self.resize(700, 460)

        root = QVBoxLayout()

        title = QLabel("Fiche complète employé")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_nom = QLabel("-")
        self.v_prenom = QLabel("-")
        self.v_poste = QLabel("-")
        self.v_phone = QLabel("-")
        self.v_email = QLabel("-")
        self.v_hire_date = QLabel("-")
        self.v_est = QLabel("-")
        self.v_status = QLabel("-")
        self.v_created_at = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Nom :", self.v_nom)
        form.addRow("Prénom :", self.v_prenom)
        form.addRow("Poste :", self.v_poste)
        form.addRow("Téléphone :", self.v_phone)
        form.addRow("Email :", self.v_email)
        form.addRow("Date d'embauche :", self.v_hire_date)
        form.addRow("Établissement :", self.v_est)
        form.addRow("Statut :", self.v_status)
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

        self.apply_local_styles()
        self.load_details()

    def apply_local_styles(self):
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

    def load_details(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    sm.id,
                    sm.last_name,
                    sm.first_name,
                    sm.role_title,
                    sm.phone,
                    sm.email,
                    sm.hire_date,
                    e.name,
                    COALESCE(sm.is_active, TRUE),
                    sm.created_at
                FROM staff_members sm
                JOIN establishments e ON e.id = sm.establishment_id
                WHERE sm.id = %s
            """
            params = [self.staff_id]
            if not self.is_global_admin:
                sql += " AND sm.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Employé introuvable.")
                return

            sid, nom, prenom, poste, phone, email, hire_date, est_name, is_active, created_at = row
            self.v_id.setText(str(sid))
            self.v_nom.setText(nom or "-")
            self.v_prenom.setText(prenom or "-")
            self.v_poste.setText(poste or "-")
            self.v_phone.setText(phone or "-")
            self.v_email.setText(email or "-")
            self.v_hire_date.setText(str(hire_date) if hire_date else "-")
            self.v_est.setText(est_name or "-")
            self.v_status.setText("Actif" if is_active else "Inactif")
            self.v_created_at.setText(str(created_at) if created_at else "-")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
