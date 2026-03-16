from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QLabel, QStackedWidget
)

from ui.students.students_page import StudentsPage
from ui.teachers.teachers_page import TeachersPage
from ui.subjects.subjects_page import SubjectsPage
from ui.class_subjects.class_subjects_page import ClassSubjectsPage
from ui.teacher_assignments.teacher_assignments_page import TeacherAssignmentsPage
from ui.classes.classes_page import ClassesPage
from ui.grades.grades_page import GradesPage
from ui.fees.fees_page import FeesPage
from ui.class_fees.class_fees_page import ClassFeesPage
from ui.payments.payments_page import PaymentsPage
from ui.finance.student_finance_page import StudentFinancePage


class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        self.setWindowTitle("Système de Gestion Scolaire")
        self.resize(1000, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()

        menu_layout = QVBoxLayout()

        self.user_label = QLabel(
            f"Connecté : {self.current_user['username']} ({self.current_user['role']})"
        )

        self.students_btn = QPushButton("Élèves")
        self.teachers_btn = QPushButton("Enseignants")
        self.classes_btn = QPushButton("Classes")
        self.subjects_btn = QPushButton("Matières")
        self.class_subjects_btn = QPushButton("Matières par classe")
        self.teacher_assignments_btn = QPushButton("Affectations enseignants")
        self.fees_btn = QPushButton("Types de frais")
        self.class_fees_btn = QPushButton("Frais par classe")
        self.payments_btn = QPushButton("Paiements")
        self.grades_btn = QPushButton("Notes")
        self.reports_btn = QPushButton("Bulletins")
        self.finance_btn = QPushButton("Situation élève")

        

        menu_layout.addWidget(self.user_label)
        menu_layout.addWidget(self.students_btn)
        menu_layout.addWidget(self.teachers_btn)
        menu_layout.addWidget(self.classes_btn)
        menu_layout.addWidget(self.subjects_btn)
        menu_layout.addWidget(self.class_subjects_btn)
        menu_layout.addWidget(self.teacher_assignments_btn)
        menu_layout.addWidget(self.fees_btn)
        menu_layout.addWidget(self.class_fees_btn)
        menu_layout.addWidget(self.payments_btn)
        menu_layout.addWidget(self.finance_btn)
        menu_layout.addWidget(self.grades_btn)
        menu_layout.addWidget(self.reports_btn)
        
        menu_layout.addStretch()

        self.stack = QStackedWidget()

        self.page_home = QLabel("Tableau de bord")
        self.page_students = StudentsPage(current_user=self.current_user)
        self.page_teachers = TeachersPage(current_user=self.current_user)
        self.page_subjects = SubjectsPage(current_user=self.current_user)
        self.page_class_subjects = ClassSubjectsPage(current_user=self.current_user)
        self.page_teacher_assignments = TeacherAssignmentsPage(current_user=self.current_user)
        self.page_classes = ClassesPage(current_user=self.current_user)
        self.page_grades = GradesPage(current_user=self.current_user)
        self.page_fees = FeesPage(current_user=self.current_user)
        self.page_class_fees = ClassFeesPage(current_user=self.current_user)
        self.page_payments = PaymentsPage(current_user=self.current_user)
        self.page_student_finance = StudentFinancePage(current_user=self.current_user)
        
        
        
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_students)
        self.stack.addWidget(self.page_classes)
        self.stack.addWidget(self.page_teachers)
        self.stack.addWidget(self.page_subjects)
        self.stack.addWidget(self.page_class_subjects)
        self.stack.addWidget(self.page_teacher_assignments)
        self.stack.addWidget(self.page_grades)
        self.stack.addWidget(self.page_fees)
        self.stack.addWidget(self.page_class_fees)
        self.stack.addWidget(self.page_payments)
        self.stack.addWidget(self.page_student_finance)

        main_layout.addLayout(menu_layout)
        main_layout.addWidget(self.stack)

        main_widget.setLayout(main_layout)

        self.students_btn.clicked.connect(self.show_students)
        self.teachers_btn.clicked.connect(self.show_teachers)
        self.subjects_btn.clicked.connect(self.show_subjects)
        self.class_subjects_btn.clicked.connect(self.show_class_subjects)
        self.teacher_assignments_btn.clicked.connect(self.show_teacher_assignments)
        self.classes_btn.clicked.connect(self.show_classes)
        self.grades_btn.clicked.connect(self.show_grades)
        self.fees_btn.clicked.connect(self.show_fees)
        self.class_fees_btn.clicked.connect(self.show_class_fees)
        self.payments_btn.clicked.connect(self.show_payments)
        self.finance_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.page_student_finance)
        )
                

    def show_students(self):
        self.stack.setCurrentWidget(self.page_students)

    def show_teachers(self):
        self.stack.setCurrentWidget(self.page_teachers)
        
    def show_subjects(self):
        self.stack.setCurrentWidget(self.page_subjects)
        
    def show_class_subjects(self):
        self.stack.setCurrentWidget(self.page_class_subjects)
        
    def show_teacher_assignments(self):
        self.stack.setCurrentWidget(self.page_teacher_assignments)
        
    def show_classes(self):
        self.stack.setCurrentWidget(self.page_classes)
        
    def show_grades(self):
        self.stack.setCurrentWidget(self.page_grades)
        
    def show_fees(self):
        self.stack.setCurrentWidget(self.page_fees)
        
    def show_class_fees(self):
        self.stack.setCurrentWidget(self.page_class_fees)
        
    def show_payments(self):
        self.stack.setCurrentWidget(self.page_payments)