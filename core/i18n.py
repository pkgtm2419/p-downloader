"""
Internationalization (i18n) and RTL Layout Management for P-Downloader.
Supports 10 major global languages with Right-to-Left (RTL) mirroring
for Arabic, Hebrew, Persian, and Urdu.
"""
from typing import Dict, List, Optional

RTL_LANGUAGES = {"ar", "he", "fa", "ur"}

SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "rtl": False},
    {"code": "es", "name": "Spanish", "native": "Español", "rtl": False},
    {"code": "fr", "name": "French", "native": "Français", "rtl": False},
    {"code": "de", "name": "German", "native": "Deutsch", "rtl": False},
    {"code": "zh", "name": "Chinese", "native": "中文 (简体)", "rtl": False},
    {"code": "ar", "name": "Arabic", "native": "العربية", "rtl": True},
    {"code": "ja", "name": "Japanese", "native": "日本語", "rtl": False},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "rtl": False},
    {"code": "ru", "name": "Russian", "native": "Русский", "rtl": False},
    {"code": "pt", "name": "Portuguese", "native": "Português", "rtl": False},
]

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "app_title": {
        "en": "P-Downloader Ultra",
        "es": "P-Downloader Ultra",
        "fr": "P-Downloader Ultra",
        "de": "P-Downloader Ultra",
        "zh": "P-Downloader 极速下载器",
        "ar": "P-Downloader الترا",
        "ja": "P-Downloader 超高速",
        "hi": "P-Downloader अल्ट्रा",
        "ru": "P-Downloader Ультра",
        "pt": "P-Downloader Ultra"
    },
    "add_url": {
        "en": "Add URL",
        "es": "Añadir URL",
        "fr": "Ajouter URL",
        "de": "URL hinzufügen",
        "zh": "添加链接",
        "ar": "إضافة رابط",
        "ja": "URLを追加",
        "hi": "यूआरएल जोड़ें",
        "ru": "Добавить URL",
        "pt": "Adicionar URL"
    },
    "batch_add": {
        "en": "Batch Add",
        "es": "Añadir por Lotes",
        "fr": "Ajout par Lot",
        "de": "Stapel-Download",
        "zh": "批量添加",
        "ar": "إضافة دفعات",
        "ja": "一括追加",
        "hi": "बैच जोड़ें",
        "ru": "Пакетное добавление",
        "pt": "Adicionar em Lote"
    },
    "pause": {
        "en": "Pause",
        "es": "Pausar",
        "fr": "Pause",
        "de": "Pausieren",
        "zh": "暂停",
        "ar": "إيقاف مؤقت",
        "ja": "一時停止",
        "hi": "रोकें",
        "ru": "Пауза",
        "pt": "Pausar"
    },
    "resume": {
        "en": "Resume",
        "es": "Reanudar",
        "fr": "Reprendre",
        "de": "Fortsetzen",
        "zh": "继续",
        "ar": "استئناف",
        "ja": "再開",
        "hi": "फिर शुरू करें",
        "ru": "Возобновить",
        "pt": "Retomar"
    },
    "delete": {
        "en": "Delete",
        "es": "Eliminar",
        "fr": "Supprimer",
        "de": "Löschen",
        "zh": "删除",
        "ar": "حذف",
        "ja": "削除",
        "hi": "हटाएं",
        "ru": "Удалить",
        "pt": "Excluir"
    },
    "stop_all": {
        "en": "Stop All",
        "es": "Detener Todo",
        "fr": "Tout Arrêter",
        "de": "Alle stoppen",
        "zh": "全部停止",
        "ar": "إيقاف الكل",
        "ja": "すべて停止",
        "hi": "सभी रोकें",
        "ru": "Остановить все",
        "pt": "Parar Tudo"
    },
    "downloading": {
        "en": "Downloading",
        "es": "Descargando",
        "fr": "Téléchargement",
        "de": "Herunterladen",
        "zh": "下载中",
        "ar": "جارٍ التنزيل",
        "ja": "ダウンロード中",
        "hi": "डाउनलोड हो रहा है",
        "ru": "Загрузка",
        "pt": "Baixando"
    },
    "completed": {
        "en": "Completed",
        "es": "Completado",
        "fr": "Terminé",
        "de": "Abgeschlossen",
        "zh": "已完成",
        "ar": "مكتمل",
        "ja": "完了",
        "hi": "पूर्ण",
        "ru": "Завершено",
        "pt": "Concluído"
    },
    "speed": {
        "en": "Speed",
        "es": "Velocidad",
        "fr": "Vitesse",
        "de": "Geschwindigkeit",
        "zh": "速度",
        "ar": "السرعة",
        "ja": "速度",
        "hi": "गति",
        "ru": "Скорость",
        "pt": "Velocidade"
    },
    "settings": {
        "en": "Settings",
        "es": "Configuración",
        "fr": "Paramètres",
        "de": "Einstellungen",
        "zh": "设置",
        "ar": "الإعدادات",
        "ja": "設定",
        "hi": "सेटिंग्स",
        "ru": "Настройки",
        "pt": "Configurações"
    }
}

_current_lang = "en"


def is_rtl(lang_code: str) -> bool:
    """Returns True if the language code requires Right-to-Left (RTL) layout direction."""
    return lang_code.lower() in RTL_LANGUAGES


def get_current_language() -> str:
    return _current_lang


def set_current_language(lang_code: str):
    global _current_lang
    _current_lang = lang_code.lower()


def t(key: str, lang_code: Optional[str] = None) -> str:
    """Translates key into designated or active language, falling back to English."""
    lang = (lang_code or _current_lang).lower()
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("en", key))


def apply_layout_direction(qapp, lang_code: str):
    """Configures PyQt6 layout direction for RTL mirroring when required."""
    if not qapp:
        return
    try:
        from PyQt6.QtCore import Qt
        if is_rtl(lang_code):
            qapp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            qapp.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    except Exception:
        pass
