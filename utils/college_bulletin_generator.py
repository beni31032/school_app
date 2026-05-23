import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.connection import get_connection
from utils.college_bulletin_service import get_college_bulletin_data

PRIMARY_BLUE = colors.HexColor("#1d4ed8")
PRIMARY_SLATE = colors.HexColor("#475569")
PRIMARY_BORDER = colors.HexColor("#cbd5e1")
PRIMARY_LIGHT = colors.HexColor("#eff6ff")
PRIMARY_LIGHT_ALT = colors.HexColor("#f8fafc")


def _safe_filename_part(value: str) -> str:
    return (
        (value or "")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _draw_page_header(c: canvas.Canvas, width: float, height: float, school_name: str, school_address: str, school_phone: str, school_email: str, school_logo: str, data: dict, compact: bool = False) -> float:
    left = 28
    right = width - 28
    top = height - 28
    block_h = 72 if not compact else 54

    c.setStrokeColor(PRIMARY_BLUE)
    c.setLineWidth(2)
    c.line(left, top + 4, right, top + 4)
    c.roundRect(left, top - block_h, right - left, block_h - 6, 10, fill=0, stroke=1)

    logo_size = 34 if compact else 42
    if school_logo and os.path.exists(school_logo):
        try:
            c.drawImage(
                school_logo,
                left + 10,
                top - 16 - logo_size,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.6 if compact else 9)
    c.drawString(left + 52, top - 10, "MINISTERE DES ENSEIGNEMENTS")
    c.drawString(left + 52, top - 21, "PRIMAIRE ET SECONDAIRE")
    c.drawRightString(right - 10, top - 10, "REPUBLIQUE TOGOLAISE")
    c.setFont("Helvetica", 7 if compact else 8)
    c.drawRightString(right - 10, top - 21, "Travail - Liberté - Patrie")

    c.setFont("Helvetica-Bold", 12 if not compact else 10)
    c.drawCentredString(width / 2, top - 18, school_name[:70])
    c.setFont("Helvetica", 7.4)
    c.drawCentredString(width / 2, top - 29, school_address[:90])
    c.drawCentredString(width / 2, top - 39, f"Tél: {school_phone} | Email: {school_email}"[:100])

    if compact:
        c.setFillColor(PRIMARY_LIGHT)
        c.roundRect(left, top - block_h - 24, right - left, 18, 8, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width / 2, top - block_h - 12, f"Bulletin de notes - Collège - suite | {data['student_name']}")
        return top - block_h - 32

    c.setFillColor(PRIMARY_LIGHT)
    c.roundRect(left, top - block_h - 38, right - left, 28, 8, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, top - block_h - 20, "BULLETIN DE NOTES - COLLEGE")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, top - block_h - 32, f"{data['term_name']}  |  {data['school_year_name']}")
    return top - block_h - 46


def _draw_subject_table_header(c: canvas.Canvas, x_positions: list[float], table_x: float, table_w: float, y: float, row_h: float) -> float:
    headers = ["MATIERE", "CLASSE", "COMPO", "MOY", "COEF", "NOTE DEF", "APPRECIATION"]
    c.setFillColor(PRIMARY_BLUE)
    c.setStrokeColor(PRIMARY_BORDER)
    c.rect(table_x, y - row_h, table_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7.2)

    for i, label in enumerate(headers):
        x1 = x_positions[i]
        x2 = x_positions[i + 1]
        c.setFillColor(colors.white)
        c.drawCentredString((x1 + x2) / 2, y - 11, label)
        c.setFillColor(colors.black)
        c.line(x2, y - row_h, x2, y)
    return y - row_h


def _draw_identity_cards(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    left = 28
    right = width - 28
    gap = 10
    total_w = right - left
    left_w = total_w * 0.58
    right_w = total_w - left_w - gap
    block_h = 50

    c.setStrokeColor(PRIMARY_BORDER)
    c.roundRect(left, y - block_h, left_w, block_h, 8, fill=0, stroke=1)
    c.roundRect(left + left_w + gap, y - block_h, right_w, block_h, 8, fill=0, stroke=1)

    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(left + 10, y - 12, f"N° bulletin : {data['bulletin_number']}")
    c.drawString(left + 10, y - 25, f"Élève : {data['student_name']}")
    c.drawString(left + 10, y - 38, f"Matricule : {data['matricule'] or '-'}  |  Sexe : {data['gender']}")

    rx = left + left_w + gap + 10
    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(rx, y - 12, f"Classe : {data['class_name']}")
    c.drawString(rx, y - 25, f"Effectif : {data['effectif']}  (G: {data['boys']} / F: {data['girls']})")
    c.drawString(rx, y - 38, f"Professeur principal : {data['titular_name'] or '-'}")
    return y - block_h - 10


def _draw_summary_section(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    left = 28
    right = width - 28
    gap = 8
    card_h = 34
    total_w = right - left
    card_w = (total_w - (gap * 3)) / 4
    cards = [
        ("Moyenne générale", f"{data['general_average']:.2f}"),
        ("Rang trimestriel", f"{data['general_rank']} / {data['effectif']}"),
        ("Moyenne annuelle", f"{data['annual_average']:.2f}"),
        ("Rang annuel", f"{data['annual_rank']}"),
    ]
    x = left
    for title, value in cards:
        c.setStrokeColor(PRIMARY_BORDER)
        c.roundRect(x, y - card_h, card_w, card_h, 8, fill=0, stroke=1)
        c.setFont("Helvetica", 6.8)
        c.setFillColor(PRIMARY_SLATE)
        c.drawCentredString(x + card_w / 2, y - 10, title)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawCentredString(x + card_w / 2, y - 23, value)
        x += card_w + gap

    y -= card_h + 10
    line_h = 16
    box_h = 48
    c.setStrokeColor(PRIMARY_BORDER)
    c.roundRect(left, y - box_h, total_w, box_h, 8, fill=0, stroke=1)
    c.setFillColor(PRIMARY_LIGHT)
    c.roundRect(left + 1, y - 19, total_w - 2, 18, 8, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left + 10, y - 12, "Synthèse de la période")
    c.setFont("Helvetica", 8)
    c.drawString(left + 10, y - 28, f"Total coefficients : {data['total_coef']}   |   Total notes : {data['total_notes']:.2f}")
    c.drawString(left + 10, y - 42, f"Moyenne classe : {data['class_general_average']:.2f}   |   Max : {data['class_highest_average']:.2f}   |   Min : {data['class_lowest_average']:.2f}")
    return y - box_h - 8


def _draw_annual_section(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    left = 28
    right = width - 28
    total_w = right - left
    box_h = 44
    c.setStrokeColor(PRIMARY_BORDER)
    c.roundRect(left, y - box_h, total_w, box_h, 8, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left + 10, y - 12, "Suivi annuel")
    c.setFont("Helvetica", 8)
    c.drawString(left + 10, y - 26, f"T1 : {data['avg_trim_1']:.2f}   |   T2 : {data['avg_trim_2']:.2f}   |   T3 : {data['avg_trim_3']:.2f}")
    c.drawString(left + 10, y - 39, f"Observation annuelle : {data['annual_observation']}")
    return y - box_h - 10


def _draw_signatures(c: canvas.Canvas, width: float, y: float) -> None:
    left = 28
    right = width - 28
    gap = 14
    box_w = (right - left - gap) / 2
    box_h = 42

    c.setStrokeColor(PRIMARY_BORDER)
    c.roundRect(left, y - box_h, box_w, box_h, 8, fill=0, stroke=1)
    c.roundRect(left + box_w + gap, y - box_h, box_w, box_h, 8, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(left + box_w / 2, y - 12, "Visa des parents")
    c.drawCentredString(left + box_w + gap + box_w / 2, y - 12, "Le Directeur")
    c.setFont("Helvetica", 8)
    c.drawRightString(right, y - box_h - 12, f"Lomé, le {datetime.today().strftime('%d/%m/%Y')}")


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
    filename = (
        f"bulletins/college/"
        f"{_safe_filename_part(data['class_name'])}_"
        f"{_safe_filename_part(data['student_name'])}_"
        f"{_safe_filename_part(data['term_name'])}_"
        f"{_safe_filename_part(data['school_year_name'])}_"
        f"{data['student_id']}.pdf"
    )

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    left = 28
    right = width - 28
    y = _draw_page_header(c, width, height, school_name, school_address, school_phone, school_email, school_logo, data, compact=False)
    y = _draw_identity_cards(c, width, y, data)

    table_x = left
    table_w = right - left
    row_h = 16

    cols = [220, 52, 52, 52, 42, 52, 69]
    x_positions = [table_x]
    for col_w in cols:
        x_positions.append(x_positions[-1] + col_w)

    y = _draw_subject_table_header(c, x_positions, table_x, table_w, y, row_h)
    c.setFont("Helvetica", 7.4)

    for index, subject in enumerate(data["subjects"]):
        if y < 120:
            c.showPage()
            y = _draw_page_header(c, width, height, school_name, school_address, school_phone, school_email, school_logo, data, compact=True)
            y = _draw_subject_table_header(c, x_positions, table_x, table_w, y, row_h)
            c.setFont("Helvetica", 7.4)

        if index % 2 == 0:
            c.setFillColor(PRIMARY_LIGHT_ALT)
            c.rect(table_x, y - row_h, table_w, row_h, fill=1, stroke=0)
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
    y = _draw_summary_section(c, width, y, data)
    y = _draw_annual_section(c, width, y, data)
    _draw_signatures(c, width, y)
    c.save()
    return filename
