from __future__ import annotations

from database.connection import get_connection


def ensure_cycle_fee_schema() -> None:
    conn = get_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cycle_fee_configs (
                id SERIAL PRIMARY KEY,
                establishment_id INTEGER REFERENCES establishments(id) ON DELETE CASCADE,
                cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
                fee_id INTEGER NOT NULL REFERENCES fees(id) ON DELETE CASCADE,
                school_year_id INTEGER NOT NULL REFERENCES school_years(id) ON DELETE CASCADE,
                amount NUMERIC NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            ALTER TABLE cycle_fee_configs
            ALTER COLUMN establishment_id DROP NOT NULL
            """
        )
        cursor.execute(
            """
            DROP INDEX IF EXISTS uq_cycle_fee_configs_global
            """
        )
        cursor.execute(
            """
            DROP INDEX IF EXISTS uq_cycle_fee_configs_est
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_cycle_fee_configs_global
            ON cycle_fee_configs (cycle_id, fee_id, school_year_id)
            WHERE establishment_id IS NULL
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_cycle_fee_configs_est
            ON cycle_fee_configs (establishment_id, cycle_id, fee_id, school_year_id)
            WHERE establishment_id IS NOT NULL
            """
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def generate_class_fees_from_cycle_configs(establishment_id: int | None, school_year_id: int, overwrite_existing: bool = True) -> tuple[int, int]:
    conn = get_connection()
    if not conn:
        raise RuntimeError("Connexion base impossible")

    inserted = 0
    updated = 0

    try:
        cursor = conn.cursor()
        if establishment_id is None:
            cursor.execute(
                """
                SELECT id, cycle_id, establishment_id
                FROM classes
                ORDER BY name
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, cycle_id, establishment_id
                FROM classes
                WHERE establishment_id = %s
                ORDER BY name
                """,
                (establishment_id,),
            )
        classes = cursor.fetchall()

        for class_id, cycle_id, class_establishment_id in classes:
            cursor.execute(
                """
                SELECT fee_id, amount
                FROM (
                    SELECT DISTINCT ON (cfg.fee_id)
                        cfg.fee_id,
                        cfg.amount,
                        CASE
                            WHEN cfg.establishment_id = %s THEN 0
                            ELSE 1
                        END AS priority
                    FROM cycle_fee_configs cfg
                    WHERE cfg.school_year_id = %s
                      AND cfg.cycle_id = %s
                      AND (cfg.establishment_id IS NULL OR cfg.establishment_id = %s)
                    ORDER BY cfg.fee_id, priority, cfg.id
                ) picked
                ORDER BY fee_id
                """,
                (class_establishment_id, school_year_id, cycle_id, class_establishment_id),
            )
            rows = cursor.fetchall()

            for fee_id, amount in rows:
                cursor.execute(
                    """
                    SELECT id, amount
                    FROM class_fees
                    WHERE class_id = %s
                      AND fee_id = %s
                      AND school_year_id = %s
                    LIMIT 1
                    """,
                    (class_id, fee_id, school_year_id),
                )
                existing = cursor.fetchone()
                if existing:
                    class_fee_id, current_amount = existing
                    if overwrite_existing and float(current_amount or 0) != float(amount or 0):
                        cursor.execute(
                            """
                            UPDATE class_fees
                            SET amount = %s
                            WHERE id = %s
                            """,
                            (amount, class_fee_id),
                        )
                        updated += 1
                else:
                    cursor.execute(
                        """
                        INSERT INTO class_fees (class_id, fee_id, amount, school_year_id)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (class_id, fee_id, amount, school_year_id),
                    )
                    inserted += 1

        conn.commit()
        return inserted, updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
