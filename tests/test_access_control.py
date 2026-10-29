"""Controle de acesso visto de fora, sem login: área logada manda pro login, rotas internas recusam,
e o filtro de robôs barra raspador sem barrar quem precisa ler a página (Google, WhatsApp, visitante)."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from support.http import get

pytestmark = [pytest.mark.security, pytest.mark.api]

PROTECTED_PAGES = ["/dashboard", "/dashboard/meu-perfil", "/dashboard/meu-clube", "/admin"]
INTERNAL_APIS = ["/api/admin/scraper-ips", "/api/cron/news"]

ALLOWED_UAS = {
    "googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "whatsapp": "WhatsApp/2.23.20.0",
    "facebook": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
}
BLOCKED_UAS = {
    "python-requests": "python-requests/2.31.0",
    "scrapy": "Scrapy/2.11 (+https://scrapy.org)",
    "headless-chrome": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 HeadlessChrome/141.0.0.0 Safari/537.36",
    "vazio": "",
}


@pytest.mark.parametrize("path", PROTECTED_PAGES)
def test_logged_area_redirects_to_login(path):
    r = get(path, follow=False)
    assert r.status_code in (302, 303, 307, 308), f"{path}: esperava redirecionar, veio HTTP {r.status_code}"
    target = urlparse(r.headers["location"])
    assert target.path == "/login", f"{path}: redirecionou para {r.headers['location']}"
    assert parse_qs(target.query).get("redirect") == [path], "o login precisa saber pra onde voltar"


@pytest.mark.parametrize("path", INTERNAL_APIS)
def test_internal_api_refuses_anonymous(path):
    r = get(path, follow=False)
    assert r.status_code in (401, 403), f"{path}: anônimo recebeu HTTP {r.status_code}"


@pytest.mark.parametrize("name", ALLOWED_UAS)
def test_bot_guard_lets_previews_and_search_through(name):
    r = get("/eventos", ua=ALLOWED_UAS[name])
    assert r.status_code == 200, f"{name} foi barrado (HTTP {r.status_code}) — quebra preview de link ou indexação"


@pytest.mark.parametrize("name", BLOCKED_UAS)
def test_bot_guard_blocks_scrapers(name):
    r = get("/eventos", ua=BLOCKED_UAS[name])
    assert r.status_code == 403, f"raspador '{name}' passou (HTTP {r.status_code})"
