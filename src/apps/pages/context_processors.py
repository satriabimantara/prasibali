from .features import AVAILABLE_FEATURES, COMING_SOON_FEATURES


def site_nav(request):
    """Feature lists for the navbar dropdown and the mobile menu (shared by every page)."""
    return {"nav_features": AVAILABLE_FEATURES, "nav_features_soon": COMING_SOON_FEATURES}
