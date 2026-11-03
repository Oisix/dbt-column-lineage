import re

from dbt_column_lineage import constants


def build_branding() -> dict:
    """BRAND_* を検証して返す。色とフォントは CSS に、URL は img/link に流れるので、
    形式が不正な値は黙って捨てる(スタイル注入や javascript: URL を避けるため)。"""
    def url(v):
        return v if v and re.fullmatch(r'(https://|/)[^\s"\'<>]+', v) else None

    def color(v):
        return v if v and re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', v) else None

    def font_family(v):
        return v if v and re.fullmatch(r"[\w\s,'\"-]+", v) else None

    name = constants.BRAND_NAME
    branding = {
        'name': name.strip() if name and name.strip() else None,
        'logoUrl': url(constants.BRAND_LOGO_URL),
        'faviconUrl': url(constants.BRAND_FAVICON_URL),
        'primaryColor': color(constants.BRAND_PRIMARY_COLOR),
        'fontUrl': url(constants.BRAND_FONT_URL),
        'fontFamily': font_family(constants.BRAND_FONT_FAMILY),
    }
    return {k: v for k, v in branding.items() if v}
