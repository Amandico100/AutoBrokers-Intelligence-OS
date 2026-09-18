# -*- coding: utf-8 -*-
"""Conserta, nas linhas `proposto` da onda 1, o que a auditoria mediu (18/09/2026).

SPEC-EXTRA-001.5 · conserto único. Quatro correções, todas pelo **módulo da
base** (`assistance_plans_base`) e todas **só em `proposto`**:

```
① vigência        date.today() -> effective_from da versão do documento   (38/38)
② produto         nome de arquivo e caixas divergentes -> forma canônica
③ plano-lixo      nome que é lista de coberturas -> `rascunho` com motivo   (4)
④ alagamento=nao  vindo de cláusula de EXCLUSÃO de outra cobertura -> `rascunho`
```

⛔ **Nada é publicado e nada é apagado.** Linha em `publicado` não é tocada: em
`publicado` uma correção mudaria, sem aviso, uma resposta que uma pessoa já
revisou — o caminho para isso é `derrubar_para_proposto` e nova revisão.

🔴 **Por que ④ vira `rascunho` e não é reextraído agora:** rerodar o extrator
nesses documentos custaria uma nova rodada de modelo e produziria linhas novas ao
lado das erradas (a unicidade é por `plano_id + servico`). Derrubar para
`rascunho` com o motivo tira a afirmação errada do caminho do segurado **hoje**,
preserva o trecho e a página que a originaram, e deixa a linha à vista de quem
for revisar. A reextração entra na próxima rodada normal da onda 1.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(RAIZ, ".env"))
except Exception:  # noqa: BLE001
    pass

from app.services.knowledge import assistance_plans_base as BASE  # noqa: E402
from app.services.knowledge import assistance_plans_extractor as X  # noqa: E402


def main(aplicar: bool = False) -> int:
    from app.core.database import get_supabase_client

    db = get_supabase_client().client
    planos = (db.table(BASE.TABELA_PLANOS).select("*").eq("curadoria", "proposto")
              .execute()).data or []
    servicos = (db.table(BASE.TABELA_SERVICOS).select("*").eq("curadoria", "proposto")
                .execute()).data or []
    docs = (db.table("normative_documents")
            .select("id, effective_from, created_at, product_line, title")
            .execute()).data or []
    por_doc = {str(d["id"]): d for d in docs}

    print("📊 linhas `proposto`: %s plano(s) · %s serviço(s)" % (len(planos), len(servicos)))
    print("modo: %s" % ("APLICAR" if aplicar else "ensaio (nada é escrito)"))

    contas = {"vigencia": 0, "produto": 0, "plano_lixo": 0, "alagamento": 0, "erros": 0}
    for p in planos:
        doc = por_doc.get(str(p.get("documento_id"))) or {}
        nova = X.vigencia_do_documento(str(p.get("documento_id")), doc, db)
        if nova and str(p.get("vigencia_inicio"))[:10] != str(nova)[:10]:
            contas["vigencia"] += 1
            if aplicar:
                try:
                    BASE.corrigir_vigencia_do_plano(
                        str(p["id"]), nova, motivo="onda 1 gravou date.today()", db=db)
                except Exception as exc:  # noqa: BLE001
                    contas["erros"] += 1
                    print("   ⛔ vigência %s: %s" % (p["id"], type(exc).__name__))

        canonico = X.produto_canonico(p.get("produto"), doc.get("product_line"))
        nome = X.nome_de_plano_valido(p.get("plano"))
        if nome is None:
            contas["plano_lixo"] += 1
            if aplicar:
                try:
                    BASE.plano_para_rascunho(
                        str(p["id"]),
                        "o nome do plano era uma lista de coberturas, não um pacote", db=db)
                except Exception as exc:  # noqa: BLE001
                    contas["erros"] += 1
                    print("   ⛔ plano-lixo %s: %s" % (p["id"], type(exc).__name__))
            continue
        if canonico != str(p.get("produto")):
            contas["produto"] += 1
            if aplicar:
                try:
                    BASE.renomear_plano_proposto(str(p["id"]), produto=canonico, db=db)
                except Exception as exc:  # noqa: BLE001
                    # 📊 a unicidade `(insurer_key, ramo, produto, plano, vigencia)`
                    # recusa a fusão quando a outra caixa já ocupa o lugar: a
                    # duplicata perde a razão de existir e vai para `rascunho`.
                    try:
                        BASE.plano_para_rascunho(
                            str(p["id"]),
                            "duplicata por caixa do produto %r" % canonico, db=db)
                    except Exception:  # noqa: BLE001
                        contas["erros"] += 1
                        print("   ⛔ produto %s: %s" % (p["id"], type(exc).__name__))

    for s in servicos:
        if str(s.get("servico")) != "alagamento" or str(s.get("coberto")) != "nao":
            continue
        contas["alagamento"] += 1
        if aplicar:
            try:
                BASE.para_rascunho(
                    str(s["id"]),
                    "'nao' de alagamento veio de cláusula de exclusão de risco de "
                    "outra cobertura — precisa ser reextraído como condicionado",
                    db=db)
            except Exception as exc:  # noqa: BLE001
                contas["erros"] += 1
                print("   ⛔ alagamento %s: %s" % (s["id"], type(exc).__name__))

    print("📊 vigência a corrigir: %(vigencia)s · produto a normalizar: %(produto)s · "
          "plano-lixo -> rascunho: %(plano_lixo)s · alagamento=nao -> rascunho: "
          "%(alagamento)s · erros: %(erros)s" % contas)
    print("🔴 linhas publicadas por este script: 0")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(aplicar="--aplicar" in sys.argv))
