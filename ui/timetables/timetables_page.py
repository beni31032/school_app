from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QComboBox,
    QLabel,
)

from database.connection import get_connection
from ui.timetables.add_timetable_dialog import AddTimetableDialog
from ui.timetables.edit_timetable_dialog import EditTimetableDialog
from utils.table_style import setup_table
from utils.timetable_service import ensure_timetables_table


class TimetablesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_timetables_table()

        layout = QVBoxLayout()

        filters = QHBoxLayout()
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()
        self.class_filter = QComboBox()

        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Année"))
        filters.addWidget(self.school_year_filter)
        filters.addWidget(QLabel("Classe"))
        filters.addWidget(self.class_filter)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.delete_btn = QPushButton("Supprimer")
        self.refresh_btn = QPushButton("Actualiser")

        btns.addWidget(self.add_btn)
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Classe",
                "Matière",
                "Enseignant",
                "Jour",
                "Début",
                "Fin",
                "Année scolaire",
                "Établissement",
            ]
        )
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        layout.addLayout(filters)
        layout.addLayout(btns)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.setStyleSheet("QLabel { color: #111827; font-weight: 600; }")

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.delete_btn.clicked.connect(self.delete_item)
        self.refresh_btn.clicked.connect(self.load_rows)
        self.establishment_filter.currentIndexChanged.connect(self.load_classes_for_filter)
        self.establishment_filter.currentIndexChanged.connect(self.load_rows)
        self.school_year_filter.currentIndexChanged.connect(self.load_rows)
        self.class_filter.currentIndexChanged.connect(self.load_rows)

        self.load_filters()
        self.load_rows()

    def load_filters(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.establishment_filter.clear()
            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cur.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cur.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                est_id = self.current_user["establishment_id"]
                cur.execute("SELECT id, name FROM establishments WHERE id=%s", (est_id,))
                row = cur.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)

            self.school_year_filter.clear()
            self.school_year_filter.addItem("Toutes", None)
            cur.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for sy_id, label in cur.fetchall():
                self.school_year_filter.addItem(label, sy_id)

            self.load_classes_for_filter()
        finally:
            conn.close()

    def load_classes_for_filter(self):
        est_id = self.establishment_filter.currentData()

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            self.class_filter.blockSignals(True)
            self.class_filter.clear()
            self.class_filter.addItem("Toutes", None)
            if est_id is None and self.is_global_admin:
                cur.execute("SELECT id, name FROM classes ORDER BY name")
            else:
                cur.execute("SELECT id, name FROM classes WHERE establishment_id=%s ORDER BY name", (est_id,))
            for class_id, name in cur.fetchall():
                self.class_filter.addItem(name, class_id)
            self.class_filter.blockSignals(False)
        finally:
            conn.close()

    def load_rows(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        est_id = self.establishment_filter.currentData()
        school_year_id = self.school_year_filter.currentData()
        class_id = self.class_filter.currentData()

        try:
            cur = conn.cursor()
            where = []
            params = []

            if self.is_global_admin:
                if est_id is not None:
                    where.append("t.establishment_id = %s")
                    params.append(est_id)
            else:
                where.append("t.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if school_year_id is not None:
                where.append("t.school_year_id = %s")
                params.append(school_year_id)
            if class_id is not None:
                where.append("t.class_id = %s")
                params.append(class_id)

            where_sql = " WHERE " + " AND ".join(where) if where else ""

            cur.execute(
                f"""
                SELECT
                    t.id,
                    c.name,
                    s.name,
                    tr.last_name || ' ' || tr.first_name AS teacher_name,
                    CASE
                        WHEN t.day_of_week::text IN ('1', 'Lundi') THEN 'Lundi'
                        WHEN t.day_of_week::text IN ('2', 'Mardi') THEN 'Mardi'
                        WHEN t.day_of_week::text IN ('3', 'Mercredi') THEN 'Mercredi'
                        WHEN t.day_of_week::text IN ('4', 'Jeudi') THEN 'Jeudi'
                        WHEN t.day_of_week::text IN ('5', 'Vendredi') THEN 'Vendredi'
                        WHEN t.day_of_week::text IN ('6', 'Samedi') THEN 'Samedi'
                        WHEN t.day_of_week::text IN ('7', 'Dimanche') THEN 'Dimanche'
                        ELSE t.day_of_week::text
                    END AS day_label,
                    to_char(t.start_time, 'HH24:MI'),
                    to_char(t.end_time, 'HH24:MI'),
                    sy.name,
                    e.name
                FROM timetables t
                JOIN classes c ON c.id = t.class_id
                JOIN subjects s ON s.id = t.subject_id
                JOIN teachers tr ON tr.id = t.teacher_id
                JOIN school_years sy ON sy.id = t.school_year_id
                JOIN establishments e ON e.id = t.establishment_id
                {where_sql}
                ORDER BY e.name, c.name, sy.id DESC,
                         CASE
                           WHEN t.day_of_week::text IN ('1', 'Lundi') THEN 1
                           WHEN t.day_of_week::text IN ('2', 'Mardi') THEN 2
                           WHEN t.day_of_week::text IN ('3', 'Mercredi') THEN 3
                           WHEN t.day_of_week::text IN ('4', 'Jeudi') THEN 4
                           WHEN t.day_of_week::text IN ('5', 'Vendredi') THEN 5
                           WHEN t.day_of_week::text IN ('6', 'Samedi') THEN 6
                           WHEN t.day_of_week::text IN ('7', 'Dimanche') THEN 7
                           ELSE 9
                         END,
                         t.start_time
                """,
                params,
            )
            rows = cur.fetchall()
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem("" if val is None else str(val)))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddTimetableDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_rows()

    def open_edit_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez une ligne.")
            return
        timetable_id_item = self.table.item(row, 0)
        if not timetable_id_item:
            return
        dialog = EditTimetableDialog(timetable_id_item.text(), current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_rows()

    def delete_item(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez une ligne.")
            return
        timetable_id_item = self.table.item(row, 0)
        if not timetable_id_item:
            return

        if QMessageBox.question(
            self,
            "Confirmation",
            "Supprimer cet emploi du temps ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cur = conn.cursor()
            if self.is_global_admin:
                cur.execute("DELETE FROM timetables WHERE id=%s", (int(timetable_id_item.text()),))
            else:
                cur.execute(
                    "DELETE FROM timetables WHERE id=%s AND establishment_id=%s",
                    (int(timetable_id_item.text()), self.current_user["establishment_id"]),
                )
            conn.commit()
            self.load_rows()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Suppression impossible : {e}")
        finally:
            conn.close()
