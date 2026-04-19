from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
    QLabel,
    QComboBox,
    QFrame,
    QFormLayout,
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.classes.add_class_dialog import AddClassDialog
from ui.classes.class_details_dialog import ClassDetailsDialog
from ui.classes.edit_class_dialog import EditClassDialog
from utils.table_style import setup_table


class ClassesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        self.layout = QVBoxLayout()

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher classe, niveau, cycle...")
        self.establishment_filter = QComboBox()
        self.cycle_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Cycle"))
        filters_layout.addWidget(self.cycle_filter)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_classes)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.details_btn)
        btn_layout.addWidget(self.refresh_btn)

        self.layout.addLayout(filters_layout)
        self.layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Niveau",
            "Cycle",
            "Titulaire",
            "Assistant",
            "Établissement",
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("classDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_name = QLabel("-")
        self.d_level = QLabel("-")
        self.d_cycle = QLabel("-")
        self.d_titular = QLabel("-")
        self.d_assistant = QLabel("-")
        self.d_est = QLabel("-")
        self.d_students = QLabel("-")

        details_layout.addRow("Classe :", self.d_name)
        details_layout.addRow("Niveau :", self.d_level)
        details_layout.addRow("Cycle :", self.d_cycle)
        details_layout.addRow("Titulaire :", self.d_titular)
        details_layout.addRow("Assistant :", self.d_assistant)
        details_layout.addRow("Établissement :", self.d_est)
        details_layout.addRow("Effectif (année en cours) :", self.d_students)

        self.layout.addWidget(self.table)
        self.layout.addWidget(self.details_card)
        self.setLayout(self.layout)

        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#classDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.search_input.textChanged.connect(self.load_classes)
        self.establishment_filter.currentIndexChanged.connect(self.load_classes)
        self.cycle_filter.currentIndexChanged.connect(self.load_classes)
        self.table.itemSelectionChanged.connect(self.load_selected_class_details)

        self.load_establishment_filter()
        self.load_cycle_filter()
        self.load_classes()

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
                cursor.execute("SELECT id, name FROM establishments WHERE id = %s", (self.current_user["establishment_id"],))
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def load_cycle_filter(self):
        self.cycle_filter.clear()
        self.cycle_filter.addItem("Tous", None)

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM cycles ORDER BY name")
            for cycle_id, name in cursor.fetchall():
                self.cycle_filter.addItem(name, cycle_id)
        finally:
            conn.close()

    def load_classes(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        est_id = self.establishment_filter.currentData()
        cycle_id = self.cycle_filter.currentData()

        try:
            cursor = conn.cursor()

            filters = [
                "(c.name ILIKE %s OR COALESCE(c.level, '') ILIKE %s OR COALESCE(cy.name, '') ILIKE %s)",
            ]
            params = [search, search, search]

            if self.is_global_admin:
                if est_id is not None:
                    filters.append("c.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("c.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if cycle_id is not None:
                filters.append("c.cycle_id = %s")
                params.append(cycle_id)

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    c.id,
                    c.name,
                    c.level,
                    COALESCE(cy.name, ''),
                    COALESCE(t1.last_name || ' ' || t1.first_name, ''),
                    COALESCE(t2.last_name || ' ' || t2.first_name, ''),
                    e.name
                FROM classes c
                JOIN establishments e ON e.id = c.establishment_id
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                LEFT JOIN teachers t1 ON t1.id = c.titular_teacher_id
                LEFT JOIN teachers t2 ON t2.id = c.assistant_teacher_id
                WHERE {where_sql}
                ORDER BY e.name, cy.name, c.name
                """,
                params,
            )

            rows = cursor.fetchall()
            self.table.setRowCount(len(rows))

            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    item = QTableWidgetItem("" if value is None else str(value))
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
        self.d_name.setText("-")
        self.d_level.setText("-")
        self.d_cycle.setText("-")
        self.d_titular.setText("-")
        self.d_assistant.setText("-")
        self.d_est.setText("-")
        self.d_students.setText("-")

    def load_selected_class_details(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            self.clear_details()
            return

        class_id_item = self.table.item(selected_row, 0)
        if not class_id_item:
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
                    c.name,
                    c.level,
                    COALESCE(cy.name, ''),
                    COALESCE(t1.last_name || ' ' || t1.first_name, ''),
                    COALESCE(t2.last_name || ' ' || t2.first_name, ''),
                    e.name
                FROM classes c
                JOIN establishments e ON e.id = c.establishment_id
                LEFT JOIN cycles cy ON cy.id = c.cycle_id
                LEFT JOIN teachers t1 ON t1.id = c.titular_teacher_id
                LEFT JOIN teachers t2 ON t2.id = c.assistant_teacher_id
                WHERE c.id = %s
            """
            params = [int(class_id_item.text())]
            if not self.is_global_admin:
                sql += " AND c.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_details()
                return

            class_name, level, cycle_name, titular_name, assistant_name, est_name = row

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM enrollments
                WHERE class_id = %s
                  AND school_year_id = (
                    SELECT id
                    FROM school_years
                    ORDER BY id DESC
                    LIMIT 1
                  )
                """,
                (int(class_id_item.text()),),
            )
            count_row = cursor.fetchone()
            students_count = count_row[0] if count_row else 0

            self.d_name.setText(class_name or "-")
            self.d_level.setText(level or "-")
            self.d_cycle.setText(cycle_name or "-")
            self.d_titular.setText(titular_name or "-")
            self.d_assistant.setText(assistant_name or "-")
            self.d_est.setText(est_name or "-")
            self.d_students.setText(str(students_count))
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddClassDialog(self.current_user, self)
        if dialog.exec():
            self.load_classes()

    def open_edit_dialog(self):
        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Sélection", "Veuillez sélectionner une classe.")
            return

        class_id_item = self.table.item(selected_row, 0)
        class_id = class_id_item.text()

        dialog = EditClassDialog(class_id, self.current_user, self)

        if dialog.exec():
            self.load_classes()

    def open_details_dialog(self):
        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Sélection", "Veuillez sélectionner une classe.")
            return

        class_id_item = self.table.item(selected_row, 0)
        if not class_id_item:
            QMessageBox.warning(self, "Erreur", "Classe invalide.")
            return

        dialog = ClassDetailsDialog(int(class_id_item.text()), self.current_user, self)
        dialog.exec()
