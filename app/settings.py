import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]


def local_url(url):
    parsed=urlparse(url)
    if parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.scheme not in ('http','https') or parsed.username or parsed.password:
        raise ValueError('Service URL must use loopback and no embedded credentials')
    return url.rstrip('/')


def load_settings(path=None):
    settings=json.loads(Path(path or ROOT/'config/settings.json').read_text(encoding='utf-8'))
    for key in ('es_url','geoserver_url','llm_url'):
        settings[key]=local_url(os.getenv(key.upper(),settings[key]))
    for name in settings['indices'].values():
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',name):
            raise ValueError('Invalid physical index name')
    return settings
