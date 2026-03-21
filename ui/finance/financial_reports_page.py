from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from utils.table_style import setup_table


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


class FinancialReportsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self.title_label = QLabel("Rapports financiers")
        self.title_label.setObjectName("dashboardTitle")

        self.subtitle_label = QLabel("Vue d'ensemble des encaissements")
        self.subtitle_label.setObjectName("dashboardSubtitle")

        # Cards
        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)

        self.today_card = StatCard("Total encaissé aujourd'hui", "0 FCFA")
        self.month_card = StatCard("Total encaissé ce mois", "0 FCFA")

        self.cards_layout.addWidget(self.today_card, 0, 0)
        self.cards_layout.addWidget(self.month_card, 0, 1)

        # Tableau frais
        self.fees_title = QLabel("Encaissement par type de frais")
        self.fees_title.setObjectName("sectionTitle")

        self.fees_table = QTableWidget()
        self.fees_table.setColumnCount(2)
        self.fees_table.setHorizontalHeaderLabels([
            "Type de frais",
            "Total encaissé"
        ])
        setup_table(self.fees_table, stretch=True)

        # Tableau classes
        self.classes_title = QLabel("Encaissement par classe")
        self.classes_title.setObjectName("sectionTitle")

        self.classes_table = QTableWidget()
        self.classes_table.setColumnCount(2)
        self.classes_table.setHorizontalHeaderLabels([
            "Classe",
            "Total encaissé"
        ])
        setup_table(self.classes_table, stretch=True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addLayout(self.cards_layout)
        layout.addWidget(self.fees_title)
        layout.addWidget(self.fees_table)
        layout.addWidget(self.classes_title)
        layout.addWidget(self.classes_table)

        self.setLayout(layout)

        self.apply_local_styles()
        self.load_reports()

    def apply_local_styles(self):
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
                margin-top: 10px;
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
        """)

    def load_reports(self):
        conn = get_connection()

        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            # Total aujourd'hui
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

            # Total ce mois
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments
                    WHERE DATE_TRUNC('month', payment_date) =
                          DATE_TRUNC('month', CURRENT_DATE)
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(p.amount), 0)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    WHERE DATE_TRUNC('month', p.payment_date) =
                          DATE_TRUNC('month', CURRENT_DATE)
                      AND s.establishment_id = %s
                    """,
                    (self.current_user["establishment_id"],)
                )

            month_total = float(cursor.fetchone()[0] or 0)

            self.today_card.value_label.setText(f"{today_total:,.0f} FCFA")
            self.month_card.value_label.setText(f"{month_total:,.0f} FCFA")

            # Par type de frais
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        COALESCE(f.name, ff.name),
                        SUM(p.amount)
                    FROM payments p
                    LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                    LEFT JOIN fees f ON f.id = cf.fee_id
                    LEFT JOIN fees ff ON ff.id = p.fee_id
                    GROUP BY COALESCE(f.name, ff.name)
                    ORDER BY 2 DESC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        COALESCE(f.name, ff.name),
                        SUM(p.amount)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
                    LEFT JOIN fees f ON f.id = cf.fee_id
                    LEFT JOIN fees ff ON ff.id = p.fee_id
                    WHERE s.establishment_id = %s
                    GROUP BY COALESCE(f.name, ff.name)
                    ORDER BY 2 DESC
                    """,
                    (self.current_user["establishment_id"],)
                )

            fee_rows = cursor.fetchall()

            self.fees_table.setRowCount(len(fee_rows))
            for i, row in enumerate(fee_rows):
                self.fees_table.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.fees_table.setItem(i, 1, QTableWidgetItem(f"{float(row[1]):,.0f}"))

            # Par classe
            if self.current_user["role"] == "ADMIN_GLOBAL":
                cursor.execute(
                    """
                    SELECT
                        c.name,
                        SUM(p.amount)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    GROUP BY c.name
                    ORDER BY 2 DESC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        c.name,
                        SUM(p.amount)
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    WHERE s.establishment_id = %s
                    GROUP BY c.name
                    ORDER BY 2 DESC
                    """,
                    (self.current_user["establishment_id"],)
                )

            class_rows = cursor.fetchall()

            self.classes_table.setRowCount(len(class_rows))
            for i, row in enumerate(class_rows):
                self.classes_table.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.classes_table.setItem(i, 1, QTableWidgetItem(f"{float(row[1]):,.0f}"))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
        finally:
            conn.close()