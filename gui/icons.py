"""
High-Resolution Crisp Lucide-Style Vector Icon Generator for P-Downloader.
Draws pixel-perfect, scalable 24x24 vector icons matching the Lucide icon standard
with rounded caps and joins, consistent line weights, and semantic colors.
"""
from typing import Optional, Dict
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QIcon, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF

# Color Palette Constants
COLOR_PRIMARY = "#2563EB"       # Primary Blue
COLOR_PRIMARY_HOVER = "#1D4ED8" # Hover Blue
COLOR_SLATE = "#64748B"         # Secondary Text / Neutral Icon
COLOR_DARK = "#172033"          # Main Text / Dark Icon
COLOR_SUCCESS = "#16A34A"       # Success Green
COLOR_WARNING = "#D97706"       # Amber Warning
COLOR_DANGER = "#DC2626"        # Red Danger / Destructive
COLOR_WHITE = "#FFFFFF"         # Pure White
COLOR_MUTED = "#94A3B8"         # Muted Slate

def _make_pen(color: str, width: float = 1.8) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen

def render_lucide_pixmap(name: str, color: str = COLOR_SLATE, size: int = 20) -> QPixmap:
    """
    Renders a Lucide icon onto a transparent square QPixmap of the requested pixel size.
    Base grid is 24x24 with scale factor size / 24.0.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # Scale painter from 24x24 logical coordinates to requested size
    scale = size / 24.0
    p.scale(scale, scale)

    pen = _make_pen(color, 1.85)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    k = name.lower().strip()

    if k in ("plus", "add", "add_url"):
        p.drawLine(12, 5, 12, 19)
        p.drawLine(5, 12, 19, 12)

    elif k in ("layers", "batch", "batch_add"):
        p.drawPolygon([QPointF(12, 2), QPointF(2, 7), QPointF(12, 12), QPointF(22, 7)])
        path1 = QPainterPath()
        path1.moveTo(2, 12)
        path1.lineTo(12, 17)
        path1.lineTo(22, 12)
        p.drawPath(path1)
        path2 = QPainterPath()
        path2.moveTo(2, 17)
        path2.lineTo(12, 22)
        path2.lineTo(22, 17)
        p.drawPath(path2)

    elif k in ("video", "youtube", "film", "stream"):
        p.drawRoundedRect(QRectF(2, 6, 14, 12), 2.5, 2.5)
        path = QPainterPath()
        path.moveTo(22, 7)
        path.lineTo(16, 11)
        path.lineTo(16, 13)
        path.lineTo(22, 17)
        path.closeSubpath()
        p.drawPath(path)

    elif k in ("globe", "extension", "web"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.drawLine(2, 12, 22, 12)
        p.drawEllipse(QRectF(7.5, 2, 9, 20))

    elif k in ("play", "resume"):
        path = QPainterPath()
        path.moveTo(6, 4)
        path.lineTo(20, 12)
        path.lineTo(6, 20)
        path.closeSubpath()
        p.setBrush(QBrush(QColor(color)))
        p.drawPath(path)

    elif k == "pause":
        p.drawLine(7, 4, 7, 20)
        p.drawLine(17, 4, 17, 20)

    elif k in ("rotate-cw", "refresh", "retry"):
        p.drawArc(QRectF(3, 3, 18, 18), -30 * 16, 270 * 16)
        path = QPainterPath()
        path.moveTo(21, 3)
        path.lineTo(21, 9)
        path.lineTo(15, 9)
        p.drawPath(path)

    elif k in ("square", "stop", "stop_all"):
        p.setBrush(QBrush(QColor(color)))
        p.drawRoundedRect(QRectF(4, 4, 16, 16), 2, 2)

    elif k in ("trash", "trash-2", "delete"):
        p.drawLine(3, 6, 21, 6)
        path = QPainterPath()
        path.moveTo(8, 6)
        path.lineTo(8, 2)
        path.lineTo(16, 2)
        path.lineTo(16, 6)
        p.drawPath(path)
        body = QPainterPath()
        body.moveTo(19, 6)
        body.lineTo(18, 20)
        body.lineTo(6, 20)
        body.lineTo(5, 6)
        p.drawPath(body)
        p.drawLine(10, 10, 10, 16)
        p.drawLine(14, 10, 14, 16)

    elif k in ("check-check", "clear_done", "clear"):
        path1 = QPainterPath()
        path1.moveTo(18, 6)
        path1.lineTo(7, 17)
        path1.lineTo(2, 12)
        p.drawPath(path1)
        path2 = QPainterPath()
        path2.moveTo(22, 10)
        path2.lineTo(12, 20)
        path2.lineTo(9.5, 17.5)
        p.drawPath(path2)

    elif k in ("clock", "scheduler"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.drawLine(12, 6, 12, 12)
        p.drawLine(12, 12, 16, 14)

    elif k in ("search", "grabber", "detect"):
        p.drawEllipse(QRectF(3, 3, 15, 15))
        p.drawLine(14, 14, 21, 21)

    elif k in ("settings", "options"):
        p.drawEllipse(QRectF(8, 8, 8, 8))
        for deg in (0, 45, 90, 135, 180, 225, 270, 315):
            rad = deg * 3.14159 / 180.0
            import math
            x1 = 12 + 8 * math.cos(rad)
            y1 = 12 + 8 * math.sin(rad)
            x2 = 12 + 10.5 * math.cos(rad)
            y2 = 12 + 10.5 * math.sin(rad)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    elif k in ("panel-left", "sidebar_toggle", "menu"):
        p.drawRoundedRect(QRectF(3, 3, 18, 18), 3, 3)
        p.drawLine(9, 3, 9, 21)

    elif k == "chevron-left":
        path = QPainterPath()
        path.moveTo(15, 18)
        path.lineTo(9, 12)
        path.lineTo(15, 6)
        p.drawPath(path)

    elif k == "chevron-right":
        path = QPainterPath()
        path.moveTo(9, 18)
        path.lineTo(15, 12)
        path.lineTo(9, 6)
        p.drawPath(path)

    elif k in ("more-vertical", "dots", "actions"):
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(10.5, 3.5, 3, 3))
        p.drawEllipse(QRectF(10.5, 10.5, 3, 3))
        p.drawEllipse(QRectF(10.5, 17.5, 3, 3))

    elif k in ("external-link", "open"):
        path = QPainterPath()
        path.moveTo(18, 13)
        path.lineTo(18, 20)
        path.lineTo(4, 20)
        path.lineTo(4, 6)
        path.lineTo(11, 6)
        p.drawPath(path)
        p.drawLine(15, 3, 21, 3)
        p.drawLine(21, 3, 21, 9)
        p.drawLine(10, 14, 21, 3)

    elif k in ("folder", "folder-open", "directory"):
        path = QPainterPath()
        path.moveTo(3, 7)
        path.lineTo(3, 19)
        path.lineTo(21, 19)
        path.lineTo(21, 9)
        path.lineTo(12, 9)
        path.lineTo(10, 6)
        path.lineTo(3, 6)
        path.closeSubpath()
        p.drawPath(path)

    elif k in ("copy", "copy_url"):
        p.drawRoundedRect(QRectF(9, 9, 12, 12), 2, 2)
        path = QPainterPath()
        path.moveTo(5, 15)
        path.lineTo(3, 15)
        path.lineTo(3, 3)
        path.lineTo(15, 3)
        path.lineTo(15, 5)
        p.drawPath(path)

    elif k in ("info", "details"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.drawLine(12, 11, 12, 17)
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(11, 6.5, 2, 2))

    elif k in ("download", "downloading"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.drawLine(12, 7, 12, 15)
        path = QPainterPath()
        path.moveTo(8, 12)
        path.lineTo(12, 16)
        path.lineTo(16, 12)
        p.drawPath(path)

    elif k in ("check-circle-2", "finished", "completed"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        path = QPainterPath()
        path.moveTo(7, 12)
        path.lineTo(11, 16)
        path.lineTo(17, 8)
        p.drawPath(path)

    elif k in ("pause-circle", "paused"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.drawLine(10, 8, 10, 16)
        p.drawLine(14, 8, 14, 16)

    elif k in ("alert-circle", "error", "expired"):
        p.drawEllipse(QRectF(2, 2, 20, 20))
        p.drawLine(12, 7, 12, 13)
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(11, 15.5, 2, 2))

    elif k in ("inbox", "all"):
        path = QPainterPath()
        path.moveTo(22, 12)
        path.lineTo(20, 4)
        path.lineTo(4, 4)
        path.lineTo(2, 12)
        p.drawPath(path)
        tray = QPainterPath()
        tray.moveTo(2, 12)
        tray.lineTo(7, 12)
        tray.lineTo(9, 16)
        tray.lineTo(15, 16)
        tray.lineTo(17, 12)
        tray.lineTo(22, 12)
        tray.lineTo(22, 20)
        tray.lineTo(2, 20)
        tray.closeSubpath()
        p.drawPath(tray)

    elif k in ("archive", "compressed", "zip"):
        p.drawRoundedRect(QRectF(2, 3, 20, 5), 1.5, 1.5)
        path = QPainterPath()
        path.moveTo(4, 8)
        path.lineTo(4, 21)
        path.lineTo(20, 21)
        path.lineTo(20, 8)
        p.drawPath(path)
        p.drawLine(10, 12, 14, 12)

    elif k in ("file-text", "documents", "document", "doc"):
        path = QPainterPath()
        path.moveTo(14, 2)
        path.lineTo(4, 2)
        path.lineTo(4, 22)
        path.lineTo(20, 22)
        path.lineTo(20, 8)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(14, 2, 14, 8)
        p.drawLine(14, 8, 20, 8)
        p.drawLine(8, 13, 16, 13)
        p.drawLine(8, 17, 13, 17)

    elif k in ("music", "audio"):
        path = QPainterPath()
        path.moveTo(9, 18)
        path.lineTo(9, 5)
        path.lineTo(20, 3)
        path.lineTo(20, 16)
        p.drawPath(path)
        p.setBrush(QBrush(QColor(color)))
        p.drawEllipse(QRectF(5, 15, 4.5, 3.5))
        p.drawEllipse(QRectF(16, 13, 4.5, 3.5))

    elif k in ("app-window", "programs", "program", "app", "exe"):
        p.drawRoundedRect(QRectF(2, 4, 20, 16), 2.5, 2.5)
        p.drawLine(2, 9, 22, 9)
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(5, 6, 2, 2))
        p.drawEllipse(QRectF(9, 6, 2, 2))

    elif k in ("list-ordered", "queue_main", "queue"):
        p.drawLine(10, 6, 21, 6)
        p.drawLine(10, 12, 21, 12)
        p.drawLine(10, 18, 21, 18)
        p.setPen(_make_pen(color, 2.0))
        p.drawLine(4, 6, 6, 6)
        p.drawLine(4, 12, 6, 12)
        p.drawLine(4, 18, 6, 18)

    elif k in ("refresh-cw", "queue_sync", "sync"):
        p.drawArc(QRectF(3, 3, 18, 18), 30 * 16, 130 * 16)
        p.drawArc(QRectF(3, 3, 18, 18), 210 * 16, 130 * 16)
        p.drawLine(20, 7, 21, 11)
        p.drawLine(17, 11, 21, 11)
        p.drawLine(4, 17, 3, 13)
        p.drawLine(7, 13, 3, 13)

    elif k in ("activity", "bandwidth", "speed"):
        path = QPainterPath()
        path.moveTo(22, 12)
        path.lineTo(18, 12)
        path.lineTo(15, 21)
        path.lineTo(9, 3)
        path.lineTo(6, 12)
        path.lineTo(2, 12)
        p.drawPath(path)

    elif k in ("network", "adapter", "bonding"):
        p.drawRect(QRectF(9, 2, 6, 5))
        p.drawRect(QRectF(2, 17, 6, 5))
        p.drawRect(QRectF(16, 17, 6, 5))
        p.drawLine(12, 7, 12, 12)
        p.drawLine(5, 12, 19, 12)
        p.drawLine(5, 12, 5, 17)
        p.drawLine(19, 12, 19, 17)

    elif k in ("gauge", "limiter", "speed_limiter"):
        p.drawArc(QRectF(2, 3, 20, 20), 0, 180 * 16)
        p.drawLine(12, 14, 17, 9)
        p.drawLine(2, 13, 4, 13)
        p.drawLine(20, 13, 22, 13)
        p.drawLine(12, 3, 12, 5)

    elif k in ("link", "url"):
        p.drawArc(QRectF(9, 4, 11, 7), -45 * 16, 180 * 16)
        p.drawArc(QRectF(4, 13, 11, 7), 135 * 16, 180 * 16)
        p.drawLine(8, 16, 16, 8)

    elif k in ("shield", "security"):
        path = QPainterPath()
        path.moveTo(12, 2)
        path.lineTo(20, 5)
        path.lineTo(20, 12)
        path.cubicTo(20, 17, 16, 21, 12, 22)
        path.cubicTo(8, 21, 4, 17, 4, 12)
        path.lineTo(4, 5)
        path.closeSubpath()
        p.drawPath(path)

    else:
        # Fallback clean document icon
        path = QPainterPath()
        path.moveTo(14, 2)
        path.lineTo(4, 2)
        path.lineTo(4, 22)
        path.lineTo(20, 22)
        path.lineTo(20, 8)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(14, 2, 14, 8)
        p.drawLine(14, 8, 20, 8)

    p.end()
    return pix

_ICON_CACHE: Dict[str, QIcon] = {}

def get_icon(name: str, color: str = COLOR_SLATE, size: int = 20) -> QIcon:
    """
    Returns a cached QIcon rendered with Lucide vector paths.
    Supports hover/active states dynamically if requested.
    """
    cache_key = f"{name}_{color}_{size}"
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    normal_pix = render_lucide_pixmap(name, color, size)
    icon = QIcon(normal_pix)

    # Add active/hover state with brighter accent
    if color == COLOR_SLATE:
        hover_pix = render_lucide_pixmap(name, COLOR_PRIMARY, size)
        icon.addPixmap(hover_pix, QIcon.Mode.Active)
        icon.addPixmap(hover_pix, QIcon.Mode.Selected)

    _ICON_CACHE[cache_key] = icon
    return icon

def get_sidebar_icon(kind: str, selected: bool = False) -> QIcon:
    """
    Returns an icon tailored for the sidebar with clear semantic colors.
    """
    k = kind.lower().strip()
    color_map = {
        "all": COLOR_PRIMARY if selected else "#2563EB",
        "compressed": "#D97706",
        "documents": "#2563EB",
        "music": "#8B5CF6",
        "programs": "#0284C7",
        "video": "#EF4444",
        "downloading": COLOR_PRIMARY,
        "finished": COLOR_SUCCESS,
        "paused": COLOR_WARNING,
        "error": COLOR_DANGER,
        "queue_main": "#F59E0B",
        "queue_sync": "#06B6D4"
    }
    icon_name_map = {
        "all": "inbox",
        "compressed": "archive",
        "documents": "file-text",
        "music": "music",
        "programs": "app-window",
        "video": "video",
        "downloading": "download",
        "finished": "check-circle-2",
        "paused": "pause-circle",
        "error": "alert-circle",
        "queue_main": "list-ordered",
        "queue_sync": "refresh-cw"
    }
    color = color_map.get(k, COLOR_SLATE)
    name = icon_name_map.get(k, "file-text")
    return get_icon(name, color, 18)

def get_file_type_icon(category_or_ext: str, size: int = 18) -> QIcon:
    """
    Returns an appropriate Lucide file icon based on category or file extension.
    """
    c = category_or_ext.lower().strip()
    if c in ("video", ".mp4", ".mkv", ".avi", ".webm", ".mov"):
        return get_icon("video", "#EF4444", size)
    elif c in ("music", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"):
        return get_icon("music", "#8B5CF6", size)
    elif c in ("compressed", ".zip", ".rar", ".7z", ".tar", ".gz", ".iso"):
        return get_icon("archive", "#D97706", size)
    elif c in ("documents", ".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"):
        return get_icon("file-text", "#2563EB", size)
    elif c in ("programs", ".exe", ".msi", ".apk", ".bat", ".cmd"):
        return get_icon("app-window", "#0284C7", size)
    return get_icon("file-text", COLOR_SLATE, size)
