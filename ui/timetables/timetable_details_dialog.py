from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from database.connection import get_connection


class TimetableDetailsDialog(QDialog):
    def __init__(self, timetable_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.timetable_id = int(timetable_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète emploi du temps")
        self.resize(760, 500)

        root = QVBoxLayout()

        title = QLabel("Fiche complète emploi du temps")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(9)

        self.v_id = QLabel("-")
        self.v_est = QLabel("-")
        self.v_class = QLabel("-")
        self.v_subject = QLabel("-")
        self.v_teacher = QLabel("-")
        self.v_day = QLabel("-")
        self.v_start = QLabel("-")
        self.v_end = QLabel("-")
        self.v_year = QLabel("-")
        self.v_duration = QLabel("-")

        form.addRow("ID :", self.v_id)
        form.addRow("Établissement :", self.v_est)
        form.addRow("Classe :", self.v_class)
        form.addRow("Matière :", self.v_subject)
        form.addRow("Enseignant :", self.v_teacher)
        form.addRow("Jour :", self.v_day)
        form.addRow("Début :", self.v_start)
        form.addRow("Fin :", self.v_end)
        form.addRow("Durée :", self.v_duration)
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
                    t.id,
                    e.name,
                    c.name,
                    s.name,
                    COALESCE(tr.last_name || ' ' || tr.first_name, '-'),
                    CASE
                        WHEN t.day_of_week::text IN ('1', 'Lundi') THEN 'Lundi'
                        WHEN t.day_of_week::text IN ('2', 'Mardi') THEN 'Mardi'
                        WHEN t.day_of_week::text IN ('3', 'Mercredi') THEN 'Mercredi'
                        WHEN t.day_of_week::text IN ('4', 'Jeudi') THEN 'Jeudi'
                        WHEN t.day_of_week::text IN ('5', 'Vendredi') THEN 'Vendredi'
                        WHEN t.day_of_week::text IN ('6', 'Samedi') THEN 'Samedi'
                        WHEN t.day_of_week::text IN ('7', 'Dimanche') THEN 'Dimanche'
                        ELSE t.day_of_week::text
                    END,
                    to_char(t.start_time, 'HH24:MI'),
                    to_char(t.end_time, 'HH24:MI'),
                    to_char(t.end_time - t.start_time, 'HH24:MI'),
                    sy.name
                FROM timetables t
                JOIN establishments e ON e.id = t.establishment_id
                JOIN classes c ON c.id = t.class_id
                JOIN subjects s ON s.id = t.subject_id
                LEFT JOIN teachers tr ON tr.id = t.teacher_id
                JOIN school_years sy ON sy.id = t.school_year_id
                WHERE t.id = %s
            """
            params = [self.timetable_id]

            if not self.is_global_admin:
                sql += " AND t.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Emploi du temps introuvable.")
                return

            (
                timetable_id,
                establishment_name,
                class_name,
                subject_name,
                teacher_name,
                day_label,
                start_time,
                end_time,
                duration,
                school_year_name,
            ) = row

            self.v_id.setText(str(timetable_id))
            self.v_est.setText(establishment_name or "-")
            self.v_class.setText(class_name or "-")
            self.v_subject.setText(subject_name or "-")
            self.v_teacher.setText(teacher_name or "-")
            self.v_day.setText(day_label or "-")
            self.v_start.setText(start_time or "-")
            self.v_end.setText(end_time or "-")
            self.v_duration.setText(duration or "-")
            self.v_year.setText(school_year_name or "-")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
