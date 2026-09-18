from django.conf import settings

from menu.models import Restaurant


def panel(request):
    """Restaurant name/logo for the panel header, and the public menu's address."""
    if not request.path.startswith("/panel/"):
        return {}
    return {
        "panel_restaurant": Restaurant.load(),
        "menu_site_url": settings.MENU_SITE_URL,
    }
