from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.pdfgen import canvas

from database.connection import get_connection
from utils.receipt_generator import (
    PAGE_HEIGHT,
    PAGE_WIDTH,
    _draw_financial_summary,
    _draw_header,
    _draw_identity_block,
    _draw_signature_footer,
    _format_money,
)


def get_school_info():
    school_name = "Ecole Privée Laïque VILLAGE PLANETAIRE"
    address = "06 BP 60041"
    phone = "93041820 / 22209174"
    email = "csvillageplanetaire@gmail.com"
    logo_path = ""

    conn = get_connection()
    if not conn:
        return school_name, address, phone, email, logo_path

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(name, ''),
                COALESCE(address, ''),
                COALESCE(phone, ''),
                COALESCE(email, ''),
                COALESCE(logo_path, '')
            FROM school_info
            ORDER BY id
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row:
            school_name = row[0] or school_name
            address = row[1] or address
            phone = row[2] or phone
            email = row[3] or email
            logo_path = row[4] or logo_path
    finally:
        conn.close()

    return school_name, address, phone, email, logo_path


def main() -> int:
    school_name, address, phone, email, logo_path = get_school_info()

    output_dir = PROJECT_ROOT / "receipts"
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "APERCU_RECU_EXEMPLE.pdf"

    c = canvas.Canvas(str(filepath), pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    def draw_page_frame():
        from utils.receipt_generator import BORDER, PRIMARY

        c.setStrokeColor(BORDER)
        c.setLineWidth(1)
        c.rect(12, 12, PAGE_WIDTH - 24, PAGE_HEIGHT - 24, stroke=1, fill=0)
        c.setStrokeColor(PRIMARY)
        c.setLineWidth(2)
        c.line(12, PAGE_HEIGHT - 12, PAGE_WIDTH - 12, PAGE_HEIGHT - 12)

    draw_page_frame()
    _draw_header(c, school_name, address, phone, email, logo_path, "RC-EXEMPLE-0001")

    y = PAGE_HEIGHT - 98
    _draw_identity_block(
        c,
        y,
        "2025-2026",
        "Koffi Ama",
        "3ème A",
    )

    y = _draw_financial_summary(c, y, 25000, 120000, 75000, 45000)

    c.setFont("Helvetica", 6.8)
    c.drawString(22, y, "Frais : Scolarité")
    c.drawString(160, y, "Date : 15/01/2026")
    c.drawRightString(PAGE_WIDTH - 22, y, "Saisi par : beni")
    y -= 14

    _draw_signature_footer(c, y)

    c.setFont("Helvetica-Oblique", 6.6)
    c.drawCentredString(PAGE_WIDTH / 2, 20, f"Aperçu exemple - montant affiché : {_format_money(25000)}")

    c.showPage()
    c.save()

    print(filepath)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
