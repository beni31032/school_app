from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QLineEdit,
    QLabel,
    QComboBox,
    QFrame,
    QFormLayout,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os

from database.connection import get_connection
from ui.students.add_student_dialog import AddStudentDialog
from ui.students.edit_student_dialog import EditStudentDialog
from ui.students.student_details_dialog import StudentDetailsDialog
from utils.table_style import setup_table


class StudentsPage(QWidget):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.is_global_admin = self.current_user["role"] == "ADMIN_GLOBAL"

        layout = QVBoxLayout()

        filters_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher: matricule, nom, prénom...")

        self.status_filter = QComboBox()
        self.status_filter.addItem("Actifs", "ACTIVE")
        self.status_filter.addItem("Inactifs", "INACTIVE")
        self.status_filter.addItem("Tous", "ALL")

        self.establishment_filter = QComboBox()
        self.school_year_filter = QComboBox()
        self.class_filter = QComboBox()

        filters_layout.addWidget(QLabel("Recherche"))
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(QLabel("Statut"))
        filters_layout.addWidget(self.status_filter)
        filters_layout.addWidget(QLabel("Établissement"))
        filters_layout.addWidget(self.establishment_filter)
        filters_layout.addWidget(QLabel("Année scolaire"))
        filters_layout.addWidget(self.school_year_filter)
        filters_layout.addWidget(QLabel("Classe"))
        filters_layout.addWidget(self.class_filter)

        buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("Ajouter")
        self.edit_btn = QPushButton("Modifier")
        self.deactivate_btn = QPushButton("Désactiver")
        self.reactivate_btn = QPushButton("Réactiver")
        self.details_btn = QPushButton("Voir fiche complète")
        self.refresh_btn = QPushButton("Actualiser")

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.deactivate_btn)
        buttons_layout.addWidget(self.reactivate_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Matricule",
            "Nom",
            "Prénom",
            "Sexe",
            "Classe",
            "Établissement",
            "Statut",
        ])
        self.table.setColumnHidden(0, True)
        setup_table(self.table)

        self.details_card = QFrame()
        self.details_card.setObjectName("studentDetailsCard")
        details_layout = QHBoxLayout(self.details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(16)

        self.photo_label = QLabel("Aucune photo")
        self.photo_label.setFixedSize(130, 160)
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setStyleSheet(
            "QLabel { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; color: #6b7280; }"
        )

        form_wrapper = QWidget()
        form = QFormLayout(form_wrapper)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(6)

        self.detail_matricule = QLabel("-")
        self.detail_last_name = QLabel("-")
        self.detail_first_name = QLabel("-")
        self.detail_gender = QLabel("-")
        self.detail_birth_date = QLabel("-")
        self.detail_establishment = QLabel("-")
        self.detail_class = QLabel("-")
        self.detail_status = QLabel("-")
        self.detail_photo_path = QLabel("-")
        self.detail_photo_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        form.addRow("Matricule :", self.detail_matricule)
        form.addRow("Nom :", self.detail_last_name)
        form.addRow("Prénom :", self.detail_first_name)
        form.addRow("Sexe :", self.detail_gender)
        form.addRow("Date de naissance :", self.detail_birth_date)
        form.addRow("Établissement :", self.detail_establishment)
        form.addRow("Classe :", self.detail_class)
        form.addRow("Statut :", self.detail_status)
        form.addRow("Chemin photo :", self.detail_photo_path)

        details_layout.addWidget(self.photo_label)
        details_layout.addWidget(form_wrapper, 1)

        layout.addLayout(filters_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.details_card)

        self.setLayout(layout)
        self.setStyleSheet(
            """
            QLabel { color: #111827; font-weight: 600; }
            QFrame#studentDetailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            """
        )

        self.add_btn.clicked.connect(self.open_add_dialog)
        self.refresh_btn.clicked.connect(self.load_students)
        self.edit_btn.clicked.connect(self.edit_student)
        self.deactivate_btn.clicked.connect(lambda: self.set_student_active(False))
        self.reactivate_btn.clicked.connect(lambda: self.set_student_active(True))
        self.details_btn.clicked.connect(self.open_details_dialog)

        self.search_input.textChanged.connect(self.load_students)
        self.status_filter.currentIndexChanged.connect(self.load_students)
        self.establishment_filter.currentIndexChanged.connect(self.on_establishment_changed)
        self.school_year_filter.currentIndexChanged.connect(self.on_school_year_changed)
        self.class_filter.currentIndexChanged.connect(self.load_students)
        self.table.itemSelectionChanged.connect(self.load_selected_student_details)

        self.load_establishment_filter()
        self.load_school_year_filter()
        self.load_class_filter()
        self.load_students()

    def load_establishment_filter(self):
        self.establishment_filter.clear()

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                self.establishment_filter.addItem("Tous", None)
                cursor.execute("SELECT id, name FROM establishments ORDER BY name")
                for est_id, name in cursor.fetchall():
                    self.establishment_filter.addItem(name, est_id)
            else:
                est_id = self.current_user["establishment_id"]
                cursor.execute("SELECT id, name FROM establishments WHERE id = %s", (est_id,))
                row = cursor.fetchone()
                if row:
                    self.establishment_filter.addItem(row[1], row[0])
                self.establishment_filter.setEnabled(False)
        finally:
            conn.close()

    def on_establishment_changed(self):
        self.load_class_filter()
        self.load_students()

    def on_school_year_changed(self):
        self.load_class_filter()
        self.load_students()

    def load_school_year_filter(self):
        self.school_year_filter.clear()

        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name
                FROM school_years
                ORDER BY id DESC
                """
            )
            for school_year_id, name in cursor.fetchall():
                self.school_year_filter.addItem(name, school_year_id)
        finally:
            conn.close()

    def load_class_filter(self):
        self.class_filter.clear()
        self.class_filter.addItem("Toutes", None)

        est_id = self.establishment_filter.currentData()
        school_year_id = self.school_year_filter.currentData()
        conn = get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            filters = []
            params = []

            if school_year_id is not None:
                filters.append("e.school_year_id = %s")
                params.append(school_year_id)

            if self.is_global_admin:
                if est_id is not None:
                    filters.append("c.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("c.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            where_sql = "WHERE " + " AND ".join(filters) if filters else ""
            cursor.execute(
                f"""
                SELECT DISTINCT c.id, c.name
                FROM classes c
                LEFT JOIN enrollments e ON e.class_id = c.id
                {where_sql}
                ORDER BY c.name
                """,
                params,
            )
            for class_id, name in cursor.fetchall():
                self.class_filter.addItem(name, class_id)
        finally:
            conn.close()

    def load_students(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        search = f"%{self.search_input.text().strip()}%"
        status_mode = self.status_filter.currentData()
        est_id = self.establishment_filter.currentData()
        school_year_id = self.school_year_filter.currentData()
        class_id = self.class_filter.currentData()

        try:
            cursor = conn.cursor()

            filters = [
                "e.school_year_id = %s",
                "(s.matricule ILIKE %s OR s.last_name ILIKE %s OR s.first_name ILIKE %s)",
            ]
            params = [school_year_id, search, search, search]

            if status_mode == "ACTIVE":
                filters.append("s.is_active = TRUE")
            elif status_mode == "INACTIVE":
                filters.append("s.is_active = FALSE")

            if self.is_global_admin:
                if est_id is not None:
                    filters.append("s.establishment_id = %s")
                    params.append(est_id)
            else:
                filters.append("s.establishment_id = %s")
                params.append(self.current_user["establishment_id"])

            if class_id is not None:
                filters.append("e.class_id = %s")
                params.append(class_id)

            where_sql = " AND ".join(filters)

            cursor.execute(
                f"""
                SELECT
                    s.id,
                    s.matricule,
                    s.last_name,
                    s.first_name,
                    s.gender,
                    c.name AS class_name,
                    est.name AS establishment_name,
                    CASE WHEN s.is_active THEN 'Actif' ELSE 'Inactif' END AS status_label
                FROM students s
                JOIN enrollments e ON e.student_id = s.id
                JOIN classes c ON c.id = e.class_id
                JOIN establishments est ON est.id = s.establishment_id
                WHERE {where_sql}
                ORDER BY s.last_name, s.first_name
                """,
                params,
            )

            students = cursor.fetchall()
            self.table.setRowCount(len(students))

            for row, student in enumerate(students):
                for col, value in enumerate(student):
                    text = "" if value is None else str(value)
                    self.table.setItem(row, col, QTableWidgetItem(text))

            if students:
                self.table.selectRow(0)
            else:
                self.clear_student_details()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
        finally:
            conn.close()

    def clear_student_details(self):
        self.photo_label.setPixmap(QPixmap())
        self.photo_label.setText("Aucune photo")
        for lbl in (
            self.detail_matricule,
            self.detail_last_name,
            self.detail_first_name,
            self.detail_gender,
            self.detail_birth_date,
            self.detail_establishment,
            self.detail_class,
            self.detail_status,
            self.detail_photo_path,
        ):
            lbl.setText("-")

    def load_selected_student_details(self):
        selected = self.table.currentRow()
        if selected < 0:
            self.clear_student_details()
            return

        student_id_item = self.table.item(selected, 0)
        if not student_id_item:
            self.clear_student_details()
            return

        student_id = int(student_id_item.text())

        conn = get_connection()
        if not conn:
            self.clear_student_details()
            return

        try:
            cursor = conn.cursor()

            sql = """
                SELECT
                    s.matricule,
                    s.last_name,
                    s.first_name,
                    s.gender,
                    s.birth_date,
                    est.name AS establishment_name,
                    c.name AS class_name,
                    s.is_active,
                    s.photo_path
                FROM students s
                LEFT JOIN establishments est ON est.id = s.establishment_id
                LEFT JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = %s
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE s.id = %s
            """
            params = [self.school_year_filter.currentData(), student_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user["establishment_id"])

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                self.clear_student_details()
                return

            (
                matricule,
                last_name,
                first_name,
                gender,
                birth_date,
                establishment_name,
                class_name,
                is_active,
                photo_path,
            ) = row

            self.detail_matricule.setText(matricule or "-")
            self.detail_last_name.setText(last_name or "-")
            self.detail_first_name.setText(first_name or "-")
            self.detail_gender.setText(gender or "-")
            self.detail_birth_date.setText(str(birth_date) if birth_date else "-")
            self.detail_establishment.setText(establishment_name or "-")
            self.detail_class.setText(class_name or "-")
            self.detail_status.setText("Actif" if is_active else "Inactif")
            self.detail_photo_path.setText(photo_path or "-")

            if photo_path:
                normalized = photo_path.replace("\\", "/")
                absolute_path = normalized if os.path.isabs(normalized) else os.path.abspath(normalized)
                if os.path.exists(absolute_path):
                    pix = QPixmap(absolute_path)
                    if not pix.isNull():
                        scaled = pix.scaled(
                            self.photo_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.photo_label.setPixmap(scaled)
                        self.photo_label.setText("")
                    else:
                        self.photo_label.setPixmap(QPixmap())
                        self.photo_label.setText("Photo invalide")
                else:
                    self.photo_label.setPixmap(QPixmap())
                    self.photo_label.setText("Photo introuvable")
            else:
                self.photo_label.setPixmap(QPixmap())
                self.photo_label.setText("Aucune photo")

        except Exception:
            self.clear_student_details()
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

        dialog = EditStudentDialog(
            student_id=student_id_item.text(),
            current_user=self.current_user,
            parent=self,
        )

        if dialog.exec():
            self.load_students()

    def set_student_active(self, active: bool):
        selected = self.table.currentRow()

        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un élève")
            return

        student_id_item = self.table.item(selected, 0)
        if not student_id_item:
            QMessageBox.warning(self, "Erreur", "Élève invalide")
            return

        confirm_msg = "réactiver" if active else "désactiver"
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment {confirm_msg} cet élève ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            if self.is_global_admin:
                cursor.execute(
                    """
                    UPDATE students
                    SET is_active = %s
                    WHERE id = %s
                    """,
                    (active, student_id_item.text()),
                )
            else:
                cursor.execute(
                    """
                    UPDATE students
                    SET is_active = %s
                    WHERE id = %s AND establishment_id = %s
                    """,
                    (active, student_id_item.text(), self.current_user["establishment_id"]),
                )
            conn.commit()
            self.load_students()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erreur", f"Mise à jour impossible : {e}")
        finally:
            conn.close()

    def open_add_dialog(self):
        dialog = AddStudentDialog(current_user=self.current_user, parent=self)
        if dialog.exec():
            self.load_students()

    def open_details_dialog(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un élève")
            return

        student_id_item = self.table.item(selected, 0)
        if not student_id_item:
            QMessageBox.warning(self, "Erreur", "Élève invalide")
            return

        dialog = StudentDetailsDialog(
            student_id=int(student_id_item.text()),
            current_user=self.current_user,
            parent=self,
        )
        dialog.exec()
