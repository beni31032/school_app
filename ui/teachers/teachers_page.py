from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.teachers.add_teacher_dialog import AddTeacherDialog
from ui.teachers.edit_teacher_dialog import EditTeacherDialog
from utils.table_style import setup_table


class TeachersPage(QWidget):
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
            "Prénom",
            "Nom",
            "Téléphone",
            "Email",
            "Date d'embauche"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        self.refresh_btn.clicked.connect(self.load_teachers)

        self.load_teachers()

    def load_teachers(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, first_name, last_name, phone, email, hire_date
                FROM teachers
                ORDER BY last_name, first_name
                """
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
        dialog = AddTeacherDialog(parent=self)
        if dialog.exec():
            self.load_teachers()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un enseignant")
            return

        teacher_id_item = self.table.item(selected, 0)
        if not teacher_id_item:
            QMessageBox.warning(self, "Erreur", "Enseignant invalide")
            return

        teacher_id = teacher_id_item.text()

        dialog = EditTeacherDialog(teacher_id=teacher_id, parent=self)
        if dialog.exec():
            self.load_teachers()