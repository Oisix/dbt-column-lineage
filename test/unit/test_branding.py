"""/api/v1/branding は設定を CSS/URL にそのまま流すので、不正値を捨てることと、ファイル/環境変数の優先順位を保証する。"""
import json

from dbt_column_lineage import branding, constants

ENV_ATTRS = ('BRAND_NAME', 'BRAND_LOGO_URL', 'BRAND_FAVICON_URL', 'BRAND_PRIMARY_COLOR', 'BRAND_FONT_URL', 'BRAND_FONT_FAMILY')


def _branding(monkeypatch, tmp_path, file=None, **env):
    for attr in ENV_ATTRS:
        monkeypatch.setattr(constants, attr, env.get(attr))
    path = tmp_path / 'brand.json'
    if file is not None:
        path.write_text(file if isinstance(file, str) else json.dumps(file))
    monkeypatch.setattr(constants, 'BRAND_CONFIG', str(path))
    return branding.build_branding()


def test_unset_and_missing_file_returns_empty(monkeypatch, tmp_path):
    assert _branding(monkeypatch, tmp_path) == {}


def test_valid_env_values_pass_through(monkeypatch, tmp_path):
    got = _branding(
        monkeypatch, tmp_path,
        BRAND_NAME=' Acme Analytics ',
        BRAND_LOGO_URL='https://cdn.example.com/logo.svg',
        BRAND_PRIMARY_COLOR='#0f766e',
        BRAND_FONT_URL='https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap',
        BRAND_FONT_FAMILY="Inter, Helvetica, Arial, sans-serif",
    )
    assert got == {
        'name': 'Acme Analytics',
        'logoUrl': 'https://cdn.example.com/logo.svg',
        'primaryColor': '#0f766e',
        'fontUrl': 'https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap',
        'fontFamily': "Inter, Helvetica, Arial, sans-serif",
    }


def test_config_file_is_used_and_env_overrides_per_key(monkeypatch, tmp_path):
    file = {'name': 'Acme', 'logoUrl': '/static/logo.svg', 'primaryColor': '#0f766e'}
    got = _branding(monkeypatch, tmp_path, file=file, BRAND_PRIMARY_COLOR='#123456')
    assert got == {'name': 'Acme', 'logoUrl': '/static/logo.svg', 'primaryColor': '#123456'}


def test_broken_or_wrong_shape_file_is_ignored(monkeypatch, tmp_path):
    assert _branding(monkeypatch, tmp_path, file='{not json') == {}
    assert _branding(monkeypatch, tmp_path, file=['a']) == {}
    assert _branding(monkeypatch, tmp_path, file={'name': 123, 'primaryColor': ['#fff']}) == {}


def test_unsafe_values_are_dropped(monkeypatch, tmp_path):
    got = _branding(
        monkeypatch, tmp_path,
        file={'logoUrl': 'javascript:alert(1)'},
        BRAND_FAVICON_URL='http://insecure.example.com/x.png',
        BRAND_PRIMARY_COLOR='red; background:url(//evil)',
        BRAND_FONT_URL='data:text/css,body{}',
        BRAND_FONT_FAMILY='x; } body { display:none',
    )
    assert got == {}
