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
        cursor.execute(
            """
            ALTER TABLE class_subjects
            ADD COLUMN IF NOT EXISTS subject_type VARCHAR(20)
            """
        )
        cursor.execute(
            """
            UPDATE class_subjects
            SET subject_type = 'OBLIGATOIRE'
            WHERE subject_type IS NULL OR TRIM(subject_type) = ''
            """
        )
        cursor.execute(
            """
            ALTER TABLE class_subjects
            ALTER COLUMN subject_type SET DEFAULT 'OBLIGATOIRE'
            """
        )
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'class_subjects_subject_type_check'
                ) THEN
                    ALTER TABLE class_subjects
                    ADD CONSTRAINT class_subjects_subject_type_check
                    CHECK (subject_type IN ('OBLIGATOIRE', 'FACULTATIVE'));
                END IF;
            END $$;
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_class_subjects_subject_type
            ON class_subjects(subject_type)
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_optional_subjects (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                class_subject_id INTEGER NOT NULL REFERENCES class_subjects(id) ON DELETE CASCADE,
                school_year_id INTEGER NOT NULL REFERENCES school_years(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_student_optional_subjects
            ON student_optional_subjects(student_id, class_subject_id, school_year_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_student_optional_subjects_student_year
            ON student_optional_subjects(student_id, school_year_id)
            """
        )
        conn.commit()
    finally:
        conn.close()
