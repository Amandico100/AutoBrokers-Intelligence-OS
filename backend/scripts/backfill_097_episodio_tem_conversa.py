# -*- coding: utf-8 -*-
"""O backfill do elo episódio ↔ conversa — SPEC-097 U3.2.

```
--dry-run   (padrão) NÃO escreve. Lê tudo, casa, e imprime as contagens.
--vivo      grava `attendance_sessions.conversation_id` SÓ nos elos 1:1.
--company   restringe a UMA corretora (padrão: todas)
```

📊 **A razão, medida em 05/09/2026:** `attendance_sessions` tem 12.755 linhas e
nenhuma sabe de qual conversa é. Casando por `(company_id, telefone)`, **57,8%**
casam com exatamente UMA conversa; o resto se divide entre telefones com várias
conversas (ambíguos) e telefones sem conversa nenhuma (órfãos — 42,2% no total,
E7).

🔴 **O 1:1 não é preciosismo: é a diferença entre um elo e uma mentira.** Um
episódio ligado à conversa errada mostra ao segurado o atendimento de outra
pessoa. ⛔ Por isso o ambíguo **não é gravado** — nunca "a primeira candidata".

⚠️ A normalização do telefone é a MESMA do produto (`webhook.py::
_conversa_do_telefone` e `dispatch_router::_digits`): só os dígitos. Um segundo
jeito de normalizar produziria um segundo conjunto de elos, divergente do
primeiro (CLAUDE.md §9.4: padrão medido com um motor e aplicado com outro é um
padrão sobre outra coisa).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

#: Quantas linhas por página de leitura. O PostgREST tem teto de 1.000.
LOTE = 1000


def p(texto: Any = "") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def so_digitos(telefone: Any) -> str:
    """A MESMA normalização que o produto já usa para achar conversa por
    telefone. ⛔ Não invente outra."""
    return "".join(c for c in str(telefone or "") if c.isdigit())


def casar_1_para_1(sessoes, conversas) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Quais episódios têm UMA conversa — **FUNÇÃO PURA**, e é ela que o guarda
    executa.

    Devolve `(elos, ambiguos, orfaos)`:

        elos      {attendance_session_id: conversation_id}   só o 1:1
        ambiguos  [attendance_session_id]                    2+ conversas
        orfaos    [attendance_session_id]                    nenhuma conversa

    🔴 A chave é `(company_id, dígitos do telefone)` — a corretora entra na
    chave, não num filtro depois (§7). Sem ela, dois segurados de corretoras
    diferentes com o mesmo número seriam a mesma pessoa.
    """
    por_telefone: Dict[Tuple[str, str], List[str]] = {}
    for c in conversas or []:
        telefone = so_digitos((c or {}).get("user_phone"))
        if not telefone:
            continue
        chave = (str((c or {}).get("company_id") or ""), telefone)
        por_telefone.setdefault(chave, []).append(str((c or {}).get("id")))

    elos: Dict[str, str] = {}
    ambiguos: List[str] = []
    orfaos: List[str] = []
    for s in sessoes or []:
        sid = str((s or {}).get("id"))
        chave = (str((s or {}).get("company_id") or ""),
                 so_digitos((s or {}).get("counterparty")))
        candidatas = por_telefone.get(chave, [])
        # 🔴 A ÂNCORA DESTE BACKFILL, e ela mora numa LINHA SÓ de propósito:
        #    a mutação U10 do guarda troca `== 1` por `>= 1` aqui, e assim ela
        #    muda o COMPORTAMENTO (grava o ambíguo) em vez de quebrar a sintaxe.
        #    ⚠️ Mutação que só estoura o parser prova que o arquivo existe, não
        #    que esta regra é o que decide (CLAUDE.md §9.3).
        casa_unica = len(candidatas) == 1
        if casa_unica:
            elos[sid] = candidatas[0]
        elif candidatas:
            ambiguos.append(sid)
        else:
            orfaos.append(sid)
    return elos, ambiguos, orfaos


# ---------------------------------------------------------------------------
# A leitura — em lotes, e sempre com a corretora na linha
# ---------------------------------------------------------------------------

def _ler_tudo(db, tabela: str, campos: str, company_id: str = "") -> List[dict]:
    linhas: List[dict] = []
    inicio = 0
    while True:
        consulta = db.table(tabela).select(campos).order("id")
        if company_id:
            consulta = consulta.eq("company_id", company_id)     # 🔴 §7
        pagina = consulta.range(inicio, inicio + LOTE - 1).execute().data or []
        linhas.extend(pagina)
        if len(pagina) < LOTE:
            return linhas
        inicio += LOTE


def rodar(company_id: str = "", escrever: bool = False) -> int:
    from app.core.database import get_supabase_client

    db = get_supabase_client().client

    # ⚠️ A coluna nasce na migration U3.1 desta SPEC. Antes dela, o ENSAIO
    #    ainda vale (e é justamente quando ele é útil: dá o tamanho do que vai
    #    ser gravado) — mas o `--vivo` não pode rodar, e dizer isso em uma linha
    #    é melhor que um traceback de PostgREST.
    migrada = True
    try:
        sessoes = _ler_tudo(db, "attendance_sessions",
                            "id, company_id, counterparty, conversation_id", company_id)
    except Exception as erro:  # noqa: BLE001
        if "conversation_id" not in str(erro):
            raise
        migrada = False
        p("⚠️  `attendance_sessions.conversation_id` ainda NÃO EXISTE — a migration")
        p("    `20260905_01_spec097_episodio_tem_conversa.sql` não foi aplicada.")
        p("    O ensaio continua (e conta o que ela vai destravar); `--vivo`, não.")
        p("")
        sessoes = _ler_tudo(db, "attendance_sessions",
                            "id, company_id, counterparty", company_id)
    conversas = _ler_tudo(db, "conversations", "id, company_id, user_phone", company_id)
    p("lidos: %d episódios · %d conversas" % (len(sessoes), len(conversas)))

    ja_ligados = [s for s in sessoes if (s or {}).get("conversation_id")]
    pendentes = [s for s in sessoes if not (s or {}).get("conversation_id")]
    elos, ambiguos, orfaos = casar_1_para_1(pendentes, conversas)

    total = len(sessoes) or 1
    p("")
    p("CONTAGENS (o VERIFY deste backfill é contagem):")
    p("  já ligados antes ....... %6d" % len(ja_ligados))
    p("  elos 1:1 a gravar ...... %6d   (%.1f%% dos pendentes)"
      % (len(elos), 100.0 * len(elos) / (len(pendentes) or 1)))
    p("  ambíguos (NÃO gravados)  %6d" % len(ambiguos))
    p("  órfãos (sem conversa) .. %6d" % len(orfaos))
    p("  total de episódios ..... %6d" % total)

    if escrever and not migrada:
        p("")
        p("⛔ RECUSADO: `--vivo` sem a migration U3.1 aplicada não tem onde gravar.")
        return 2

    if not escrever:
        p("")
        p("--dry-run: NADA foi gravado. Rode com `--vivo` para aplicar.")
        p("Depois do `--vivo`, o VERIFY é este SQL:")
        p("  select count(*) filter (where conversation_id is not null) as com_elo,")
        p("         count(*) as total from attendance_sessions;")
        p("  -- esperado com_elo = %d + %d" % (len(ja_ligados), len(elos)))
        return 0

    gravados = 0
    falhas = 0
    por_id = {str(s["id"]): s for s in pendentes}
    for sid, conversa in elos.items():
        empresa = str((por_id.get(sid) or {}).get("company_id") or "")
        if not empresa:
            falhas += 1
            continue
        try:
            (db.table("attendance_sessions")
               .update({"conversation_id": conversa})
               .eq("company_id", empresa)                       # 🔴 §7
               .eq("id", sid)
               .is_("conversation_id", "null")                  # ⛔ idempotente
               .execute())
            gravados += 1
        except Exception as erro:  # noqa: BLE001
            falhas += 1
            if falhas <= 3:
                p("  ⚠️  falha ao gravar um elo (%s)" % type(erro).__name__)

    p("")
    p("GRAVADOS: %d · falhas: %d" % (gravados, falhas))
    confere = _ler_tudo(db, "attendance_sessions",
                        "id, company_id, conversation_id", company_id)
    com_elo = len([s for s in confere if (s or {}).get("conversation_id")])
    p("VERIFY (recontagem no banco): com_elo=%d de %d episódios" % (com_elo, len(confere)))
    return 0 if not falhas else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill do elo episódio ↔ conversa (SPEC-097 U3.2)")
    ap.add_argument("--vivo", action="store_true", help="grava de verdade")
    ap.add_argument("--dry-run", action="store_true",
                    help="(padrão) só lê e conta; nada é gravado")
    ap.add_argument("--company", default="", help="restringe a uma corretora")
    args = ap.parse_args()
    return rodar(company_id=str(args.company or ""), escrever=bool(args.vivo))


if __name__ == "__main__":
    sys.exit(main())
