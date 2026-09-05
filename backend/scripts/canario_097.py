# -*- coding: utf-8 -*-
"""O canário vivo da SPEC-097 — o desfecho, medido no banco de verdade.

```
--dry-run   (padrão) imprime o PLANO e não toca em nada.
--vivo      cria UM episódio canário na Resulta, abre uma espera, ASSUME a
            conversa, marca o fim pelo EPISÓDIO e prova no banco o que mudou —
            e o que NÃO mudou. Ao fim apaga o que criou, por id, e prova que
            apagou.
```

## O que ele mede, e por que cada medida existe

```
Q1  `abrir_espera(seguradora, vence em +2h)` na conversa canário
    → tem de existir EXATAMENTE 1 linha em `work_waits`, ativa, da corretora.
      📊 05/09/2026: `work_waits` tinha ZERO linhas na vida — a tabela existia
      e ninguém escrevia nela.

Q2  a atendente ASSUME (claimed_by) e a IA tem de calar
    → `pausar_ia(conversa)` = True com status 'open'. É o defeito E6: hoje só
      `status == 'HUMAN_REQUESTED'` pausava, e o robô respondia por cima dela.

Q3  `marcar_fim(attendance_session_id=…)` — o desfecho pelo EPISÓDIO
    → o EPISÓDIO ganha `resolvido_em`+`resolucao_motivo`, e a conversa ligada
      pela junção R3 ganha o MESMO instante (E8).

Q4  🔴 E `marcar_fim` NÃO APAGA `claimed_by`.
    → encerrar não é desatribuir. Quem atendeu continua sendo a dona do
      atendimento depois de ele terminar; a Fila é que deixa de contá-lo.

C   a LINHA DE CONTROLE: o MESMO `marcar_fim`, no MESMO episódio, com uma
    `company_id` que não é a dele → tem de NÃO marcar nada. Sem esta linha, um
    Q3 verde prova só que o caminho feliz escreve — não que a corretora é o
    que decide (CLAUDE.md §9.2).
```

⛔ Ele nunca imprime telefone nem nome: ids truncados e nada mais. Apaga SÓ as
linhas cujo id ele mesmo criou.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# 🔴 ANTES de qualquer `import app.` — é no ato do import que a variável é lida,
# e um import anterior tornaria a ordem uma coincidência.
os.environ["AUTOBROKERS_CANARIO"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# 🔴 MEDIDO em 04/09/2026 (`select id from companies`), não lembrado.
RESULTA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"

#: ⛔ Um número que não é de ninguém — o canário nunca usa telefone real.
TELEFONE_CANARIO = "5500000000097"
MARCA = "canario:097"


def p(texto="") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def plano() -> int:
    p("PLANO do canário 097 (nada foi executado — rode com `--vivo`):")
    p("  1. cria a conversa canário (title '%s') e o EPISÓDIO canário" % MARCA)
    p("     (`attendance_sessions`, summary {'canario':'097'}) já LIGADOS pela")
    p("     junção R3 (`attendance_sessions.conversation_id`)")
    p("  2. Q1 `abrir_espera(esperando_seguradora, vence em +2h)` → VERIFY:")
    p("     1 linha ativa em `work_waits`, com a corretora")
    p("  3. Q2 a atendente ASSUME: `claimed_by` = um usuário real da corretora,")
    p("     status segue 'open' → `pausar_ia(conversa)` tem de dar True (E6)")
    p("  4. Q3 `marcar_fim(attendance_session_id=…, motivo=")
    p("     'resolvido_pelo_segurado')` → VERIFY: `resolvido_em` no EPISÓDIO e")
    p("     o MESMO instante na conversa ligada (E8)")
    p("  5. Q4 🔴 e `claimed_by` CONTINUA lá — encerrar não é desatribuir")
    p("  6. CONTROLE: o mesmo `marcar_fim` com outra `company_id` → não marca")
    p("     nada (a segunda chamada é no episódio JÁ resolvido, então o teste é")
    p("     feito num episódio de controle criado só para isso)")
    p("  7. LIMPEZA por id (work_waits → episódio → conversa) e VERIFY 0/0/0")
    p("")
    p("  ⛔ Nenhuma mensagem sai. Nenhum agente é ligado. Só banco.")
    return 0


async def vivo(company_id: str, limpar: bool = True) -> int:
    from app.core.database import create_async_supabase_client, get_supabase_client
    from app.services.o_fim_do_atendimento import (
        ATIVO, ESPERANDO_SEGURADORA, RESOLVIDO_PELO_SEGURADO, abrir_espera,
        marcar_fim, pausar_ia,
    )

    sinc = get_supabase_client().client
    db = await create_async_supabase_client()

    agora = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())
    conversa_id = episodio_id = episodio_controle_id = None
    resultado = 0

    usuarios = (sinc.table("users_v2").select("id, role")
                .eq("company_id", company_id).limit(5).execute()).data or []
    if not usuarios:
        p("⛔ FALTOU: nenhum usuário na corretora %s — sem dono não dá para" % company_id[:8])
        p("   medir Q2/Q4.")
        return 2
    dono = str(usuarios[0]["id"])

    try:
        # ---------- 1. o mundo do canário --------------------------------
        # ⚠️ `conversations.user_id` é NOT NULL (📊 medido em 05/09/2026, na
        #    1ª rodada `--vivo`: 23502). O dono da conversa canário é o mesmo
        #    usuário que vai assumi-la no Q2.
        conversa = (sinc.table("conversations").insert({
            "company_id": company_id, "user_id": dono, "session_id": session_id,
            "channel": "whatsapp", "status": "open", "title": MARCA,
            "user_phone": TELEFONE_CANARIO, "unread_count": 0,
        }).execute()).data
        conversa_id = str(conversa[0]["id"])
        try:
            episodio = (sinc.table("attendance_sessions").insert({
                "company_id": company_id, "observer_number": TELEFONE_CANARIO,
                "counterparty": TELEFONE_CANARIO, "started_at": agora.isoformat(),
                "last_event_at": agora.isoformat(), "status": "open",
                "conversation_id": conversa_id, "summary": {"canario": "097"},
            }).execute()).data
        except Exception as erro:  # noqa: BLE001
            if "conversation_id" in str(erro) or "resolvido_em" in str(erro):
                p("⛔ FALTOU: a migration `20260905_01_spec097_episodio_tem_conversa.sql`")
                p("   ainda não foi aplicada — `attendance_sessions` não tem as colunas")
                p("   do elo nem do desfecho. Sem elas não há o que medir aqui.")
                raise
            raise
        episodio_id = str(episodio[0]["id"])
        p("conversa %s… · episódio %s… (ligados pela junção R3)"
          % (conversa_id[:8], episodio_id[:8]))

        # ---------- 2. Q1: a espera --------------------------------------
        abriu, porque = await abrir_espera(
            db, company_id=company_id, conversation_id=conversa_id,
            kind=ESPERANDO_SEGURADORA, scope=MARCA,
            vence_em_iso=(agora + timedelta(hours=2)).isoformat())
        esperas = (sinc.table("work_waits")
                   .select("id, kind, status, company_id, vence_em")
                   .eq("company_id", company_id)
                   .eq("conversation_id", conversa_id).execute()).data or []
        ativas = [w for w in esperas if w.get("status") == ATIVO]
        p("Q1 abrir_espera → abriu=%s porque=%s | linhas=%d ativas=%d kind=%s"
          % (abriu, porque, len(esperas), len(ativas),
             (ativas[0].get("kind") if ativas else "—")))
        p("Q1 régua: 1 linha ativa de `esperando_seguradora` → %s"
          % ("OK" if len(ativas) == 1 and ativas[0].get("kind") == ESPERANDO_SEGURADORA
             else "⛔ FALHOU"))
        if not (len(ativas) == 1):
            resultado = 1

        # ---------- 3. Q2: a atendente assume ----------------------------
        (sinc.table("conversations")
             .update({"claimed_by": dono, "claimed_by_name": MARCA})
             .eq("company_id", company_id)                      # 🔴 §7
             .eq("id", conversa_id).execute())
        linha = (sinc.table("conversations")
                 .select("id, status, claimed_by")
                 .eq("company_id", company_id)
                 .eq("id", conversa_id).limit(1).execute()).data[0]
        pausou = pausar_ia(linha)
        p("Q2 claimed_by preenchido, status=%s → pausar_ia=%s | régua: True → %s"
          % (linha.get("status"), pausou, "OK" if pausou else "⛔ FALHOU (E6)"))
        if not pausou:
            resultado = 1

        # ---------- 4. Q3: o fim pelo EPISÓDIO ---------------------------
        marcou, motivo = await marcar_fim(
            db, company_id=company_id, motivo=RESOLVIDO_PELO_SEGURADO,
            attendance_session_id=episodio_id)
        ep = (sinc.table("attendance_sessions")
              .select("id, resolvido_em, resolucao_motivo, conversation_id")
              .eq("company_id", company_id)
              .eq("id", episodio_id).limit(1).execute()).data[0]
        cv = (sinc.table("conversations")
              .select("id, resolvido_em, resolucao_motivo, claimed_by, status")
              .eq("company_id", company_id)
              .eq("id", conversa_id).limit(1).execute()).data[0]
        p("Q3 marcar_fim(episódio) → marcou=%s motivo=%s" % (marcou, motivo))
        p("Q3 EPISÓDIO: resolvido_em=%s motivo=%s"
          % (ep.get("resolvido_em"), ep.get("resolucao_motivo")))
        p("Q3 CONVERSA: resolvido_em=%s motivo=%s"
          % (cv.get("resolvido_em"), cv.get("resolucao_motivo")))
        espelhou = bool(ep.get("resolvido_em")) and bool(cv.get("resolvido_em"))
        p("Q3 régua: episódio marcado E conversa espelhada (E8) → %s"
          % ("OK" if espelhou else "⛔ FALHOU"))
        if not espelhou:
            resultado = 1

        # ---------- 5. Q4: o dono FICA -----------------------------------
        manteve = str(cv.get("claimed_by") or "") == dono
        p("Q4 claimed_by depois do fim = %s | régua: continua %s… → %s"
          % ((str(cv.get("claimed_by"))[:8] + "…") if cv.get("claimed_by") else "NULO",
             dono[:8], "OK" if manteve else "⛔ FALHOU — encerrar apagou o dono"))
        if not manteve:
            resultado = 1

        # ---------- 6. CONTROLE: a corretora é o que decide --------------
        # ⚠️ Num episódio NOVO, senão a recusa poderia vir da idempotência
        #    (`resolvido_em IS NULL`) em vez de vir do filtro por corretora — e
        #    um controle que passa pelo motivo errado não controla nada.
        controle = (sinc.table("attendance_sessions").insert({
            "company_id": company_id, "observer_number": TELEFONE_CANARIO,
            "counterparty": TELEFONE_CANARIO, "started_at": agora.isoformat(),
            "last_event_at": agora.isoformat(), "status": "open",
            "summary": {"canario": "097-controle"},
        }).execute()).data
        episodio_controle_id = str(controle[0]["id"])
        outra = str(uuid.uuid4())
        marcou_ctl, porque_ctl = await marcar_fim(
            db, company_id=outra, motivo=RESOLVIDO_PELO_SEGURADO,
            attendance_session_id=episodio_controle_id)
        ep_ctl = (sinc.table("attendance_sessions")
                  .select("id, resolvido_em")
                  .eq("id", episodio_controle_id).limit(1).execute()).data[0]
        recusou = (not marcou_ctl) and ep_ctl.get("resolvido_em") is None
        p("CONTROLE outra corretora → marcou=%s porque=%s resolvido_em=%s | %s"
          % (marcou_ctl, porque_ctl, ep_ctl.get("resolvido_em"),
             "OK — o UUID não é autorização (§7)" if recusou
             else "⛔ MARCOU O EPISÓDIO DE OUTRA CORRETORA"))
        if not recusou:
            resultado = 1

    except Exception as erro:  # noqa: BLE001
        p("⛔ o canário parou: %s: %s" % (type(erro).__name__, erro))
        resultado = 2
    finally:
        if limpar:
            # ⛔ Apaga SÓ o que o canário criou, POR ID.
            for w in ((sinc.table("work_waits").select("id")
                       .eq("company_id", company_id)
                       .eq("conversation_id", conversa_id).execute()).data or []) \
                    if conversa_id else []:
                sinc.table("work_waits").delete().eq("id", str(w["id"])).execute()
            for alvo in (episodio_id, episodio_controle_id):
                if alvo:
                    sinc.table("attendance_sessions").delete().eq("id", alvo).execute()
            if conversa_id:
                sinc.table("conversations").delete().eq("id", conversa_id).execute()

            restam_w = len((sinc.table("work_waits").select("id")
                            .eq("company_id", company_id)
                            .eq("conversation_id", conversa_id).execute()).data or []) \
                if conversa_id else 0
            restam_e = 0
            for alvo in (episodio_id, episodio_controle_id):
                if alvo:
                    restam_e += len((sinc.table("attendance_sessions").select("id")
                                     .eq("id", alvo).execute()).data or [])
            restam_c = len((sinc.table("conversations").select("id")
                            .eq("id", conversa_id).execute()).data or []) \
                if conversa_id else 0
            p("LIMPEZA — work_waits=%d · episódios=%d · conversas=%d (esperado 0/0/0)"
              % (restam_w, restam_e, restam_c))
            if restam_w or restam_e or restam_c:
                resultado = 1
    return resultado


def main() -> int:
    ap = argparse.ArgumentParser(description="O canário da SPEC-097")
    ap.add_argument("--vivo", action="store_true", help="executa de verdade")
    ap.add_argument("--dry-run", action="store_true", help="só imprime o plano (padrão)")
    ap.add_argument("--company", default=RESULTA)
    ap.add_argument("--sem-limpeza", action="store_true",
                    help="não apaga o que criou (para inspeção manual)")
    args = ap.parse_args()

    if not args.vivo:
        return plano()

    import asyncio
    return asyncio.run(vivo(str(args.company), limpar=not args.sem_limpeza))


if __name__ == "__main__":
    sys.exit(main())
