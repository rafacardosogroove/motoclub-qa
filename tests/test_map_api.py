"""Contrato da API que alimenta o mapa (todas as camadas numa resposta só).

Coordenada errada não dá erro em lugar nenhum: o pino simplesmente aparece no lugar errado. Por isso o teste
confere coordenada por coordenada — e procura o padrão de um bug real, em que todos os postos de uma cidade
ganhavam a mesma coordenada e viravam uma pilha de pinos no centro da cidade.
"""
from __future__ import annotations

from collections import Counter

import pytest

from support.http import get

pytestmark = pytest.mark.api

# Brasil com folga (inclui ilhas oceânicas)
BR_LAT, BR_LNG = (-34.5, 6.0), (-75.0, -28.0)
BR_UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
          "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}  # clube/sede fora do Brasil existe e é legítimo
MAX_SAME_SPOT = 3  # mais que isso no mesmo ponto exato, numa camada, é geocodificação caindo no centro da cidade

# Pilhas já conhecidas e reportadas (docs/estudos-de-caso.md, achado A3). Pilha NOVA reprova; se as conhecidas
# forem corrigidas, o teste avisa (XPASS) para tirar daqui.
KNOWN_STACKS = {
    ("oficinas", (-24.18334, -46.78962)),
    ("postos", (-24.18334, -46.78962)),
    ("postos", (-24.17998, -46.78581)),
}


@pytest.fixture(scope="module")
def layers():
    r = get("/api/mapa/pontos")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert isinstance(data, dict) and data, "resposta vazia"
    return data


def test_core_layers_present(layers):
    for name in ("clubes", "eventos", "oficinas"):
        assert name in layers, f"camada '{name}' sumiu da resposta"
        assert isinstance(layers[name], list)


def test_every_point_has_valid_coordinates(layers):
    bad = []
    for layer, items in layers.items():
        for item in items:
            lat, lng = item.get("lat"), item.get("lng")
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                bad.append(f"{layer}/{item.get('id')}: lat/lng ausente ({lat}, {lng})")
            elif not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
                bad.append(f"{layer}/{item.get('id')}: coordenada impossível ({lat}, {lng})")
    assert not bad, "\n".join(bad[:20])


def test_brazilian_points_are_inside_brazil(layers):
    """Se o estado é brasileiro, o pino tem que estar no Brasil (lat/lng trocados caem no oceano ou na África)."""
    bad = []
    for layer, items in layers.items():
        for item in items:
            state = item.get("state") or ""
            lat, lng = item.get("lat"), item.get("lng")
            if state.upper() in BR_UFS and isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                if not (BR_LAT[0] <= lat <= BR_LAT[1] and BR_LNG[0] <= lng <= BR_LNG[1]):
                    bad.append(f"{layer}/{item.get('id')} ({item.get('city')}/{state}): ({lat}, {lng})")
    assert not bad, "pinos fora do Brasil:\n" + "\n".join(bad[:20])


def test_no_pin_stacks_from_city_level_geocoding(layers):
    stacks: dict[tuple, int] = {}
    for layer, items in layers.items():
        if layer == "sedes":  # várias sedes podem dividir o mesmo endereço de propósito
            continue
        spots = Counter((round(i["lat"], 5), round(i["lng"], 5)) for i in items
                        if isinstance(i.get("lat"), (int, float)) and isinstance(i.get("lng"), (int, float)))
        stacks.update({(layer, spot): n for spot, n in spots.items() if n > MAX_SAME_SPOT})
    new = {k: n for k, n in stacks.items() if k not in KNOWN_STACKS}
    assert not new, "\n".join(f"{layer}: {n} pinos em {spot}" for (layer, spot), n in new.items())
    if stacks:
        pytest.xfail(f"achado A3, ainda aberto: {len(stacks)} pilhas de pinos conhecidas")
