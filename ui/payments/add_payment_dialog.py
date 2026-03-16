import os
import sys
import subprocess
from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton, QMessageBox,
    QLabel, QDoubleSpinBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView
)

from database.connection import get_connection
from utils.receipt_generator import generate_receipt


class AddPaymentDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user
        self.current_school_year_id = None
        self.selected_student_id = None

        self.setWindowTitle("Ajouter un paiement")
        self.setFixedWidth(700)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un élève par nom, prénom ou matricule")

        self.students_table = QTableWidget()
        self.students_table.setColumnCount(3)
        self.students_table.setHorizontalHeaderLabels(["ID", "Élève", "Classe"])
        self.students_table.setColumnHidden(0, True)
        self.students_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.students_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.class_label = QLabel("-")
        self.fee_input = QTableWidget()
        self.fee_input.setColumnCount(4)
        self.fee_input.setHorizontalHeaderLabels(["ClassFeeID", "Frais", "Montant prévu", "FeeID"])
        self.fee_input.setColumnHidden(0, True)
        self.fee_input.setColumnHidden(3, True)
        self.fee_input.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.expected_amount_label = QLabel("0")
        self.total_paid_label = QLabel("0")
        self.remaining_label = QLabel("0")

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(100000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)

        self.save_btn = QPushButton("Enregistrer")
        self.cancel_btn = QPushButton("Annuler")

        self.save_btn.clicked.connect(self.save_payment)
        self.cancel_btn.clicked.connect(self.reject)

        self.layout.addWidget(QLabel("Recherche élève"))
        self.layout.addWidget(self.search_input)
        self.layout.addWidget(self.students_table)

        self.form_layout.addRow("Classe actuelle :", self.class_label)
        self.layout.addLayout(self.form_layout)

        self.layout.addWidget(QLabel("Frais disponibles"))
        self.layout.addWidget(self.fee_input)

        summary_form = QFormLayout()
        summary_form.addRow("Montant prévu :", self.expected_amount_label)
        summary_form.addRow("Déjà payé :", self.total_paid_label)
        summary_form.addRow("Reste à payer :", self.remaining_label)
        summary_form.addRow("Montant à encaisser :", self.amount_input)

        self.layout.addLayout(summary_form)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.cancel_btn)

        self.setLayout(self.layout)

        self.search_input.textChanged.connect(self.load_students)
        self.students_table.itemSelectionChanged.connect(self.on_student_selected)
        self.fee_input.itemSelectionChanged.connect(self.on_fee_changed)

        self.load_current_school_year()
        self.load_students()

    def load_current_school_year(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id
                FROM school_years
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Validation", "Aucune année scolaire trouvée.")
                return

            self.current_school_year_id = row[0]

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement année scolaire impossible : {e}")
        finally:
            conn.close()

    def load_students(self):
        self.students_table.setRowCount(0)
        self.selected_student_id = None
        self.class_label.setText("-")
        self.clear_fee_state()

        if self.current_school_year_id is None:
            return

        search_text = self.search_input.text().strip()
        search_pattern = f"%{search_text}%"

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
                        s.id,
                        s.last_name || ' ' || s.first_name AS label,
                        c.name AS class_name
                    FROM students s
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    WHERE e.school_year_id = %s
                      AND s.is_active = TRUE
                      AND (
                          s.first_name ILIKE %s
                          OR s.last_name ILIKE %s
                          OR s.matricule ILIKE %s
                      )
                    ORDER BY s.last_name, s.first_name
                    """,
                    (
                        self.current_school_year_id,
                        search_pattern,
                        search_pattern,
                        search_pattern
                    )
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.last_name || ' ' || s.first_name AS label,
                        c.name AS class_name
                    FROM students s
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    WHERE e.school_year_id = %s
                      AND s.establishment_id = %s
                      AND s.is_active = TRUE
                      AND (
                          s.first_name ILIKE %s
                          OR s.last_name ILIKE %s
                          OR s.matricule ILIKE %s
                      )
                    ORDER BY s.last_name, s.first_name
                    """,
                    (
                        self.current_school_year_id,
                        self.current_user["establishment_id"],
                        search_pattern,
                        search_pattern,
                        search_pattern
                    )
                )

            rows = cursor.fetchall()

            self.students_table.setRowCount(len(rows))
            for i, (student_id, label, class_name) in enumerate(rows):
                self.students_table.setItem(i, 0, QTableWidgetItem(str(student_id)))
                self.students_table.setItem(i, 1, QTableWidgetItem(label))
                self.students_table.setItem(i, 2, QTableWidgetItem(class_name))

            self.students_table.resizeColumnsToContents()

            if rows:
                self.students_table.selectRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement élèves impossible : {e}")
        finally:
            conn.close()

    def clear_fee_state(self):
        self.fee_input.setRowCount(0)
        self.expected_amount_label.setText("0")
        self.total_paid_label.setText("0")
        self.remaining_label.setText("0")
        self.amount_input.setValue(0)

    def get_current_student_class(self, student_id):
        conn = get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.id, c.name
                FROM enrollments e
                JOIN classes c ON c.id = e.class_id
                WHERE e.student_id = %s
                  AND e.school_year_id = %s
                LIMIT 1
                """,
                (student_id, self.current_school_year_id)
            )
            return cursor.fetchone()

        except Exception:
            return None
        finally:
            conn.close()

    def on_student_selected(self):
        selected_row = self.students_table.currentRow()
        if selected_row == -1:
            self.selected_student_id = None
            self.class_label.setText("-")
            self.clear_fee_state()
            return

        student_id_item = self.students_table.item(selected_row, 0)
        if not student_id_item:
            return

        self.selected_student_id = int(student_id_item.text())
        self.load_fees_for_student()

    def load_fees_for_student(self):
        self.clear_fee_state()

        if self.selected_student_id is None:
            return

        class_row = self.get_current_student_class(self.selected_student_id)
        if not class_row:
            self.class_label.setText("-")
            return

        class_id, class_name = class_row
        self.class_label.setText(class_name)

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    cf.id AS class_fee_id,
                    f.name,
                    cf.amount,
                    cf.fee_id
                FROM class_fees cf
                JOIN fees f ON f.id = cf.fee_id
                WHERE cf.class_id = %s
                  AND cf.school_year_id = %s
                ORDER BY f.name
                """,
                (class_id, self.current_school_year_id)
            )
            rows = cursor.fetchall()

            self.fee_input.setRowCount(len(rows))
            for i, (class_fee_id, fee_name, amount, fee_id) in enumerate(rows):
                self.fee_input.setItem(i, 0, QTableWidgetItem(str(class_fee_id)))
                self.fee_input.setItem(i, 1, QTableWidgetItem(fee_name))
                self.fee_input.setItem(i, 2, QTableWidgetItem(f"{float(amount):.2f}"))
                self.fee_input.setItem(i, 3, QTableWidgetItem(str(fee_id)))

            self.fee_input.resizeColumnsToContents()

            if rows:
                self.fee_input.selectRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement frais impossible : {e}")
        finally:
            conn.close()

    def get_total_paid(self, student_id, class_fee_id):
        conn = get_connection()
        if not conn:
            return 0.0

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE student_id = %s
                  AND class_fee_id = %s
                """,
                (student_id, class_fee_id)
            )
            row = cursor.fetchone()
            return float(row[0] or 0)

        except Exception:
            return 0.0
        finally:
            conn.close()

    def get_discount(self, student_id, fee_id):
        conn = get_connection()
        if not conn:
            return 0.0

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM student_discounts
                WHERE student_id = %s
                  AND fee_id = %s
                """,
                (student_id, fee_id)
            )
            row = cursor.fetchone()
            return float(row[0] or 0)

        except Exception:
            return 0.0
        finally:
            conn.close()

    def on_fee_changed(self):
        self.expected_amount_label.setText("0")
        self.total_paid_label.setText("0")
        self.remaining_label.setText("0")
        self.amount_input.setValue(0)

        selected_row = self.fee_input.currentRow()
        if self.selected_student_id is None or selected_row == -1:
            return

        class_fee_id = int(self.fee_input.item(selected_row, 0).text())
        expected_amount = float(self.fee_input.item(selected_row, 2).text())
        fee_id = int(self.fee_input.item(selected_row, 3).text())

        total_paid = self.get_total_paid(self.selected_student_id, class_fee_id)
        discount = self.get_discount(self.selected_student_id, fee_id)

        net_expected = max(expected_amount - discount, 0)
        remaining = max(net_expected - total_paid, 0)

        self.expected_amount_label.setText(f"{net_expected:.2f}")
        self.total_paid_label.setText(f"{total_paid:.2f}")
        self.remaining_label.setText(f"{remaining:.2f}")

        if remaining > 0:
            self.amount_input.setValue(remaining)

    def generate_receipt_number(self):
        conn = get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            year_str = str(date.today().year)

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM payments
                WHERE receipt_number LIKE %s
                """,
                (f"RC-{year_str}-%",)
            )
            count = cursor.fetchone()[0]
            next_number = count + 1

            return f"RC-{year_str}-{next_number:05d}"

        except Exception:
            return None
        finally:
            conn.close()

    def save_payment(self):
        if self.selected_student_id is None:
            QMessageBox.warning(self, "Validation", "Veuillez sélectionner un élève.")
            return

        selected_fee_row = self.fee_input.currentRow()
        if selected_fee_row == -1:
            QMessageBox.warning(self, "Validation", "Veuillez sélectionner un frais.")
            return

        amount = float(self.amount_input.value())
        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Le montant doit être supérieur à 0.")
            return

        class_fee_id = int(self.fee_input.item(selected_fee_row, 0).text())
        fee_id = int(self.fee_input.item(selected_fee_row, 3).text())
        remaining = float(self.remaining_label.text())

        if amount > remaining and remaining > 0:
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Le montant dépasse le reste à payer. Voulez-vous continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        receipt_number = self.generate_receipt_number()
        if not receipt_number:
            QMessageBox.critical(self, "Erreur", "Impossible de générer le numéro de reçu.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO payments (
                    student_id, fee_id, class_fee_id, amount,
                    payment_date, receipt_number, created_by
                )
                VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, %s)
                RETURNING id
                """,
                (
                    self.selected_student_id,
                    fee_id,
                    class_fee_id,
                    amount,
                    receipt_number,
                    self.current_user["id"]
                )
            )

            payment_id = cursor.fetchone()[0]
            conn.commit()

            pdf_path = generate_receipt(payment_id)
            self.open_pdf(pdf_path)

            QMessageBox.information(
                self,
                "Succès",
                f"Paiement enregistré avec succès.\nReçu : {receipt_number}"
            )
            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Enregistrement impossible : {e}")
        finally:
            conn.close()

    def open_pdf(self, filepath):
        try:
            if sys.platform.startswith("win"):
                os.startfile(filepath)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", filepath], check=False)
            else:
                subprocess.run(["xdg-open", filepath], check=False)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Paiement enregistré, mais impossible d'ouvrir le reçu : {e}"
            )