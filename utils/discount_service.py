from database.connection import get_connection


def ensure_discount_schema() -> None:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            ALTER TABLE student_discounts
            ADD COLUMN IF NOT EXISTS school_year_id INTEGER
            """
        )
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'student_discounts_school_year_id_fkey'
                ) THEN
                    ALTER TABLE student_discounts
                    ADD CONSTRAINT student_discounts_school_year_id_fkey
                    FOREIGN KEY (school_year_id) REFERENCES school_years(id);
                END IF;
            END $$;
            """
        )
        cursor.execute(
            """
            WITH latest_school_year AS (
                SELECT id
                FROM school_years
                ORDER BY id DESC
                LIMIT 1
            ),
            inferred_discounts AS (
                SELECT
                    sd.id,
                    COALESCE(
                        (
                            SELECT cf.school_year_id
                            FROM class_fees cf
                            JOIN enrollments e
                              ON e.class_id = cf.class_id
                             AND e.school_year_id = cf.school_year_id
                            WHERE e.student_id = sd.student_id
                              AND cf.fee_id = sd.fee_id
                            ORDER BY cf.school_year_id DESC
                            LIMIT 1
                        ),
                        (SELECT id FROM latest_school_year)
                    ) AS inferred_school_year_id
                FROM student_discounts sd
                WHERE sd.school_year_id IS NULL
            )
            UPDATE student_discounts sd
            SET school_year_id = inferred_discounts.inferred_school_year_id
            FROM inferred_discounts
            WHERE sd.id = inferred_discounts.id
              AND inferred_discounts.inferred_school_year_id IS NOT NULL
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_student_discounts_student_fee_year
            ON student_discounts(student_id, fee_id, school_year_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_student_discounts_school_year
            ON student_discounts(school_year_id)
            """
        )
        conn.commit()
    finally:
        conn.close()
