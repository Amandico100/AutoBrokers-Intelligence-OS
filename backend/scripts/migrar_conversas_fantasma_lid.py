# -*- coding: utf-8 -*-
"""As conversas-FANTASMA que o `@lid` criou — plano, VERIFY e ROLLBACK.

```
(padrão)    PLANO. NÃO escreve nada. Conta por corretora e diz o que faria.
--vivo      aplica, roda o VERIFY e imprime o ROLLBACK (ids).
--company   restringe a UMA corretora (padrão: todas)
```

🔴 **O QUE É UMA CONVERSA-FANTASMA** (medido no banco de produção, 09/09/2026)

O WhatsApp Web endereça o chat por `@lid` — um identificador **opaco** de ~15
dígitos. `normalize_evolution_inbound` fazia `remoteJid.split("@")[0]` e gravava
aquilo em `conversations.user_phone`. Resultado:

    📊 as 5 pausas por intervenção humana de toda a história do produto estão
       em conversas com `user_phone` de 15 dígitos — e a conversa REAL do mesmo
       segurado seguia `open`, com o robô respondendo por cima da atendente.
    📊 11 mensagens de 09/09 espelhadas em DUAS conversas (a real e a fantasma).

O código já não cria mais nenhuma (`identidade_do_evento.telefone_do_evento`).
Este script cuida do que ficou para trás.

📊 **O PLANO RODADO EM 09/09/2026** (só leitura, `python scripts/migrar_conversas_fantasma_lid.py`):

    774 conversas · 174 FANTASMAS · 174 delas ABERTAS
      corretora 04b5cdbc… ....  68 fantasmas · 68 abertas · 5 com pausa humana
      corretora 6c9c55e2… ... 106 fantasmas · 106 abertas · 5 com pausa humana
      pausa a copiar para a conversa real ....   7
      sem par real encontrado (só fecham) .... 165

⚠️ São **174**, não as "~30" estimadas antes de medir — e 10 delas guardam
trabalho humano que hoje está preso numa conversa que ninguém abre.

⛔ **DUAS COISAS, E A ORDEM IMPORTA.** Fechar a fantasma sem antes levar a pausa
para a conversa real **desfaria** o trabalho da atendente: a conversa dela
voltaria a ser do robô no instante do fechamento. Por isso a cópia vem primeiro,
e só depois o fechamento.

🔴 **O QUE LIGA A FANTASMA À REAL É O `wa_message_id`**, e não o telefone —
telefone é justamente o que a fantasma não tem. A mesma mensagem do WhatsApp foi
espelhada nas duas linhas (`messages.payload->>wa_message_id`), e esse id é
único no mundo. ⚠️ Casar por outra coisa aqui seria adivinhar de quem é a
conversa, e o preço de errar é mostrar a uma pessoa o atendimento de outra.

⚠️ **NENHUM TELEFONE, NENHUM LID É IMPRESSO.** As contagens são por corretora;
os ids que o ROLLBACK precisa são `uuid` de conversa, não PII.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

LOTE = 1000

#: O motivo que esta migração escreve.
MOTIVO = "fantasma_lid"

#: 🔴 A LISTA FECHADA DO BANCO — `ck_conversations_resolucao_motivo`, migration
#: `20260826_04_spec086_blocoA_a_conversa_tem_fim.sql:97`.
#:
#: ⛔ `fantasma_lid` **não está nela**, e é por isso que este script recusa o
#: `--vivo` até a migration do valor novo ser aplicada. Descobrir isso por um
#: `23514` no meio de trinta UPDATEs seria descobrir tarde: os primeiros já
#: teriam gravado, e o rollback nasceria pela metade.
MOTIVOS_ACEITOS_PELO_BANCO = (
    "acionamento_concluido", "encaminhado", "resolvido_pelo_segurado",
    "fechado_por_humano", "expirou",
)

#: Um celular BR completo tem 13 dígitos (`55` + DDD + 9). Um LID observado em
#: produção tem 15 e não começa com `55`.
#:
#: ⚠️ **O critério do plano dizia "≥ 13 dígitos", e ele condenaria TODO celular
#: brasileiro** — 📊 `5548988887777` tem exatamente 13. O que separa fantasma de
#: telefone é `> 13` **ou** a ausência do DDI. Está escrito aqui, e não num
#: comentário longe, porque é a linha que decide o que é fechado.
DIGITOS_DE_TELEFONE_BR = 13


def p(texto: Any = "") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


# ---------------------------------------------------------------------------
# AS FUNÇÕES PURAS — é o que o guarda executa
# ---------------------------------------------------------------------------

def e_fantasma(user_phone: Any) -> bool:
    """Este `user_phone` é um LID disfarçado de telefone?"""
    d = "".join(ch for ch in str(user_phone or "") if ch.isdigit())
    if not d:
        return False
    return (not d.startswith("55")) or len(d) > DIGITOS_DE_TELEFONE_BR


def parear_pelo_wa_id(fantasmas: List[dict], mensagens: List[dict]) -> Dict[str, str]:
    """`{id_da_fantasma: id_da_conversa_real}` — só os pares SEM ambiguidade.

    `mensagens` traz `conversation_id` e `payload` de todas as linhas cujo
    `wa_message_id` aparece em alguma fantasma. Uma fantasma casa com a real
    quando as duas espelharam **a mesma** mensagem do WhatsApp.

    ⛔ Duas candidatas = não grava. É a mesma disciplina do backfill do elo
    episódio↔conversa: um par errado mostra a uma pessoa o atendimento de outra.
    """
    ids_fantasma = {str(f.get("id")) for f in fantasmas or []}
    por_wa: Dict[str, set] = {}
    for m in mensagens or []:
        wa = str(((m or {}).get("payload") or {}).get("wa_message_id") or "")
        if not wa:
            continue
        por_wa.setdefault(wa, set()).add(str((m or {}).get("conversation_id") or ""))

    candidatas: Dict[str, set] = {}
    for wa, conversas in por_wa.items():
        fant = {c for c in conversas if c in ids_fantasma}
        reais = {c for c in conversas if c and c not in ids_fantasma}
        for f in fant:
            candidatas.setdefault(f, set()).update(reais)
    return {f: next(iter(reais)) for f, reais in candidatas.items() if len(reais) == 1}


def tem_pausa(conversa: dict) -> bool:
    """A fantasma guarda trabalho humano que precisa ser levado para a real?"""
    c = conversa or {}
    return bool(c.get("claimed_by") or c.get("claimed_by_name")
                or str(c.get("status") or "") == "HUMAN_REQUESTED")


# ---------------------------------------------------------------------------
# A leitura
# ---------------------------------------------------------------------------

def _ler_tudo(db, tabela: str, campos: str, company_id: str = "",
              coluna_in: str = "", valores_in: Optional[List[str]] = None) -> List[dict]:
    linhas: List[dict] = []
    inicio = 0
    while True:
        consulta = db.table(tabela).select(campos).order("id")
        if company_id:
            consulta = consulta.eq("company_id", company_id)     # 🔴 CLAUDE.md §7
        if coluna_in and valores_in:
            consulta = consulta.in_(coluna_in, valores_in)
        pagina = consulta.range(inicio, inicio + LOTE - 1).execute().data or []
        linhas.extend(pagina)
        if len(pagina) < LOTE:
            return linhas
        inicio += LOTE


def _mensagens_das_fantasmas(db, ids: List[str]) -> List[dict]:
    """As linhas de `messages` das fantasmas e as das conversas que compartilham
    o mesmo `wa_message_id`. Duas passadas: a primeira colhe os ids do WhatsApp,
    a segunda procura quem mais os tem."""
    das_fantasmas: List[dict] = []
    for i in range(0, len(ids), 50):
        das_fantasmas.extend(_ler_tudo(db, "messages", "id, conversation_id, payload",
                                       coluna_in="conversation_id",
                                       valores_in=ids[i:i + 50]))
    was = sorted({str(((m or {}).get("payload") or {}).get("wa_message_id") or "")
                  for m in das_fantasmas} - {""})
    gemeas: List[dict] = []
    for i in range(0, len(was), 50):
        inicio = 0
        while True:
            pagina = (db.table("messages").select("id, conversation_id, payload")
                      .in_("payload->>wa_message_id", was[i:i + 50])
                      .order("id").range(inicio, inicio + LOTE - 1).execute().data or [])
            gemeas.extend(pagina)
            if len(pagina) < LOTE:
                break
            inicio += LOTE
    return das_fantasmas + gemeas


# ---------------------------------------------------------------------------

def _sql(valor: Any) -> str:
    return "NULL" if valor in (None, "") else "'%s'" % str(valor).replace("'", "''")


def rodar(company_id: str = "", escrever: bool = False) -> int:
    from app.core.database import get_supabase_client

    db = get_supabase_client().client

    conversas = _ler_tudo(
        db, "conversations",
        "id, company_id, user_phone, channel, status, claimed_by, claimed_by_name, "
        "claimed_at, resolvido_em, resolucao_motivo, created_at", company_id)
    fantasmas = [c for c in conversas if e_fantasma(c.get("user_phone"))]
    abertas = [c for c in fantasmas if str(c.get("status") or "") != "closed"]

    p("lidas: %d conversas · %d FANTASMAS · %d delas abertas"
      % (len(conversas), len(fantasmas), len(abertas)))
    p("")
    p("POR CORRETORA (contagem — nenhum telefone, nenhum LID):")
    por_empresa: Dict[str, List[dict]] = {}
    for c in fantasmas:
        por_empresa.setdefault(str(c.get("company_id") or "?"), []).append(c)
    for empresa, linhas in sorted(por_empresa.items()):
        p("  %s ... %3d fantasmas · %3d abertas · %3d com pausa humana"
          % (empresa, len(linhas),
             sum(1 for c in linhas if str(c.get("status") or "") != "closed"),
             sum(1 for c in linhas if tem_pausa(c))))
    if not fantasmas:
        p("  (nenhuma)")
        p("")
        p("NADA A FAZER.")
        return 0

    ids = [str(c.get("id")) for c in fantasmas]
    mensagens = _mensagens_das_fantasmas(db, ids)
    pares = parear_pelo_wa_id(fantasmas, mensagens)
    por_id = {str(c.get("id")): c for c in conversas}

    # A cópia só acontece quando há o que copiar E a real ainda está `open`:
    # uma real já assumida por outra pessoa não é sobrescrita.
    a_copiar: List[Tuple[str, str]] = []
    for fid, real in pares.items():
        fantasma = por_id.get(fid) or {}
        alvo = por_id.get(real) or {}
        if tem_pausa(fantasma) and str(alvo.get("status") or "") == "open":
            a_copiar.append((fid, real))

    p("")
    p("O QUE ESTE SCRIPT FARIA:")
    p("  (1) copiar a pausa da fantasma para a conversa REAL ... %3d" % len(a_copiar))
    p("      (status, claimed_by, claimed_by_name, claimed_at)")
    p("  (2) fechar a fantasma (status=closed, resolvido_em=agora,")
    p("      resolucao_motivo='%s') ......................... %3d" % (MOTIVO, len(abertas)))
    p("  sem par real encontrado (só fecham) .................. %3d"
      % sum(1 for c in abertas if str(c.get("id")) not in pares))

    if MOTIVO not in MOTIVOS_ACEITOS_PELO_BANCO:
        p("")
        p("BLOQUEIO: `%s` NAO esta na lista fechada do CHECK" % MOTIVO)
        p("   `ck_conversations_resolucao_motivo` (migration 20260826_04).")
        p("   O `--vivo` fica recusado ate esta migration ser aplicada:")
        p("")
        p("   APPLY:")
        p("     ALTER TABLE public.conversations")
        p("       DROP CONSTRAINT IF EXISTS ck_conversations_resolucao_motivo;")
        p("     ALTER TABLE public.conversations")
        p("       ADD CONSTRAINT ck_conversations_resolucao_motivo")
        p("       CHECK (resolucao_motivo IS NULL OR resolucao_motivo IN (")
        p("         %s, '%s'));"
          % (", ".join("'%s'" % m for m in MOTIVOS_ACEITOS_PELO_BANCO), MOTIVO))
        p("   VERIFY:")
        p("     select pg_get_constraintdef(oid) from pg_constraint")
        p("      where conname = 'ck_conversations_resolucao_motivo';")
        p("     -- tem de conter '%s'" % MOTIVO)
        p("   ROLLBACK: o mesmo ALTER sem o valor novo (e nenhuma linha o usa")
        p("     enquanto este script nao rodar com --vivo).")

    if not escrever:
        p("")
        p("PLANO: NADA foi gravado. Rode com `--vivo` para aplicar.")
        p("VERIFY depois do --vivo (esperado ZERO):")
        p("  select count(*) from conversations")
        p("   where status <> 'closed'")
        p("     and (user_phone !~ '^55'")
        p("          or length(regexp_replace(user_phone, '[^0-9]', '', 'g')) > 13);")
        return 0

    if MOTIVO not in MOTIVOS_ACEITOS_PELO_BANCO:
        p("")
        p("RECUSADO: ver o BLOQUEIO acima. Nada foi gravado.")
        return 2

    # ---------------------------- APPLY ----------------------------
    p("")
    p("ROLLBACK (guarde ANTES de continuar — estado anterior, linha a linha):")
    for fid, real in a_copiar:
        alvo = por_id.get(real) or {}
        p("  update conversations set status='%s', claimed_by=%s, claimed_by_name=%s, "
          "claimed_at=%s where id='%s';"
          % (alvo.get("status") or "open",
             _sql(alvo.get("claimed_by")), _sql(alvo.get("claimed_by_name")),
             _sql(alvo.get("claimed_at")), real))
    for c in abertas:
        p("  update conversations set status='%s', resolvido_em=NULL, "
          "resolucao_motivo=NULL where id='%s';"
          % (c.get("status") or "open", c.get("id")))

    agora = datetime.now(timezone.utc).isoformat()
    copiadas = fechadas = falhas = 0
    for fid, real in a_copiar:
        fantasma = por_id.get(fid) or {}
        try:
            (db.table("conversations").update({
                "status": fantasma.get("status") or "HUMAN_REQUESTED",
                "claimed_by": fantasma.get("claimed_by"),
                "claimed_by_name": fantasma.get("claimed_by_name"),
                "claimed_at": fantasma.get("claimed_at") or agora,
            }).eq("id", real)
             .eq("company_id", str(fantasma.get("company_id") or ""))   # §7
             .execute())
            copiadas += 1
        except Exception as erro:  # noqa: BLE001
            falhas += 1
            p("  falhou a copia em %s (%s)" % (real, type(erro).__name__))

    for c in abertas:
        try:
            (db.table("conversations").update({
                "status": "closed",
                "resolvido_em": agora,
                "resolucao_motivo": MOTIVO,
            }).eq("id", str(c.get("id")))
             .eq("company_id", str(c.get("company_id") or ""))          # §7
             .execute())
            fechadas += 1
        except Exception as erro:  # noqa: BLE001
            falhas += 1
            p("  falhou o fechamento em %s (%s)" % (c.get("id"), type(erro).__name__))

    # ---------------------------- VERIFY ---------------------------
    p("")
    p("APLICADO: %d pausas copiadas · %d fantasmas fechadas · %d falhas"
      % (copiadas, fechadas, falhas))
    depois = _ler_tudo(db, "conversations", "id, company_id, user_phone, status", company_id)
    restantes = [c for c in depois
                 if e_fantasma(c.get("user_phone")) and str(c.get("status") or "") != "closed"]
    p("VERIFY: fantasmas ainda ABERTAS = %d  (esperado 0)" % len(restantes))
    return 0 if (not restantes and not falhas) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Migra as conversas-fantasma do @lid")
    ap.add_argument("--vivo", action="store_true",
                    help="APLICA (o padrão é só planejar)")
    ap.add_argument("--company", default="", help="restringe a uma corretora")
    args = ap.parse_args()
    p("=" * 70)
    p("CONVERSAS-FANTASMA DO @lid — %s" % ("APLICANDO" if args.vivo else "PLANO"))
    p("=" * 70)
    return rodar(company_id=args.company, escrever=bool(args.vivo))


if __name__ == "__main__":
    sys.exit(main())
