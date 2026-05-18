from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection


def quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def split_amount(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    raw_parts = [quantize_amount(total * weight) for weight in weights[:-1]]
    used = sum(raw_parts, Decimal("0"))
    raw_parts.append(total - used)
    return raw_parts


def build_receipt_number(counters: dict[int, int], payment_date: date) -> str:
    year = payment_date.year
    counters[year] += 1
    return f"RC-{year}-{counters[year]:05d}"


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

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = 'beni'
            LIMIT 1
            """
        )
        user_row = cursor.fetchone()
        if not user_row:
            cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            user_row = cursor.fetchone()
        if not user_row:
            raise RuntimeError("Aucun utilisateur trouvé pour created_by")
        created_by = int(user_row[0])

        cursor.execute("DELETE FROM payments")
        deleted_rows = cursor.rowcount

        cursor.execute(
            """
            SELECT
                s.id,
                s.first_name,
                s.last_name,
                c.name,
                c.id,
                f.name,
                f.id,
                cf.id,
                cf.amount
            FROM students s
            JOIN enrollments e
                ON e.student_id = s.id
               AND e.school_year_id = %s
            JOIN classes c ON c.id = e.class_id
            JOIN class_fees cf
                ON cf.class_id = c.id
               AND cf.school_year_id = %s
            JOIN fees f ON f.id = cf.fee_id
            ORDER BY c.name, s.last_name, s.first_name, f.name
            """,
            (school_year_id, school_year_id),
        )
        rows = cursor.fetchall()

        students: dict[int, dict] = {}
        for student_id, first_name, last_name, class_name, class_id, fee_name, fee_id, class_fee_id, amount in rows:
            if student_id not in students:
                students[student_id] = {
                    "student_id": student_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "class_name": class_name,
                    "class_id": class_id,
                    "fees": {},
                }
            students[student_id]["fees"][fee_name] = {
                "fee_id": fee_id,
                "class_fee_id": class_fee_id,
                "amount": Decimal(amount),
            }

        receipt_counters: dict[int, int] = defaultdict(int)
        total_payments = 0
        total_amount = Decimal("0")
        profile_counts: dict[str, int] = defaultdict(int)

        for index, student in enumerate(sorted(students.values(), key=lambda item: (item["class_name"], item["last_name"], item["first_name"], item["student_id"]))):
            fees = student["fees"]
            inscription = fees.get("Inscription")
            scolarite = fees.get("Scolarité")
            profile_code = index % 10

            if profile_code in (0, 1, 2):
                profile = "full"
            elif profile_code in (3, 4, 5):
                profile = "strong_partial"
            elif profile_code in (6, 7):
                profile = "mid_partial"
            elif profile_code == 8:
                profile = "light_partial"
            else:
                profile = "unpaid"
            profile_counts[profile] += 1

            payments_to_create: list[tuple[int, int, Decimal, date]] = []

            if inscription and profile != "unpaid":
                if profile == "light_partial":
                    inscription_amount = Decimal("2500")
                else:
                    inscription_amount = Decimal(inscription["amount"])
                inscription_date = date(2025, 9, 18) + timedelta(days=index % 20)
                payments_to_create.append(
                    (
                        inscription["fee_id"],
                        inscription["class_fee_id"],
                        inscription_amount,
                        inscription_date,
                    )
                )

            if scolarite and profile != "unpaid":
                base_amount = Decimal(scolarite["amount"])
                if profile == "full":
                    target = base_amount
                    weights = [Decimal("0.30"), Decimal("0.30"), Decimal("0.40")]
                    dates = [
                        date(2025, 10, 10) + timedelta(days=index % 12),
                        date(2026, 1, 15) + timedelta(days=index % 10),
                        date(2026, 5, 17),
                    ]
                elif profile == "strong_partial":
                    target = quantize_amount(base_amount * Decimal("0.75"))
                    weights = [Decimal("0.50"), Decimal("0.50")]
                    dates = [
                        date(2025, 11, 12) + timedelta(days=index % 10),
                        date(2026, 3, 10) + timedelta(days=index % 8),
                    ]
                elif profile == "mid_partial":
                    target = quantize_amount(base_amount * Decimal("0.50"))
                    weights = [Decimal("0.50"), Decimal("0.50")]
                    dates = [
                        date(2025, 10, 28) + timedelta(days=index % 7),
                        date(2026, 2, 18) + timedelta(days=index % 7),
                    ]
                else:
                    target = quantize_amount(base_amount * Decimal("0.25"))
                    weights = [Decimal("1.0")]
                    dates = [date(2026, 5, 17)]

                for amount_part, payment_date in zip(split_amount(target, weights), dates):
                    payments_to_create.append(
                        (
                            scolarite["fee_id"],
                            scolarite["class_fee_id"],
                            amount_part,
                            payment_date,
                        )
                    )

            for fee_id, class_fee_id, amount, payment_date in payments_to_create:
                receipt_number = build_receipt_number(receipt_counters, payment_date)
                cursor.execute(
                    """
                    INSERT INTO payments (
                        student_id, fee_id, class_fee_id, amount,
                        payment_date, receipt_number, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        student["student_id"],
                        fee_id,
                        class_fee_id,
                        amount,
                        payment_date,
                        receipt_number,
                        created_by,
                    ),
                )
                total_payments += 1
                total_amount += amount

        conn.commit()

        print(f"Année scolaire : {school_year_name}")
        print(f"Paiements supprimés avant recharge : {deleted_rows}")
        print(f"Paiements créés : {total_payments}")
        print(f"Montant total encaissé : {int(total_amount)} FCFA")
        print("Profils :")
        for profile_name in ("full", "strong_partial", "mid_partial", "light_partial", "unpaid"):
            print(f"  - {profile_name}: {profile_counts.get(profile_name, 0)} élèves")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
