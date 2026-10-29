"""Ajudantes de tela compartilhados pelos testes."""
from __future__ import annotations

from playwright.sync_api import Page, Response


def open_page(page: Page, path: str, *, expect_status_below: int = 400) -> Response | None:
    resp = page.goto(path, wait_until="domcontentloaded")
    assert resp is not None, f"{path}: sem resposta"
    assert resp.status < expect_status_below, f"{path}: HTTP {resp.status}"
    return resp


def horizontal_overflow(page: Page) -> int:
    """Quantos px a página passa da largura da tela (no celular a página não pode rolar pro lado)."""
    return page.evaluate("() => Math.max(0, document.documentElement.scrollWidth - window.innerWidth)")


def assert_no_horizontal_scroll(page: Page, path: str = "") -> None:
    over = horizontal_overflow(page)
    if over > 2:
        culprit = page.evaluate(
            """() => { const w = window.innerWidth; const els = [...document.querySelectorAll('body *')]
                 .filter(e => { const r = e.getBoundingClientRect(); return r.right > w + 2 && r.width > 0 && getComputedStyle(e).position !== 'fixed'; })
                 .map(e => (e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).slice(0, 3).join('.') : '')).slice(0, 90));
                 return els.slice(-3); }"""
        )
        raise AssertionError(f"{path}: página rola {over}px pro lado no celular — elementos: {culprit}")


def wait_hydrated(page: Page, timeout: int = 30_000) -> None:
    """Espera a rede acalmar (client components buscam dados depois de montar)."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
