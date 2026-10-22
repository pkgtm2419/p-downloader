"""
Generates the modern IDM-inspired P-Downloader logo:
Rounded square box with 3 lines coming down and merging into a single download arrow at the bottom.
Outputs high-res PNG and multi-resolution Windows ICO.
"""
import os
import struct
from PyQt6.QtGui import (
    QImage, QPainter, QPainterPath, QColor, QLinearGradient,
    QPen, QBrush, QFont
)
from PyQt6.QtCore import Qt, QPointF, QRectF

def create_logo(size: int = 512) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    scale = size / 512.0

    # 1. Outer Box: Rounded Rectangle with IDM Modern Green Gradient
    box_rect = QRectF(24 * scale, 24 * scale, 464 * scale, 464 * scale)
    corner_radius = 100 * scale

    # Gradient for the rounded box (Emerald / Teal IDM signature colors)
    box_grad = QLinearGradient(0, 0, size, size)
    box_grad.setColorAt(0.0, QColor("#10b981"))   # Vibrant emerald
    box_grad.setColorAt(0.5, QColor("#059669"))   # Deep green
    box_grad.setColorAt(1.0, QColor("#065f46"))   # Dark forest green

    box_path = QPainterPath()
    box_path.addRoundedRect(box_rect, corner_radius, corner_radius)

    # Fill Box
    painter.fillPath(box_path, QBrush(box_grad))

    # Inner Top Highlight (Modern Glassmorphism Sheen)
    sheen_rect = QRectF(32 * scale, 30 * scale, 448 * scale, 180 * scale)
    sheen_grad = QLinearGradient(0, 30 * scale, 0, 210 * scale)
    sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 70))
    sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    sheen_path = QPainterPath()
    sheen_path.addRoundedRect(sheen_rect, corner_radius * 0.8, corner_radius * 0.8)
    painter.fillPath(sheen_path, QBrush(sheen_grad))

    # Box Border Stroke
    border_pen = QPen(QColor(255, 255, 255, 80), 6 * scale)
    painter.strokePath(box_path, border_pen)

    # 2. Draw 3 Lines Coming Down and Merging
    # Left Line: curves from top-left into center
    line_pen = QPen(QColor("#ffffff"), 24 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(line_pen)

    # Left incoming line
    left_path = QPainterPath()
    left_path.moveTo(150 * scale, 100 * scale)
    left_path.cubicTo(
        150 * scale, 180 * scale,
        240 * scale, 220 * scale,
        256 * scale, 275 * scale
    )
    painter.drawPath(left_path)

    # Right incoming line
    right_path = QPainterPath()
    right_path.moveTo(362 * scale, 100 * scale)
    right_path.cubicTo(
        362 * scale, 180 * scale,
        272 * scale, 220 * scale,
        256 * scale, 275 * scale
    )
    painter.drawPath(right_path)

    # Center vertical line
    center_path = QPainterPath()
    center_path.moveTo(256 * scale, 100 * scale)
    center_path.lineTo(256 * scale, 280 * scale)
    painter.drawPath(center_path)

    # 3. Merged Bottom Downward Arrow (Single bold mark at the bottom)
    arrow_path = QPainterPath()
    # Arrow stem from merge point down
    arrow_stem = QRectF(238 * scale, 270 * scale, 36 * scale, 60 * scale)
    arrow_path.addRoundedRect(arrow_stem, 6 * scale, 6 * scale)

    # Arrow Head
    head_tip = QPointF(256 * scale, 420 * scale)
    head_left = QPointF(170 * scale, 335 * scale)
    head_left_in = QPointF(225 * scale, 335 * scale)
    head_right_in = QPointF(287 * scale, 335 * scale)
    head_right = QPointF(342 * scale, 335 * scale)

    head_path = QPainterPath()
    head_path.moveTo(head_tip)
    head_path.lineTo(head_left)
    head_path.lineTo(head_left_in)
    head_path.lineTo(head_right_in)
    head_path.lineTo(head_right)
    head_path.closeSubpath()

    # Arrow Gradient (Crisp pure white with cyan glow)
    arrow_grad = QLinearGradient(0, 260 * scale, 0, 420 * scale)
    arrow_grad.setColorAt(0.0, QColor("#f0fdf4"))
    arrow_grad.setColorAt(1.0, QColor("#ffffff"))

    painter.fillPath(head_path, QBrush(arrow_grad))
    painter.fillPath(arrow_path, QBrush(arrow_grad))

    # Subtle arrow outline for crispness
    painter.setPen(QPen(QColor(255, 255, 255, 120), 2 * scale))
    painter.drawPath(head_path)

    painter.end()
    return image

def save_ico(png_images, ico_path):
    """Packages multiple PNG QImages into a standard Windows .ico file."""
    # Write Windows ICO format with embedded PNGs
    num_images = len(png_images)
    header = struct.pack('<HHH', 0, 1, num_images)
    
    entries = []
    png_datas = []
    
    offset = 6 + (num_images * 16)
    
    for img in png_images:
        import io
        from PyQt6.QtCore import QBuffer, QIODevice
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        data = bytes(buf.data())
        buf.close()
        
        w = img.width() if img.width() < 256 else 0
        h = img.height() if img.height() < 256 else 0
        size = len(data)
        
        entry = struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, size, offset)
        entries.append(entry)
        png_datas.append(data)
        offset += size

    with open(ico_path, 'wb') as f:
        f.write(header)
        for e in entries:
            f.write(e)
        for d in png_datas:
            f.write(d)

def main():
    res_dir = os.path.dirname(__file__)
    os.makedirs(res_dir, exist_ok=True)

    master = create_logo(512)
    master.save(os.path.join(res_dir, "logo.png"), "PNG")
    print("Created logo.png (512x512)")

    # Create various resolutions for ICO
    sizes = [256, 128, 64, 48, 32, 16]
    images = []
    for s in sizes:
        scaled = master.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        images.append(scaled)
        scaled.save(os.path.join(res_dir, f"logo_{s}.png"), "PNG")

    ico_path = os.path.join(res_dir, "logo.ico")
    save_ico(images, ico_path)
    print(f"Created multi-res logo.ico at {ico_path}")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    main()
