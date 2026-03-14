from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QDoubleSpinBox
)

from database.connection import get_connection


class AddClassFeeDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user

        self.setWindowTitle("Ajouter un frais à une classe")
        self.setFixedWidth(450)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.establishment_input = QComboBox()
        self.class_input = QComboBox()
        self.fee_input = QComboBox()
        self.school_year_input = QComboBox()

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(100000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Établissement :", self.establishment_input)
        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Type de frais :", self.fee_input)
        self.form_layout.addRow("Montant :", self.amount_input)
        self.form_layout.addRow("Année scolaire :", self.school_year_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

        self.load_establishments()
        self.load_fees()
        self.load_school_years()

        self.establishment_input.currentIndexChanged.connect(self.load_classes)
        self.load_classes()

    def load_establishments(self):
        self.establishment_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
            else:
                cursor.execute(
                    "SELECT id, name FROM establishments WHERE id = %s",
                    (self.current_user["establishment_id"],)
                )

            rows = cursor.fetchall()

            for est_id, name in rows:
                self.establishment_input.addItem(name, est_id)

            if self.current_user["role"] != "ADMIN_GLOBAL":
                self.establishment_input.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement établissements impossible : {e}")
        finally:
            conn.close()

    def load_classes(self):
        self.class_input.clear()

        establishment_id = self.establishment_input.currentData()
        if establishment_id is None:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM classes
                WHERE establishment_id = %s
                ORDER BY name
                """,
                (establishment_id,)
            )
            rows = cursor.fetchall()

            for class_id, name in rows:
                self.class_input.addItem(name, class_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement classes impossible : {e}")
        finally:
            conn.close()

    def load_fees(self):
        self.fee_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM fees
                ORDER BY name
                """
            )
            rows = cursor.fetchall()

            for fee_id, name in rows:
                self.fee_input.addItem(name, fee_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement frais impossible : {e}")
        finally:
            conn.close()

    def load_school_years(self):
        self.school_year_input.clear()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
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
            rows = cursor.fetchall()

            for school_year_id, name in rows:
                self.school_year_input.addItem(name, school_year_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement années scolaires impossible : {e}")
        finally:
            conn.close()

    def save_data(self):
        class_id = self.class_input.currentData()
        fee_id = self.fee_input.currentData()
        school_year_id = self.school_year_input.currentData()
        amount = float(self.amount_input.value())

        if None in (class_id, fee_id, school_year_id):
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

            cursor.execute(
                """
                SELECT 1
                FROM class_fees
                WHERE class_id = %s
                  AND fee_id = %s
                  AND school_year_id = %s
                """,
                (class_id, fee_id, school_year_id)
            )
            exists = cursor.fetchone()

            if exists:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Ce frais existe déjà pour cette classe et cette année scolaire."
                )
                return

            cursor.execute(
                """
                INSERT INTO class_fees (class_id, fee_id, amount, school_year_id)
                VALUES (%s, %s, %s, %s)
                """,
                (class_id, fee_id, amount, school_year_id)
            )

            conn.commit()
            QMessageBox.information(self, "Succès", "Frais par classe enregistré avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()