from ui.students.students_page import StudentsPage
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QLabel, QStackedWidget
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Système de Gestion Scolaire")
        self.resize(1000, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()

        # MENU LATERAL
        menu_layout = QVBoxLayout()

        self.students_btn = QPushButton("Élèves")
        self.teachers_btn = QPushButton("Enseignants")
        self.classes_btn = QPushButton("Classes")
        self.payments_btn = QPushButton("Paiements")
        self.grades_btn = QPushButton("Notes")
        self.reports_btn = QPushButton("Bulletins")

        menu_layout.addWidget(self.students_btn)
        menu_layout.addWidget(self.teachers_btn)
        menu_layout.addWidget(self.classes_btn)
        menu_layout.addWidget(self.payments_btn)
        menu_layout.addWidget(self.grades_btn)
        menu_layout.addWidget(self.reports_btn)
        menu_layout.addStretch()

        # ZONE CONTENU
        self.stack = QStackedWidget()

        self.page_home = QLabel("Tableau de bord")
        self.page_students = StudentsPage()
        self.page_teachers = QLabel("Gestion des enseignants")

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_students)
        self.stack.addWidget(self.page_teachers)

        main_layout.addLayout(menu_layout)
        main_layout.addWidget(self.stack)

        main_widget.setLayout(main_layout)

        # connexions
        self.students_btn.clicked.connect(self.show_students)
        self.teachers_btn.clicked.connect(self.show_teachers)

    def show_students(self):
        self.stack.setCurrentWidget(self.page_students)

    def show_teachers(self):
        self.stack.setCurrentWidget(self.page_teachers)