from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QFrame,
    QFormLayout,
)

from database.connection import get_connection
from ui.staff.add_staff_dialog import AddStaffDialog
from ui.staff.staff_details_dialog import StaffDetailsDialog
from ui.staff.edit_staff_dialog import EditStaffDialog
from utils.salary_service import ensure_salary_table
from utils.table_style import setup_table


class StaffPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        ensure_salary_table()

        layout = QVBoxLayout()
        filters_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par nom, poste, téléphone ou email")

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

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.disable_btn = QPushButton("Désactiver")
        self.enable_btn = QPushButton("Réactiver")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.disable_btn)
        buttons_layout.addWidget(self.enable_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Nom", "Prénom", "Poste", "Téléphone", "Email", "Date embauche", "Statut"]
        )
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("staffDetailsCard")
        details_layout = QFormLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setVerticalSpacing(6)

        self.detail_nom = QLabel("-")
        self.detail_prenom = QLabel("-")
        self.detail_poste = QLabel("-")
        self.detail_phone = QLabel("-")
        self.detail_email = QLabel("-")
        self.detail_hire_date = QLabel("-")
        self.detail_est = QLabel("-")
        self.detail_status = QLabel("-")

        details_layout.addRow("Nom :", self.detail_nom)
        details_layout.addRow("Prénom :", self.detail_prenom)
        details_layout.addRow("Poste :", self.detail_poste)
        details_layout.addRow("Téléphone :", self.detail_phone)
        details_layout.addRow("Email :", self.detail_email)
        details_layout.addRow("Date d'embauche :", self.detail_hire_date)
        details_layout.addRow("Établissement :", self.detail_est)
        details_layout.addRow("Statut :", self.detail_status)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.details_card)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#staffDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.disable_btn.clicked.connect(lambda: self.set_active(False))
        self.enable_btn.clicked.connect(lambda: self.set_active(True))
        self.details_btn.clicked.connect(self.open_details_dialog)
        self.refresh_btn.clicked.connect(self.load_staff)
        self.search_input.textChanged.connect(self.load_staff)
        self.status_filter.currentIndexChanged.connect(self.load_staff)
        self.establishment_filter.currentIndexChanged.connect(self.load_staff)
        self.table.itemSelectionChanged.connect(self.load_selected_staff_details)

        self.load_establishment_filter()
        self.load_staff()

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

    def load_staff(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        status_mode = self.status_filter.currentData()
        establishment_id = self.establishment_filter.currentData()

        try:
            cursor = conn.cursor()

            status_sql = ""
            params = [search, search, search, search]
            if status_mode == "ACTIVE":
                status_sql += " AND COALESCE(sm.is_active, TRUE) = TRUE"
            elif status_mode == "INACTIVE":
                status_sql += " AND COALESCE(sm.is_active, TRUE) = FALSE"

            if self.is_global_admin:
                if establishment_id is not None:
                    status_sql += " AND sm.establishment_id = %s"
                    params.append(establishment_id)
                query = f"""
                    SELECT sm.id, sm.last_name, sm.first_name, sm.role_title, sm.phone, sm.email, sm.hire_date,
                           CASE WHEN COALESCE(sm.is_active, TRUE) THEN 'Actif' ELSE 'Inactif' END
                    FROM staff_members sm
                    WHERE (
                        sm.first_name ILIKE %s OR sm.last_name ILIKE %s
                        OR COALESCE(sm.role_title, '') ILIKE %s
                        OR COALESCE(sm.phone, '') ILIKE %s
                    )
                    {status_sql}
                    ORDER BY sm.last_name, sm.first_name
                """
                cursor.execute(query, params)
            else:
                query = f"""
                    SELECT sm.id, sm.last_name, sm.first_name, sm.role_title, sm.phone, sm.email, sm.hire_date,
                           CASE WHEN COALESCE(sm.is_active, TRUE) THEN 'Actif' ELSE 'Inactif' END
                    FROM staff_members sm
                    WHERE sm.establishment_id = %s
                      AND (
                        sm.first_name ILIKE %s OR sm.last_name ILIKE %s
                        OR COALESCE(sm.role_title, '') ILIKE %s
                        OR COALESCE(sm.phone, '') ILIKE %s
                      )
                      {status_sql}
                    ORDER BY sm.last_name, sm.first_name
                """
                cursor.execute(query, [self.current_user["establishment_id"], *params])

            rows = cursor.fetchall()
            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem("" if value is None else str(value)))
            if rows:
                self.table.selectRow(0)
            else:
                self.clear_staff_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def clear_staff_details(self):
        self.detail_nom.setText("-")
        self.detail_prenom.setText("-")
        self.detail_poste.setText("-")
        self.detail_phone.setText("-")
        self.detail_email.setText("-")
        self.detail_hire_date.setText("-")
        self.detail_est.setText("-")
        self.detail_status.setText("-")

    def load_selected_staff_details(self):
        selected = self.table.currentRow()
        if selected == -1:
            self.clear_staff_details()
            return

        item = self.table.item(selected, 0)
        if not item:
            self.clear_staff_details()
            return

        conn = get_connection()
        if not conn:
            self.clear_staff_details()
            return

        try:
            cursor = conn.cursor()
            sql = """
                SELECT sm.last_name, sm.first_name, sm.role_title, sm.phone, sm.email, sm.hire_date,
                       e.name, CASE WHEN COALESCE(sm.is_active, TRUE) THEN 'Actif' ELSE 'Inactif' END
                FROM staff_members sm
                JOIN establishments e ON e.id = sm.establishment_id
                WHERE sm.id = %s
            """
            params = [int(item.text())]
            if not self.is_global_admin:
                sql += " AND sm.establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_staff_details()
                return

            nom, prenom, poste, phone, email, hire_date, est_name, status_label = row
            self.detail_nom.setText(nom or "-")
            self.detail_prenom.setText(prenom or "-")
            self.detail_poste.setText(poste or "-")
            self.detail_phone.setText(phone or "-")
            self.detail_email.setText(email or "-")
            self.detail_hire_date.setText(str(hire_date) if hire_date else "-")
            self.detail_est.setText(est_name or "-")
            self.detail_status.setText(status_label or "-")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddStaffDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_staff()

    def open_edit_dialog(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un employé")
            return
        item = self.table.item(selected, 0)
        if not item:
            return
        dialog = EditStaffDialog(item.text(), current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_staff()

    def open_details_dialog(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un employé")
            return
        item = self.table.item(selected, 0)
        if not item:
            QMessageBox.warning(self, "Erreur", "Employé invalide")
            return
        dialog = StaffDetailsDialog(int(item.text()), current_user=self.current_user, parent=self)
        dialog.exec()

    def set_active(self, active: bool):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un employé")
            return

        staff_id_item = self.table.item(selected, 0)
        if not staff_id_item:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                cursor.execute(
                    "UPDATE staff_members SET is_active = %s WHERE id = %s",
                    (active, int(staff_id_item.text())),
                )
            else:
                cursor.execute(
                    "UPDATE staff_members SET is_active = %s WHERE id = %s AND establishment_id = %s",
                    (active, int(staff_id_item.text()), self.current_user["establishment_id"]),
                )
            conn.commit()
            self.load_staff()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Mise à jour impossible : {e}")
        finally:
            conn.close()
