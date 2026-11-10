"""
Typed Settings Schema Registry and Configuration Engine for P-Downloader.
Provides structured type validation, default registries, JSON import/export,
and section categorization for all application settings.
"""
from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Callable, Dict, List, Optional, Union


class SettingType(str, Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    ENUM = "enum"


class SettingSection(str, Enum):
    NETWORK = "network"
    ENGINE = "engine"
    PROXY = "proxy"
    DNS = "dns"
    VIDEO = "video"
    DEBRID = "debrid"
    APPEARANCE = "appearance"
    INTEGRATION = "integration"
    SECURITY = "security"
    PATHS = "paths"


@dataclass
class SettingDef:
    key: str
    type: SettingType
    default: Any
    label: str
    section: SettingSection
    description: str = ""
    enum_values: Optional[List[str]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    validator: Optional[Callable[[Any], bool]] = None


# Comprehensive Schema Registry of all P-Downloader Configuration Keys
SETTINGS_SCHEMA: Dict[str, SettingDef] = {
    # 1. Network & Engine
    "connection_mode": SettingDef(
        key="connection_mode",
        type=SettingType.ENUM,
        default="Direct",
        label="Connection Mode",
        section=SettingSection.ENGINE,
        enum_values=["Direct", "High Speed", "Medium", "Low Speed"]
    ),
    "default_connections": SettingDef(
        key="default_connections",
        type=SettingType.INT,
        default=8,
        label="Default Connections per Download",
        section=SettingSection.ENGINE,
        min_value=1,
        max_value=32
    ),
    "simultaneous_downloads": SettingDef(
        key="simultaneous_downloads",
        type=SettingType.INT,
        default=3,
        label="Simultaneous Downloads",
        section=SettingSection.ENGINE,
        min_value=1,
        max_value=20
    ),
    "max_active_downloads": SettingDef(
        key="max_active_downloads",
        type=SettingType.INT,
        default=3,
        label="Max Active Downloads",
        section=SettingSection.ENGINE,
        min_value=1,
        max_value=20
    ),
    "max_global_streams": SettingDef(
        key="max_global_streams",
        type=SettingType.INT,
        default=32,
        label="Max Global Concurrency Streams",
        section=SettingSection.ENGINE,
        min_value=1,
        max_value=128
    ),
    "timeout": SettingDef(
        key="timeout",
        type=SettingType.INT,
        default=30,
        label="Socket Timeout (seconds)",
        section=SettingSection.ENGINE,
        min_value=5,
        max_value=300
    ),
    "limit_speed_enabled": SettingDef(
        key="limit_speed_enabled",
        type=SettingType.BOOL,
        default=False,
        label="Enable Global Speed Limiter",
        section=SettingSection.ENGINE
    ),
    "speed_limit_kb": SettingDef(
        key="speed_limit_kb",
        type=SettingType.INT,
        default=1024,
        label="Speed Limit (KB/s)",
        section=SettingSection.ENGINE,
        min_value=10,
        max_value=1000000
    ),
    "network_bonding": SettingDef(
        key="network_bonding",
        type=SettingType.BOOL,
        default=False,
        label="Multi-Adapter Bandwidth Bonding",
        section=SettingSection.NETWORK
    ),
    "bound_adapter": SettingDef(
        key="bound_adapter",
        type=SettingType.STR,
        default="",
        label="Bound Network Adapter IP",
        section=SettingSection.NETWORK
    ),
    "vpn_killswitch": SettingDef(
        key="vpn_killswitch",
        type=SettingType.BOOL,
        default=False,
        label="VPN Kill Switch (Fail Closed)",
        section=SettingSection.NETWORK
    ),

    # 2. Proxy
    "use_proxy": SettingDef(
        key="use_proxy",
        type=SettingType.BOOL,
        default=False,
        label="Use Proxy Server",
        section=SettingSection.PROXY
    ),
    "proxy_proto": SettingDef(
        key="proxy_proto",
        type=SettingType.ENUM,
        default="HTTP",
        label="Proxy Protocol",
        section=SettingSection.PROXY,
        enum_values=["HTTP", "HTTPS", "SOCKS5"]
    ),
    "proxy_host": SettingDef(
        key="proxy_host",
        type=SettingType.STR,
        default="",
        label="Proxy Host",
        section=SettingSection.PROXY
    ),
    "proxy_port": SettingDef(
        key="proxy_port",
        type=SettingType.INT,
        default=8080,
        label="Proxy Port",
        section=SettingSection.PROXY,
        min_value=1,
        max_value=65535
    ),

    # 3. Encrypted DNS / DoH
    "dns_mode": SettingDef(
        key="dns_mode",
        type=SettingType.ENUM,
        default="System",
        label="DNS Resolution Mode",
        section=SettingSection.DNS,
        enum_values=["System", "DoH"]
    ),
    "doh_provider": SettingDef(
        key="doh_provider",
        type=SettingType.ENUM,
        default="Cloudflare",
        label="DNS-over-HTTPS Provider",
        section=SettingSection.DNS,
        enum_values=["Cloudflare", "Google", "Quad9", "Custom"]
    ),
    "custom_doh_url": SettingDef(
        key="custom_doh_url",
        type=SettingType.STR,
        default="",
        label="Custom DoH Endpoint URL",
        section=SettingSection.DNS
    ),

    # 4. Universal Video / Streaming
    "video_concurrent_fragments": SettingDef(
        key="video_concurrent_fragments",
        type=SettingType.INT,
        default=4,
        label="HLS/DASH Concurrent Fragment Downloads",
        section=SettingSection.VIDEO,
        min_value=1,
        max_value=16
    ),
    "video_preferred_res": SettingDef(
        key="video_preferred_res",
        type=SettingType.ENUM,
        default="best",
        label="Default Preferred Video Quality",
        section=SettingSection.VIDEO,
        enum_values=["best", "1080p", "720p", "480p", "360p", "worst"]
    ),
    "video_audio_format": SettingDef(
        key="video_audio_format",
        type=SettingType.ENUM,
        default="mp3",
        label="Default Audio Extractor Format",
        section=SettingSection.VIDEO,
        enum_values=["mp3", "m4a", "aac", "wav", "flac"]
    ),
    "hls_live_record_duration": SettingDef(
        key="hls_live_record_duration",
        type=SettingType.INT,
        default=0,
        label="Live Stream Max Record Duration (seconds, 0=unlimited)",
        section=SettingSection.VIDEO,
        min_value=0
    ),

    # 5. Security & Antivirus
    "antivirus_enabled": SettingDef(
        key="antivirus_enabled",
        type=SettingType.BOOL,
        default=True,
        label="Scan Finished Downloads with Antivirus",
        section=SettingSection.SECURITY
    ),
    "antivirus_path": SettingDef(
        key="antivirus_path",
        type=SettingType.STR,
        default="",
        label="Custom Antivirus Scanner Executable Path",
        section=SettingSection.SECURITY
    ),
    "ssrf_protection": SettingDef(
        key="ssrf_protection",
        type=SettingType.BOOL,
        default=True,
        label="Enforce SSRF IP Pinning and Private IP Block",
        section=SettingSection.SECURITY
    ),

    # 6. Debrid Cloud Providers
    "debrid_rd_token": SettingDef(
        key="debrid_rd_token",
        type=SettingType.STR,
        default="",
        label="Real-Debrid API Key",
        section=SettingSection.DEBRID
    ),
    "debrid_ad_token": SettingDef(
        key="debrid_ad_token",
        type=SettingType.STR,
        default="",
        label="AllDebrid API Key",
        section=SettingSection.DEBRID
    ),
    "debrid_prem_token": SettingDef(
        key="debrid_prem_token",
        type=SettingType.STR,
        default="",
        label="Premiumize API Key",
        section=SettingSection.DEBRID
    ),

    # 7. Appearance & I18N
    "theme": SettingDef(
        key="theme",
        type=SettingType.ENUM,
        default="Modern Dark",
        label="User Interface Theme",
        section=SettingSection.APPEARANCE,
        enum_values=["Modern Dark", "Classic Light", "Tokyo Night", "Nord", "Cyberpunk", "Solarized Dark", "Gruvbox", "Monokai Pro", "Catppuccin Mocha"]
    ),
    "language": SettingDef(
        key="language",
        type=SettingType.STR,
        default="en",
        label="Language Code",
        section=SettingSection.APPEARANCE
    ),
    "sound_on_finish": SettingDef(
        key="sound_on_finish",
        type=SettingType.BOOL,
        default=True,
        label="Play Sound on Download Finish",
        section=SettingSection.APPEARANCE
    ),
    "toast_on_finish": SettingDef(
        key="toast_on_finish",
        type=SettingType.BOOL,
        default=True,
        label="Show Desktop Notification on Finish",
        section=SettingSection.APPEARANCE
    ),
    "minimize_tray": SettingDef(
        key="minimize_tray",
        type=SettingType.BOOL,
        default=True,
        label="Minimize to System Tray",
        section=SettingSection.APPEARANCE
    ),
    "sidebar_collapsed": SettingDef(
        key="sidebar_collapsed",
        type=SettingType.BOOL,
        default=False,
        label="Sidebar Collapsed",
        section=SettingSection.APPEARANCE
    ),

    # 8. Integration & Automation
    "auto_startup": SettingDef(
        key="auto_startup",
        type=SettingType.BOOL,
        default=False,
        label="Launch at System Startup",
        section=SettingSection.INTEGRATION
    ),
    "clipboard_monitor": SettingDef(
        key="clipboard_monitor",
        type=SettingType.BOOL,
        default=False,
        label="Monitor System Clipboard for Download Links",
        section=SettingSection.INTEGRATION
    ),
    "show_dlg": SettingDef(
        key="show_dlg",
        type=SettingType.BOOL,
        default=True,
        label="Show Start Download Confirmation Dialog",
        section=SettingSection.INTEGRATION
    ),
    "auto_extract_archives": SettingDef(
        key="auto_extract_archives",
        type=SettingType.BOOL,
        default=False,
        label="Automatically Extract Downloaded Archives",
        section=SettingSection.INTEGRATION
    ),

    # 9. Paths
    "default_dir": SettingDef(
        key="default_dir",
        type=SettingType.STR,
        default="",
        label="Default Downloads Directory",
        section=SettingSection.PATHS
    ),
    "temp_dir": SettingDef(
        key="temp_dir",
        type=SettingType.STR,
        default="",
        label="Temporary Download Chunks Directory",
        section=SettingSection.PATHS
    ),
}


def get_setting_def(key: str) -> Optional[SettingDef]:
    """Retrieves the schema definition for a setting key."""
    return SETTINGS_SCHEMA.get(key)


def validate_setting(key: str, value: Any) -> Any:
    """
    Validates and coerces a value according to its schema definition.
    Raises ValueError on validation failure.
    """
    definition = get_setting_def(key)
    if definition is None:
        # Unregistered setting passes through as string
        return str(value)

    stype = definition.type
    if stype == SettingType.BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            clean = value.strip().lower()
            if clean in ("1", "true", "yes", "on", "enable", "enabled"):
                return True
            if clean in ("0", "false", "no", "off", "disable", "disabled", ""):
                return False
            raise ValueError(f"Invalid boolean value for {key}: '{value}'")
        return bool(value)

    if stype == SettingType.INT:
        try:
            val = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Setting {key} must be an integer, got: {value!r}")
        if definition.min_value is not None and val < definition.min_value:
            raise ValueError(f"Setting {key} must be >= {definition.min_value}")
        if definition.max_value is not None and val > definition.max_value:
            raise ValueError(f"Setting {key} must be <= {definition.max_value}")
        return val

    if stype == SettingType.FLOAT:
        try:
            val = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Setting {key} must be a float, got: {value!r}")
        if definition.min_value is not None and val < definition.min_value:
            raise ValueError(f"Setting {key} must be >= {definition.min_value}")
        if definition.max_value is not None and val > definition.max_value:
            raise ValueError(f"Setting {key} must be <= {definition.max_value}")
        return val

    if stype == SettingType.ENUM:
        str_val = str(value).strip()
        if definition.enum_values:
            # Case-insensitive enum matching
            lookup = {ev.lower(): ev for ev in definition.enum_values}
            matched = lookup.get(str_val.lower())
            if matched is None:
                raise ValueError(
                    f"Invalid enum value '{str_val}' for {key}. Allowed: {definition.enum_values}"
                )
            return matched
        return str_val

    if stype == SettingType.STR:
        str_val = str(value)
        if definition.validator and not definition.validator(str_val):
            raise ValueError(f"Validation failed for string setting {key}")
        return str_val

    return value


def to_db_string(key: str, value: Any) -> str:
    """Coerces a typed value to its stored string representation in SQLite."""
    validated = validate_setting(key, value)
    if isinstance(validated, bool):
        return "1" if validated else "0"
    return str(validated)


def from_db_string(key: str, str_val: str, default: Any = None) -> Any:
    """Converts a database string value into its registered Python type."""
    definition = get_setting_def(key)
    if definition is None:
        return str_val if str_val is not None else default

    if str_val is None or str_val == "":
        return definition.default if default is None else default

    try:
        return validate_setting(key, str_val)
    except ValueError:
        return definition.default if default is None else default


def export_settings_dict(db: Any) -> Dict[str, Any]:
    """Exports all registered settings from the database as a typed dictionary."""
    result: Dict[str, Any] = {}
    for key, definition in SETTINGS_SCHEMA.items():
        raw = db.get_setting(key, "")
        if raw != "":
            result[key] = from_db_string(key, raw)
        else:
            result[key] = definition.default
    return result


def export_settings_json(db: Any, indent: int = 2) -> str:
    """Exports all registered settings from the database as a formatted JSON string."""
    return json.dumps(export_settings_dict(db), indent=indent, sort_keys=True)


def import_settings_json(db: Any, json_str: str) -> Dict[str, Any]:
    """
    Imports and validates settings from a JSON string into the database.
    Returns a dictionary of successfully applied key-value pairs.
    """
    data = json.loads(json_str)
    if not isinstance(data, dict):
        raise ValueError("Settings import JSON must be a dictionary object")

    applied: Dict[str, Any] = {}
    for key, val in data.items():
        if key in SETTINGS_SCHEMA:
            typed_val = validate_setting(key, val)
            db_val = to_db_string(key, typed_val)
            db.set_setting(key, db_val)
            applied[key] = typed_val
    return applied
