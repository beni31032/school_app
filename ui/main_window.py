# main_window.py


from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QLabel, QStackedWidget, QScrollArea, QFrame
)

from ui.dashboard.dashboard_page import DashboardPage
from ui.students.students_page import StudentsPage
from ui.teachers.teachers_page import TeachersPage
from ui.staff.staff_page import StaffPage
from ui.classes.classes_page import ClassesPage
from ui.subjects.subjects_page import SubjectsPage
from ui.class_subjects.class_subjects_page import ClassSubjectsPage
from ui.teacher_assignments.teacher_assignments_page import TeacherAssignmentsPage
from ui.timetables.timetables_page import TimetablesPage
from ui.lists.lists_page import ListsPage
from ui.statistics.statistics_page import StatisticsPage
from ui.grades.grades_page import GradesPage
from ui.fees.fees_page import FeesPage
from ui.cycle_fees.cycle_fee_configs_page import CycleFeeConfigsPage
from ui.class_fees.class_fees_page import ClassFeesPage
from ui.payments.payments_page import PaymentsPage
from ui.finance.student_finance_page import StudentFinancePage
from ui.finance.discounts_page import DiscountsPage
from ui.finance.expenses_page import ExpensesPage
from ui.finance.salaries_page import SalariesPage
from ui.finance.financial_reports_page import FinancialReportsPage
from ui.grades.primary_grades_page import PrimaryGradesPage
from ui.grades.college_grades_page import CollegeGradesPage
from ui.grades.lycee_grades_page import LyceeGradesPage
from ui.bulletins.primary_bulletins_page import PrimaryBulletinsPage
from ui.bulletins.college_bulletins_page import CollegeBulletinsPage
from ui.bulletins.lycee_bulletins_page import LyceeBulletinsPage
from ui.settings.settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user
        self.menu_buttons = []
        self.section_toggles = {}
        self.section_contents = {}
        self.button_sections = {}
        self.section_colors = {
            "Vue générale": "#93c5fd",
            "Administration": "#86efac",
            "Suivi et analyses": "#fcd34d",
            "Finance": "#fca5a5",
            "Pédagogie": "#c4b5fd",
            "Rapports": "#67e8f9",
        }

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

            QPushButton#sectionToggle {
                background-color: transparent;
                border: none;
                padding: 8px 10px 4px 10px;
                text-align: left;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 800;
            }

            QPushButton#sectionToggle:hover {
                background-color: #172033;
            }

            QWidget#sectionContent {
                background-color: transparent;
            }

            QFrame#sectionDivider {
                background-color: #1f2937;
                min-height: 1px;
                max-height: 1px;
                border: none;
                margin: 0 8px 4px 8px;
            }

            QFrame#footerDivider {
                background-color: #1f2937;
                min-height: 1px;
                max-height: 1px;
                border: none;
                margin: 6px 10px;
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

            QPushButton#footerButton {
                background-color: transparent;
                color: #cbd5e1;
                border: 1px solid #243041;
                padding: 10px 14px;
                text-align: left;
                border-radius: 10px;
                font-size: 13px;
                margin: 6px 10px 10px 10px;
            }

            QPushButton#footerButton:hover {
                background-color: #172033;
                border: 1px solid #334155;
                color: white;
            }

            QLabel {
                color: white;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QScrollArea > QWidget > QWidget {
                background: transparent;
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
        self.menu_widget.setFixedWidth(280)

        menu_wrapper_layout = QVBoxLayout()
        menu_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        menu_wrapper_layout.setSpacing(0)

        self.menu_scroll = QScrollArea()
        self.menu_scroll.setWidgetResizable(True)
        self.menu_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.menu_content = QWidget()
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
        self.staff_btn = self.create_menu_button("Employés", "👷")
        self.classes_btn = self.create_menu_button("Classes", "🏫")
        self.subjects_btn = self.create_menu_button("Matières", "📚")
        self.class_subjects_btn = self.create_menu_button("Matières par classe", "📘")
        self.teacher_assignments_btn = self.create_menu_button("Affectations", "🧑‍💼")
        self.timetables_btn = self.create_menu_button("Emplois du temps", "🗓️")
        self.lists_btn = self.create_menu_button("Listes", "📋")
        self.statistics_btn = self.create_menu_button("Statistiques", "📈")
        self.fees_btn = self.create_menu_button("Types de frais", "💰")
        self.cycle_fees_btn = self.create_menu_button("Tarifs par cycle", "🧮")
        self.class_fees_btn = self.create_menu_button("Frais par classe", "💳")
        self.discounts_btn = self.create_menu_button("Réductions", "🏷️")
        self.expenses_btn = self.create_menu_button("Dépenses", "🧾")
        self.salaries_btn = self.create_menu_button("Salaires", "💼")
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

        self.add_section(menu_layout, "Vue générale", [self.dashboard_btn], expanded=True)
        self.add_section(
            menu_layout,
            "Administration",
            [
                self.students_btn,
                self.teachers_btn,
                self.staff_btn,
                self.classes_btn,
                self.subjects_btn,
                self.class_subjects_btn,
                self.teacher_assignments_btn,
                self.timetables_btn,
            ],
            expanded=False,
        )
        self.add_section(
            menu_layout,
            "Suivi et analyses",
            [self.lists_btn, self.statistics_btn],
            expanded=False,
        )
        self.add_section(
            menu_layout,
            "Finance",
            [
                self.fees_btn,
                self.cycle_fees_btn,
                self.class_fees_btn,
                self.discounts_btn,
                self.expenses_btn,
                self.salaries_btn,
                self.payments_btn,
                self.finance_btn,
            ],
            expanded=False,
        )
        self.add_section(
            menu_layout,
            "Pédagogie",
            [
                self.grades_btn,
                self.grades_submenu,
                self.bulletins_btn,
                self.bulletins_submenu,
            ],
            expanded=False,
        )
        self.add_section(
            menu_layout,
            "Rapports",
            [self.financial_reports_btn],
            expanded=False,
        )
        menu_layout.addStretch()

        self.menu_content.setLayout(menu_layout)
        self.menu_scroll.setWidget(self.menu_content)
        menu_wrapper_layout.addWidget(self.menu_scroll)

        self.footer_divider = QFrame()
        self.footer_divider.setObjectName("footerDivider")
        self.settings_btn = QPushButton("⚙  Paramètres")
        self.settings_btn.setObjectName("footerButton")
        self.settings_btn.setCheckable(True)
        self.menu_buttons.append(self.settings_btn)

        menu_wrapper_layout.addWidget(self.footer_divider)
        menu_wrapper_layout.addWidget(self.settings_btn)
        self.menu_widget.setLayout(menu_wrapper_layout)

        # =========================
        # PAGES
        # =========================
        self.stack = QStackedWidget()

        self.page_home = DashboardPage(current_user=self.current_user)
        self.page_students = StudentsPage(current_user=self.current_user)
        self.page_teachers = TeachersPage(current_user=self.current_user)
        self.page_staff = StaffPage(current_user=self.current_user)
        self.page_classes = ClassesPage(current_user=self.current_user)
        self.page_subjects = SubjectsPage(current_user=self.current_user)
        self.page_class_subjects = ClassSubjectsPage(current_user=self.current_user)
        self.page_teacher_assignments = TeacherAssignmentsPage(current_user=self.current_user)
        self.page_timetables = TimetablesPage(current_user=self.current_user)
        self.page_lists = ListsPage(current_user=self.current_user)
        self.page_statistics = StatisticsPage(current_user=self.current_user)
        self.page_grades = GradesPage(current_user=self.current_user)
        self.page_fees = FeesPage(current_user=self.current_user)
        self.page_cycle_fees = CycleFeeConfigsPage(current_user=self.current_user)
        self.page_class_fees = ClassFeesPage(current_user=self.current_user)
        self.page_payments = PaymentsPage(current_user=self.current_user)
        self.page_student_finance = StudentFinancePage(current_user=self.current_user)
        self.page_discounts = DiscountsPage(self.current_user)
        self.page_expenses = ExpensesPage(self.current_user)
        self.page_salaries = SalariesPage(self.current_user)
        self.page_financial_reports = FinancialReportsPage(self.current_user)
        self.page_settings = SettingsPage(self.current_user)
        
        #Grades
        self.page_primary_grades = PrimaryGradesPage(current_user=self.current_user)
        self.page_college_grades = CollegeGradesPage(current_user=self.current_user)
        self.page_lycee_grades = LyceeGradesPage(current_user=self.current_user)
        #Bulletins
        self.page_primary_bulletins = PrimaryBulletinsPage(current_user=self.current_user)
        self.page_college_bulletins = CollegeBulletinsPage(current_user=self.current_user)
        self.page_lycee_bulletins = LyceeBulletinsPage(current_user=self.current_user)

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_students)
        self.stack.addWidget(self.page_teachers)
        self.stack.addWidget(self.page_staff)
        self.stack.addWidget(self.page_classes)
        self.stack.addWidget(self.page_subjects)
        self.stack.addWidget(self.page_class_subjects)
        self.stack.addWidget(self.page_teacher_assignments)
        self.stack.addWidget(self.page_timetables)
        self.stack.addWidget(self.page_lists)
        self.stack.addWidget(self.page_statistics)
        self.stack.addWidget(self.page_fees)
        self.stack.addWidget(self.page_cycle_fees)
        self.stack.addWidget(self.page_class_fees)
        self.stack.addWidget(self.page_discounts)
        self.stack.addWidget(self.page_expenses)
        self.stack.addWidget(self.page_salaries)
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
        self.stack.addWidget(self.page_settings)

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
        self.staff_btn.clicked.connect(
            lambda: self.switch_page(self.staff_btn, self.page_staff)
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
        self.timetables_btn.clicked.connect(
            lambda: self.switch_page(self.timetables_btn, self.page_timetables)
        )
        self.lists_btn.clicked.connect(
            lambda: self.switch_page(self.lists_btn, self.page_lists)
        )
        self.statistics_btn.clicked.connect(
            lambda: self.switch_page(self.statistics_btn, self.page_statistics)
        )
        self.fees_btn.clicked.connect(
            lambda: self.switch_page(self.fees_btn, self.page_fees)
        )
        self.cycle_fees_btn.clicked.connect(
            lambda: self.switch_page(self.cycle_fees_btn, self.page_cycle_fees)
        )
        self.class_fees_btn.clicked.connect(
            lambda: self.switch_page(self.class_fees_btn, self.page_class_fees)
        )
        self.discounts_btn.clicked.connect(
            lambda: self.switch_page(self.discounts_btn, self.page_discounts)
        )
        self.expenses_btn.clicked.connect(
            lambda: self.switch_page(self.expenses_btn, self.page_expenses)
        )
        self.salaries_btn.clicked.connect(
            lambda: self.switch_page(self.salaries_btn, self.page_salaries)
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
        self.settings_btn.clicked.connect(
            lambda: self.switch_page(self.settings_btn, self.page_settings)
        )
        
        # Page par défaut
        self.switch_page(self.dashboard_btn, self.page_home)

    def create_menu_button(self, text, icon):
        btn = QPushButton(f"{icon}  {text}")
        btn.setCheckable(True)
        self.menu_buttons.append(btn)
        return btn

    def add_section(self, parent_layout, title, widgets, expanded=True):
        toggle_btn = QPushButton()
        toggle_btn.setObjectName("sectionToggle")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(expanded)

        content = QWidget()
        content.setObjectName("sectionContent")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        for widget in widgets:
            content_layout.addWidget(widget)
            if widget in self.menu_buttons:
                self.button_sections[widget] = title

        content.setLayout(content_layout)
        content.setVisible(expanded)

        self.section_toggles[title] = toggle_btn
        self.section_contents[title] = content
        self.update_section_toggle_text(title)
        toggle_btn.clicked.connect(lambda checked=False, section=title: self.toggle_section(section))

        parent_layout.addWidget(toggle_btn)
        parent_layout.addWidget(content)

    def update_section_toggle_text(self, title):
        is_open = self.section_contents[title].isVisible()
        arrow = "▾" if is_open else "▸"
        self.section_toggles[title].setText(f"{arrow}  {title.upper()}")
        color = self.section_colors.get(title, "#93c5fd")
        bg = color + "22" if is_open else "transparent"
        border = color + "44" if is_open else "transparent"
        self.section_toggles[title].setStyleSheet(f"""
            QPushButton#sectionToggle {{
                background-color: {bg};
                color: {color};
                border: 1px solid {border};
                padding: 8px 10px 4px 10px;
                text-align: left;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 800;
            }}
            QPushButton#sectionToggle:hover {{
                background-color: #172033;
            }}
        """)

    def set_active_button(self, active_button):
        for btn in self.menu_buttons:
            btn.setChecked(False)
        active_button.setChecked(True)

    def switch_page(self, button, page):
        section = self.button_sections.get(button)
        if section:
            self.expand_only_section(section)
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

    def toggle_section(self, title):
        is_visible = self.section_contents[title].isVisible()
        if is_visible:
            self.section_contents[title].setVisible(False)
            self.section_toggles[title].setChecked(False)
            self.update_section_toggle_text(title)
            return
        self.expand_only_section(title)

    def expand_only_section(self, active_title):
        for title, content in self.section_contents.items():
            is_active = title == active_title
            content.setVisible(is_active)
            self.section_toggles[title].setChecked(is_active)
            self.update_section_toggle_text(title)
