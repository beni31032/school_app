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


class ClassSubjectDetailsDialog(QDialog):
    def __init__(self, class_subject_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.class_subject_id = int(class_subject_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complete matiere par classe")
        self.resize(760, 460)

        root = QVBoxLayout()

        title = QLabel("Fiche complete matiere par classe")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_class = QLabel("-")
        self.v_est = QLabel("-")
        self.v_subject = QLabel("-")
        self.v_coef = QLabel("-")
        self.v_cycle = QLabel("-")
        self.v_level = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Classe :", self.v_class)
        form.addRow("Etablissement :", self.v_est)
        form.addRow("Matiere :", self.v_subject)
        form.addRow("Coefficient :", self.v_coef)
        form.addRow("Cycle :", self.v_cycle)
        form.addRow("Niveau :", self.v_level)

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
                    cs.id,
                    c.name,
                    e.name,
                    s.name,
                    cs.coefficient,
                    COALESCE(cy.name, ''),
                    COALESCE(c.level, '')
                FROM class_subjects cs
                JOIN classes c ON c.id = cs.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN subjects s ON s.id = cs.subject_id
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                WHERE cs.id = %s
            """
            params = [self.class_subject_id]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Affectation introuvable.")
                return

            row_id, class_name, est_name, subject_name, coefficient, cycle_name, level = row
            self.v_id.setText(str(row_id))
            self.v_class.setText(class_name or "-")
            self.v_est.setText(est_name or "-")
            self.v_subject.setText(subject_name or "-")
            self.v_coef.setText(str(coefficient) if coefficient is not None else "-")
            self.v_cycle.setText(cycle_name or "-")
            self.v_level.setText(level or "-")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
