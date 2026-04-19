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

from database.connection import get_connection
from ui.subjects.add_subject_dialog import AddSubjectDialog
from ui.subjects.edit_subject_dialog import EditSubjectDialog
from ui.subjects.subject_details_dialog import SubjectDetailsDialog
from utils.subject_service import ensure_subject_schema
from utils.table_style import setup_table


class SubjectsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_subject_schema()

        layout = QVBoxLayout()

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher une matiere...")
        self.establishment_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Etablissement"))
        filters_layout.addWidget(self.establishment_filter)

        buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.details_btn = QPushButton("Voir fiche complete")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Matiere", "Etablissement"])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("subjectDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_name = QLabel("-")
        self.d_est = QLabel("-")
        self.d_class_count = QLabel("-")
        self.d_teacher_count = QLabel("-")

        details_layout.addRow("Matiere :", self.d_name)
        details_layout.addRow("Etablissement :", self.d_est)
        details_layout.addRow("Classes associees :", self.d_class_count)
        details_layout.addRow("Affectations enseignants :", self.d_teacher_count)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.details_card)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#subjectDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_subjects)
        self.search_input.textChanged.connect(self.load_subjects)
        self.establishment_filter.currentIndexChanged.connect(self.load_subjects)
        self.table.itemSelectionChanged.connect(self.load_selected_subject_details)

        self.load_establishment_filter()
        self.load_subjects()

    def load_establishment_filter(self):
        self.establishment_filter.clear()

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cursor.execute(
                    """
                    SELECT id, name
                    FROM establishments
                    ORDER BY name
                    """
                )
                for est_id, name in cursor.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                cursor.execute(
                    """
                    SELECT id, name
                    FROM establishments
                    WHERE id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)

        finally:
            conn.close()

    def load_subjects(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        establishment_id = self.establishment_filter.currentData()

        try:
            cursor = conn.cursor()

            filters = ["s.name ILIKE %s"]
            params = [search]

            if self.is_global_admin:
                if establishment_id is not None:
                    filters.append("s.establishment_id = %s")
                    params.append(establishment_id)
            else:
                filters.append("s.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    s.id,
                    s.name,
                    COALESCE(e.name, '-')
                FROM subjects s
                LEFT JOIN establishments e ON e.id = s.establishment_id
                WHERE {where_sql}
                ORDER BY s.name
                """,
                params,
            )
            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))

            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    self.table.setItem(row_index, col_index, QTableWidgetItem(text))

            if rows:
                self.table.selectRow(0)
            else:
                self.clear_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def clear_details(self):
        self.d_name.setText("-")
        self.d_est.setText("-")
        self.d_class_count.setText("-")
        self.d_teacher_count.setText("-")

    def load_selected_subject_details(self):
        selected = self.table.currentRow()
        if selected == -1:
            self.clear_details()
            return

        subject_id_item = self.table.item(selected, 0)
        if not subject_id_item:
            self.clear_details()
            return

        subject_id = int(subject_id_item.text())
        conn = get_connection()
        if not conn:
            self.clear_details()
            return

        try:
            cursor = conn.cursor()

            sql = """
                SELECT
                    s.name,
                    COALESCE(e.name, '-')
                FROM subjects s
                LEFT JOIN establishments e ON e.id = s.establishment_id
                WHERE s.id = %s
            """
            params = [subject_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            name, est_name = row

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM class_subjects
                WHERE subject_id = %s
                """,
                (subject_id,),
            )
            class_count_row = cursor.fetchone()
            class_count = class_count_row[0] if class_count_row else 0

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM teacher_assignments
                WHERE subject_id = %s
                """,
                (subject_id,),
            )
            teacher_count_row = cursor.fetchone()
            teacher_count = teacher_count_row[0] if teacher_count_row else 0

            self.d_name.setText(name or "-")
            self.d_est.setText(est_name or "-")
            self.d_class_count.setText(str(class_count))
            self.d_teacher_count.setText(str(teacher_count))

        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddSubjectDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_subjects()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Selectionnez une matiere")
            return

        subject_id_item = self.table.item(selected, 0)
        if not subject_id_item:
            QMessageBox.warning(self, "Erreur", "Matiere invalide")
            return

        subject_id = subject_id_item.text()

        dialog = EditSubjectDialog(subject_id=subject_id, current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_subjects()

    def open_details_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Selectionnez une matiere")
            return

        subject_id_item = self.table.item(selected, 0)
        if not subject_id_item:
            QMessageBox.warning(self, "Erreur", "Matiere invalide")
            return

        dialog = SubjectDetailsDialog(
            subject_id=int(subject_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()
