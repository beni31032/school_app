import os
import subprocess
import sys
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

        max_val = max(self.values) if self.values else 0
        if max_val <= 0:
            return

        n = len(self.values)
        spacing = 8
        bar_width = max(14, int((chart_rect.width() - spacing * (n - 1)) / n))
        x = chart_rect.left()

        for i, value in enumerate(self.values):
            h = int((value / max_val) * (chart_rect.height() - 26))
            bar_top = chart_rect.bottom() - h

            painter.fillRect(x, bar_top, bar_width, h, self.bar_color)

            painter.setPen(QColor("#1f2937"))
            short_label = str(self.labels[i])[:8]
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

            payment_where = ["DATE_TRUNC('month', p.payment_date) = DATE_TRUNC('month', CURRENT_DATE)"]
            payment_params = []
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

            expense_where = ["DATE_TRUNC('month', e.expense_date) = DATE_TRUNC('month', CURRENT_DATE)"]
            expense_params = []
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

            self.payments_month_card.value_label.setText(f"{enc_month:,.0f} FCFA")
            self.expenses_month_card.value_label.setText(f"{dep_month:,.0f} FCFA")
            self.net_month_card.value_label.setText(f"{(enc_month - dep_month):,.0f} FCFA")

            # Levels table (calcul robuste: dû = frais de classe * effectif ; payé = paiements liés aux class_fees de l'année)
            level_where = []
            level_params = [school_year_id, school_year_id, school_year_id]
            if est_id is not None:
                level_where.append("c.establishment_id=%s")
                level_params.append(est_id)
            level_where_sql = f"WHERE {' AND '.join(level_where)}" if level_where else ""

            cur.execute(
                f"""
                WITH class_student_count AS (
                    SELECT e.class_id, COUNT(DISTINCT e.student_id) AS students_count
                    FROM enrollments e
                    JOIN students s ON s.id = e.student_id
                    WHERE e.school_year_id = %s
                      AND s.is_active = TRUE
                    GROUP BY e.class_id
                ),
                class_fee_total AS (
                    SELECT cf.class_id, COALESCE(SUM(cf.amount),0) AS fee_total
                    FROM class_fees cf
                    WHERE cf.school_year_id = %s
                    GROUP BY cf.class_id
                ),
                class_paid_total AS (
                    SELECT cf.class_id, COALESCE(SUM(p.amount),0) AS paid_total
                    FROM payments p
                    JOIN class_fees cf ON cf.id = p.class_fee_id
                    WHERE cf.school_year_id = %s
                    GROUP BY cf.class_id
                )
                SELECT
                    COALESCE(cy.name, 'Non défini') AS level_name,
                    COALESCE(SUM(csc.students_count),0) AS students_count,
                    COALESCE(SUM(COALESCE(cft.fee_total,0) * COALESCE(csc.students_count,0)),0) AS due_amount,
                    COALESCE(SUM(COALESCE(cpt.paid_total,0)),0) AS paid_amount
                FROM classes c
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                LEFT JOIN class_student_count csc ON csc.class_id = c.id
                LEFT JOIN class_fee_total cft ON cft.class_id = c.id
                LEFT JOIN class_paid_total cpt ON cpt.class_id = c.id
                {level_where_sql}
                GROUP BY COALESCE(cy.name, 'Non défini')
                ORDER BY level_name
                """,
                level_params,
            )
            level_rows = cur.fetchall()

            self.levels_table.setRowCount(len(level_rows))
            level_labels = []
            level_rates = []
            total_due = 0.0
            total_paid = 0.0
            for i, (level, count_students, due, paid) in enumerate(level_rows):
                due = float(due or 0)
                paid = float(paid or 0)
                remaining = max(0.0, due - paid)
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

            # Trend table
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
                month_idx = max(1, int(month_no))
                amount_val = float(amount)
                self.trend_table.setItem(i, 0, QTableWidgetItem(month_names[month_idx - 1]))
                self.trend_table.setItem(i, 1, QTableWidgetItem(f"{amount_val:,.0f}"))
                month_amounts[month_idx] = amount_val

            self.trend_chart.set_data(
                month_names,
                [month_amounts[m] for m in range(1, 13)],
            )

            # Graphique réussite par niveau (moyenne >= 10/20)
            success_where = ["e.school_year_id=%s", "s.is_active=TRUE", "t.school_year_id = e.school_year_id"]
            success_params = [school_year_id]
            if est_id is not None:
                success_where.append("s.establishment_id=%s")
                success_params.append(est_id)

            cur.execute(
                f"""
                WITH subject_scores AS (
                    SELECT
                        COALESCE(cy.name, 'Non défini') AS level_name,
                        e.student_id,
                        g.term_id,
                        g.subject_id,
                        AVG(
                            CASE
                                WHEN COALESCE(g.max_score, 0) > 0 THEN (g.value * 20.0 / g.max_score)
                                ELSE g.value
                            END
                        ) AS subject_avg_20
                    FROM enrollments e
                    JOIN students s ON s.id = e.student_id
                    JOIN classes c ON c.id = e.class_id
                    LEFT JOIN cycles cy ON cy.id = c.cycle_id
                    JOIN grades g ON g.student_id = e.student_id
                    JOIN terms t ON t.id = g.term_id
                    WHERE {' AND '.join(success_where)}
                    GROUP BY COALESCE(cy.name, 'Non défini'), e.student_id, g.term_id, g.subject_id
                ),
                student_term_avg AS (
                    SELECT
                        level_name,
                        student_id,
                        term_id,
                        AVG(subject_avg_20) AS avg_20
                    FROM subject_scores
                    GROUP BY level_name, student_id, term_id
                )
                SELECT
                    level_name,
                    SUM(CASE WHEN avg_20 >= 10 THEN 1 ELSE 0 END) AS success_count,
                    COUNT(*) AS evaluated_count
                FROM student_term_avg
                GROUP BY level_name
                ORDER BY level_name
                """,
                success_params,
            )
            success_rows = cur.fetchall()
            success_level_labels = []
            success_level_rates = []
            total_success_count = 0.0
            total_evaluated_count = 0.0
            self.success_by_level_table.setRowCount(len(success_rows))
            for index, (level_name, success_count, evaluated_count) in enumerate(success_rows):
                success_count = float(success_count or 0)
                evaluated_count = float(evaluated_count or 0)
                total_success_count += success_count
                total_evaluated_count += evaluated_count
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

            # Graphique réussite par trimestre
            cur.execute(
                f"""
                WITH subject_scores AS (
                    SELECT
                        t.id AS term_id,
                        t.name AS term_name,
                        e.student_id,
                        g.subject_id,
                        AVG(
                            CASE
                                WHEN COALESCE(g.max_score, 0) > 0 THEN (g.value * 20.0 / g.max_score)
                                ELSE g.value
                            END
                        ) AS subject_avg_20
                    FROM enrollments e
                    JOIN students s ON s.id = e.student_id
                    JOIN grades g ON g.student_id = e.student_id
                    JOIN terms t ON t.id = g.term_id
                    WHERE {' AND '.join(success_where)}
                    GROUP BY t.id, t.name, e.student_id, g.subject_id
                ),
                student_term_avg AS (
                    SELECT
                        term_id,
                        term_name,
                        student_id,
                        AVG(subject_avg_20) AS avg_20
                    FROM subject_scores
                    GROUP BY term_id, term_name, student_id
                )
                SELECT
                    term_id,
                    term_name,
                    SUM(CASE WHEN avg_20 >= 10 THEN 1 ELSE 0 END) AS success_count,
                    COUNT(*) AS evaluated_count
                FROM student_term_avg
                GROUP BY term_id, term_name
                ORDER BY term_id
                """,
                success_params,
            )
            term_success_rows = cur.fetchall()
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
            self._open_file(filepath)
            QMessageBox.information(self, "Succès", f"Aperçu PDF généré : {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Aperçu impossible : {e}")

    def print_current(self):
        self.preview_pdf()

    def _open_file(self, filepath):
        if sys.platform.startswith("win"):
            os.startfile(filepath)
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
