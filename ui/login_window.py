from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox
)

from ui.main_window import MainWindow
from database.connection import get_connection

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

        username = self.username_input.text()
        password = self.password_input.text()

        conn = get_connection()

        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible")
            return

        cursor = conn.cursor()

        query = """
        SELECT id, role
        FROM users
        WHERE username=%s AND password_hash=%s
        """

        cursor.execute(query, (username, password))

        user = cursor.fetchone()

        conn.close()

        if user:
            self.main_window = MainWindow()
            self.main_window.show()

            self.close()
        else:
            QMessageBox.warning(self, "Erreur", "Identifiants incorrects")