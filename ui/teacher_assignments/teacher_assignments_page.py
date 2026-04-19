from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QLineEdit,
    QLabel,
    QComboBox,
    QFrame,
    QFormLayout,
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.teacher_assignments.add_teacher_assignment_dialog import AddTeacherAssignmentDialog
from ui.teacher_assignments.edit_teacher_assignment_dialog import EditTeacherAssignmentDialog
from ui.teacher_assignments.teacher_assignment_details_dialog import TeacherAssignmentDetailsDialog
from utils.table_style import setup_table


class TeacherAssignmentsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        layout = QVBoxLayout()

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher enseignant, matière, classe...")
        self.establishment_filter = QComboBox()
        self.class_filter = QComboBox()
        self.school_year_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Classe"))
        filters_layout.addWidget(self.class_filter)
        filters_layout.addWidget(QLabel("Année scolaire"))
        filters_layout.addWidget(self.school_year_filter)

        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Enseignant",
            "Matière",
            "Classe",
            "Établissement",
            "Année scolaire",
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("assignmentDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_teacher = QLabel("-")
        self.d_subject = QLabel("-")
        self.d_class = QLabel("-")
        self.d_est = QLabel("-")
        self.d_year = QLabel("-")

        details_layout.addRow("Enseignant :", self.d_teacher)
        details_layout.addRow("Matière :", self.d_subject)
        details_layout.addRow("Classe :", self.d_class)
        details_layout.addRow("Établissement :", self.d_est)
        details_layout.addRow("Année scolaire :", self.d_year)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.details_card)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#assignmentDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_data)
        self.search_input.textChanged.connect(self.load_data)
        self.establishment_filter.currentIndexChanged.connect(self.on_establishment_changed)
        self.class_filter.currentIndexChanged.connect(self.load_data)
        self.school_year_filter.currentIndexChanged.connect(self.load_data)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_establishment_filter()
        self.load_school_year_filter()
        self.load_class_filter()
        self.load_data()

    def on_establishment_changed(self):
        self.load_class_filter()
        self.load_data()

    def load_establishment_filter(self):
        self.establishment_filter.clear()

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cursor.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
                    (self.current_user["establishment_id"],),
                )
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def load_class_filter(self):
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("Toutes", None)

        conn = get_connection()
        if not conn:
            self.class_filter.blockSignals(False)
            return

        try:
            cursor = conn.cursor()
            params = []
            sql = """
                SELECT c.id, c.name
                FROM classes c
            """

            if self.is_global_admin:
                establishment_id = self.establishment_filter.currentData()
                if establishment_id is not None:
                    sql += " WHERE c.establishment_id = %s"
                    params.append(establishment_id)
            else:
                sql += " WHERE c.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            sql += " ORDER BY c.name"
            cursor.execute(sql, params)

            for class_id, name in cursor.fetchall():
                self.class_filter.addItem(name, class_id)
        finally:
            conn.close()
            self.class_filter.blockSignals(False)

    def load_school_year_filter(self):
        self.school_year_filter.clear()
        self.school_year_filter.addItem("Toutes", None)

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM school_years
                ORDER BY id DESC
                """
            )
            for school_year_id, name in cursor.fetchall():
                self.school_year_filter.addItem(name, school_year_id)
        finally:
            conn.close()

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        est_id = self.establishment_filter.currentData()
        class_id = self.class_filter.currentData()
        school_year_id = self.school_year_filter.currentData()

        try:
            cursor = conn.cursor()

            filters = [
                "(t.first_name ILIKE %s OR t.last_name ILIKE %s OR s.name ILIKE %s OR c.name ILIKE %s)",
            ]
            params = [search, search, search, search]

            if self.is_global_admin:
                if est_id is not None:
                    filters.append("c.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("c.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if school_year_id is not None:
                filters.append("ta.school_year_id = %s")
                params.append(school_year_id)

            if class_id is not None:
                filters.append("ta.class_id = %s")
                params.append(class_id)

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    ta.id,
                    t.last_name || ' ' || t.first_name AS teacher_name,
                    s.name AS subject_name,
                    c.name AS class_name,
                    e.name AS establishment_name,
                    sy.name AS school_year_name
                FROM teacher_assignments ta
                JOIN teachers t ON t.id = ta.teacher_id
                JOIN subjects s ON s.id = ta.subject_id
                JOIN classes c ON c.id = ta.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN school_years sy ON sy.id = ta.school_year_id
                WHERE {where_sql}
                ORDER BY sy.name DESC, e.name, c.name, s.name
                """,
                params,
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_index, col_index, item)

            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def clear_details(self):
        self.d_teacher.setText("-")
        self.d_subject.setText("-")
        self.d_class.setText("-")
        self.d_est.setText("-")
        self.d_year.setText("-")

    def load_selected_details(self):
        selected = self.table.currentRow()
        if selected == -1:
            self.clear_details()
            return

        item = self.table.item(selected, 0)
        if not item:
            self.clear_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    t.last_name || ' ' || t.first_name,
                    s.name,
                    c.name,
                    e.name,
                    sy.name
                FROM teacher_assignments ta
                JOIN teachers t ON t.id = ta.teacher_id
                JOIN subjects s ON s.id = ta.subject_id
                JOIN classes c ON c.id = ta.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN school_years sy ON sy.id = ta.school_year_id
                WHERE ta.id = %s
            """
            params = [int(item.text())]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            teacher_name, subject_name, class_name, est_name, year_name = row
            self.d_teacher.setText(teacher_name or "-")
            self.d_subject.setText(subject_name or "-")
            self.d_class.setText(class_name or "-")
            self.d_est.setText(est_name or "-")
            self.d_year.setText(year_name or "-")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddTeacherAssignmentDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        assignment_id_item = self.table.item(selected, 0)
        if not assignment_id_item:
            QMessageBox.warning(self, "Erreur", "Affectation invalide")
            return

        dialog = EditTeacherAssignmentDialog(
            assignment_id=assignment_id_item.text(),
            current_user=self.current_user,
            parent=self
        )
        if dialog.exec():
            self.load_data()

    def open_details_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        assignment_id_item = self.table.item(selected, 0)
        if not assignment_id_item:
            QMessageBox.warning(self, "Erreur", "Affectation invalide")
            return

        dialog = TeacherAssignmentDetailsDialog(
            assignment_id=int(assignment_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()
