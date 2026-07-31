"""HTTP client"""
import logging, requests
from dataclasses import dataclass
from typing import Any, Optional
log = logging.getLogger("maskai.http")
@dataclass
class ApiResult:
    """Typed API result — all HTTP helpers return this"""
    ok: bool
    status: int = 0
    data: Any = None
    error: Optional[str] = None

def api_get(url, **kw):
    """Safe GET with typed result"""
    try:
        r = requests.get(url, timeout=kw.pop("timeout", config.HTTP_TIMEOUT), **kw)
        if r.status_code < 200 or r.status_code >= 300:
            log.warning("API GET %s: %s", r.status_code, r.text[:100])
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, data=r.json() if r.text else None, status=r.status_code)
    except requests.Timeout:
        log.error("API GET timeout: %s", url.replace(BOT_TOKEN, "***")[:80])
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        log.error("API GET connection error: %s", url.replace(BOT_TOKEN, "***")[:80])
        return ApiResult(False, error="connection")
    except ValueError as e:
        log.error(f"API GET invalid JSON: {e}")
        return ApiResult(False, error="invalid_json")
    except requests.RequestException as exc:
        log.error("API GET request error: %s", exc)
        return ApiResult(False, error=str(exc)[:200])

def api_post(url, json=None, data=None, **kw):
    """Safe POST with typed result"""
    try:
        r = requests.post(url, json=json, data=data, timeout=kw.pop("timeout", config.HTTP_TIMEOUT), **kw)
        if r.status_code < 200 or r.status_code >= 300:
            log.warning("API POST %s: %s", r.status_code, r.text[:100])
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, data=r.json() if r.text else {}, status=r.status_code)
    except requests.Timeout:
        log.error("API POST timeout: %s", url.replace(BOT_TOKEN, "***")[:80])
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        log.error("API POST connection error: %s", url.replace(BOT_TOKEN, "***")[:80])
        return ApiResult(False, error="connection")
    except ValueError as e:
        log.error(f"API POST invalid JSON: {e}")
        return ApiResult(False, error="invalid_json")
    except requests.RequestException as exc:
        log.error("API POST request error: %s", exc)
        return ApiResult(False, error=str(exc)[:200])


def api_patch(url, json=None, **kw):
    """Safe PATCH with typed result"""
    try:
        r = requests.patch(url, json=json, timeout=kw.pop("timeout", config.HTTP_TIMEOUT), **kw)
        if r.status_code < 200 or r.status_code >= 300:
            log.warning("API PATCH %s: %s", r.status_code, r.text[:100])
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        # 204 has no body
        if r.status_code == 204:
            return ApiResult(True, status=204)
        return ApiResult(True, data=r.json() if r.text else None, status=r.status_code)
    except requests.Timeout:
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        return ApiResult(False, error="connection")
    except ValueError:
        return ApiResult(False, error="invalid_json")
    except requests.RequestException as exc:
        return ApiResult(False, error=str(exc)[:200])

def api_delete(url, **kw):
    """Safe DELETE with typed result"""
    try:
        r = requests.delete(url, timeout=kw.pop("timeout", config.HTTP_TIMEOUT), **kw)
        if r.status_code < 200 or r.status_code >= 300:
            log.warning("API DELETE %s: %s", r.status_code, r.text[:100])
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, status=r.status_code)
    except requests.Timeout:
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        return ApiResult(False, error="connection")
    except requests.RequestException as exc:
        return ApiResult(False, error=str(exc)[:200])

def api_delete(url, **kw):
    """Safe DELETE with typed result"""
    try:
        r = requests.delete(url, timeout=kw.pop("timeout", config.HTTP_TIMEOUT), **kw)
        if r.status_code < 200 or r.status_code >= 300:
            log.warning("API DELETE %s: %s", r.status_code, r.text[:100])
            return ApiResult(False, status=r.status_code, error=r.text[:200])
        return ApiResult(True, status=r.status_code)
    except requests.Timeout:
        return ApiResult(False, error="timeout")
    except requests.ConnectionError:
        return ApiResult(False, error="connection")
    except requests.RequestException as exc:
        return ApiResult(False, error=str(exc)[:200])