import sys
from PyQt6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from database.connection import get_connection

conn = get_connection()

if conn:
    print("Connexion à la base réussie")
    conn.close()
else:
    print("Connexion échouée")


app = QApplication(sys.argv)

window = LoginWindow()
window.show()

sys.exit(app.exec())