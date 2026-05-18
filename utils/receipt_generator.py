import os
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from database.connection import get_connection


PAGE_WIDTH, PAGE_HEIGHT = A5
LEFT_MARGIN = 22
RIGHT_MARGIN = PAGE_WIDTH - 22
TOP_MARGIN = PAGE_HEIGHT - 22
PRIMARY = colors.HexColor("#1d4ed8")
PRIMARY_SOFT = colors.HexColor("#dbeafe")
INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#cbd5e1")
INFO_BG = colors.HexColor("#eff6ff")
SUCCESS_BG = colors.HexColor("#ecfdf5")
SUCCESS_FG = colors.HexColor("#047857")
WARNING_BG = colors.HexColor("#fff7ed")
WARNING_FG = colors.HexColor("#c2410c")
NEUTRAL_BG = colors.HexColor("#f8fafc")


def _format_money(value) -> str:
    return f"{int(float(value or 0)):,.0f} FCFA".replace(",", " ")


def _format_date(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _draw_round_rect(c: canvas.Canvas, x, y, w, h, fill_color=colors.white, stroke_color=BORDER, radius=10):
    c.setFillColor(fill_color)
    c.setStrokeColor(stroke_color)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def _draw_label_value(c: canvas.Canvas, x, y, label: str, value: str, label_width=62):
    c.setFont("Helvetica-Bold", 7.8)
    c.setFillColor(MUTED)
    c.drawString(x, y, label)
    c.setFont("Helvetica", 8.2)
    c.setFillColor(INK)
    c.drawString(x + label_width, y, value or "-")


def _draw_section_title(c: canvas.Canvas, x, y, title: str):
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(x, y, title)


def _draw_fit_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, start_size: float, min_size: float = 6.4):
    content = text or "-"
    size = start_size
    while size >= min_size and stringWidth(content, "Helvetica-Bold", size) > max_width:
        size -= 0.2
    c.setFont("Helvetica-Bold", max(size, min_size))
    c.drawString(x, y, content)


def _draw_fit_text_multiline(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    start_size: float,
    min_size: float = 6.8,
    max_lines: int = 2,
    line_gap: float = 10,
):
    content = (text or "-").strip()
    words = content.split()
    if not words:
        words = ["-"]

    size = start_size
    chosen_lines = [content]

    while size >= min_size:
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if stringWidth(test, "Helvetica-Bold", size) <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        if len(lines) <= max_lines:
            chosen_lines = lines
            break
        size -= 0.2

    c.setFont("Helvetica-Bold", max(size, min_size))
    for index, line in enumerate(chosen_lines[:max_lines]):
        c.drawString(x, y - (index * line_gap), line)


def _get_school_identity(cursor, establishment_id):
    school_name = "École"
    address = ""
    phone = ""
    email = ""
    logo_path = ""

    if establishment_id is not None:
        cursor.execute(
            """
            SELECT name, COALESCE(address, ''), COALESCE(phone, '')
            FROM establishments
            WHERE id = %s
            """,
            (establishment_id,),
        )
        row = cursor.fetchone()
        if row:
            school_name, address, phone = row

    cursor.execute(
        """
        SELECT COALESCE(email, ''), COALESCE(logo_path, '')
        FROM school_info
        ORDER BY id
        LIMIT 1
        """
    )
    info_row = cursor.fetchone()
    if info_row:
        email = info_row[0] or ""
        logo_path = info_row[1] or ""

    return school_name, address, phone, email, logo_path


def _draw_header(c: canvas.Canvas, school_name: str, address: str, phone: str, email: str, logo_path: str, receipt_number: str):
    header_h = 58
    header_y = TOP_MARGIN - 64
    _draw_round_rect(c, LEFT_MARGIN, header_y, RIGHT_MARGIN - LEFT_MARGIN, header_h, fill_color=colors.white, radius=8)

    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(
                logo_path,
                LEFT_MARGIN + 8,
                header_y + 8,
                width=38,
                height=38,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    badge_w = 108
    badge_x = RIGHT_MARGIN - badge_w - 8
    badge_y = header_y + 11
    text_x = LEFT_MARGIN + 52
    text_max_width = badge_x - text_x - 8

    c.setFillColor(INK)
    _draw_fit_text_multiline(c, school_name or "École", text_x, header_y + 42, text_max_width, 10.0, 7.0, max_lines=2, line_gap=10)
    c.setFont("Helvetica", 6.8)
    c.setFillColor(MUTED)
    c.drawString(text_x, header_y + 23, (address or "-")[:48])
    c.drawString(text_x, header_y + 13, f"Tél : {(phone or '-')[:28]}")
    c.drawString(text_x, header_y + 3, f"Email : {(email or '-')[:32]}")

    _draw_round_rect(c, badge_x, badge_y, badge_w, 32, fill_color=PRIMARY_SOFT, stroke_color=PRIMARY, radius=10)
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(badge_x + badge_w / 2, badge_y + 21, "REÇU DE PAIEMENT")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.4)
    c.drawCentredString(badge_x + badge_w / 2, badge_y + 9, receipt_number[:20])


def _draw_identity_block(c: canvas.Canvas, y_top: float, school_year_name: str, student_name: str, class_name: str):
    block_h = 66
    block_w = 150
    _draw_round_rect(c, LEFT_MARGIN, y_top - block_h, block_w, block_h, fill_color=colors.white, radius=10)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawString(LEFT_MARGIN + 10, y_top - 14, "Identité du paiement")

    value_x = LEFT_MARGIN + 74
    c.setFont("Helvetica", 7.8)
    c.setFillColor(INK)
    c.drawString(LEFT_MARGIN + 10, y_top - 32, "Eleve")
    c.setStrokeColor(BORDER)
    c.setDash(1, 2)
    c.line(LEFT_MARGIN + 42, y_top - 30, value_x - 6, y_top - 30)
    c.setDash()
    c.drawString(value_x, y_top - 32, (student_name or "-")[:18])
    c.drawString(LEFT_MARGIN + 10, y_top - 46, "Classe")
    c.setDash(1, 2)
    c.line(LEFT_MARGIN + 42, y_top - 44, value_x - 6, y_top - 44)
    c.setDash()
    c.drawString(value_x, y_top - 46, (class_name or "-")[:18])
    c.drawString(LEFT_MARGIN + 10, y_top - 60, "Année")
    c.setDash(1, 2)
    c.line(LEFT_MARGIN + 42, y_top - 58, value_x - 6, y_top - 58)
    c.setDash()
    c.drawString(value_x, y_top - 60, (school_year_name or "-")[:18])

    return y_top - block_h


def _draw_financial_summary(c: canvas.Canvas, y_top: float, amount: float, total_expected: float, total_paid: float, remaining: float):
    grid_x = LEFT_MARGIN + 158
    grid_top = y_top
    gap = 6
    card_w = (RIGHT_MARGIN - grid_x - gap) / 2
    card_h = 30
    cards = [
        ("Montant encaissé", _format_money(amount), INFO_BG, PRIMARY),
        ("Montant prévu", _format_money(total_expected), NEUTRAL_BG, INK),
        ("Total réglé", _format_money(total_paid), SUCCESS_BG, SUCCESS_FG),
        ("Reste à payer", _format_money(max(remaining, 0)), WARNING_BG if remaining > 0 else SUCCESS_BG, WARNING_FG if remaining > 0 else SUCCESS_FG),
    ]

    for index, (title, value, bg, fg) in enumerate(cards):
        row = index // 2
        col = index % 2
        x = grid_x + col * (card_w + gap)
        y = grid_top - row * (card_h + gap) - card_h
        _draw_round_rect(c, x, y, card_w, card_h, fill_color=bg, stroke_color=BORDER, radius=8)
        c.setFillColor(INK)
        c.setFont("Helvetica", 6.9)
        c.drawCentredString(x + card_w / 2, y + 20, title)
        c.setFont("Helvetica-Bold", 8.4)
        c.setFillColor(fg)
        c.drawCentredString(x + card_w / 2, y + 9, value)

    return grid_top - ((2 * card_h) + gap) - 8


def _draw_signature_footer(c: canvas.Canvas, y: float):
    box_w = 106
    box_h = 40
    left_x = LEFT_MARGIN
    right_x = RIGHT_MARGIN - box_w

    _draw_round_rect(c, left_x, y - box_h, box_w, box_h, fill_color=colors.white, radius=8)
    _draw_round_rect(c, right_x, y - box_h, box_w, box_h, fill_color=colors.white, radius=8)

    c.setFont("Helvetica-Bold", 7.0)
    c.setFillColor(INK)
    c.drawCentredString(left_x + box_w / 2, y - 12, "Visa parent")
    c.drawCentredString(right_x + box_w / 2, y - 12, "Visa caissier")

    c.setStrokeColor(BORDER)
    c.line(left_x + 16, y - 26, left_x + box_w - 16, y - 26)
    c.line(right_x + 16, y - 26, right_x + box_w - 16, y - 26)


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
                s.establishment_id,
                COALESCE(fcf.name, ffallback.name, '-') AS fee_name,
                COALESCE(u.username, '-') AS cashier_name
            FROM payments p
            JOIN students s ON s.id = p.student_id
            LEFT JOIN class_fees cf ON cf.id = p.class_fee_id
            LEFT JOIN fees fcf ON fcf.id = cf.fee_id
            LEFT JOIN fees ffallback ON ffallback.id = p.fee_id
            LEFT JOIN school_years sy ON sy.id = cf.school_year_id
            LEFT JOIN enrollments e
              ON e.student_id = s.id
             AND e.school_year_id = cf.school_year_id
            LEFT JOIN classes c ON c.id = e.class_id
            LEFT JOIN users u ON u.id = p.created_by
            WHERE p.id = %s
            LIMIT 1
            """,
            (payment_id,),
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
            fee_name,
            cashier_name,
        ) = row

        school_name, address, phone, email, logo_path = _get_school_identity(cursor, establishment_id)
        student_name = f"{first_name} {last_name}".strip()

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
            (student_id, school_year_id, school_year_id),
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
            (student_id, school_year_id, school_year_id),
        )
        total_paid = float(cursor.fetchone()[0] or 0)
        remaining = total_expected - total_paid

    finally:
        conn.close()

    os.makedirs("receipts", exist_ok=True)
    filepath = f"receipts/{receipt_number}.pdf"

    c = canvas.Canvas(filepath, pagesize=A5)

    def draw_page_frame():
        c.setStrokeColor(BORDER)
        c.setLineWidth(1)
        c.rect(12, 12, PAGE_WIDTH - 24, PAGE_HEIGHT - 24, stroke=1, fill=0)
        c.setStrokeColor(PRIMARY)
        c.setLineWidth(2)
        c.line(12, PAGE_HEIGHT - 12, PAGE_WIDTH - 12, PAGE_HEIGHT - 12)

    draw_page_frame()
    _draw_header(c, school_name, address, phone, email, logo_path, receipt_number)

    y = TOP_MARGIN - 76
    _draw_identity_block(
        c,
        y,
        school_year_name,
        student_name,
        class_name,
    )
    y = _draw_financial_summary(c, y, amount, total_expected, total_paid, remaining)

    c.setFont("Helvetica", 6.8)
    c.setFillColor(MUTED)
    c.drawString(LEFT_MARGIN, y, f"Frais : {fee_name or '-'}")
    c.drawString(LEFT_MARGIN + 132, y, f"Date : {_format_date(payment_date)}")
    c.drawRightString(RIGHT_MARGIN, y, f"Saisi par : {cashier_name or '-'}")
    y -= 14
    visa_y = y

    if y < 72:
        c.showPage()
        draw_page_frame()
        _draw_header(c, school_name, address, phone, email, logo_path, receipt_number)
        y = PAGE_HEIGHT - 92
        visa_y = y

    _draw_signature_footer(c, visa_y)

    c.setFont("Helvetica-Oblique", 6.6)
    c.setFillColor(MUTED)
    c.drawCentredString(PAGE_WIDTH / 2, 20, "Document généré par le système de gestion scolaire")

    c.showPage()
    c.save()
    return filepath
