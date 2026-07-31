"""HTML escaping"""
import html

def escape_html(value):
    """Escape HTML special characters"""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)
