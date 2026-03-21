from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.class_fees.add_class_fee_dialog import AddClassFeeDialog
from ui.class_fees.edit_class_fee_dialog import EditClassFeeDialog
from utils.table_style import setup_table


class ClassFeesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        layout = QVBoxLayout()
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Établissement",
            "Frais",
            "Montant",
            "Année scolaire"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.refresh_btn.clicked.connect(self.load_data)

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
                        cf.id,
                        c.name AS class_name,
                        e.name AS establishment_name,
                        f.name AS fee_name,
                        cf.amount,
                        sy.name AS school_year_name
                    FROM class_fees cf
                    JOIN classes c ON c.id = cf.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN fees f ON f.id = cf.fee_id
                    JOIN school_years sy ON sy.id = cf.school_year_id
                    ORDER BY sy.name DESC, e.name, c.name, f.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        cf.id,
                        c.name AS class_name,
                        e.name AS establishment_name,
                        f.name AS fee_name,
                        cf.amount,
                        sy.name AS school_year_name
                    FROM class_fees cf
                    JOIN classes c ON c.id = cf.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN fees f ON f.id = cf.fee_id
                    JOIN school_years sy ON sy.id = cf.school_year_id
                    WHERE c.establishment_id = %s
                    ORDER BY sy.name DESC, c.name, f.name
                    """,
                    (self.current_user["establishment_id"],)
                )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    text = "" if value is None else str(value)
                    self.table.setItem(row_index, col_index, QTableWidgetItem(text))

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddClassFeeDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        class_fee_id_item = self.table.item(selected, 0)
        if not class_fee_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide")
            return

        class_fee_id = class_fee_id_item.text()

        dialog = EditClassFeeDialog(
            class_fee_id=class_fee_id,
            current_user=self.current_user,
            parent=self
        )
        if dialog.exec():
            self.load_data()