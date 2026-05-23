from PyQt6.QtWidgets import QInputDialog, QMessageBox

from utils.system_printing import (
    get_available_printer_names,
    get_default_printer_name,
    get_printing_diagnostic,
    open_file,
    send_file_to_printer,
)


def preview_pdf_file(parent, filepath: str, success_prefix: str = "Aperçu PDF généré") -> None:
    try:
        open_file(filepath)
        QMessageBox.information(parent, "Aperçu PDF", f"{success_prefix} : {filepath}")
    except Exception as e:
        QMessageBox.critical(parent, "Erreur", f"Aperçu impossible : {e}")


def print_pdf_file(parent, filepath: str, prefix_message: str) -> bool:
    printer_names = get_available_printer_names()
    if not printer_names:
        _open_pdf_with_warning(
            parent,
            filepath,
            (
                f"{get_printing_diagnostic()}\n\n"
                "Le PDF a quand même été ouvert pour que vous puissiez l'enregistrer "
                "ou l'imprimer plus tard sur un poste configuré."
            ),
        )
        return False

    printer_name = _choose_printer(parent, printer_names)
    if not printer_name:
        return False

    try:
        result_message = send_file_to_printer(filepath, printer_name)
        QMessageBox.information(
            parent,
            "Impression",
            f"{prefix_message}\n\nImprimante : {printer_name}\n{result_message}",
        )
        return True
    except Exception as e:
        _open_pdf_with_warning(
            parent,
            filepath,
            (
                f"Envoi direct à l'imprimante impossible : {e}\n\n"
                "Le PDF a été ouvert pour que vous puissiez essayer une impression manuelle."
            ),
        )
        return False


def _choose_printer(parent, printer_names: list[str]) -> str | None:
    if len(printer_names) == 1:
        return printer_names[0]

    default_printer = get_default_printer_name()
    default_index = 0
    if default_printer in printer_names:
        default_index = printer_names.index(default_printer)

    printer_name, accepted = QInputDialog.getItem(
        parent,
        "Choisir l'imprimante",
        "Imprimante :",
        printer_names,
        default_index,
        False,
    )
    if not accepted or not printer_name:
        return None
    return printer_name


def _open_pdf_with_warning(parent, filepath: str, message: str) -> None:
    try:
        open_file(filepath)
    except Exception as open_error:
        message = f"{message}\n\nOuverture du PDF impossible : {open_error}"

    QMessageBox.warning(parent, "Impression", message)
