import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QFormLayout,
    QPushButton,
    QMessageBox,
)

from database.connection import get_connection


class StudentDetailsDialog(QDialog):
    def __init__(self, student_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.student_id = int(student_id)
        self.current_user = current_user
        self.is_global_admin = self.current_user.get("role") == "ADMIN_GLOBAL"

        self.setWindowTitle("Fiche complète élève")
        self.resize(760, 520)

        root = QVBoxLayout()

        title = QLabel("Fiche complète élève")
        title.setObjectName("dialogTitle")

        card = QFrame()
        card.setObjectName("detailsCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(18)

        self.photo_label = QLabel("Aucune photo")
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setFixedSize(210, 260)
        self.photo_label.setObjectName("photoBox")

        info_wrap = QFrame()
        info_layout = QFormLayout(info_wrap)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setVerticalSpacing(8)

        self.v_id = QLabel("-")
        self.v_matricule = QLabel("-")
        self.v_nom = QLabel("-")
        self.v_prenom = QLabel("-")
        self.v_sexe = QLabel("-")
        self.v_birth = QLabel("-")
        self.v_est = QLabel("-")
        self.v_class = QLabel("-")
        self.v_status = QLabel("-")
        self.v_photo_path = QLabel("-")
        self.v_photo_path.setWordWrap(True)
        self.v_photo_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        info_layout.addRow("ID :", self.v_id)
        info_layout.addRow("Matricule :", self.v_matricule)
        info_layout.addRow("Nom :", self.v_nom)
        info_layout.addRow("Prénom :", self.v_prenom)
        info_layout.addRow("Sexe :", self.v_sexe)
        info_layout.addRow("Date naissance :", self.v_birth)
        info_layout.addRow("Établissement :", self.v_est)
        info_layout.addRow("Classe (année en cours) :", self.v_class)
        info_layout.addRow("Statut :", self.v_status)
        info_layout.addRow("Photo :", self.v_photo_path)

        card_layout.addWidget(self.photo_label)
        card_layout.addWidget(info_wrap, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)

        root.addWidget(title)
        root.addWidget(card)
        root.addLayout(actions)
        self.setLayout(root)

        self.apply_local_styles()
        self.load_details()

    def apply_local_styles(self):
        self.setStyleSheet(
            """
            QDialog { background-color: #f1f5f9; }
            QLabel#dialogTitle {
                color: #111827;
                font-size: 22px;
                font-weight: 800;
                margin-bottom: 4px;
            }
            QFrame#detailsCard {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            QLabel {
                color: #111827;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#photoBox {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                color: #6b7280;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            """
        )

    def _clear(self):
        self.v_id.setText("-")
        self.v_matricule.setText("-")
        self.v_nom.setText("-")
        self.v_prenom.setText("-")
        self.v_sexe.setText("-")
        self.v_birth.setText("-")
        self.v_est.setText("-")
        self.v_class.setText("-")
        self.v_status.setText("-")
        self.v_photo_path.setText("-")
        self.photo_label.setPixmap(QPixmap())
        self.photo_label.setText("Aucune photo")

    def load_details(self):
        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            self._clear()
            return

        try:
            cursor = conn.cursor()

            sql = """
                SELECT
                    s.id,
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
                   AND e.school_year_id = (
                       SELECT id
                       FROM school_years
                       ORDER BY id DESC
                       LIMIT 1
                   )
                LEFT JOIN classes c ON c.id = e.class_id
                WHERE s.id = %s
            """
            params = [self.student_id]
            if not self.is_global_admin:
                sql += " AND s.establishment_id = %s"
                params.append(self.current_user.get("establishment_id"))

            cursor.execute(sql, params)
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Erreur", "Élève introuvable.")
                self._clear()
                return

            sid, matricule, nom, prenom, sexe, birth, est_name, class_name, is_active, photo_path = row

            self.v_id.setText(str(sid))
            self.v_matricule.setText(matricule or "-")
            self.v_nom.setText(nom or "-")
            self.v_prenom.setText(prenom or "-")
            self.v_sexe.setText(sexe or "-")
            self.v_birth.setText(str(birth) if birth else "-")
            self.v_est.setText(est_name or "-")
            self.v_class.setText(class_name or "-")
            self.v_status.setText("Actif" if is_active else "Inactif")
            self.v_photo_path.setText(photo_path or "-")

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

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Chargement impossible : {e}")
            self._clear()
        finally:
            conn.close()
