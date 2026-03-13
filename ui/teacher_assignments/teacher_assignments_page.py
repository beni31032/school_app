from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.teacher_assignments.add_teacher_assignment_dialog import AddTeacherAssignmentDialog
from ui.teacher_assignments.edit_teacher_assignment_dialog import EditTeacherAssignmentDialog


class TeacherAssignmentsPage(QWidget):
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
            "Enseignant",
            "Matière",
            "Classe",
            "Établissement",
            "Année scolaire"
        ])
        self.table.setColumnHidden(0, True)

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
                        ta.id,
                        t.first_name || ' ' || t.last_name AS teacher_name,
                        s.name AS subject_name,
                        c.name AS class_name,
                        e.name AS establishment_name,
                        sy.name AS school_year_name
                    FROM teacher_assignments ta
                    JOIN teachers t ON t.id = ta.teacher_id
                    JOIN subjects s ON s.id = ta.subject_id
                    JOIN classes c ON c.id = ta.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN school_years sy ON sy.id = ta.school_year_id
                    ORDER BY sy.name DESC, e.name, c.name, s.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        ta.id,
                        t.first_name || ' ' || t.last_name AS teacher_name,
                        s.name AS subject_name,
                        c.name AS class_name,
                        e.name AS establishment_name,
                        sy.name AS school_year_name
                    FROM teacher_assignments ta
                    JOIN teachers t ON t.id = ta.teacher_id
                    JOIN subjects s ON s.id = ta.subject_id
                    JOIN classes c ON c.id = ta.class_id
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN school_years sy ON sy.id = ta.school_year_id
                    WHERE c.establishment_id = %s
                    ORDER BY sy.name DESC, e.name, c.name, s.name
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
        dialog = AddTeacherAssignmentDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_data()

    def open_edit_dialog(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne")
            return

        assignment_id_item = self.table.item(selected, 0)
        if not assignment_id_item:
            QMessageBox.warning(self, "Erreur", "Affectation invalide")
            return

        assignment_id = assignment_id_item.text()

        dialog = EditTeacherAssignmentDialog(
            assignment_id=assignment_id,
            current_user=self.current_user,
            parent=self
        )
        if dialog.exec():
            self.load_data()