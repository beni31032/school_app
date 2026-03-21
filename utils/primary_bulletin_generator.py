# utils/primary_bulletin_generator.py

import os
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from database.connection import get_connection
from utils.primary_bulletin_service import get_primary_bulletin_data


def generate_primary_bulletin(student_id: int, term_id: int) -> str:
    data = get_primary_bulletin_data(student_id, term_id)

    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name, address, phone, email
            FROM school_info
            LIMIT 1
            """
        )
        school = cursor.fetchone()

        school_name = school[0] if school else "École"
        school_address = school[1] if school else ""
        school_phone = school[2] if school else ""
        school_email = school[3] if school else ""

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE gender = 'M') AS boys,
                COUNT(*) FILTER (WHERE gender = 'F') AS girls
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            WHERE e.class_id = %s
              AND s.is_active = TRUE
            """,
            (data["class_id"],)
        )
        total, boys, girls = cursor.fetchone()

    finally:
        conn.close()

    # N° basé sur l'ordre alphabétique / rang dans la classe
    numero = data["rank"]

    os.makedirs("bulletins/primary", exist_ok=True)
    filename = f"bulletins/primary/{data['student_name'].replace(' ', '_')}.pdf"

    c = canvas.Canvas(filename, pagesize=A5)
    width, height = A5

    left = 20
    right = width - 20
    y = height - 20

    # =========================
    # EN-TÊTE
    # =========================
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(left, y, "MINISTERE DES ENSEIGNEMENTS")
    y -= 9
    c.drawString(left, y, "PRIMAIRE ET SECONDAIRE")

    c.drawRightString(right, y + 9, "REPUBLIQUE TOGOLAISE")
    c.setFont("Helvetica", 6.5)
    c.drawRightString(right, y, "Travail - Liberté - Patrie")

    y -= 14

    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(width / 2, y, school_name)

    y -= 9
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(width / 2, y, school_address)

    y -= 8
    c.drawCentredString(width / 2, y, f"Tél : {school_phone} | Email : {school_email}")

    # Cadre photo vide
    photo_x = right - 70
    photo_y = y - 55
    c.rect(photo_x, photo_y, 50, 55)

    y -= 42

    # =========================
    # TITRE
    # =========================
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, y, "Bulletin d'évaluation")

    y -= 11
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, y, data["term_name"])

    # Bloc droite
    c.setFont("Helvetica", 7)
    info_x = photo_x - 5
    c.drawRightString(info_x, y + 26, f"Année scolaire : {data['school_year_name']}")
    c.drawRightString(info_x, y + 14, f"Classe : {data['class_name']}")
    c.drawRightString(info_x, y + 2, f"Effectif : {total}")
    c.drawRightString(info_x, y - 10, f"G : {boys}")
    c.drawRightString(info_x, y - 22, f"F : {girls}")

    y -= 34

    # =========================
    # IDENTITÉ
    # =========================
    # Cadre identité
    box_y_top = y + 8
    box_height = 35
    c.rect(left, box_y_top - box_height, width - 40, box_height)

    c.setFont("Helvetica", 8)
    c.drawString(left + 6, y, f"N° : {numero}")

    y -= 12
    c.drawString(left + 6, y, f"Nom et Prénom(s) : {data['student_name']}")
    c.drawRightString(right - 6, y, f"Sexe : {data['gender']}")

    y -= 18

    # =========================
    # TABLEAU
    # =========================
    table_x = left
    table_width = width - 40

    col_disc = 220
    col_note = 45
    col_sur = table_width - col_disc - col_note

    row_h = 15

    x1 = table_x
    x2 = table_x + col_disc
    x3 = x2 + col_note
    x4 = table_x + table_width

    # Header
    c.setFillColor(colors.lightgrey)
    c.rect(table_x, y - row_h, table_width, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)

    c.line(x2, y - row_h, x2, y)
    c.line(x3, y - row_h, x3, y)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x1 + 4, y - 10, "DISCIPLINES")
    c.drawCentredString((x2 + x3) / 2, y - 10, "NOTES")
    c.drawCentredString((x3 + x4) / 2, y - 10, "SUR")

    y -= row_h
    c.setFont("Helvetica", 7.5)

    for subject in data["subjects"]:
        c.rect(table_x, y - row_h, table_width, row_h, fill=0, stroke=1)
        c.line(x2, y - row_h, x2, y)
        c.line(x3, y - row_h, x3, y)

        c.drawString(x1 + 4, y - 10, subject["subject_name"][:42])
        c.drawCentredString((x2 + x3) / 2, y - 10, f"{subject['score']:.1f}")
        c.drawCentredString((x3 + x4) / 2, y - 10, f"{subject['max_score']:.0f}")

        y -= row_h

    # Ligne total
    c.rect(table_x, y - row_h, table_width, row_h, fill=0, stroke=1)
    c.line(x2, y - row_h, x2, y)
    c.line(x3, y - row_h, x3, y)

    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString((x1 + x2) / 2, y - 10, "TOTAL NOTE")
    c.drawCentredString((x2 + x3) / 2, y - 10, f"{data['total_score']:.1f}")
    c.drawCentredString((x3 + x4) / 2, y - 10, f"{data['total_max']:.0f}")

    y -= 25

    # =========================
    # RÉSUMÉ
    # =========================
    summary_height = 45
    c.rect(left, y - summary_height + 8, width - 40, summary_height)

    c.setFont("Helvetica", 8)

    c.drawString(left + 6, y, f"Admis(e) : {data['admitted']}")
    c.drawString(left + 150, y, f"Rang : {data['rank']} sur {data['effectif']} élèves")

    y -= 12
    c.drawString(left + 6, y, f"Moyenne : {data['average']:.2f}")
    c.drawString(left + 150, y, f"Observation : {data['observation']}")

    y -= 12
    c.drawString(left + 6, y, f"Note max : {data['note_max']:.0f}")
    c.drawString(left + 150, y, f"Note min : {data['note_min']:.0f}")

    # Visa parents
    visa_w = 110
    visa_h = 34
    visa_x = right - visa_w
    visa_y = y - 38
    c.rect(visa_x, visa_y, visa_w, visa_h)
    c.drawCentredString(visa_x + visa_w / 2, visa_y + 14, "VISA DES PARENTS")

    # =========================
    # BAS DE PAGE
    # =========================
    y = 65
    c.setFont("Helvetica", 8)
    c.drawString(left, y, f"Titulaire : {data.get('titular_name') or '-'}")
    c.drawCentredString(width / 2, y, f"Lomé, le {datetime.today().strftime('%d/%m/%Y')}")
    c.drawRightString(right, y, "Le Directeur")

    c.showPage()
    c.save()

    return filename