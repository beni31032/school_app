from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


random.seed(20260508)

ESTABLISHMENT_NAME = "Etablissement 1"
SCHOOL_YEAR_NAME = "2025-2026"
PRIMARY_FEES = [
    ("Inscription", "Frais d'inscription annuels"),
    ("Scolarité", "Frais de scolarité"),
    ("Tenue", "Frais de tenue scolaire"),
    ("Bibliothèque", "Frais de bibliothèque"),
    ("Examen", "Frais d'examen"),
]


@dataclass(frozen=True)
class TeacherSeed:
    first_name: str
    last_name: str
    phone: str
    email: str
    hire_date: date


@dataclass(frozen=True)
class StaffSeed:
    first_name: str
    last_name: str
    role_title: str
    phone: str
    email: str
    hire_date: date


TEACHERS = [
    TeacherSeed("Mireille", "Akakpo", "90010001", "mireille.akakpo@vp.tg", date(2024, 9, 1)),
    TeacherSeed("Kossi", "Lawson", "90010002", "kossi.lawson@vp.tg", date(2023, 9, 1)),
    TeacherSeed("Ama", "Mensah", "90010003", "ama.mensah@vp.tg", date(2022, 9, 1)),
    TeacherSeed("Koffi", "Adjovi", "90010004", "koffi.adjovi@vp.tg", date(2024, 1, 10)),
    TeacherSeed("Clarisse", "Dossou", "90010005", "clarisse.dossou@vp.tg", date(2023, 3, 15)),
    TeacherSeed("Eric", "Assogba", "90010006", "eric.assogba@vp.tg", date(2021, 10, 1)),
    TeacherSeed("Joelle", "Anani", "90010007", "joelle.anani@vp.tg", date(2020, 9, 1)),
    TeacherSeed("Idriss", "Bamba", "90010008", "idriss.bamba@vp.tg", date(2022, 11, 1)),
    TeacherSeed("Florence", "Sika", "90010009", "florence.sika@vp.tg", date(2024, 9, 1)),
]

STAFF_MEMBERS = [
    StaffSeed("Afi", "Komlan", "Caissière", "91020001", "afi.komlan@vp.tg", date(2023, 9, 1)),
    StaffSeed("Sena", "Tossou", "Surveillant", "91020002", "sena.tossou@vp.tg", date(2024, 2, 1)),
    StaffSeed("Yawovi", "Kponton", "Gardien", "91020003", "yawovi.kponton@vp.tg", date(2022, 7, 1)),
]

CLASSES = [
    {"name": "GS A", "level": "GS", "cycle": "Maternelle", "titular": "Mireille Akakpo"},
    {"name": "CP1 A", "level": "CP1", "cycle": "Primaire", "titular": "Idriss Bamba"},
    {"name": "CM1 A", "level": "CM1", "cycle": "Primaire", "titular": "Florence Sika"},
    {"name": "6ème A", "level": "6ème", "cycle": "Collège", "titular": "Kossi Lawson"},
    {"name": "3ème A", "level": "3ème", "cycle": "Collège", "titular": "Ama Mensah"},
    {"name": "2nde A", "level": "2nde", "cycle": "Lycée", "titular": "Joelle Anani"},
]

SUBJECTS = [
    "Langage",
    "Numération",
    "Motricité",
    "Éveil",
    "Français",
    "Mathématiques",
    "ESVT",
    "Histoire-Géographie",
    "Anglais",
    "EPS",
    "SVT",
    "Physique-Chimie",
    "Informatique",
    "Philosophie",
    "Latin",
    "Allemand",
    "Espagnol",
]

CLASS_SUBJECTS = {
    "GS A": [
        ("Langage", 1, "OBLIGATOIRE"),
        ("Numération", 1, "OBLIGATOIRE"),
        ("Motricité", 1, "OBLIGATOIRE"),
        ("Éveil", 1, "OBLIGATOIRE"),
    ],
    "CP1 A": [
        ("Français", 3, "OBLIGATOIRE"),
        ("Mathématiques", 3, "OBLIGATOIRE"),
        ("ESVT", 2, "OBLIGATOIRE"),
        ("Histoire-Géographie", 2, "OBLIGATOIRE"),
        ("EPS", 1, "OBLIGATOIRE"),
    ],
    "CM1 A": [
        ("Français", 3, "OBLIGATOIRE"),
        ("Mathématiques", 3, "OBLIGATOIRE"),
        ("ESVT", 2, "OBLIGATOIRE"),
        ("Histoire-Géographie", 2, "OBLIGATOIRE"),
        ("Anglais", 2, "OBLIGATOIRE"),
        ("EPS", 1, "OBLIGATOIRE"),
    ],
    "6ème A": [
        ("Français", 4, "OBLIGATOIRE"),
        ("Mathématiques", 4, "OBLIGATOIRE"),
        ("Anglais", 2, "OBLIGATOIRE"),
        ("Histoire-Géographie", 2, "OBLIGATOIRE"),
        ("SVT", 2, "OBLIGATOIRE"),
        ("EPS", 1, "OBLIGATOIRE"),
        ("Informatique", 1, "OBLIGATOIRE"),
        ("Latin", 1, "FACULTATIVE"),
    ],
    "3ème A": [
        ("Français", 4, "OBLIGATOIRE"),
        ("Mathématiques", 4, "OBLIGATOIRE"),
        ("Anglais", 2, "OBLIGATOIRE"),
        ("Histoire-Géographie", 2, "OBLIGATOIRE"),
        ("SVT", 2, "OBLIGATOIRE"),
        ("Physique-Chimie", 2, "OBLIGATOIRE"),
        ("EPS", 1, "OBLIGATOIRE"),
        ("Allemand", 1, "FACULTATIVE"),
        ("Espagnol", 1, "FACULTATIVE"),
    ],
    "2nde A": [
        ("Français", 4, "OBLIGATOIRE"),
        ("Mathématiques", 4, "OBLIGATOIRE"),
        ("Anglais", 2, "OBLIGATOIRE"),
        ("Histoire-Géographie", 2, "OBLIGATOIRE"),
        ("SVT", 2, "OBLIGATOIRE"),
        ("Physique-Chimie", 2, "OBLIGATOIRE"),
        ("Philosophie", 2, "OBLIGATOIRE"),
        ("Informatique", 1, "OBLIGATOIRE"),
        ("Allemand", 1, "FACULTATIVE"),
        ("Espagnol", 1, "FACULTATIVE"),
    ],
}

SUBJECT_TEACHER = {
    "Langage": "Mireille Akakpo",
    "Numération": "Mireille Akakpo",
    "Motricité": "Florence Sika",
    "Éveil": "Mireille Akakpo",
    "Français": "Kossi Lawson",
    "Mathématiques": "Ama Mensah",
    "ESVT": "Idriss Bamba",
    "Histoire-Géographie": "Idriss Bamba",
    "Anglais": "Koffi Adjovi",
    "EPS": "Clarisse Dossou",
    "SVT": "Florence Sika",
    "Physique-Chimie": "Ama Mensah",
    "Informatique": "Eric Assogba",
    "Philosophie": "Joelle Anani",
    "Latin": "Kossi Lawson",
    "Allemand": "Koffi Adjovi",
    "Espagnol": "Koffi Adjovi",
}

CLASS_FEE_AMOUNTS = {
    "GS A": {"Inscription": 15000, "Scolarité": 45000, "Tenue": 10000},
    "CP1 A": {"Inscription": 20000, "Scolarité": 60000, "Tenue": 12000, "Bibliothèque": 5000},
    "CM1 A": {"Inscription": 20000, "Scolarité": 65000, "Tenue": 12000, "Bibliothèque": 5000},
    "6ème A": {"Inscription": 25000, "Scolarité": 90000, "Tenue": 15000, "Bibliothèque": 5000, "Examen": 10000},
    "3ème A": {"Inscription": 25000, "Scolarité": 95000, "Tenue": 15000, "Bibliothèque": 5000, "Examen": 15000},
    "2nde A": {"Inscription": 30000, "Scolarité": 120000, "Tenue": 18000, "Bibliothèque": 5000, "Examen": 20000},
}

CLASS_STUDENTS = {
    "GS A": [
        ("Ama", "Koffi", date(2020, 5, 14), "F"),
        ("Yao", "Mensah", date(2020, 8, 9), "M"),
        ("Diane", "Soglo", date(2019, 11, 20), "F"),
        ("Kevin", "Tetteh", date(2020, 3, 3), "M"),
        ("Ruth", "Akouete", date(2020, 7, 18), "F"),
        ("Boris", "Sika", date(2020, 1, 27), "M"),
    ],
    "CP1 A": [
        ("Afi", "Balo", date(2018, 4, 11), "F"),
        ("Noel", "Kouassi", date(2018, 6, 30), "M"),
        ("Merveille", "Assi", date(2018, 2, 12), "F"),
        ("Junior", "Komi", date(2018, 10, 6), "M"),
        ("Prisca", "Gnama", date(2018, 8, 8), "F"),
        ("Luc", "Adjei", date(2018, 3, 22), "M"),
    ],
    "CM1 A": [
        ("Clarisse", "Aka", date(2015, 2, 16), "F"),
        ("Ibrahim", "Koffi", date(2015, 7, 7), "M"),
        ("Sandrine", "Diallo", date(2015, 1, 28), "F"),
        ("Didier", "Kouadio", date(2015, 5, 4), "M"),
        ("Murielle", "Gnagne", date(2015, 12, 19), "F"),
        ("Fabrice", "Tano", date(2015, 9, 1), "M"),
    ],
    "6ème A": [
        ("Arielle", "Bamba", date(2013, 4, 15), "F"),
        ("John", "Amani", date(2013, 9, 10), "M"),
        ("Sonia", "Diallo", date(2013, 1, 5), "F"),
        ("Brice", "Aka", date(2013, 6, 24), "M"),
        ("Yasmine", "Kone", date(2012, 11, 11), "F"),
        ("Boris", "Fumey", date(2013, 2, 2), "M"),
    ],
    "3ème A": [
        ("Amadou", "Aka", date(2010, 5, 1), "M"),
        ("Joelle", "Bamba", date(2010, 3, 19), "F"),
        ("Mariam", "Diallo", date(2010, 7, 12), "F"),
        ("Kevin", "Koffi", date(2010, 8, 20), "M"),
        ("Noel", "Tano", date(2010, 10, 14), "M"),
        ("Ruth", "Assi", date(2010, 12, 1), "F"),
    ],
    "2nde A": [
        ("Clarisse", "Dogbe", date(2008, 4, 8), "F"),
        ("Kevin", "Aka", date(2008, 6, 23), "M"),
        ("Flore", "Dogbe", date(2008, 1, 17), "F"),
        ("Noel", "Amani", date(2008, 9, 3), "M"),
        ("Awa", "Balo", date(2008, 7, 25), "F"),
        ("Didier", "Kouame", date(2008, 11, 29), "M"),
    ],
}

TIMETABLE_SEEDS = {
    "6ème A": [
        (1, "08:00", "08:55", "Français"),
        (1, "09:00", "09:55", "Mathématiques"),
        (2, "08:00", "08:55", "Anglais"),
        (2, "09:00", "09:55", "Histoire-Géographie"),
        (4, "10:10", "11:05", "SVT"),
        (5, "14:00", "14:55", "Informatique"),
    ],
    "3ème A": [
        (1, "08:00", "08:55", "Mathématiques"),
        (1, "09:00", "09:55", "Français"),
        (3, "10:10", "11:05", "Physique-Chimie"),
        (4, "08:00", "08:55", "Anglais"),
        (5, "14:00", "14:55", "SVT"),
        (5, "15:00", "15:55", "EPS"),
    ],
    "2nde A": [
        (1, "08:00", "08:55", "Philosophie"),
        (1, "09:00", "09:55", "Mathématiques"),
        (2, "10:10", "11:05", "Français"),
        (3, "08:00", "08:55", "Physique-Chimie"),
        (4, "14:00", "14:55", "Informatique"),
        (5, "15:00", "15:55", "SVT"),
    ],
}


def next_receipt(counter: int) -> str:
    return f"RC-2025-{counter:04d}"


def main() -> int:
    conn = get_connection()
    if not conn:
        print("Connexion base impossible.")
        return 1

    try:
        cursor = conn.cursor()

        for table in [
            "students",
            "teachers",
            "staff_members",
            "classes",
            "subjects",
            "class_subjects",
            "teacher_assignments",
            "fees",
            "class_fees",
            "payments",
            "student_discounts",
            "salary_obligations",
            "salary_payments",
            "timetables",
            "student_optional_subjects",
            "enrollments",
            "grades",
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            if int(cursor.fetchone()[0]) > 0:
                print(f"Le peuplement a été arrêté: la table '{table}' n'est pas vide.")
                conn.rollback()
                return 1

        cursor.execute("SELECT id FROM establishments WHERE name = %s LIMIT 1", (ESTABLISHMENT_NAME,))
        establishment_row = cursor.fetchone()
        if not establishment_row:
            print(f"Etablissement introuvable: {ESTABLISHMENT_NAME}")
            conn.rollback()
            return 1
        establishment_id = int(establishment_row[0])

        cursor.execute("SELECT id FROM school_years WHERE name = %s LIMIT 1", (SCHOOL_YEAR_NAME,))
        year_row = cursor.fetchone()
        if not year_row:
            print(f"Année scolaire introuvable: {SCHOOL_YEAR_NAME}")
            conn.rollback()
            return 1
        school_year_id = int(year_row[0])

        cursor.execute("SELECT id, name FROM terms WHERE school_year_id = %s ORDER BY id", (school_year_id,))
        terms = {name: term_id for term_id, name in cursor.fetchall()}
        if len(terms) < 3:
            print("Les 3 trimestres de l'année scolaire sont requis.")
            conn.rollback()
            return 1

        cursor.execute("SELECT id, name FROM cycles")
        cycles = {name: cycle_id for cycle_id, name in cursor.fetchall()}

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            ("beni",),
        )
        admin_user_id = int(cursor.fetchone()[0])

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE role = 'SECRETAIRE' AND establishment_id = %s
            ORDER BY id
            LIMIT 1
            """,
            (establishment_id,),
        )
        cashier_user_id = int(cursor.fetchone()[0])

        teacher_ids = {}
        for teacher in TEACHERS:
            cursor.execute(
                """
                INSERT INTO teachers (first_name, last_name, phone, email, hire_date, is_active, establishment_id)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                RETURNING id
                """,
                (
                    teacher.first_name,
                    teacher.last_name,
                    teacher.phone,
                    teacher.email,
                    teacher.hire_date,
                    establishment_id,
                ),
            )
            teacher_ids[f"{teacher.first_name} {teacher.last_name}"] = int(cursor.fetchone()[0])

        staff_ids = {}
        for member in STAFF_MEMBERS:
            cursor.execute(
                """
                INSERT INTO staff_members (
                    establishment_id, first_name, last_name, role_title, phone, email, hire_date, is_active, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                RETURNING id
                """,
                (
                    establishment_id,
                    member.first_name,
                    member.last_name,
                    member.role_title,
                    member.phone,
                    member.email,
                    member.hire_date,
                ),
            )
            staff_ids[f"{member.first_name} {member.last_name}"] = int(cursor.fetchone()[0])

        class_ids = {}
        for class_seed in CLASSES:
            cursor.execute(
                """
                INSERT INTO classes (name, level, establishment_id, cycle_id, titular_teacher_id, assistant_teacher_id)
                VALUES (%s, %s, %s, %s, %s, NULL)
                RETURNING id
                """,
                (
                    class_seed["name"],
                    class_seed["level"],
                    establishment_id,
                    cycles[class_seed["cycle"]],
                    teacher_ids[class_seed["titular"]],
                ),
            )
            class_ids[class_seed["name"]] = int(cursor.fetchone()[0])

        subject_ids = {}
        for subject_name in SUBJECTS:
            cursor.execute(
                """
                INSERT INTO subjects (name, establishment_id)
                VALUES (%s, %s)
                RETURNING id
                """,
                (subject_name, establishment_id),
            )
            subject_ids[subject_name] = int(cursor.fetchone()[0])

        class_subject_ids = {}
        for class_name, subject_rows in CLASS_SUBJECTS.items():
            for subject_name, coefficient, subject_type in subject_rows:
                cursor.execute(
                    """
                    INSERT INTO class_subjects (class_id, subject_id, coefficient, subject_type)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (class_ids[class_name], subject_ids[subject_name], coefficient, subject_type),
                )
                class_subject_ids[(class_name, subject_name)] = int(cursor.fetchone()[0])

                cursor.execute(
                    """
                    INSERT INTO teacher_assignments (teacher_id, subject_id, class_id, school_year_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        teacher_ids[SUBJECT_TEACHER[subject_name]],
                        subject_ids[subject_name],
                        class_ids[class_name],
                        school_year_id,
                    ),
                )

        fee_ids = {}
        for fee_name, description in PRIMARY_FEES:
            cursor.execute(
                """
                INSERT INTO fees (name, description)
                VALUES (%s, %s)
                RETURNING id
                """,
                (fee_name, description),
            )
            fee_ids[fee_name] = int(cursor.fetchone()[0])

        class_fee_ids = {}
        for class_name, fees in CLASS_FEE_AMOUNTS.items():
            for fee_name, amount in fees.items():
                cursor.execute(
                    """
                    INSERT INTO class_fees (class_id, fee_id, amount, school_year_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (class_ids[class_name], fee_ids[fee_name], amount, school_year_id),
                )
                class_fee_ids[(class_name, fee_name)] = int(cursor.fetchone()[0])

        student_ids = {}
        receipt_counter = 1
        class_student_ids = {}
        for class_name, students in CLASS_STUDENTS.items():
            class_student_ids[class_name] = []
            level_code = "".join(ch for ch in class_name if ch.isalnum())[:4].upper()
            for index, (first_name, last_name, birth_date, gender) in enumerate(students, start=1):
                matricule = f"{level_code}-{index:03d}"
                cursor.execute(
                    """
                    INSERT INTO students (matricule, first_name, last_name, birth_date, gender, photo_path, establishment_id, is_active)
                    VALUES (%s, %s, %s, %s, %s, NULL, %s, TRUE)
                    RETURNING id
                    """,
                    (matricule, first_name, last_name, birth_date, gender, establishment_id),
                )
                student_id = int(cursor.fetchone()[0])
                student_ids[(class_name, first_name, last_name)] = student_id
                class_student_ids[class_name].append(student_id)

                cursor.execute(
                    """
                    INSERT INTO enrollments (student_id, class_id, school_year_id)
                    VALUES (%s, %s, %s)
                    """,
                    (student_id, class_ids[class_name], school_year_id),
                )

                inscription_amount = CLASS_FEE_AMOUNTS[class_name]["Inscription"]
                cursor.execute(
                    """
                    INSERT INTO payments (student_id, fee_id, amount, payment_date, receipt_number, created_by, class_fee_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        student_id,
                        fee_ids["Inscription"],
                        inscription_amount,
                        date(2025, 9, 20),
                        next_receipt(receipt_counter),
                        cashier_user_id,
                        class_fee_ids[(class_name, "Inscription")],
                    ),
                )
                receipt_counter += 1

                if "Scolarité" in CLASS_FEE_AMOUNTS[class_name]:
                    tuition_total = CLASS_FEE_AMOUNTS[class_name]["Scolarité"]
                    first_installment = int(round(tuition_total * (0.35 if index % 2 else 0.45)))
                    cursor.execute(
                        """
                        INSERT INTO payments (student_id, fee_id, amount, payment_date, receipt_number, created_by, class_fee_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            student_id,
                            fee_ids["Scolarité"],
                            first_installment,
                            date(2025, 10, 18),
                            next_receipt(receipt_counter),
                            cashier_user_id,
                            class_fee_ids[(class_name, "Scolarité")],
                        ),
                    )
                    receipt_counter += 1

                if "Bibliothèque" in CLASS_FEE_AMOUNTS[class_name] and index <= 3:
                    cursor.execute(
                        """
                        INSERT INTO payments (student_id, fee_id, amount, payment_date, receipt_number, created_by, class_fee_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            student_id,
                            fee_ids["Bibliothèque"],
                            CLASS_FEE_AMOUNTS[class_name]["Bibliothèque"],
                            date(2025, 11, 5),
                            next_receipt(receipt_counter),
                            cashier_user_id,
                            class_fee_ids[(class_name, "Bibliothèque")],
                        ),
                    )
                    receipt_counter += 1

        # Réductions ciblées sur la scolarité.
        discount_targets = [
            ("CM1 A", "Clarisse", "Aka", 5000, "Bourse d'encouragement"),
            ("3ème A", "Amadou", "Aka", 10000, "Appui social"),
            ("2nde A", "Clarisse", "Dogbe", 15000, "Excellence académique"),
        ]
        for class_name, first_name, last_name, amount, reason in discount_targets:
            cursor.execute(
                """
                INSERT INTO student_discounts (student_id, fee_id, amount, reason, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (
                    student_ids[(class_name, first_name, last_name)],
                    fee_ids["Scolarité"],
                    amount,
                    reason,
                    cashier_user_id,
                ),
            )

        # Options facultatives par élève pour 3ème et 2nde.
        option_map = {
            "3ème A": {
                "Allemand": ["Amadou Aka", "Mariam Diallo", "Noel Tano"],
                "Espagnol": ["Joelle Bamba", "Kevin Koffi", "Ruth Assi"],
            },
            "2nde A": {
                "Allemand": ["Clarisse Dogbe", "Kevin Aka", "Didier Kouame"],
                "Espagnol": ["Flore Dogbe", "Noel Amani", "Awa Balo"],
            },
        }
        name_to_student_id = {}
        for class_name, students in CLASS_STUDENTS.items():
            for first_name, last_name, *_ in students:
                name_to_student_id[f"{first_name} {last_name}"] = student_ids[(class_name, first_name, last_name)]

        for class_name, subject_groups in option_map.items():
            for subject_name, student_names in subject_groups.items():
                for full_name in student_names:
                    cursor.execute(
                        """
                        INSERT INTO student_optional_subjects (student_id, class_subject_id, school_year_id, created_at)
                        VALUES (%s, %s, %s, NOW())
                        """,
                        (
                            name_to_student_id[full_name],
                            class_subject_ids[(class_name, subject_name)],
                            school_year_id,
                        ),
                    )

        # Notes.
        primary_classes = {"GS A", "CP1 A", "CM1 A"}
        term_order = ["Trimestre 1", "Trimestre 2", "Trimestre 3"]
        for class_name, students in CLASS_STUDENTS.items():
            subjects_for_class = CLASS_SUBJECTS[class_name]
            for term_index, term_name in enumerate(term_order, start=1):
                term_id = terms[term_name]
                for student_index, (first_name, last_name, *_rest) in enumerate(students, start=1):
                    student_id = student_ids[(class_name, first_name, last_name)]
                    for subject_index, (subject_name, _coef, subject_type) in enumerate(subjects_for_class, start=1):
                        # Facultatives individuelles: seulement pour les élèves inscrits à l'option.
                        if class_name in option_map and subject_type == "FACULTATIVE":
                            cursor.execute(
                                """
                                SELECT 1
                                FROM student_optional_subjects
                                WHERE student_id = %s
                                  AND class_subject_id = %s
                                  AND school_year_id = %s
                                LIMIT 1
                                """,
                                (student_id, class_subject_ids[(class_name, subject_name)], school_year_id),
                            )
                            if not cursor.fetchone():
                                continue

                        teacher_id = teacher_ids[SUBJECT_TEACHER[subject_name]]

                        if class_name in primary_classes:
                            value = round(5.5 + ((student_index * 0.55) + (subject_index * 0.18) + (term_index * 0.22)) % 4.0, 1)
                            cursor.execute(
                                """
                                INSERT INTO grades (student_id, subject_id, teacher_id, term_id, value, created_by, max_score, grade_type)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
                                """,
                                (
                                    student_id,
                                    subject_ids[subject_name],
                                    teacher_id,
                                    term_id,
                                    value,
                                    admin_user_id,
                                    10,
                                ),
                            )
                        else:
                            classe_value = round(8.5 + ((student_index * 0.9) + (subject_index * 0.35) + (term_index * 0.25)) % 8.0, 1)
                            compo_value = round(9.0 + ((student_index * 0.8) + (subject_index * 0.3) + (term_index * 0.45)) % 8.0, 1)
                            for grade_type, value in (("classe", classe_value), ("compo", compo_value)):
                                cursor.execute(
                                    """
                                    INSERT INTO grades (student_id, subject_id, teacher_id, term_id, value, created_by, max_score, grade_type)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        student_id,
                                        subject_ids[subject_name],
                                        teacher_id,
                                        term_id,
                                        value,
                                        admin_user_id,
                                        20,
                                        grade_type,
                                    ),
                                )

        # Emplois du temps.
        for class_name, slots in TIMETABLE_SEEDS.items():
            for day_of_week, start_time, end_time, subject_name in slots:
                cursor.execute(
                    """
                    INSERT INTO timetables (
                        establishment_id, class_id, subject_id, teacher_id, school_year_id,
                        day_of_week, start_time, end_time, room, notes, created_by, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, NOW())
                    """,
                    (
                        establishment_id,
                        class_ids[class_name],
                        subject_ids[subject_name],
                        teacher_ids[SUBJECT_TEACHER[subject_name]],
                        school_year_id,
                        day_of_week,
                        start_time,
                        end_time,
                        "Salle 1" if class_name in {"6ème A", "3ème A"} else "Salle 2",
                        admin_user_id,
                    ),
                )

        # Dépenses.
        cursor.execute(
            """
            INSERT INTO expenses (establishment_id, category, amount, description, expense_date, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (establishment_id, "Fournitures", 35000, "Achat de craies et registres", date(2025, 9, 25), cashier_user_id),
        )
        cursor.execute(
            """
            INSERT INTO expenses (establishment_id, category, amount, description, expense_date, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (establishment_id, "Entretien", 20000, "Nettoyage des salles", date(2025, 10, 12), cashier_user_id),
        )

        # Salaires : une obligation par personne pour avril 2026, avec quelques paiements.
        teacher_salary = 85000
        staff_salary = {"Caissière": 70000, "Surveillant": 60000, "Gardien": 50000}
        obligation_ids = []
        for full_name, teacher_id in teacher_ids.items():
            cursor.execute(
                """
                INSERT INTO salary_obligations (
                    establishment_id, teacher_id, period_month, period_year, amount_due, notes,
                    created_by, created_at, person_type, person_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                RETURNING id
                """,
                (
                    establishment_id,
                    teacher_id,
                    4,
                    2026,
                    teacher_salary,
                    f"Salaire enseignant - {full_name}",
                    admin_user_id,
                    "teacher",
                    teacher_id,
                ),
            )
            obligation_ids.append(("teacher", teacher_id, int(cursor.fetchone()[0]), teacher_salary))

        for member in STAFF_MEMBERS:
            full_name = f"{member.first_name} {member.last_name}"
            member_id = staff_ids[full_name]
            amount_due = staff_salary[member.role_title]
            cursor.execute(
                """
                INSERT INTO salary_obligations (
                    establishment_id, staff_member_id, period_month, period_year, amount_due, notes,
                    created_by, created_at, person_type, person_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                RETURNING id
                """,
                (
                    establishment_id,
                    member_id,
                    4,
                    2026,
                    amount_due,
                    f"Salaire employé - {full_name}",
                    admin_user_id,
                    "staff",
                    member_id,
                ),
            )
            obligation_ids.append(("staff", member_id, int(cursor.fetchone()[0]), amount_due))

        for idx, (person_type, person_id, obligation_id, amount_due) in enumerate(obligation_ids, start=1):
            if idx % 3 == 0:
                continue
            amount_paid = amount_due if idx % 2 else int(amount_due * 0.6)
            cursor.execute(
                """
                INSERT INTO salary_payments (
                    establishment_id, teacher_id, staff_member_id, period_month, period_year,
                    amount, payment_date, payment_method, reference, notes, created_by, created_at,
                    obligation_id, person_type, person_id
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    establishment_id,
                    person_id if person_type == "teacher" else None,
                    person_id if person_type == "staff" else None,
                    4,
                    2026,
                    amount_paid,
                    date(2026, 4, 30),
                    "Virement" if person_type == "teacher" else "Espèces",
                    f"SAL-2026-04-{idx:03d}",
                    "Paiement test de démonstration",
                    admin_user_id,
                    obligation_id,
                    person_type,
                    person_id,
                ),
            )

        conn.commit()

        print("Peuplement de démonstration effectué.")
        print("- 9 enseignants")
        print("- 3 employés")
        print("- 6 classes")
        print("- 17 matières")
        print("- 36 élèves")
        print("- notes sur 3 trimestres")
        print("- frais, paiements, réductions")
        print("- obligations de salaires et paiements")
        print("- emplois du temps de démonstration")
        return 0

    except Exception as exc:
        conn.rollback()
        print(f"Peuplement impossible: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
