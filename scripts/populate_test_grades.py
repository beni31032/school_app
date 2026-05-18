from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


PRIMARY_CYCLES = {"Maternelle", "Primaire"}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def primary_grade(student_index: int, subject_index: int, term_index: int) -> float:
    value = 5.6 + ((student_index * 0.47) + (subject_index * 0.19) + (term_index * 0.23)) % 4.1
    return round(clamp(value, 4.5, 9.8), 1)


def secondary_classe_grade(student_index: int, subject_index: int, term_index: int) -> float:
    value = 8.4 + ((student_index * 0.83) + (subject_index * 0.31) + (term_index * 0.27)) % 8.3
    return round(clamp(value, 6.0, 18.8), 1)


def secondary_compo_grade(student_index: int, subject_index: int, term_index: int) -> float:
    value = 8.9 + ((student_index * 0.79) + (subject_index * 0.28) + (term_index * 0.41)) % 8.1
    return round(clamp(value, 6.5, 19.0), 1)


def main() -> None:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM school_years ORDER BY id DESC LIMIT 1")
        school_year_row = cursor.fetchone()
        if not school_year_row:
            raise RuntimeError("Aucune année scolaire trouvée")
        school_year_id, school_year_name = school_year_row

        cursor.execute("SELECT id FROM users WHERE username = 'beni' LIMIT 1")
        user_row = cursor.fetchone()
        if not user_row:
            cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            user_row = cursor.fetchone()
        if not user_row:
            raise RuntimeError("Aucun utilisateur trouvé pour created_by")
        created_by = int(user_row[0])

        cursor.execute("DELETE FROM grades")
        deleted_rows = cursor.rowcount

        cursor.execute(
            """
            SELECT id, name
            FROM terms
            WHERE school_year_id = %s
            ORDER BY id
            """,
            (school_year_id,),
        )
        terms = cursor.fetchall()
        if not terms:
            raise RuntimeError("Aucun trimestre trouvé pour l'année active")

        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                cy.name,
                COALESCE(c.level, '')
            FROM classes c
            JOIN cycles cy ON cy.id = c.cycle_id
            ORDER BY cy.name, c.name
            """
        )
        classes = cursor.fetchall()

        total_inserted = 0
        class_summaries: list[tuple[str, int]] = []

        for class_id, class_name, cycle_name, _level_name in classes:
            cursor.execute(
                """
                SELECT
                    e.student_id,
                    s.last_name,
                    s.first_name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                WHERE e.class_id = %s
                  AND e.school_year_id = %s
                  AND s.is_active = TRUE
                ORDER BY s.last_name, s.first_name, s.id
                """,
                (class_id, school_year_id),
            )
            students = cursor.fetchall()
            if not students:
                class_summaries.append((class_name, 0))
                continue

            cursor.execute(
                """
                SELECT
                    cs.subject_id,
                    sub.name,
                    COALESCE(cs.subject_type, 'OBLIGATOIRE') AS subject_type,
                    COALESCE(cs.coefficient, 1) AS coefficient,
                    ta.teacher_id
                FROM class_subjects cs
                JOIN subjects sub ON sub.id = cs.subject_id
                LEFT JOIN teacher_assignments ta
                    ON ta.class_id = cs.class_id
                   AND ta.subject_id = cs.subject_id
                   AND ta.school_year_id = %s
                WHERE cs.class_id = %s
                ORDER BY sub.name
                """,
                (school_year_id, class_id),
            )
            subjects = cursor.fetchall()
            if not subjects:
                class_summaries.append((class_name, 0))
                continue

            optional_choices = set()
            cursor.execute(
                """
                SELECT sos.student_id, cs.subject_id
                FROM student_optional_subjects sos
                JOIN class_subjects cs ON cs.id = sos.class_subject_id
                WHERE sos.school_year_id = %s
                  AND cs.class_id = %s
                """,
                (school_year_id, class_id),
            )
            optional_choices = {(student_id, subject_id) for student_id, subject_id in cursor.fetchall()}

            inserted_for_class = 0
            for term_index, (term_id, _term_name) in enumerate(terms, start=1):
                for student_index, (student_id, _last_name, _first_name) in enumerate(students, start=1):
                    for subject_index, (subject_id, _subject_name, subject_type, _coefficient, teacher_id) in enumerate(subjects, start=1):
                        if subject_type == "FACULTATIVE" and (student_id, subject_id) not in optional_choices:
                            continue

                        if cycle_name in PRIMARY_CYCLES:
                            value = primary_grade(student_index, subject_index, term_index)
                            cursor.execute(
                                """
                                INSERT INTO grades (
                                    student_id, subject_id, teacher_id, term_id, value,
                                    created_by, max_score, grade_type
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
                                """,
                                (
                                    student_id,
                                    subject_id,
                                    teacher_id,
                                    term_id,
                                    value,
                                    created_by,
                                    10,
                                ),
                            )
                            inserted_for_class += 1
                        else:
                            classe_value = secondary_classe_grade(student_index, subject_index, term_index)
                            compo_value = secondary_compo_grade(student_index, subject_index, term_index)
                            for grade_type, value in (("classe", classe_value), ("compo", compo_value)):
                                cursor.execute(
                                    """
                                    INSERT INTO grades (
                                        student_id, subject_id, teacher_id, term_id, value,
                                        created_by, max_score, grade_type
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        student_id,
                                        subject_id,
                                        teacher_id,
                                        term_id,
                                        value,
                                        created_by,
                                        20,
                                        grade_type,
                                    ),
                                )
                                inserted_for_class += 1

            total_inserted += inserted_for_class
            class_summaries.append((class_name, inserted_for_class))

        conn.commit()

        print(f"Année scolaire : {school_year_name}")
        print(f"Notes supprimées avant recharge : {deleted_rows}")
        print(f"Notes créées : {total_inserted}")
        for class_name, inserted_for_class in class_summaries:
            print(f"{class_name}: {inserted_for_class} notes")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
