from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

from database.connection import get_connection


class StatCard(QFrame):
    def __init__(self, title: str, value: str):
        super().__init__()

        self.setObjectName("statCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

        self.setLayout(layout)


class DashboardPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

        self.title_label = QLabel("Tableau de bord")
        self.title_label.setObjectName("dashboardTitle")

        self.subtitle_label = QLabel("Vue d'ensemble du système scolaire")
        self.subtitle_label.setObjectName("dashboardSubtitle")

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)

        self.students_card = StatCard("Élèves", "0")
        self.teachers_card = StatCard("Enseignants", "0")
        self.classes_card = StatCard("Classes", "0")
        self.today_payments_card = StatCard("Encaissement du jour", "0 FCFA")
        self.month_payments_card = StatCard("Encaissement du mois", "0 FCFA")
        self.remaining_card = StatCard("Reste global à payer", "0 FCFA")

        self.cards_layout.addWidget(self.students_card, 0, 0)
        self.cards_layout.addWidget(self.teachers_card, 0, 1)
        self.cards_layout.addWidget(self.classes_card, 0, 2)
        self.cards_layout.addWidget(self.today_payments_card, 1, 0)
        self.cards_layout.addWidget(self.month_payments_card, 1, 1)
        self.cards_layout.addWidget(self.remaining_card, 1, 2)

        self.recent_title = QLabel("Derniers paiements")
        self.recent_title.setObjectName("sectionTitle")

        self.recent_payments_table = QTableWidget()
        self.recent_payments_table.setColumnCount(5)
        self.recent_payments_table.setHorizontalHeaderLabels([
            "Reçu",
            "Élève",
            "Frais",
            "Montant",
            "Date"
        ])

        self.recent_payments_table.verticalHeader().setVisible(False)
        self.recent_payments_table.setAlternatingRowColors(True)
        self.recent_payments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_payments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_payments_table.horizontalHeader().setStretchLastSection(True)
        self.recent_payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.subtitle_label)
        self.main_layout.addLayout(self.cards_layout)
        self.main_layout.addWidget(self.recent_title)
        self.main_layout.addWidget(self.recent_payments_table)

        self.setLayout(self.main_layout)

        self.apply_styles()
        self.load_data()

    def apply_styles(self):
        self.setStyleSheet("""
            QLabel#dashboardTitle {
                font-size: 24px;
                font-weight: bold;
                color: #111827;
                margin-bottom: 4px;
            }

            QLabel#dashboardSubtitle {
                font-size: 13px;
                color: #6b7280;
                margin-bottom: 10px;
            }

            QLabel#sectionTitle {
                font-size: 16px;
                font-weight: bold;
                color: #111827;
                margin-top: 18px;
                margin-bottom: 6px;
            }

            QFrame#statCard {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }

            QLabel#statTitle {
                font-size: 13px;
                color: #6b7280;
            }

            QLabel#statValue {
                font-size: 22px;
                font-weight: bold;
                color: #111827;
                margin-top: 6px;
            }

            QTableWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e5e7eb;
                alternate-background-color: #f8fafc;
                gridline-color: #e5e7eb;
            }

            QHeaderView::section {
                background-color: #2563eb;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

    def load_data(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            # Élèves
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM students
                    WHERE is_active = TRUE
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM students
                    WHERE is_active = TRUE
                      AND establishment_id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )

            students_count = cursor.fetchone()[0]

            # Enseignants
            cursor.execute("SELECT COUNT(*) FROM teachers")
            teachers_count = cursor.fetchone()[0]

            # Classes
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute("SELECT COUNT(*) FROM classes")
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM classes
                    WHERE establishment_id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )

            classes_count = cursor.fetchone()[0]

            # Encaissement du jour
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments
                    WHERE payment_date = CURRENT_DATE
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(p.amount), 0)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    WHERE p.payment_date = CURRENT_DATE
                      AND s.establishment_id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )

            today_total = float(cursor.fetchone()[0] or 0)

            # Encaissement du mois
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments
                    WHERE DATE_TRUNC('month', payment_date) = DATE_TRUNC('month', CURRENT_DATE)
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(p.amount), 0)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    WHERE DATE_TRUNC('month', p.payment_date) = DATE_TRUNC('month', CURRENT_DATE)
                      AND s.establishment_id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )

            month_total = float(cursor.fetchone()[0] or 0)

            # Reste global à payer
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(remaining_data.remaining), 0)
                    FROM (
                        SELECT
                            e.student_id,
                            cf.id AS class_fee_id,
                            GREATEST(
                                cf.amount
                                - COALESCE((
                                    SELECT SUM(sd.amount)
                                    FROM student_discounts sd
                                    WHERE sd.student_id = e.student_id
                                      AND sd.fee_id = cf.fee_id
                                ), 0)
                                - COALESCE((
                                    SELECT SUM(p.amount)
                                    FROM payments p
                                    WHERE p.student_id = e.student_id
                                      AND p.class_fee_id = cf.id
                                ), 0),
                                0
                            ) AS remaining
                        FROM enrollments e
                        JOIN class_fees cf
                          ON cf.class_id = e.class_id
                         AND cf.school_year_id = e.school_year_id
                        JOIN students s ON s.id = e.student_id
                        WHERE s.is_active = TRUE
                    ) AS remaining_data
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(remaining_data.remaining), 0)
                    FROM (
                        SELECT
                            e.student_id,
                            cf.id AS class_fee_id,
                            GREATEST(
                                cf.amount
                                - COALESCE((
                                    SELECT SUM(sd.amount)
                                    FROM student_discounts sd
                                    WHERE sd.student_id = e.student_id
                                      AND sd.fee_id = cf.fee_id
                                ), 0)
                                - COALESCE((
                                    SELECT SUM(p.amount)
                                    FROM payments p
                                    WHERE p.student_id = e.student_id
                                      AND p.class_fee_id = cf.id
                                ), 0),
                                0
                            ) AS remaining
                        FROM enrollments e
                        JOIN class_fees cf
                          ON cf.class_id = e.class_id
                         AND cf.school_year_id = e.school_year_id
                        JOIN students s ON s.id = e.student_id
                        WHERE s.is_active = TRUE
                          AND s.establishment_id = %s
                    ) AS remaining_data
                    """,
                    (self.current_user["establishment_id"],)
                )

            remaining_total = float(cursor.fetchone()[0] or 0)

            # Derniers paiements
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        p.receipt_number,
                        s.last_name || ' ' || s.first_name AS student_name,
                        COALESCE(fcf.name, ffallback.name) AS fee_name,
                        p.amount,
                        p.payment_date
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                    LEFT JOIN fees fcf ON fcf.id = cf.fee_id
                    LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
                    ORDER BY p.id DESC
                    LIMIT 10
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        p.receipt_number,
                        s.last_name || ' ' || s.first_name AS student_name,
                        COALESCE(fcf.name, ffallback.name) AS fee_name,
                        p.amount,
                        p.payment_date
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                    LEFT JOIN fees fcf ON fcf.id = cf.fee_id
                    LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
                    WHERE s.establishment_id = %s
                    ORDER BY p.id DESC
                    LIMIT 10
                    """,
                    (self.current_user["establishment_id"],)
                )

            recent_rows = cursor.fetchall()

            # Injection des valeurs
            self.students_card.value_label.setText(str(students_count))
            self.teachers_card.value_label.setText(str(teachers_count))
            self.classes_card.value_label.setText(str(classes_count))
            self.today_payments_card.value_label.setText(f"{today_total:,.0f} FCFA")
            self.month_payments_card.value_label.setText(f"{month_total:,.0f} FCFA")
            self.remaining_card.value_label.setText(f"{remaining_total:,.0f} FCFA")

            self.recent_payments_table.setRowCount(len(recent_rows))
            for i, row in enumerate(recent_rows):
                receipt, student, fee, amount, pay_date = row
                values = [
                    receipt or "",
                    student or "",
                    fee or "",
                    f"{float(amount or 0):,.0f}",
                    str(pay_date) if pay_date else ""
                ]
                for j, value in enumerate(values):
                    self.recent_payments_table.setItem(i, j, QTableWidgetItem(value))

            self.recent_payments_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement dashboard impossible : {e}")
        finally:
            conn.close()