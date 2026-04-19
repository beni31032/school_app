from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QPushButton, QMessageBox, QDoubleSpinBox, QHBoxLayout
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from utils.table_style import setup_table


class AddDiscountDialog(QDialog):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)

        self.current_user = current_user
        self.selected_student_id = None
        self.current_school_year_id = None

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
        self.cancel_btn = QPushButton("Annuler")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addWidget(QLabel("Recherche élève"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.students_table)

        layout.addWidget(QLabel("Type de frais"))
        layout.addWidget(self.fee_table)

        layout.addLayout(form)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.apply_local_styles()

        self.search_input.textChanged.connect(self.load_students)
        self.students_table.itemSelectionChanged.connect(self.on_student_selected)
        self.save_btn.clicked.connect(self.save_discount)
        self.cancel_btn.clicked.connect(self.reject)

        self.load_current_school_year()
        self.load_students()
        self.load_fees()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f8fafc; }
            QLabel {
                color: #111827;
                font-weight: 600;
            }
            QLineEdit, QDoubleSpinBox {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QTableWidget {
                background-color: white;
                color: #111827;
                gridline-color: #d1d5db;
                selection-background-color: #bfdbfe;
                selection-color: #111827;
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
            if row:
                self.current_school_year_id = row[0]
        finally:
            conn.close()

    def load_students(self):
        conn = get_connection()
        if not conn:
            return

        if self.current_school_year_id is None:
            self.students_table.setRowCount(0)
            return

        search = f"%{self.search_input.text()}%"

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.last_name || ' ' || s.first_name,
                        c.name
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
                    (self.current_school_year_id, search, search, search)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.last_name || ' ' || s.first_name,
                        c.name
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
                        search,
                        search,
                        search
                    )
                )

            rows = cursor.fetchall()

            self.students_table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    item = QTableWidgetItem(str(val))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.students_table.setItem(i, j, item)

            if rows:
                self.students_table.selectRow(0)

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
                    item = QTableWidgetItem(str(val))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.fee_table.setItem(i, j, item)

            if rows:
                self.fee_table.selectRow(0)

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
        reason = self.reason_input.text().strip()

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

            # vérifier montant max selon la classe de l'élève sur l'année en cours
            cursor.execute(
                """
                SELECT cf.amount
                FROM class_fees cf
                JOIN enrollments e
                  ON e.class_id = cf.class_id
                 AND e.school_year_id = cf.school_year_id
                WHERE e.student_id = %s
                  AND e.school_year_id = %s
                  AND cf.fee_id = %s
                LIMIT 1
                """,
                (self.selected_student_id, self.current_school_year_id, fee_id)
            )

            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(
                    self,
                    "Validation",
                    "Aucun frais configuré pour cet élève et ce type de frais."
                )
                return

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
