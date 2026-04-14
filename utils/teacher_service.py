from database.connection import get_connection


def ensure_teacher_schema() -> None:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            ALTER TABLE teachers
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_teachers_active_name
            ON teachers(is_active, last_name, first_name)
            """
        )
        conn.commit()
    finally:
        conn.close()
