from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox,
    QHeaderView
)

from database.connection import get_connection


class StudentFinancePage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.current_school_year_id = None
        self.selected_student_id = None

        layout = QVBoxLayout()
        form = QFormLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un élève par nom, prénom ou matricule")

        form.addRow("Recherche élève :", self.search_input)
        layout.addLayout(form)

        self.students_table = QTableWidget()
        self.students_table.setColumnCount(3)
        self.students_table.setHorizontalHeaderLabels(["ID", "Élève", "Classe"])
        self.students_table.setColumnHidden(0, True)
        self.students_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.students_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(QLabel("Élèves"))
        layout.addWidget(self.students_table)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(5)
        self.summary_table.setHorizontalHeaderLabels([
            "Frais",
            "Montant prévu",
            "Réduction",
            "Payé",
            "Reste"
        ])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(QLabel("Résumé financier"))
        layout.addWidget(self.summary_table)

        layout.addWidget(QLabel("Total restant :"))
        self.total_remaining_label = QLabel("0.00")
        layout.addWidget(self.total_remaining_label)

        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels([
            "Reçu",
            "Frais",
            "Montant",
            "Date",
            "Saisi par"
        ])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(QLabel("Historique des paiements"))
        layout.addWidget(self.payments_table)

        self.setLayout(layout)

        self.search_input.textChanged.connect(self.load_students)
        self.students_table.itemSelectionChanged.connect(self.on_student_selected)

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

            if row:
                self.current_school_year_id = row[0]

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement année scolaire impossible : {e}")
        finally:
            conn.close()

    def load_students(self):
        self.students_table.setRowCount(0)
        self.summary_table.setRowCount(0)
        self.payments_table.setRowCount(0)
        self.total_remaining_label.setText("0.00")
        self.selected_student_id = None

        conn = get_connection()
        if not conn or self.current_school_year_id is None:
            return

        search_text = self.search_input.text().strip()
        search_pattern = f"%{search_text}%"

        try:
            cursor = conn.cursor()

            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.last_name || ' ' || s.first_name AS student_name,
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
                        s.last_name || ' ' || s.first_name AS student_name,
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

            for i, (student_id, student_name, class_name) in enumerate(rows):
                self.students_table.setItem(i, 0, QTableWidgetItem(str(student_id)))
                self.students_table.setItem(i, 1, QTableWidgetItem(student_name))
                self.students_table.setItem(i, 2, QTableWidgetItem(class_name))

            self.students_table.resizeColumnsToContents()

            if rows:
                self.students_table.selectRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement élèves impossible : {e}")
        finally:
            conn.close()

    def on_student_selected(self):
        selected_row = self.students_table.currentRow()

        if selected_row == -1:
            self.selected_student_id = None
            self.summary_table.setRowCount(0)
            self.payments_table.setRowCount(0)
            self.total_remaining_label.setText("0.00")
            return

        student_id_item = self.students_table.item(selected_row, 0)
        if not student_id_item:
            return

        self.selected_student_id = int(student_id_item.text())
        self.load_financial_summary()
        self.load_payment_history()

    def load_financial_summary(self):
        self.summary_table.setRowCount(0)
        self.total_remaining_label.setText("0.00")

        if self.selected_student_id is None or self.current_school_year_id is None:
            return

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    f.name,
                    cf.amount,
                    COALESCE((
                        SELECT SUM(sd.amount)
                        FROM student_discounts sd
                        WHERE sd.student_id = %s
                          AND sd.fee_id = f.id
                    ), 0) AS discount,
                    COALESCE((
                        SELECT SUM(p.amount)
                        FROM payments p
                        WHERE p.student_id = %s
                          AND p.class_fee_id = cf.id
                    ), 0) AS paid
                FROM class_fees cf
                JOIN fees f ON f.id = cf.fee_id
                JOIN enrollments e ON e.class_id = cf.class_id
                WHERE e.student_id = %s
                  AND e.school_year_id = %s
                  AND cf.school_year_id = %s
                ORDER BY f.name
                """,
                (
                    self.selected_student_id,
                    self.selected_student_id,
                    self.selected_student_id,
                    self.current_school_year_id,
                    self.current_school_year_id
                )
            )

            rows = cursor.fetchall()

            self.summary_table.setRowCount(len(rows))
            total_remaining = 0.0

            for i, row in enumerate(rows):
                fee_name, expected, discount, paid = row

                expected = float(expected or 0)
                discount = float(discount or 0)
                paid = float(paid or 0)
                remaining = (expected - discount) - paid

                total_remaining += remaining

                values = [
                    fee_name,
                    f"{expected:.2f}",
                    f"{discount:.2f}",
                    f"{paid:.2f}",
                    f"{remaining:.2f}"
                ]

                for j, value in enumerate(values):
                    self.summary_table.setItem(i, j, QTableWidgetItem(value))

            self.total_remaining_label.setText(f"{total_remaining:.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement résumé financier impossible : {e}")
        finally:
            conn.close()

    def load_payment_history(self):
        self.payments_table.setRowCount(0)

        if self.selected_student_id is None:
            return

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    p.receipt_number,
                    COALESCE(fcf.name, ffallback.name) AS fee_name,
                    p.amount,
                    p.payment_date,
                    u.username
                FROM payments p
                JOIN users u ON u.id = p.created_by
                LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                LEFT JOIN fees fcf ON fcf.id = cf.fee_id
                LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
                WHERE p.student_id = %s
                ORDER BY p.payment_date DESC, p.id DESC
                """,
                (self.selected_student_id,)
            )

            rows = cursor.fetchall()
            self.payments_table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                receipt_number, fee_name, amount, payment_date, username = row

                values = [
                    receipt_number or "",
                    fee_name or "",
                    f"{float(amount or 0):.2f}",
                    str(payment_date) if payment_date else "",
                    username or ""
                ]

                for j, value in enumerate(values):
                    self.payments_table.setItem(i, j, QTableWidgetItem(value))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement historique paiements impossible : {e}")
        finally:
            conn.close()