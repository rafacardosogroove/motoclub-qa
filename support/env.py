"""Configuração da suíte, só por variável de ambiente. Nenhuma chave é obrigatória: tudo aqui roda contra o site público.

- `QA_BASE_URL`  — site alvo (padrão: produção, https://motoclub.run)
- `QA_USER_AGENT` — navegador que a suíte declara. O portal recusa robôs nas páginas de conteúdo (403), então a suíte
  se apresenta como um Chrome comum, igual a um visitante.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36 motoclub-qa"
)


@dataclass(frozen=True)
class Settings:
    base_url: str
    user_agent: str


def settings() -> Settings:
    return Settings(
        base_url=os.environ.get("QA_BASE_URL", "https://motoclub.run").rstrip("/"),
        user_agent=os.environ.get("QA_USER_AGENT", DEFAULT_UA),
    )
