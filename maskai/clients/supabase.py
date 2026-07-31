"""Supabase REST client"""
import logging
from maskai.clients.http import api_get, api_post, api_patch, api_delete
log = logging.getLogger("maskai.supabase")
def supabase_get(table, params=None):
    """Supabase GET. Returns ApiResult — check .ok, use .data"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        if isinstance(params, dict):
            q = "&".join(f"{k}={v}" for k, v in params.items())
        else:
            q = "&".join(f"{k}={v}" for k, v in params)
        url += f"?{q}"
    return api_get(url, headers=SUPABASE_HEADERS)

def supabase_post(table, data):
    """Supabase POST. Returns ApiResult — check .ok, use .data"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    return api_post(url, json=data, headers=SUPABASE_HEADERS)

def supabase_delete(table, field, value):
    """Supabase DELETE. Returns ApiResult — check .ok"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{field}=eq.{value}"
    return api_delete(url, headers=SUPABASE_HEADERS)

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

def supabase_patch(table, filters, data):
    """Supabase PATCH. Returns ApiResult — check .ok"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if filters:
        q = "&".join(f"{k}=eq.{v}" for k, v in filters)
        url += f"?{q}"
    return api_patch(url, json=data, headers=SUPABASE_HEADERS)

