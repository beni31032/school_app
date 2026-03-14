from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QPushButton, QMessageBox, QDoubleSpinBox
)

from database.connection import get_connection


class EditClassFeeDialog(QDialog):
    def __init__(self, class_fee_id, current_user, parent=None):
        super().__init__(parent)

        self.class_fee_id = int(class_fee_id)
        self.current_user = current_user

        self.setWindowTitle("Modifier un montant de frais")
        self.setFixedWidth(420)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.class_label = QLabel("-")
        self.establishment_label = QLabel("-")
        self.fee_label = QLabel("-")
        self.school_year_label = QLabel("-")

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(100000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Établissement :", self.establishment_label)
        self.form_layout.addRow("Classe :", self.class_label)
        self.form_layout.addRow("Frais :", self.fee_label)
        self.form_layout.addRow("Année scolaire :", self.school_year_label)
        self.form_layout.addRow("Montant :", self.amount_input)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

        self.load_data()

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        c.name,
                        e.name,
                        f.name,
                        sy.name,
                        cf.amount
                    FROM class_fees cf
                    JOIN classes c ON c.id = cf.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN fees f ON f.id = cf.fee_id
                    JOIN school_years sy ON sy.id = cf.school_year_id
                    WHERE cf.id = %s
                    """,
                    (self.class_fee_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        c.name,
                        e.name,
                        f.name,
                        sy.name,
                        cf.amount
                    FROM class_fees cf
                    JOIN classes c ON c.id = cf.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN fees f ON f.id = cf.fee_id
                    JOIN school_years sy ON sy.id = cf.school_year_id
                    WHERE cf.id = %s
                      AND c.establishment_id = %s
                    """,
                    (self.class_fee_id, self.current_user["establishment_id"])
                )

            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Enregistrement introuvable ou non autorisé.")
                self.reject()
                return

            class_name, establishment_name, fee_name, school_year_name, amount = row

            self.class_label.setText(class_name or "-")
            self.establishment_label.setText(establishment_name or "-")
            self.fee_label.setText(fee_name or "-")
            self.school_year_label.setText(school_year_name or "-")
            self.amount_input.setValue(float(amount or 0))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def update_data(self):
        amount = float(self.amount_input.value())

        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Le montant doit être supérieur à 0.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    UPDATE class_fees
                    SET amount = %s
                    WHERE id = %s
                    """,
                    (amount, self.class_fee_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE class_fees cf
                    SET amount = %s
                    FROM classes c
                    WHERE cf.id = %s
                      AND c.id = cf.class_id
                      AND c.establishment_id = %s
                    """,
                    (amount, self.class_fee_id, self.current_user["establishment_id"])
                )

            conn.commit()
            QMessageBox.information(self, "Succès", "Montant modifié avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()