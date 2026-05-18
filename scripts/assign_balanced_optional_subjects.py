from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


LANGUAGE_SUBJECTS = ("Allemand", "Espagnol")
PRACTICAL_SUBJECTS = ("Dessin", "Enseignement ménager")
TARGET_LEVEL_MARKERS = ("1ère", "1ere", "première", "premiere", "tle", "terminale")
OPTION_PATTERNS = (
    ("Allemand", "Dessin"),
    ("Espagnol", "Enseignement ménager"),
    ("Allemand", "Enseignement ménager"),
    ("Espagnol", "Dessin"),
)


def is_target_level(level_name: str) -> bool:
    normalized = (level_name or "").strip().lower()
    return any(marker in normalized for marker in TARGET_LEVEL_MARKERS)


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

        cursor.execute(
            """
            SELECT id, name, COALESCE(level, '')
            FROM classes
            ORDER BY name
            """
        )
        classes = [row for row in cursor.fetchall() if is_target_level(row[2])]

        total_deleted = 0
        total_created = 0
        class_summaries = []

        for class_id, class_name, _level_name in classes:
            cursor.execute(
                """
                SELECT s.id
                FROM students s
                JOIN enrollments e
                    ON e.student_id = s.id
                   AND e.school_year_id = %s
                WHERE e.class_id = %s
                ORDER BY s.last_name, s.first_name, s.id
                """,
                (school_year_id, class_id),
            )
            student_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT cs.id, sub.name
                FROM class_subjects cs
                JOIN subjects sub ON sub.id = cs.subject_id
                WHERE cs.class_id = %s
                  AND COALESCE(cs.subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'
                ORDER BY sub.name
                """,
                (class_id,),
            )
            subject_rows = cursor.fetchall()
            subject_map = {name: class_subject_id for class_subject_id, name in subject_rows}

            missing = [
                name
                for name in (*LANGUAGE_SUBJECTS, *PRACTICAL_SUBJECTS)
                if name not in subject_map
            ]
            if missing:
                raise RuntimeError(
                    f"Classe {class_name}: matières facultatives manquantes: {', '.join(missing)}"
                )

            cursor.execute(
                """
                DELETE FROM student_optional_subjects sos
                WHERE sos.school_year_id = %s
                  AND sos.student_id IN (
                      SELECT e.student_id
                      FROM enrollments e
                      WHERE e.class_id = %s
                        AND e.school_year_id = %s
                  )
                  AND sos.class_subject_id IN (
                      SELECT id
                      FROM class_subjects
                      WHERE class_id = %s
                        AND COALESCE(subject_type, 'OBLIGATOIRE') = 'FACULTATIVE'
                  )
                """,
                (school_year_id, class_id, school_year_id, class_id),
            )
            total_deleted += cursor.rowcount

            created_for_class = 0
            language_counts = {name: 0 for name in LANGUAGE_SUBJECTS}
            practical_counts = {name: 0 for name in PRACTICAL_SUBJECTS}

            for index, student_id in enumerate(student_ids):
                language_subject, practical_subject = OPTION_PATTERNS[index % len(OPTION_PATTERNS)]

                for subject_name in (language_subject, practical_subject):
                    cursor.execute(
                        """
                        INSERT INTO student_optional_subjects (student_id, class_subject_id, school_year_id)
                        VALUES (%s, %s, %s)
                        """,
                        (student_id, subject_map[subject_name], school_year_id),
                    )
                    created_for_class += 1

                language_counts[language_subject] += 1
                practical_counts[practical_subject] += 1

            total_created += created_for_class
            class_summaries.append(
                (
                    class_name,
                    len(student_ids),
                    language_counts,
                    practical_counts,
                    created_for_class,
                )
            )

        conn.commit()

        print(f"Annee scolaire: {school_year_name}")
        print(f"Choix supprimes: {total_deleted}")
        print(f"Choix crees: {total_created}")
        for class_name, student_count, language_counts, practical_counts, created_for_class in class_summaries:
            print(
                f"{class_name}: {student_count} eleves, {created_for_class} choix | "
                f"Langues={language_counts} | Pratiques={practical_counts}"
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
