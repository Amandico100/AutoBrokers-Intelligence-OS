"""SPEC-071 · BLOCO 4.4 — marca no acervo quem NÃO era cliente.

📊 `attendance_transcripts` tem 150.734 linhas e `insurer_key` estava nulo em
100% delas. Isso não era só um campo vazio: `deve_espelhar` pergunta
`bool(insurer_key)` para decidir se a conversa vai para a mesa da atendente, e
`bool(None)` é False sempre. O portão nunca disparou.

O código novo (`canais_observados`) impede as PRÓXIMAS. Este script trata as que
já estão gravadas.

POR QUE UM SCRIPT, E NÃO UM `UPDATE` NA MIGRATION
==================================================
Porque a lista de quem é seguradora tem de ter **um** dono. Cravar os telefones
em SQL criaria uma segunda fonte de verdade, e daqui a dois meses ninguém saberia
qual das duas manda quando divergissem (CLAUDE.md §5). Aqui a lista vem do
catálogo, sempre — o mesmo que a allowlist e o espelho leem.

`--sql` imprime o comando em vez de executar, para quem só tem acesso ao banco.
O SQL sai GERADO do catálogo: continua sem ninguém digitar telefone.

MODO DE USAR
============
    python scripts/marcar_canais_no_acervo.py --sql        # só mostra
    python scripts/marcar_canais_no_acervo.py --executar   # aplica (precisa env)

⚠️ Idempotente: marcar de novo escreve o mesmo valor. Rodar duas vezes não faz
diferença nenhuma.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.atlas.canais_observados import (  # noqa: E402
    CANAIS_OBSERVADOS, PRESTADORA, SEGURADORA,
)

# 🔴 A CHAVE QUE UMA PRESTADORA RECEBE, e por que não é `insurer_key`.
#
# A Localiza atende HDI e Tokio com o mesmo roteiro. Gravar `hdi` na linha dela
# faria "15 diárias" — que é regra da LOCALIZA — virar regra da HDI, e o erro só
# apareceria quando um segurado recebesse a informação errada. `curadoria_cartas`
# já registrava isso antes de mim.
#
# Mas ela também não é cliente e não pode ficar na mesa da atendente. Por isso
# recebe um prefixo que o produto reconhece como "não é companhia".
PREFIXO_PRESTADORA = "prestadora:"
PREFIXO_FORA = "fora_do_dominio"


def valor_para_a_coluna(canal: dict) -> str:
    """O que vai em `insurer_key` para este canal."""
    if canal["natureza"] == SEGURADORA:
        return canal["insurer_key"]
    if canal["natureza"] == PRESTADORA:
        return f"{PREFIXO_PRESTADORA}{canal['prestadora_key']}"
    return PREFIXO_FORA


def gerar_sql() -> str:
    """Um UPDATE por canal, gerado do catálogo. Sem telefone digitado."""
    linhas = [
        "-- GERADO por scripts/marcar_canais_no_acervo.py a partir de",
        "-- app/services/atlas/canais_observados.py — não editar à mão.",
        "--",
        "-- VERIFY depois de rodar:",
        "--   SELECT insurer_key, count(*) FROM public.attendance_transcripts",
        "--    WHERE insurer_key IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;",
        "-- ROLLBACK:",
        "--   UPDATE public.attendance_transcripts SET insurer_key = NULL",
        "--    WHERE insurer_key IS NOT NULL;   -- devolve ao estado de 15/08",
        "",
    ]
    for canal in CANAIS_OBSERVADOS:
        valor = valor_para_a_coluna(canal)
        if not valor or valor.endswith(":"):
            continue
        escopo = (f"\n   AND company_id = '{canal['company_id']}'"
                  if canal["company_id"] else "")
        linhas.append(
            f"-- {canal['natureza']:15s} {canal['valor']:16s} "
            f"{canal['evidencia'][:70]}\n"
            f"UPDATE public.attendance_transcripts\n"
            f"   SET insurer_key = '{valor}'\n"
            f" WHERE counterparty = '{canal['valor']}'{escopo}\n"
            f"   AND insurer_key IS DISTINCT FROM '{valor}';\n")
    return "\n".join(linhas)


def executar() -> int:
    from app.core.database import get_supabase_client

    cliente = get_supabase_client().client
    total = 0
    for canal in CANAIS_OBSERVADOS:
        valor = valor_para_a_coluna(canal)
        if not valor or valor.endswith(":"):
            continue
        q = (cliente.table("attendance_transcripts")
             .update({"insurer_key": valor})
             .eq("counterparty", canal["valor"]))
        # ⚠️ O escopo do `@lid` é filtro OBRIGATÓRIO, não otimização: um `@lid`
        # que a Resulta viu não diz nada sobre a AutoFleet, e marcar linhas da
        # outra corretora seria dado de um tenant decidindo o da outra (§7).
        if canal["company_id"]:
            q = q.eq("company_id", canal["company_id"])
        marcadas = len(q.execute().data or [])
        total += marcadas
        print(f"  {canal['valor']:16s} -> {valor:24s} {marcadas:6d} linha(s)")
    return total


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sql", action="store_true", help="imprime o SQL, não aplica")
    p.add_argument("--executar", action="store_true", help="aplica no banco")
    a = p.parse_args()

    if a.sql:
        print(gerar_sql())
        return 0
    if a.executar:
        print(f"Marcando {len(CANAIS_OBSERVADOS)} canais no acervo...")
        print(f"\nTotal: {executar()} linha(s) marcadas.")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
