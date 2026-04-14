from database.connection import get_connection


def ensure_expenses_table() -> None:
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                establishment_id INTEGER NOT NULL REFERENCES establishments(id),
                amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
                category VARCHAR(100) NOT NULL,
                expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
                description TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expenses_est_date
            ON expenses(establishment_id, expense_date DESC)
            """
        )
        conn.commit()
    finally:
        conn.close()
