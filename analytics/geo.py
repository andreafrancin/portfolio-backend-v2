"""The country of a visit, looked up on this server.

The IP address is only used for this lookup (and for the day's anonymous code); it is never stored.
Country data: DB-IP.com "IP to Country Lite" (CC BY 4.0), downloaded at deploy time by
`python manage.py download_geoip`. Without the file every visit simply has no country.
"""
import ipaddress
import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_reader = None
_loaded = False
_lock = threading.Lock()


def _open():
    global _reader, _loaded
    with _lock:
        if _loaded:
            return _reader
        _loaded = True
        try:
            import maxminddb
            _reader = maxminddb.open_database(str(settings.ANALYTICS_GEOIP_PATH))
        except FileNotFoundError:
            logger.info("Country database not found at %s; visits will have no country.", settings.ANALYTICS_GEOIP_PATH)
        except Exception as exc:  # a broken or unreadable file must never break visit counting
            logger.warning("Country database could not be opened: %s", exc)
        return _reader


def country_of(ip: str) -> str:
    """Two-letter country code for a public IP address, or "" when unknown."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ""
    if not address.is_global:
        return ""
    reader = _open()
    if reader is None:
        return ""
    try:
        record = reader.get(ip) or {}
    except Exception:
        return ""
    code = (record.get("country") or {}).get("iso_code") or ""
    return code if len(code) == 2 else ""


def reset() -> None:
    """Forget the open file, so a freshly downloaded one is used."""
    global _reader, _loaded
    with _lock:
        if _reader is not None:
            try:
                _reader.close()
            except Exception:
                pass
        _reader, _loaded = None, False
