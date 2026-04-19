import csv
import os
import subprocess
import sys
from datetime import datetime

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
    QLineEdit,
    QFrame,
    QFormLayout,
)
from PyQt6.QtCore import Qt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.connection import get_connection
from utils.expense_service import ensure_expenses_table
from utils.salary_service import ensure_salary_table
from utils.teacher_service import ensure_teacher_schema
from utils.table_style import setup_table


LIST_TYPES = [
    ("Élèves par classe", "STUDENTS_BY_CLASS"),
    ("Tous les élèves", "ALL_STUDENTS"),
    ("Enseignants", "TEACHERS"),
    ("Employés", "STAFF"),
    ("Classes", "CLASSES"),
]


class ListsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_teacher_schema()
        ensure_salary_table()
        ensure_expenses_table()

        self.current_headers = []
        self.current_rows = []

        layout = QVBoxLayout()

        filters = QHBoxLayout()
        self.type_filter = QComboBox()
        for label, key in LIST_TYPES:
            self.type_filter.addItem(label, key)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Recherche rapide...")
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()
        self.class_filter = QComboBox()

        filters.addWidget(QLabel("Type"))
        filters.addWidget(self.type_filter)
        filters.addWidget(QLabel("Recherche"))
        filters.addWidget(self.search_input)
        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.establishment_filter)
        filters.addWidget(QLabel("Année"))
        filters.addWidget(self.school_year_filter)
        filters.addWidget(QLabel("Classe"))
        filters.addWidget(self.class_filter)

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
        self.school_year_filter.currentIndexChanged.connect(self.load_data)
        self.class_filter.currentIndexChanged.connect(self.load_data)
        self.search_input.textChanged.connect(self.load_data)
        self.refresh_btn.clicked.connect(self.load_data)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.preview_pdf_btn.clicked.connect(self.preview_pdf)
        self.print_btn.clicked.connect(self.print_current)

        self.load_establishments()
        self.load_school_years()
        self.load_classes()
        self.load_data()

    def apply_combo_style(self):
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QLineEdit {
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
        self.class_filter.setEnabled(key == "STUDENTS_BY_CLASS")
        self.load_data()

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
                cur.execute("SELECT id, name FROM establishments WHERE id=%s", (est_id,))
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
            for sy_id, label in cur.fetchall():
                self.school_year_filter.addItem(label, sy_id)
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
            if est_id is None and self.is_global_admin:
                cur.execute("SELECT id, name FROM classes ORDER BY name")
            else:
                cur.execute("SELECT id, name FROM classes WHERE establishment_id=%s ORDER BY name", (est_id,))
            for class_id, name in cur.fetchall():
                self.class_filter.addItem(name, class_id)
        finally:
            conn.close()

    def load_data(self):
        key = self.type_filter.currentData()
        est_id = self.establishment_filter.currentData()
        sy_id = self.school_year_filter.currentData()
        class_id = self.class_filter.currentData()
        search = f"%{self.search_input.text().strip()}%"

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cur = conn.cursor()

            if key == "STUDENTS_BY_CLASS":
                where = [
                    "e.school_year_id=%s",
                    "s.is_active=TRUE",
                    "(s.matricule ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s OR c.name ILIKE %s)",
                ]
                params = [sy_id, search, search, search, search]
                if class_id is not None:
                    where.append("e.class_id=%s")
                    params.append(class_id)
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("s.establishment_id=%s")
                        params.append(est_id)
                else:
                    where.append("s.establishment_id=%s")
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

            elif key == "ALL_STUDENTS":
                where = ["s.is_active=TRUE", "(s.matricule ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s)"]
                params = [search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("s.establishment_id=%s")
                        params.append(est_id)
                else:
                    where.append("s.establishment_id=%s")
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

            elif key == "TEACHERS":
                where = [
                    "COALESCE(t.is_active, TRUE)=TRUE",
                    "(t.last_name ILIKE %s OR t.first_name ILIKE %s OR COALESCE(t.phone,'') ILIKE %s OR COALESCE(t.email,'') ILIKE %s)",
                ]
                params = [search, search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("t.establishment_id=%s")
                        params.append(est_id)
                else:
                    where.append("t.establishment_id=%s")
                    params.append(self.current_user["establishment_id"])

                cur.execute(
                    f"""
                    SELECT t.last_name, t.first_name, COALESCE(t.phone,''), COALESCE(t.email,'')
                    FROM teachers t
                    WHERE {' AND '.join(where)}
                    ORDER BY t.last_name, t.first_name
                    """,
                    params,
                )
                headers = ["Nom", "Prénom", "Téléphone", "Email"]

            elif key == "STAFF":
                where = [
                    "COALESCE(sm.is_active, TRUE)=TRUE",
                    "(sm.last_name ILIKE %s OR sm.first_name ILIKE %s OR COALESCE(sm.role_title,'') ILIKE %s OR COALESCE(sm.phone,'') ILIKE %s OR COALESCE(sm.email,'') ILIKE %s)",
                ]
                params = [search, search, search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("sm.establishment_id=%s")
                        params.append(est_id)
                else:
                    where.append("sm.establishment_id=%s")
                    params.append(self.current_user["establishment_id"])

                cur.execute(
                    f"""
                    SELECT sm.last_name, sm.first_name, sm.role_title, COALESCE(sm.phone,''), COALESCE(sm.email,'')
                    FROM staff_members sm
                    WHERE {' AND '.join(where)}
                    ORDER BY sm.last_name, sm.first_name
                    """,
                    params,
                )
                headers = ["Nom", "Prénom", "Poste", "Téléphone", "Email"]

            else:  # CLASSES
                where = ["(c.name ILIKE %s OR COALESCE(c.level,'') ILIKE %s OR COALESCE(cy.name,'') ILIKE %s OR e.name ILIKE %s)"]
                params = [search, search, search, search]
                if self.is_global_admin:
                    if est_id is not None:
                        where.append("c.establishment_id=%s")
                        params.append(est_id)
                else:
                    where.append("c.establishment_id=%s")
                    params.append(self.current_user["establishment_id"])
                where_sql = " WHERE " + " AND ".join(where) if where else ""
                cur.execute(
                    f"""
                    SELECT c.name, c.level, COALESCE(cy.name,''), e.name
                    FROM classes c
                    LEFT JOIN cycles cy ON cy.id = c.cycle_id
                    JOIN establishments e ON e.id = c.establishment_id
                    {where_sql}
                    ORDER BY e.name, c.name
                    """,
                    params,
                )
                headers = ["Classe", "Niveau", "Cycle", "Établissement"]

            rows = cur.fetchall()
            self.current_headers = headers
            self.current_rows = [["" if v is None else str(v) for v in row] for row in rows]
            self._fill_table()
            self._update_summary()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def _fill_table(self):
        self.table.clear()
        self.table.setColumnCount(len(self.current_headers))
        self.table.setHorizontalHeaderLabels(self.current_headers)
        self.table.setRowCount(len(self.current_rows))
        for r, row in enumerate(self.current_rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)

    def _update_summary(self):
        self.summary_type.setText(self.type_filter.currentText())
        scope_parts = [
            f"Établissement : {self.establishment_filter.currentText()}",
            f"Année : {self.school_year_filter.currentText()}",
        ]
        if self.class_filter.isEnabled():
            scope_parts.append(f"Classe : {self.class_filter.currentText()}")
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
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(self.current_headers)
                writer.writerows(self.current_rows)
            QMessageBox.information(self, "Succès", f"CSV exporté : {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Export CSV impossible : {e}")

    def _generate_pdf(self):
        if not self.current_rows:
            raise ValueError("Aucune donnée à imprimer")

        os.makedirs("prints/lists", exist_ok=True)
        filename = f"prints/lists/{self.type_filter.currentData()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(filename, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        styles = getSampleStyleSheet()
        title = self.type_filter.currentText()
        subtitle = (
            f"Établissement: {self.establishment_filter.currentText()} | "
            f"Année scolaire: {self.school_year_filter.currentText()} | "
            f"Classe: {self.class_filter.currentText()}"
        )

        table_data = [self.current_headers] + self.current_rows
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story = [
            Paragraph(f"<b>Liste - {title}</b>", styles["Title"]),
            Spacer(1, 8),
            Paragraph(subtitle, styles["Normal"]),
            Spacer(1, 14),
            table,
        ]
        doc.build(story)
        return filename

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
