import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.connection import get_connection


def _get_school_identity(cursor, establishment_id):
    school_name = "École"
    address = ""
    phone = ""
    email = ""

    if establishment_id is not None:
        cursor.execute(
            """
            SELECT name, COALESCE(address, ''), COALESCE(phone, '')
            FROM establishments
            WHERE id = %s
            """,
            (establishment_id,)
        )
        row = cursor.fetchone()
        if row:
            school_name, address, phone = row

    cursor.execute(
        """
        SELECT COALESCE(email, '')
        FROM school_info
        ORDER BY id
        LIMIT 1
        """
    )
    info_row = cursor.fetchone()
    if info_row:
        email = info_row[0] or ""

    return school_name, address, phone, email


def generate_receipt(payment_id):
    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.receipt_number,
                p.payment_date,
                p.amount,
                s.first_name,
                s.last_name,
                COALESCE(c.name, '-') AS class_name,
                sy.id AS school_year_id,
                COALESCE(sy.name, '-') AS school_year_name,
                p.student_id,
                s.establishment_id
            FROM payments p
            JOIN students s ON s.id = p.student_id
            LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
            LEFT JOIN school_years sy ON sy.id = cf.school_year_id
            LEFT JOIN enrollments e
              ON e.student_id = s.id
             AND e.school_year_id = cf.school_year_id
            LEFT JOIN classes c ON c.id = e.class_id
            WHERE p.id = %s
            LIMIT 1
            """,
            (payment_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise Exception("Paiement introuvable.")

        (
            receipt_number,
            payment_date,
            amount,
            first_name,
            last_name,
            class_name,
            school_year_id,
            school_year_name,
            student_id,
            establishment_id,
        ) = row

        school_name, address, phone, email = _get_school_identity(cursor, establishment_id)
        student_name = f"{first_name} {last_name}"

        cursor.execute(
            """
            SELECT COALESCE(SUM(cf.amount), 0)
            FROM class_fees cf
            JOIN enrollments e
              ON e.class_id = cf.class_id
             AND e.school_year_id = cf.school_year_id
            WHERE e.student_id = %s
              AND (%s IS NULL OR e.school_year_id = %s)
            """,
            (student_id, school_year_id, school_year_id)
        )
        total_expected = float(cursor.fetchone()[0] or 0)

        cursor.execute(
            """
            SELECT COALESCE(SUM(p.amount), 0)
            FROM payments p
            LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
            WHERE p.student_id = %s
              AND (%s IS NULL OR cf.school_year_id = %s)
            """,
            (student_id, school_year_id, school_year_id)
        )
        total_paid = float(cursor.fetchone()[0] or 0)
        remaining = total_expected - total_paid

        cursor.execute(
            """
            SELECT p.payment_date, p.amount
            FROM payments p
            LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
            WHERE p.student_id = %s
              AND (%s IS NULL OR cf.school_year_id = %s)
            ORDER BY p.payment_date, p.id
            """,
            (student_id, school_year_id, school_year_id)
        )
        history = cursor.fetchall()
    finally:
        conn.close()

    os.makedirs("receipts", exist_ok=True)
    filepath = f"receipts/{receipt_number}.pdf"

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, school_name)

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(200, y, address)

    y -= 15
    c.drawString(200, y, f"Tél : {phone}")

    y -= 15
    c.drawString(200, y, f"Email : {email}")

    y -= 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, y, f"Reçu de paiement N° {receipt_number}")

    y -= 40
    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Année scolaire : {school_year_name}")
    y -= 20
    c.drawString(60, y, f"Nom et Prénoms : {student_name}")
    y -= 20
    c.drawString(60, y, f"Classe : {class_name}")
    y -= 20
    c.drawString(60, y, f"Date opération : {payment_date}")

    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, f"Montant payé : {int(float(amount))} FCFA")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Etat des paiements")

    y -= 20
    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Total écolage : {int(total_expected)} F")
    y -= 20
    c.drawString(60, y, f"Total réglé : {int(total_paid)} F")
    y -= 20
    c.drawString(60, y, f"Reste à régler : {int(remaining)} F")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Détail des règlements")

    y -= 20
    c.setFont("Helvetica", 11)
    for paid_at, amt in history:
        if y < 80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
        c.drawString(60, y, str(paid_at))
        c.drawString(200, y, f"{int(float(amt or 0))} F")
        y -= 20

    y -= 20
    c.drawString(60, y, "Signature caissier(e)")

    c.showPage()
    c.save()
    return filepath
