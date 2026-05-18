from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QMessageBox, QPushButton, QVBoxLayout
)

from database.connection import get_connection
from utils.cycle_fee_service import ensure_cycle_fee_schema


class EditCycleFeeConfigDialog(QDialog):
    def __init__(self, config_id: int, current_user, parent=None):
        super().__init__(parent)
        self.config_id = config_id
        self.current_user = current_user
        ensure_cycle_fee_schema()

        self.setWindowTitle("Modifier un tarif par cycle")
        self.setFixedWidth(460)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.establishment_input = QComboBox()
        self.cycle_input = QComboBox()
        self.fee_input = QComboBox()
        self.school_year_input = QComboBox()

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(100000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.form_layout.addRow("Portée :", self.establishment_input)
        self.form_layout.addRow("Cycle :", self.cycle_input)
        self.form_layout.addRow("Type de frais :", self.fee_input)
        self.form_layout.addRow("Montant :", self.amount_input)
        self.form_layout.addRow("Année scolaire :", self.school_year_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.apply_local_styles()

        self.save_btn.clicked.connect(self.save_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.load_establishments()
        self.load_cycles()
        self.load_fees()
        self.load_school_years()
        self.load_existing()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 135px;
            }
            QComboBox, QDoubleSpinBox {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            """
        )

    def load_establishments(self):
        self.establishment_input.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            if self.current_user["role"] == "ADMIN_GLOBAL":
                self.establishment_input.addItem("Toute l'école", None)
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
            else:
                self.establishment_input.addItem("Toute l'école", None)
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
                    (self.current_user["establishment_id"],),
                )
            for est_id, name in cursor.fetchall():
                self.establishment_input.addItem(f"{name} (exception)", est_id)
        finally:
            conn.close()

    def load_cycles(self):
        self.cycle_input.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM cycles ORDER BY name")
            for cycle_id, name in cursor.fetchall():
                self.cycle_input.addItem(name, cycle_id)
        finally:
            conn.close()

    def load_fees(self):
        self.fee_input.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM fees ORDER BY name")
            for fee_id, name in cursor.fetchall():
                self.fee_input.addItem(name, fee_id)
        finally:
            conn.close()

    def load_school_years(self):
        self.school_year_input.clear()
        conn = get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM school_years ORDER BY id DESC")
            for school_year_id, name in cursor.fetchall():
                self.school_year_input.addItem(name, school_year_id)
        finally:
            conn.close()

    def load_existing(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT establishment_id, cycle_id, fee_id, school_year_id, amount
                FROM cycle_fee_configs
                WHERE id = %s
                """,
                (self.config_id,),
            )
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Configuration introuvable.")
                self.reject()
                return
            establishment_id, cycle_id, fee_id, school_year_id, amount = row
            self.establishment_input.setCurrentIndex(self.establishment_input.findData(establishment_id))
            self.cycle_input.setCurrentIndex(self.cycle_input.findData(cycle_id))
            self.fee_input.setCurrentIndex(self.fee_input.findData(fee_id))
            self.school_year_input.setCurrentIndex(self.school_year_input.findData(school_year_id))
            self.amount_input.setValue(float(amount or 0))
        finally:
            conn.close()

    def save_data(self):
        establishment_id = self.establishment_input.currentData()
        cycle_id = self.cycle_input.currentData()
        fee_id = self.fee_input.currentData()
        school_year_id = self.school_year_input.currentData()
        amount = float(self.amount_input.value())

        if None in (establishment_id, cycle_id, fee_id, school_year_id):
            QMessageBox.warning(self, "Validation", "Tous les champs sont obligatoires.")
            return
        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Le montant doit être supérieur à 0.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            if establishment_id is None:
                cursor.execute(
                    """
                    SELECT id
                    FROM cycle_fee_configs
                    WHERE establishment_id IS NULL
                      AND cycle_id = %s
                      AND fee_id = %s
                      AND school_year_id = %s
                      AND id <> %s
                    LIMIT 1
                    """,
                    (cycle_id, fee_id, school_year_id, self.config_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT id
                    FROM cycle_fee_configs
                    WHERE establishment_id = %s
                      AND cycle_id = %s
                      AND fee_id = %s
                      AND school_year_id = %s
                      AND id <> %s
                    LIMIT 1
                    """,
                    (establishment_id, cycle_id, fee_id, school_year_id, self.config_id),
                )
            if cursor.fetchone():
                QMessageBox.warning(self, "Validation", "Une configuration équivalente existe déjà.")
                return
            cursor.execute(
                """
                UPDATE cycle_fee_configs
                SET establishment_id = %s,
                    cycle_id = %s,
                    fee_id = %s,
                    school_year_id = %s,
                    amount = %s
                WHERE id = %s
                """,
                (establishment_id, cycle_id, fee_id, school_year_id, amount, self.config_id),
            )
            conn.commit()
            QMessageBox.information(self, "Succès", "Tarif par cycle modifié.")
            self.accept()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()
