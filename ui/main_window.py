from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QLabel, QStackedWidget
)

from ui.dashboard.dashboard_page import DashboardPage
from ui.students.students_page import StudentsPage
from ui.teachers.teachers_page import TeachersPage
from ui.classes.classes_page import ClassesPage
from ui.subjects.subjects_page import SubjectsPage
from ui.class_subjects.class_subjects_page import ClassSubjectsPage
from ui.teacher_assignments.teacher_assignments_page import TeacherAssignmentsPage
from ui.grades.grades_page import GradesPage
from ui.fees.fees_page import FeesPage
from ui.class_fees.class_fees_page import ClassFeesPage
from ui.payments.payments_page import PaymentsPage
from ui.finance.student_finance_page import StudentFinancePage
from ui.finance.discounts_page import DiscountsPage
from ui.finance.financial_reports_page import FinancialReportsPage
from ui.grades.primary_grades_page import PrimaryGradesPage
from ui.bulletins.primary_bulletins_page import PrimaryBulletinsPage


class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.menu_buttons = []

        self.setWindowTitle("Système de Gestion Scolaire")
        self.resize(1200, 750)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f1f5f9;
            }

            QWidget#sidebar {
                background-color: #111827;
                border-right: 1px solid #1f2937;
            }

            QLabel#userLabel {
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                border-bottom: 1px solid #1f2937;
                margin-bottom: 10px;
            }

            QPushButton {
                background-color: transparent;
                color: darkgray;
                border: none;
                padding: 10px 14px;
                text-align: left;
                border-radius: 8px;
                font-size: 13px;
            }

            QPushButton:hover {
                background-color: #1f2937;
            }

            QPushButton:checked {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
            }

            QPushButton:pressed {
                background-color: #1d4ed8;
            }

            QLabel {
                color: white;
            }

            QStackedWidget {
                background-color: #f1f5f9;
            }
            
            QTableWidget {
                background-color: white;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                gridline-color: #e5e7eb;
                alternate-background-color: #f8fafc;
                selection-background-color: #dbeafe;
                selection-color: #111827;
                font-size: 13px;
            }

            QTableWidget::item {
                color: #111827;
                padding: 6px;
            }

            QHeaderView::section {
                background-color: #2563eb;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
           
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =========================
        # SIDEBAR
        # =========================
        self.menu_widget = QWidget()
        self.menu_widget.setObjectName("sidebar")
        self.menu_widget.setFixedWidth(240)

        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(10, 12, 10, 12)
        menu_layout.setSpacing(6)

        self.user_label = QLabel(
        f"👤 {self.current_user['username']}\n{self.current_user['role']}"
        )
        self.user_label.setObjectName("userLabel")

        self.dashboard_btn = self.create_menu_button("Dashboard", "🏠")
        self.students_btn = self.create_menu_button("Élèves", "🎓")
        self.teachers_btn = self.create_menu_button("Enseignants", "👨‍🏫")
        self.classes_btn = self.create_menu_button("Classes", "🏫")
        self.subjects_btn = self.create_menu_button("Matières", "📚")
        self.class_subjects_btn = self.create_menu_button("Matières par classe", "📘")
        self.teacher_assignments_btn = self.create_menu_button("Affectations", "🧑‍💼")
        self.fees_btn = self.create_menu_button("Types de frais", "💰")
        self.class_fees_btn = self.create_menu_button("Frais par classe", "💳")
        self.discounts_btn = self.create_menu_button("Réductions", "🏷️")
        self.payments_btn = self.create_menu_button("Paiements", "💵")
        self.finance_btn = self.create_menu_button("Situation élève", "📊")
        # Grades menu with submenu
        self.grades_btn = self.create_menu_button("Notes", "📝")
        self.grades_submenu = QWidget()
        self.grades_submenu_layout = QVBoxLayout()
        self.grades_submenu_layout.setContentsMargins(20, 0, 0, 0)
        self.grades_submenu_layout.setSpacing(4)
        self.primary_grades_btn = self.create_submenu_button("Primaire")
        self.college_grades_btn = self.create_submenu_button("Collège")
        self.lycee_grades_btn = self.create_submenu_button("Lycée")
        self.grades_submenu_layout.addWidget(self.primary_grades_btn)
        self.grades_submenu_layout.addWidget(self.college_grades_btn)
        self.grades_submenu_layout.addWidget(self.lycee_grades_btn)
        self.grades_submenu.setLayout(self.grades_submenu_layout)
        self.grades_submenu.setVisible(False)
        # Bulletins menu with submenu
        self.bulletins_btn = self.create_menu_button("Bulletins", "📄")
        self.bulletins_submenu = QWidget()
        self.bulletins_submenu_layout = QVBoxLayout()
        self.bulletins_submenu_layout.setContentsMargins(20, 0, 0, 0)
        self.bulletins_submenu_layout.setSpacing(4)
        self.primary_bulletins_btn = self.create_submenu_button("Primaire")
        self.college_bulletins_btn = self.create_submenu_button("Collège")
        self.lycee_bulletins_btn = self.create_submenu_button("Lycée")
        self.bulletins_submenu_layout.addWidget(self.primary_bulletins_btn)
        self.bulletins_submenu_layout.addWidget(self.college_bulletins_btn)
        self.bulletins_submenu_layout.addWidget(self.lycee_bulletins_btn)
        self.bulletins_submenu.setLayout(self.bulletins_submenu_layout)
        self.bulletins_submenu.setVisible(False)
        # Financial reports menu
        self.financial_reports_btn = self.create_menu_button("Rapports", "📈")

        menu_layout.addWidget(self.user_label)
        menu_layout.addWidget(self.dashboard_btn)
        menu_layout.addWidget(self.students_btn)
        menu_layout.addWidget(self.teachers_btn)
        menu_layout.addWidget(self.classes_btn)
        menu_layout.addWidget(self.subjects_btn)
        menu_layout.addWidget(self.class_subjects_btn)
        menu_layout.addWidget(self.teacher_assignments_btn)
        menu_layout.addWidget(self.fees_btn)
        menu_layout.addWidget(self.class_fees_btn)
        menu_layout.addWidget(self.discounts_btn)
        menu_layout.addWidget(self.payments_btn)
        menu_layout.addWidget(self.finance_btn)
        menu_layout.addWidget(self.grades_btn)
        menu_layout.addWidget(self.grades_submenu)
        menu_layout.addWidget(self.bulletins_btn)
        menu_layout.addWidget(self.bulletins_submenu)
        menu_layout.addWidget(self.financial_reports_btn)
        menu_layout.addStretch()

        self.menu_widget.setLayout(menu_layout)

        # =========================
        # PAGES
        # =========================
        self.stack = QStackedWidget()

        self.page_home = DashboardPage(current_user=self.current_user)
        self.page_students = StudentsPage(current_user=self.current_user)
        self.page_teachers = TeachersPage(current_user=self.current_user)
        self.page_classes = ClassesPage(current_user=self.current_user)
        self.page_subjects = SubjectsPage(current_user=self.current_user)
        self.page_class_subjects = ClassSubjectsPage(current_user=self.current_user)
        self.page_teacher_assignments = TeacherAssignmentsPage(current_user=self.current_user)
        self.page_grades = GradesPage(current_user=self.current_user)
        self.page_fees = FeesPage(current_user=self.current_user)
        self.page_class_fees = ClassFeesPage(current_user=self.current_user)
        self.page_payments = PaymentsPage(current_user=self.current_user)
        self.page_student_finance = StudentFinancePage(current_user=self.current_user)
        self.page_discounts = DiscountsPage(self.current_user)
        self.page_financial_reports = FinancialReportsPage(self.current_user)
        
        #Grades
        self.page_primary_grades = PrimaryGradesPage(current_user=self.current_user)
        self.page_college_grades = QLabel("Le module Notes Collège sera ajouté ensuite.")
        self.page_college_grades.setStyleSheet("font-size: 16px; padding: 20px;")
        self.page_lycee_grades = QLabel("Le module Notes Lycée sera ajouté ensuite.")
        self.page_lycee_grades.setStyleSheet("font-size: 16px; padding: 20px;")
        #Bulletins
        self.page_primary_bulletins = PrimaryBulletinsPage(current_user=self.current_user)
        self.page_college_bulletins = QLabel("Le module Bulletins Collège sera ajouté ensuite.")
        self.page_college_bulletins.setStyleSheet("font-size: 16px; padding: 20px;")
        self.page_lycee_bulletins = QLabel("Le module Bulletins Lycée sera ajouté ensuite.")
        self.page_lycee_bulletins.setStyleSheet("font-size: 16px; padding: 20px;")

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_students)
        self.stack.addWidget(self.page_teachers)
        self.stack.addWidget(self.page_classes)
        self.stack.addWidget(self.page_subjects)
        self.stack.addWidget(self.page_class_subjects)
        self.stack.addWidget(self.page_teacher_assignments)
        self.stack.addWidget(self.page_fees)
        self.stack.addWidget(self.page_class_fees)
        self.stack.addWidget(self.page_discounts)
        self.stack.addWidget(self.page_payments)
        self.stack.addWidget(self.page_student_finance)
        self.stack.addWidget(self.page_grades)
        self.stack.addWidget(self.page_primary_bulletins)
        self.stack.addWidget(self.page_college_bulletins)
        self.stack.addWidget(self.page_lycee_bulletins)
        self.stack.addWidget(self.page_financial_reports)
        self.stack.addWidget(self.page_primary_grades)
        self.stack.addWidget(self.page_college_grades)
        self.stack.addWidget(self.page_lycee_grades)

        main_layout.addWidget(self.menu_widget)
        main_layout.addWidget(self.stack)

        main_widget.setLayout(main_layout)

        # =========================
        # CONNECTIONS
        # =========================
        self.dashboard_btn.clicked.connect(
            lambda: self.switch_page(self.dashboard_btn, self.page_home)
        )
        self.students_btn.clicked.connect(
            lambda: self.switch_page(self.students_btn, self.page_students)
        )
        self.teachers_btn.clicked.connect(
            lambda: self.switch_page(self.teachers_btn, self.page_teachers)
        )
        self.classes_btn.clicked.connect(
            lambda: self.switch_page(self.classes_btn, self.page_classes)
        )
        self.subjects_btn.clicked.connect(
            lambda: self.switch_page(self.subjects_btn, self.page_subjects)
        )
        self.class_subjects_btn.clicked.connect(
            lambda: self.switch_page(self.class_subjects_btn, self.page_class_subjects)
        )
        self.teacher_assignments_btn.clicked.connect(
            lambda: self.switch_page(self.teacher_assignments_btn, self.page_teacher_assignments)
        )
        self.fees_btn.clicked.connect(
            lambda: self.switch_page(self.fees_btn, self.page_fees)
        )
        self.class_fees_btn.clicked.connect(
            lambda: self.switch_page(self.class_fees_btn, self.page_class_fees)
        )
        self.discounts_btn.clicked.connect(
            lambda: self.switch_page(self.discounts_btn, self.page_discounts)
        )
        self.payments_btn.clicked.connect(
            lambda: self.switch_page(self.payments_btn, self.page_payments)
        )
        self.finance_btn.clicked.connect(
            lambda: self.switch_page(self.finance_btn, self.page_student_finance)
        )
        self.grades_btn.clicked.connect(
            self.toggle_grades_submenu
        )
        self.financial_reports_btn.clicked.connect(
            lambda: self.switch_page(self.financial_reports_btn, self.page_financial_reports)
        )
        self.primary_grades_btn.clicked.connect(
            lambda: self.switch_page(self.primary_grades_btn, self.page_primary_grades)
        )
        self.college_grades_btn.clicked.connect(
            lambda: self.switch_page(self.college_grades_btn, self.page_college_grades)
        )
        self.lycee_grades_btn.clicked.connect(
            lambda: self.switch_page(self.lycee_grades_btn, self.page_lycee_grades)
        )
        self.bulletins_btn.clicked.connect(
            self.toggle_bulletins_submenu
        )
        self.primary_bulletins_btn.clicked.connect(
            lambda: self.switch_page(self.primary_bulletins_btn, self.page_primary_bulletins)
        )
        self.college_bulletins_btn.clicked.connect(
            lambda: self.switch_page(self.college_bulletins_btn, self.page_college_bulletins)
        )
        self.lycee_bulletins_btn.clicked.connect(
            lambda: self.switch_page(self.lycee_bulletins_btn, self.page_lycee_bulletins)
        )
        
        # Page par défaut
        self.switch_page(self.dashboard_btn, self.page_home)

    def create_menu_button(self, text, icon):
        btn = QPushButton(f"{icon}  {text}")
        btn.setCheckable(True)
        self.menu_buttons.append(btn)
        return btn

    def set_active_button(self, active_button):
        for btn in self.menu_buttons:
            btn.setChecked(False)
        active_button.setChecked(True)

    def switch_page(self, button, page):
        self.set_active_button(button)
        self.stack.setCurrentWidget(page)
        
    def create_submenu_button(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cbd5e1;
                border: none;
                padding: 8px 12px;
                text-align: left;
                border-radius: 6px;
                font-size: 12px;
            }

            QPushButton:hover {
                background-color: #1f2937;
            }

            QPushButton:checked {
                background-color: #1d4ed8;
                color: white;
                font-weight: bold;
            }
        """)
        self.menu_buttons.append(btn)
        return btn
    
    def toggle_grades_submenu(self):
        is_visible = self.grades_submenu.isVisible()
        self.grades_submenu.setVisible(not is_visible)
        
    def toggle_bulletins_submenu(self):
        is_visible = self.bulletins_submenu.isVisible()
        self.bulletins_submenu.setVisible(not is_visible)