from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QPushButton, QMessageBox, QSpinBox, QHBoxLayout
)

from database.connection import get_connection


class EditClassSubjectDialog(QDialog):
    def __init__(self, class_subject_id, current_user, parent=None):
        super().__init__(parent)

        self.class_subject_id = int(class_subject_id)
        self.current_user = current_user

        self.setWindowTitle("Modifier coefficient")
        self.setFixedWidth(400)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.class_label = QLabel("-")
        self.subject_label = QLabel("-")

        self.coefficient_input = QSpinBox()
        self.coefficient_input.setMinimum(1)
        self.coefficient_input.setMaximum(20)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.update_data)
        self.cancel_btn.clicked.connect(self.reject)

        self.form_layout.addRow("Classe :", self.class_label)
        self.form_layout.addRow("Matière :", self.subject_label)
        self.form_layout.addRow("Coefficient :", self.coefficient_input)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.apply_local_styles()

        self.load_data()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
                min-width: 130px;
            }
            QSpinBox {
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
            QPushButton:pressed { background-color: #1e40af; }
            """
        )

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
                        cs.coefficient,
                        c.name,
                        s.name
                    FROM class_subjects cs
                    JOIN classes c ON c.id = cs.class_id
                    JOIN subjects s ON s.id = cs.subject_id
                    WHERE cs.id = %s
                    """,
                    (self.class_subject_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        cs.coefficient,
                        c.name,
                        s.name
                    FROM class_subjects cs
                    JOIN classes c ON c.id = cs.class_id
                    JOIN subjects s ON s.id = cs.subject_id
                    WHERE cs.id = %s
                      AND c.establishment_id = %s
                    """,
                    (self.class_subject_id, self.current_user["establishment_id"])
                )

            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Affectation introuvable ou non autorisée.")
                self.reject()
                return

            coefficient, class_name, subject_name = row

            self.class_label.setText(class_name or "-")
            self.subject_label.setText(subject_name or "-")
            self.coefficient_input.setValue(coefficient or 1)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self.reject()
        finally:
            conn.close()

    def update_data(self):
        coefficient = self.coefficient_input.value()

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    UPDATE class_subjects
                    SET coefficient = %s
                    WHERE id = %s
                    """,
                    (coefficient, self.class_subject_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE class_subjects cs
                    SET coefficient = %s
                    FROM classes c
                    WHERE cs.id = %s
                      AND c.id = cs.class_id
                      AND c.establishment_id = %s
                    """,
                    (coefficient, self.class_subject_id, self.current_user["establishment_id"])
                )

            conn.commit()
            QMessageBox.information(self, "Succès", "Coefficient modifié avec succès.")
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Modification impossible : {e}")
        finally:
            conn.close()
