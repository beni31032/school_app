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
from utils.subject_service import ensure_subject_schema


class SubjectDetailsDialog(QDialog):
    def __init__(self, subject_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.subject_id = int(subject_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"
        ensure_subject_schema()

        self.setWindowTitle("Fiche complete matiere")
        self.resize(700, 420)

        root = QVBoxLayout()

        title = QLabel("Fiche complete matiere")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_name = QLabel("-")
        self.v_est = QLabel("-")
        self.v_class_count = QLabel("-")
        self.v_teacher_count = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Matiere :", self.v_name)
        form.addRow("Etablissement :", self.v_est)
        form.addRow("Classes associees :", self.v_class_count)
        form.addRow("Affectations enseignants :", self.v_teacher_count)

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
                    s.id,
                    s.name,
                    COALESCE(e.name, '-')
                FROM subjects s
                LEFT JOIN establishments e ON e.id = s.establishment_id
                WHERE s.id = %s
            """
            params = [self.subject_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Matiere introuvable.")
                return

            subject_id, name, est_name = row

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM class_subjects
                WHERE subject_id = %s
                """,
                (subject_id,),
            )
            class_count_row = cursor.fetchone()
            class_count = class_count_row[0] if class_count_row else 0

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM teacher_assignments
                WHERE subject_id = %s
                """,
                (subject_id,),
            )
            teacher_count_row = cursor.fetchone()
            teacher_count = teacher_count_row[0] if teacher_count_row else 0

            self.v_id.setText(str(subject_id))
            self.v_name.setText(name or "-")
            self.v_est.setText(est_name or "-")
            self.v_class_count.setText(str(class_count))
            self.v_teacher_count.setText(str(teacher_count))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
