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

def supabase_delete(table, field_or_filters, value=None):
    """Supabase DELETE. Accepts (table, field, value) or (table, [(k,v),...])"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if isinstance(field_or_filters, list):
        q = "&".join(f"{k}=eq.{v}" for k, v in field_or_filters)
        url += f"?{q}"
    else:
        url += f"?{field_or_filters}=eq.{value}"
    return api_delete(url, headers=SUPABASE_HEADERS)

def supabase_patch(table, filters, data):
    """Supabase PATCH. Returns ApiResult — check .ok"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if filters:
        q = "&".join(f"{k}=eq.{v}" for k, v in filters)
        url += f"?{q}"
    return api_patch(url, json=data, headers=SUPABASE_HEADERS)

