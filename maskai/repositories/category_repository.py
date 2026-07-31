"""Category repository"""
import logging
from maskai.clients.supabase import supabase_get, supabase_post, supabase_patch, supabase_delete
log = logging.getLogger("maskai.repo.category")

# ── Category Ownership Helpers ──
def get_accessible_category(cat_id, user_id):
    """Get category if user can access it (global or owned)"""
    result = supabase_get("maskai_categories", {"id": f"eq.{cat_id}", "select": "id,name,icon,type,user_id"})
    if not result.ok:
        return None
    cats = result.data if isinstance(result.data, list) else []
    if not cats:
        return None
    cat = cats[0]
    if cat.get("user_id") not in (0, user_id):
        return None
    return cat

def is_category_owner(cat, user_id):
    """Check if user owns this category (not global, not other user)"""
    return cat and cat.get("user_id") == user_id

def list_accessible_categories(user_id):
    """List categories visible to user: own + global"""
    # Use two queries — Supabase doesn't support OR
    r1 = supabase_get("maskai_categories", {"user_id": f"eq.{user_id}", "select": "id,name,icon,type,user_id"})
    r2 = supabase_get("maskai_categories", {"user_id": "eq.0", "select": "id,name,icon,type,user_id"})
    own = r1.data if r1.ok and isinstance(r1.data, list) else []
    global_cats = r2.data if r2.ok and isinstance(r2.data, list) else []
    return own + global_cats

def delete_owned_category(cat_id, user_id):
    """Delete category if user owns it. Uses id+user_id filter"""
    cat = get_accessible_category(cat_id, user_id)
    if not cat:
        return False, "Kategori tidak ditemukan"
    if cat.get("user_id") == 0:
        return False, "Kategori global tidak bisa dihapus"
    # Delete with dual filter — extra safety
    r = api_delete(f"{SUPABASE_URL}/rest/v1/maskai_categories?id=eq.{cat_id}&user_id=eq.{user_id}", headers=SUPABASE_HEADERS)
    if not r.ok:
        return False, "Gagal menghapus"
    return True, None

def update_owned_category(cat_id, user_id, payload):
    """Update category if user owns it. Uses id+user_id filter"""
    cat = get_accessible_category(cat_id, user_id)
    if not cat:
        return False, "Kategori tidak ditemukan"
    if cat.get("user_id") == 0:
        return False, "Kategori global tidak bisa diedit"
    result = supabase_patch("maskai_categories", [("id", cat_id), ("user_id", user_id)], payload)
    if not result.ok:
        return False, "Gagal update"
    return True, None

# ── Commands ──
