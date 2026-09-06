# -*- coding: utf-8 -*-
"""Propõe o Jeito de atender de uma corretora a partir das conversas dela.

```
--dry-run   (padrão) MEDE e IMPRIME. Não escreve uma linha.
--vivo      grava `tone_proposto` (+ origem, instante e evidência).
            🔴 NUNCA grava `tone`: publicar é ato da corretora, na tela.
```

## Por que este script existe

A leitura do site propõe um jeito **plausível**. As conversas propõem o jeito
**real** — 📊 06/09/2026: 11.981 mensagens escritas por humanos da corretora no
WhatsApp, e nenhuma delas jamais foi lida para nada. A Resulta abre afetiva,
com emoji e em primeira pessoa; a AutoFleet trata por Sr./Sra., sem emoji,
explicando o procedimento. Mesmos sócios, mesmo produto: o que difere é o
acervo, e é por isso que "tom padrão da casa" seria a resposta errada.

⚠️ A estatística é **determinística** e a regra que a traduz em escolhas está
escrita em `capture.escolhas_das_taxas` — não dentro de um prompt. A chamada de
modelo é OPCIONAL (`--com-modelo`) e serve só para princípios, termos
preferidos e o que evitar, sobre ≤60 trechos **anonimizados**.

⛔ Não imprime telefone, nome, e-mail nem trecho de conversa: só as taxas.
"""
from __future__ import annotations

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

#: 📊 MEDIDO em `select id, company_name from companies`, não lembrado.
RESULTA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"


def p(texto="") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Propõe o Jeito de atender (SPEC-098 U2.3)")
    ap.add_argument("--company", default=RESULTA)
    ap.add_argument("--vivo", action="store_true",
                    help="grava a PROPOSTA (tone_proposto). Nunca grava `tone`.")
    ap.add_argument("--dry-run", action="store_true", help="só mede e imprime (padrão)")
    ap.add_argument("--amostra", type=int, default=300)
    ap.add_argument("--com-modelo", action="store_true",
                    help="acrescenta princípios/termos/evitar com UMA chamada de modelo")
    args = ap.parse_args()

    from app.core.database import get_supabase_client
    from app.services.brand.capture import BrandCaptureService
    from app.services.brand.jeito_de_atender import ESCOLHAS, render

    svc = BrandCaptureService(get_supabase_client())

    llm = None
    if args.com_modelo:
        llm = svc._llm_de_marca(args.company)
        if llm is None:
            p("⚠️ modelo indisponível — seguindo só com a estatística")

    lido = svc.propor_jeito_das_conversas(args.company, amostra=args.amostra, llm=llm)

    if not lido.get("ok"):
        p("⛔ %s (lidas=%s · descartadas=%s)"
          % (lido.get("motivo"), lido.get("lidas"), lido.get("descartadas")))
        return 2

    taxas = lido["evidencia"]["taxas"]
    p("corretora %s… · %s" % (str(args.company)[:8], lido["evidencia"]["resumo"]))
    p("mensagens medidas: %d" % taxas.get("mensagens", 0))
    for chave in ("saudacao", "afetiva", "senhor_senhora", "voce", "emoji",
                  "primeira_pessoa", "passos", "tamanho_medio"):
        p("  %-16s %s" % (chave, taxas.get(chave)))

    p("")
    p("ESCOLHAS propostas (pela regra escrita em `escolhas_das_taxas`):")
    for campo in ESCOLHAS:
        valor = lido["jeito"].get(campo)
        p("  %-12s %s" % (campo, ESCOLHAS[campo].get(valor, "—") if valor else "—"))

    bloco = render(lido["jeito"])
    p("")
    p("O BLOCO que iria ao prompt (%d caracteres):" % len(bloco))
    p(bloco or "  (vazio)")

    if not args.vivo:
        p("")
        p("PLANO (nada foi gravado — rode com `--vivo`):")
        p("  update brand_profiles set tone_proposto=<acima>,")
        p("         tone_proposto_origem='conversas', tone_proposto_em=now(),")
        p("         tone_evidencia=<as taxas + o resumo>")
        p("  🔴 `tone` NÃO entra no update. A corretora publica na tela.")
        return 0

    svc.propor_jeito(args.company, lido["jeito"], origem="conversas",
                     evidencia=lido["evidencia"])
    conferido = (svc.db.table("brand_profiles")
                 .select("tone::text, tone_proposto_origem, tone_proposto_em")
                 .eq("company_id", args.company).limit(1).execute()).data or [{}]
    p("")
    p("GRAVADO. VERIFY: tone_proposto_origem=%s · tone (ATIVO, inalterado)=%s"
      % (conferido[0].get("tone_proposto_origem"), conferido[0].get("tone")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
