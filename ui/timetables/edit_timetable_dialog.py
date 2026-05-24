from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from database.connection import get_connection
from utils.message_boxes import show_error_dialog
from utils.subject_service import ensure_subject_schema
from utils.teacher_service import ensure_teacher_schema


class EditTimetableDialog(QDialog):
    def __init__(self, timetable_id, current_user, parent=None):
        super().__init__(parent)
        self.timetable_id = int(timetable_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_teacher_schema()
        ensure_subject_schema()

        self.setWindowTitle("Modifier emploi du temps")
        self.setFixedWidth(460)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.school_year_input = QComboBox()
        self.class_input = QComboBox()
        self.subject_input = QComboBox()
        self.teacher_input = QComboBox()
        self.day_input = QComboBox()
        self.start_time_input = QTimeEdit()
        self.end_time_input = QTimeEdit()

        for day_value, day_label in [
            (1, "Lundi"),
            (2, "Mardi"),
            (3, "Mercredi"),
            (4, "Jeudi"),
            (5, "Vendredi"),
            (6, "Samedi"),
        ]:
            self.day_input.addItem(day_label, day_value)
        self.start_time_input.setDisplayFormat("HH:mm")
        self.end_time_input.setDisplayFormat("HH:mm")

        form.addRow("Année scolaire :", self.school_year_input)
        form.addRow("Classe :", self.class_input)
        form.addRow("Matière :", self.subject_input)
        form.addRow("Enseignant :", self.teacher_input)
        form.addRow("Jour :", self.day_input)
        form.addRow("Début :", self.start_time_input)
        form.addRow("Fin :", self.end_time_input)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")
        btns.addWidget(self.save_btn)
        btns.addWidget(self.cancel_btn)

        layout.addLayout(form)
        layout.addLayout(btns)
        self.setLayout(layout)
        self.apply_local_styles()

        self.save_btn.clicked.connect(self.update_item)
        self.cancel_btn.clicked.connect(self.reject)
        self.class_input.currentIndexChanged.connect(lambda _: self.load_subjects_for_selected_class())

        self.load_data()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 135px;
            }
            QComboBox, QTimeEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            """
        )

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            self.reject()
            return
        try:
            cur = conn.cursor()
            if self.is_global_admin:
                cur.execute(
                    """
                    SELECT establishment_id, school_year_id, class_id, subject_id, teacher_id,
                           day_of_week, start_time, end_time
                    FROM timetables
                    WHERE id=%s
                    """,
                    (self.timetable_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT establishment_id, school_year_id, class_id, subject_id, teacher_id,
                           day_of_week, start_time, end_time
                    FROM timetables
                    WHERE id=%s AND establishment_id=%s
                    """,
                    (self.timetable_id, self.current_user["establishment_id"]),
                )
            row = cur.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Ligne introuvable")
                self.reject()
                return

            est_id, school_year_id, class_id, subject_id, teacher_id, day, start_time, end_time = row

            self.school_year_input.clear()
            cur.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for sy_id, label in cur.fetchall():
                self.school_year_input.addItem(label, sy_id)
            self._select_combo(self.school_year_input, school_year_id)

            self.class_input.clear()
            cur.execute("SELECT id, name FROM classes WHERE establishment_id=%s ORDER BY name", (est_id,))
            for c_id, name in cur.fetchall():
                self.class_input.addItem(name, c_id)
            self._select_combo(self.class_input, class_id)

            self.load_subjects_for_selected_class(selected_subject_id=subject_id)

            self.teacher_input.clear()
            cur.execute(
                """
                SELECT
                    id,
                    last_name || ' ' || first_name ||
                    CASE WHEN COALESCE(is_active, TRUE) THEN '' ELSE ' (Inactif)' END
                FROM teachers
                WHERE establishment_id=%s
                ORDER BY COALESCE(is_active, TRUE) DESC, last_name, first_name
                """,
                (est_id,),
            )
            for t_id, name in cur.fetchall():
                self.teacher_input.addItem(name, t_id)
            self._select_combo(self.teacher_input, teacher_id)

            self._select_day(day)
            self.start_time_input.setTime(self._to_qtime(start_time))
            self.end_time_input.setTime(self._to_qtime(end_time))
        except Exception as e:
            show_error_dialog(self, "Erreur", "Chargement impossible.", e)
            self.reject()
        finally:
            conn.close()

    def _select_combo(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _select_day(self, day):
        normalized_day = {
            "1": "Lundi",
            "2": "Mardi",
            "3": "Mercredi",
            "4": "Jeudi",
            "5": "Vendredi",
            "6": "Samedi",
            "7": "Dimanche",
        }.get(str(day), str(day))
        numeric_day = {
            "Lundi": 1,
            "Mardi": 2,
            "Mercredi": 3,
            "Jeudi": 4,
            "Vendredi": 5,
            "Samedi": 6,
            "Dimanche": 7,
        }.get(normalized_day)
        idx = self.day_input.findData(numeric_day)
        if idx < 0:
            idx = self.day_input.findText(normalized_day)
        if idx >= 0:
            self.day_input.setCurrentIndex(idx)

    def _to_qtime(self, value):
        if hasattr(value, "hour") and hasattr(value, "minute"):
            return QTime(value.hour, value.minute)

        text_value = str(value or "")
        for time_format in ("HH:mm:ss", "HH:mm"):
            parsed = QTime.fromString(text_value, time_format)
            if parsed.isValid():
                return parsed
        return QTime(7, 30)

    def load_subjects_for_selected_class(self, selected_subject_id=None):
        self.subject_input.clear()
        class_id = self.class_input.currentData()
        if class_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.id, s.name
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.class_id = %s
                ORDER BY s.name
                """,
                (class_id,),
            )
            rows = cur.fetchall()
            selected_index = 0
            for index, (subject_id, name) in enumerate(rows):
                self.subject_input.addItem(name, subject_id)
                if selected_subject_id is not None and subject_id == selected_subject_id:
                    selected_index = index

            if self.subject_input.count() > 0:
                self.subject_input.setCurrentIndex(selected_index)
        except Exception as e:
            show_error_dialog(self, "Erreur", "Chargement des matières impossible.", e)
        finally:
            conn.close()

    def update_item(self):
        school_year_id = self.school_year_input.currentData()
        class_id = self.class_input.currentData()
        subject_id = self.subject_input.currentData()
        teacher_id = self.teacher_input.currentData()
        day = self.day_input.currentData()
        start_time = self.start_time_input.time().toPyTime()
        end_time = self.end_time_input.time().toPyTime()

        if not all([school_year_id, class_id, subject_id, teacher_id]):
            QMessageBox.warning(self, "Validation", "Tous les champs sont obligatoires.")
            return

        if self.start_time_input.time() >= self.end_time_input.time():
            QMessageBox.warning(self, "Validation", "L'heure de fin doit être après l'heure de début.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cur = conn.cursor()
            if self.is_global_admin:
                cur.execute("SELECT establishment_id FROM timetables WHERE id=%s", (self.timetable_id,))
            else:
                cur.execute(
                    "SELECT establishment_id FROM timetables WHERE id=%s AND establishment_id=%s",
                    (self.timetable_id, self.current_user["establishment_id"]),
                )
            row = cur.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Ligne introuvable")
                return
            est_id = row[0]

            cur.execute(
                """
                SELECT 1
                FROM timetables
                WHERE id <> %s
                  AND class_id=%s AND school_year_id=%s AND day_of_week=%s
                  AND NOT (end_time <= %s OR start_time >= %s)
                LIMIT 1
                """,
                (self.timetable_id, class_id, school_year_id, day, start_time, end_time),
            )
            if cur.fetchone():
                QMessageBox.warning(self, "Validation", "Conflit d'horaire pour cette classe.")
                return

            cur.execute(
                """
                SELECT 1
                FROM timetables
                WHERE id <> %s
                  AND teacher_id=%s AND school_year_id=%s AND day_of_week=%s
                  AND NOT (end_time <= %s OR start_time >= %s)
                LIMIT 1
                """,
                (self.timetable_id, teacher_id, school_year_id, day, start_time, end_time),
            )
            if cur.fetchone():
                QMessageBox.warning(self, "Validation", "Conflit d'horaire pour cet enseignant.")
                return

            if self.is_global_admin:
                cur.execute(
                    """
                    UPDATE timetables
                    SET school_year_id=%s, class_id=%s, subject_id=%s, teacher_id=%s,
                        day_of_week=%s, start_time=%s, end_time=%s
                    WHERE id=%s
                    """,
                    (school_year_id, class_id, subject_id, teacher_id, day, start_time, end_time, self.timetable_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE timetables
                    SET school_year_id=%s, class_id=%s, subject_id=%s, teacher_id=%s,
                        day_of_week=%s, start_time=%s, end_time=%s
                    WHERE id=%s AND establishment_id=%s
                    """,
                    (school_year_id, class_id, subject_id, teacher_id, day, start_time, end_time, self.timetable_id, est_id),
                )

            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            show_error_dialog(self, "Erreur", "Mise à jour impossible.", e)
        finally:
            conn.close()
