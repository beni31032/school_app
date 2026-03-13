from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.classes.add_class_dialog import AddClassDialog
from ui.classes.edit_class_dialog import EditClassDialog


class ClassesPage(QWidget):
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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Niveau",
            "Établissement"
        ])
        self.table.setColumnHidden(0, True)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.refresh_btn.clicked.connect(self.load_classes)

        self.load_classes()

    def load_classes(self):
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
                        c.id,
                        c.name,
                        c.level,
                        e.name AS establishment_name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    ORDER BY e.name, c.level, c.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        c.id,
                        c.name,
                        c.level,
                        e.name AS establishment_name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    WHERE c.establishment_id = %s
                    ORDER BY c.level, c.name
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
        dialog = AddClassDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_classes()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une classe")
            return

        class_id_item = self.table.item(selected, 0)
        if not class_id_item:
            QMessageBox.warning(self, "Erreur", "Classe invalide")
            return

        class_id = class_id_item.text()

        dialog = EditClassDialog(
            class_id=class_id,
            current_user=self.current_user,
            parent=self
        )
        if dialog.exec():
            self.load_classes()