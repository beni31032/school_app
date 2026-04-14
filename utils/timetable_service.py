from database.connection import get_connection


def ensure_timetables_table() -> None:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS timetables (
                id SERIAL PRIMARY KEY,
                establishment_id INTEGER NOT NULL REFERENCES establishments(id),
                class_id INTEGER NOT NULL REFERENCES classes(id),
                subject_id INTEGER NOT NULL REFERENCES subjects(id),
                teacher_id INTEGER REFERENCES teachers(id),
                school_year_id INTEGER NOT NULL REFERENCES school_years(id),
                day_of_week VARCHAR(20) NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                room VARCHAR(60),
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                CHECK (start_time < end_time)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timetable_class_year_day
            ON timetables(class_id, school_year_id, day_of_week, start_time)
            """
        )
        conn.commit()
    finally:
        conn.close()
