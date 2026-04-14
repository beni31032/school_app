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


class EditTimetableDialog(QDialog):
    def __init__(self, timetable_id, current_user, parent=None):
        super().__init__(parent)
        self.timetable_id = int(timetable_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

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

        self.day_input.addItems(["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"])
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

        self.save_btn.clicked.connect(self.update_item)
        self.cancel_btn.clicked.connect(self.reject)

        self.load_data()

    def load_data(self):
        conn = get_connection()
        if not conn:
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

            self.subject_input.clear()
            cur.execute("SELECT id, name FROM subjects WHERE establishment_id=%s ORDER BY name", (est_id,))
            for s_id, name in cur.fetchall():
                self.subject_input.addItem(name, s_id)
            self._select_combo(self.subject_input, subject_id)

            self.teacher_input.clear()
            cur.execute(
                "SELECT id, last_name || ' ' || first_name FROM teachers WHERE establishment_id=%s ORDER BY last_name, first_name",
                (est_id,),
            )
            for t_id, name in cur.fetchall():
                self.teacher_input.addItem(name, t_id)
            self._select_combo(self.teacher_input, teacher_id)

            self._select_day(day)
            self.start_time_input.setTime(QTime(start_time.hour, start_time.minute))
            self.end_time_input.setTime(QTime(end_time.hour, end_time.minute))
        finally:
            conn.close()

    def _select_combo(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _select_day(self, day):
        idx = self.day_input.findText(day)
        if idx >= 0:
            self.day_input.setCurrentIndex(idx)

    def update_item(self):
        school_year_id = self.school_year_input.currentData()
        class_id = self.class_input.currentData()
        subject_id = self.subject_input.currentData()
        teacher_id = self.teacher_input.currentData()
        day = self.day_input.currentText()
        start_time = self.start_time_input.time().toString("HH:mm")
        end_time = self.end_time_input.time().toString("HH:mm")

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
                  AND NOT (end_time <= %s::time OR start_time >= %s::time)
                LIMIT 1
                """,
                (self.timetable_id, class_id, school_year_id, day, start_time, end_time),
            )
            if cur.fetchone():
                QMessageBox.warning(self, "Validation", "Conflit d'horaire pour cette classe.")
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
            QMessageBox.critical(self, "Erreur", f"Mise à jour impossible : {e}")
        finally:
            conn.close()
