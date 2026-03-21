from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QPushButton, QMessageBox, QDoubleSpinBox
)

from database.connection import get_connection
from utils.table_style import setup_table


class AddDiscountDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user
        self.selected_student_id = None

        self.setWindowTitle("Ajouter une réduction")
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un élève")

        self.students_table = QTableWidget()
        self.students_table.setColumnCount(3)
        self.students_table.setHorizontalHeaderLabels(["ID", "Élève", "Classe"])
        self.students_table.setColumnHidden(0, True)
        self.students_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        self.fee_table = QTableWidget()
        self.fee_table.setColumnCount(2)
        self.fee_table.setHorizontalHeaderLabels(["ID", "Frais"])
        self.fee_table.setColumnHidden(0, True)
        setup_table(self.fee_table)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(10000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(1000)

        self.reason_input = QLineEdit()

        form = QFormLayout()
        form.addRow("Montant :", self.amount_input)
        form.addRow("Motif :", self.reason_input)

        self.save_btn = QPushButton("Enregistrer")

        
        
        layout.addWidget(QLabel("Recherche élève"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.students_table)

        layout.addWidget(QLabel("Type de frais"))
        layout.addWidget(self.fee_table)

        layout.addLayout(form)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        self.search_input.textChanged.connect(self.load_students)
        self.students_table.itemSelectionChanged.connect(self.on_student_selected)
        self.save_btn.clicked.connect(self.save_discount)

        self.load_students()
        self.load_fees()

    def load_students(self):
        conn = get_connection()
        if not conn:
            return

        search = f"%{self.search_input.text()}%"

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.last_name || ' ' || s.first_name,
                    c.name
                FROM students s
                JOIN enrollments e ON e.student_id = s.id
                JOIN classes c ON c.id = e.class_id
                WHERE s.first_name ILIKE %s
                OR s.last_name ILIKE %s
                ORDER BY s.last_name
                """,
                (search, search)
            )

            rows = cursor.fetchall()

            self.students_table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    self.students_table.setItem(i, j, QTableWidgetItem(str(val)))

        finally:
            conn.close()

    def load_fees(self):
        conn = get_connection()
        if not conn:
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

            self.fee_table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    self.fee_table.setItem(i, j, QTableWidgetItem(str(val)))

        finally:
            conn.close()

    def on_student_selected(self):
        row = self.students_table.currentRow()

        if row != -1:
            self.selected_student_id = int(
                self.students_table.item(row, 0).text()
            )

    def save_discount(self):

        if not self.selected_student_id:
            QMessageBox.warning(self, "Validation", "Sélectionnez un élève.")
            return

        fee_row = self.fee_table.currentRow()

        if fee_row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez un frais.")
            return

        fee_id = int(self.fee_table.item(fee_row, 0).text())
        amount = float(self.amount_input.value())
        reason = self.reason_input.text()

        if amount <= 0:
            QMessageBox.warning(
                self,
                "Validation",
                "Le montant doit être supérieur à 0."
            )
            return

        conn = get_connection()

        if not conn:
            return

        try:
            cursor = conn.cursor()

            # vérifier doublon
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM student_discounts
                WHERE student_id = %s
                AND fee_id = %s
                """,
                (self.selected_student_id, fee_id)
            )

            if cursor.fetchone()[0] > 0:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Une réduction existe déjà pour ce frais."
                )
                return

            # vérifier montant max
            cursor.execute(
                """
                SELECT MAX(amount)
                FROM class_fees
                WHERE fee_id = %s
                """,
                (fee_id,)
            )

            row = cursor.fetchone()
            max_amount = float(row[0] or 0)

            if amount > max_amount:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "La réduction dépasse le montant du frais."
                )
                return

            cursor.execute(
                """
                INSERT INTO student_discounts
                (student_id, fee_id, amount, reason, created_by)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (
                    self.selected_student_id,
                    fee_id,
                    amount,
                    reason,
                    self.current_user["id"]
                )
            )

            conn.commit()

            QMessageBox.information(
                self,
                "Succès",
                "Réduction enregistrée avec succès."
            )

            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", str(e))

        finally:
            conn.close()