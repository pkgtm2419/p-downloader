"""
High-Resolution Crisp Vector Icon Generator for P-Downloader Sidebar.
Renders pixel-perfect, modern vector icons to replace mismatched Windows emojis.
"""
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QIcon, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF

def _make_pen(color: str, width: float = 1.8, round_cap: bool = True) -> QPen:
    pen = QPen(QColor(color), width)
    if round_cap:
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen

def get_sidebar_icon(kind: str) -> QIcon:
    """
    Renders a crisp 20x20 modern vector icon.
    """
    pix = QPixmap(20, 20)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    k = kind.lower()

    if k == "all":
        # Emerald squircle with downward arrow and base tray
        p.setBrush(QBrush(QColor("#10b981")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 1.5, 17, 17), 5, 5)
        # Arrow
        p.setPen(_make_pen("#ffffff", 2.0))
        p.drawLine(10, 4, 10, 11)
        p.drawLine(7, 9, 10, 12)
        p.drawLine(13, 9, 10, 12)
        # Base tray
        p.drawLine(6, 14, 14, 14)

    elif k == "compressed":
        # Amber package box
        p.setBrush(QBrush(QColor("#f59e0b")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 2.5, 17, 15), 4, 4)
        # Box tape line
        p.setPen(_make_pen("#ffffff", 1.8))
        p.drawLine(10, 3, 10, 17)
        p.drawLine(6, 7, 14, 7)

    elif k == "documents":
        # Blue paper file with folded corner
        p.setBrush(QBrush(QColor("#3b82f6")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(2.5, 1.5, 15, 17), 3, 3)
        # Text lines on document
        p.setPen(_make_pen("#ffffff", 1.6))
        p.drawLine(6, 7, 14, 7)
        p.drawLine(6, 10, 14, 10)
        p.drawLine(6, 13, 11, 13)

    elif k == "music":
        # Purple circle with musical note
        p.setBrush(QBrush(QColor("#8b5cf6")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 1.5, 17, 17), 5, 5)
        # Note
        p.setBrush(QBrush(QColor("#ffffff")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(5, 11, 5, 4))
        p.setPen(_make_pen("#ffffff", 1.8))
        p.drawLine(10, 6, 10, 12)
        p.drawLine(10, 6, 14, 5)
        p.drawLine(14, 5, 14, 10)

    elif k == "programs":
        # Cyan application window
        p.setBrush(QBrush(QColor("#0ea5e9")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 2.5, 17, 15), 4, 4)
        # Window buttons and title bar
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(QRectF(4.5, 4.5, 2, 2))
        p.drawEllipse(QRectF(8, 4.5, 2, 2))
        p.setPen(_make_pen("#ffffff", 1.2, False))
        p.drawLine(2, 8, 18, 8)

    elif k == "video":
        # Rose / Coral clapperboard with play symbol
        p.setBrush(QBrush(QColor("#f43f5e")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 2.5, 17, 15), 4, 4)
        # White play triangle
        path = QPainterPath()
        path.moveTo(8, 6.5)
        path.lineTo(14, 10)
        path.lineTo(8, 13.5)
        path.closeSubpath()
        p.setBrush(QBrush(QColor("#ffffff")))
        p.fillPath(path, QBrush(QColor("#ffffff")))

    elif k == "downloading":
        # Sky-blue circular active download badge
        p.setBrush(QBrush(QColor("#0284c7")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(1.5, 1.5, 17, 17))
        # Arrow pointing down
        p.setPen(_make_pen("#ffffff", 2.0))
        p.drawLine(10, 5, 10, 13)
        p.drawLine(7, 10, 10, 13)
        p.drawLine(13, 10, 10, 13)

    elif k == "finished":
        # Emerald green circular check badge
        p.setBrush(QBrush(QColor("#10b981")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(1.5, 1.5, 17, 17))
        # Crisp checkmark
        p.setPen(_make_pen("#ffffff", 2.2))
        p.drawLine(5, 10, 8, 13)
        p.drawLine(8, 13, 14, 7)

    elif k == "paused":
        # Amber circular pause badge
        p.setBrush(QBrush(QColor("#f59e0b")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(1.5, 1.5, 17, 17))
        # Two vertical bars
        p.setPen(_make_pen("#ffffff", 2.2))
        p.drawLine(7, 6, 7, 14)
        p.drawLine(12, 6, 12, 14)

    elif k == "error":
        # Crimson circular error badge
        p.setBrush(QBrush(QColor("#ef4444")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(1.5, 1.5, 17, 17))
        # Exclamation mark
        p.setPen(_make_pen("#ffffff", 2.0))
        p.drawLine(10, 5, 10, 11)
        p.drawPoint(10, 13)

    elif k == "queue_main":
        # Amber lightning bolt / queue badge
        p.setBrush(QBrush(QColor("#f59e0b")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 1.5, 17, 17), 5, 5)
        # Lightning shape
        path = QPainterPath()
        path.moveTo(10.5, 4)
        path.lineTo(6.5, 10)
        path.lineTo(10, 10)
        path.lineTo(9.5, 16)
        path.lineTo(14, 9.5)
        path.lineTo(10.5, 9.5)
        path.closeSubpath()
        p.setBrush(QBrush(QColor("#ffffff")))
        p.fillPath(path, QBrush(QColor("#ffffff")))

    elif k == "queue_sync":
        # Cyan / Blue circular sync badge
        p.setBrush(QBrush(QColor("#06b6d4")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1.5, 1.5, 17, 17), 5, 5)
        # Circular sync arrows
        p.setPen(_make_pen("#ffffff", 1.8))
        p.drawArc(QRectF(4.5, 4.5, 11, 11), 30 * 16, 120 * 16)
        p.drawArc(QRectF(4.5, 4.5, 11, 11), 210 * 16, 120 * 16)

    p.end()
    return QIcon(pix)
