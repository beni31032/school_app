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


class ClassDetailsDialog(QDialog):
    def __init__(self, class_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.class_id = int(class_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète classe")
        self.resize(760, 500)

        root = QVBoxLayout()

        title = QLabel("Fiche complète classe")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_name = QLabel("-")
        self.v_level = QLabel("-")
        self.v_cycle = QLabel("-")
        self.v_titular = QLabel("-")
        self.v_assistant = QLabel("-")
        self.v_est = QLabel("-")
        self.v_students = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Classe :", self.v_name)
        form.addRow("Niveau :", self.v_level)
        form.addRow("Cycle :", self.v_cycle)
        form.addRow("Titulaire :", self.v_titular)
        form.addRow("Assistant :", self.v_assistant)
        form.addRow("Établissement :", self.v_est)
        form.addRow("Effectif (année en cours) :", self.v_students)

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
                    c.id,
                    c.name,
                    c.level,
                    COALESCE(cy.name, ''),
                    COALESCE(t1.last_name || ' ' || t1.first_name, ''),
                    COALESCE(t2.last_name || ' ' || t2.first_name, ''),
                    e.name
                FROM classes c
                JOIN establishments e ON e.id = c.establishment_id
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                LEFT JOIN teachers t1 ON t1.id = c.titular_teacher_id
                LEFT JOIN teachers t2 ON t2.id = c.assistant_teacher_id
                WHERE c.id = %s
            """
            params = [self.class_id]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Classe introuvable.")
                return

            class_id, name, level, cycle_name, titular_name, assistant_name, est_name = row

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM enrollments
                WHERE class_id = %s
                  AND school_year_id = (
                      SELECT id
                      FROM school_years
                      ORDER BY id DESC
                      LIMIT 1
                  )
                """,
                (class_id,),
            )
            count_row = cursor.fetchone()
            count_students = count_row[0] if count_row else 0

            self.v_id.setText(str(class_id))
            self.v_name.setText(name or "-")
            self.v_level.setText(level or "-")
            self.v_cycle.setText(cycle_name or "-")
            self.v_titular.setText(titular_name or "-")
            self.v_assistant.setText(assistant_name or "-")
            self.v_est.setText(est_name or "-")
            self.v_students.setText(str(count_students))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
