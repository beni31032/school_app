import os
import sys
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QAbstractItemView
)

from database.connection import get_connection
from utils.pdf_utils import merge_pdfs
from utils.table_style import setup_table
from utils.primary_bulletin_generator import generate_primary_bulletin


class PrimaryBulletinsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.buttons_layout = QHBoxLayout()

        self.class_input = QComboBox()
        self.term_input = QComboBox()

        self.load_btn = QPushButton("Charger")
        self.print_one_btn = QPushButton("Imprimer l'élève sélectionné")
        self.print_all_btn = QPushButton("Imprimer toute la classe")

        self.table = QTableWidget()
        setup_table(self.table, stretch=True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Trimestre :", self.term_input)

        self.buttons_layout.addWidget(self.load_btn)
        self.buttons_layout.addWidget(self.print_one_btn)
        self.buttons_layout.addWidget(self.print_all_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(self.buttons_layout)
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)

        self.load_btn.clicked.connect(self.load_students)
        self.print_one_btn.clicked.connect(self.print_bulletin)
        self.print_all_btn.clicked.connect(self.print_all_bulletins)

        self.load_classes()
        self.load_terms()

    def load_classes(self):
        self.class_input.clear()

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
                        e.name || ' - ' || c.name
                    FROM classes c
                    JOIN establishments e ON e.id = c.establishment_id
                    JOIN cycles cy ON cy.id = c.cycle_id
                    WHERE cy.name = 'Primaire'
                    ORDER BY e.name, c.name
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        c.id,
                        c.name
                    FROM classes c
                    JOIN cycles cy ON cy.id = c.cycle_id
                    WHERE c.establishment_id = %s
                      AND cy.name = 'Primaire'
                    ORDER BY c.name
                    """,
                    (self.current_user["establishment_id"],)
                )

            for class_id, label in cursor.fetchall():
                self.class_input.addItem(label, class_id)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement classes impossible : {e}")
        finally:
            conn.close()

    def load_terms(self):
        self.term_input.clear()

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM terms
                ORDER BY id
                """
            )

            for term_id, name in cursor.fetchall():
                self.term_input.addItem(name, term_id)

        finally:
            conn.close()

    def load_students(self):
        class_id = self.class_input.currentData()
        term_id = self.term_input.currentData()

        if class_id is None or term_id is None:
            QMessageBox.warning(self, "Validation", "Classe et trimestre obligatoires.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT school_year_id
                FROM terms
                WHERE id = %s
                """,
                (term_id,)
            )
            row = cursor.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Trimestre invalide.")
                return

            school_year_id = row[0]

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.matricule,
                    s.last_name || ' ' || s.first_name AS student_name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND s.is_active = TRUE
                ORDER BY s.last_name, s.first_name
                """,
                (class_id, school_year_id)
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["ID", "Matricule", "Élève"])
            self.table.setColumnHidden(0, True)

            for i, (student_id, matricule, student_name) in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(str(student_id)))
                self.table.setItem(i, 1, QTableWidgetItem("" if matricule is None else str(matricule)))
                self.table.setItem(i, 2, QTableWidgetItem(student_name))

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement élèves impossible : {e}")
        finally:
            conn.close()

    def print_bulletin(self):
        selected_row = self.table.currentRow()
        term_id = self.term_input.currentData()

        if selected_row == -1:
            QMessageBox.warning(self, "Validation", "Sélectionnez un élève.")
            return

        if term_id is None:
            QMessageBox.warning(self, "Validation", "Sélectionnez un trimestre.")
            return

        student_id_item = self.table.item(selected_row, 0)
        if not student_id_item:
            QMessageBox.warning(self, "Erreur", "Élève invalide.")
            return

        student_id = int(student_id_item.text())

        try:
            pdf_path = generate_primary_bulletin(student_id, term_id)
            self.open_pdf(pdf_path)

            QMessageBox.information(
                self,
                "Succès",
                f"Bulletin généré : {pdf_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération bulletin impossible : {e}")

    def print_all_bulletins(self):
        class_id = self.class_input.currentData()
        term_id = self.term_input.currentData()

        if class_id is None or term_id is None:
            QMessageBox.warning(self, "Validation", "Sélectionnez une classe et un trimestre.")
            return

        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Validation", "Chargez d'abord les élèves de la classe.")
            return

        generated_files = []

        try:
            class_label = self.class_input.currentText().replace(" - ", "_").replace(" ", "_").replace("/", "_")
            term_label = self.term_input.currentText().replace(" ", "_").replace("/", "_")

            for row in range(self.table.rowCount()):
                student_id_item = self.table.item(row, 0)
                if not student_id_item:
                    continue

                student_id = int(student_id_item.text())
                pdf_path = generate_primary_bulletin(student_id, term_id)
                generated_files.append(pdf_path)

            if not generated_files:
                QMessageBox.warning(self, "Erreur", "Aucun bulletin n'a été généré.")
                return

            merged_output = f"bulletins/primary/{class_label}_{term_label}_classe_complete.pdf"
            merged_pdf = merge_pdfs(generated_files, merged_output)

            self.open_pdf(merged_pdf)

            QMessageBox.information(
                self,
                "Succès",
                f"{len(generated_files)} bulletin(s) généré(s) et fusionné(s).\nFichier : {merged_pdf}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération des bulletins impossible : {e}")
    def open_pdf(self, filepath):
        try:
            if sys.platform.startswith("win"):
                os.startfile(filepath)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", filepath], check=False)
            else:
                subprocess.run(["xdg-open", filepath], check=False)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Bulletin généré, mais impossible de l'ouvrir : {e}"
            )

    def open_path(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Bulletins générés, mais impossible d'ouvrir le dossier : {e}"
            )