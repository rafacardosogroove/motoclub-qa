"""Fixtures da suíte de QA do MotoClub Brasil (Python + pytest + Playwright).

- Celular primeiro: todo teste de tela roda em 375x812 com toque — a maioria dos motociclistas acessa pelo celular.
- Erro de JavaScript não tratado na página (pageerror) reprova o teste, mesmo que a tela "pareça" certa.
- Só leitura: nada aqui grava no banco, então a suíte pode rodar contra produção.
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page

from support.env import settings

MOBILE = {"viewport": {"width": 375, "height": 812}, "is_mobile": True, "has_touch": True, "device_scale_factor": 2}

# Erros de página que não são bug do portal
IGNORED_PAGE_ERRORS = [
    re.compile(r"ResizeObserver loop", re.I),
    re.compile(r"Failed to load chunk|ChunkLoadError|Loading chunk", re.I),  # o portal recarrega sozinho após deploy
    re.compile(r"NEXT_REDIRECT"),
    re.compile(r"Failed to fetch|NetworkError|Load failed", re.I),  # requisição cortada pela navegação
]


def pytest_configure(config):
    for m in (
        "smoke: páginas públicas abrem sem erro, no celular",
        "share: preview de link (og:image) que o WhatsApp monta",
        "security: controle de acesso visto de fora, sem login",
        "api: só HTTP, sem navegador",
    ):
        config.addinivalue_line("markers", m)


@pytest.fixture(scope="session")
def cfg():
    return settings()


@pytest.fixture(scope="session")
def base_url(cfg):
    return cfg.base_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url, cfg):
    return {**browser_context_args, **MOBILE, "base_url": base_url, "user_agent": cfg.user_agent,
            "locale": "pt-BR", "timezone_id": "America/Sao_Paulo"}


@pytest.fixture
def page(page: Page, request):
    """O `page` do pytest-playwright + timeouts folgados + coleta de erro de JavaScript (checado no fim do teste)."""
    page.set_default_timeout(30_000)
    page.set_default_navigation_timeout(60_000)
    request.node.js_errors = []
    page.on("pageerror", lambda e: request.node.js_errors.append(str(e)))
    yield page


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    """Erro de JavaScript reprova o próprio teste (fase call, não teardown), para valer `xfail` de achado conhecido."""
    result = yield
    real = [e for e in getattr(item, "js_errors", []) if not any(p.search(e) for p in IGNORED_PAGE_ERRORS)]
    assert not real, "erro de JavaScript na página:\n" + "\n".join(real[:5])
    return result
