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


class AddTimetableDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        self.setWindowTitle("Ajouter emploi du temps")
        self.setFixedWidth(460)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.establishment_input = QComboBox()
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
        self.start_time_input.setTime(QTime(7, 30))
        self.end_time_input.setTime(QTime(8, 30))

        form.addRow("Établissement :", self.establishment_input)
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

        self.save_btn.clicked.connect(self.save_item)
        self.cancel_btn.clicked.connect(self.reject)
        self.establishment_input.currentIndexChanged.connect(self.load_dependent_data)

        self.load_base_data()

    def load_base_data(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.establishment_input.clear()
            if self.is_global_admin:
                cur.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cur.fetchall():
                    self.establishment_input.addItem(name, est_id)
            else:
                est_id = self.current_user["establishment_id"]
                cur.execute("SELECT id, name FROM establishments WHERE id=%s", (est_id,))
                row = cur.fetchone()
                if row:
                    self.establishment_input.addItem(row[1], row[0])
                self.establishment_input.setEnabled(False)

            self.school_year_input.clear()
            cur.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for sy_id, label in cur.fetchall():
                self.school_year_input.addItem(label, sy_id)

            self.load_dependent_data()
        finally:
            conn.close()

    def load_dependent_data(self):
        est_id = self.establishment_input.currentData()
        if est_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.class_input.clear()
            cur.execute(
                """
                SELECT id, name FROM classes
                WHERE establishment_id = %s
                ORDER BY name
                """,
                (est_id,),
            )
            for class_id, name in cur.fetchall():
                self.class_input.addItem(name, class_id)

            self.subject_input.clear()
            cur.execute(
                """
                SELECT id, name FROM subjects
                WHERE establishment_id = %s
                ORDER BY name
                """,
                (est_id,),
            )
            for subject_id, name in cur.fetchall():
                self.subject_input.addItem(name, subject_id)

            self.teacher_input.clear()
            cur.execute(
                """
                SELECT id, last_name || ' ' || first_name
                FROM teachers
                WHERE establishment_id = %s
                ORDER BY last_name, first_name
                """,
                (est_id,),
            )
            for teacher_id, name in cur.fetchall():
                self.teacher_input.addItem(name, teacher_id)
        finally:
            conn.close()

    def save_item(self):
        est_id = self.establishment_input.currentData()
        school_year_id = self.school_year_input.currentData()
        class_id = self.class_input.currentData()
        subject_id = self.subject_input.currentData()
        teacher_id = self.teacher_input.currentData()
        day = self.day_input.currentText()
        start_time = self.start_time_input.time().toString("HH:mm")
        end_time = self.end_time_input.time().toString("HH:mm")

        if not all([est_id, school_year_id, class_id, subject_id, teacher_id]):
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
            cur.execute(
                """
                SELECT 1
                FROM timetables
                WHERE class_id=%s AND school_year_id=%s AND day_of_week=%s
                  AND NOT (end_time <= %s::time OR start_time >= %s::time)
                LIMIT 1
                """,
                (class_id, school_year_id, day, start_time, end_time),
            )
            if cur.fetchone():
                QMessageBox.warning(self, "Validation", "Conflit d'horaire pour cette classe.")
                return

            cur.execute(
                """
                INSERT INTO timetables (
                    establishment_id, school_year_id, class_id, subject_id,
                    teacher_id, day_of_week, start_time, end_time
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (est_id, school_year_id, class_id, subject_id, teacher_id, day, start_time, end_time),
            )
            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()
