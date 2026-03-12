from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox
)

from database.connection import get_connection
from ui.main_window import MainWindow
from utils.security import verify_password


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Connexion - Gestion Scolaire")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton("Se connecter")
        self.login_button.clicked.connect(self.login)

        layout.addWidget(QLabel("Connexion"))
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Validation", "Veuillez remplir tous les champs.")
            return

        conn = get_connection()
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, password_hash, role, establishment_id
                FROM users
                WHERE username = %s
                """,
                (username,)
            )

            user = cursor.fetchone()

            if not user:
                QMessageBox.warning(self, "Erreur", "Identifiants incorrects")
                return

            user_id, db_username, password_hash, role, establishment_id = user

            if not verify_password(password, password_hash):
                QMessageBox.warning(self, "Erreur", "Identifiants incorrects")
                return

            self.current_user = {
                "id": user_id,
                "username": db_username,
                "role": role,
                "establishment_id": establishment_id
            }

            QMessageBox.information(self, "Succès", "Connexion réussie")

            self.main_window = MainWindow(self.current_user)
            self.main_window.show()
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la connexion : {e}")
        finally:
            conn.close()