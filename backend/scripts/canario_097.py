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

Q5  🔴 O CORREDOR TERMINA **SEM ESPELHO** — e o episódio recebe o desfecho.
    → um dublê da sessão de acionamento (`client_phone`, `created_at`, e
      **nenhum** `mirror_conversation_id`) entra no MOTOR de verdade
      (`dispatch_router._marcar_fim_do_atendimento`, fase `resolvido`), e o
      EPISÓDIO daquele telefone tem de ganhar `resolvido_em`.
      📊 05/09/2026: `attendance_session_id` tinha 15 ocorrências no backend e
      ZERO escritas — o caminho "com `DISPATCH_MIRROR=0` o episódio basta"
      nunca recebia episódio nenhum, e o acionamento saía sem marcar nada.
      CONTROLE do próprio Q5: o mesmo resolvedor, num telefone sem episódio,
      tem de devolver vazio — senão ele estaria devolvendo qualquer linha.

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
#: ⚠️ Um telefone SÓ do Q5, e a separação não é enfeite: o resolvedor do
#: corredor junta por `(company_id, counterparty)` e recusa empate de
#: `last_event_at`. Reaproveitar o número do Q1–Q4 faria o Q5 medir a colisão
#: entre episódios canários em vez de medir o elo.
TELEFONE_CORREDOR = "5500000000098"
#: ⛔ E este nunca ganha episódio — é o controle do Q5.
TELEFONE_SEM_EPISODIO = "5500000000099"
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
    p("  3. Q2 CONTROLE: a MESMA conversa SEM dono → `pausar_ia` False; então")
    p("     a atendente ASSUME: `claimed_by` = um usuário real da corretora,")
    p("     status segue 'open' → `pausar_ia(conversa)` tem de dar True (E6)")
    p("  4. Q3 `marcar_fim(attendance_session_id=…, motivo=")
    p("     'resolvido_pelo_segurado')` → VERIFY: `resolvido_em` no EPISÓDIO e")
    p("     o MESMO instante na conversa ligada (E8)")
    p("  5. Q4 🔴 e `claimed_by` CONTINUA lá — encerrar não é desatribuir;")
    p("     Q4b e MESMO ASSIM `pausar_ia` volta a dar False — a pausa é do")
    p("     atendimento VIVO, e morre com o desfecho (P0-1)")
    p("  6. Q5 o CORREDOR sem espelho: dublê da sessão de acionamento (só")
    p("     `client_phone`, sem `mirror_conversation_id`) no motor real")
    p("     `_marcar_fim_do_atendimento(fase='resolvido')` → o EPISÓDIO daquele")
    p("     telefone ganha `resolvido_em`; e o resolvedor num telefone SEM")
    p("     episódio devolve vazio (controle do próprio Q5)")
    p("  7. CONTROLE: o mesmo `marcar_fim` com outra `company_id` → não marca")
    p("     nada (a segunda chamada é no episódio JÁ resolvido, então o teste é")
    p("     feito num episódio de controle criado só para isso)")
    p("  8. LIMPEZA por id (work_waits → episódio → conversa) e VERIFY 0/0/0")
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
    episodio_corredor_id = None
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
        # 🔴 A LINHA DE CONTROLE, e ela vem ANTES: a MESMA conversa, ainda sem
        #    dono, tem de dar `pausar_ia = False`. Sem ela, um `True` depois do
        #    claim provaria só que a função devolve True — não que é o DONO que
        #    a faz mudar de resposta (CLAUDE.md §9.2).
        antes = (sinc.table("conversations")
                 .select("id, status, claimed_by, resolvido_em")
                 .eq("company_id", company_id)
                 .eq("id", conversa_id).limit(1).execute()).data[0]
        pausou_antes = pausar_ia(antes)
        p("Q2 CONTROLE (mesma conversa, SEM dono) → pausar_ia=%s | régua: False → %s"
          % (pausou_antes, "OK" if not pausou_antes else "⛔ pausa sem ninguém ter assumido"))
        if pausou_antes:
            resultado = 1

        (sinc.table("conversations")
             .update({"claimed_by": dono, "claimed_by_name": MARCA})
             .eq("company_id", company_id)                      # 🔴 §7
             .eq("id", conversa_id).execute())
        linha = (sinc.table("conversations")
                 .select("id, status, claimed_by, resolvido_em")
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

        # ---------- 5.b Q4b: depois do fim, a IA VOLTA A FALAR -----------
        # 🔴 O par do Q4, e ele é o P0-1. `claimed_by` FICA (Q4) — e é por isso
        #    que a pausa não pode olhar só para ele: 📊 `get_or_create_conversation`
        #    reusa a MESMA linha por telefone, então a mensagem que este segurado
        #    mandar em novembro cai nesta conversa encerrada, com o dono de
        #    setembro ainda nela. Sem esta régua, o caminho feliz da Fila deixa o
        #    segurado sem robô para sempre.
        pausou_depois = pausar_ia(cv)
        p("Q4b claimed_by=%s + resolvido_em=%s → pausar_ia=%s | régua: False → %s"
          % (bool(cv.get("claimed_by")), bool(cv.get("resolvido_em")), pausou_depois,
             "OK — a pausa é do atendimento VIVO" if not pausou_depois
             else "⛔ FALHOU (P0-1) — a IA cala PARA SEMPRE neste segurado"))
        if pausou_depois:
            resultado = 1

        # ---------- 6. Q5: o CORREDOR termina SEM ESPELHO ----------------
        # 🔴 O motor de verdade, com um DUBLÊ da sessão de acionamento. O que se
        #    afirma é o comportamento de `_marcar_fim_do_atendimento` sobre uma
        #    sessão REAL na forma (CLAUDE.md §9.4) — não o de um helper local
        #    que reimplementasse a junção.
        from app.services.dispatch_router import (
            _episodio_do_atendimento, _marcar_fim_do_atendimento,
        )

        corredor = (sinc.table("attendance_sessions").insert({
            "company_id": company_id, "observer_number": TELEFONE_CANARIO,
            "counterparty": TELEFONE_CORREDOR, "started_at": agora.isoformat(),
            "last_event_at": agora.isoformat(), "status": "open",
            "summary": {"canario": "097-corredor"},
        }).execute()).data
        episodio_corredor_id = str(corredor[0]["id"])

        # ⛔ SEM `mirror_conversation_id` — é este o caso que a U1.2 conserta:
        #    `DISPATCH_MIRROR=0`, nenhuma conversa espelhada, e o desfecho tendo
        #    de chegar ao episódio assim mesmo.
        sessao_duble = {"client_phone": TELEFONE_CORREDOR,
                        "created_at": agora.isoformat(),
                        "state": "resolvido"}
        await _marcar_fim_do_atendimento(db, company_id, sessao_duble, "resolvido")
        ep_cor = (sinc.table("attendance_sessions")
                  .select("id, resolvido_em, resolucao_motivo")
                  .eq("company_id", company_id)
                  .eq("id", episodio_corredor_id).limit(1).execute()).data[0]
        elo = str(sessao_duble.get("attendance_session_id") or "")
        p("Q5 corredor SEM espelho → episódio resolvido_em=%s motivo=%s | elo na "
          "sessão=%s" % (ep_cor.get("resolvido_em"), ep_cor.get("resolucao_motivo"),
                         (elo[:8] + "…") if elo else "NENHUM"))
        chegou = (bool(ep_cor.get("resolvido_em"))
                  and str(ep_cor.get("resolucao_motivo") or "") == "acionamento_concluido"
                  and elo == episodio_corredor_id)
        p("Q5 régua: o EPISÓDIO recebe o desfecho do corredor sem espelho → %s"
          % ("OK" if chegou else "⛔ FALHOU — o elo não chegou (P1-4)"))
        if not chegou:
            resultado = 1

        # 🔴 CONTROLE DO Q5: o MESMO resolvedor, num telefone sem episódio.
        #    Sem esta linha, um Q5 verde provaria só que algo foi marcado — não
        #    que a junção por telefone é o que escolhe (CLAUDE.md §9.2).
        vazio = await _episodio_do_atendimento(
            db, company_id, {"client_phone": TELEFONE_SEM_EPISODIO,
                             "created_at": agora.isoformat()})
        p("Q5 CONTROLE telefone sem episódio → resolvedor devolveu %r | %s"
          % (vazio, "OK" if not vazio else "⛔ DEVOLVEU UM EPISÓDIO QUE NÃO É DELE"))
        if vazio:
            resultado = 1

        # ---------- 7. CONTROLE: a corretora é o que decide --------------
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
                  .eq("company_id", company_id)                  # 🔴 §7
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
            #
            # 🔴 E COM `company_id` EM TODO DELETE E EM TODA RECONFERÊNCIA —
            #    não é redundância com o id. O backend usa service role e
            #    atravessa a RLS inteira, e este script roda contra o banco VIVO
            #    do Founder: §7 diz que o filtro de corretora no código é
            #    obrigação, não enfeite. Um id trocado numa edição apagaria a
            #    linha de outra corretora, e nada barraria.
            for w in ((sinc.table("work_waits").select("id")
                       .eq("company_id", company_id)
                       .eq("conversation_id", conversa_id).execute()).data or []) \
                    if conversa_id else []:
                (sinc.table("work_waits").delete()
                 .eq("company_id", company_id)                   # 🔴 §7
                 .eq("id", str(w["id"])).execute())
            for alvo in (episodio_id, episodio_controle_id, episodio_corredor_id):
                if alvo:
                    (sinc.table("attendance_sessions").delete()
                     .eq("company_id", company_id)               # 🔴 §7
                     .eq("id", alvo).execute())
            if conversa_id:
                (sinc.table("conversations").delete()
                 .eq("company_id", company_id)                   # 🔴 §7
                 .eq("id", conversa_id).execute())

            restam_w = len((sinc.table("work_waits").select("id")
                            .eq("company_id", company_id)
                            .eq("conversation_id", conversa_id).execute()).data or []) \
                if conversa_id else 0
            restam_e = 0
            for alvo in (episodio_id, episodio_controle_id, episodio_corredor_id):
                if alvo:
                    restam_e += len((sinc.table("attendance_sessions").select("id")
                                     .eq("company_id", company_id)   # 🔴 §7
                                     .eq("id", alvo).execute()).data or [])
            restam_c = len((sinc.table("conversations").select("id")
                            .eq("company_id", company_id)            # 🔴 §7
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
