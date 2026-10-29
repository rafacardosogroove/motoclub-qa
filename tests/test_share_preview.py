"""Preview de link no WhatsApp: o card grande só aparece se a og:image for exatamente o que as meta tags declaram.

O navegador mostra qualquer JPEG; o crawler do WhatsApp não. Ele desiste do card em silêncio quando a imagem
é progressive, tem perfil ICC, não bate com og:image:width/height ou vem sem Content-Length.
Estes testes olham a página como o crawler (User-Agent do facebookexternalhit) e a imagem byte a byte.
"""
from __future__ import annotations

import html
import re

import pytest

from support import jpeg
from support.http import get, sample

pytestmark = [pytest.mark.share, pytest.mark.api]

CRAWLER_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"

# Achado A1 (docs/estudos-de-caso.md): página de clube não declara og:image — o link vai pro WhatsApp sem imagem,
# mesmo quando o clube tem brasão. strict=True: quando corrigirem, o teste passa a reprovar até tirar a marca.
CLUB_WITHOUT_OG_IMAGE = pytest.mark.xfail(reason="achado A1: página de clube sem og:image", strict=True)
SHARED_PAGES = sample("/eventos", 3) + [pytest.param(p, marks=CLUB_WITHOUT_OG_IMAGE) for p in sample("/clubes", 1)]


def og_tags(page_html: str) -> dict[str, str]:
    tags = {}
    for prop, content in re.findall(r'<meta\s+property="(og:[a-z:_]+)"\s+content="([^"]*)"', page_html):
        tags.setdefault(prop, html.unescape(content))
    return tags


@pytest.fixture(scope="module", params=SHARED_PAGES or [None],
                ids=lambda p: "/".join((p or "/nenhuma").strip("/").split("/")[:2])[:48])
def shared(request):
    if not request.param:
        pytest.skip("sitemap sem eventos/clubes")
    r = get(request.param, ua=CRAWLER_UA)
    assert r.status_code == 200, f"{request.param}: crawler recebeu HTTP {r.status_code}"
    return request.param, og_tags(r.text)


def test_page_declares_complete_og_tags(shared):
    path, tags = shared
    for prop in ("og:title", "og:description", "og:url", "og:image"):
        assert tags.get(prop), f"{path}: falta {prop}"
    assert tags["og:image"].startswith("https://"), f"{path}: og:image precisa ser URL absoluta https"


def test_og_image_matches_what_whatsapp_expects(shared):
    path, tags = shared
    assert tags.get("og:image"), f"{path}: falta og:image"
    r = get(tags["og:image"], ua=CRAWLER_UA)
    assert r.status_code == 200, f"{path}: og:image respondeu HTTP {r.status_code}"
    assert r.headers.get("content-length"), f"{path}: og:image sem Content-Length (o WhatsApp desiste)"

    served = r.headers.get("content-type", "").split(";")[0]
    declared_type = tags.get("og:image:type")
    if declared_type and served != declared_type:
        if "/api/og" in tags["og:image"]:
            pytest.xfail(f"achado A2, ainda aberto: banner de evento sem imagem declara {declared_type} e serve {served}")
        pytest.fail(f"{path}: og:image:type declara {declared_type}, servidor manda {served}")
    if served != "image/jpeg":
        return  # as regras de marcador abaixo são de JPEG

    info = jpeg.inspect(r.content)
    assert not info.progressive, f"{path}: JPEG progressive — o WhatsApp não monta o card grande"
    assert not info.has_icc, f"{path}: JPEG com perfil ICC"
    if tags.get("og:image:width") and tags.get("og:image:height"):
        declared = (int(tags["og:image:width"]), int(tags["og:image:height"]))
        assert (info.width, info.height) == declared, (
            f"{path}: meta tags declaram {declared}, imagem real é {(info.width, info.height)}")
