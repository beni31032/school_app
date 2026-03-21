from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QHBoxLayout, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from ui.classes.add_class_dialog import AddClassDialog
from ui.classes.edit_class_dialog import EditClassDialog


class ClassesPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        self.layout = QVBoxLayout()

        # Boutons
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.refresh_btn = QPushButton("Actualiser")

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.refresh_btn.clicked.connect(self.load_classes)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.refresh_btn)

        self.layout.addLayout(btn_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Niveau",
            "Cycle",
            "Titulaire",
            "Assistant",
            "Établissement"
        ])

        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

        self.load_classes()

    # ===============================
    # LOAD CLASSES
    # ===============================
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
                        cy.name AS cycle_name,
                        COALESCE(t1.last_name || ' ' || t1.first_name, '') AS titular_name,
                        COALESCE(t2.last_name || ' ' || t2.first_name, '') AS assistant_name,
                        e.name AS establishment_name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    LEFT JOIN cycles cy ON cy.id = c.cycle_id
                    LEFT JOIN teachers t1 ON t1.id = c.titular_teacher_id
                    LEFT JOIN teachers t2 ON t2.id = c.assistant_teacher_id
                    ORDER BY e.name, cy.name, c.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        c.id,
                        c.name,
                        c.level,
                        cy.name AS cycle_name,
                        COALESCE(t1.last_name || ' ' || t1.first_name, '') AS titular_name,
                        COALESCE(t2.last_name || ' ' || t2.first_name, '') AS assistant_name,
                        e.name AS establishment_name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    LEFT JOIN cycles cy ON cy.id = c.cycle_id
                    LEFT JOIN teachers t1 ON t1.id = c.titular_teacher_id
                    LEFT JOIN teachers t2 ON t2.id = c.assistant_teacher_id
                    WHERE c.establishment_id = %s
                    ORDER BY cy.name, c.name
                    """,
                    (self.current_user["establishment_id"],)
                )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))

            for row_index, row_data in enumerate(rows):
                for col_index, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_index, col_index, item)

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    # ===============================
    # ADD
    # ===============================
    def open_add_dialog(self):
        dialog = AddClassDialog(self.current_user, self)
        if dialog.exec():
            self.load_classes()

    # ===============================
    # EDIT
    # ===============================
    def open_edit_dialog(self):
        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Sélection", "Veuillez sélectionner une classe.")
            return

        class_id_item = self.table.item(selected_row, 0)
        class_id = class_id_item.text()

        dialog = EditClassDialog(class_id, self.current_user, self)

        if dialog.exec():
            self.load_classes()