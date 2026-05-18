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
from ui.class_subjects.add_class_subject_dialog import AddClassSubjectDialog
from ui.class_subjects.edit_class_subject_dialog import EditClassSubjectDialog
from ui.class_subjects.class_subject_details_dialog import ClassSubjectDetailsDialog
from utils.subject_service import ensure_subject_schema
from utils.table_style import setup_table


class ClassSubjectsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_subject_schema()

        layout = QVBoxLayout()

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher classe, matiere...")
        self.establishment_filter = QComboBox()
        self.class_filter = QComboBox()
        self.type_filter = QComboBox()
        self.type_filter.addItem("Tous", None)
        self.type_filter.addItem("Obligatoires", "OBLIGATOIRE")
        self.type_filter.addItem("Facultatives", "FACULTATIVE")

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Etablissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Classe"))
        filters_layout.addWidget(self.class_filter)
        filters_layout.addWidget(QLabel("Type"))
        filters_layout.addWidget(self.type_filter)

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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Etablissement",
            "Matiere",
            "Type",
            "Coefficient",
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("classSubjectDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.d_class = QLabel("-")
        self.d_est = QLabel("-")
        self.d_subject = QLabel("-")
        self.d_type = QLabel("-")
        self.d_coef = QLabel("-")

        details_layout.addRow("Classe :", self.d_class)
        details_layout.addRow("Etablissement :", self.d_est)
        details_layout.addRow("Matiere :", self.d_subject)
        details_layout.addRow("Type :", self.d_type)
        details_layout.addRow("Coefficient :", self.d_coef)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.details_card)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#classSubjectDetailsCard {
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
        self.type_filter.currentIndexChanged.connect(self.load_data)
        self.table.itemSelectionChanged.connect(self.load_selected_details)

        self.load_establishment_filter()
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

    def on_establishment_changed(self):
        self.load_class_filter()
        self.load_data()

    def load_class_filter(self):
        self.class_filter.clear()
        self.class_filter.addItem("Toutes", None)

        conn = get_connection()
        if not conn:
            return

        est_id = self.establishment_filter.currentData()
        try:
            cursor = conn.cursor()
            if self.is_global_admin and est_id is None:
                cursor.execute("SELECT id, name FROM classes ORDER BY name")
            else:
                target_est = est_id if self.is_global_admin else self.current_user["establishment_id"]
                cursor.execute(
                    """
                    SELECT id, name
                    FROM classes
                    WHERE establishment_id = %s
                    ORDER BY name
                    """,
                    (target_est,),
                )
            for class_id, name in cursor.fetchall():
                self.class_filter.addItem(name, class_id)
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
        subject_type = self.type_filter.currentData()

        try:
            cursor = conn.cursor()

            filters = [
                "(c.name ILIKE %s OR s.name ILIKE %s)",
            ]
            params = [search, search]

            if self.is_global_admin:
                if est_id is not None:
                    filters.append("c.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("c.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if class_id is not None:
                filters.append("c.id = %s")
                params.append(class_id)

            if subject_type is not None:
                filters.append("COALESCE(cs.subject_type, 'OBLIGATOIRE') = %s")
                params.append(subject_type)

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    cs.id,
                    c.name AS class_name,
                    e.name AS establishment_name,
                    s.name AS subject_name,
                    COALESCE(cs.subject_type, 'OBLIGATOIRE') AS subject_type,
                    cs.coefficient
                FROM class_subjects cs
                JOIN classes c ON c.id = cs.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN subjects s ON s.id = cs.subject_id
                WHERE {where_sql}
                ORDER BY e.name, c.name, s.name
                """,
                params,
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    if col_index == 4:
                        value = "Facultative" if value == "FACULTATIVE" else "Obligatoire"
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
        self.d_class.setText("-")
        self.d_est.setText("-")
        self.d_subject.setText("-")
        self.d_type.setText("-")
        self.d_coef.setText("-")

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
                    c.name,
                    e.name,
                    s.name,
                    COALESCE(cs.subject_type, 'OBLIGATOIRE'),
                    cs.coefficient
                FROM class_subjects cs
                JOIN classes c ON c.id = cs.class_id
                JOIN establishments e ON e.id = c.establishment_id
                JOIN subjects s ON s.id = cs.subject_id
                WHERE cs.id = %s
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

            class_name, est_name, subject_name, subject_type, coefficient = row
            self.d_class.setText(class_name or "-")
            self.d_est.setText(est_name or "-")
            self.d_subject.setText(subject_name or "-")
            self.d_type.setText("Facultative" if subject_type == "FACULTATIVE" else "Obligatoire")
            self.d_coef.setText(str(coefficient) if coefficient is not None else "-")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddClassSubjectDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Selectionnez une ligne")
            return

        class_subject_id_item = self.table.item(selected, 0)
        if not class_subject_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide")
            return

        dialog = EditClassSubjectDialog(
            class_subject_id=class_subject_id_item.text(),
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec():
            self.load_data()

    def open_details_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Selectionnez une ligne")
            return

        class_subject_id_item = self.table.item(selected, 0)
        if not class_subject_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide")
            return

        dialog = ClassSubjectDetailsDialog(
            class_subject_id=int(class_subject_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()
