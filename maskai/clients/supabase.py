"""MASKAI — Supabase REST client"""
import logging
from maskai.clients.http import api_get, api_post, api_patch, api_delete
from maskai.config import SUPABASE_URL, SUPABASE_HEADERS
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

def supabase_patch(table, filters, data):
    """Supabase PATCH. Returns ApiResult — check .ok"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if filters:
        q = "&".join(f"{k}=eq.{v}" for k, v in filters)
        url += f"?{q}"
    return api_patch(url, json=data, headers=SUPABASE_HEADERS)

