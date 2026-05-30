import os
import traceback
import unicodedata
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QScrollArea,
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.connection import get_connection
from utils.expense_service import ensure_expenses_table
from utils.qt_printing import preview_pdf_file, print_pdf_file
from utils.salary_service import ensure_salary_table
from utils.teacher_service import ensure_teacher_schema
from utils.table_style import setup_table


class StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")
        self.value_label = QLabel("0")
        self.value_label.setObjectName("statValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)


class SimpleBarChart(QFrame):
    def __init__(self, title: str, color: str = "#2563eb", value_suffix: str = "", precision: int = 0):
        super().__init__()
        self.title = title
        self.bar_color = QColor(color)
        self.value_suffix = value_suffix
        self.precision = precision
        self.labels = []
        self.values = []
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("chartFrame")

    def set_data(self, labels, values):
        self.labels = labels or []
        self.values = values or []
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        title_rect = rect.adjusted(0, 0, 0, -rect.height() + 26)
        painter.setPen(QColor("#111827"))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

        chart_rect = rect.adjusted(10, 36, -10, -22)
        axis_pen = QPen(QColor("#cbd5e1"))
        painter.setPen(axis_pen)
        painter.drawLine(chart_rect.left(), chart_rect.bottom(), chart_rect.right(), chart_rect.bottom())

        if not self.labels or not self.values:
            return

        count = min(len(self.labels), len(self.values))
        if count <= 0:
            return

        safe_labels = self.labels[:count]
        safe_values = self.values[:count]

        max_val = max(safe_values) if safe_values else 0
        if max_val <= 0:
            return

        n = len(safe_values)
        spacing = 8
        bar_width = max(14, int((chart_rect.width() - spacing * (n - 1)) / n))
        x = chart_rect.left()

        for i, value in enumerate(safe_values):
            h = int((value / max_val) * (chart_rect.height() - 26))
            bar_top = chart_rect.bottom() - h

            painter.fillRect(x, bar_top, bar_width, h, self.bar_color)

            painter.setPen(QColor("#1f2937"))
            short_label = str(safe_labels[i])[:8]
            if self.precision > 0:
                value_text = f"{value:.{self.precision}f}{self.value_suffix}"
            else:
                value_text = f"{value:,.0f}{self.value_suffix}"
            painter.drawText(x, chart_rect.bottom() + 14, bar_width, 12, Qt.AlignmentFlag.AlignCenter, short_label)
            painter.drawText(x, bar_top - 14, bar_width, 12, Qt.AlignmentFlag.AlignCenter, value_text)
            x += bar_width + spacing


class StatisticsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_teacher_schema()
        ensure_salary_table()
        ensure_expenses_table()

        self.root_layout = QVBoxLayout()
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("statsContent")
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        filters = QHBoxLayout()
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()
        self.civil_year_filter = QComboBox()
        self.refresh_btn = QPushButton("Actualiser")

        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Année scolaire"))
        filters.addWidget(self.school_year_filter)
        filters.addWidget(QLabel("Année civile"))
        filters.addWidget(self.civil_year_filter)
        filters.addWidget(self.refresh_btn)

        self.cards_grid = QGridLayout()
        self.students_card = StatCard("Élèves actifs")
        self.teachers_card = StatCard("Enseignants actifs")
        self.staff_card = StatCard("Employés actifs")
        self.payments_month_card = StatCard("Encaissement du mois")
        self.expenses_month_card = StatCard("Dépenses du mois")
        self.net_month_card = StatCard("Solde net du mois")
        self.recovery_rate_card = StatCard("Taux de recouvrement global")
        self.success_rate_card = StatCard("Taux de réussite global")

        self.cards_grid.addWidget(self.students_card, 0, 0)
        self.cards_grid.addWidget(self.teachers_card, 0, 1)
        self.cards_grid.addWidget(self.staff_card, 0, 2)
        self.cards_grid.addWidget(self.payments_month_card, 1, 0)
        self.cards_grid.addWidget(self.expenses_month_card, 1, 1)
        self.cards_grid.addWidget(self.net_month_card, 1, 2)
        self.cards_grid.addWidget(self.recovery_rate_card, 2, 0)
        self.cards_grid.addWidget(self.success_rate_card, 2, 1)

        self.levels_label = QLabel("Synthèse par niveau")
        self.levels_chart = SimpleBarChart("Taux de recouvrement par niveau (%)", "#0ea5e9", "%", 1)
        self.levels_table = QTableWidget()
        self.levels_table.setColumnCount(5)
        self.levels_table.setHorizontalHeaderLabels(["Niveau", "Élèves", "Encaissement", "Reste à payer", "Taux recouvrement"])
        self.levels_table.setMaximumHeight(210)
        setup_table(self.levels_table)

        self.trend_label = QLabel("Tendance mensuelle (encaissements)")
        self.trend_chart = SimpleBarChart("Encaissements mensuels", "#2563eb")
        self.trend_table = QTableWidget()
        self.trend_table.setColumnCount(2)
        self.trend_table.setHorizontalHeaderLabels(["Mois", "Montant encaissé"])
        self.trend_table.setMaximumHeight(180)
        setup_table(self.trend_table)
        self.success_by_level_label = QLabel("Taux de réussite par niveau")
        self.success_by_level_chart = SimpleBarChart("Réussite par niveau (%)", "#16a34a", "%", 1)
        self.success_by_level_table = QTableWidget()
        self.success_by_level_table.setColumnCount(4)
        self.success_by_level_table.setHorizontalHeaderLabels(["Niveau", "Évalués", "Réussites", "Taux"])
        self.success_by_level_table.setMaximumHeight(190)
        setup_table(self.success_by_level_table)
        self.success_by_term_label = QLabel("Taux de réussite par trimestre")
        self.success_by_term_chart = SimpleBarChart("Réussite par trimestre (%)", "#f59e0b", "%", 1)
        self.success_by_term_table = QTableWidget()
        self.success_by_term_table.setColumnCount(4)
        self.success_by_term_table.setHorizontalHeaderLabels(["Trimestre", "Évalués", "Réussites", "Taux"])
        self.success_by_term_table.setMaximumHeight(190)
        setup_table(self.success_by_term_table)

        actions = QHBoxLayout()
        self.preview_btn = QPushButton("Aperçu PDF")
        self.print_btn = QPushButton("Imprimer")
        self.preview_btn.setObjectName("statsActionBtn")
        self.print_btn.setObjectName("statsActionBtn")
        actions.addWidget(self.preview_btn)
        actions.addWidget(self.print_btn)

        self.layout.addLayout(filters)
        self.layout.addLayout(self.cards_grid)
        self.layout.addWidget(self.levels_label)
        self.layout.addWidget(self.levels_chart)
        self.layout.addWidget(self.levels_table)
        self.layout.addWidget(self.trend_label)
        self.layout.addWidget(self.trend_chart)
        self.layout.addWidget(self.trend_table)
        self.layout.addWidget(self.success_by_level_label)
        self.layout.addWidget(self.success_by_level_chart)
        self.layout.addWidget(self.success_by_level_table)
        self.layout.addWidget(self.success_by_term_label)
        self.layout.addWidget(self.success_by_term_chart)
        self.layout.addWidget(self.success_by_term_table)
        self.layout.addLayout(actions)
        self.scroll_area.setWidget(self.content_widget)
        self.root_layout.addWidget(self.scroll_area)
        self.setLayout(self.root_layout)

        self.apply_local_style()

        self.refresh_btn.clicked.connect(self.load_statistics)
        self.establishment_filter.currentIndexChanged.connect(self.load_statistics)
        self.school_year_filter.currentIndexChanged.connect(self.load_statistics)
        self.civil_year_filter.currentIndexChanged.connect(self.load_statistics)
        self.preview_btn.clicked.connect(self.preview_pdf)
        self.print_btn.clicked.connect(self.print_current)

        self.load_filters()
        self.load_statistics()

    def apply_local_style(self):
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#statCard { background: white; border: 1px solid #e5e7eb; border-radius: 10px; }
            QLabel#statTitle { color: #6b7280; font-size: 12px; }
            QLabel#statValue { color: #111827; font-size: 22px; font-weight: bold; }
            QFrame#chartFrame { background: white; border: 1px solid #e5e7eb; border-radius: 10px; }
            QWidget#statsContent { background: #f1f5f9; }
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
            QPushButton#statsActionBtn {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton#statsActionBtn:hover { background-color: #1d4ed8; }
            QPushButton#statsActionBtn:pressed { background-color: #1e40af; }
            """
        )

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
            cur.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for sy_id, label in cur.fetchall():
                self.school_year_filter.addItem(label, sy_id)

            self.civil_year_filter.clear()
            current_year = datetime.now().year
            for y in range(current_year - 2, current_year + 3):
                self.civil_year_filter.addItem(str(y), y)
            self.civil_year_filter.setCurrentText(str(current_year))
        finally:
            conn.close()

    def _get_reference_month_and_year(self, civil_year):
        now = datetime.now()
        month = int(now.month)
        year = int(civil_year or now.year)
        return month, year

    def _set_month_card_titles(self, month: int, year: int):
        month_names = [
            "Janvier",
            "Février",
            "Mars",
            "Avril",
            "Mai",
            "Juin",
            "Juillet",
            "Août",
            "Septembre",
            "Octobre",
            "Novembre",
            "Décembre",
        ]
        label = f"{month_names[max(1, min(month, 12)) - 1]} {year}"
        self.payments_month_card.title_label.setText(f"Encaissement du mois ({label})")
        self.expenses_month_card.title_label.setText(f"Dépenses du mois ({label})")
        self.net_month_card.title_label.setText(f"Solde net du mois ({label})")

    def _normalize_level_name(self, level_name: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(level_name or ""))
        return "".join(char for char in normalized if not unicodedata.combining(char)).lower()

    def _load_level_recovery_rows(self, cursor, school_year_id: int, est_id):
        params = [school_year_id, school_year_id, school_year_id]
        est_filter = ""
        if est_id is not None:
            est_filter = " AND s.establishment_id = %s"
            params.append(est_id)

        cursor.execute(
            f"""
            WITH enrolled_students AS (
                SELECT DISTINCT
                    s.id AS student_id,
                    e.class_id
                FROM students s
                JOIN enrollments e ON e.student_id = s.id
                WHERE e.school_year_id = %s
                  AND s.is_active = TRUE
                  {est_filter}
            ),
            student_fee_lines AS (
                SELECT
                    es.student_id,
                    es.class_id,
                    COALESCE(cf.amount, 0) AS expected_amount,
                    COALESCE(sd.discount_amount, 0) AS discount_amount,
                    COALESCE(pp.paid_amount, 0) AS paid_amount
                FROM enrolled_students es
                JOIN class_fees cf
                    ON cf.class_id = es.class_id
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
                    ON sd.student_id = es.student_id
                   AND sd.fee_id = cf.fee_id
                LEFT JOIN (
                    SELECT
                        student_id,
                        class_fee_id,
                        SUM(amount) AS paid_amount
                    FROM payments
                    GROUP BY student_id, class_fee_id
                ) pp
                    ON pp.student_id = es.student_id
                   AND pp.class_fee_id = cf.id
            ),
            student_finance AS (
                SELECT
                    es.student_id,
                    es.class_id,
                    GREATEST(
                        COALESCE(SUM(sfl.expected_amount - sfl.discount_amount), 0),
                        0
                    ) AS due_total,
                    LEAST(
                        COALESCE(SUM(sfl.paid_amount), 0),
                        GREATEST(COALESCE(SUM(sfl.expected_amount - sfl.discount_amount), 0), 0)
                    ) AS paid_total,
                    GREATEST(
                        COALESCE(SUM(sfl.expected_amount - sfl.discount_amount - sfl.paid_amount), 0),
                        0
                    ) AS remaining_total
                FROM enrolled_students es
                LEFT JOIN student_fee_lines sfl
                    ON sfl.student_id = es.student_id
                   AND sfl.class_id = es.class_id
                GROUP BY es.student_id, es.class_id
            )
            SELECT
                COALESCE(cy.name, 'Non défini') AS level_name,
                COUNT(DISTINCT sf.student_id) AS students_count,
                COALESCE(SUM(sf.due_total), 0) AS due_amount,
                COALESCE(SUM(sf.paid_total), 0) AS paid_amount,
                COALESCE(SUM(sf.remaining_total), 0) AS remaining_amount
            FROM student_finance sf
            JOIN classes c ON c.id = sf.class_id
            LEFT JOIN cycles cy ON cy.id = c.cycle_id
            GROUP BY COALESCE(cy.name, 'Non défini')
            ORDER BY level_name
            """,
            params,
        )
        return cursor.fetchall()

    def _load_success_statistics(self, cursor, school_year_id: int, est_id):
        est_filter = ""
        primary_params = [school_year_id]
        secondary_params = [school_year_id]
        if est_id is not None:
            est_filter = " AND s.establishment_id = %s"
            primary_params.append(est_id)
            secondary_params.append(est_id)

        primary_cycle_condition = "LOWER(COALESCE(cy.name, '')) = 'primaire'"
        secondary_cycle_condition = "LOWER(COALESCE(cy.name, '')) <> 'primaire'"
        student_based_optional_condition = """
            LOWER(COALESCE(st.class_level, '')) LIKE '%%3eme%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%3ème%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%seconde%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%2nde%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%premiere%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%première%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%1ere%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%1ère%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%terminale%%'
            OR LOWER(COALESCE(st.class_level, '')) LIKE '%%tle%%'
        """

        cursor.execute(
            f"""
            WITH class_subject_names AS (
                SELECT
                    cs.class_id,
                    sb.name AS subject_name
                FROM class_subjects cs
                JOIN subjects sb ON sb.id = cs.subject_id
                GROUP BY cs.class_id, sb.name
            ),
            student_terms AS (
                SELECT DISTINCT
                    e.student_id,
                    e.class_id,
                    COALESCE(cy.name, 'Non défini') AS level_name,
                    t.id AS term_id,
                    t.name AS term_name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                JOIN classes c ON c.id = e.class_id
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                JOIN terms t ON t.school_year_id = e.school_year_id
                WHERE e.school_year_id = %s
                  AND s.is_active = TRUE
                  AND {primary_cycle_condition}
                  {est_filter}
                  AND EXISTS (
                        SELECT 1
                        FROM grades g
                        WHERE g.student_id = e.student_id
                          AND g.term_id = t.id
                    )
            ),
            subject_scores AS (
                SELECT
                    st.level_name,
                    st.term_id,
                    st.term_name,
                    st.student_id,
                    csn.subject_name,
                    COALESCE(MAX(CASE WHEN gs.name = csn.subject_name THEN g.value END), 0) AS score
                FROM student_terms st
                JOIN class_subject_names csn ON csn.class_id = st.class_id
                LEFT JOIN grades g
                    ON g.student_id = st.student_id
                   AND g.term_id = st.term_id
                LEFT JOIN subjects gs ON gs.id = g.subject_id
                GROUP BY st.level_name, st.term_id, st.term_name, st.student_id, csn.subject_name
            ),
            student_averages AS (
                SELECT
                    level_name,
                    term_id,
                    term_name,
                    student_id,
                    AVG(score) AS average_score
                FROM subject_scores
                GROUP BY level_name, term_id, term_name, student_id
            )
            SELECT
                level_name,
                term_id,
                term_name,
                COUNT(*) AS evaluated_count,
                SUM(CASE WHEN average_score >= 5 THEN 1 ELSE 0 END) AS success_count
            FROM student_averages
            GROUP BY level_name, term_id, term_name
            ORDER BY term_id, level_name
            """,
            primary_params,
        )
        primary_rows = cursor.fetchall()

        cursor.execute(
            f"""
            WITH student_terms AS (
                SELECT DISTINCT
                    e.student_id,
                    e.class_id,
                    e.school_year_id,
                    COALESCE(c.level, '') AS class_level,
                    COALESCE(cy.name, 'Non défini') AS level_name,
                    t.id AS term_id,
                    t.name AS term_name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                JOIN classes c ON c.id = e.class_id
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                JOIN terms t ON t.school_year_id = e.school_year_id
                WHERE e.school_year_id = %s
                  AND s.is_active = TRUE
                  AND {secondary_cycle_condition}
                  {est_filter}
                  AND EXISTS (
                        SELECT 1
                        FROM grades g
                        WHERE g.student_id = e.student_id
                          AND g.term_id = t.id
                    )
            ),
            applicable_subjects AS (
                SELECT
                    st.level_name,
                    st.term_id,
                    st.term_name,
                    st.student_id,
                    cs.subject_id,
                    COALESCE(cs.coefficient, 1) AS coefficient,
                    COALESCE(cs.subject_type, 'OBLIGATOIRE') AS subject_type
                FROM student_terms st
                JOIN class_subjects cs ON cs.class_id = st.class_id
                WHERE (
                        COALESCE(cs.subject_type, 'OBLIGATOIRE') <> 'FACULTATIVE'
                        OR NOT ({student_based_optional_condition})
                        OR EXISTS (
                            SELECT 1
                            FROM student_optional_subjects sos
                            WHERE sos.student_id = st.student_id
                              AND sos.class_subject_id = cs.id
                              AND sos.school_year_id = st.school_year_id
                        )
                    )
            ),
            subject_scores AS (
                SELECT
                    aps.level_name,
                    aps.term_id,
                    aps.term_name,
                    aps.student_id,
                    aps.subject_id,
                    aps.coefficient,
                    aps.subject_type,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'classe' THEN g.value END), 0) AS classe_note,
                    COALESCE(MAX(CASE WHEN g.grade_type = 'compo' THEN g.value END), 0) AS compo_note
                FROM applicable_subjects aps
                LEFT JOIN grades g
                    ON g.student_id = aps.student_id
                   AND g.term_id = aps.term_id
                   AND g.subject_id = aps.subject_id
                GROUP BY
                    aps.level_name,
                    aps.term_id,
                    aps.term_name,
                    aps.student_id,
                    aps.subject_id,
                    aps.coefficient,
                    aps.subject_type
            ),
            student_totals AS (
                SELECT
                    level_name,
                    term_id,
                    term_name,
                    student_id,
                    SUM(CASE WHEN subject_type <> 'FACULTATIVE' THEN coefficient ELSE 0 END) AS mandatory_total_coef,
                    SUM(CASE WHEN subject_type <> 'FACULTATIVE' THEN ((classe_note + compo_note) / 2.0) * coefficient ELSE 0 END) AS mandatory_total_notes,
                    SUM(CASE WHEN subject_type = 'FACULTATIVE' THEN coefficient ELSE 0 END) AS optional_total_coef,
                    SUM(CASE WHEN subject_type = 'FACULTATIVE' THEN ((classe_note + compo_note) / 2.0) * coefficient ELSE 0 END) AS optional_total_notes
                FROM subject_scores
                GROUP BY level_name, term_id, term_name, student_id
            ),
            student_averages AS (
                SELECT
                    level_name,
                    term_id,
                    term_name,
                    student_id,
                    CASE
                        WHEN mandatory_total_coef > 0 THEN
                            (
                                mandatory_total_notes
                                + CASE
                                    WHEN optional_total_coef > 0 THEN GREATEST(FLOOR(optional_total_notes / optional_total_coef) - 10, 0)
                                    ELSE 0
                                  END
                            ) / mandatory_total_coef
                        ELSE 0
                    END AS general_average
                FROM student_totals
            )
            SELECT
                level_name,
                term_id,
                term_name,
                COUNT(*) AS evaluated_count,
                SUM(CASE WHEN general_average >= 10 THEN 1 ELSE 0 END) AS success_count
            FROM student_averages
            GROUP BY level_name, term_id, term_name
            ORDER BY term_id, level_name
            """,
            secondary_params,
        )
        secondary_rows = cursor.fetchall()

        level_stats = defaultdict(lambda: {"evaluated": 0, "success": 0})
        term_stats = {}
        total_success = 0
        total_evaluated = 0

        for level_name, term_id, term_name, evaluated_count, success_count in [*primary_rows, *secondary_rows]:
            evaluated_count = int(evaluated_count or 0)
            success_count = int(success_count or 0)
            level_stats[level_name]["evaluated"] += evaluated_count
            level_stats[level_name]["success"] += success_count

            if term_id not in term_stats:
                term_stats[term_id] = {"name": term_name, "evaluated": 0, "success": 0}
            term_stats[term_id]["evaluated"] += evaluated_count
            term_stats[term_id]["success"] += success_count

            total_evaluated += evaluated_count
            total_success += success_count

        level_rows = []
        for level_name in sorted(level_stats.keys(), key=lambda value: self._normalize_level_name(value)):
            stats = level_stats[level_name]
            level_rows.append((level_name, stats["success"], stats["evaluated"]))

        term_rows = []
        for term_id in sorted(term_stats.keys()):
            stats = term_stats[term_id]
            term_rows.append((term_id, stats["name"], stats["success"], stats["evaluated"]))

        return level_rows, term_rows, total_success, total_evaluated

    def _reset_trend_widgets(self):
        self.trend_table.setRowCount(0)
        self.trend_chart.set_data([], [])

    def _reset_success_widgets(self):
        self.success_by_level_table.setRowCount(0)
        self.success_by_term_table.setRowCount(0)
        self.success_by_level_chart.set_data([], [])
        self.success_by_term_chart.set_data([], [])
        self.success_rate_card.value_label.setText("0.0%")

    def load_statistics(self):
        est_id = self.establishment_filter.currentData()
        school_year_id = self.school_year_filter.currentData()
        civil_year = self.civil_year_filter.currentData()

        if school_year_id is None:
            self.levels_chart.set_data([], [])
            self.trend_chart.set_data([], [])
            self.success_by_level_chart.set_data([], [])
            self.success_by_term_chart.set_data([], [])
            self.levels_table.setRowCount(0)
            self.trend_table.setRowCount(0)
            self.success_by_level_table.setRowCount(0)
            self.success_by_term_table.setRowCount(0)
            self.recovery_rate_card.value_label.setText("0.0%")
            self.success_rate_card.value_label.setText("0.0%")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()

            # Cards
            student_sql = "SELECT COUNT(*) FROM students WHERE is_active=TRUE"
            teacher_sql = "SELECT COUNT(*) FROM teachers WHERE COALESCE(is_active, TRUE)=TRUE"
            staff_sql = "SELECT COUNT(*) FROM staff_members WHERE COALESCE(is_active, TRUE)=TRUE"
            params = []

            if est_id is not None:
                student_sql += " AND establishment_id=%s"
                teacher_sql += " AND establishment_id=%s"
                staff_sql += " AND establishment_id=%s"
                params = [est_id]

            cur.execute(student_sql, params)
            self.students_card.value_label.setText(str(cur.fetchone()[0] or 0))
            cur.execute(teacher_sql, params)
            self.teachers_card.value_label.setText(str(cur.fetchone()[0] or 0))
            cur.execute(staff_sql, params)
            self.staff_card.value_label.setText(str(cur.fetchone()[0] or 0))

            ref_month, ref_year = self._get_reference_month_and_year(civil_year)
            self._set_month_card_titles(ref_month, ref_year)

            payment_where = ["EXTRACT(MONTH FROM p.payment_date) = %s", "EXTRACT(YEAR FROM p.payment_date) = %s"]
            payment_params = [ref_month, ref_year]
            if est_id is not None:
                payment_where.append("s.establishment_id=%s")
                payment_params.append(est_id)

            cur.execute(
                f"""
                SELECT COALESCE(SUM(p.amount),0)
                FROM payments p
                JOIN students s ON s.id = p.student_id
                WHERE {' AND '.join(payment_where)}
                """,
                payment_params,
            )
            enc_month = float(cur.fetchone()[0] or 0)

            expense_where = ["EXTRACT(MONTH FROM e.expense_date) = %s", "EXTRACT(YEAR FROM e.expense_date) = %s"]
            expense_params = [ref_month, ref_year]
            if est_id is not None:
                expense_where.append("e.establishment_id=%s")
                expense_params.append(est_id)
            cur.execute(
                f"""
                SELECT COALESCE(SUM(e.amount),0)
                FROM expenses e
                WHERE {' AND '.join(expense_where)}
                """,
                expense_params,
            )
            dep_month = float(cur.fetchone()[0] or 0)

            salary_where = ["EXTRACT(MONTH FROM sp.payment_date) = %s", "EXTRACT(YEAR FROM sp.payment_date) = %s"]
            salary_params = [ref_month, ref_year]
            if est_id is not None:
                salary_where.append("sp.establishment_id=%s")
                salary_params.append(est_id)
            cur.execute(
                f"""
                SELECT COALESCE(SUM(sp.amount), 0)
                FROM salary_payments sp
                WHERE {' AND '.join(salary_where)}
                """,
                salary_params,
            )
            dep_month += float(cur.fetchone()[0] or 0)

            self.payments_month_card.value_label.setText(f"{enc_month:,.0f} FCFA")
            self.expenses_month_card.value_label.setText(f"{dep_month:,.0f} FCFA")
            self.net_month_card.value_label.setText(f"{(enc_month - dep_month):,.0f} FCFA")

            level_rows = self._load_level_recovery_rows(cur, school_year_id, est_id)

            self.levels_table.setRowCount(len(level_rows))
            level_labels = []
            level_rates = []
            total_due = 0.0
            total_paid = 0.0
            for i, (level, count_students, due, paid, remaining) in enumerate(level_rows):
                due = float(due or 0)
                paid = float(paid or 0)
                remaining = float(remaining or 0)
                rate = (paid / due * 100.0) if due > 0 else 0.0
                total_due += due
                total_paid += paid

                vals = [
                    str(level),
                    str(count_students),
                    f"{paid:,.0f}",
                    f"{remaining:,.0f}",
                    f"{rate:.1f}%",
                ]
                for j, val in enumerate(vals):
                    self.levels_table.setItem(i, j, QTableWidgetItem(val))
                level_labels.append(str(level))
                level_rates.append(float(rate))

            self.levels_chart.set_data(level_labels, level_rates)
            global_recovery = (total_paid / total_due * 100.0) if total_due > 0 else 0.0
            self.recovery_rate_card.value_label.setText(f"{global_recovery:.1f}%")

            try:
                trend_where = ["EXTRACT(YEAR FROM p.payment_date) = %s"]
                trend_params = [civil_year]
                if est_id is not None:
                    trend_where.append("s.establishment_id=%s")
                    trend_params.append(est_id)

                cur.execute(
                    f"""
                    SELECT EXTRACT(MONTH FROM p.payment_date)::int AS month_no,
                           COALESCE(SUM(p.amount),0)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    WHERE {' AND '.join(trend_where)}
                    GROUP BY month_no
                    ORDER BY month_no
                    """,
                    trend_params,
                )
                trend_rows = cur.fetchall()

                self.trend_table.setRowCount(len(trend_rows))
                month_names = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aou", "Sep", "Oct", "Nov", "Dec"]
                month_amounts = {m: 0.0 for m in range(1, 13)}
                for i, (month_no, amount) in enumerate(trend_rows):
                    month_idx = max(1, min(12, int(month_no or 1)))
                    amount_val = float(amount)
                    self.trend_table.setItem(i, 0, QTableWidgetItem(month_names[month_idx - 1]))
                    self.trend_table.setItem(i, 1, QTableWidgetItem(f"{amount_val:,.0f}"))
                    month_amounts[month_idx] = amount_val

                self.trend_chart.set_data(
                    month_names,
                    [month_amounts[m] for m in range(1, 13)],
                )
            except Exception:
                self._reset_trend_widgets()
                traceback.print_exc()

            try:
                success_rows, term_success_rows, total_success_count, total_evaluated_count = self._load_success_statistics(
                    cur,
                    school_year_id,
                    est_id,
                )
                success_level_labels = []
                success_level_rates = []
                self.success_by_level_table.setRowCount(len(success_rows))
                for index, (level_name, success_count, evaluated_count) in enumerate(success_rows):
                    success_count = float(success_count or 0)
                    evaluated_count = float(evaluated_count or 0)
                    rate = (success_count * 100.0 / evaluated_count) if evaluated_count else 0.0
                    row_values = [
                        str(level_name),
                        f"{evaluated_count:.0f}",
                        f"{success_count:.0f}",
                        f"{rate:.1f}%",
                    ]
                    for column_index, value in enumerate(row_values):
                        self.success_by_level_table.setItem(index, column_index, QTableWidgetItem(value))
                    success_level_labels.append(str(level_name))
                    success_level_rates.append(round(rate, 1))
                self.success_by_level_chart.set_data(success_level_labels, success_level_rates)
                global_success_rate = (total_success_count * 100.0 / total_evaluated_count) if total_evaluated_count else 0.0
                self.success_rate_card.value_label.setText(f"{global_success_rate:.1f}%")

                term_labels = []
                term_rates = []
                self.success_by_term_table.setRowCount(len(term_success_rows))
                for index, (_, term_name, success_count, evaluated_count) in enumerate(term_success_rows):
                    success_count = float(success_count or 0)
                    evaluated_count = float(evaluated_count or 0)
                    rate = (success_count * 100.0 / evaluated_count) if evaluated_count else 0.0
                    row_values = [
                        str(term_name),
                        f"{evaluated_count:.0f}",
                        f"{success_count:.0f}",
                        f"{rate:.1f}%",
                    ]
                    for column_index, value in enumerate(row_values):
                        self.success_by_term_table.setItem(index, column_index, QTableWidgetItem(value))
                    term_labels.append(str(term_name))
                    term_rates.append(round(rate, 1))
                self.success_by_term_chart.set_data(term_labels, term_rates)
            except Exception:
                self._reset_success_widgets()
                traceback.print_exc()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement statistiques impossible : {e}")
        finally:
            conn.close()

    def _generate_pdf(self):
        os.makedirs("prints/statistics", exist_ok=True)
        filepath = f"prints/statistics/statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        levels_headers = [self.levels_table.horizontalHeaderItem(i).text() for i in range(self.levels_table.columnCount())]
        levels_rows = []
        for r in range(self.levels_table.rowCount()):
            levels_rows.append([
                self.levels_table.item(r, c).text() if self.levels_table.item(r, c) else ""
                for c in range(self.levels_table.columnCount())
            ])

        trend_headers = [self.trend_table.horizontalHeaderItem(i).text() for i in range(self.trend_table.columnCount())]
        trend_rows = []
        for r in range(self.trend_table.rowCount()):
            trend_rows.append([
                self.trend_table.item(r, c).text() if self.trend_table.item(r, c) else ""
                for c in range(self.trend_table.columnCount())
            ])

        success_level_headers = [
            self.success_by_level_table.horizontalHeaderItem(i).text()
            for i in range(self.success_by_level_table.columnCount())
        ]
        success_level_rows = []
        for r in range(self.success_by_level_table.rowCount()):
            success_level_rows.append([
                self.success_by_level_table.item(r, c).text() if self.success_by_level_table.item(r, c) else ""
                for c in range(self.success_by_level_table.columnCount())
            ])

        success_term_headers = [
            self.success_by_term_table.horizontalHeaderItem(i).text()
            for i in range(self.success_by_term_table.columnCount())
        ]
        success_term_rows = []
        for r in range(self.success_by_term_table.rowCount()):
            success_term_rows.append([
                self.success_by_term_table.item(r, c).text() if self.success_by_term_table.item(r, c) else ""
                for c in range(self.success_by_term_table.columnCount())
            ])

        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
        styles = getSampleStyleSheet()

        def make_table(data):
            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ]
                )
            )
            return table

        story = [
            Paragraph("<b>Statistiques</b>", styles["Title"]),
            Spacer(1, 8),
            Paragraph(
                f"Établissement: {self.establishment_filter.currentText()} | "
                f"Année scolaire: {self.school_year_filter.currentText()} | "
                f"Année civile: {self.civil_year_filter.currentText()}",
                styles["Normal"],
            ),
            Spacer(1, 12),
            Paragraph("<b>Synthèse par niveau</b>", styles["Heading3"]),
            make_table([levels_headers] + (levels_rows or [["-", "-", "-", "-", "-"]])),
            Spacer(1, 12),
            Paragraph("<b>Tendance mensuelle</b>", styles["Heading3"]),
            make_table([trend_headers] + (trend_rows or [["-", "-"]])),
            Spacer(1, 12),
            Paragraph("<b>Réussite par niveau</b>", styles["Heading3"]),
            make_table([success_level_headers] + (success_level_rows or [["-", "-", "-", "-"]])),
            Spacer(1, 12),
            Paragraph("<b>Réussite par trimestre</b>", styles["Heading3"]),
            make_table([success_term_headers] + (success_term_rows or [["-", "-", "-", "-"]])),
        ]

        doc.build(story)
        return filepath

    def preview_pdf(self):
        try:
            filepath = self._generate_pdf()
            preview_pdf_file(self, filepath)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Aperçu impossible : {e}")

    def print_current(self):
        try:
            filepath = self._generate_pdf()
            print_pdf_file(self, filepath, "Statistiques envoyées à l'impression.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impression impossible : {e}")
