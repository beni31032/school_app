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


class TeacherAssignmentDetailsDialog(QDialog):
    def __init__(self, assignment_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.assignment_id = int(assignment_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète affectation")
        self.resize(760, 460)

        root = QVBoxLayout()

        title = QLabel("Fiche complète affectation")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_teacher = QLabel("-")
        self.v_subject = QLabel("-")
        self.v_class = QLabel("-")
        self.v_est = QLabel("-")
        self.v_year = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Enseignant :", self.v_teacher)
        form.addRow("Matière :", self.v_subject)
        form.addRow("Classe :", self.v_class)
        form.addRow("Établissement :", self.v_est)
        form.addRow("Année scolaire :", self.v_year)

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
                    ta.id,
                    t.last_name || ' ' || t.first_name,
                    s.name,
                    c.name,
                    e.name,
                    sy.name
                FROM teacher_assignments ta
                JOIN teachers t ON t.id = ta.teacher_id
                JOIN subjects s ON s.id = ta.subject_id
                JOIN classes c ON c.id = ta.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN school_years sy ON sy.id = ta.school_year_id
                WHERE ta.id = %s
            """
            params = [self.assignment_id]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Affectation introuvable.")
                return

            assignment_id, teacher_name, subject_name, class_name, est_name, year_name = row
            self.v_id.setText(str(assignment_id))
            self.v_teacher.setText(teacher_name or "-")
            self.v_subject.setText(subject_name or "-")
            self.v_class.setText(class_name or "-")
            self.v_est.setText(est_name or "-")
            self.v_year.setText(year_name or "-")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
