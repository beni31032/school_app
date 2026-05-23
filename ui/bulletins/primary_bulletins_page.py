# utils/primary_bulletin_gpage.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QAbstractItemView, QLineEdit, QLabel, QFrame, QInputDialog
)
from PyQt6.QtCore import Qt

from database.connection import get_connection
from utils.pdf_utils import merge_pdfs
from utils.system_printing import (
    get_available_printer_names,
    get_default_printer_name,
    get_printing_diagnostic,
    open_file,
    send_file_to_printer,
)
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
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par matricule, nom ou prénom")

        self.load_btn = QPushButton("Charger")
        self.preview_btn = QPushButton("Aperçu PDF")
        self.print_one_btn = QPushButton("Imprimer l'élève sélectionné")
        self.print_all_btn = QPushButton("Imprimer toute la classe")

        self.table = QTableWidget()
        setup_table(self.table, stretch=True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("bulletinsSummaryCard")
        summary_layout = QFormLayout(self.summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setVerticalSpacing(6)
        self.info_class = QLabel("-")
        self.info_term = QLabel("-")
        self.info_students = QLabel("0")
        summary_layout.addRow("Classe :", self.info_class)
        summary_layout.addRow("Trimestre :", self.info_term)
        summary_layout.addRow("Élèves chargés :", self.info_students)

        self.form_layout.addRow("Classe :", self.class_input)
        self.form_layout.addRow("Trimestre :", self.term_input)
        self.form_layout.addRow("Recherche :", self.search_input)

        self.buttons_layout.addWidget(self.load_btn)
        self.buttons_layout.addWidget(self.preview_btn)
        self.buttons_layout.addWidget(self.print_one_btn)
        self.buttons_layout.addWidget(self.print_all_btn)

        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(self.buttons_layout)
        self.layout.addWidget(self.summary_card)
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QLineEdit {
                background-color: white;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 28px;
            }
            QFrame#bulletinsSummaryCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.load_btn.clicked.connect(self.load_students)
        self.preview_btn.clicked.connect(self.preview_bulletin)
        self.print_one_btn.clicked.connect(self.print_bulletin)
        self.print_all_btn.clicked.connect(self.print_all_bulletins)
        self.search_input.textChanged.connect(self.load_students)

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
                  AND (
                      s.matricule ILIKE %s
                      OR s.first_name ILIKE %s
                      OR s.last_name ILIKE %s
                  )
                ORDER BY s.last_name, s.first_name
                """,
                (
                    class_id,
                    school_year_id,
                    f"%{self.search_input.text().strip()}%",
                    f"%{self.search_input.text().strip()}%",
                    f"%{self.search_input.text().strip()}%",
                )
            )

            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["ID", "Matricule", "Élève"])
            self.table.setColumnHidden(0, True)

            for i, (student_id, matricule, student_name) in enumerate(rows):
                values = (str(student_id), "" if matricule is None else str(matricule), student_name)
                for j, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i, j, item)

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.info_class.setText(self.class_input.currentText() or "-")
            self.info_term.setText(self.term_input.currentText() or "-")
            self.info_students.setText(str(len(rows)))
            if rows:
                self.table.selectRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement élèves impossible : {e}")
        finally:
            conn.close()

    def preview_bulletin(self):
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
                "Aperçu PDF",
                f"Aperçu généré : {pdf_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération bulletin impossible : {e}")

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
            self.print_pdf_file(pdf_path, "Bulletin envoyé à l'impression.")
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
            self.print_pdf_file(
                merged_pdf,
                f"{len(generated_files)} bulletin(s) généré(s) et fusionné(s)."
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération des bulletins impossible : {e}")

    def open_pdf(self, filepath):
        try:
            open_file(filepath)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Bulletin généré, mais impossible de l'ouvrir : {e}"
            )

    def print_pdf_file(self, filepath, prefix_message):
        printer_names = get_available_printer_names()
        if not printer_names:
            self.open_pdf(filepath)
            QMessageBox.warning(
                self,
                "Impression indisponible",
                (
                    f"{get_printing_diagnostic()}\n\n"
                    "Le PDF a quand même été ouvert pour que vous puissiez l'enregistrer "
                    "ou l'imprimer plus tard sur un poste configuré."
                ),
            )
            return

        printer_name = self.choose_printer(printer_names)
        if not printer_name:
            return

        try:
            result_message = send_file_to_printer(filepath, printer_name)
            QMessageBox.information(
                self,
                "Impression",
                f"{prefix_message}\n\nImprimante : {printer_name}\n{result_message}",
            )
        except Exception as e:
            self.open_pdf(filepath)
            QMessageBox.warning(
                self,
                "Impression",
                (
                    f"Envoi direct à l'imprimante impossible : {e}\n\n"
                    "Le PDF a été ouvert pour que vous puissiez essayer une impression manuelle."
                ),
            )

    def choose_printer(self, printer_names):
        if len(printer_names) == 1:
            return printer_names[0]

        default_printer = get_default_printer_name()
        default_index = 0
        if default_printer in printer_names:
            default_index = printer_names.index(default_printer)

        printer_name, accepted = QInputDialog.getItem(
            self,
            "Choisir l'imprimante",
            "Imprimante :",
            printer_names,
            default_index,
            False,
        )
        if not accepted or not printer_name:
            return None
        return printer_name

    def open_path(self, path):
        try:
            open_file(path)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Bulletins générés, mais impossible d'ouvrir le dossier : {e}"
            )
