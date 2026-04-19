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
)

from database.connection import get_connection
from ui.teachers.add_teacher_dialog import AddTeacherDialog
from ui.teachers.edit_teacher_dialog import EditTeacherDialog
from utils.teacher_service import ensure_teacher_schema
from utils.table_style import setup_table


class TeachersPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_teacher_schema()

        layout = QVBoxLayout()

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher: nom, prénom, téléphone, email...")

        self.status_filter = QComboBox()
        self.status_filter.addItem("Actifs", "ACTIVE")
        self.status_filter.addItem("Inactifs", "INACTIVE")
        self.status_filter.addItem("Tous", "ALL")

        self.establishment_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Statut"))
        filters_layout.addWidget(self.status_filter)
        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)

        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.deactivate_btn = QPushButton("Désactiver")
        self.reactivate_btn = QPushButton("Réactiver")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.deactivate_btn)
        buttons_layout.addWidget(self.reactivate_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Nom",
            "Prénom",
            "Téléphone",
            "Email",
            "Date d'embauche",
            "Établissement",
            "Statut",
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.setStyleSheet("QLabel { color: #111827; font-weight: 600; }")

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.deactivate_btn.clicked.connect(lambda: self.set_teacher_active(False))
        self.reactivate_btn.clicked.connect(lambda: self.set_teacher_active(True))
        self.refresh_btn.clicked.connect(self.load_teachers)

        self.search_input.textChanged.connect(self.load_teachers)
        self.status_filter.currentIndexChanged.connect(self.load_teachers)
        self.establishment_filter.currentIndexChanged.connect(self.load_teachers)

        self.load_establishment_filter()
        self.load_teachers()

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
                est_id = self.current_user["establishment_id"]
                cursor.execute("SELECT id, name FROM establishments WHERE id = %s", (est_id,))
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def load_teachers(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        status_mode = self.status_filter.currentData()
        est_id = self.establishment_filter.currentData()

        try:
            cursor = conn.cursor()

            filters = [
                "(t.first_name ILIKE %s OR t.last_name ILIKE %s OR COALESCE(t.phone,'') ILIKE %s OR COALESCE(t.email,'') ILIKE %s)",
            ]
            params = [search, search, search, search]

            if status_mode == "ACTIVE":
                filters.append("COALESCE(t.is_active, TRUE) = TRUE")
            elif status_mode == "INACTIVE":
                filters.append("COALESCE(t.is_active, TRUE) = FALSE")

            if self.is_global_admin:
                if est_id is not None:
                    filters.append("t.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("t.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    t.id,
                    t.last_name,
                    t.first_name,
                    t.phone,
                    t.email,
                    t.hire_date,
                    COALESCE(e.name, '-') AS establishment_name,
                    CASE WHEN COALESCE(t.is_active, TRUE) THEN 'Actif' ELSE 'Inactif' END AS status_label
                FROM teachers t
                LEFT JOIN establishments e ON e.id = t.establishment_id
                WHERE {where_sql}
                ORDER BY t.last_name, t.first_name
                """,
                params,
            )
            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))

            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    self.table.setItem(row_index, col_index, QTableWidgetItem(text))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddTeacherDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_teachers()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un enseignant")
            return

        teacher_id_item = self.table.item(selected, 0)
        if not teacher_id_item:
            QMessageBox.warning(self, "Erreur", "Enseignant invalide")
            return

        dialog = EditTeacherDialog(
            teacher_id=teacher_id_item.text(),
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec():
            self.load_teachers()

    def set_teacher_active(self, active: bool):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un enseignant")
            return

        teacher_id_item = self.table.item(selected, 0)
        if not teacher_id_item:
            QMessageBox.warning(self, "Erreur", "Enseignant invalide")
            return

        action = "réactiver" if active else "désactiver"
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment {action} cet enseignant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                cursor.execute(
                    "UPDATE teachers SET is_active = %s WHERE id = %s",
                    (active, int(teacher_id_item.text())),
                )
            else:
                cursor.execute(
                    "UPDATE teachers SET is_active = %s WHERE id = %s AND establishment_id = %s",
                    (active, int(teacher_id_item.text()), self.current_user["establishment_id"]),
                )
            conn.commit()
            self.load_teachers()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Mise à jour impossible : {e}")
        finally:
            conn.close()
