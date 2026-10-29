"""Inspeção de JPEG no nível dos marcadores — o que o crawler do WhatsApp olha e o navegador ignora.

Pillow diz o tamanho; os marcadores dizem o resto: progressive (SOF2) e perfil ICC (APP2) fazem o WhatsApp
desistir do card grande sem dar erro nenhum. Foi a causa raiz do bug do card de evento (ver docs/estudos-de-caso.md).
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class JpegInfo:
    width: int
    height: int
    progressive: bool
    has_icc: bool
    has_jfif: bool


def inspect(data: bytes) -> JpegInfo:
    assert data[:2] == b"\xff\xd8", "não é JPEG (falta o SOI)"
    progressive = has_icc = has_jfif = False
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xDA:  # início dos dados da imagem: acabaram os cabeçalhos
            break
        length = int.from_bytes(data[i + 2:i + 4], "big")
        payload = data[i + 4:i + 2 + length]
        if marker == 0xC2:
            progressive = True
        elif marker == 0xE0 and payload.startswith(b"JFIF\x00"):
            has_jfif = True
        elif marker == 0xE2 and payload.startswith(b"ICC_PROFILE\x00"):
            has_icc = True
        i += 2 + length
    with Image.open(io.BytesIO(data)) as im:
        width, height = im.size
    return JpegInfo(width, height, progressive, has_icc, has_jfif)
