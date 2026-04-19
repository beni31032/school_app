from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
    QPushButton,
    QMessageBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDateEdit,
)
from datetime import datetime, timedelta
import re
import unicodedata

from database.connection import get_connection
from utils.security import hash_password
from utils.table_style import setup_table


def readonly_item(value) -> QTableWidgetItem:
    item = QTableWidgetItem("" if value is None else str(value))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class SettingsCard(QFrame):
    def __init__(self, title: str, value: str = "-", hint: str = ""):
        super().__init__()
        self.setObjectName("settingsCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("settingsCardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("settingsCardValue")
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("settingsCardHint")
        self.hint_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)
        layout.addStretch()
        self.setLayout(layout)


class BaseSettingsDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(520)

        self.root = QVBoxLayout()
        self.form = QFormLayout()
        self.form.setVerticalSpacing(10)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        actions = QHBoxLayout()
        actions.addWidget(self.save_btn)
        actions.addWidget(self.cancel_btn)

        self.root.addLayout(self.form)
        self.root.addLayout(actions)
        self.setLayout(self.root)

        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                selection-background-color: #2563eb;
                selection-color: white;
                outline: none;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 8px;
                font-weight: 700;
                padding: 6px 12px;
            }
            QPushButton:first-of-type {
                background-color: #2563eb;
                color: white;
                border: none;
            }
            QPushButton:first-of-type:hover { background-color: #1d4ed8; }
            QPushButton:last-of-type {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
            }
            """
        )

        self.cancel_btn.clicked.connect(self.reject)


class EstablishmentDialog(BaseSettingsDialog):
    def __init__(self, current_user, establishment_id=None, parent=None):
        super().__init__("Établissement", parent=parent)
        self.current_user = current_user
        self.establishment_id = establishment_id

        self.name_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()

        self.form.addRow("Nom :", self.name_input)
        self.form.addRow("Adresse :", self.address_input)
        self.form.addRow("Téléphone :", self.phone_input)

        self.save_btn.clicked.connect(self.save_establishment)

        if self.establishment_id:
            self.load_establishment()

    def load_establishment(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, COALESCE(address, ''), COALESCE(phone, '') FROM establishments WHERE id = %s",
                (self.establishment_id,),
            )
            row = cursor.fetchone()
            if row:
                self.name_input.setText(row[0] or "")
                self.address_input.setText(row[1] or "")
                self.phone_input.setText(row[2] or "")
        finally:
            conn.close()

    def save_establishment(self):
        name = self.name_input.text().strip()
        address = self.address_input.text().strip() or None
        phone = self.phone_input.text().strip() or None

        if not name:
            QMessageBox.warning(self, "Validation", "Le nom est obligatoire")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cursor = conn.cursor()
            if self.establishment_id:
                cursor.execute(
                    """
                    UPDATE establishments
                    SET name = %s, address = %s, phone = %s
                    WHERE id = %s
                    """,
                    (name, address, phone, self.establishment_id),
                )
            else:
                cursor.execute(
                    "SELECT id FROM establishments WHERE LOWER(name) = LOWER(%s)",
                    (name,),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Un établissement avec ce nom existe déjà")
                    conn.rollback()
                    return
                cursor.execute(
                    """
                    INSERT INTO establishments (name, address, phone)
                    VALUES (%s, %s, %s)
                    """,
                    (name, address, phone),
                )
            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()


class SchoolYearDialog(BaseSettingsDialog):
    def __init__(self, current_user, school_year_id=None, parent=None):
        super().__init__("Année scolaire", parent=parent)
        self.current_user = current_user
        self.school_year_id = school_year_id

        self.name_input = QLineEdit()
        self.start_date_input = QDateEdit()
        self.end_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.end_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setDate(QDate.currentDate())
        self.end_date_input.setDate(QDate.currentDate().addMonths(10))

        self.form.addRow("Nom :", self.name_input)
        self.form.addRow("Date début :", self.start_date_input)
        self.form.addRow("Date fin :", self.end_date_input)

        self.save_btn.clicked.connect(self.save_school_year)

        if self.school_year_id:
            self.load_school_year()

    def load_school_year(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, start_date, end_date FROM school_years WHERE id = %s",
                (self.school_year_id,),
            )
            row = cursor.fetchone()
            if row:
                self.name_input.setText(row[0] or "")
                if row[1]:
                    self.start_date_input.setDate(QDate.fromString(str(row[1]), "yyyy-MM-dd"))
                if row[2]:
                    self.end_date_input.setDate(QDate.fromString(str(row[2]), "yyyy-MM-dd"))
        finally:
            conn.close()

    def save_school_year(self):
        name = self.name_input.text().strip()
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")

        if not name:
            QMessageBox.warning(self, "Validation", "Le nom est obligatoire")
            return
        if self.end_date_input.date() < self.start_date_input.date():
            QMessageBox.warning(self, "Validation", "La date de fin doit être après la date de début")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cursor = conn.cursor()
            if self.school_year_id:
                cursor.execute(
                    """
                    UPDATE school_years
                    SET name = %s, start_date = %s, end_date = %s
                    WHERE id = %s
                    """,
                    (name, start_date, end_date, self.school_year_id),
                )
            else:
                cursor.execute(
                    "SELECT id FROM school_years WHERE name = %s",
                    (name,),
                )
                if cursor.fetchone():
                    QMessageBox.warning(self, "Validation", "Cette année scolaire existe déjà")
                    conn.rollback()
                    return
                cursor.execute(
                    """
                    INSERT INTO school_years (name, start_date, end_date)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, start_date, end_date),
                )
                new_school_year_id = cursor.fetchone()[0]
                self.create_default_terms(cursor, new_school_year_id, start_date, end_date)
            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()

    def create_default_terms(self, cursor, school_year_id: int, start_date: str, end_date: str):
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        total_days = max((end - start).days, 2)

        term1_end = start + timedelta(days=total_days // 3)
        term2_end = start + timedelta(days=(2 * total_days) // 3)
        term2_start = term1_end + timedelta(days=1)
        term3_start = term2_end + timedelta(days=1)

        terms = [
            ("Trimestre 1", start, term1_end),
            ("Trimestre 2", term2_start, term2_end),
            ("Trimestre 3", term3_start, end),
        ]
        for name, t_start, t_end in terms:
            cursor.execute(
                """
                INSERT INTO terms (name, school_year_id, start_date, end_date)
                VALUES (%s, %s, %s, %s)
                """,
                (name, school_year_id, t_start.isoformat(), t_end.isoformat()),
            )


class UserDialog(BaseSettingsDialog):
    ROLE_OPTIONS = ["ADMIN_GLOBAL", "SECRETAIRE", "COMPTABLE", "SURVEILLANT", "DIRECTEUR"]

    def __init__(self, current_user, user_id=None, parent=None):
        super().__init__("Utilisateur", parent=parent)
        self.current_user = current_user
        self.user_id = user_id

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_input = QComboBox()
        self.establishment_input = QComboBox()

        for role in self.ROLE_OPTIONS:
            self.role_input.addItem(role, role)

        self.form.addRow("Nom d'utilisateur :", self.username_input)
        self.form.addRow("Mot de passe :", self.password_input)
        self.form.addRow("Rôle :", self.role_input)
        self.form.addRow("Établissement :", self.establishment_input)

        self.load_establishments()
        self.role_input.currentIndexChanged.connect(self.sync_role_constraints)
        self.save_btn.clicked.connect(self.save_user)

        if self.user_id:
            self.password_input.setPlaceholderText("Laisser vide pour ne pas changer")
            self.load_user()

        self.sync_role_constraints()

    def load_establishments(self):
        self.establishment_input.clear()
        self.establishment_input.addItem("Aucun / Global", None)

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM establishments ORDER BY name")
            for est_id, name in cursor.fetchall():
                self.establishment_input.addItem(name, est_id)
        finally:
            conn.close()

    def load_user(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, role, establishment_id FROM users WHERE id = %s",
                (self.user_id,),
            )
            row = cursor.fetchone()
            if row:
                username, role, establishment_id = row
                self.username_input.setText(username or "")
                self.select_combo_data(self.role_input, role)
                self.select_combo_data(self.establishment_input, establishment_id)
        finally:
            conn.close()

    def select_combo_data(self, combo, data):
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    def sync_role_constraints(self):
        is_global = self.role_input.currentData() == "ADMIN_GLOBAL"
        if is_global:
            self.establishment_input.setCurrentIndex(0)
        self.establishment_input.setEnabled(not is_global)

    def save_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        role = self.role_input.currentData()
        establishment_id = self.establishment_input.currentData()

        if not username:
            QMessageBox.warning(self, "Validation", "Le nom d'utilisateur est obligatoire")
            return
        if not self.user_id and not password:
            QMessageBox.warning(self, "Validation", "Le mot de passe est obligatoire")
            return
        if role != "ADMIN_GLOBAL" and establishment_id is None:
            QMessageBox.warning(self, "Validation", "Un établissement est requis pour ce rôle")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            if self.user_id:
                cursor.execute(
                    "SELECT id FROM users WHERE LOWER(username) = LOWER(%s) AND id <> %s",
                    (username, self.user_id),
                )
            else:
                cursor.execute(
                    "SELECT id FROM users WHERE LOWER(username) = LOWER(%s)",
                    (username,),
                )
            if cursor.fetchone():
                QMessageBox.warning(self, "Validation", "Ce nom d'utilisateur existe déjà")
                conn.rollback()
                return

            if self.user_id:
                if password:
                    cursor.execute(
                        """
                        UPDATE users
                        SET username = %s, password_hash = %s, role = %s, establishment_id = %s
                        WHERE id = %s
                        """,
                        (username, hash_password(password), role, establishment_id, self.user_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE users
                        SET username = %s, role = %s, establishment_id = %s
                        WHERE id = %s
                        """,
                        (username, role, establishment_id, self.user_id),
                    )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, role, establishment_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (username, hash_password(password), role, establishment_id),
                )

            conn.commit()
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()


class SettingsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("Paramètres")
        title.setObjectName("settingsTitle")
        subtitle = QLabel("Centre de configuration du système scolaire")
        subtitle.setObjectName("settingsSubtitle")

        actions = QHBoxLayout()
        actions.addStretch()
        self.refresh_btn = QPushButton("Actualiser")
        actions.addWidget(self.refresh_btn)

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)

        self.user_card = SettingsCard("Utilisateur connecté", "-", "Compte actuellement utilisé pour la session")
        self.role_card = SettingsCard("Rôle", "-", "Niveau d'accès actif")
        self.establishment_card = SettingsCard("Établissement actif", "-", "Contexte principal de travail")
        self.school_year_card = SettingsCard("Année scolaire active", "-", "Année utilisée par défaut dans les modules")

        self.cards_layout.addWidget(self.user_card, 0, 0)
        self.cards_layout.addWidget(self.role_card, 0, 1)
        self.cards_layout.addWidget(self.establishment_card, 1, 0)
        self.cards_layout.addWidget(self.school_year_card, 1, 1)

        self.tabs = QTabWidget()

        self.establishments_tab = QWidget()
        self.school_years_tab = QWidget()
        self.users_tab = QWidget()
        self.promotion_tab = QWidget()

        self.tabs.addTab(self.establishments_tab, "Établissements")
        self.tabs.addTab(self.school_years_tab, "Années scolaires")
        self.tabs.addTab(self.users_tab, "Utilisateurs")
        self.tabs.addTab(self.promotion_tab, "Passage année suivante")

        self._build_establishments_tab()
        self._build_school_years_tab()
        self._build_users_tab()
        self._build_promotion_tab()

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addLayout(actions)
        root.addLayout(self.cards_layout)
        root.addWidget(self.tabs)
        self.setLayout(root)

        self.setStyleSheet(
            """
            QLabel#settingsTitle {
                font-size: 24px;
                font-weight: 800;
                color: #111827;
            }
            QLabel#settingsSubtitle {
                font-size: 13px;
                color: #6b7280;
                margin-bottom: 8px;
            }
            QFrame#settingsCard {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 12px;
            }
            QLabel#settingsCardTitle {
                color: #64748b;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#settingsCardValue {
                color: #111827;
                font-size: 20px;
                font-weight: 800;
            }
            QLabel#settingsCardHint {
                color: #6b7280;
                font-size: 12px;
            }
            QTabWidget::pane {
                border: 1px solid #d1d5db;
                background: white;
                border-radius: 12px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e2e8f0;
                color: #0f172a;
                padding: 10px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #2563eb;
                color: white;
            }
            QLabel {
                color: #111827;
                font-weight: 600;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            """
        )

        self.refresh_btn.clicked.connect(self.refresh_all)
        self.refresh_all()

    def _build_establishments_tab(self):
        layout = QVBoxLayout()
        actions = QHBoxLayout()
        self.add_establishment_btn = QPushButton("Ajouter")
        self.edit_establishment_btn = QPushButton("Modifier")
        actions.addWidget(self.add_establishment_btn)
        actions.addWidget(self.edit_establishment_btn)
        actions.addStretch()

        self.establishments_table = QTableWidget()
        self.establishments_table.setColumnCount(4)
        self.establishments_table.setHorizontalHeaderLabels(["ID", "Nom", "Adresse", "Téléphone"])
        self.establishments_table.setColumnHidden(0, True)
        setup_table(self.establishments_table, stretch=True)
        self.establishments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(actions)
        layout.addWidget(self.establishments_table)
        self.establishments_tab.setLayout(layout)

        self.add_establishment_btn.clicked.connect(self.open_add_establishment)
        self.edit_establishment_btn.clicked.connect(self.open_edit_establishment)
        self.add_establishment_btn.setEnabled(self.is_global_admin)
        self.edit_establishment_btn.setEnabled(self.is_global_admin)

    def _build_school_years_tab(self):
        layout = QVBoxLayout()
        actions = QHBoxLayout()
        self.add_school_year_btn = QPushButton("Ajouter")
        self.edit_school_year_btn = QPushButton("Modifier")
        actions.addWidget(self.add_school_year_btn)
        actions.addWidget(self.edit_school_year_btn)
        actions.addStretch()

        self.school_years_table = QTableWidget()
        self.school_years_table.setColumnCount(4)
        self.school_years_table.setHorizontalHeaderLabels(["ID", "Nom", "Date début", "Date fin"])
        self.school_years_table.setColumnHidden(0, True)
        setup_table(self.school_years_table, stretch=True)
        self.school_years_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(actions)
        layout.addWidget(self.school_years_table)
        self.school_years_tab.setLayout(layout)

        self.add_school_year_btn.clicked.connect(self.open_add_school_year)
        self.edit_school_year_btn.clicked.connect(self.open_edit_school_year)
        self.add_school_year_btn.setEnabled(self.is_global_admin)
        self.edit_school_year_btn.setEnabled(self.is_global_admin)

    def _build_users_tab(self):
        layout = QVBoxLayout()
        actions = QHBoxLayout()
        self.add_user_btn = QPushButton("Ajouter")
        self.edit_user_btn = QPushButton("Modifier")
        actions.addWidget(self.add_user_btn)
        actions.addWidget(self.edit_user_btn)
        actions.addStretch()

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Utilisateur", "Rôle", "Établissement", "Type accès"])
        self.users_table.setColumnHidden(0, True)
        setup_table(self.users_table, stretch=True)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(actions)
        layout.addWidget(self.users_table)
        self.users_tab.setLayout(layout)

        self.add_user_btn.clicked.connect(self.open_add_user)
        self.edit_user_btn.clicked.connect(self.open_edit_user)
        self.add_user_btn.setEnabled(self.is_global_admin)
        self.edit_user_btn.setEnabled(self.is_global_admin)

    def _build_promotion_tab(self):
        self.promotion_classes_cache = {}
        self.promotion_class_meta = {}

        layout = QVBoxLayout()
        filters = QHBoxLayout()
        actions = QHBoxLayout()

        self.promotion_establishment_filter = QComboBox()
        self.promotion_source_year_filter = QComboBox()
        self.promotion_target_year_filter = QComboBox()
        self.promotion_class_filter = QComboBox()
        self.load_promotion_btn = QPushButton("Charger les élèves")
        self.run_promotion_btn = QPushButton("Générer les inscriptions")
        self.bulk_promote_btn = QPushButton("Tout promouvoir")
        self.bulk_repeat_btn = QPushButton("Tout faire redoubler")
        self.bulk_exit_btn = QPushButton("Tout marquer sortis")
        self.propose_targets_btn = QPushButton("Proposer classes cibles")

        filters.addWidget(QLabel("Établissement"))
        filters.addWidget(self.promotion_establishment_filter)
        filters.addWidget(QLabel("Année source"))
        filters.addWidget(self.promotion_source_year_filter)
        filters.addWidget(QLabel("Classe"))
        filters.addWidget(self.promotion_class_filter)
        filters.addWidget(QLabel("Année cible"))
        filters.addWidget(self.promotion_target_year_filter)

        self.promotion_help = QLabel(
            "Choisis l'année de départ, puis filtre si besoin par classe pour traiter un passage global ou classe par classe."
        )
        self.promotion_help.setWordWrap(True)

        actions.addWidget(self.load_promotion_btn)
        actions.addWidget(self.bulk_promote_btn)
        actions.addWidget(self.bulk_repeat_btn)
        actions.addWidget(self.bulk_exit_btn)
        actions.addWidget(self.propose_targets_btn)
        actions.addWidget(self.run_promotion_btn)
        actions.addStretch()

        self.promotion_table = QTableWidget()
        self.promotion_table.setColumnCount(7)
        self.promotion_table.setHorizontalHeaderLabels(
            ["ID", "Matricule", "Nom", "Prénom", "Classe actuelle", "Décision", "Classe cible"]
        )
        self.promotion_table.setColumnHidden(0, True)
        setup_table(self.promotion_table, stretch=True)
        self.promotion_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(filters)
        layout.addWidget(self.promotion_help)
        layout.addLayout(actions)
        layout.addWidget(self.promotion_table)
        self.promotion_tab.setLayout(layout)

        self.promotion_establishment_filter.currentIndexChanged.connect(self.refresh_promotion_scope)
        self.promotion_source_year_filter.currentIndexChanged.connect(self.refresh_promotion_scope)
        self.promotion_class_filter.currentIndexChanged.connect(self.clear_promotion_table)
        self.load_promotion_btn.clicked.connect(self.load_promotion_students)
        self.bulk_promote_btn.clicked.connect(self.bulk_set_promoted)
        self.bulk_repeat_btn.clicked.connect(self.bulk_set_repeat)
        self.bulk_exit_btn.clicked.connect(self.bulk_set_exit)
        self.propose_targets_btn.clicked.connect(self.propose_targets_for_all)
        self.run_promotion_btn.clicked.connect(self.run_promotion)

    def clear_promotion_table(self):
        self.promotion_table.setRowCount(0)

    def refresh_promotion_scope(self):
        self.load_promotion_class_cache()
        self.clear_promotion_table()

    def load_promotion_filters(self):
        self.promotion_establishment_filter.clear()
        self.promotion_source_year_filter.clear()
        self.promotion_target_year_filter.clear()
        self.promotion_class_filter.clear()

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                self.promotion_establishment_filter.addItem("Tous", None)
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cursor.fetchall():
                    self.promotion_establishment_filter.addItem(name, est_id)
            else:
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
                    (self.current_user["establishment_id"],),
                )
                row = cursor.fetchone()
                if row:
                    self.promotion_establishment_filter.addItem(row[1], row[0])
                self.promotion_establishment_filter.setEnabled(False)

            cursor.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            years = cursor.fetchall()
            for year_id, name in years:
                self.promotion_source_year_filter.addItem(name, year_id)
                self.promotion_target_year_filter.addItem(name, year_id)

            if self.promotion_target_year_filter.count() > 1:
                self.promotion_target_year_filter.setCurrentIndex(0)
                self.promotion_source_year_filter.setCurrentIndex(1)
            self.load_promotion_class_cache()
            self.load_promotion_class_options()
        finally:
            conn.close()

    def load_promotion_class_cache(self):
        self.promotion_classes_cache = {}
        self.promotion_class_meta = {}

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            params = []
            sql = """
                SELECT c.id, c.name, COALESCE(c.level, ''), c.establishment_id, c.cycle_id
                FROM classes c
            """
            est_id = self.promotion_establishment_filter.currentData()
            if self.is_global_admin and est_id is not None:
                sql += " WHERE c.establishment_id = %s"
                params.append(est_id)
            elif not self.is_global_admin:
                sql += " WHERE c.establishment_id = %s"
                params.append(self.current_user["establishment_id"])
            sql += " ORDER BY c.name"
            cursor.execute(sql, params)
            for class_id, class_name, level, establishment_id, cycle_id in cursor.fetchall():
                self.promotion_classes_cache.setdefault(establishment_id, []).append((class_id, class_name))
                self.promotion_class_meta[class_id] = {
                    "name": class_name,
                    "level": level or "",
                    "establishment_id": establishment_id,
                    "cycle_id": cycle_id,
                }
            self.load_promotion_class_options()
        finally:
            conn.close()

    def load_promotion_class_options(self):
        self.promotion_class_filter.blockSignals(True)
        self.promotion_class_filter.clear()
        self.promotion_class_filter.addItem("Toutes", None)

        source_year_id = self.promotion_source_year_filter.currentData()
        if source_year_id is None:
            return

        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            filters = ["e.school_year_id = %s"]
            params = [source_year_id]

            if self.is_global_admin:
                est_id = self.promotion_establishment_filter.currentData()
                if est_id is not None:
                    filters.append("c.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("c.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            where_sql = " AND ".join(filters)
            cursor.execute(
                f"""
                SELECT DISTINCT c.id, c.name
                FROM enrollments e
                JOIN classes c ON c.id = e.class_id
                WHERE {where_sql}
                ORDER BY c.name
                """,
                params,
            )
            for class_id, class_name in cursor.fetchall():
                self.promotion_class_filter.addItem(class_name, class_id)
        finally:
            self.promotion_class_filter.blockSignals(False)
            conn.close()

    def normalize_text(self, value: str) -> str:
        value = (value or "").strip().lower()
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        return value

    def level_rank(self, meta: dict) -> int:
        label = self.normalize_text(meta.get("level") or meta.get("name") or "")
        mapping = {
            "tps": 1,
            "ps": 2,
            "ms": 3,
            "gs": 4,
            "cp1": 10,
            "cp2": 11,
            "ce1": 12,
            "ce2": 13,
            "cm1": 14,
            "cm2": 15,
            "6eme": 20,
            "5eme": 21,
            "4eme": 22,
            "3eme": 23,
            "seconde": 30,
            "2nde": 30,
            "premiere": 31,
            "1ere": 31,
            "terminale": 32,
            "tle": 32,
        }
        for key, rank in mapping.items():
            if key in label:
                return rank
        return 999

    def extract_stream(self, meta: dict) -> str:
        name = (meta.get("name") or "").strip()
        level = (meta.get("level") or "").strip()
        if level and name.lower().startswith(level.lower()):
            stream = name[len(level):].strip()
            return stream or ""
        parts = name.split()
        return parts[-1] if len(parts) > 1 else ""

    def find_next_class_id(self, current_class_id):
        meta = self.promotion_class_meta.get(current_class_id)
        if not meta:
            return None

        current_rank = self.level_rank(meta)
        current_stream = self.extract_stream(meta)
        establishment_id = meta["establishment_id"]
        cycle_id = meta["cycle_id"]

        candidates = []
        for class_id, candidate_meta in self.promotion_class_meta.items():
            if candidate_meta["establishment_id"] != establishment_id:
                continue
            if candidate_meta["cycle_id"] != cycle_id:
                continue
            candidate_rank = self.level_rank(candidate_meta)
            if candidate_rank <= current_rank:
                continue
            same_stream = self.extract_stream(candidate_meta) == current_stream
            candidates.append((candidate_rank, 0 if same_stream else 1, candidate_meta["name"], class_id))

        if not candidates:
            return None
        candidates.sort()
        return candidates[0][3]

    def _make_decision_combo(self, current_class_id=None):
        combo = QComboBox()
        combo.addItem("Promu", "PROMOTED")
        combo.addItem("Redouble", "REPEAT")
        combo.addItem("Sorti", "EXIT")
        combo.setProperty("current_class_id", current_class_id)
        return combo

    def _make_target_class_combo(self, establishment_id, current_class_id=None):
        combo = QComboBox()
        for class_id, class_name in self.promotion_classes_cache.get(establishment_id, []):
            combo.addItem(class_name, class_id)
        if current_class_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == current_class_id:
                    combo.setCurrentIndex(i)
                    break
        return combo

    def load_promotion_students(self):
        self.promotion_table.setRowCount(0)

        source_year_id = self.promotion_source_year_filter.currentData()
        class_filter_id = self.promotion_class_filter.currentData()
        if source_year_id is None:
            QMessageBox.warning(self, "Validation", "Choisis l'année source")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cursor = conn.cursor()
            filters = ["e.school_year_id = %s", "s.is_active = TRUE"]
            params = [source_year_id]

            if self.is_global_admin:
                est_id = self.promotion_establishment_filter.currentData()
                if est_id is not None:
                    filters.append("s.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("s.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if class_filter_id is not None:
                filters.append("e.class_id = %s")
                params.append(class_filter_id)

            where_sql = " AND ".join(filters)
            cursor.execute(
                f"""
                SELECT
                    s.id,
                    s.matricule,
                    s.last_name,
                    s.first_name,
                    c.name,
                    c.id,
                    s.establishment_id
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                JOIN classes c ON c.id = e.class_id
                WHERE {where_sql}
                ORDER BY s.last_name, s.first_name
                """,
                params,
            )
            rows = cursor.fetchall()

            self.promotion_table.setRowCount(len(rows))
            for row_index, (student_id, matricule, last_name, first_name, class_name, class_id, establishment_id) in enumerate(rows):
                self.promotion_table.setItem(row_index, 0, readonly_item(student_id))
                self.promotion_table.setItem(row_index, 1, readonly_item(matricule))
                self.promotion_table.setItem(row_index, 2, readonly_item(last_name))
                self.promotion_table.setItem(row_index, 3, readonly_item(first_name))
                self.promotion_table.setItem(row_index, 4, readonly_item(class_name))

                decision_combo = self._make_decision_combo(current_class_id=class_id)
                target_combo = self._make_target_class_combo(establishment_id, current_class_id=class_id)
                decision_combo.currentIndexChanged.connect(
                    lambda _=None, d=decision_combo, t=target_combo: self.sync_promotion_row(d, t)
                )
                self.sync_promotion_row(decision_combo, target_combo)

                self.promotion_table.setCellWidget(row_index, 5, decision_combo)
                self.promotion_table.setCellWidget(row_index, 6, target_combo)

            if rows:
                self.promotion_table.selectRow(0)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def sync_promotion_row(self, decision_combo, target_combo):
        decision = decision_combo.currentData()
        current_class_id = decision_combo.property("current_class_id")
        if decision == "REPEAT":
            for i in range(target_combo.count()):
                if target_combo.itemData(i) == current_class_id:
                    target_combo.setCurrentIndex(i)
                    break
            target_combo.setEnabled(True)
        elif decision == "EXIT":
            target_combo.setEnabled(False)
        else:
            next_class_id = self.find_next_class_id(current_class_id)
            if next_class_id is None:
                decision_combo.setCurrentIndex(2)
                target_combo.setEnabled(False)
                return
            for i in range(target_combo.count()):
                if target_combo.itemData(i) == next_class_id:
                    target_combo.setCurrentIndex(i)
                    break
            target_combo.setEnabled(True)

    def bulk_set_promoted(self):
        for row in range(self.promotion_table.rowCount()):
            decision_combo = self.promotion_table.cellWidget(row, 5)
            if decision_combo:
                next_class_id = self.find_next_class_id(decision_combo.property("current_class_id"))
                decision_combo.setCurrentIndex(0 if next_class_id is not None else 2)

    def bulk_set_repeat(self):
        for row in range(self.promotion_table.rowCount()):
            decision_combo = self.promotion_table.cellWidget(row, 5)
            if decision_combo:
                decision_combo.setCurrentIndex(1)

    def bulk_set_exit(self):
        for row in range(self.promotion_table.rowCount()):
            decision_combo = self.promotion_table.cellWidget(row, 5)
            if decision_combo:
                decision_combo.setCurrentIndex(2)

    def propose_targets_for_all(self):
        for row in range(self.promotion_table.rowCount()):
            decision_combo = self.promotion_table.cellWidget(row, 5)
            target_combo = self.promotion_table.cellWidget(row, 6)
            if decision_combo and target_combo:
                self.sync_promotion_row(decision_combo, target_combo)

    def run_promotion(self):
        source_year_id = self.promotion_source_year_filter.currentData()
        target_year_id = self.promotion_target_year_filter.currentData()

        if source_year_id is None or target_year_id is None:
            QMessageBox.warning(self, "Validation", "Choisis les années source et cible")
            return
        if source_year_id == target_year_id:
            QMessageBox.warning(self, "Validation", "L'année cible doit être différente de l'année source")
            return
        if self.promotion_table.rowCount() == 0:
            QMessageBox.warning(self, "Validation", "Charge d'abord les élèves")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        created = 0
        skipped = 0
        exits = 0

        try:
            cursor = conn.cursor()
            for row in range(self.promotion_table.rowCount()):
                student_id_item = self.promotion_table.item(row, 0)
                if not student_id_item:
                    continue

                student_id = int(student_id_item.text())
                decision_combo = self.promotion_table.cellWidget(row, 5)
                target_combo = self.promotion_table.cellWidget(row, 6)
                decision = decision_combo.currentData() if decision_combo else None
                target_class_id = target_combo.currentData() if target_combo and target_combo.isEnabled() else None

                if decision == "EXIT":
                    exits += 1
                    continue

                if target_class_id is None:
                    conn.rollback()
                    QMessageBox.warning(self, "Validation", f"Classe cible manquante à la ligne {row + 1}")
                    return

                cursor.execute(
                    """
                    SELECT id
                    FROM enrollments
                    WHERE student_id = %s AND school_year_id = %s
                    """,
                    (student_id, target_year_id),
                )
                existing = cursor.fetchone()
                if existing:
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO enrollments (student_id, class_id, school_year_id)
                    VALUES (%s, %s, %s)
                    """,
                    (student_id, target_class_id, target_year_id),
                )
                created += 1

            conn.commit()
            QMessageBox.information(
                self,
                "Succès",
                f"Passage terminé.\n\nInscriptions créées : {created}\nDéjà existantes ignorées : {skipped}\nSortis : {exits}"
            )
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Passage impossible : {e}")
        finally:
            conn.close()

    def refresh_all(self):
        self.load_summary()
        self.load_establishments()
        self.load_school_years()
        self.load_users()
        self.load_promotion_filters()

    def load_summary(self):
        self.user_card.value_label.setText(self.current_user.get("username", "-"))
        self.role_card.value_label.setText(self.current_user.get("role", "-"))

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            establishment_name = "Tous les établissements" if self.is_global_admin else "-"
            if self.current_user.get("establishment_id"):
                cursor.execute("SELECT name FROM establishments WHERE id = %s", (self.current_user["establishment_id"],))
                row = cursor.fetchone()
                if row:
                    establishment_name = row[0]

            cursor.execute("SELECT name FROM school_years ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            school_year_name = row[0] if row else "-"

            self.establishment_card.value_label.setText(establishment_name)
            self.school_year_card.value_label.setText(school_year_name)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement paramètres impossible : {e}")
        finally:
            conn.close()

    def load_establishments(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                cursor.execute("SELECT id, name, COALESCE(address, ''), COALESCE(phone, '') FROM establishments ORDER BY name")
            else:
                cursor.execute(
                    "SELECT id, name, COALESCE(address, ''), COALESCE(phone, '') FROM establishments WHERE id = %s ORDER BY name",
                    (self.current_user["establishment_id"],),
                )
            rows = cursor.fetchall()
            self.establishments_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.establishments_table.setItem(i, j, readonly_item(value))
            if rows:
                self.establishments_table.selectRow(0)
        finally:
            conn.close()

    def load_school_years(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, start_date, end_date FROM school_years ORDER BY id DESC")
            rows = cursor.fetchall()
            self.school_years_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.school_years_table.setItem(i, j, readonly_item(value))
            if rows:
                self.school_years_table.selectRow(0)
        finally:
            conn.close()

    def load_users(self):
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                cursor.execute(
                    """
                    SELECT u.id, u.username, u.role, COALESCE(e.name, '-')
                    FROM users u
                    LEFT JOIN establishments e ON e.id = u.establishment_id
                    ORDER BY u.username
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT u.id, u.username, u.role, COALESCE(e.name, '-')
                    FROM users u
                    LEFT JOIN establishments e ON e.id = u.establishment_id
                    WHERE u.establishment_id = %s OR u.id = %s
                    ORDER BY u.username
                    """,
                    (self.current_user["establishment_id"], self.current_user["id"]),
                )
            rows = cursor.fetchall()
            self.users_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                user_id, username, role, establishment_name = row
                access_type = "Global" if role == "ADMIN_GLOBAL" else "Établissement"
                values = [user_id, username, role, establishment_name, access_type]
                for j, value in enumerate(values):
                    self.users_table.setItem(i, j, readonly_item(value))
            if rows:
                self.users_table.selectRow(0)
        finally:
            conn.close()

    def _selected_id(self, table):
        row = table.currentRow()
        if row == -1:
            return None
        item = table.item(row, 0)
        if not item:
            return None
        return int(item.text())

    def open_add_establishment(self):
        dialog = EstablishmentDialog(self.current_user, parent=self)
        if dialog.exec():
            self.refresh_all()

    def open_edit_establishment(self):
        establishment_id = self._selected_id(self.establishments_table)
        if not establishment_id:
            QMessageBox.warning(self, "Validation", "Sélectionnez un établissement")
            return
        dialog = EstablishmentDialog(self.current_user, establishment_id=establishment_id, parent=self)
        if dialog.exec():
            self.refresh_all()

    def open_add_school_year(self):
        dialog = SchoolYearDialog(self.current_user, parent=self)
        if dialog.exec():
            self.refresh_all()

    def open_edit_school_year(self):
        school_year_id = self._selected_id(self.school_years_table)
        if not school_year_id:
            QMessageBox.warning(self, "Validation", "Sélectionnez une année scolaire")
            return
        dialog = SchoolYearDialog(self.current_user, school_year_id=school_year_id, parent=self)
        if dialog.exec():
            self.refresh_all()

    def open_add_user(self):
        dialog = UserDialog(self.current_user, parent=self)
        if dialog.exec():
            self.refresh_all()

    def open_edit_user(self):
        user_id = self._selected_id(self.users_table)
        if not user_id:
            QMessageBox.warning(self, "Validation", "Sélectionnez un utilisateur")
            return
        dialog = UserDialog(self.current_user, user_id=user_id, parent=self)
        if dialog.exec():
            self.refresh_all()
