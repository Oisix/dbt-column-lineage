import json
import logging
import os
import re

from dbt_column_lineage import constants

logger = logging.getLogger(__name__)

# レスポンスのキー -> 個別指定の環境変数(constants の属性名)
ENV_KEYS = {
    'name': 'BRAND_NAME',
    'logoUrl': 'BRAND_LOGO_URL',
    'faviconUrl': 'BRAND_FAVICON_URL',
    'primaryColor': 'BRAND_PRIMARY_COLOR',
    'fontUrl': 'BRAND_FONT_URL',
    'fontFamily': 'BRAND_FONT_FAMILY',
}


def _read_config_file() -> dict:
    path = constants.BRAND_CONFIG
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f'ignoring brand config {path}: {e}')
        return {}
    return data if isinstance(data, dict) else {}


def build_branding() -> dict:
    """ブランド設定(任意の JSON ファイル + BRAND_* 環境変数)を検証して返す。色とフォントは CSS に、
    URL は img/link に流れるので、形式が不正な値は黙って捨てる(スタイル注入や javascript: URL を避けるため)。"""
    def url(v):
        return v if re.fullmatch(r'(https://|/)[^\s"\'<>]+', v) else None

    def color(v):
        return v if re.fullmatch(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})', v) else None

    def font_family(v):
        return v if re.fullmatch(r"[\w\s,'\"-]+", v) else None

    validators = {
        'name': lambda v: v.strip() or None,
        'logoUrl': url,
        'faviconUrl': url,
        'primaryColor': color,
        'fontUrl': url,
        'fontFamily': font_family,
    }
    file_values = _read_config_file()
    branding = {}
    for key, env_attr in ENV_KEYS.items():
        value = getattr(constants, env_attr) or file_values.get(key)
        if isinstance(value, str) and (checked := validators[key](value)):
            branding[key] = checked
    return branding
