# -*- coding: utf-8 -*-
"""O canário vivo da SPEC-097.1 — o pós-acionamento, medido no banco de verdade.

```
--dry-run   (padrão) imprime o PLANO e não toca em nada.
--vivo      cria UM episódio+conversa canário na Resulta, roda o MOTOR real do
            corredor, prova a espera, a novidade SUPRIMIDA, o dossiê PÓS e o
            desfecho — e apaga o que criou, por id e por corretora.
```

## Por que ele é a ÚNICA prova possível

📊 Medido em 05/09/2026: `work_waits` tem **zero linhas na vida** e
`work_steps` com `step_type='dispatch_phase'` são 12 em todo o banco, sem um
`captured` sequer. **Não há histórico para medir** — os quatro `work_runs` são
de 18–19/08, anteriores à migration de 26/08. Uma régua sobre o acervo não
consegue dizer nada sobre a U1; só um canário consegue.

## O que ele mede

```
Q1  a TELA da seguradora passa por `extract_capture_anchors` (o motor REAL do
    corredor) e o `captured` que ele devolve vai para
    `_pos_acionamento_do_checkpoint` — a função que o checkpoint chama para
    cumprir a U1, e que **não** cria `work_runs`/`work_steps`/`work_events`
    → 1 linha ativa em `work_waits`, `scope='pos_acionamento'`,
      `kind='esperando_seguradora'`, com a corretora e com `vence_em`.
      CONTROLE, ANTES: nenhuma espera na conversa (senão Q1 mede o passado).

Q2  a MESMA tela com OUTRA data
    → a espera anterior fica `satisfeito_por='substituida'` e sobra UMA ativa
      (📊 até 05/09 a segunda era PERDIDA no UNIQUE — [B3p]/[K2]);
    → e a NOVIDADE é GERADA e **SUPRIMIDA**: 📊 os 4 agentes `attendance` estão
      `is_active=false`, então em produção nada sai — e o motivo fica gravado em
      `ficha_atendimento.acompanhamento` provando que houve algo a dizer.
      CONTROLE: a contagem de `work_events` da corretora é a MESMA antes e
      depois — ZERO tentados. 🔴 O canário não escreve em tabela que ele não
      sabe apagar: `work_events` é APPEND-ONLY no banco.

Q3  o dossiê do handoff sobre a conversa canário (montagem PURA, nada enviado)
    → título `🔁 PÓS-ACIONAMENTO`, `Onde parou` com a espera escrita, e
      **nunca** "conclua o acionamento".
      CONTROLE: a MESMA função numa conversa SEM acionamento → título antigo.

Q4  `marcar_fim` → a espera fica `satisfeito_por='desfecho'` e nenhuma ativa
    sobra. CONTROLE: a espera de OUTRA corretora (não criada aqui) não é
    tocada — o filtro é por `company_id` em toda escrita (§7).
```

⛔ Nenhuma mensagem sai. Nenhum agente é ligado. Nada de PII: ids truncados e
contagens. A limpeza apaga SÓ as linhas cujo id ele mesmo criou — `work_waits`,
o episódio e as duas conversas — e VERIFICA 0/0/0.

🔴 **E ele não cria o que não consegue recolher.** A versão de 05/09 passava
por `registrar_checkpoint` e deixava em produção um `work_run` e quatro
`work_events` que o próprio banco proíbe apagar (append-only). Canário sem volta
não é canário: é lixo com nome bonito.
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

# 🔴 ANTES de qualquer `import app.` — a variável é lida no ato do import.
os.environ["AUTOBROKERS_CANARIO"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

#: 🔴 MEDIDO (`select id from companies`), não lembrado.
RESULTA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"

#: ⛔ Números que não são de ninguém — o canário nunca usa telefone real.
TELEFONE_CANARIO = "5500000000971"
TELEFONE_SEM_ACIONAMENTO = "5500000000972"
MARCA = "canario:097.1"


def p(texto="") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


#: 💭 A TELA DO CANÁRIO — texto de seguradora, no formato que as âncoras reais
#: leem. ⛔ Números óbvios e fictícios: o canário nunca copia tela de segurado.
TELA_DO_CANARIO = ("Seu servico foi aberto com sucesso! Protocolo: 2026-00000971. "
                   "O atendimento esta agendado para o dia %s as 14:00.")


def _captured_do_motor(dia):
    """O `captured` que o CORREDOR REAL escreveria diante desta tela.

    🔴 P0 do red team: montar `session['protocolo']` à mão provava a espera
    sobre uma sessão que **a produção nunca monta**. Aqui a tela passa por
    `extract_capture_anchors` — o mesmo motor de `insurer_dispatch_service:2323`
    — e o que entra no checkpoint é o que ele devolveu (CLAUDE.md §9.4).

    Devolve `(captured, nome_do_corredor, tela)`.
    """
    from app.services.corridor_playbooks import _PLAYBOOKS, extract_capture_anchors

    tela = TELA_DO_CANARIO % dia.strftime("%d/%m/%Y")
    for nome in sorted(_PLAYBOOKS):
        achado = extract_capture_anchors(_PLAYBOOKS[nome], tela) or {}
        if achado.get("protocol") and achado.get("schedule"):
            return achado, nome, tela
    return {}, "", tela


def plano() -> int:
    p("PLANO do canário 097.1 (nada foi executado — rode com `--vivo`):")
    p("  0. CONTROLE ANTES: conta as esperas da conversa canário → tem de ser 0")
    p("     (senão Q1 mediria uma linha que já existia)")
    p("  1. cria a conversa canário (title '%s') e o EPISÓDIO canário," % MARCA)
    p("     ligados pela junção R3, mais uma conversa de CONTROLE sem acionamento")
    p("  2. Q1 a TELA da seguradora passa por `extract_capture_anchors` (o motor")
    p("     REAL do corredor) e o `captured` que ele devolve vai para")
    p("     `dispatch_router._pos_acionamento_do_checkpoint(fase='captured')`")
    p("     — o motor da U1 SEM a papelada durável — → VERIFY: 1")
    p("     linha ativa em `work_waits`, `scope='pos_acionamento'`,")
    p("     `kind='esperando_seguradora'`, com `company_id` e `vence_em` = o DIA")
    p("     agendado na tela, lido dd/mm (nunca MDY)")
    p("     🔴 antes desta versão a sessão era montada à mão, com chaves que")
    p("     nenhum escritor produz — o P0 do red team")
    p("  3. Q2 a MESMA tela com OUTRA data → VERIFY: a anterior")
    p("     `satisfeito_por='substituida'`, UMA ativa; e a NOVIDADE é gerada e")
    p("     SUPRIMIDA (📊 agentes desligados), com o motivo gravado em")
    p("     `ficha_atendimento.acompanhamento` — e ZERO `work_events` tentados,")
    p("     medido por CONTAGEM da corretora antes × depois")
    p("  4. Q3 `HumanHandoffTool._montar_dossie` (montagem PURA, nada é enviado)")
    p("     → título `🔁 PÓS-ACIONAMENTO`, `Onde parou` com a espera escrita,")
    p("     e NUNCA 'conclua o acionamento'. CONTROLE: a conversa sem acionamento")
    p("     recebe o título antigo")
    p("  5. Q4 `marcar_fim(acionamento_concluido)` → a espera fica")
    p("     `satisfeito_por='desfecho'` e nenhuma ativa sobra")
    p("  6. LIMPEZA por id E por corretora (work_waits → attendance_sessions →")
    p("     conversations) e VERIFY 0/0/0. 🔴 Não há `work_runs` nem")
    p("     `work_events` para apagar porque o canário não os cria: a tabela é")
    p("     append-only e uma limpeza impossível é uma limpeza que não existe")
    p("")
    p("  ⛔ Nenhuma mensagem sai. Nenhum agente é ligado. Nenhuma migration é")
    p("     aplicada. Zero PII na saída.")
    return 0


async def vivo(company_id: str, limpar: bool = True) -> int:  # noqa: C901
    from app.agents.tools.human_handoff import HumanHandoffTool
    from app.core.database import create_async_supabase_client, get_supabase_client
    from app.services import dispatch_router as DR
    from app.services.o_fim_do_atendimento import (
        ACIONAMENTO_CONCLUIDO, ATIVO, ESCOPO_POS_ACIONAMENTO, marcar_fim,
    )

    sinc = get_supabase_client().client
    db = await create_async_supabase_client()

    agora = datetime.now(timezone.utc)
    # As duas datas que a seguradora "diz" na tela — a segunda é a previsão que
    # MUDOU, e é ela que tem de gerar a novidade (U5.1).
    dia_1 = agora + timedelta(days=3)
    dia_2 = agora + timedelta(days=10)
    session_id = str(uuid.uuid4())
    conversa_id = conversa_controle_id = episodio_id = None
    resultado = 0

    usuarios = (sinc.table("users_v2").select("id")
                .eq("company_id", company_id).limit(1).execute()).data or []
    if not usuarios:
        p("⛔ FALTOU: nenhum usuário na corretora %s — `conversations.user_id` é"
          % company_id[:8])
        p("   NOT NULL e não há de quem ser a conversa canário.")
        return 2
    dono = str(usuarios[0]["id"])

    def esperas_da_conversa(cid):
        if not cid:
            return []
        return (sinc.table("work_waits")
                .select("id, kind, scope, status, satisfeito_por, vence_em, company_id")
                .eq("company_id", company_id)                  # 🔴 §7
                .eq("conversation_id", cid).execute()).data or []

    try:
        # ---------- 1. o mundo do canário --------------------------------
        conversa = (sinc.table("conversations").insert({
            "company_id": company_id, "user_id": dono, "session_id": session_id,
            "channel": "whatsapp", "status": "open", "title": MARCA,
            "user_phone": TELEFONE_CANARIO, "unread_count": 0,
            "ficha_atendimento": {"servico": "vidros", "ramo": "auto",
                                  "seguradora": "canaria",
                                  "dispatch_state": "captured",
                                  "protocolo": "P-CANARIO-0971"},
            "last_message_preview": "e a previsao do vidro?",
        }).execute()).data
        conversa_id = str(conversa[0]["id"])
        controle = (sinc.table("conversations").insert({
            "company_id": company_id, "user_id": dono,
            "session_id": str(uuid.uuid4()), "channel": "whatsapp",
            "status": "open", "title": MARCA + ":controle",
            "user_phone": TELEFONE_SEM_ACIONAMENTO, "unread_count": 0,
            "ficha_atendimento": {"servico": "guincho", "faltando": ["endereço exato"]},
            "last_message_preview": "meu carro quebrou agora, preciso de guincho",
        }).execute()).data
        conversa_controle_id = str(controle[0]["id"])
        episodio = (sinc.table("attendance_sessions").insert({
            "company_id": company_id, "observer_number": TELEFONE_CANARIO,
            "counterparty": TELEFONE_CANARIO, "started_at": agora.isoformat(),
            "last_event_at": agora.isoformat(), "status": "open",
            "conversation_id": conversa_id, "summary": {"canario": "097.1"},
        }).execute()).data
        episodio_id = str(episodio[0]["id"])
        p("conversa %s… · controle %s… · episódio %s…"
          % (conversa_id[:8], conversa_controle_id[:8], episodio_id[:8]))

        # ---------- 0. O CONTROLE, e ele vem ANTES -----------------------
        antes = esperas_da_conversa(conversa_id)
        p("CONTROLE ANTES — esperas na conversa canário: %d (esperado 0) → %s"
          % (len(antes), "OK" if not antes else "⛔ FALHOU"))
        if antes:
            resultado = 1

        # ---------- 2. Q1: o MOTOR real abre a espera --------------------
        #
        # 🔴 P0 do red team (05/09/2026): esta sessão era montada À MÃO, com
        # `protocolo` e `previsao` soltos e dentro de `slots` — **chaves que
        # nenhum escritor do produto produz**. O canário provava a espera sobre
        # uma sessão que a produção nunca monta (CLAUDE.md §9.4: o texto da tela
        # vem do acervo, não da imaginação).
        #
        # Agora a tela passa pelo MOTOR real (`extract_capture_anchors`), e o
        # que vai para o checkpoint é o `captured` que ele devolveu.
        cap_1, corredor, tela_1 = _captured_do_motor(dia_1)
        if not cap_1.get("protocol") or not cap_1.get("schedule"):
            p("⛔ FALTOU: nenhuma âncora real de corredor casou a tela do canário —")
            p("   sem `captured` do motor o canário mediria a sessão imaginada.")
            p("   tela=%r captured=%r" % (tela_1[:80], cap_1))
            return 2
        p("Q1 âncoras REAIS do corredor `%s` → captured=%r" % (corredor, cap_1))
        sessao = {"state": "captured", "case_id": "case-%s" % MARCA,
                  "mirror_conversation_id": conversa_id,
                  "playbook_ref": "canaria-auto", "subservice": "vidros",
                  "company_id": company_id, "client_phone": TELEFONE_CANARIO,
                  # ⚠️ `slots` é o que a URA PEDE, nunca o que ela devolve.
                  "slots": {"placa": "ABC1D23", "cep": "01310000"},
                  "captured": dict(cap_1)}
        # 🔴 [J-5] — `_pos_acionamento_do_checkpoint`, E NÃO `registrar_checkpoint`.
        #
        # ⛔ `registrar_checkpoint` cria `work_runs`+`work_steps`+`work_events`
        #    antes de chegar aqui, e **`work_events` é APPEND-ONLY** no banco
        #    (trigger `tg_work_events_append_only`: DELETE proibido). Com
        #    `work_runs` cascateando para ela, a limpeza do canário virava
        #    impossível por desenho — o canário criava lixo em produção que ele
        #    mesmo não conseguia recolher (o juiz mediu: 1 run e 4 eventos
        #    residentes na Resulta).
        #
        # ⚠️ E o que a U1 promete NÃO é o run: é a espera. Esta é a função que
        #    `registrar_checkpoint` chama para cumpri-la (l.1270) — o MESMO
        #    motor, sem a papelada durável que o canário não sabe desfazer.
        #    A sessão vai SEM `work_run_id`, e é isso que mantém a espera e a
        #    supressão inteiramente recolhíveis.
        await DR._pos_acionamento_do_checkpoint(db, company_id, dict(sessao),
                                                "captured")

        linhas = esperas_da_conversa(conversa_id)
        ativas = [w for w in linhas if w.get("status") == ATIVO]
        certa = (len(ativas) == 1
                 and str(ativas[0].get("scope")) == ESCOPO_POS_ACIONAMENTO
                 and str(ativas[0].get("kind")) == "esperando_seguradora"
                 and str(ativas[0].get("company_id")) == company_id
                 # 🔴 O prazo é o DIA QUE A SEGURADORA DISSE na tela, lido
                 #    como dd/mm ([3] do red team: em MDY `12/09` viraria
                 #    dezembro, e o vigia só cobraria em três meses).
                 and str(ativas[0].get("vence_em") or "")[:10] == dia_1.strftime("%Y-%m-%d"))
        p("Q1 checkpoint `captured` → linhas=%d ativas=%d scope=%s kind=%s"
          % (len(linhas), len(ativas),
             ativas[0].get("scope") if ativas else "—",
             ativas[0].get("kind") if ativas else "—"))
        p("Q1 régua: 1 ativa em `pos_acionamento`, esperando a seguradora, com"
          " a previsão como prazo → %s" % ("OK" if certa else "⛔ FALHOU"))
        if not certa:
            resultado = 1

        # ---------- 3. Q2: a previsão MUDA -------------------------------
        # 🔴 [J-5] O CONTROLE MUDOU DE PERGUNTA, E A NOVA É A HONESTA.
        #
        # ⚠️ A anterior contava eventos do tipo da novidade e depois exigia que
        #    NENHUM tivesse nascido — contra a própria montagem, que criava um
        #    `work_run` e escrevia eventos de fase. Agora o canário não cria run
        #    nenhum, então a pergunta pode ser a que interessa: **a corretora
        #    inteira termina com o MESMO número de `work_events` que tinha.**
        #    Zero tentados, medido por contagem antes × depois.
        def _eventos_da_corretora():
            achado = (sinc.table("work_events").select("id", count="exact")
                      .eq("company_id", company_id).limit(1).execute())   # 🔴 §7
            return int(getattr(achado, "count", None) or 0)

        eventos_antes = _eventos_da_corretora()
        cap_2, _corredor2, _tela2 = _captured_do_motor(dia_2)
        sessao2 = dict(sessao, captured=dict(cap_2))
        await DR._pos_acionamento_do_checkpoint(db, company_id, sessao2, "captured")

        linhas2 = esperas_da_conversa(conversa_id)
        ativas2 = [w for w in linhas2 if w.get("status") == ATIVO]
        substituidas = [w for w in linhas2 if w.get("satisfeito_por") == "substituida"]
        p("Q2 previsão mudou → linhas=%d ativas=%d substituídas=%d"
          % (len(linhas2), len(ativas2), len(substituidas)))
        ok2 = len(ativas2) == 1 and len(substituidas) == 1
        p("Q2 régua: a anterior vira 'substituida' e sobra UMA ativa → %s"
          % ("OK" if ok2 else "⛔ FALHOU"))
        if not ok2:
            resultado = 1

        eventos_depois = _eventos_da_corretora()
        nasceram = eventos_depois - eventos_antes

        # 🔴 A SUPRESSÃO MORA NA FICHA DA CONVERSA — achado da lente
        # DADO+verdade. 📊 `work_events.work_run_id` é NOT NULL e só 4 de 729
        # conversas têm `work_run`: para a conversa canária, que não tem sombra,
        # o INSERT em `work_events` **violaria a coluna** e a prova sumiria no
        # `except`. O registro que sempre existe é
        # `ficha_atendimento.acompanhamento`, e é ele que o canário confere.
        ficha_depois = ((sinc.table("conversations").select("ficha_atendimento")
                         .eq("company_id", company_id)                 # 🔴 §7
                         .eq("id", conversa_id).limit(1).execute()).data or [{}])[0]
        marca = ((ficha_depois.get("ficha_atendimento") or {}).get("acompanhamento")
                 if isinstance(ficha_depois.get("ficha_atendimento"), dict) else None)
        marca = marca if isinstance(marca, dict) else {}
        motivo_suprimida = str((marca.get("ultima") or {}).get("motivo") or "")
        na_ficha = int(marca.get("suprimidas") or 0) >= 1 and bool(motivo_suprimida)
        p("Q2b novidade: na ficha suprimidas=%s motivo=%r · work_events da "
          "corretora antes=%d depois=%d"
          % (marca.get("suprimidas"), motivo_suprimida, eventos_antes, eventos_depois))
        p("Q2b régua: 📊 os agentes estão DESLIGADOS, então a novidade é GERADA e"
          " SUPRIMIDA, nunca enviada, e a supressão fica ESCRITA → %s"
          % ("OK" if na_ficha else "⛔ FALHOU"))
        p("Q2b CONTROLE: ZERO `work_events` tentados — a contagem da corretora "
          "não mudou → %s"
          % ("OK" if nasceram == 0 else "⛔ FALHOU (%d eventos novos)" % nasceram))
        if not na_ficha or nasceram:
            resultado = 1

        # ---------- 4. Q3: o dossiê PÓS (montagem pura) ------------------
        linha_conversa = (sinc.table("conversations").select("*")
                          .eq("company_id", company_id)                # 🔴 §7
                          .eq("id", conversa_id).limit(1).execute()).data or [{}]
        linha_controle = (sinc.table("conversations").select("*")
                          .eq("company_id", company_id)                # 🔴 §7
                          .eq("id", conversa_controle_id).limit(1).execute()).data or [{}]
        ferramenta = HumanHandoffTool(sinc)
        dossie = ferramenta._montar_dossie(linha_conversa[0], "")
        dossie_controle = ferramenta._montar_dossie(linha_controle[0], "")
        ok3 = ("PÓS-ACIONAMENTO" in dossie
               and "onde parou" in dossie.lower()
               and "esperando" in dossie.lower()
               and "conclua o acionamento" not in dossie.lower())
        p("Q3 dossiê: título POS=%s · 'Onde parou'=%s · 'conclua'=%s"
          % ("PÓS-ACIONAMENTO" in dossie, "onde parou" in dossie.lower(),
             "conclua o acionamento" in dossie.lower()))
        p("Q3 régua: diz PÓS, diz de quem se espera e nunca manda concluir → %s"
          % ("OK" if ok3 else "⛔ FALHOU"))
        p("Q3 CONTROLE: a conversa SEM acionamento recebe o título antigo → %s"
          % ("OK" if "PÓS-ACIONAMENTO" not in dossie_controle else "⛔ FALHOU"))
        if not ok3 or "PÓS-ACIONAMENTO" in dossie_controle:
            resultado = 1

        # ---------- 5. Q4: o desfecho fecha a espera ---------------------
        marcou, porque = await marcar_fim(db, company_id=company_id,
                                          motivo=ACIONAMENTO_CONCLUIDO,
                                          conversation_id=conversa_id)
        linhas4 = esperas_da_conversa(conversa_id)
        ativas4 = [w for w in linhas4 if w.get("status") == ATIVO]
        por_desfecho = [w for w in linhas4 if w.get("satisfeito_por") == "desfecho"]
        p("Q4 marcar_fim → marcou=%s porque=%s | ativas=%d por_desfecho=%d"
          % (marcou, porque, len(ativas4), len(por_desfecho)))
        p("Q4 régua: nenhuma ativa e a do pós fechada por 'desfecho' → %s"
          % ("OK" if not ativas4 and por_desfecho else "⛔ FALHOU"))
        if ativas4 or not por_desfecho:
            resultado = 1
    except Exception as erro:  # noqa: BLE001
        p("⛔ o canário parou: %s: %s" % (type(erro).__name__, erro))
        resultado = 2
    finally:
        if limpar:
            # ⛔ Apaga SÓ o que criou, POR ID **e** por corretora. 🔴 §7: o
            #    backend usa service role e atravessa a RLS inteira; um id
            #    trocado numa edição apagaria linha de outra corretora.
            #
            # 🔴 [J-5] TRÊS TABELAS, E SÓ TRÊS — porque o canário não cria mais
            #    `work_runs`, `work_steps` nem `work_events`. A versão anterior
            #    tentava apagá-las e **crashava**: `work_events` é append-only
            #    (trigger `tg_work_events_append_only`), `work_runs` cascateia
            #    para ela, e apagar a conversa disparava `SET NULL` em
            #    `work_runs.company_id`, barrado por `tg_work_runs_company_imutavel`.
            #    O caminho certo não era forçar a limpeza: era **não criar** o
            #    que não se sabe recolher.
            if conversa_id:
                for w in esperas_da_conversa(conversa_id):
                    (sinc.table("work_waits").delete()
                     .eq("company_id", company_id).eq("id", str(w["id"])).execute())
            if episodio_id:
                (sinc.table("attendance_sessions").delete()
                 .eq("company_id", company_id).eq("id", episodio_id).execute())
            for cid in (conversa_id, conversa_controle_id):
                if cid:
                    (sinc.table("conversations").delete()
                     .eq("company_id", company_id).eq("id", cid).execute())

            restam_w = len(esperas_da_conversa(conversa_id))
            restam_e = len((sinc.table("attendance_sessions").select("id")
                            .eq("company_id", company_id)
                            .eq("id", episodio_id).execute()).data or []) if episodio_id else 0
            restam_c = 0
            for cid in (conversa_id, conversa_controle_id):
                if cid:
                    restam_c += len((sinc.table("conversations").select("id")
                                     .eq("company_id", company_id)
                                     .eq("id", cid).execute()).data or [])
            p("LIMPEZA — work_waits=%d · episódios=%d · conversas=%d (esperado 0/0/0)"
              % (restam_w, restam_e, restam_c))
            if restam_w or restam_e or restam_c:
                resultado = 1
    return resultado


def main() -> int:
    ap = argparse.ArgumentParser(description="O canário da SPEC-097.1")
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
