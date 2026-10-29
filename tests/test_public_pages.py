"""Smoke das páginas públicas no celular: abrem (HTTP < 400), sem erro de JavaScript, com a marca no título
e sem rolar pro lado. As páginas de detalhe vêm do sitemap, então a suíte sempre testa conteúdo real."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from support.http import sample
from support.ui import assert_no_horizontal_scroll, open_page, wait_hydrated

pytestmark = pytest.mark.smoke

STATIC = [
    "/", "/eventos", "/eventos?view=lista", "/eventos?view=mes", "/clubes", "/motoclubes", "/mapa",
    "/voce-viu", "/reportar-roubo", "/ofertas", "/bandas", "/bares", "/oficinas", "/lojas", "/locutores",
    "/servicos-evento", "/motociclistas", "/motos-a-venda", "/noticias", "/memorial", "/ranking-de-km",
    "/para-clubes", "/termos-de-uso", "/politica-de-privacidade", "/enviar-flyer", "/login", "/cadastro",
    "/esqueci-senha",
]

# Seções do sitemap com página de detalhe
DETAIL_SECTIONS = ["/eventos", "/clubes", "/bandas", "/bares", "/oficinas", "/lojas", "/servicos-evento",
                   "/noticias", "/motoclubes", "/viagem"]


@pytest.mark.parametrize("path", STATIC)
def test_static_public_page(page: Page, path: str):
    open_page(page, path)
    wait_hydrated(page)
    assert "motoclub" in page.title().lower(), f"{path}: título sem a marca ({page.title()!r})"
    assert_no_horizontal_scroll(page, path)


@pytest.mark.parametrize("section", DETAIL_SECTIONS, ids=[s.strip("/") for s in DETAIL_SECTIONS])
def test_detail_page_from_sitemap(page: Page, section: str):
    paths = sample(section)
    if not paths:
        pytest.skip(f"sitemap sem páginas em {section}")
    path = paths[0]
    open_page(page, path)
    wait_hydrated(page)
    expect(page.locator("h1").first).to_be_visible()
    assert_no_horizontal_scroll(page, path)


def test_unknown_page_is_404(page: Page):
    resp = page.goto("/essa-pagina-nao-existe-qa", wait_until="domcontentloaded")
    assert resp is not None and resp.status == 404
