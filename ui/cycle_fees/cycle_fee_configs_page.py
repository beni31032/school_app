from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QMessageBox, QLineEdit, QLabel, QComboBox
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.cycle_fees.add_cycle_fee_config_dialog import AddCycleFeeConfigDialog
from ui.cycle_fees.edit_cycle_fee_config_dialog import EditCycleFeeConfigDialog
from utils.cycle_fee_service import ensure_cycle_fee_schema, generate_class_fees_from_cycle_configs
from utils.table_style import setup_table


class CycleFeeConfigsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"
        ensure_cycle_fee_schema()

        layout = QVBoxLayout()
        filters_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher cycle, frais, portée...")
        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Portée"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Année scolaire"))
        filters_layout.addWidget(self.school_year_filter)

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.generate_btn = QPushButton("Générer frais des classes")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.generate_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Portée", "Cycle", "Type de frais", "Montant", "Année scolaire"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)
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
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.generate_btn.clicked.connect(self.generate_class_fees)
        self.refresh_btn.clicked.connect(self.load_data)
        self.search_input.textChanged.connect(self.load_data)
        self.establishment_filter.currentIndexChanged.connect(self.load_data)
        self.school_year_filter.currentIndexChanged.connect(self.load_data)

        self.load_establishment_filter()
        self.load_school_year_filter()
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
                self.establishment_filter.addItem("Toute l'école", "GLOBAL")
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cursor.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                self.establishment_filter.addItem("Tous", None)
                self.establishment_filter.addItem("Toute l'école", "GLOBAL")
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
                    (self.current_user["establishment_id"],),
                )
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
        finally:
            conn.close()

    def load_school_year_filter(self):
        self.school_year_filter.clear()
        self.school_year_filter.addItem("Toutes", None)
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for school_year_id, name in cursor.fetchall():
                self.school_year_filter.addItem(name, school_year_id)
        finally:
            conn.close()

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cursor = conn.cursor()
            search = f"%{self.search_input.text().strip()}%"
            establishment_scope = self.establishment_filter.currentData()
            school_year_id = self.school_year_filter.currentData()

            filters = [
                "(COALESCE(e.name, 'Toute l''école') ILIKE %s OR COALESCE(cy.name, '') ILIKE %s OR COALESCE(f.name, '') ILIKE %s OR COALESCE(sy.name, '') ILIKE %s)"
            ]
            params = [search, search, search, search]

            if establishment_scope == "GLOBAL":
                filters.append("cfg.establishment_id IS NULL")
            elif establishment_scope is not None:
                if self.is_global_admin:
                    filters.append("cfg.establishment_id = %s")
                    params.append(establishment_scope)
                else:
                    filters.append("cfg.establishment_id = %s")
                    params.append(establishment_scope)

            if school_year_id is not None:
                filters.append("cfg.school_year_id = %s")
                params.append(school_year_id)

            where_sql = " AND ".join(filters)
            cursor.execute(
                f"""
                SELECT
                    cfg.id,
                    COALESCE(e.name, 'Toute l''école'),
                    cy.name,
                    f.name,
                    cfg.amount,
                    sy.name
                FROM cycle_fee_configs cfg
                LEFT JOIN establishments e ON e.id = cfg.establishment_id
                JOIN cycles cy ON cy.id = cfg.cycle_id
                JOIN fees f ON f.id = cfg.fee_id
                JOIN school_years sy ON sy.id = cfg.school_year_id
                WHERE {where_sql}
                ORDER BY sy.name DESC, COALESCE(e.name, 'Toute l''école'), cy.name, f.name
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
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddCycleFeeConfigDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un tarif.")
            return
        config_id_item = self.table.item(selected, 0)
        if not config_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide.")
            return
        dialog = EditCycleFeeConfigDialog(
            config_id=int(config_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec():
            self.load_data()

    def generate_class_fees(self):
        establishment_scope = self.establishment_filter.currentData()
        school_year_id = self.school_year_filter.currentData()

        if school_year_id is None:
            QMessageBox.warning(self, "Validation", "Choisissez une année scolaire précise.")
            return

        try:
            inserted, updated = generate_class_fees_from_cycle_configs(
                establishment_id=None if establishment_scope in (None, "GLOBAL") else establishment_scope,
                school_year_id=school_year_id,
                overwrite_existing=True,
            )
            QMessageBox.information(
                self,
                "Succès",
                f"Génération terminée.\n\nCréés : {inserted}\nMis à jour : {updated}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération impossible : {e}")
