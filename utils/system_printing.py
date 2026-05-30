import os
import subprocess
import sys

from PyQt6.QtPrintSupport import QPrinterInfo
from pypdf import PdfReader


def open_file(filepath: str) -> None:
    if sys.platform.startswith("win"):
        os.startfile(filepath)
    elif sys.platform.startswith("darwin"):
        subprocess.run(["open", filepath], check=False)
    else:
        subprocess.run(["xdg-open", filepath], check=False)


def _run_lpstat() -> str:
    try:
        result = subprocess.run(
            ["lpstat", "-p", "-d"],
            capture_output=True,
            text=True,
            check=False,
        )
        return ((result.stdout or "") + (result.stderr or "")).strip()
    except Exception:
        return ""


def _parse_lpstat_printer_names(output: str) -> list[str]:
    printer_names = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("printer "):
            continue
        parts = line.split()
        if len(parts) >= 2:
            printer_names.append(parts[1])
    return printer_names


def get_printer_statuses() -> list[dict[str, object]]:
    if not sys.platform.startswith("linux"):
        return [
            {"name": name, "enabled": True, "is_default": False}
            for name in get_available_printer_names()
        ]

    output = _run_lpstat()
    if not output or "Scheduler is not running" in output:
        return []

    default_name = None
    statuses: list[dict[str, object]] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("system default destination:"):
            default_name = line.split(":", 1)[1].strip()
            continue
        if not line.startswith("printer "):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        name = parts[1]
        enabled = " disabled since " not in line
        statuses.append(
            {
                "name": name,
                "enabled": enabled,
                "is_default": False,
            }
        )

    for status in statuses:
        status["is_default"] = status["name"] == default_name

    return statuses


def get_available_printer_names() -> list[str]:
    statuses = get_printer_statuses()
    if statuses:
        enabled_printers = [
            str(status["name"])
            for status in statuses
            if bool(status.get("enabled"))
        ]
        if enabled_printers:
            return enabled_printers

    try:
        qt_printer_names = [printer.printerName() for printer in QPrinterInfo.availablePrinters()]
    except Exception:
        qt_printer_names = []

    if not sys.platform.startswith("linux"):
        return qt_printer_names

    lpstat_output = _run_lpstat()
    if "Scheduler is not running" in lpstat_output:
        return []

    lpstat_printer_names = _parse_lpstat_printer_names(lpstat_output)
    if lpstat_printer_names:
        return lpstat_printer_names

    return qt_printer_names


def get_default_printer_name() -> str | None:
    for status in get_printer_statuses():
        if bool(status.get("is_default")) and bool(status.get("enabled")):
            return str(status["name"])
    return None


def _detect_pdf_media(filepath: str) -> str | None:
    try:
        reader = PdfReader(filepath)
        if not reader.pages:
            return None

        page = reader.pages[0]
        media_box = page.mediabox
        width = float(media_box.width)
        height = float(media_box.height)
        shortest, longest = sorted([width, height])

        if abs(shortest - 419.5) < 12 and abs(longest - 595.3) < 12:
            return "A5"
        if abs(shortest - 595.3) < 12 and abs(longest - 841.9) < 12:
            return "A4"
    except Exception:
        return None

    return None


def _detect_pdf_orientation(filepath: str) -> str | None:
    try:
        reader = PdfReader(filepath)
        if not reader.pages:
            return None

        page = reader.pages[0]
        media_box = page.mediabox
        width = float(media_box.width)
        height = float(media_box.height)
        return "landscape" if width > height else "portrait"
    except Exception:
        return None


def send_file_to_printer(filepath: str, printer_name: str | None = None) -> str:
    if sys.platform.startswith("linux"):
        orientation = _detect_pdf_orientation(filepath)
        orientation_requested = "4" if orientation == "landscape" else "3"
        command = [
            "lp",
            "-o",
            "fit-to-page",
            "-o",
            "position=center",
            "-o",
            f"orientation-requested={orientation_requested}",
        ]
        if printer_name:
            command.extend(["-d", printer_name])

        detected_media = _detect_pdf_media(filepath)
        if detected_media:
            command.extend(["-o", f"media={detected_media}"])

        command.append(filepath)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        if result.returncode != 0:
            raise RuntimeError(output or "Envoi à l'imprimante impossible.")
        return output or "Document envoyé à l'imprimante."

    raise RuntimeError("Impression directe non prise en charge sur ce système.")


def get_printing_diagnostic() -> str:
    printer_names = get_available_printer_names()
    if printer_names:
        return f"Imprimantes détectées : {', '.join(printer_names)}"

    output = _run_lpstat()
    if "Scheduler is not running" in output:
        return (
            "Aucune imprimante détectée. Le service d'impression CUPS n'est pas démarré "
            "sur ce poste."
        )
    if output:
        return f"Aucune imprimante détectée. Détail système : {output}"

    return "Aucune imprimante détectée sur ce poste."
