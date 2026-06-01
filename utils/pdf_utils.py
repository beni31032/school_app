from pypdf import PdfWriter
from utils.path_utils import ensure_app_parent, resolve_app_path


def merge_pdfs(pdf_files: list[str], output_path: str) -> str:
    if not pdf_files:
        raise ValueError("Aucun fichier PDF à fusionner.")

    resolved_output_path = ensure_app_parent(output_path)

    writer = PdfWriter()

    for pdf_file in pdf_files:
        writer.append(str(resolve_app_path(pdf_file)))

    with resolved_output_path.open("wb") as f:
        writer.write(f)

    writer.close()
    return str(resolved_output_path)
