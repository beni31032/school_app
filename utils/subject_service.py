from database.connection import get_connection


def ensure_subject_schema() -> None:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            ALTER TABLE subjects
            ADD COLUMN IF NOT EXISTS establishment_id INTEGER
            """
        )
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'subjects_establishment_id_fkey'
                ) THEN
                    ALTER TABLE subjects
                    ADD CONSTRAINT subjects_establishment_id_fkey
                    FOREIGN KEY (establishment_id) REFERENCES establishments(id);
                END IF;
            END $$;
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_subjects_establishment_name
            ON subjects(establishment_id, name)
            """
        )
        conn.commit()
    finally:
        conn.close()
