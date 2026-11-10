"""
Download Table Model (IM-07).
QAbstractTableModel providing high-performance representation and sorting
for downloads in P-Downloader.
"""
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from gui.styles import format_bytes, format_speed, format_eta

COLUMNS = [
    "File Name",
    "Size",
    "Status",
    "Progress",
    "Transfer Rate",
    "Time Left",
    "Category",
    "Actions"
]


class DownloadTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[Dict[str, Any]] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(COLUMNS):
                return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return item.get("filename", "Unknown")
            elif col == 1:
                total = item.get("total_bytes", 0)
                return format_bytes(total) if total > 0 else "Unknown"
            elif col == 2:
                return (item.get("status") or "Queued").capitalize()
            elif col == 3:
                total = item.get("total_bytes", 0)
                dl = item.get("downloaded_bytes", 0)
                if total > 0:
                    pct = min(100.0, (dl / total) * 100.0)
                    return f"{pct:.1f}% ({format_bytes(dl)})"
                return format_bytes(dl) if dl > 0 else "0%"
            elif col == 4:
                return format_speed(item.get("speed", 0.0)) if item.get("status") == "downloading" else "---"
            elif col == 5:
                total = item.get("total_bytes", 0)
                dl = item.get("downloaded_bytes", 0)
                spd = item.get("speed", 0.0)
                return format_eta(total, dl, spd) if item.get("status") == "downloading" else "---"
            elif col == 6:
                return item.get("category", "General")
            elif col == 7:
                return ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (1, 4, 5):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            elif col in (2, 6, 7):
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ToolTipRole:
            if col == 0:
                return f"{item.get('filename')}\nURL: {item.get('url', '')}\nSave Path: {item.get('save_path', '')}"

        return None

    def set_items(self, items: List[Dict[str, Any]]):
        """Replaces the items list with new data."""
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def get_item(self, row: int) -> Optional[Dict[str, Any]]:
        """Returns the item dict at the specified row."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_task_id(self, row: int) -> Optional[str]:
        """Returns task_id for row."""
        item = self.get_item(row)
        return item.get("task_id") if item else None

    def find_row_by_task_id(self, task_id: str) -> int:
        """Finds row index for a task_id, or -1 if not found."""
        for i, item in enumerate(self._items):
            if item.get("task_id") == task_id:
                return i
        return -1
