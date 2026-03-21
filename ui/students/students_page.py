from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.students.add_student_dialog import AddStudentDialog
from ui.students.edit_student_dialog import EditStudentDialog
from utils.table_style import setup_table


class StudentsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        layout = QVBoxLayout()

        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.delete_btn = QPushButton("Supprimer")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Matricule",
            "Prénom",
            "Nom",
            "Sexe",
            "Classe"
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.refresh_btn.clicked.connect(self.load_students)
        self.edit_btn.clicked.connect(self.edit_student)
        self.delete_btn.clicked.connect(self.delete_student)

        self.load_students()

    def load_students(self):
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
                        s.id,
                        s.matricule,
                        s.first_name,
                        s.last_name,
                        s.gender,
                        c.name AS class_name
                    FROM students s
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    WHERE e.school_year_id = (
                        SELECT id
                        FROM school_years
                        ORDER BY id DESC
                        LIMIT 1
                    )
                    AND s.is_active = TRUE
                    ORDER BY s.last_name, s.first_name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.matricule,
                        s.first_name,
                        s.last_name,
                        s.gender,
                        c.name AS class_name
                    FROM students s
                    JOIN enrollments e ON e.student_id = s.id
                    JOIN classes c ON c.id = e.class_id
                    WHERE e.school_year_id = (
                        SELECT id
                        FROM school_years
                        ORDER BY id DESC
                        LIMIT 1
                    )
                    AND s.establishment_id = %s
                    AND s.is_active = TRUE
                    ORDER BY s.last_name, s.first_name
                    """,
                    (self.current_user["establishment_id"],)
                )

            students = cursor.fetchall()

            self.table.setRowCount(len(students))

            for row, student in enumerate(students):
                for col, value in enumerate(student):
                    text = "" if value is None else str(value)
                    self.table.setItem(row, col, QTableWidgetItem(text))

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()
            
    def edit_student(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un élève")
            return

        student_id_item = self.table.item(selected, 0)
        if not student_id_item:
            QMessageBox.warning(self, "Erreur", "Élève invalide")
            return

        student_id = student_id_item.text()

        dialog = EditStudentDialog(
            student_id=student_id,
            current_user=self.current_user,
            parent=self
        )

        if dialog.exec():
            self.load_students()
            
            
    def delete_student(self):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un élève")
            return

        student_id_item = self.table.item(selected, 0)
        if not student_id_item:
            QMessageBox.warning(self, "Erreur", "Élève invalide")
            return

        student_id = student_id_item.text()

        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous vraiment désactiver cet élève ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE students
                SET is_active = FALSE
                WHERE id = %s
                """,
                (student_id,)
            )
            conn.commit()

            QMessageBox.information(self, "Succès", "Élève désactivé avec succès.")
            self.load_students()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Suppression impossible : {e}")
        finally:
            conn.close()
            

    def open_add_dialog(self):
        dialog = AddStudentDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_students()