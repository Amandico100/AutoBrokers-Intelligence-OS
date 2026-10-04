"""O link do relatório sai COM endereço no ambiente de produção (programa multicálculo, passo 0.5).

📊 04/10/2026: o `smith-api` de produção tem `SMITH_WEB_URL` e `FRONTEND_URL`, mas não tem
`PUBLIC_APP_URL` nem `NEXT_PUBLIC_APP_URL`. A rota de compartilhar e o `report_tool` liam só as duas
últimas e devolviam `url = None` — "link criado", sem link. Este teste chama a ROTA REAL de
compartilhar (`app.api.artifacts.compartilhar`) com o serviço de artefatos em dublê.

Rodar:  cd backend && python tests/test_o_link_do_relatorio_tem_endereco.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VARS = ("PUBLIC_APP_URL", "NEXT_PUBLIC_APP_URL", "SMITH_WEB_URL", "FRONTEND_URL")
TOKEN = "t" * 43


class _ServicoDuble:
    def __init__(self, _db):
        pass

    def compartilhar(self, **_kw):
        return {"token": TOKEN, "expires_at": "2026-11-03T00:00:00+00:00"}


def _rota(env: dict) -> dict:
    for v in VARS:
        os.environ.pop(v, None)
    os.environ.update(env)
    from app.api import artifacts as mod

    mod._autorizar = lambda _k: None
    mod.get_supabase_client = lambda: None
    mod.ArtifactService = _ServicoDuble
    payload = mod.CompartilharIn(company_id="c-1", artifact_id="a-1")
    return asyncio.run(mod.compartilhar(payload, x_internal_key="x"))


def main() -> int:
    falhas = 0

    def checa(nome, cond):
        nonlocal falhas
        print(("PASS " if cond else "FAIL ") + nome)
        falhas += 0 if cond else 1

    # [1] o ambiente de PRODUÇÃO (só SMITH_WEB_URL e FRONTEND_URL) -> o link sai com endereço
    r = _rota({"SMITH_WEB_URL": "https://painel.exemplo/", "FRONTEND_URL": "https://outro.exemplo"})
    checa("[1] produção: url com endereço e /r/<token>", r.get("url") == f"https://painel.exemplo/r/{TOKEN}")

    # [2] só FRONTEND_URL também serve
    r = _rota({"FRONTEND_URL": "https://front.exemplo"})
    checa("[2] só FRONTEND_URL: url com endereço", r.get("url") == f"https://front.exemplo/r/{TOKEN}")

    # [3] quem já configurou a pública continua vencendo
    r = _rota({"PUBLIC_APP_URL": "https://publico.exemplo", "FRONTEND_URL": "https://front.exemplo"})
    checa("[3] PUBLIC_APP_URL vence", r.get("url") == f"https://publico.exemplo/r/{TOKEN}")

    # [4] CONTROLE: nenhum endereço configurado -> url None (o teste CONSEGUE ver a diferença)
    r = _rota({})
    checa("[4] controle: sem endereço -> None", r.get("url") is None)

    # [4b] a base é VALIDADA como a do irmão TS `lib/public-url.ts` (red team 04/10):
    # endereço interno, localhost, sem esquema ou com caminho NÃO vai para o segurado.
    casos = [
        ({"SMITH_WEB_URL": "http://smith-web:3000", "FRONTEND_URL": "https://front.exemplo.com.br"},
         f"https://front.exemplo.com.br/r/{TOKEN}", "host interno sem ponto cai para o próximo"),
        ({"FRONTEND_URL": "http://localhost:3000"}, None, "localhost -> sem link"),
        ({"FRONTEND_URL": "http://127.0.0.1:3000"}, None, "127.0.0.1 -> sem link"),
        ({"SMITH_WEB_URL": "app.exemplo.com.br"}, None, "sem esquema -> sem link"),
        ({"SMITH_WEB_URL": "ftp://app.exemplo.com.br"}, None, "esquema que não é http(s) -> sem link"),
        ({"SMITH_WEB_URL": "https://app.exemplo.com.br/dashboard?x=1"},
         f"https://app.exemplo.com.br/r/{TOKEN}", "caminho e query saem: fica a origem"),
        ({"SMITH_WEB_URL": "  https://app.exemplo.com.br//  "},
         f"https://app.exemplo.com.br/r/{TOKEN}", "espaço e barras no fim saem"),
        ({"SMITH_WEB_URL": "http://smith-web:3000, https://app.exemplo.com.br"},
         f"https://app.exemplo.com.br/r/{TOKEN}", "lista com vírgula: a 1ª válida"),
        ({"PUBLIC_APP_URL": '"https://publico.exemplo.com"'},
         f"https://publico.exemplo.com/r/{TOKEN}", "aspas em volta saem"),
        ({"PUBLIC_APP_URL": "   ", "FRONTEND_URL": "https://front.exemplo.com.br"},
         f"https://front.exemplo.com.br/r/{TOKEN}", "variável em branco passa a vez"),
        # confirmação de 04/10: usuário e SENHA da URL iam inteiros para o WhatsApp do segurado
        ({"SMITH_WEB_URL": "https://usuario:s3nh4@app.exemplo.com.br/painel"},
         f"https://app.exemplo.com.br/r/{TOKEN}", "usuário e senha da URL saem"),
        ({"SMITH_WEB_URL": "https://usuario@App.Exemplo.com.br:8443"},
         f"https://app.exemplo.com.br:8443/r/{TOKEN}", "usuário sai, a porta fica"),
        # CONTROLE da mesma linha: sem credencial, a porta continua (a régua não come a porta)
        ({"SMITH_WEB_URL": "https://app.exemplo.com.br:8443"},
         f"https://app.exemplo.com.br:8443/r/{TOKEN}", "controle: porta sem credencial fica"),
    ]
    for env, esperado, nome in casos:
        r = _rota(env)
        checa(f"[4b] {nome}", r.get("url") == esperado)

    # [5] um lugar só: nenhum dos dois leitores reimplementa a base
    raiz = Path(__file__).resolve().parents[1]
    for rel in ("app/agents/tools/report_tool.py", "app/api/artifacts.py"):
        texto = (raiz / rel).read_text(encoding="utf-8")
        checa(f"[5] {rel} usa base_publica_do_app", "base_publica_do_app()" in texto
              and 'os.getenv("PUBLIC_APP_URL")' not in texto)

    print(f"\n{falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
