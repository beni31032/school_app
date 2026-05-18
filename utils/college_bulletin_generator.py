import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.connection import get_connection
from utils.college_bulletin_service import get_college_bulletin_data


def generate_college_bulletin(student_id: int, term_id: int) -> str:
    data = get_college_bulletin_data(student_id, term_id)

    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                e.name,
                COALESCE(e.address, ''),
                COALESCE(e.phone, ''),
                COALESCE(si.email, ''),
                COALESCE(si.logo_path, '')
            FROM classes c
            JOIN establishments e ON e.id = c.establishment_id
            LEFT JOIN school_info si ON TRUE
            WHERE c.id = %s
            ORDER BY si.id
            LIMIT 1
            """,
            (data["class_id"],)
        )
        school = cursor.fetchone()
    finally:
        conn.close()

    school_name = school[0] if school else "École"
    school_address = school[1] if school else ""
    school_phone = school[2] if school else ""
    school_email = school[3] if school else ""
    school_logo = school[4] if school else ""

    os.makedirs("bulletins/college", exist_ok=True)
    filename = f"bulletins/college/{data['student_name'].replace(' ', '_')}_{data['term_name'].replace(' ', '_')}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    left = 28
    right = width - 28
    y = height - 28

    if school_logo and os.path.exists(school_logo):
        try:
            c.drawImage(school_logo, left, y - 24, width=42, height=42, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "MINISTERE DES ENSEIGNEMENTS")
    y -= 11
    c.drawString(left, y, "PRIMAIRE ET SECONDAIRE")
    c.drawRightString(right, y + 11, "REPUBLIQUE TOGOLAISE")
    c.setFont("Helvetica", 8)
    c.drawRightString(right, y, "Travail - Liberté - Patrie")

    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, y, school_name)
    y -= 10
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, school_address)
    y -= 10
    c.drawCentredString(width / 2, y, f"Tél: {school_phone} | Email: {school_email}")

    y -= 16
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "BULLETIN DE NOTES - COLLEGE")
    y -= 12
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, y, f"{data['term_name']} - {data['school_year_name']}")

    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(left, y, f"N° bulletin: {data['bulletin_number']}")
    c.drawString(left + 170, y, f"Matricule: {data['matricule'] or '-'}")
    c.drawRightString(right, y, f"Classe: {data['class_name']}")

    y -= 12
    c.drawString(left, y, f"Élève: {data['student_name']}")
    c.drawRightString(right, y, f"Sexe: {data['gender']}")

    y -= 12
    c.drawString(left, y, f"Professeur principal: {data['titular_name'] or '-'}")
    c.drawRightString(right, y, f"Effectif: {data['effectif']} (G: {data['boys']} / F: {data['girls']})")

    y -= 18
    table_x = left
    table_w = right - left
    row_h = 16

    cols = [220, 52, 52, 52, 42, 52, 69]
    headers = ["MATIERE", "CLASSE", "COMPO", "MOY", "COEF", "NOTE DEF", "APPRECIATION"]

    x_positions = [table_x]
    for col_w in cols:
        x_positions.append(x_positions[-1] + col_w)

    c.setFillColor(colors.lightgrey)
    c.rect(table_x, y - row_h, table_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7.2)

    for i, label in enumerate(headers):
        x1 = x_positions[i]
        x2 = x_positions[i + 1]
        c.drawCentredString((x1 + x2) / 2, y - 11, label)
        c.line(x2, y - row_h, x2, y)

    y -= row_h
    c.setFont("Helvetica", 7.4)

    for subject in data["subjects"]:
        if y < 120:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 7.4)

        c.rect(table_x, y - row_h, table_w, row_h, fill=0, stroke=1)
        for x in x_positions[1:-1]:
            c.line(x, y - row_h, x, y)

        c.drawString(x_positions[0] + 3, y - 11, subject["subject_name"][:44])
        c.drawCentredString((x_positions[1] + x_positions[2]) / 2, y - 11, f"{subject['classe_note']:.2f}")
        c.drawCentredString((x_positions[2] + x_positions[3]) / 2, y - 11, f"{subject['compo_note']:.2f}")
        c.drawCentredString((x_positions[3] + x_positions[4]) / 2, y - 11, f"{subject['moy_trim']:.2f}")
        c.drawCentredString((x_positions[4] + x_positions[5]) / 2, y - 11, str(subject["coefficient"]))
        c.drawCentredString((x_positions[5] + x_positions[6]) / 2, y - 11, f"{subject['note_def']:.2f}")
        c.drawCentredString((x_positions[6] + x_positions[7]) / 2, y - 11, subject["appreciation"][:12])

        y -= row_h

    y -= 10
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, f"Total coefficients: {data['total_coef']}")
    c.drawString(left + 150, y, f"Total notes: {data['total_notes']:.2f}")
    c.drawRightString(right, y, f"Moyenne générale: {data['general_average']:.2f}")

    y -= 12
    c.setFont("Helvetica", 9)
    c.drawString(left, y, f"Rang trimestriel: {data['general_rank']} / {data['effectif']}")
    c.drawString(left + 180, y, f"Moyenne classe: {data['class_general_average']:.2f}")
    c.drawRightString(right, y, f"Max: {data['class_highest_average']:.2f} | Min: {data['class_lowest_average']:.2f}")

    y -= 14
    c.drawString(left, y, f"Moy T1: {data['avg_trim_1']:.2f} | Moy T2: {data['avg_trim_2']:.2f} | Moy T3: {data['avg_trim_3']:.2f}")
    c.drawRightString(right, y, f"Moy annuelle: {data['annual_average']:.2f} | Rang annuel: {data['annual_rank']}")

    y -= 14
    c.drawString(left, y, f"Observation annuelle: {data['annual_observation']}")

    y -= 32
    c.drawString(left, y, "Visa des parents")
    c.drawRightString(right, y, f"Lomé, le {datetime.today().strftime('%d/%m/%Y')}")
    c.drawRightString(right, y - 30, "Le Directeur")

    c.showPage()
    c.save()
    return filename
