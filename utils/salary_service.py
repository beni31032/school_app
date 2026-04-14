from database.connection import get_connection


def ensure_salary_table() -> None:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_members (
                id SERIAL PRIMARY KEY,
                establishment_id INTEGER NOT NULL REFERENCES establishments(id),
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                role_title VARCHAR(120) NOT NULL,
                phone VARCHAR(30),
                email VARCHAR(120),
                hire_date DATE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS salary_obligations (
                id SERIAL PRIMARY KEY,
                establishment_id INTEGER NOT NULL REFERENCES establishments(id),
                teacher_id INTEGER REFERENCES teachers(id),
                staff_member_id INTEGER REFERENCES staff_members(id),
                person_type VARCHAR(20) DEFAULT 'TEACHER',
                person_id INTEGER,
                period_month INTEGER NOT NULL CHECK (period_month BETWEEN 1 AND 12),
                period_year INTEGER NOT NULL CHECK (period_year >= 2000),
                amount_due NUMERIC(12,2) NOT NULL CHECK (amount_due > 0),
                notes TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS salary_payments (
                id SERIAL PRIMARY KEY,
                establishment_id INTEGER NOT NULL REFERENCES establishments(id),
                teacher_id INTEGER REFERENCES teachers(id),
                staff_member_id INTEGER REFERENCES staff_members(id),
                person_type VARCHAR(20) DEFAULT 'TEACHER',
                person_id INTEGER,
                period_month INTEGER NOT NULL CHECK (period_month BETWEEN 1 AND 12),
                period_year INTEGER NOT NULL CHECK (period_year >= 2000),
                amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
                payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
                payment_method VARCHAR(50),
                reference VARCHAR(100),
                notes TEXT,
                obligation_id INTEGER REFERENCES salary_obligations(id),
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )

        cursor.execute(
            """
            UPDATE salary_obligations
            SET person_type = 'TEACHER', person_id = teacher_id
            WHERE person_type IS NULL AND teacher_id IS NOT NULL
            """
        )
        cursor.execute(
            """
            UPDATE salary_payments
            SET person_type = 'TEACHER', person_id = teacher_id
            WHERE person_type IS NULL AND teacher_id IS NOT NULL
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_salary_obligation_person_period
            ON salary_obligations(establishment_id, person_type, person_id, period_month, period_year)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_salary_payments_obligation
            ON salary_payments(obligation_id)
            """
        )
        conn.commit()
    finally:
        conn.close()
