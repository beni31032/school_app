#table_style.py


from PyQt6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt


def setup_table(table: QTableWidget, stretch: bool = True):
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)

    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    table.setShowGrid(True)

    # ⚠️ IMPORTANT : ne pas bloquer l'édition ici
    # (sinon ça casse le module notes)
    # table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    if stretch:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    else:
        table.horizontalHeader().setStretchLastSection(True)

    # =========================
    # STYLE GLOBAL UNIFIÉ
    # =========================
    table.setStyleSheet("""
        QTableWidget {
            background-color: white;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            gridline-color: #e5e7eb;
            font-size: 13px;
            color: #111827;
        }

        QTableWidget::item {
            padding: 6px;
        }

        QTableWidget::item:selected {
            background-color: #bfdbfe;
            color: black;
        }

        QHeaderView::section {
            background-color: #2563eb;
            color: white;
            padding: 6px;
            border: none;
            font-weight: bold;
            height: 32px;
        }
    """)

    # Alignement header
    table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    table.horizontalHeader().setMinimumHeight(36)