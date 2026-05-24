import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.connection import get_connection
from utils.lycee_bulletin_service import get_lycee_bulletin_data

PRIMARY_BLUE = colors.HexColor("#1d4ed8")
PRIMARY_SLATE = colors.HexColor("#475569")
PRIMARY_BORDER = colors.HexColor("#cbd5e1")
PRIMARY_LIGHT_ALT = colors.HexColor("#f8fafc")


def _safe_filename_part(value: str) -> str:
    return (
        (value or "")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def _get_term_index(term_name: str) -> int:
    normalized = (term_name or "").strip().lower()
    if "3" in normalized or "troisi" in normalized:
        return 3
    if "2" in normalized or "deuxi" in normalized:
        return 2
    return 1


def _get_observation_label(avg: float) -> str:
    if avg >= 16:
        return "Très bien"
    if avg >= 14:
        return "Bien"
    if avg >= 12:
        return "Assez bien"
    if avg >= 10:
        return "Passable"
    return "Insuffisant"


def _resolve_photo_path(photo_path: str | None) -> str | None:
    if not photo_path:
        return None
    normalized = photo_path.replace("\\", "/")
    absolute_path = normalized if os.path.isabs(normalized) else os.path.abspath(normalized)
    if os.path.exists(absolute_path):
        return absolute_path
    return None


def _draw_page_header(
    c: canvas.Canvas,
    width: float,
    height: float,
    school_name: str,
    school_address: str,
    school_phone: str,
    school_email: str,
    school_logo: str,
    data: dict,
    compact: bool = False,
) -> float:
    left = 28
    right = width - 28
    top = height - 28

    c.setStrokeColor(PRIMARY_BLUE)
    c.setLineWidth(2)
    c.line(left, top + 4, right, top + 4)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.6 if compact else 9)
    c.drawString(left, top - 10, "MINISTERE DE")
    c.drawString(left, top - 21, "L'EDUCATION NATIONALE")
    c.drawRightString(right - 10, top - 10, "REPUBLIQUE TOGOLAISE")
    c.setFont("Helvetica", 7 if compact else 8)
    c.drawRightString(right - 10, top - 21, "Travail - Liberté - Patrie")

    logo_size = 28 if compact else 38
    center_logo_drawn = False
    if school_logo and os.path.exists(school_logo):
        try:
            c.drawImage(
                school_logo,
                (width - logo_size) / 2,
                top - 14 - logo_size,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )
            center_logo_drawn = True
        except Exception:
            center_logo_drawn = False

    c.setFont("Helvetica-Bold", 12 if not compact else 10)
    if center_logo_drawn:
        c.drawCentredString(width / 2, top - 18 - logo_size, school_name[:70])
    else:
        c.drawCentredString(width / 2, top - 18, school_name[:70])

    c.setFont("Helvetica", 7.4)
    address_y = top - 31 - logo_size if center_logo_drawn else top - 29
    contact_y = top - 41 - logo_size if center_logo_drawn else top - 39
    c.drawCentredString(width / 2, address_y, school_address[:90])
    c.drawCentredString(width / 2, contact_y, f"Tél: {school_phone} | Email: {school_email}"[:100])

    title_top_y = contact_y - (14 if compact else 22)
    subtitle_y = title_top_y - (11 if compact else 14)

    if compact:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(width / 2, title_top_y, f"Bulletin de notes - Lycée - suite | {data['student_name']}")
        return subtitle_y - 10

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, title_top_y, "BULLETIN DE NOTES - LYCEE")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, subtitle_y, f"{data['term_name']}  |  {data['school_year_name']}")
    return subtitle_y - 14


def _draw_subject_table_header(
    c: canvas.Canvas,
    x_positions: list[float],
    table_x: float,
    table_w: float,
    y: float,
    row_h: float,
) -> float:
    headers = ["MATIERES", "CLASSE", "COMPO", "MOY", "COEF", "NOTE DEF", "RANG", "APPRECIATION", "PROF."]
    c.setFillColor(colors.HexColor("#374151"))
    c.setStrokeColor(PRIMARY_BORDER)
    c.rect(table_x, y - row_h, table_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 6.9)

    for i, label in enumerate(headers):
        x1 = x_positions[i]
        x2 = x_positions[i + 1]
        c.setFillColor(colors.white)
        c.drawCentredString((x1 + x2) / 2, y - 11, label)
        c.setFillColor(colors.black)
        c.line(x2, y - row_h, x2, y)
    return y - row_h


def _draw_subject_group_row(
    c: canvas.Canvas,
    table_x: float,
    table_w: float,
    y: float,
    label: str,
    row_h: float,
) -> float:
    c.setStrokeColor(PRIMARY_BORDER)
    c.setFillColor(colors.HexColor("#d1d5db"))
    c.rect(table_x, y - row_h, table_w, row_h, fill=1, stroke=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-BoldOblique", 7.8)
    c.drawString(table_x + 6, y - 10.5, label)
    return y - row_h


def _draw_identity_cards(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    left = 28
    right = width - 28
    gap = 8
    total_w = right - left
    photo_w = 72
    info_total_w = total_w - photo_w - gap
    left_w = info_total_w * 0.57
    right_w = info_total_w - left_w - gap
    block_h = 52

    c.setStrokeColor(PRIMARY_BORDER)
    c.rect(left, y - block_h, left_w, block_h, fill=0, stroke=1)
    c.rect(left + left_w + gap, y - block_h, right_w, block_h, fill=0, stroke=1)
    photo_x = left + left_w + gap + right_w + gap
    c.rect(photo_x, y - block_h, photo_w, block_h, fill=0, stroke=1)

    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(left + 10, y - 12, f"N° bulletin : {data['bulletin_number']}")
    c.drawString(left + 10, y - 25, f"Élève : {data['student_name']}")
    c.drawString(left + 10, y - 38, f"Matricule : {data['matricule'] or '-'}  |  Sexe : {data['gender']}")

    rx = left + left_w + gap + 10
    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(rx, y - 12, f"Classe : {data['class_name']}")
    c.drawString(rx, y - 25, f"Effectif : {data['effectif']}  (G: {data['boys']} / F: {data['girls']})")
    c.drawString(rx, y - 38, f"Professeur principal : {data['titular_name'] or '-'}")

    resolved_photo_path = _resolve_photo_path(data.get("photo_path"))
    inner_margin = 7
    inner_x = photo_x + inner_margin
    inner_y = y - block_h + inner_margin
    inner_w = photo_w - (inner_margin * 2)
    inner_h = block_h - (inner_margin * 2) - 7
    if resolved_photo_path:
        try:
            c.drawImage(
                resolved_photo_path,
                inner_x,
                inner_y + 7,
                width=inner_w,
                height=inner_h,
                preserveAspectRatio=True,
                mask="auto",
                anchor="c",
            )
        except Exception:
            c.rect(inner_x, inner_y + 7, inner_w, inner_h, fill=0, stroke=1)
            c.setFont("Helvetica", 7)
            c.drawCentredString(photo_x + photo_w / 2, y - block_h + 8, "Photo")
    else:
        c.rect(inner_x, inner_y + 7, inner_w, inner_h, fill=0, stroke=1)
        c.setFont("Helvetica", 7)
        c.drawCentredString(photo_x + photo_w / 2, y - block_h + 8, "Photo")
    return y - block_h - 10


def _draw_summary_section(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    left = 28
    right = width - 28
    total_w = right - left
    term_index = _get_term_index(data.get("term_name") or "")
    is_third_term = term_index == 3
    top_h = 92 if is_third_term else 74
    bottom_h = 42
    gap = 8
    left_w = total_w * 0.25
    center_w = total_w * 0.36
    right_w = total_w - left_w - center_w - (gap * 2)

    lx = left
    cx = lx + left_w + gap
    rx = cx + center_w + gap

    c.setStrokeColor(PRIMARY_BORDER)
    c.rect(lx, y - top_h, left_w, top_h, fill=0, stroke=1)
    c.rect(cx, y - top_h, center_w, top_h, fill=0, stroke=1)
    c.rect(rx, y - top_h, right_w, top_h, fill=0, stroke=1)

    c.setFont("Helvetica", 7.6)
    left_rows = [
        ("Retards", ""),
        ("Absences", ""),
        ("Exclusions", ""),
        ("Tableau", ""),
        ("TH+Encouragement", ""),
        ("TH+Félicitation", ""),
    ]
    left_row_h = top_h / len(left_rows)
    for idx, (label, value) in enumerate(left_rows):
        row_top = y - (idx * left_row_h)
        row_bottom = row_top - left_row_h
        c.line(lx, row_bottom, lx + left_w, row_bottom)
        split_x = lx + (left_w * 0.62)
        c.line(split_x, row_bottom, split_x, row_top)
        c.drawString(lx + 4, row_top - 10, label)
        if value:
            c.drawString(split_x + 4, row_top - 10, value)

    center_rows: list[tuple[str, str, str]] = []
    if term_index >= 1:
        center_rows.append(("Moy. du 1er Trim.", f"{data['avg_trim_1']:.2f}", f"{data.get('rank_trim_1', 0)}e" if data.get("rank_trim_1", 0) else ""))
    if term_index >= 2:
        center_rows.append(("Moy. du 2e Trim.", f"{data['avg_trim_2']:.2f}", f"{data.get('rank_trim_2', 0)}e" if data.get("rank_trim_2", 0) else ""))
    if term_index >= 3:
        center_rows.append(("Moy. du 3e Trim.", f"{data['avg_trim_3']:.2f}", f"{data.get('rank_trim_3', data['general_rank'])}e"))
        center_rows.append(("Moyenne annuelle", f"{data['annual_average']:.2f}", f"{data['annual_rank']}e"))

    center_row_h = top_h / len(center_rows)
    label_w = center_w * 0.54
    value_w = center_w * 0.22
    rank_w = center_w - label_w - value_w
    for idx, (label, value, rank_value) in enumerate(center_rows):
        row_top = y - (idx * center_row_h)
        row_bottom = row_top - center_row_h
        c.line(cx, row_bottom, cx + center_w, row_bottom)
        c.line(cx + label_w, row_bottom, cx + label_w, row_top)
        c.line(cx + label_w + value_w, row_bottom, cx + label_w + value_w, row_top)
        c.drawString(cx + 4, row_top - 10, label)
        c.drawCentredString(cx + label_w + (value_w / 2), row_top - 10, value)
        if rank_value:
            c.drawCentredString(cx + label_w + value_w + (rank_w / 2), row_top - 10, rank_value)

    right_rows = [
        ("Avertissement", "Travail"),
        ("", "Discipline"),
        ("Blâme", "Travail"),
        ("", "Discipline"),
    ]
    right_row_h = top_h / len(right_rows)
    split_x = rx + (right_w * 0.56)
    for idx, (left_label, right_label) in enumerate(right_rows):
        row_top = y - (idx * right_row_h)
        row_bottom = row_top - right_row_h
        c.line(rx, row_bottom, rx + right_w, row_bottom)
        c.line(split_x, row_bottom, split_x, row_top)
        if left_label:
            c.drawString(rx + 4, row_top - 10, left_label)
        if right_label:
            c.drawString(split_x + 4, row_top - 10, right_label)

    y -= top_h + 6
    c.rect(left, y - bottom_h, total_w, bottom_h, fill=0, stroke=1)
    half_x = left + (total_w / 2)
    c.line(half_x, y - bottom_h, half_x, y)
    c.line(left, y - 14, right, y - 14)
    c.line(left, y - 28, right, y - 28)

    c.setFont("Helvetica", 7.6)
    c.drawString(left + 6, y - 10, "Moy. la plus forte de la classe")
    c.drawRightString(half_x - 6, y - 10, f"{data['class_highest_average']:.2f}")
    c.drawString(half_x + 6, y - 10, "Moy. générale de la classe")
    c.drawRightString(right - 6, y - 10, f"{data['class_general_average']:.2f}")

    c.drawString(left + 6, y - 24, "Moy. la plus faible de la classe")
    c.drawRightString(half_x - 6, y - 24, f"{data['class_lowest_average']:.2f}")
    c.drawString(half_x + 6, y - 24, "Bonus facultatives")
    c.drawRightString(right - 6, y - 24, f"+{data['optional_bonus']}" if data.get("optional_bonus", 0) > 0 else "-")

    if is_third_term:
        c.drawString(left + 6, y - 38, "Moy. annuelle la plus forte")
        c.drawRightString(half_x - 6, y - 38, "-")
        c.drawString(half_x + 6, y - 38, "Moy. annuelle la plus faible")
        c.drawRightString(right - 6, y - 38, "-")
    else:
        c.drawString(left + 6, y - 38, "Observation du trimestre")
        c.drawRightString(right - 6, y - 38, _get_observation_label(float(data["general_average"])))

    return y - bottom_h - 8


def _draw_annual_section(c: canvas.Canvas, width: float, y: float, data: dict) -> float:
    is_third_term = _get_term_index(data.get("term_name") or "") == 3
    if not is_third_term:
        return y

    left = 28
    right = width - 28
    total_w = right - left
    box_h = 52
    c.setStrokeColor(PRIMARY_BORDER)
    c.rect(left, y - box_h, total_w, box_h, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#e5e7eb"))
    c.rect(left, y - 16, total_w, 16, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left + 8, y - 11, "Suivi annuel")
    c.setFont("Helvetica", 8)
    thirds = total_w / 3
    c.drawCentredString(left + thirds * 0.5, y - 30, f"T1 : {data['avg_trim_1']:.2f}")
    c.drawCentredString(left + thirds * 1.5, y - 30, f"T2 : {data['avg_trim_2']:.2f}")
    c.drawCentredString(left + thirds * 2.5, y - 30, f"T3 : {data['avg_trim_3']:.2f}")
    c.line(left + thirds, y - 40, left + thirds, y - 18)
    c.line(left + thirds * 2, y - 40, left + thirds * 2, y - 18)
    c.drawString(left + 8, y - 45, f"Observation annuelle : {data['annual_observation']}")
    return y - box_h - 10


def _draw_signatures(c: canvas.Canvas, width: float, y: float) -> None:
    left = 28
    right = width - 28
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left, y - 4, "Visa des parents")
    c.drawCentredString(width / 2, y - 4, f"Lomé, le {datetime.today().strftime('%d/%m/%Y')}")
    c.drawRightString(right, y - 4, "Le Directeur")


def generate_lycee_bulletin(student_id: int, term_id: int) -> str:
    data = get_lycee_bulletin_data(student_id, term_id)

    conn = get_connection()
    if not conn:
        raise Exception("Connexion base impossible")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(si.name, e.name),
                COALESCE(si.address, e.address, ''),
                COALESCE(si.phone, e.phone, ''),
                COALESCE(si.email, ''),
                COALESCE(si.logo_path, '')
            FROM classes c
            JOIN establishments e ON e.id = c.establishment_id
            LEFT JOIN school_info si ON TRUE
            WHERE c.id = %s
            ORDER BY si.id
            LIMIT 1
            """,
            (data["class_id"],),
        )
        school = cursor.fetchone()
    finally:
        conn.close()

    school_name = school[0] if school else "École"
    school_address = school[1] if school else ""
    school_phone = school[2] if school else ""
    school_email = school[3] if school else ""
    school_logo = school[4] if school else ""

    os.makedirs("bulletins/lycee", exist_ok=True)
    filename = (
        f"bulletins/lycee/"
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

    cols = [140, 43, 43, 43, 32, 44, 32, 86, 76]
    x_positions = [table_x]
    for col_w in cols:
        x_positions.append(x_positions[-1] + col_w)

    y = _draw_subject_table_header(c, x_positions, table_x, table_w, y, row_h)
    c.setFont("Helvetica", 7.4)

    mandatory_subjects = [subject for subject in data["subjects"] if not subject.get("is_optional")]
    optional_subjects = [subject for subject in data["subjects"] if subject.get("is_optional")]

    sections: list[tuple[str, list[dict]]] = [("Matières obligatoires", mandatory_subjects)]
    if optional_subjects:
        sections.append(("Matières facultatives", optional_subjects))

    row_index = 0
    for section_idx, (section_label, section_subjects) in enumerate(sections):
        if section_idx > 0:
            y -= 6
        if y < 140:
            c.showPage()
            y = _draw_page_header(c, width, height, school_name, school_address, school_phone, school_email, school_logo, data, compact=True)
            y = _draw_subject_table_header(c, x_positions, table_x, table_w, y, row_h)
            c.setFont("Helvetica", 7.4)
        y = _draw_subject_group_row(c, table_x, table_w, y, section_label, 13)

        for subject in section_subjects:
            if y < 120:
                c.showPage()
                y = _draw_page_header(c, width, height, school_name, school_address, school_phone, school_email, school_logo, data, compact=True)
                y = _draw_subject_table_header(c, x_positions, table_x, table_w, y, row_h)
                c.setFont("Helvetica", 7.4)
                y = _draw_subject_group_row(c, table_x, table_w, y, section_label, 13)

            if row_index % 2 == 0:
                c.setFillColor(PRIMARY_LIGHT_ALT)
                c.rect(table_x, y - row_h, table_w, row_h, fill=1, stroke=0)
            c.rect(table_x, y - row_h, table_w, row_h, fill=0, stroke=1)
            for x in x_positions[1:-1]:
                c.line(x, y - row_h, x, y)

            c.setFillColor(colors.black)
            c.drawString(x_positions[0] + 3, y - 11, subject["subject_name"][:28])
            c.drawCentredString((x_positions[1] + x_positions[2]) / 2, y - 11, f"{subject['classe_note']:.2f}")
            c.drawCentredString((x_positions[2] + x_positions[3]) / 2, y - 11, f"{subject['compo_note']:.2f}")
            c.drawCentredString((x_positions[3] + x_positions[4]) / 2, y - 11, f"{subject['moy_trim']:.2f}")
            c.drawCentredString((x_positions[4] + x_positions[5]) / 2, y - 11, str(subject["coefficient"]))
            c.drawCentredString((x_positions[5] + x_positions[6]) / 2, y - 11, f"{subject['note_def']:.2f}")
            c.drawCentredString((x_positions[6] + x_positions[7]) / 2, y - 11, str(subject["rang"]))
            c.drawCentredString((x_positions[7] + x_positions[8]) / 2, y - 11, subject["appreciation"][:14])
            c.drawString(x_positions[8] + 3, y - 11, subject["teacher_name"][:18])

            y -= row_h
            row_index += 1

    if optional_subjects and data.get("optional_bonus", 0) > 0:
        bonus_row_h = 14
        c.setFillColor(colors.white)
        c.rect(table_x, y - bonus_row_h, table_w, bonus_row_h, fill=1, stroke=1)
        c.line(x_positions[1], y - bonus_row_h, x_positions[1], y)
        c.line(x_positions[5], y - bonus_row_h, x_positions[5], y)
        c.line(x_positions[6], y - bonus_row_h, x_positions[6], y)
        c.setFont("Helvetica-Bold", 7.4)
        c.setFillColor(colors.black)
        c.drawString(x_positions[0] + 3, y - 10, "Bonus facultatives")
        c.drawCentredString((x_positions[5] + x_positions[6]) / 2, y - 10, f"+{data['optional_bonus']}")
        y -= bonus_row_h

    total_row_h = 15
    c.setFillColor(colors.white)
    c.rect(table_x, y - total_row_h, table_w, total_row_h, fill=1, stroke=1)
    c.line(x_positions[1], y - total_row_h, x_positions[1], y)
    c.line(x_positions[4], y - total_row_h, x_positions[4], y)
    c.line(x_positions[5], y - total_row_h, x_positions[5], y)
    c.line(x_positions[6], y - total_row_h, x_positions[6], y)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(x_positions[0] + 3, y - 10, "Total definitif")
    c.drawCentredString((x_positions[4] + x_positions[5]) / 2, y - 10, str(data["total_coef"]))
    c.drawCentredString((x_positions[5] + x_positions[6]) / 2, y - 10, f"{data['total_notes']:.2f}")

    y -= total_row_h + 10
    y = _draw_summary_section(c, width, y, data)
    y = _draw_annual_section(c, width, y, data)
    _draw_signatures(c, width, y)
    c.save()
    return filename
