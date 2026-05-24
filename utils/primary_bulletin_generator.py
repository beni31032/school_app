import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas

from database.connection import get_connection
from utils.primary_bulletin_service import get_primary_bulletin_data


PRIMARY_BLUE = colors.HexColor("#374151")
PRIMARY_SLATE = colors.HexColor("#111827")
PRIMARY_BORDER = colors.HexColor("#6b7280")
PRIMARY_LIGHT = colors.HexColor("#f3f4f6")
PRIMARY_LIGHT_ALT = colors.HexColor("#f9fafb")
PRIMARY_SUCCESS = colors.HexColor("#16a34a")
PRIMARY_DANGER = colors.HexColor("#dc2626")


def _safe_filename_part(value: str) -> str:
    return (
        (value or "")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _draw_school_header(c: canvas.Canvas, width: float, height: float, school_name: str, school_address: str, school_phone: str, school_email: str, school_logo: str) -> float:
    left = 18
    right = width - 18
    top = height - 16

    c.setStrokeColor(PRIMARY_BLUE)
    c.setLineWidth(2)
    c.line(left, top, right, top)

    header_y = top - 10

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(left, header_y, "MINISTERE DE")
    c.drawString(left, header_y - 9, "L'EDUCATION NATIONALE")

    c.drawRightString(right, header_y, "REPUBLIQUE TOGOLAISE")
    c.setFont("Helvetica", 6.4)
    c.drawRightString(right, header_y - 9, "Travail - Liberté - Patrie")

    center_logo_drawn = False
    if school_logo and os.path.exists(school_logo):
        try:
            logo_size = 34
            c.drawImage(
                school_logo,
                (width - logo_size) / 2,
                header_y - 34,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )
            center_logo_drawn = True
        except Exception:
            center_logo_drawn = False

    c.setFont("Helvetica-Bold", 10)
    if center_logo_drawn:
        c.drawCentredString(width / 2, header_y - 41, school_name[:60])
    else:
        c.drawCentredString(width / 2, header_y - 6, school_name[:60])
    c.setFont("Helvetica", 6.5)
    address_y = header_y - 50 if center_logo_drawn else header_y - 16
    contact_y = header_y - 59 if center_logo_drawn else header_y - 25
    c.drawCentredString(width / 2, address_y, school_address[:72])
    c.drawCentredString(width / 2, contact_y, f"Tél : {school_phone} | Email : {school_email}"[:90])

    return contact_y - 11


def _draw_title_banner(c: canvas.Canvas, width: float, y: float, term_name: str, school_year_name: str) -> float:
    banner_h = 26
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y - 13, "Bulletin d'évaluation")
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(width / 2, y - 24, f"{term_name}  |  {school_year_name}")
    return y - banner_h - 8


def _draw_identity_block(c: canvas.Canvas, width: float, y: float, data: dict, total: int, boys: int, girls: int, numero: int) -> float:
    left = 20
    block_h = 64
    photo_w = 42
    photo_h = 44
    photo_x = width - 24 - photo_w
    photo_y = y - block_h + 10

    c.setStrokeColor(PRIMARY_BORDER)
    c.setLineWidth(1)
    c.rect(left, y - block_h, width - 40, block_h, fill=0, stroke=1)
    c.setFillColor(PRIMARY_LIGHT_ALT)
    c.rect(left + 1, y - 22, width - 42, 21, fill=1, stroke=0)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left + 8, y - 14, f"N° {numero}")

    c.setFont("Helvetica", 8)
    c.drawString(left + 8, y - 31, f"Nom et prénom(s) : {data['student_name']}")
    c.drawString(left + 8, y - 43, f"Sexe : {data['gender']}")
    c.drawString(left + 8, y - 55, f"Classe : {data['class_name']}")

    c.drawString(photo_x - 92, y - 31, f"Effectif : {total}")
    c.drawString(photo_x - 92, y - 43, f"Garçons : {boys}")
    c.drawString(photo_x - 92, y - 55, f"Filles : {girls}")

    c.setStrokeColor(PRIMARY_SLATE)
    c.rect(photo_x, photo_y, photo_w, photo_h)
    photo_path = data.get("photo_path")
    drawn = False
    if photo_path:
        normalized = photo_path.replace("\\", "/")
        absolute_path = normalized if os.path.isabs(normalized) else os.path.abspath(normalized)
        if os.path.exists(absolute_path):
            try:
                c.drawImage(
                    absolute_path,
                    photo_x + 1.5,
                    photo_y + 1.5,
                    width=photo_w - 3,
                    height=photo_h - 3,
                    preserveAspectRatio=True,
                    mask="auto",
                    anchor="c",
                )
                drawn = True
            except Exception:
                drawn = False

    c.setFont("Helvetica", 6.3)
    if not drawn:
        c.drawCentredString(photo_x + photo_w / 2, y - 60, "Photo")

    return y - block_h - 8


def _draw_table(c: canvas.Canvas, width: float, y: float, data: dict) -> tuple[float, float]:
    left = 20
    table_w = width - 40
    row_h = 14
    col_disc = 210
    col_note = 44
    col_sur = table_w - col_disc - col_note

    x1 = left
    x2 = left + col_disc
    x3 = x2 + col_note
    x4 = left + table_w

    c.setFillColor(PRIMARY_BLUE)
    c.rect(left, y - row_h, table_w, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.3)
    c.drawString(x1 + 5, y - 10, "DISCIPLINES")
    c.drawCentredString((x2 + x3) / 2, y - 10, "NOTES")
    c.drawCentredString((x3 + x4) / 2, y - 10, "SUR")
    c.setStrokeColor(PRIMARY_BORDER)
    c.rect(left, y - row_h, table_w, row_h, fill=0, stroke=1)
    c.line(x2, y - row_h, x2, y)
    c.line(x3, y - row_h, x3, y)

    y -= row_h
    c.setFont("Helvetica", 7.2)
    for idx, subject in enumerate(data["subjects"]):
        if idx % 2 == 0:
            c.setFillColor(PRIMARY_LIGHT_ALT)
            c.rect(left, y - row_h, table_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(PRIMARY_BORDER)
        c.rect(left, y - row_h, table_w, row_h, fill=0, stroke=1)
        c.line(x2, y - row_h, x2, y)
        c.line(x3, y - row_h, x3, y)

        c.setFillColor(colors.black)
        c.drawString(x1 + 5, y - 10, subject["subject_name"][:42])
        c.drawCentredString((x2 + x3) / 2, y - 10, f"{subject['score']:.1f}")
        c.drawCentredString((x3 + x4) / 2, y - 10, f"{subject['max_score']:.0f}")
        y -= row_h

    c.setFillColor(PRIMARY_LIGHT)
    c.rect(left, y - row_h, table_w, row_h, fill=1, stroke=0)
    c.setStrokeColor(PRIMARY_BLUE)
    c.setLineWidth(1)
    c.rect(left, y - row_h, table_w, row_h, fill=0, stroke=1)
    c.line(x2, y - row_h, x2, y)
    c.line(x3, y - row_h, x3, y)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7.7)
    c.drawCentredString((x1 + x2) / 2, y - 10, "TOTAL NOTE")
    c.drawCentredString((x2 + x3) / 2, y - 10, f"{data['total_score']:.1f}")
    c.drawCentredString((x3 + x4) / 2, y - 10, f"{data['total_max']:.0f}")
    y -= row_h
    return y, row_h


def _draw_summary_cards(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    return y


def _draw_observation_and_signatures(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    left = 20
    right = width - 20
    summary_h = 46

    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(left, y - summary_h, width - 40, summary_h)

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.black)
    c.drawString(left + 6, y - 12, f"Admis(e) : {data['admitted']}")
    c.drawString(left + 140, y - 12, f"Rang : {data['rank']} sur {data['effectif']} élèves")

    c.drawString(left + 6, y - 26, f"Moyenne : {data['average']:.2f}")
    c.drawString(left + 140, y - 26, f"Observation : {data['observation']}")

    c.drawString(left + 6, y - 40, f"Note max : {data['note_max']:.0f}")
    c.drawString(left + 140, y - 40, f"Note min : {data['note_min']:.0f}")

    visa_w = 116
    visa_h = 28
    visa_x = right - visa_w
    visa_y = y - summary_h - visa_h - 2
    c.rect(visa_x, visa_y, visa_w, visa_h)
    c.setFont("Helvetica", 8)
    c.drawCentredString(visa_x + visa_w / 2, visa_y + 11, "VISA DES PARENTS")

    footer_y = visa_y - 26
    c.drawString(left, footer_y, f"Titulaire : {data['titular_name'] or '-'}")
    c.drawCentredString(width / 2, footer_y, f"Lomé, le {datetime.today().strftime('%d/%m/%Y')}")
    c.drawRightString(right, footer_y, "Le Directeur")
    return footer_y


def generate_primary_bulletin(student_id: int, term_id: int) -> str:
    data = get_primary_bulletin_data(student_id, term_id)

    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(si.name, e.name),
                COALESCE(e.address, si.address, ''),
                COALESCE(e.phone, si.phone, ''),
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

        school_name = school[0] if school else "École"
        school_address = school[1] if school else ""
        school_phone = school[2] if school else ""
        school_email = school[3] if school else ""
        school_logo = school[4] if school else ""

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE gender = 'M') AS boys,
                COUNT(*) FILTER (WHERE gender = 'F') AS girls
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            WHERE e.class_id = %s
              AND e.school_year_id = (
                    SELECT school_year_id
                    FROM terms
                    WHERE id = %s
              )
              AND s.is_active = TRUE
            """,
            (data["class_id"], term_id)
        )
        total, boys, girls = cursor.fetchone()
    finally:
        conn.close()

    numero = data["rank"]

    os.makedirs("bulletins/primary", exist_ok=True)
    filename = (
        f"bulletins/primary/"
        f"{_safe_filename_part(data['class_name'])}_"
        f"{_safe_filename_part(data['student_name'])}_"
        f"{_safe_filename_part(data['term_name'])}_"
        f"{_safe_filename_part(data['school_year_name'])}_"
        f"{data['student_id']}.pdf"
    )

    c = canvas.Canvas(filename, pagesize=A5)
    width, height = A5

    y = _draw_school_header(c, width, height, school_name, school_address, school_phone, school_email, school_logo)
    y = _draw_title_banner(c, width, y, data["term_name"], data["school_year_name"])
    y = _draw_identity_block(c, width, y, data, total or 0, boys or 0, girls or 0, numero)
    y, _ = _draw_table(c, width, y, data)
    y -= 8
    y = _draw_summary_cards(c, width, y, data)
    _draw_observation_and_signatures(c, width, y, data)

    c.save()
    return filename
