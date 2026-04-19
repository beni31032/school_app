import os
import subprocess
import sys
from datetime import datetime

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
    QLineEdit,
    QFrame,
    QFormLayout,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.connection import get_connection
from ui.timetables.add_timetable_dialog import AddTimetableDialog
from ui.timetables.edit_timetable_dialog import EditTimetableDialog
from ui.timetables.timetable_details_dialog import TimetableDetailsDialog
from utils.subject_service import ensure_subject_schema
from utils.table_style import setup_table
from utils.teacher_service import ensure_teacher_schema
from utils.timetable_service import ensure_timetables_table


class TimetablesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_timetables_table()
        ensure_teacher_schema()
        ensure_subject_schema()

        layout = QVBoxLayout()

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()
        self.class_filter = QComboBox()
        self.day_filter = QComboBox()
        self.current_schedule_rows = []
        self.current_schedule_class_name = "-"
        self.current_schedule_year_name = "-"
        self.current_schedule_establishment_name = "-"

        filters.addWidget(QLabel("Recherche"))
        filters.addWidget(self.search_input)
        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Année"))
        filters.addWidget(self.school_year_filter)
        filters.addWidget(QLabel("Classe"))
        filters.addWidget(self.class_filter)
        filters.addWidget(QLabel("Jour"))
        filters.addWidget(self.day_filter)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.details_btn = QPushButton("Voir fiche complète")
        self.delete_btn = QPushButton("Supprimer")
        self.refresh_btn = QPushButton("Actualiser")
        self.preview_btn = QPushButton("Aperçu PDF")
        self.print_btn = QPushButton("Imprimer")

        btns.addWidget(self.add_btn)
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.details_btn)
        btns.addWidget(self.delete_btn)
        btns.addWidget(self.refresh_btn)
        btns.addWidget(self.preview_btn)
        btns.addWidget(self.print_btn)

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

        self.schedule_title = QLabel("Tableau hebdomadaire")
        self.schedule_title.setObjectName("scheduleTitle")
        self.schedule_hint = QLabel("Sélectionne une classe pour afficher son emploi du temps sous forme de tableau.")
        self.schedule_hint.setObjectName("scheduleHint")

        self.weekly_table = QTableWidget()
        self.weekly_table.setColumnCount(7)
        self.weekly_table.setHorizontalHeaderLabels(["Horaire", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"])
        self.weekly_table.verticalHeader().setVisible(False)
        self.weekly_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.weekly_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.weekly_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.weekly_table.setWordWrap(True)
        self.weekly_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.weekly_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.details_card = QFrame()
        self.details_card.setObjectName("timetableDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_est = QLabel("-")
        self.d_class = QLabel("-")
        self.d_subject = QLabel("-")
        self.d_teacher = QLabel("-")
        self.d_day = QLabel("-")
        self.d_start = QLabel("-")
        self.d_end = QLabel("-")
        self.d_year = QLabel("-")

        details_layout.addRow("Établissement :", self.d_est)
        details_layout.addRow("Classe :", self.d_class)
        details_layout.addRow("Matière :", self.d_subject)
        details_layout.addRow("Enseignant :", self.d_teacher)
        details_layout.addRow("Jour :", self.d_day)
        details_layout.addRow("Début :", self.d_start)
        details_layout.addRow("Fin :", self.d_end)
        details_layout.addRow("Année scolaire :", self.d_year)

        layout.addLayout(filters)
        layout.addLayout(btns)
        layout.addWidget(self.table)
        layout.addWidget(self.schedule_title)
        layout.addWidget(self.schedule_hint)
        layout.addWidget(self.weekly_table)
        layout.addWidget(self.details_card)
        self.setLayout(layout)
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QLabel#scheduleTitle {
                font-size: 18px;
                font-weight: 800;
                padding-top: 6px;
            }
            QLabel#scheduleHint {
                color: #475569;
                font-weight: 500;
                padding-bottom: 4px;
            }
            QFrame#timetableDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.delete_btn.clicked.connect(self.delete_item)
        self.refresh_btn.clicked.connect(self.load_rows)
        self.preview_btn.clicked.connect(self.preview_weekly_schedule_pdf)
        self.print_btn.clicked.connect(self.print_weekly_schedule)
        self.search_input.textChanged.connect(self.load_rows)
        self.establishment_filter.currentIndexChanged.connect(self.load_classes_for_filter)
        self.establishment_filter.currentIndexChanged.connect(self.load_rows)
        self.school_year_filter.currentIndexChanged.connect(self.load_rows)
        self.class_filter.currentIndexChanged.connect(self.load_rows)
        self.day_filter.currentIndexChanged.connect(self.load_rows)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

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

            self.day_filter.clear()
            self.day_filter.addItem("Tous", None)
            for day_label in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]:
                self.day_filter.addItem(day_label, day_label)

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
        day_value = self.day_filter.currentData()
        search = f"%{self.search_input.text().strip()}%"

        try:
            cur = conn.cursor()
            where = [
                "(c.name ILIKE %s OR s.name ILIKE %s OR COALESCE(tr.last_name,'') ILIKE %s OR COALESCE(tr.first_name,'') ILIKE %s)"
            ]
            params = [search, search, search, search]

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
            if day_value is not None:
                where.append("t.day_of_week::text IN (%s, %s)")
                day_index = {
                    "Lundi": "1",
                    "Mardi": "2",
                    "Mercredi": "3",
                    "Jeudi": "4",
                    "Vendredi": "5",
                    "Samedi": "6",
                    "Dimanche": "7",
                }.get(day_value, day_value)
                params.extend([day_index, day_value])

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
                    item = QTableWidgetItem("" if val is None else str(val))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, j, item)
            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()
            self.load_weekly_schedule()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def clear_details(self):
        self.d_est.setText("-")
        self.d_class.setText("-")
        self.d_subject.setText("-")
        self.d_teacher.setText("-")
        self.d_day.setText("-")
        self.d_start.setText("-")
        self.d_end.setText("-")
        self.d_year.setText("-")

    def load_selected_details(self):
        row = self.table.currentRow()
        if row < 0:
            self.clear_details()
            return

        timetable_id_item = self.table.item(row, 0)
        if not timetable_id_item:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cur = conn.cursor()
            sql = """
                SELECT
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
                    sy.name
                FROM timetables t
                JOIN establishments e ON e.id = t.establishment_id
                JOIN classes c ON c.id = t.class_id
                JOIN subjects s ON s.id = t.subject_id
                LEFT JOIN teachers tr ON tr.id = t.teacher_id
                JOIN school_years sy ON sy.id = t.school_year_id
                WHERE t.id = %s
            """
            params = [int(timetable_id_item.text())]
            if not self.is_global_admin:
                sql += " AND t.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cur.execute(sql, params)
            row = cur.fetchone()
            if not row:
                self.clear_details()
                return

            (
                establishment_name,
                class_name,
                subject_name,
                teacher_name,
                day_label,
                start_time,
                end_time,
                school_year_name,
            ) = row

            self.d_est.setText(establishment_name or "-")
            self.d_class.setText(class_name or "-")
            self.d_subject.setText(subject_name or "-")
            self.d_teacher.setText(teacher_name or "-")
            self.d_day.setText(day_label or "-")
            self.d_start.setText(start_time or "-")
            self.d_end.setText(end_time or "-")
            self.d_year.setText(school_year_name or "-")
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

    def open_details_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez une ligne.")
            return
        timetable_id_item = self.table.item(row, 0)
        if not timetable_id_item:
            return
        dialog = TimetableDetailsDialog(int(timetable_id_item.text()), current_user=self.current_user, parent=self)
        dialog.exec()

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

    def load_weekly_schedule(self):
        class_id = self.class_filter.currentData()
        school_year_id = self.school_year_filter.currentData()

        self.weekly_table.clearContents()
        self.weekly_table.setRowCount(0)
        self.weekly_table.clearSpans()
        self.weekly_table.setColumnCount(7)
        self.weekly_table.setHorizontalHeaderLabels(["Horaire", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"])
        self.current_schedule_rows = []
        self.current_schedule_class_name = "-"
        self.current_schedule_year_name = "-"
        self.current_schedule_establishment_name = self.establishment_filter.currentText() or "-"

        if class_id is None:
            self.schedule_hint.setText("Sélectionne une classe pour afficher son emploi du temps sous forme de tableau.")
            return

        conn = get_connection()
        if not conn:
            self.schedule_hint.setText("Impossible de charger le tableau hebdomadaire.")
            return

        try:
            cur = conn.cursor()
            params = [class_id]
            where = ["t.class_id = %s"]

            if school_year_id is not None:
                where.append("t.school_year_id = %s")
                params.append(school_year_id)

            if self.is_global_admin:
                establishment_id = self.establishment_filter.currentData()
                if establishment_id is not None:
                    where.append("t.establishment_id = %s")
                    params.append(establishment_id)
            else:
                where.append("t.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            cur.execute(
                f"""
                SELECT
                    c.name,
                    COALESCE(sy.name, '-'),
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
                    to_char(t.start_time, 'HH24:MI') AS start_label,
                    to_char(t.end_time, 'HH24:MI') AS end_label,
                    s.name AS subject_name,
                    COALESCE(tr.last_name || ' ' || tr.first_name, '') AS teacher_name
                FROM timetables t
                JOIN classes c ON c.id = t.class_id
                JOIN subjects s ON s.id = t.subject_id
                LEFT JOIN teachers tr ON tr.id = t.teacher_id
                LEFT JOIN school_years sy ON sy.id = t.school_year_id
                WHERE {" AND ".join(where)}
                ORDER BY
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
                    t.start_time,
                    t.end_time
                """,
                params,
            )
            rows = cur.fetchall()

            if not rows:
                self.schedule_hint.setText("Aucun créneau trouvé pour cette classe avec les filtres actuels.")
                return

            class_name = rows[0][0]
            school_year_name = rows[0][1]
            self.current_schedule_class_name = class_name or "-"
            self.current_schedule_year_name = school_year_name or "-"
            self.schedule_hint.setText(f"Emploi du temps de {class_name} | Année scolaire : {school_year_name}")

            days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
            day_to_column = {day: index + 1 for index, day in enumerate(days)}

            slot_pairs = []
            for _, _, day_label, start_label, end_label, subject_name, teacher_name in rows:
                slot_pairs.append((start_label, end_label))

            unique_pairs = sorted(set(slot_pairs), key=lambda pair: (pair[0], pair[1]))
            slots = [f"{start_label} - {end_label}" for start_label, end_label in unique_pairs]
            slot_map = {slot_label: index for index, slot_label in enumerate(slots)}

            self.weekly_table.setRowCount(len(slots))
            for row_index, slot_label in enumerate(slots):
                slot_item = QTableWidgetItem(slot_label)
                slot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                slot_item.setFlags(slot_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.weekly_table.setItem(row_index, 0, slot_item)
                self.weekly_table.setRowHeight(row_index, 64)

            grid_text = {}
            for _, _, day_label, start_label, end_label, subject_name, teacher_name in rows:
                if day_label not in day_to_column:
                    continue
                slot_label = f"{start_label} - {end_label}"
                row_index = slot_map[slot_label]
                column_index = day_to_column[day_label]
                label = subject_name or "-"
                if teacher_name:
                    label = f"{label}\n{teacher_name}"
                grid_text[(row_index, column_index)] = label
                item = QTableWidgetItem(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                color = self._subject_color(subject_name or "")
                item.setBackground(color)
                self.weekly_table.setItem(row_index, column_index, item)

            self.current_schedule_rows = []
            for row_index, slot_label in enumerate(slots):
                row_values = [slot_label]
                for day in days:
                    row_values.append(grid_text.get((row_index, day_to_column[day]), ""))
                self.current_schedule_rows.append(row_values)

            for column_index in range(1, len(days) + 1):
                start_row = None
                previous_text = None
                for row_index in range(len(slots) + 1):
                    text = None
                    if row_index < len(slots):
                        item = self.weekly_table.item(row_index, column_index)
                        text = item.text() if item else ""

                    if row_index == 0:
                        start_row = 0
                        previous_text = text
                        continue

                    if text != previous_text:
                        if previous_text:
                            span_length = row_index - start_row
                            if span_length > 1:
                                self.weekly_table.setSpan(start_row, column_index, span_length, 1)
                        start_row = row_index
                        previous_text = text
                # loop intentionally closes spans through sentinel row
            self.weekly_table.resizeRowsToContents()

        except Exception:
            self.schedule_hint.setText("Impossible de générer le tableau hebdomadaire.")
        finally:
            conn.close()

    def _subject_color(self, subject_name: str):
        palette = [
            "#FDE68A",
            "#BFDBFE",
            "#FBCFE8",
            "#C7D2FE",
            "#A7F3D0",
            "#FCD34D",
            "#FDBA74",
            "#DDD6FE",
            "#BAE6FD",
            "#FECACA",
        ]
        index = sum(ord(char) for char in subject_name) % len(palette)
        from PyQt6.QtGui import QColor
        return QColor(palette[index])

    def _generate_weekly_schedule_pdf(self):
        if not self.current_schedule_rows:
            raise ValueError("Aucun emploi du temps à imprimer")

        os.makedirs("prints/timetables", exist_ok=True)
        filename = (
            "prints/timetables/"
            f"{self.current_schedule_class_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        doc = SimpleDocTemplate(
            filename,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
        )
        styles = getSampleStyleSheet()
        title = f"Emploi du temps - {self.current_schedule_class_name}"
        subtitle = (
            f"Établissement : {self.current_schedule_establishment_name} | "
            f"Année scolaire : {self.current_schedule_year_name}"
        )

        headers = ["Horaire", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
        table_data = [headers] + self.current_schedule_rows
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story = [
            Paragraph(f"<b>{title}</b>", styles["Title"]),
            Spacer(1, 8),
            Paragraph(subtitle, styles["Normal"]),
            Spacer(1, 14),
            table,
        ]
        doc.build(story)
        return filename

    def preview_weekly_schedule_pdf(self):
        try:
            filepath = self._generate_weekly_schedule_pdf()
            self._open_file(filepath)
            QMessageBox.information(self, "Succès", f"Aperçu PDF généré : {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Aperçu impossible : {e}")

    def print_weekly_schedule(self):
        self.preview_weekly_schedule_pdf()

    def _open_file(self, filepath):
        if sys.platform.startswith("win"):
            os.startfile(filepath)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
