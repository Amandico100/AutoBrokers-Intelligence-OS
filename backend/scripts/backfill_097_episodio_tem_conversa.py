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

🔴 A normalização do telefone é `app/telefone_br.py::variantes_br` — a MESMA
regra do nono dígito que o Atlas usa para correlacionar telefone
(`observer_intake:866,1007`) e que o intake usa para gravar o elo novo. ⚠️ Ela
NÃO é "só os dígitos": 📊 medido em 05/09/2026, o casador estrito tratava
`5548988887777` e `554888887777` como duas pessoas, e um par gravado com o 9 de
um lado e sem ele do outro virava órfão. Um segundo jeito de normalizar produz
um segundo conjunto de elos, divergente do primeiro (CLAUDE.md §9.4: padrão
medido com um motor e aplicado com outro é um padrão sobre outra coisa).
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# ⚠️ DEPOIS do `sys.path`, e é o ÚNICO import de `app.` no corpo do módulo: o
#    guarda carrega este arquivo solto, por caminho. `app/telefone_br.py` não
#    importa nada — nem `app.core`, nem `app.services` — justamente para poder
#    ser importado aqui sem subir o mundo (SPEC-097 P3-4).
from app.telefone_br import variantes_br

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


def casar_1_para_1(sessoes, conversas) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Quais episódios têm UMA conversa — **FUNÇÃO PURA**, e é ela que o guarda
    executa.

    Devolve `(elos, ambiguos, orfaos)`:

        elos      {attendance_session_id: conversation_id}   só o 1:1
        ambiguos  [attendance_session_id]                    2+ conversas
        orfaos    [attendance_session_id]                    nenhuma conversa

    🔴 A chave é `(company_id, telefone)` — a corretora entra na chave, não num
    filtro depois (§7). Sem ela, dois segurados de corretoras diferentes com o
    mesmo número seriam a mesma pessoa.

    ⚠️ **E o telefone entra pelas suas VARIANTES** (`variantes_br`): a conversa
    é indexada sob as duas formas do nono dígito, e o episódio procura pelas
    duas. 📊 P3-4: o casador estrito transformava em órfão todo par gravado com
    9 de um lado e sem 9 do outro.

    ⛔ **Ampliar o casador não afrouxa o 1:1.** As candidatas são
    DESDUPLICADAS: se as duas formas acham a MESMA conversa, é uma; se acham
    duas conversas diferentes, é ambíguo — e ambíguo não é gravado.
    """
    por_telefone: Dict[Tuple[str, str], List[str]] = {}
    for c in conversas or []:
        empresa = str((c or {}).get("company_id") or "")
        for forma in variantes_br((c or {}).get("user_phone")):
            por_telefone.setdefault((empresa, forma), []).append(str((c or {}).get("id")))

    elos: Dict[str, str] = {}
    ambiguos: List[str] = []
    orfaos: List[str] = []
    for s in sessoes or []:
        sid = str((s or {}).get("id"))
        empresa = str((s or {}).get("company_id") or "")
        candidatas: List[str] = []
        vistas = set()
        for forma in sorted(variantes_br((s or {}).get("counterparty"))):
            for cid in por_telefone.get((empresa, forma), []):
                if cid not in vistas:
                    vistas.add(cid)
                    candidatas.append(cid)
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
