# motoclub-qa

[![QA em produção](../../actions/workflows/qa.yml/badge.svg)](../../actions/workflows/qa.yml)

Suíte de testes automatizados do **[MotoClub Brasil](https://motoclub.run)** — plataforma para motociclistas e moto clubes
(clubes, eventos, mapa, alertas de moto roubada) que eu idealizei, construí e testo. Roda **contra produção**, toda
semana, sem nenhuma chave de acesso: só olha o site como um visitante, um robô de busca ou o WhatsApp olhariam.

> **English summary.** Automated QA suite (Python, pytest, Playwright) for a real production platform I built.
> Mobile-first E2E smoke, share-preview checks that inspect JPEG markers the way WhatsApp's crawler does, access-control
> and bot-guard checks, and a map API contract test. Read-only, runs weekly on GitHub Actions against production.
> [Case studies](docs/estudos-de-caso.md) document real silent bugs — no error, no log — and how they were found.

Autor: **Rafael Cardoso** — SDET / QA Lead · [LinkedIn](https://www.linkedin.com/in/rafael-cardoso-da-costa/)

---

## O que é testado

| Arquivo | O quê | Por quê |
|---|---|---|
| [`test_public_pages.py`](tests/test_public_pages.py) | ~40 páginas públicas abrem no **celular (375px)**, sem erro de JavaScript, com título e sem rolar pro lado | A maioria dos motociclistas usa o celular; erro de JS reprova mesmo com a tela "parecendo" certa |
| [`test_share_preview.py`](tests/test_share_preview.py) | A `og:image` vista como o crawler do WhatsApp: tamanho real × declarado, JPEG baseline, sem ICC, `Content-Length`, tipo servido × declarado | O WhatsApp descarta o card grande **em silêncio** ([caso 2](docs/estudos-de-caso.md#2-o-link-no-whatsapp-às-vezes-vinha-com-imagem-grande-às-vezes-sem)) |
| [`test_access_control.py`](tests/test_access_control.py) | Área logada redireciona pro login (com retorno), rotas internas recusam anônimo, filtro de robôs barra raspador e deixa passar Google/WhatsApp | Bloquear o WhatsApp por engano mata o preview de link; liberar raspador entrega o conteúdo |
| [`test_map_api.py`](tests/test_map_api.py) | Contrato da API do mapa: camadas presentes, coordenadas válidas, pinos de estado brasileiro dentro do Brasil, sem pilha de pinos no mesmo ponto | Coordenada errada não dá erro: o pino só aparece no lugar errado |

**Dados de teste vêm do `sitemap.xml`.** A suíte não depende de massa fixa nem de acesso ao banco, e sempre testa
conteúdo que existe de verdade.

## Decisões de projeto

- **Só leitura.** Nada aqui grava em produção. Os testes que criam contas e dados (permissões com sessão real,
  ver a [técnica](docs/estudos-de-caso.md#técnica-que-atravessa-vários-casos-testar-com-sessão-real-nunca-com-a-chave-de-serviço))
  ficam no repositório privado do produto, porque precisam da chave de serviço do banco.
- **Celular primeiro.** Todo teste de tela roda em 375x812 com toque.
- **Achado conhecido não deixa o CI vermelho, mas também não some.** Fica como `xfail` com o motivo e o número do
  achado; vários com `strict=True`, então quando o bug é corrigido o teste reprova até a marca sair.
- **Erro de JavaScript reprova o próprio teste** (fase *call*, via hook em [`conftest.py`](conftest.py)), não o
  teardown — assim o `xfail` de um achado conhecido funciona.
- **Evidência na falha:** screenshot, vídeo e trace do Playwright só quando falha; relatório HTML sempre.

## Achados

Na primeira execução contra produção (28/10/2026), a suíte encontrou 4 problemas que ninguém tinha relatado.
Um deles foi corrigido no mesmo dia — e o `xfail(strict=True)` avisou sozinho. Detalhes no fim dos
[estudos de caso](docs/estudos-de-caso.md#achados-desta-suíte-28102026).

## Como rodar

```bash
python -m venv .venv && . .venv/bin/activate   # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
pytest --html=report/index.html --self-contained-html
```

Só HTTP, sem navegador (segundos): `pytest -m api`. Outro ambiente: `QA_BASE_URL=https://staging.exemplo pytest`.

## Stack

Python 3.12 · pytest · Playwright · requests · Pillow · pytest-html · GitHub Actions
