"""Cliente HTTP da suíte (sem navegador) e leitura do sitemap para achar páginas reais.

O sitemap é a fonte dos dados de teste: a suíte não depende de chave de banco nem de massa fixa,
e sempre testa conteúdo que existe de verdade em produção.
"""
from __future__ import annotations

import functools
import re
from collections import defaultdict

import requests

from .env import settings

TIMEOUT = 30


@functools.lru_cache(maxsize=1)
def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = settings().user_agent
    return s


def get(path: str, *, ua: str | None = None, follow: bool = True, **kw) -> requests.Response:
    url = path if path.startswith("http") else settings().base_url + path
    headers = {"User-Agent": ua} if ua is not None else None  # "" testa o User-Agent vazio
    return session().get(url, headers=headers, allow_redirects=follow, timeout=TIMEOUT, **kw)


@functools.lru_cache(maxsize=1)
def sitemap_paths() -> dict[str, list[str]]:
    """{'/eventos': ['/eventos/slug-1', ...], ...} na ordem em que o sitemap lista."""
    r = get("/sitemap.xml")
    r.raise_for_status()
    base = settings().base_url
    groups: dict[str, list[str]] = defaultdict(list)
    for loc in re.findall(r"<loc>([^<]+)</loc>", r.text):
        path = loc.replace(base, "", 1) if loc.startswith(base) else re.sub(r"^https?://[^/]+", "", loc)
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            groups["/" + parts[0]].append(path)
    return dict(groups)


def sample(section: str, n: int = 1) -> list[str]:
    return sitemap_paths().get(section, [])[:n]
