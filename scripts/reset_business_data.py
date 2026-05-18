from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


BUSINESS_TABLES = [
    "audit_logs",
    "salary_payments",
    "salary_obligations",
    "expenses",
    "payments",
    "student_discounts",
    "student_optional_subjects",
    "grades",
    "timetables",
    "teacher_assignments",
    "class_subjects",
    "class_fees",
    "enrollments",
    "fees",
    "subjects",
    "classes",
    "teachers",
    "staff_members",
    "students",
]

PRESERVED_TABLES = [
    "users",
    "establishments",
    "school_years",
    "terms",
    "cycles",
    "school_info",
]


def main() -> int:
    conn = get_connection()
    if not conn:
        print("Connexion base impossible.")
        return 1

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        existing_tables = {row[0] for row in cursor.fetchall()}

        tables_to_reset = [table for table in BUSINESS_TABLES if table in existing_tables]
        missing_tables = [table for table in BUSINESS_TABLES if table not in existing_tables]

        if not tables_to_reset:
            print("Aucune table métier à nettoyer.")
            return 0

        before_counts: dict[str, int] = {}
        for table in tables_to_reset:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            before_counts[table] = int(cursor.fetchone()[0])

        truncate_sql = "TRUNCATE TABLE " + ", ".join(tables_to_reset) + " RESTART IDENTITY CASCADE"
        cursor.execute(truncate_sql)
        conn.commit()

        print("Nettoyage métier effectué.")
        print("")
        print("Tables vidées :")
        for table in tables_to_reset:
            print(f"- {table}: {before_counts[table]} ligne(s) supprimée(s)")

        if missing_tables:
            print("")
            print("Tables absentes ignorées :")
            for table in missing_tables:
                print(f"- {table}")

        print("")
        print("Tables conservées :")
        for table in PRESERVED_TABLES:
            if table in existing_tables:
                print(f"- {table}")

        return 0
    except Exception as exc:
        conn.rollback()
        print(f"Reset impossible: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
