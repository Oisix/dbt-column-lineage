"""/api/v1/branding は BRAND_* を CSS/URL にそのまま流すので、不正値を捨てることを保証する。"""
from dbt_column_lineage import branding, constants


def _branding(monkeypatch, **env):
    for key in ('BRAND_NAME', 'BRAND_LOGO_URL', 'BRAND_FAVICON_URL', 'BRAND_PRIMARY_COLOR', 'BRAND_FONT_URL', 'BRAND_FONT_FAMILY'):
        monkeypatch.setattr(constants, key, env.get(key))
    return branding.build_branding()


def test_unset_returns_empty(monkeypatch):
    assert _branding(monkeypatch) == {}


def test_valid_values_pass_through(monkeypatch):
    got = _branding(
        monkeypatch,
        BRAND_NAME=' Spry Analytics ',
        BRAND_LOGO_URL='https://cdn.example.com/logo.svg',
        BRAND_PRIMARY_COLOR='#7737ab',
        BRAND_FONT_URL='https://fonts.googleapis.com/css2?family=Manrope:wght@400;700&display=swap',
        BRAND_FONT_FAMILY="Manrope, Helvetica, Arial, sans-serif",
    )
    assert got == {
        'name': 'Spry Analytics',
        'logoUrl': 'https://cdn.example.com/logo.svg',
        'primaryColor': '#7737ab',
        'fontUrl': 'https://fonts.googleapis.com/css2?family=Manrope:wght@400;700&display=swap',
        'fontFamily': "Manrope, Helvetica, Arial, sans-serif",
    }


def test_unsafe_values_are_dropped(monkeypatch):
    got = _branding(
        monkeypatch,
        BRAND_LOGO_URL='javascript:alert(1)',
        BRAND_FAVICON_URL='http://insecure.example.com/x.png',
        BRAND_PRIMARY_COLOR='red; background:url(//evil)',
        BRAND_FONT_URL='data:text/css,body{}',
        BRAND_FONT_FAMILY='x; } body { display:none',
    )
    assert got == {}
