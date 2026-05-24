from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox


def show_error_dialog(parent, title: str, summary: str, error=None) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(summary)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    details = str(error).strip() if error is not None else ""
    if details:
        box.setInformativeText(details)
        box.setDetailedText(details)

    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setMinimumWidth(640)
    box.setStyleSheet(
        """
        QLabel {
            min-width: 520px;
            color: #111827;
        }
        QTextEdit {
            min-width: 640px;
            min-height: 220px;
            font-family: monospace;
        }
        """
    )
    box.exec()
