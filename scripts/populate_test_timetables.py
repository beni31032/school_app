from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


PRIMARY_SLOTS = [
    (1, "08:00", "08:55"),
    (1, "09:00", "09:55"),
    (1, "10:10", "11:05"),
    (2, "08:00", "08:55"),
    (2, "09:00", "09:55"),
    (2, "10:10", "11:05"),
    (3, "08:00", "08:55"),
    (3, "09:00", "09:55"),
    (4, "08:00", "08:55"),
    (4, "09:00", "09:55"),
    (4, "10:10", "11:05"),
    (5, "08:00", "08:55"),
    (5, "09:00", "09:55"),
    (5, "10:10", "11:05"),
]

SECONDARY_SLOTS = [
    (1, "08:00", "08:55"),
    (1, "09:00", "09:55"),
    (1, "10:10", "11:05"),
    (1, "11:10", "12:05"),
    (2, "08:00", "08:55"),
    (2, "09:00", "09:55"),
    (2, "10:10", "11:05"),
    (2, "11:10", "12:05"),
    (3, "08:00", "08:55"),
    (3, "09:00", "09:55"),
    (4, "08:00", "08:55"),
    (4, "09:00", "09:55"),
    (4, "10:10", "11:05"),
    (4, "11:10", "12:05"),
    (5, "08:00", "08:55"),
    (5, "09:00", "09:55"),
    (5, "10:10", "11:05"),
    (5, "11:10", "12:05"),
    (6, "08:00", "08:55"),
    (6, "09:00", "09:55"),
]


@dataclass(frozen=True)
class SubjectAssignment:
    subject_id: int
    subject_name: str
    teacher_id: int | None
    teacher_name: str
    coefficient: float
    subject_type: str


def normalized_weight(coefficient: float, subject_type: str) -> int:
    if subject_type == "FACULTATIVE":
        return 1
    if coefficient >= 20:
        return 3
    if coefficient >= 10:
        return 2
    if coefficient >= 3:
        return 2
    return 1


def build_rotation(assignments: list[SubjectAssignment], class_index: int, slot_count: int) -> list[SubjectAssignment]:
    weighted: list[SubjectAssignment] = []
    for assignment in assignments:
        weighted.extend([assignment] * normalized_weight(float(assignment.coefficient or 1), assignment.subject_type or "OBLIGATOIRE"))

    if not weighted:
        return []

    start = class_index % len(weighted)
    ordered = weighted[start:] + weighted[:start]
    rotation: list[SubjectAssignment] = []
    for slot_index in range(slot_count):
        rotation.append(ordered[slot_index % len(ordered)])
    return rotation


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

        cursor.execute("DELETE FROM timetables")
        deleted_rows = cursor.rowcount

        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                COALESCE(c.level, ''),
                cy.name,
                c.establishment_id
            FROM classes c
            JOIN cycles cy ON cy.id = c.cycle_id
            ORDER BY cy.name, c.name
            """
        )
        classes = cursor.fetchall()

        total_created = 0
        class_summaries = []

        for class_index, (class_id, class_name, level_name, cycle_name, establishment_id) in enumerate(classes):
            cursor.execute(
                """
                SELECT
                    cs.subject_id,
                    s.name,
                    ta.teacher_id,
                    COALESCE(t.last_name, '') || CASE WHEN t.first_name IS NOT NULL AND t.first_name <> '' THEN ' ' || t.first_name ELSE '' END AS teacher_name,
                    COALESCE(cs.coefficient, 1),
                    COALESCE(cs.subject_type, 'OBLIGATOIRE')
                FROM class_subjects cs
                JOIN subjects s ON s.id = cs.subject_id
                LEFT JOIN teacher_assignments ta
                    ON ta.class_id = cs.class_id
                   AND ta.subject_id = cs.subject_id
                   AND ta.school_year_id = %s
                LEFT JOIN teachers t ON t.id = ta.teacher_id
                WHERE cs.class_id = %s
                ORDER BY COALESCE(cs.subject_type, 'OBLIGATOIRE') DESC, COALESCE(cs.coefficient, 1) DESC, s.name
                """,
                (school_year_id, class_id),
            )
            assignments = [
                SubjectAssignment(
                    subject_id=subject_id,
                    subject_name=subject_name,
                    teacher_id=teacher_id,
                    teacher_name=(teacher_name or "").strip() or "-",
                    coefficient=float(coefficient or 1),
                    subject_type=subject_type or "OBLIGATOIRE",
                )
                for subject_id, subject_name, teacher_id, teacher_name, coefficient, subject_type in cursor.fetchall()
            ]
            if not assignments:
                class_summaries.append((class_name, 0))
                continue

            slots = PRIMARY_SLOTS if cycle_name in ("Maternelle", "Primaire") else SECONDARY_SLOTS
            rotation = build_rotation(assignments, class_index, len(slots))

            created_for_class = 0
            room_label = f"Salle {class_name}"
            for (day_of_week, start_time, end_time), assignment in zip(slots, rotation):
                cursor.execute(
                    """
                    INSERT INTO timetables (
                        establishment_id, class_id, subject_id, teacher_id, school_year_id,
                        day_of_week, start_time, end_time, room, notes, created_by, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        establishment_id,
                        class_id,
                        assignment.subject_id,
                        assignment.teacher_id,
                        school_year_id,
                        str(day_of_week),
                        start_time,
                        end_time,
                        room_label,
                        None if assignment.subject_type == "OBLIGATOIRE" else "Option",
                        created_by,
                    ),
                )
                created_for_class += 1

            total_created += created_for_class
            class_summaries.append((class_name, created_for_class))

        conn.commit()

        print(f"Année scolaire : {school_year_name}")
        print(f"Créneaux supprimés avant recharge : {deleted_rows}")
        print(f"Créneaux créés : {total_created}")
        for class_name, created_for_class in class_summaries:
            print(f"{class_name}: {created_for_class} créneaux")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
