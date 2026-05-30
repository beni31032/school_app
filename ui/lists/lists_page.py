import csv
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.connection import get_connection
from utils.college_bulletin_service import get_college_bulletin_data
from utils.discount_service import ensure_discount_schema
from utils.expense_service import ensure_expenses_table
from utils.lycee_bulletin_service import get_lycee_bulletin_data
from utils.primary_bulletin_service import get_primary_bulletin_data
from utils.qt_printing import preview_pdf_file, print_pdf_file
from utils.salary_service import ensure_salary_table
from utils.table_style import setup_table
from utils.teacher_service import ensure_teacher_schema


LIST_TYPES = [
    ("Élèves par classe", "STUDENTS_BY_CLASS"),
    ("Élèves en règle", "STUDENTS_REGULAR"),
    ("Élèves non en règle", "STUDENTS_NOT_REGULAR"),
    ("Retards de paiement élevés", "STUDENTS_PAYMENT_DELAY"),
    ("Liste des notes", "GRADES_BY_CLASS"),
    ("Élèves sans note", "MISSING_GRADES_BY_CLASS"),
    ("Liste des résultats", "RESULTS_BY_CLASS"),
    ("Résultats par ordre de mérite", "MERIT_RESULTS_BY_CLASS"),
    ("Admis / non admis", "ADMISSION_BY_CLASS"),
    ("Élèves par matière facultative", "OPTIONAL_SUBJECT_STUDENTS"),
    ("Paiements par classe", "CLASS_PAYMENTS"),
    ("Réductions accordées", "DISCOUNTS_GRANTED"),
    ("Enseignants par classe et matière", "TEACHERS_BY_CLASS_SUBJECT"),
    ("Effectifs par classe", "CLASS_ENROLLMENT_STATS"),
    ("Élèves sans photo", "STUDENTS_WITHOUT_PHOTO"),
    ("Reçus / paiements sur période", "PAYMENT_RECEIPTS_PERIOD"),
    ("Tous les élèves", "ALL_STUDENTS"),
    ("Enseignants", "TEACHERS"),
    ("Employés", "STAFF"),
    ("Classes", "CLASSES"),
]

CLASS_FILTER_TYPES = {
    "STUDENTS_BY_CLASS",
    "STUDENTS_REGULAR",
    "STUDENTS_NOT_REGULAR",
    "STUDENTS_PAYMENT_DELAY",
    "GRADES_BY_CLASS",
    "MISSING_GRADES_BY_CLASS",
    "RESULTS_BY_CLASS",
    "MERIT_RESULTS_BY_CLASS",
    "ADMISSION_BY_CLASS",
    "OPTIONAL_SUBJECT_STUDENTS",
    "CLASS_PAYMENTS",
    "DISCOUNTS_GRANTED",
    "TEACHERS_BY_CLASS_SUBJECT",
    "CLASS_ENROLLMENT_STATS",
    "STUDENTS_WITHOUT_PHOTO",
    "PAYMENT_RECEIPTS_PERIOD",
}

TERM_FILTER_TYPES = {
    "GRADES_BY_CLASS",
    "MISSING_GRADES_BY_CLASS",
    "RESULTS_BY_CLASS",
    "MERIT_RESULTS_BY_CLASS",
    "ADMISSION_BY_CLASS",
}

SUBJECT_FILTER_TYPES = {
    "MISSING_GRADES_BY_CLASS",
    "OPTIONAL_SUBJECT_STUDENTS",
}

DATE_FILTER_TYPES = {
    "PAYMENT_RECEIPTS_PERIOD",
}

CLASS_REQUIRED_TYPES = {
    "GRADES_BY_CLASS",
    "MISSING_GRADES_BY_CLASS",
    "RESULTS_BY_CLASS",
    "MERIT_RESULTS_BY_CLASS",
    "ADMISSION_BY_CLASS",
    "OPTIONAL_SUBJECT_STUDENTS",
}


class ListsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_discount_schema()
        ensure_teacher_schema()
        ensure_salary_table()
        ensure_expenses_table()

        self.current_headers: list[str] = []
        self.current_rows: list[list[str]] = []
        self.current_footer_lines: list[str] = []

        layout = QVBoxLayout()

        filters = QHBoxLayout()
        self.type_filter = QComboBox()
        for label, key in LIST_TYPES:
            self.type_filter.addItem(label, key)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Recherche rapide...")
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()
        self.term_filter = QComboBox()
        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.type_label = QLabel("Type")
        self.search_label = QLabel("Recherche")
        self.establishment_label = QLabel("Établissement")
        self.school_year_label = QLabel("Année")
        self.term_label = QLabel("Trimestre")
        self.class_label = QLabel("Classe")
        self.subject_label = QLabel("Matière")
        self.start_date_label = QLabel("Du")
        self.end_date_label = QLabel("Au")

        today = QDate.currentDate()
        self.start_date_filter = QDateEdit()
        self.start_date_filter.setCalendarPopup(True)
        self.start_date_filter.setDisplayFormat("yyyy-MM-dd")
        self.start_date_filter.setDate(QDate(today.year(), today.month(), 1))

        self.end_date_filter = QDateEdit()
        self.end_date_filter.setCalendarPopup(True)
        self.end_date_filter.setDisplayFormat("yyyy-MM-dd")
        self.end_date_filter.setDate(today)

        filters.addWidget(self.type_label)
        filters.addWidget(self.type_filter)
        filters.addWidget(self.search_label)
        filters.addWidget(self.search_input)
        filters.addWidget(self.establishment_label)
        filters.addWidget(self.establishment_filter)
        filters.addWidget(self.school_year_label)
        filters.addWidget(self.school_year_filter)
        filters.addWidget(self.term_label)
        filters.addWidget(self.term_filter)
        filters.addWidget(self.class_label)
        filters.addWidget(self.class_filter)
        filters.addWidget(self.subject_label)
        filters.addWidget(self.subject_filter)
        filters.addWidget(self.start_date_label)
        filters.addWidget(self.start_date_filter)
        filters.addWidget(self.end_date_label)
        filters.addWidget(self.end_date_filter)

        actions = QHBoxLayout()
        self.refresh_btn = QPushButton("Actualiser")
        self.export_csv_btn = QPushButton("Exporter CSV")
        self.preview_pdf_btn = QPushButton("Aperçu PDF")
        self.print_btn = QPushButton("Imprimer")

        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.export_csv_btn)
        actions.addWidget(self.preview_pdf_btn)
        actions.addWidget(self.print_btn)

        self.table = QTableWidget()
        setup_table(self.table)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("listsSummaryCard")
        summary_layout = QFormLayout(self.summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setVerticalSpacing(6)

        self.summary_type = QLabel("-")
        self.summary_scope = QLabel("-")
        self.summary_count = QLabel("0")

        summary_layout.addRow("Liste :", self.summary_type)
        summary_layout.addRow("Filtre appliqué :", self.summary_scope)
        summary_layout.addRow("Nombre de lignes :", self.summary_count)

        layout.addLayout(filters)
        layout.addLayout(actions)
        layout.addWidget(self.summary_card)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.apply_combo_style()

        self.type_filter.currentIndexChanged.connect(self.on_type_changed)
        self.establishment_filter.currentIndexChanged.connect(self.load_classes)
        self.establishment_filter.currentIndexChanged.connect(self.load_data)
        self.school_year_filter.currentIndexChanged.connect(self.load_terms)
        self.school_year_filter.currentIndexChanged.connect(self.load_classes)
        self.school_year_filter.currentIndexChanged.connect(self.load_data)
        self.term_filter.currentIndexChanged.connect(self.load_data)
        self.class_filter.currentIndexChanged.connect(self.load_subjects)
        self.class_filter.currentIndexChanged.connect(self.load_data)
        self.subject_filter.currentIndexChanged.connect(self.load_data)
        self.start_date_filter.dateChanged.connect(self.load_data)
        self.end_date_filter.dateChanged.connect(self.load_data)
        self.search_input.textChanged.connect(self.load_data)
        self.refresh_btn.clicked.connect(self.load_data)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.preview_pdf_btn.clicked.connect(self.preview_pdf)
        self.print_btn.clicked.connect(self.print_current)

        self.load_establishments()
        self.load_school_years()
        self.load_terms()
        self.load_classes()
        self.load_subjects()
        self.on_type_changed()

    def apply_combo_style(self):
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QLineEdit, QDateEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QComboBox {
                background-color: #303030;
                color: #ffffff;
                border: 1px solid #525252;
                border-radius: 4px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }
            QFrame#listsSummaryCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

    def on_type_changed(self):
        key = self.type_filter.currentData()
        class_enabled = key in CLASS_FILTER_TYPES
        term_enabled = key in TERM_FILTER_TYPES
        subject_enabled = key in SUBJECT_FILTER_TYPES
        date_enabled = key in DATE_FILTER_TYPES

        self.class_label.setVisible(class_enabled)
        self.class_filter.setVisible(class_enabled)
        self.class_filter.setEnabled(class_enabled)

        self.term_label.setVisible(term_enabled)
        self.term_filter.setVisible(term_enabled)
        self.term_filter.setEnabled(term_enabled)

        self.subject_label.setVisible(subject_enabled)
        self.subject_filter.setVisible(subject_enabled)
        self.subject_filter.setEnabled(subject_enabled)

        self.start_date_label.setVisible(date_enabled)
        self.start_date_filter.setVisible(date_enabled)
        self.start_date_filter.setEnabled(date_enabled)

        self.end_date_label.setVisible(date_enabled)
        self.end_date_filter.setVisible(date_enabled)
        self.end_date_filter.setEnabled(date_enabled)

        self.load_subjects()
        self.load_data()

    def _level_is_student_based(self, level_name: str) -> bool:
        normalized = (level_name or "").strip().lower()
        aliases = ("3eme", "3ème", "seconde", "2nde", "premiere", "première", "1ere", "1ère", "terminale", "tle")
        return any(alias in normalized for alias in aliases)

    def _secondary_observation(self, average: float) -> str:
        if average >= 16:
            return "Très bien"
        if average >= 14:
            return "Bien"
        if average >= 12:
            return "Assez bien"
        if average >= 10:
            return "Passable"
        return "Insuffisant"

    def _get_date_range(self) -> tuple[str, str]:
        return (
            self.start_date_filter.date().toString("yyyy-MM-dd"),
            self.end_date_filter.date().toString("yyyy-MM-dd"),
        )

    def _set_current_data(
        self,
        headers: list[str],
        rows: list[list[str]],
        footer_lines: list[str] | None = None,
    ):
        self.current_headers = headers
        self.current_rows = rows
        self.current_footer_lines = footer_lines or []
        self._fill_table()
        self._update_summary()

    def _get_class_titular_name(self, cursor, class_id: int) -> str:
        cursor.execute(
            """
            SELECT COALESCE(t.last_name || ' ' || t.first_name, '')
            FROM classes c
            LEFT JOIN teachers t ON t.id = c.titular_teacher_id
            WHERE c.id = %s
            """,
            (class_id,),
        )
        row = cursor.fetchone()
        return (row[0] or "").strip() if row else ""

    def load_establishments(self):
        self.establishment_filter.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cur.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cur.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                est_id = self.current_user["establishment_id"]
                cur.execute("SELECT id, name FROM establishments WHERE id = %s", (est_id,))
                row = cur.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def load_school_years(self):
        self.school_year_filter.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for school_year_id, name in cur.fetchall():
                self.school_year_filter.addItem(name, school_year_id)
        finally:
            conn.close()

    def load_terms(self):
        school_year_id = self.school_year_filter.currentData()
        self.term_filter.clear()
        if school_year_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name
                FROM terms
                WHERE school_year_id = %s
                ORDER BY id
                """,
                (school_year_id,),
            )
            for term_id, name in cur.fetchall():
                self.term_filter.addItem(name, term_id)
        finally:
            conn.close()

    def load_classes(self):
        est_id = self.establishment_filter.currentData()
        self.class_filter.clear()
        self.class_filter.addItem("Toutes", None)

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            params: list[object] = []
            sql = "SELECT id, name FROM classes"
            if self.is_global_admin:
                if est_id is not None:
                    sql += " WHERE establishment_id = %s"
                    params.append(est_id)
            else:
                sql += " WHERE establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            sql += " ORDER BY name"
            cur.execute(sql, params)
            for class_id, name in cur.fetchall():
                self.class_filter.addItem(name, class_id)
        finally:
            conn.close()

    def load_subjects(self):
        class_id = self.class_filter.currentData()
        self.subject_filter.clear()
        self.subject_filter.addItem("Toutes", None)

        if class_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            key = self.type_filter.currentData()
            sql = """
                SELECT DISTINCT sb.id, sb.name
                FROM class_subjects cs
                JOIN subjects sb ON sb.id = cs.subject_id
                WHERE cs.class_id = %s
            """
            params: list[object] = [class_id]
            if key == "OPTIONAL_SUBJECT_STUDENTS":
                sql += " AND COALESCE(cs.subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'"
            sql += " ORDER BY sb.name"
            cur.execute(sql, params)
            for subject_id, name in cur.fetchall():
                self.subject_filter.addItem(name, subject_id)
        finally:
            conn.close()

    def _get_class_context(self, cursor, class_id: int) -> tuple[str, str]:
        cursor.execute(
            """
            SELECT COALESCE(cy.name, ''), COALESCE(c.level, '')
            FROM classes c
            LEFT JOIN cycles cy ON cy.id = c.cycle_id
            WHERE c.id = %s
            """,
            (class_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Classe introuvable.")
        return str(row[0] or ""), str(row[1] or "")

    def _get_filtered_student_rows(
        self,
        cursor,
        class_id: int,
        school_year_id: int,
        search: str,
    ) -> list[tuple[int, str, str, str, str]]:
        cursor.execute(
            """
            SELECT DISTINCT
                s.id,
                COALESCE(s.matricule, ''),
                s.last_name,
                s.first_name,
                COALESCE(s.gender, '')
            FROM enrollments e
            JOIN students s ON s.id = e.student_id
            WHERE e.class_id = %s
              AND e.school_year_id = %s
              AND s.is_active = TRUE
              AND (
                    COALESCE(s.matricule, '') ILIKE %s
                    OR s.last_name ILIKE %s
                    OR s.first_name ILIKE %s
              )
            ORDER BY s.last_name, s.first_name
            """,
            (class_id, school_year_id, search, search, search),
        )
        return cursor.fetchall()

    def _build_student_payment_status_query(
        self,
        est_id,
        school_year_id,
        class_id,
        search: str,
    ) -> tuple[str, list[object]]:
        where = [
            "e.school_year_id = %s",
            "s.is_active = TRUE",
            "(s.matricule ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR c.name ILIKE %s)",
        ]
        params: list[object] = [school_year_id, search, search, search, search]

        if class_id is not None:
            where.append("e.class_id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("s.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("s.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        sql = f"""
            WITH filtered_students AS (
                SELECT DISTINCT
                    s.id AS student_id,
                    s.matricule,
                    s.last_name,
                    s.first_name,
                    s.gender,
                    c.id AS class_id,
                    c.name AS class_name
                FROM students s
                JOIN enrollments e ON e.student_id = s.id
                JOIN classes c ON c.id = e.class_id
                WHERE {' AND '.join(where)}
            ),
            student_fee_lines AS (
                SELECT
                    fs.student_id,
                    cf.id AS class_fee_id,
                    COALESCE(cf.amount, 0) AS expected_amount,
                    COALESCE(sd.discount_amount, 0) AS discount_amount,
                    COALESCE(pp.paid_amount, 0) AS paid_amount
                FROM filtered_students fs
                JOIN class_fees cf
                    ON cf.class_id = fs.class_id
                   AND cf.school_year_id = %s
                LEFT JOIN (
                    SELECT
                        student_id,
                        fee_id,
                        SUM(amount) AS discount_amount
                    FROM student_discounts
                    WHERE school_year_id = %s
                    GROUP BY student_id, fee_id
                ) sd
                    ON sd.student_id = fs.student_id
                   AND sd.fee_id = cf.fee_id
                LEFT JOIN (
                    SELECT
                        student_id,
                        class_fee_id,
                        SUM(amount) AS paid_amount
                    FROM payments
                    GROUP BY student_id, class_fee_id
                ) pp
                    ON pp.student_id = fs.student_id
                   AND pp.class_fee_id = cf.id
            )
            SELECT
                fs.matricule,
                fs.last_name,
                fs.first_name,
                fs.gender,
                fs.class_name,
                ROUND(COALESCE(SUM(sfl.expected_amount), 0), 2) AS expected_total,
                ROUND(COALESCE(SUM(sfl.discount_amount), 0), 2) AS discount_total,
                ROUND(COALESCE(SUM(sfl.paid_amount), 0), 2) AS paid_total,
                ROUND(
                    GREATEST(
                        COALESCE(SUM(sfl.expected_amount - sfl.discount_amount - sfl.paid_amount), 0),
                        0
                    ),
                    2
                ) AS remaining_total
            FROM filtered_students fs
            LEFT JOIN student_fee_lines sfl ON sfl.student_id = fs.student_id
            GROUP BY
                fs.student_id,
                fs.matricule,
                fs.last_name,
                fs.first_name,
                fs.gender,
                fs.class_name
        """
        params.append(school_year_id)
        params.append(school_year_id)
        return sql, params

    def _load_payment_status_rows(self, cursor, mode: str, est_id, school_year_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        base_sql, params = self._build_student_payment_status_query(est_id, school_year_id, class_id, search)
        if mode == "regular":
            sql = base_sql + """
                HAVING GREATEST(
                    COALESCE(SUM(sfl.expected_amount - sfl.discount_amount - sfl.paid_amount), 0),
                    0
                ) <= 0.0001
                ORDER BY fs.class_name, fs.last_name, fs.first_name
            """
        elif mode == "not_regular":
            sql = base_sql + """
                HAVING GREATEST(
                    COALESCE(SUM(sfl.expected_amount - sfl.discount_amount - sfl.paid_amount), 0),
                    0
                ) > 0.0001
                ORDER BY fs.class_name, fs.last_name, fs.first_name
            """
        else:
            sql = base_sql + """
                HAVING GREATEST(
                    COALESCE(SUM(sfl.expected_amount - sfl.discount_amount - sfl.paid_amount), 0),
                    0
                ) > 0.0001
                ORDER BY remaining_total DESC, fs.class_name, fs.last_name, fs.first_name
            """

        cursor.execute(sql, params)
        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Classe", "Montant prévu", "Réduction", "Payé", "Reste"]
        return headers, cursor.fetchall()

    def _load_primary_grade_rows(self, cursor, class_id: int, term_id: int, school_year_id: int, search: str) -> tuple[list[str], list[list[str]]]:
        students = self._get_filtered_student_rows(cursor, class_id, school_year_id, search)

        cursor.execute(
            """
            SELECT DISTINCT sb.name
            FROM class_subjects cs
            JOIN subjects sb ON sb.id = cs.subject_id
            WHERE cs.class_id = %s
            ORDER BY sb.name
            """,
            (class_id,),
        )
        subject_names = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                g.student_id,
                sb.name,
                MAX(g.value) AS score,
                MAX(g.max_score) AS max_score
            FROM grades g
            JOIN subjects sb ON sb.id = g.subject_id
            JOIN class_subjects cs
                ON cs.subject_id = g.subject_id
               AND cs.class_id = %s
            JOIN enrollments e
                ON e.student_id = g.student_id
               AND e.class_id = %s
               AND e.school_year_id = %s
            WHERE g.term_id = %s
            GROUP BY g.student_id, sb.name
            """,
            (class_id, class_id, school_year_id, term_id),
        )
        grades_map = {
            (int(student_id), str(subject_name)): (score, max_score)
            for student_id, subject_name, score, max_score in cursor.fetchall()
        }

        rows: list[list[str]] = []
        for student_id, matricule, last_name, first_name, gender in students:
            for subject_name in subject_names:
                score, max_score = grades_map.get((int(student_id), subject_name), (None, None))
                rows.append(
                    [
                        str(matricule or ""),
                        str(last_name or ""),
                        str(first_name or ""),
                        str(gender or ""),
                        str(subject_name),
                        "" if score is None else f"{float(score):.2f}",
                        "" if max_score is None else f"{float(max_score):.2f}",
                    ]
                )

        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Matière", "Note", "Barème"]
        return headers, rows

    def _load_secondary_grade_rows(
        self,
        cursor,
        class_id: int,
        term_id: int,
        school_year_id: int,
        search: str,
        class_level: str,
    ) -> tuple[list[str], list[list[str]]]:
        students = self._get_filtered_student_rows(cursor, class_id, school_year_id, search)

        cursor.execute(
            """
            SELECT
                cs.subject_id,
                sb.name,
                COALESCE(cs.coefficient, 1),
                COALESCE(cs.subject_type, 'OBLIGATOIRE')
            FROM class_subjects cs
            JOIN subjects sb ON sb.id = cs.subject_id
            WHERE cs.class_id = %s
            ORDER BY sb.name
            """,
            (class_id,),
        )
        subjects = cursor.fetchall()

        optional_subject_choices: set[tuple[int, int]] = set()
        if self._level_is_student_based(class_level):
            cursor.execute(
                """
                SELECT sos.student_id, cs.subject_id
                FROM student_optional_subjects sos
                JOIN class_subjects cs ON cs.id = sos.class_subject_id
                WHERE sos.school_year_id = %s
                  AND cs.class_id = %s
                """,
                (school_year_id, class_id),
            )
            optional_subject_choices = {
                (int(student_id), int(subject_id))
                for student_id, subject_id in cursor.fetchall()
            }

        cursor.execute(
            """
            SELECT
                g.student_id,
                g.subject_id,
                MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END) AS classe_note,
                MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END) AS compo_note
            FROM grades g
            JOIN enrollments e
                ON e.student_id = g.student_id
               AND e.class_id = %s
               AND e.school_year_id = %s
            WHERE g.term_id = %s
              AND g.grade_type IN ('classe', 'compo')
            GROUP BY g.student_id, g.subject_id
            """,
            (class_id, school_year_id, term_id),
        )
        grades_map = {
            (int(student_id), int(subject_id)): (classe_note, compo_note)
            for student_id, subject_id, classe_note, compo_note in cursor.fetchall()
        }

        rows: list[list[str]] = []
        for student_id, matricule, last_name, first_name, gender in students:
            for subject_id, subject_name, coefficient, subject_type in subjects:
                is_optional = subject_type == "FACULTATIVE"
                if is_optional and self._level_is_student_based(class_level):
                    if (int(student_id), int(subject_id)) not in optional_subject_choices:
                        continue

                classe_note, compo_note = grades_map.get((int(student_id), int(subject_id)), (None, None))
                classe_display = "" if classe_note is None else f"{float(classe_note):.2f}"
                compo_display = "" if compo_note is None else f"{float(compo_note):.2f}"
                moyenne_display = ""
                note_def_display = ""
                if classe_note is not None and compo_note is not None:
                    moyenne = round((float(classe_note) + float(compo_note)) / 2.0, 2)
                    note_def = round(moyenne * float(coefficient or 1), 2)
                    moyenne_display = f"{moyenne:.2f}"
                    note_def_display = f"{note_def:.2f}"

                rows.append(
                    [
                        str(matricule or ""),
                        str(last_name or ""),
                        str(first_name or ""),
                        str(gender or ""),
                        str(subject_name),
                        "Facultative" if is_optional else "Obligatoire",
                        str(int(coefficient or 1)),
                        classe_display,
                        compo_display,
                        moyenne_display,
                        note_def_display,
                    ]
                )

        headers = [
            "Matricule",
            "Nom",
            "Prénom",
            "Sexe",
            "Matière",
            "Type",
            "Coef",
            "Note classe",
            "Composition",
            "Moyenne",
            "Note déf.",
        ]
        return headers, rows

    def _build_result_records(
        self,
        cursor,
        class_id: int,
        term_id: int,
        school_year_id: int,
        search: str,
    ) -> tuple[str, list[dict]]:
        cycle_name, _class_level = self._get_class_context(cursor, class_id)
        students = self._get_filtered_student_rows(cursor, class_id, school_year_id, search)

        records: list[dict] = []
        if cycle_name == "Primaire":
            for student_id, matricule, last_name, first_name, gender in students:
                data = get_primary_bulletin_data(int(student_id), int(term_id))
                average = float(data["average"] or 0)
                records.append(
                    {
                        "matricule": str(matricule or ""),
                        "last_name": str(last_name or ""),
                        "first_name": str(first_name or ""),
                        "gender": str(gender or ""),
                        "total_score": float(data["total_score"] or 0),
                        "total_max": float(data["total_max"] or 0),
                        "average": average,
                        "rank": int(data["rank"] or 0),
                        "effectif": int(data["effectif"] or 0),
                        "observation": str(data.get("observation", "")),
                        "status": str(data.get("admitted", "Non")),
                    }
                )
            return cycle_name, records

        result_loader = get_college_bulletin_data if cycle_name == "Collège" else get_lycee_bulletin_data
        for student_id, matricule, last_name, first_name, gender in students:
            data = result_loader(int(student_id), int(term_id))
            average = float(data["general_average"] or 0)
            records.append(
                {
                    "matricule": str(matricule or ""),
                    "last_name": str(last_name or ""),
                    "first_name": str(first_name or ""),
                    "gender": str(gender or ""),
                    "total_coef": int(data["total_coef"] or 0),
                    "total_notes": float(data["total_notes"] or 0),
                    "bonus": int(data.get("optional_bonus", 0) or 0),
                    "average": average,
                    "rank": int(data["general_rank"] or 0),
                    "effectif": int(data["effectif"] or 0),
                    "observation": self._secondary_observation(average),
                    "status": "Oui" if average >= 10 else "Non",
                }
            )
        return cycle_name, records

    def _load_results_rows(
        self,
        cursor,
        class_id: int,
        term_id: int,
        school_year_id: int,
        search: str,
        sort_by_rank: bool,
    ) -> tuple[list[str], list[list[str]]]:
        cycle_name, records = self._build_result_records(cursor, class_id, term_id, school_year_id, search)
        if sort_by_rank:
            records.sort(key=lambda item: (item["rank"] or 999999, item["last_name"], item["first_name"]))
        else:
            records.sort(key=lambda item: (item["last_name"], item["first_name"]))

        if cycle_name == "Primaire":
            headers = [
                "Matricule",
                "Nom",
                "Prénom",
                "Sexe",
                "Total points",
                "Total max",
                "Moyenne",
                "Rang",
                "Observation",
                "Admis",
            ]
            rows = []
            for item in records:
                rows.append(
                    [
                        item["matricule"],
                        item["last_name"],
                        item["first_name"],
                        item["gender"],
                        f"{item['total_score']:.2f}",
                        f"{item['total_max']:.2f}",
                        f"{item['average']:.2f}",
                        f"{item['rank']}/{item['effectif']}" if item["effectif"] > 0 else "-",
                        item["observation"],
                        item["status"],
                    ]
                )
            return headers, rows

        headers = [
            "Matricule",
            "Nom",
            "Prénom",
            "Sexe",
            "Total coef",
            "Total notes",
            "Bonus",
            "Moyenne générale",
            "Rang",
            "Observation",
            "Admis",
        ]
        rows = []
        for item in records:
            rows.append(
                [
                    item["matricule"],
                    item["last_name"],
                    item["first_name"],
                    item["gender"],
                    str(item["total_coef"]),
                    f"{item['total_notes']:.2f}",
                    str(item["bonus"]),
                    f"{item['average']:.2f}",
                    f"{item['rank']}/{item['effectif']}" if item["effectif"] > 0 else "-",
                    item["observation"],
                    item["status"],
                ]
            )
        return headers, rows

    def _build_results_footer_lines(
        self,
        cursor,
        class_id: int,
        term_id: int,
        school_year_id: int,
        search: str,
    ) -> list[str]:
        _cycle_name, records = self._build_result_records(cursor, class_id, term_id, school_year_id, search)
        titular_name = self._get_class_titular_name(cursor, class_id)

        effectif = len(records)
        admitted_count = sum(1 for item in records if str(item.get("status", "")).strip().lower() in {"oui", "admis", "admis(e)"})
        not_admitted_count = max(effectif - admitted_count, 0)
        class_average = round(sum(float(item.get("average", 0) or 0) for item in records) / effectif, 2) if effectif else 0.0
        success_rate = round((admitted_count / effectif) * 100, 2) if effectif else 0.0

        return [
            f"Titulaire de la classe : {titular_name or '-'}",
            (
                "Statistiques : "
                f"Effectif = {effectif} | "
                f"Admis = {admitted_count} | "
                f"Non admis = {not_admitted_count} | "
                f"Moyenne de classe = {class_average:.2f} | "
                f"Pourcentage de réussite = {success_rate:.2f}%"
            ),
        ]

    def _load_missing_grades_rows(
        self,
        cursor,
        class_id: int,
        term_id: int,
        school_year_id: int,
        search: str,
        subject_id,
    ) -> tuple[list[str], list[list[str]]]:
        cycle_name, class_level = self._get_class_context(cursor, class_id)
        if cycle_name == "Primaire":
            students = self._get_filtered_student_rows(cursor, class_id, school_year_id, search)
            sql = """
                SELECT DISTINCT cs.subject_id, sb.name
                FROM class_subjects cs
                JOIN subjects sb ON sb.id = cs.subject_id
                WHERE cs.class_id = %s
            """
            params: list[object] = [class_id]
            if subject_id is not None:
                sql += " AND cs.subject_id = %s"
                params.append(subject_id)
            sql += " ORDER BY sb.name"
            cursor.execute(sql, params)
            subjects = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    g.student_id,
                    g.subject_id,
                    MAX(g.value)
                FROM grades g
                JOIN enrollments e
                    ON e.student_id = g.student_id
                   AND e.class_id = %s
                   AND e.school_year_id = %s
                WHERE g.term_id = %s
                GROUP BY g.student_id, g.subject_id
                """,
                (class_id, school_year_id, term_id),
            )
            grade_map = {
                (int(student_id), int(existing_subject_id)): value
                for student_id, existing_subject_id, value in cursor.fetchall()
            }

            rows: list[list[str]] = []
            for student_id, matricule, last_name, first_name, gender in students:
                for current_subject_id, subject_name in subjects:
                    if (int(student_id), int(current_subject_id)) not in grade_map:
                        rows.append(
                            [
                                str(matricule or ""),
                                str(last_name or ""),
                                str(first_name or ""),
                                str(gender or ""),
                                str(subject_name),
                                "Note",
                            ]
                        )
            headers = ["Matricule", "Nom", "Prénom", "Sexe", "Matière", "Champ manquant"]
            return headers, rows

        students = self._get_filtered_student_rows(cursor, class_id, school_year_id, search)
        sql = """
            SELECT
                cs.subject_id,
                sb.name,
                COALESCE(cs.subject_type, 'OBLIGATOIRE')
            FROM class_subjects cs
            JOIN subjects sb ON sb.id = cs.subject_id
            WHERE cs.class_id = %s
        """
        params = [class_id]
        if subject_id is not None:
            sql += " AND cs.subject_id = %s"
            params.append(subject_id)
        sql += " ORDER BY sb.name"
        cursor.execute(sql, params)
        subjects = cursor.fetchall()

        optional_subject_choices: set[tuple[int, int]] = set()
        if self._level_is_student_based(class_level):
            cursor.execute(
                """
                SELECT sos.student_id, cs.subject_id
                FROM student_optional_subjects sos
                JOIN class_subjects cs ON cs.id = sos.class_subject_id
                WHERE sos.school_year_id = %s
                  AND cs.class_id = %s
                """,
                (school_year_id, class_id),
            )
            optional_subject_choices = {
                (int(student_id), int(optional_subject_id))
                for student_id, optional_subject_id in cursor.fetchall()
            }

        cursor.execute(
            """
            SELECT
                g.student_id,
                g.subject_id,
                MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END) AS classe_note,
                MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END) AS compo_note
            FROM grades g
            JOIN enrollments e
                ON e.student_id = g.student_id
               AND e.class_id = %s
               AND e.school_year_id = %s
            WHERE g.term_id = %s
              AND g.grade_type IN ('classe', 'compo')
            GROUP BY g.student_id, g.subject_id
            """,
            (class_id, school_year_id, term_id),
        )
        grades_map = {
            (int(student_id), int(existing_subject_id)): (classe_note, compo_note)
            for student_id, existing_subject_id, classe_note, compo_note in cursor.fetchall()
        }

        rows = []
        for student_id, matricule, last_name, first_name, gender in students:
            for current_subject_id, subject_name, subject_type in subjects:
                if subject_type == "FACULTATIVE" and self._level_is_student_based(class_level):
                    if (int(student_id), int(current_subject_id)) not in optional_subject_choices:
                        continue

                classe_note, compo_note = grades_map.get((int(student_id), int(current_subject_id)), (None, None))
                missing_parts = []
                if classe_note is None:
                    missing_parts.append("Note classe")
                if compo_note is None:
                    missing_parts.append("Composition")
                if missing_parts:
                    rows.append(
                        [
                            str(matricule or ""),
                            str(last_name or ""),
                            str(first_name or ""),
                            str(gender or ""),
                            str(subject_name),
                            " / ".join(missing_parts),
                        ]
                    )

        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Matière", "Champ manquant"]
        return headers, rows

    def _load_optional_subject_students_rows(
        self,
        cursor,
        class_id: int,
        school_year_id: int,
        search: str,
        subject_id,
    ) -> tuple[list[str], list[tuple]]:
        cycle_name, class_level = self._get_class_context(cursor, class_id)
        student_based = cycle_name != "Primaire" and self._level_is_student_based(class_level)

        if student_based:
            sql = """
                SELECT
                    s.matricule,
                    s.last_name,
                    s.first_name,
                    s.gender,
                    c.name,
                    sb.name
                FROM student_optional_subjects sos
                JOIN class_subjects cs ON cs.id = sos.class_subject_id
                JOIN subjects sb ON sb.id = cs.subject_id
                JOIN students s ON s.id = sos.student_id
                JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.class_id = cs.class_id
                   AND e.school_year_id = sos.school_year_id
                JOIN classes c ON c.id = cs.class_id
                WHERE sos.school_year_id = %s
                  AND cs.class_id = %s
                  AND s.is_active = TRUE
                  AND (
                        COALESCE(s.matricule, '') ILIKE %s
                        OR s.last_name ILIKE %s
                        OR s.first_name ILIKE %s
                        OR sb.name ILIKE %s
                  )
            """
            params: list[object] = [school_year_id, class_id, search, search, search, search]
            if subject_id is not None:
                sql += " AND cs.subject_id = %s"
                params.append(subject_id)
            sql += " ORDER BY sb.name, s.last_name, s.first_name"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        else:
            sql = """
                SELECT
                    s.matricule,
                    s.last_name,
                    s.first_name,
                    s.gender,
                    c.name,
                    sb.name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                JOIN classes c ON c.id = e.class_id
                JOIN class_subjects cs ON cs.class_id = e.class_id
                JOIN subjects sb ON sb.id = cs.subject_id
                WHERE e.school_year_id = %s
                  AND e.class_id = %s
                  AND s.is_active = TRUE
                  AND COALESCE(cs.subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'
                  AND (
                        COALESCE(s.matricule, '') ILIKE %s
                        OR s.last_name ILIKE %s
                        OR s.first_name ILIKE %s
                        OR sb.name ILIKE %s
                  )
            """
            params = [school_year_id, class_id, search, search, search, search]
            if subject_id is not None:
                sql += " AND cs.subject_id = %s"
                params.append(subject_id)
            sql += " ORDER BY sb.name, s.last_name, s.first_name"
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Classe", "Matière facultative"]
        return headers, rows

    def _load_class_payments_rows(self, cursor, est_id, school_year_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        where = [
            "cf.school_year_id = %s",
            "(COALESCE(p.receipt_number, '') ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR f.name ILIKE %s OR c.name ILIKE %s)",
        ]
        params: list[object] = [school_year_id, search, search, search, search, search]

        if class_id is not None:
            where.append("c.id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("c.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("c.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        cursor.execute(
            f"""
            SELECT
                COALESCE(p.receipt_number, ''),
                s.matricule,
                s.last_name,
                s.first_name,
                c.name,
                f.name,
                ROUND(COALESCE(p.amount, 0), 2),
                p.payment_date,
                COALESCE(u.username, '')
            FROM payments p
            JOIN students s ON s.id = p.student_id
            LEFT JOIN users u ON u.id = p.created_by
            JOIN class_fees cf ON cf.id = p.class_fee_id
            JOIN classes c ON c.id = cf.class_id
            JOIN fees f ON f.id = cf.fee_id
            WHERE {' AND '.join(where)}
            ORDER BY c.name, p.payment_date DESC, p.id DESC
            """,
            params,
        )
        headers = ["Reçu", "Matricule", "Nom", "Prénom", "Classe", "Frais", "Montant", "Date", "Saisi par"]
        return headers, cursor.fetchall()

    def _load_payment_receipts_period_rows(self, cursor, est_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        start_date, end_date = self._get_date_range()
        where = [
            "p.payment_date BETWEEN %s AND %s",
            "(COALESCE(p.receipt_number, '') ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR COALESCE(fcf.name, ffallback.name, '') ILIKE %s OR c.name ILIKE %s)",
        ]
        params: list[object] = [start_date, end_date, search, search, search, search, search]

        if class_id is not None:
            where.append("c.id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("c.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("c.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        cursor.execute(
            f"""
            SELECT
                COALESCE(p.receipt_number, ''),
                s.matricule,
                s.last_name,
                s.first_name,
                c.name,
                COALESCE(fcf.name, ffallback.name, ''),
                ROUND(COALESCE(p.amount, 0), 2),
                p.payment_date,
                COALESCE(u.username, '')
            FROM payments p
            JOIN students s ON s.id = p.student_id
            LEFT JOIN users u ON u.id = p.created_by
            LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
            LEFT JOIN classes c ON c.id = cf.class_id
            LEFT JOIN fees fcf ON fcf.id = cf.fee_id
            LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
            WHERE {' AND '.join(where)}
            ORDER BY p.payment_date DESC, p.id DESC
            """,
            params,
        )
        headers = ["Reçu", "Matricule", "Nom", "Prénom", "Classe", "Frais", "Montant", "Date", "Saisi par"]
        return headers, cursor.fetchall()

    def _load_discounts_rows(self, cursor, est_id, school_year_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        where = [
            "d.school_year_id = %s",
            "(COALESCE(s.matricule, '') ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR f.name ILIKE %s OR c.name ILIKE %s OR COALESCE(d.reason, '') ILIKE %s)",
        ]
        params: list[object] = [school_year_id, search, search, search, search, search, search]

        if class_id is not None:
            where.append("c.id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("s.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("s.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        cursor.execute(
            f"""
            SELECT DISTINCT
                s.matricule,
                s.last_name,
                s.first_name,
                c.name,
                f.name,
                ROUND(COALESCE(d.amount, 0), 2),
                COALESCE(d.reason, ''),
                d.created_at
            FROM student_discounts d
            JOIN students s ON s.id = d.student_id
            JOIN enrollments e
              ON e.student_id = s.id
             AND e.school_year_id = d.school_year_id
            JOIN classes c ON c.id = e.class_id
            JOIN fees f ON f.id = d.fee_id
            WHERE {' AND '.join(where)}
            ORDER BY d.created_at DESC, s.last_name, s.first_name
            """,
            params,
        )
        headers = ["Matricule", "Nom", "Prénom", "Classe", "Frais", "Montant", "Motif", "Date"]
        return headers, cursor.fetchall()

    def _load_teachers_by_class_subject_rows(self, cursor, est_id, school_year_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        where = [
            "ta.school_year_id = %s",
            "(t.last_name ILIKE %s OR t.first_name ILIKE %s OR sb.name ILIKE %s OR c.name ILIKE %s)",
        ]
        params: list[object] = [school_year_id, search, search, search, search]

        if class_id is not None:
            where.append("c.id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("c.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("c.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        cursor.execute(
            f"""
            SELECT
                c.name,
                sb.name,
                t.last_name,
                t.first_name,
                COALESCE(t.phone, ''),
                COALESCE(t.email, '')
            FROM teacher_assignments ta
            JOIN teachers t ON t.id = ta.teacher_id
            JOIN classes c ON c.id = ta.class_id
            JOIN subjects sb ON sb.id = ta.subject_id
            WHERE {' AND '.join(where)}
            ORDER BY c.name, sb.name, t.last_name, t.first_name
            """,
            params,
        )
        headers = ["Classe", "Matière", "Nom", "Prénom", "Téléphone", "Email"]
        return headers, cursor.fetchall()

    def _load_class_enrollment_stats_rows(self, cursor, est_id, school_year_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        where = [
            "e.school_year_id = %s",
            "s.is_active = TRUE",
            "(c.name ILIKE %s OR COALESCE(c.level, '') ILIKE %s OR COALESCE(cy.name, '') ILIKE %s)",
        ]
        params: list[object] = [school_year_id, search, search, search]

        if class_id is not None:
            where.append("c.id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("c.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("c.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        cursor.execute(
            f"""
            SELECT
                c.name,
                COALESCE(c.level, ''),
                COALESCE(cy.name, ''),
                COUNT(DISTINCT s.id) AS total_students,
                COUNT(DISTINCT s.id) FILTER (WHERE s.gender = 'M') AS boys,
                COUNT(DISTINCT s.id) FILTER (WHERE s.gender = 'F') AS girls
            FROM classes c
            LEFT JOIN cycles cy ON cy.id = c.cycle_id
            JOIN enrollments e ON e.class_id = c.id
            JOIN students s ON s.id = e.student_id
            WHERE {' AND '.join(where)}
            GROUP BY c.id, c.name, c.level, cy.name
            ORDER BY c.name
            """,
            params,
        )
        headers = ["Classe", "Niveau", "Cycle", "Effectif", "Garçons", "Filles"]
        return headers, cursor.fetchall()

    def _load_students_without_photo_rows(self, cursor, est_id, school_year_id, class_id, search: str) -> tuple[list[str], list[tuple]]:
        where = [
            "e.school_year_id = %s",
            "s.is_active = TRUE",
            "(s.photo_path IS NULL OR BTRIM(s.photo_path) = '')",
            "(COALESCE(s.matricule, '') ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR c.name ILIKE %s)",
        ]
        params: list[object] = [school_year_id, search, search, search, search]

        if class_id is not None:
            where.append("c.id = %s")
            params.append(class_id)

        if self.is_global_admin:
            if est_id is not None:
                where.append("s.establishment_id = %s")
                params.append(est_id)
        else:
            where.append("s.establishment_id = %s")
            params.append(self.current_user["establishment_id"])

        cursor.execute(
            f"""
            SELECT
                s.matricule,
                s.last_name,
                s.first_name,
                s.gender,
                c.name
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            JOIN classes c ON c.id = e.class_id
            WHERE {' AND '.join(where)}
            ORDER BY c.name, s.last_name, s.first_name
            """,
            params,
        )
        headers = ["Matricule", "Nom", "Prénom", "Sexe", "Classe"]
        return headers, cursor.fetchall()

    def load_data(self):
        key = self.type_filter.currentData()
        est_id = self.establishment_filter.currentData()
        school_year_id = self.school_year_filter.currentData()
        term_id = self.term_filter.currentData()
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        search_text = self.search_input.text().strip()
        search = f"%{search_text}%"
        footer_lines: list[str] = []

        if key in CLASS_REQUIRED_TYPES and class_id is None:
            self._set_current_data([], [])
            return
        if key in TERM_FILTER_TYPES and term_id is None:
            self._set_current_data([], [])
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()

            if key == "STUDENTS_BY_CLASS":
                where = [
                    "e.school_year_id = %s",
                    "s.is_active = TRUE",
                    "(COALESCE(s.matricule, '') ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR c.name ILIKE %s)",
                ]
                params: list[object] = [school_year_id, search, search, search, search]
                if class_id is not None:
                    where.append("e.class_id = %s")
                    params.append(class_id)
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("s.establishment_id = %s")
                        params.append(est_id)
                else:
                    where.append("s.establishment_id = %s")
                    params.append(self.current_user["establishment_id"])
                cur.execute(
                    f"""
                    SELECT s.matricule, s.last_name, s.first_name, s.gender, c.name
                    FROM students s
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    WHERE {' AND '.join(where)}
                    ORDER BY s.last_name, s.first_name
                    """,
                    params,
                )
                headers = ["Matricule", "Nom", "Prénom", "Sexe", "Classe"]
                rows = cur.fetchall()
                if class_id is not None:
                    titular_name = self._get_class_titular_name(cur, int(class_id))
                    footer_lines.append(f"Titulaire de la classe : {titular_name or '-'}")

            elif key == "STUDENTS_REGULAR":
                headers, rows = self._load_payment_status_rows(cur, "regular", est_id, school_year_id, class_id, search)

            elif key == "STUDENTS_NOT_REGULAR":
                headers, rows = self._load_payment_status_rows(cur, "not_regular", est_id, school_year_id, class_id, search)

            elif key == "STUDENTS_PAYMENT_DELAY":
                headers, rows = self._load_payment_status_rows(cur, "delay", est_id, school_year_id, class_id, search)

            elif key == "GRADES_BY_CLASS":
                cycle_name, class_level = self._get_class_context(cur, int(class_id))
                if cycle_name == "Primaire":
                    headers, rows = self._load_primary_grade_rows(cur, int(class_id), int(term_id), int(school_year_id), search)
                else:
                    headers, rows = self._load_secondary_grade_rows(cur, int(class_id), int(term_id), int(school_year_id), search, class_level)

            elif key == "MISSING_GRADES_BY_CLASS":
                headers, rows = self._load_missing_grades_rows(cur, int(class_id), int(term_id), int(school_year_id), search, subject_id)

            elif key == "RESULTS_BY_CLASS":
                headers, rows = self._load_results_rows(cur, int(class_id), int(term_id), int(school_year_id), search, sort_by_rank=False)
                footer_lines = self._build_results_footer_lines(cur, int(class_id), int(term_id), int(school_year_id), search)

            elif key == "MERIT_RESULTS_BY_CLASS":
                headers, rows = self._load_results_rows(cur, int(class_id), int(term_id), int(school_year_id), search, sort_by_rank=True)
                footer_lines = self._build_results_footer_lines(cur, int(class_id), int(term_id), int(school_year_id), search)

            elif key == "ADMISSION_BY_CLASS":
                headers, rows = self._load_results_rows(cur, int(class_id), int(term_id), int(school_year_id), search, sort_by_rank=True)
                footer_lines = self._build_results_footer_lines(cur, int(class_id), int(term_id), int(school_year_id), search)

            elif key == "OPTIONAL_SUBJECT_STUDENTS":
                headers, rows = self._load_optional_subject_students_rows(cur, int(class_id), int(school_year_id), search, subject_id)

            elif key == "CLASS_PAYMENTS":
                headers, rows = self._load_class_payments_rows(cur, est_id, school_year_id, class_id, search)

            elif key == "DISCOUNTS_GRANTED":
                headers, rows = self._load_discounts_rows(cur, est_id, school_year_id, class_id, search)

            elif key == "TEACHERS_BY_CLASS_SUBJECT":
                headers, rows = self._load_teachers_by_class_subject_rows(cur, est_id, school_year_id, class_id, search)

            elif key == "CLASS_ENROLLMENT_STATS":
                headers, rows = self._load_class_enrollment_stats_rows(cur, est_id, school_year_id, class_id, search)

            elif key == "STUDENTS_WITHOUT_PHOTO":
                headers, rows = self._load_students_without_photo_rows(cur, est_id, school_year_id, class_id, search)

            elif key == "PAYMENT_RECEIPTS_PERIOD":
                headers, rows = self._load_payment_receipts_period_rows(cur, est_id, class_id, search)

            elif key == "ALL_STUDENTS":
                where = [
                    "s.is_active = TRUE",
                    "(COALESCE(s.matricule, '') ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s)",
                ]
                params = [search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("s.establishment_id = %s")
                        params.append(est_id)
                else:
                    where.append("s.establishment_id = %s")
                    params.append(self.current_user["establishment_id"])
                cur.execute(
                    f"""
                    SELECT s.matricule, s.last_name, s.first_name, s.gender
                    FROM students s
                    WHERE {' AND '.join(where)}
                    ORDER BY s.last_name, s.first_name
                    """,
                    params,
                )
                headers = ["Matricule", "Nom", "Prénom", "Sexe"]
                rows = cur.fetchall()

            elif key == "TEACHERS":
                where = [
                    "COALESCE(t.is_active, TRUE) = TRUE",
                    "(t.last_name ILIKE %s OR t.first_name ILIKE %s OR COALESCE(t.phone, '') ILIKE %s OR COALESCE(t.email, '') ILIKE %s)",
                ]
                params = [search, search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("t.establishment_id = %s")
                        params.append(est_id)
                else:
                    where.append("t.establishment_id = %s")
                    params.append(self.current_user["establishment_id"])
                cur.execute(
                    f"""
                    SELECT t.last_name, t.first_name, COALESCE(t.phone, ''), COALESCE(t.email, '')
                    FROM teachers t
                    WHERE {' AND '.join(where)}
                    ORDER BY t.last_name, t.first_name
                    """,
                    params,
                )
                headers = ["Nom", "Prénom", "Téléphone", "Email"]
                rows = cur.fetchall()

            elif key == "STAFF":
                where = [
                    "COALESCE(sm.is_active, TRUE) = TRUE",
                    "(sm.last_name ILIKE %s OR sm.first_name ILIKE %s OR COALESCE(sm.role_title, '') ILIKE %s OR COALESCE(sm.phone, '') ILIKE %s OR COALESCE(sm.email, '') ILIKE %s)",
                ]
                params = [search, search, search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("sm.establishment_id = %s")
                        params.append(est_id)
                else:
                    where.append("sm.establishment_id = %s")
                    params.append(self.current_user["establishment_id"])
                cur.execute(
                    f"""
                    SELECT sm.last_name, sm.first_name, sm.role_title, COALESCE(sm.phone, ''), COALESCE(sm.email, '')
                    FROM staff_members sm
                    WHERE {' AND '.join(where)}
                    ORDER BY sm.last_name, sm.first_name
                    """,
                    params,
                )
                headers = ["Nom", "Prénom", "Poste", "Téléphone", "Email"]
                rows = cur.fetchall()

            else:
                where = [
                    "(c.name ILIKE %s OR COALESCE(c.level, '') ILIKE %s OR COALESCE(cy.name, '') ILIKE %s OR e.name ILIKE %s)"
                ]
                params = [search, search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("c.establishment_id = %s")
                        params.append(est_id)
                else:
                    where.append("c.establishment_id = %s")
                    params.append(self.current_user["establishment_id"])
                cur.execute(
                    f"""
                    SELECT c.name, c.level, COALESCE(cy.name, ''), e.name
                    FROM classes c
                    LEFT JOIN cycles cy ON cy.id = c.cycle_id
                    JOIN establishments e ON e.id = c.establishment_id
                    WHERE {' AND '.join(where)}
                    ORDER BY e.name, c.name
                    """,
                    params,
                )
                headers = ["Classe", "Niveau", "Cycle", "Établissement"]
                rows = cur.fetchall()

            normalized_rows = [["" if value is None else str(value) for value in row] for row in rows]
            self._set_current_data(headers, normalized_rows, footer_lines=footer_lines)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def _fill_table(self):
        self.table.clear()
        self.table.setColumnCount(len(self.current_headers))
        if self.current_headers:
            self.table.setHorizontalHeaderLabels(self.current_headers)
        self.table.setRowCount(len(self.current_rows))
        for row_index, row in enumerate(self.current_rows):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def _update_summary(self):
        self.summary_type.setText(self.type_filter.currentText())
        scope_parts = [
            f"Établissement : {self.establishment_filter.currentText()}",
            f"Année : {self.school_year_filter.currentText()}",
        ]
        if self.term_filter.isEnabled():
            scope_parts.append(f"Trimestre : {self.term_filter.currentText()}")
        if self.class_filter.isEnabled():
            scope_parts.append(f"Classe : {self.class_filter.currentText()}")
        if self.subject_filter.isEnabled():
            scope_parts.append(f"Matière : {self.subject_filter.currentText()}")
        if self.start_date_filter.isEnabled() and self.end_date_filter.isEnabled():
            start_date, end_date = self._get_date_range()
            scope_parts.append(f"Période : {start_date} -> {end_date}")
        search_text = self.search_input.text().strip()
        if search_text:
            scope_parts.append(f"Recherche : {search_text}")
        self.summary_scope.setText(" | ".join(scope_parts))
        self.summary_count.setText(str(len(self.current_rows)))

    def export_csv(self):
        if not self.current_rows:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter")
            return

        os.makedirs("exports/lists", exist_ok=True)
        filename = f"exports/lists/{self.type_filter.currentData()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle, delimiter=";")
                writer.writerow(self.current_headers)
                writer.writerows(self.current_rows)
            QMessageBox.information(self, "Succès", f"CSV exporté : {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Export CSV impossible : {e}")

    def _get_pdf_school_identity(self) -> dict[str, str]:
        identity = {
            "school_name": "Établissement scolaire",
            "address": "-",
            "phone": "-",
            "email": "-",
            "logo_path": "",
        }

        conn = get_connection()
        if not conn:
            return identity

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    COALESCE(name, ''),
                    COALESCE(address, ''),
                    COALESCE(phone, ''),
                    COALESCE(email, ''),
                    COALESCE(logo_path, '')
                FROM school_info
                ORDER BY id
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row:
                identity["school_name"] = row[0] or identity["school_name"]
                identity["address"] = row[1] or "-"
                identity["phone"] = row[2] or "-"
                identity["email"] = row[3] or "-"
                identity["logo_path"] = row[4] or ""
        finally:
            conn.close()

        return identity

    def _build_pdf_header_story(self, styles, available_width: float) -> list:
        identity = self._get_pdf_school_identity()
        left_width = 150
        right_width = 150
        center_width = max(available_width - left_width - right_width, 220)

        left_block = Paragraph(
            "<para align='left'><b>MINISTERE DE</b><br/><b>L'EDUCATION NATIONALE</b></para>",
            styles["Normal"],
        )
        right_block = Paragraph(
            "<para align='right'><b>REPUBLIQUE TOGOLAISE</b><br/>Travail - Liberte - Patrie</para>",
            styles["Normal"],
        )

        center_flowables = []
        logo_path = (identity.get("logo_path") or "").replace("\\", "/")
        if logo_path:
            absolute_logo = logo_path if os.path.isabs(logo_path) else str(Path(logo_path).resolve())
            if os.path.exists(absolute_logo):
                try:
                    center_flowables.append(RLImage(absolute_logo, width=42, height=42))
                    center_flowables.append(Spacer(1, 4))
                except Exception:
                    pass

        center_flowables.append(
            Paragraph(
                f"<para align='center'><b>{identity['school_name']}</b></para>",
                styles["Title"],
            )
        )
        center_flowables.append(
            Paragraph(
                f"<para align='center'>{identity['address']}</para>",
                styles["Normal"],
            )
        )
        center_flowables.append(
            Paragraph(
                f"<para align='center'>Tel : {identity['phone']} | Email : {identity['email']}</para>",
                styles["Normal"],
            )
        )

        header_table = Table(
            [[left_block, center_flowables, right_block]],
            colWidths=[left_width, center_width, right_width],
        )
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                    ("LINEABOVE", (0, 0), (-1, 0), 1.8, colors.HexColor("#2563eb")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        subtitle_parts = [
            f"Établissement : {self.establishment_filter.currentText()}",
            f"Année scolaire : {self.school_year_filter.currentText()}",
        ]
        if self.term_filter.isEnabled():
            subtitle_parts.append(f"Trimestre : {self.term_filter.currentText()}")
        if self.class_filter.isEnabled():
            subtitle_parts.append(f"Classe : {self.class_filter.currentText()}")
        if self.subject_filter.isEnabled():
            subtitle_parts.append(f"Matière : {self.subject_filter.currentText()}")
        if self.start_date_filter.isEnabled() and self.end_date_filter.isEnabled():
            start_date, end_date = self._get_date_range()
            subtitle_parts.append(f"Période : {start_date} -> {end_date}")
        subtitle_parts.append(f"Imprimé le : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        return [
            header_table,
            Spacer(1, 10),
            Paragraph(
                f"<para align='center'><b>LISTE - {self.type_filter.currentText().upper()}</b></para>",
                styles["Title"],
            ),
            Spacer(1, 4),
            Paragraph(
                f"<para align='center'>{' | '.join(subtitle_parts)}</para>",
                styles["Normal"],
            ),
            Spacer(1, 12),
        ]

    def _build_pdf_table(self, available_width: float) -> Table:
        table_data = [self.current_headers] + self.current_rows
        column_count = len(self.current_headers)
        if column_count == 0:
            return Table([[]])

        weights: list[float] = []
        for col_index, header in enumerate(self.current_headers):
            column_values = [row[col_index] for row in self.current_rows if col_index < len(row)]
            max_len = max([len(header or "")] + [len(value or "") for value in column_values], default=8)
            if max_len <= 6:
                weight = 0.8
            elif max_len <= 10:
                weight = 1.0
            elif max_len <= 16:
                weight = 1.25
            elif max_len <= 24:
                weight = 1.55
            else:
                weight = 1.9
            weights.append(weight)

        total_weight = sum(weights) or float(column_count)
        col_widths = [(available_width * weight) / total_weight for weight in weights]

        if column_count <= 5:
            font_size = 9
        elif column_count <= 7:
            font_size = 8
        elif column_count <= 9:
            font_size = 7
        else:
            font_size = 6.2

        table = Table(table_data, repeatRows=1, colWidths=col_widths, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), font_size),
                    ("LEADING", (0, 0), (-1, -1), font_size + 1.2),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    def _build_grades_matrix_story(self, styles, available_width: float) -> list:
        if not self.current_rows:
            return []

        is_secondary = "Composition" in self.current_headers
        if is_secondary:
            table = self._build_secondary_grades_matrix_table(available_width)
        else:
            table = self._build_primary_grades_matrix_table(available_width)

        info_lines = [
            f"<b>Année scolaire :</b> {self.school_year_filter.currentText()}",
            f"<b>Évaluation :</b> {self.term_filter.currentText()}",
            f"<b>Classe :</b> {self.class_filter.currentText()}",
        ]

        story = [
            Paragraph("<para align='center'><b>DETAIL DES NOTES</b></para>", styles["Title"]),
            Spacer(1, 6),
        ]
        for line in info_lines:
            story.append(Paragraph(line, styles["Normal"]))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 6))
        story.append(table)
        return story

    def _build_primary_grades_matrix_table(self, available_width: float) -> Table:
        student_map: dict[tuple[str, str], dict[str, str]] = {}
        subjects: list[str] = []

        for row in self.current_rows:
            matricule, last_name, first_name, _gender, subject_name, score, _max_score = row
            student_key = (matricule, f"{last_name} {first_name}".strip())
            if student_key not in student_map:
                student_map[student_key] = {}
            student_map[student_key][subject_name] = score
            if subject_name not in subjects:
                subjects.append(subject_name)

        header_top = ["N°", "Nom élève"] + subjects
        header_bottom = ["", ""] + ["Note" for _ in subjects]
        table_data = [header_top, header_bottom]

        for index, ((_, student_name), grades_by_subject) in enumerate(student_map.items(), start=1):
            row = [str(index), student_name]
            for subject_name in subjects:
                row.append(grades_by_subject.get(subject_name, ""))
            table_data.append(row)

        no_width = 26
        name_width = 170
        remaining_width = max(available_width - no_width - name_width, 180)
        subject_width = remaining_width / max(len(subjects), 1)
        col_widths = [no_width, name_width] + [subject_width for _ in subjects]

        table = Table(table_data, repeatRows=2, colWidths=col_widths, hAlign="LEFT")
        style_commands = [
            ("SPAN", (0, 0), (0, 1)),
            ("SPAN", (1, 0), (1, 1)),
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#d1d5db")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 2), (1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ("LEADING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        table.setStyle(TableStyle(style_commands))
        return table

    def _build_secondary_grades_matrix_table(self, available_width: float) -> Table:
        student_map: dict[tuple[str, str], dict[str, tuple[str, str]]] = {}
        subjects: list[str] = []

        for row in self.current_rows:
            matricule, last_name, first_name, _gender, subject_name, _subject_type, _coef, classe_note, compo_note, _moyenne, _note_def = row
            student_key = (matricule, f"{last_name} {first_name}".strip())
            if student_key not in student_map:
                student_map[student_key] = {}
            student_map[student_key][subject_name] = (classe_note, compo_note)
            if subject_name not in subjects:
                subjects.append(subject_name)

        header_top = ["N°", "Nom élève"]
        header_bottom = ["", ""]
        for subject_name in subjects:
            header_top.extend([subject_name, ""])
            header_bottom.extend(["Classe", "Compo."])

        table_data = [header_top, header_bottom]
        for index, ((_, student_name), grades_by_subject) in enumerate(student_map.items(), start=1):
            row = [str(index), student_name]
            for subject_name in subjects:
                classe_note, compo_note = grades_by_subject.get(subject_name, ("", ""))
                row.extend([classe_note, compo_note])
            table_data.append(row)

        no_width = 24
        name_width = 180
        remaining_width = max(available_width - no_width - name_width, 220)
        subcol_count = max(len(subjects) * 2, 1)
        subject_sub_width = remaining_width / subcol_count
        col_widths = [no_width, name_width]
        for _subject_name in subjects:
            col_widths.extend([subject_sub_width, subject_sub_width])

        table = Table(table_data, repeatRows=2, colWidths=col_widths, hAlign="LEFT")
        style_commands = [
            ("SPAN", (0, 0), (0, 1)),
            ("SPAN", (1, 0), (1, 1)),
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#d1d5db")),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 2), (1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6.2),
            ("FONTSIZE", (0, 1), (-1, -1), 5.8),
            ("LEADING", (0, 0), (-1, -1), 6.8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]
        col_index = 2
        for _subject_name in subjects:
            style_commands.append(("SPAN", (col_index, 0), (col_index + 1, 0)))
            col_index += 2
        table.setStyle(TableStyle(style_commands))
        return table

    def _generate_pdf(self):
        if not self.current_rows:
            raise ValueError("Aucune donnée à imprimer")

        os.makedirs("prints/lists", exist_ok=True)
        filename = f"prints/lists/{self.type_filter.currentData()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        is_grades_list = self.type_filter.currentData() == "GRADES_BY_CLASS"

        doc = SimpleDocTemplate(
            filename,
            pagesize=landscape(A4) if is_grades_list else A4,
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
        )
        styles = getSampleStyleSheet()

        story = self._build_pdf_header_story(styles, doc.width)
        if is_grades_list:
            story.extend(self._build_grades_matrix_story(styles, doc.width))
        else:
            story.append(self._build_pdf_table(doc.width))
        if self.current_footer_lines:
            story.append(Spacer(1, 14))
            for line in self.current_footer_lines:
                story.append(Paragraph(f"<b>{line}</b>", styles["Normal"]))
                story.append(Spacer(1, 4))
        doc.build(story)
        return filename

    def preview_pdf(self):
        try:
            filepath = self._generate_pdf()
            preview_pdf_file(self, filepath)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Aperçu impossible : {e}")

    def print_current(self):
        try:
            filepath = self._generate_pdf()
            print_pdf_file(self, filepath, "Liste envoyée à l'impression.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impression impossible : {e}")
