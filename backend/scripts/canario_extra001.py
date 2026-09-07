# -*- coding: utf-8 -*-
"""O canário da SPEC-EXTRA-001, pela linha de comando.

```
--dry-run   (padrão) imprime o PLANO e o censo; não toca em nada.
--vivo      executa Q1–Q6 AQUI. Só funciona onde há Redis (o governador
            recusa mensagem fria sem ele — falha fechada, de propósito).
            Fora do contêiner, use a rota admin:
            POST /api/admin/canario/extra001  (cabeçalho X-Internal-Key)
```
Ambiente exigido no `--vivo`: `BILLING_CANARIO_ALLOWLIST` (≥ 2 números, só
dígitos, separados por vírgula) e `CANARIO_TESTE_B` (o destino; tem de estar na
allowlist). ⛔ Os valores nunca entram no repositório. ⛔ Nunca imprime telefone.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ["AUTOBROKERS_CANARIO"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="O canário da SPEC-EXTRA-001")
    ap.add_argument("--vivo", action="store_true", help="executa de verdade (precisa de Redis)")
    ap.add_argument("--dry-run", action="store_true", help="só imprime o plano (padrão)")
    ap.add_argument("--sem-limpeza", action="store_true", help="não desfaz o que criou")
    ap.add_argument("--esperar-retorno", type=int, default=0,
                    help="segundos esperando uma resposta REAL de TESTE-B pelo webhook (só depois do Implantar)")
    args = ap.parse_args()

    from app.services.canario_extra001 import RESULTA, plano, rodar

    if not args.vivo:
        out = plano(RESULTA)
        print("\n".join(out["linhas"]))
        return 0

    import asyncio

    out = asyncio.run(rodar(RESULTA, limpar=not args.sem_limpeza, esperar_retorno_s=args.esperar_retorno))
    print("\n".join(out["linhas"]))
    print(json.dumps(out["perguntas"], ensure_ascii=False, indent=1))
    return 0 if all(v.startswith("OK") for v in out["perguntas"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
