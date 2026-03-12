from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout
)

from database.connection import get_connection


class StudentsPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # boutons
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.delete_btn = QPushButton("Supprimer")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addWidget(self.refresh_btn)

        # tableau
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Matricule",
            "Nom",
            "Prénom",
            "Sexe",
            "Photo"
        ])

        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load_students()

    def load_students(self):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT matricule, first_name, last_name, gender, photo_path
        FROM students
        """)

        students = cursor.fetchall()

        self.table.setRowCount(len(students))

        for row, student in enumerate(students):
            for col, value in enumerate(student):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        conn.close()