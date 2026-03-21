from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.class_subjects.add_class_subject_dialog import AddClassSubjectDialog
from ui.class_subjects.edit_class_subject_dialog import EditClassSubjectDialog
from utils.table_style import setup_table


class ClassSubjectsPage(QWidget):
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Classe",
            "Établissement",
            "Matière",
            "Coefficient"
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
                        cs.id,
                        c.name AS class_name,
                        e.name AS establishment_name,
                        s.name AS subject_name,
                        cs.coefficient
                    FROM class_subjects cs
                    JOIN classes c ON c.id = cs.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN subjects s ON s.id = cs.subject_id
                    ORDER BY e.name, c.name, s.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        cs.id,
                        c.name AS class_name,
                        e.name AS establishment_name,
                        s.name AS subject_name,
                        cs.coefficient
                    FROM class_subjects cs
                    JOIN classes c ON c.id = cs.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN subjects s ON s.id = cs.subject_id
                    WHERE c.establishment_id = %s
                    ORDER BY e.name, c.name, s.name
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
        dialog = AddClassSubjectDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        class_subject_id_item = self.table.item(selected, 0)
        if not class_subject_id_item:
            QMessageBox.warning(self, "Erreur", "Ligne invalide")
            return

        class_subject_id = class_subject_id_item.text()

        dialog = EditClassSubjectDialog(
            class_subject_id=class_subject_id,
            current_user=self.current_user,
            parent=self
        )
        if dialog.exec():
            self.load_data()