import os
from pypdf import PdfWriter


def merge_pdfs(pdf_files: list[str], output_path: str) -> str:
    if not pdf_files:
        raise ValueError("Aucun fichier PDF à fusionner.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    writer = PdfWriter()

    for pdf_file in pdf_files:
        writer.append(pdf_file)

    with open(output_path, "wb") as f:
        writer.write(f)

    writer.close()
    return output_path