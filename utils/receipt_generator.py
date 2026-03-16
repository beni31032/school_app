import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.connection import get_connection


def generate_receipt(payment_id):

    conn = get_connection()
    cursor = conn.cursor()

    # ----------------------------
    # Informations école
    # ----------------------------
    cursor.execute("""
        SELECT name, address, phone, email
        FROM school_info
        LIMIT 1
    """)

    school = cursor.fetchone()

    school_name = school[0]
    address = school[1]
    phone = school[2]
    email = school[3]

    # ----------------------------
    # Informations paiement
    # ----------------------------
    cursor.execute(
        """
        SELECT
            p.receipt_number,
            p.payment_date,
            p.amount,
            s.first_name,
            s.last_name,
            c.name,
            sy.name,
            p.student_id
        FROM payments p
        JOIN students s ON s.id = p.student_id
        JOIN enrollments e ON e.student_id = s.id
        JOIN classes c ON c.id = e.class_id
        JOIN school_years sy ON sy.id = e.school_year_id
        WHERE p.id = %s
        """,
        (payment_id,)
    )

    row = cursor.fetchone()

    receipt_number = row[0]
    payment_date = row[1]
    amount = float(row[2])
    first_name = row[3]
    last_name = row[4]
    class_name = row[5]
    school_year = row[6]
    student_id = row[7]

    student_name = f"{first_name} {last_name}"

    # ----------------------------
    # Situation financière
    # ----------------------------
    cursor.execute(
        """
        SELECT
            SUM(cf.amount) AS total_expected,
            COALESCE(SUM(p.amount),0) AS total_paid
        FROM class_fees cf
        JOIN enrollments e ON e.class_id = cf.class_id
        LEFT JOIN payments p
            ON p.class_fee_id = cf.id
           AND p.student_id = e.student_id
        WHERE e.student_id = %s
        AND cf.school_year_id = e.school_year_id
        """,
        (student_id,)
    )

    totals = cursor.fetchone()

    total_expected = float(totals[0] or 0)
    total_paid = float(totals[1] or 0)

    remaining = total_expected - total_paid

    # ----------------------------
    # Historique paiements
    # ----------------------------
    cursor.execute(
        """
        SELECT payment_date, amount
        FROM payments
        WHERE student_id = %s
        ORDER BY payment_date
        """,
        (student_id,)
    )

    history = cursor.fetchall()

    conn.close()

    # ----------------------------
    # Création PDF
    # ----------------------------
    os.makedirs("receipts", exist_ok=True)

    filepath = f"receipts/{receipt_number}.pdf"

    c = canvas.Canvas(filepath, pagesize=A4)

    width, height = A4
    y = height - 50

    # ----------------------------
    # En-tête école
    # ----------------------------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, school_name)

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(200, y, address)

    y -= 15
    c.drawString(200, y, f"Tél : {phone}")

    y -= 15
    c.drawString(200, y, f"Email : {email}")

    # ----------------------------
    # Titre reçu
    # ----------------------------
    y -= 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, y, f"Reçu de paiement N° {receipt_number}")

    # ----------------------------
    # Infos élève
    # ----------------------------
    y -= 40
    c.setFont("Helvetica", 11)

    c.drawString(60, y, f"Année scolaire : {school_year}")

    y -= 20
    c.drawString(60, y, f"Nom et Prénoms : {student_name}")

    y -= 20
    c.drawString(60, y, f"Classe : {class_name}")

    y -= 20
    c.drawString(60, y, f"Date opération : {payment_date}")

    # ----------------------------
    # Montant payé
    # ----------------------------
    y -= 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, f"Montant payé : {int(amount)} FCFA")

    # ----------------------------
    # Etat des paiements
    # ----------------------------
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

    # ----------------------------
    # Historique
    # ----------------------------
    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Détail des règlements")

    y -= 20
    c.setFont("Helvetica", 11)

    for date, amt in history:
        c.drawString(60, y, str(date))
        c.drawString(200, y, f"{int(amt)} F")
        y -= 20

    # ----------------------------
    # Signature
    # ----------------------------
    y -= 40
    c.drawString(60, y, "Signature caissier(e)")

    c.showPage()
    c.save()

    return filepath