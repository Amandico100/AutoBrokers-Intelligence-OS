# -*- coding: utf-8 -*-
"""O canário vivo da SPEC-096 — o turno tipado, medido no produto de verdade.

```
--dry-run   (padrão) imprime o PLANO e não toca em nada.
--vivo      sobe o app FastAPI in-process e roda quatro turnos na Resulta:
            um feliz, um repetido, um abandonado e a LINHA DE CONTROLE.
            Ao fim apaga o que criou e prova que apagou.
```

## O que ele mede, e por que cada medida existe

```
Q1  "Responda apenas: OK" no modo PAINEL
    → TTFSE (1º evento), TTFT (1º delta), T_COMPLETE (turn.completed) e a
      ORDEM dos tipos. 📊 A régua vem do BLOCO 0.3 medido no backend
      IMPLANTADO em 04/09/2026: TTFT 1,13 s e `[DONE]` só em 8,71 s — os
      ~7,5 s de sobra eram o gatilho de memória segurando o stream aberto.
      Régua: TTFT ≤ 1,3 × 1,13 s  E  T_COMPLETE nitidamente < 8,7 s.

Q2  o MESMO `client_request_id`, de novo
    → o índice único parcial da migration A.1 decide: ou a segunda resposta é
      recusada pelo banco, ou ela grava e há duas. O canário DIZ qual foi.

Q3  o consumidor abandona no 5º evento
    → a task não é cancelada: a resposta INTEIRA tem de estar gravada com
      `status: complete` (A.4). É o defeito (x) do GATE ZERO, medido.

E.2 a LINHA DE CONTROLE: o MESMO POST, sem `X-Internal-Key`, com `userId` no
    corpo → tem de cair em modo WIDGET (o `userId` é descartado e as checagens
    de widget rodam). Sem esta linha, um Q1 verde não prova que a chave é o que
    decide — prova só que o caminho feliz funciona (CLAUDE.md §9.2).
```

⛔ Ele nunca imprime conteúdo de mensagem que não seja a do próprio canário, e
apaga SÓ as linhas cujo id ele mesmo criou.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# 🔴 ANTES de qualquer `import app.` — é no ato da publicação que a variável é
# lida, e um import anterior tornaria a ordem uma coincidência.
os.environ["AUTOBROKERS_CANARIO"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# 🔴 MEDIDO em 04/09/2026 (`select id from companies`), não lembrado.
RESULTA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"

#: 📊 BLOCO 0.3, backend implantado, 04/09/2026 22:40.
TTFT_DE_REFERENCIA_S = 1.13
DONE_DE_REFERENCIA_S = 8.71

PERGUNTA = "Responda apenas: OK"


def p(texto=""):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def plano():
    p("PLANO do canário 096 (nada foi executado — rode com `--vivo`):")
    p("  0. lê no banco: agente ativo da Resulta e um usuário `admin_company` dela")
    p("  1. cria a conversa canário (session_id novo, title 'canario:096') pelo")
    p("     MESMO caminho do BFF: insert em `conversations`")
    p("  2. sobe o app FastAPI in-process (httpx + ASGITransport) e faz POST")
    p("     /chat/stream em modo painel (X-Internal-Key do ambiente)")
    p("  3. Q1 '%s' → TTFSE, TTFT, T_COMPLETE e a ORDEM dos tipos" % PERGUNTA)
    p("  4. Q2 com o MESMO client_request_id → conta as respostas gravadas")
    p("  5. Q3 abandonando o consumo no 5º evento → espera e confere `complete`")
    p("  6. CONTROLE (E.2), duas linhas que CONSEGUEM falhar:")
    p("     (a) sem chave, companyId INEXISTENTE + agentId real da Resulta →")
    p("         o turno é servido para a corretora DO AGENTE (o corpo é ignorado,")
    p("         log `trust=widget_company_ignored`)")
    p("     (b) sem chave, userId qualquer → modo widget, userId descartado")
    p("         (resposta legada `{token}`, log `[STREAM] modo=widget`)")
    p("  7. apaga as mensagens e a conversa criadas, e prova count=0")
    p("")
    p("  Régua: TTFT ≤ %.2fs (1,3 × %.2f) e T_COMPLETE < %.2fs"
      % (TTFT_DE_REFERENCIA_S * 1.3, TTFT_DE_REFERENCIA_S, DONE_DE_REFERENCIA_S))


def chave_interna():
    from app.core import settings
    for candidata in (getattr(settings, "ADMIN_API_KEY", None),
                      getattr(settings, "BACKEND_INTERNAL_API_KEY", None),
                      os.getenv("ADMIN_API_KEY"), os.getenv("BACKEND_INTERNAL_API_KEY")):
        if candidata and str(candidata).strip():
            return str(candidata).strip()
    return None


def eventos_do_corpo(texto):
    """Quebra o corpo SSE em envelopes (e nas linhas legadas)."""
    saida = []
    for linha in texto.splitlines():
        if not linha.startswith("data: "):
            continue
        bruto = linha[6:].strip()
        if bruto == "[DONE]" or bruto.startswith("["):
            saida.append({"type": bruto})
            continue
        try:
            saida.append(json.loads(bruto))
        except Exception:  # noqa: BLE001
            saida.append({"type": "?"})
    return saida


async def vivo(company_id, limpar=True):
    import httpx

    from app.core.database import get_supabase_client

    db = get_supabase_client().client

    chave = chave_interna()
    if not chave:
        p("⛔ FALTOU: nenhuma chave interna no ambiente (ADMIN_API_KEY / "
          "BACKEND_INTERNAL_API_KEY). Sem ela não há modo painel.")
        return 2

    agentes = (db.table("agents").select("id, name")
               .eq("company_id", company_id).eq("is_active", True)
               .order("created_at").limit(1).execute()).data
    if not agentes:
        p("⛔ FALTOU: a corretora %s não tem agente ativo." % company_id[:8])
        return 2
    agent_id = agentes[0]["id"]

    # 🔴 A tabela é `users_v2`. 📊 `users` devolve PGRST205 ("could not find
    # the table in the schema cache") — o canário inteiro morria no passo 0.
    usuarios = (db.table("users_v2").select("id, role")
                .eq("company_id", company_id).limit(5).execute()).data or []
    escolhido = next((u for u in usuarios if u.get("role") == "admin_company"), None) or (usuarios[0] if usuarios else None)
    if not escolhido:
        p("⛔ FALTOU: nenhum usuário na corretora %s." % company_id[:8])
        return 2
    user_id = escolhido["id"]

    session_id = str(uuid.uuid4())
    conv = (db.table("conversations").insert({
        "company_id": company_id, "user_id": user_id, "session_id": session_id,
        "agent_id": agent_id, "channel": "web", "status": "open",
        "title": "canario:096", "unread_count": 0,
    }).execute()).data
    conversation_id = conv[0]["id"]
    p("conversa canário criada: %s (sessao %s…)" % (conversation_id[:8], session_id[:8]))

    from app.main import app

    transporte = httpx.ASGITransport(app=app)
    resultado = 0
    ids_das_mensagens = []

    try:
        async with httpx.AsyncClient(transport=transporte, base_url="http://canario",
                                     timeout=120.0) as cliente:

            def corpo(crid, com_user=True):
                dados = {
                    "chatInput": PERGUNTA,
                    "sessionId": session_id,
                    "companyId": company_id,
                    "agentId": agent_id,
                    "client_request_id": crid,
                    "assistantMessageId": str(uuid.uuid4()),
                }
                if com_user:
                    dados["userId"] = user_id
                return dados

            # ---------- Q1 ---------------------------------------------------
            crid1 = str(uuid.uuid4())
            d1 = corpo(crid1)
            ids_das_mensagens.append(d1["assistantMessageId"])
            comeco = time.monotonic()
            ttfse = ttft = None
            tipos = []
            async with cliente.stream("POST", "/chat/stream", json=d1,
                                      headers={"X-Internal-Key": chave}) as r:
                p("Q1 status HTTP: %s" % r.status_code)
                async for linha in r.aiter_lines():
                    if not linha.startswith("data: "):
                        continue
                    if ttfse is None:
                        ttfse = time.monotonic() - comeco
                    bruto = linha[6:].strip()
                    if bruto == "[DONE]":
                        tipos.append("[DONE]")
                        break
                    try:
                        ev = json.loads(bruto)
                    except Exception:  # noqa: BLE001
                        continue
                    tipos.append(ev.get("type", "?"))
                    if ev.get("type") == "assistant.content.delta" and ttft is None:
                        ttft = time.monotonic() - comeco
            total = time.monotonic() - comeco
            p("Q1 ORDEM: %s" % " → ".join(tipos))
            p("Q1 TTFSE=%.2fs  TTFT=%s  T_COMPLETE=%.2fs"
              % (ttfse or -1, ("%.2fs" % ttft) if ttft else "—", total))
            teto = TTFT_DE_REFERENCIA_S * 1.3
            p("Q1 régua: TTFT ≤ %.2fs → %s · T_COMPLETE < %.2fs → %s"
              % (teto, "OK" if (ttft or 99) <= teto else "ESTOUROU",
                 DONE_DE_REFERENCIA_S, "OK" if total < DONE_DE_REFERENCIA_S else "ESTOUROU"))

            # ---------- Q2: o mesmo client_request_id ------------------------
            d2 = corpo(crid1)
            ids_das_mensagens.append(d2["assistantMessageId"])
            r2 = await cliente.post("/chat/stream", json=d2, headers={"X-Internal-Key": chave})
            p("Q2 status HTTP: %s (mesmo client_request_id)" % r2.status_code)

            # ---------- Q3: o consumidor abandona ----------------------------
            crid3 = str(uuid.uuid4())
            d3 = corpo(crid3)
            ids_das_mensagens.append(d3["assistantMessageId"])
            vistos = 0
            async with cliente.stream("POST", "/chat/stream", json=d3,
                                      headers={"X-Internal-Key": chave}) as r3:
                async for linha in r3.aiter_lines():
                    if linha.startswith("data: "):
                        vistos += 1
                        if vistos >= 5:
                            break
            p("Q3 abandonado no 5º evento; esperando a task terminar…")
            import asyncio
            await asyncio.sleep(12)

            # ---------- CONTROLE (E.2) --------------------------------------
            # ⚠️ A primeira versão desta linha media "nenhum envelope tipado
            # saiu" — e isso é verdade em TODA resposta de widget, inclusive
            # numa em que o corpo mandasse na corretora. Um controle que não
            # consegue falhar não é controle (CLAUDE.md §9.3). As duas linhas
            # abaixo CONSEGUEM: cada uma tem um veredito que depende do
            # conserto.

            # (a) o corpo não escolhe a CORRETORA: `companyId` inexistente +
            #     `agentId` REAL da Resulta → o turno tem de ser servido para a
            #     Resulta (a dona do agente), não 404 nem a company do corpo.
            crid4 = str(uuid.uuid4())
            d4 = corpo(crid4)
            d4["companyId"] = str(uuid.uuid4())          # uma corretora que não existe
            ids_das_mensagens.append(d4["assistantMessageId"])
            r4 = await cliente.post("/chat/stream", json=d4)   # SEM a chave
            eventos = eventos_do_corpo(r4.text)
            formas = {("legado {token}" if "token" in e else e.get("type", "?")) for e in eventos}
            p("CONTROLE (a): companyId inexistente + agentId da Resulta → status=%s formas=%s"
              % (r4.status_code, sorted(formas)))
            p("CONTROLE (a): %s"
              % ("OK — o turno rodou na corretora DO AGENTE (o corpo foi ignorado)"
                 if r4.status_code == 200 and "legado {token}" in formas
                 else "⛔ o corpo escolheu a corretora (404/erro = a company do corpo foi usada)"))
            p("           procure no log: `trust=widget_company_ignored`")

            # (b) o corpo não escolhe a PESSOA: `userId` qualquer, sem chave →
            #     modo widget, `userId` descartado.
            crid5 = str(uuid.uuid4())
            d5 = corpo(crid5)
            d5["userId"] = str(uuid.uuid4())             # um usuário que não é dali
            ids_das_mensagens.append(d5["assistantMessageId"])
            r5 = await cliente.post("/chat/stream", json=d5)   # SEM a chave
            formas5 = {("legado {token}" if "token" in e else e.get("type", "?"))
                       for e in eventos_do_corpo(r5.text)}
            p("CONTROLE (b): userId estranho sem chave → status=%s formas=%s"
              % (r5.status_code, sorted(formas5)))
            p("CONTROLE (b): %s"
              % ("OK — modo widget (nenhum envelope tipado; userId descartado)"
                 if not any(str(f).startswith("turn.") for f in formas5)
                 else "⛔ SAIU ENVELOPE TIPADO SEM CHAVE"))
            p("           procure no log: `[STREAM] modo=widget`")

        # ---------- VERIFY ---------------------------------------------------
        gravadas = (db.table("messages")
                    .select("id, role, type, payload")
                    .eq("conversation_id", conversation_id).execute()).data or []
        p("")
        p("VERIFY — mensagens na conversa canário: %d" % len(gravadas))
        for m in gravadas:
            turno = ((m.get("payload") or {}).get("turn") or {})
            p("   %s · status=%s ttft=%s total=%s stages=%s crid=%s"
              % (m["role"], turno.get("status"), turno.get("ttft_ms"),
                 turno.get("total_ms"), turno.get("stages"),
                 str((m.get("payload") or {}).get("client_request_id"))[:8]))
        repetidas = [m for m in gravadas
                     if str((m.get("payload") or {}).get("client_request_id") or "").startswith(crid1[:8])]
        p("VERIFY Q2 — respostas com o MESMO client_request_id: %d %s"
          % (len(repetidas), "(o índice A.1 recusou a segunda)" if len(repetidas) == 1 else "(o banco aceitou as duas)"))

    finally:
        if limpar:
            db.table("messages").delete().eq("conversation_id", conversation_id).execute()
            db.table("conversations").delete().eq("id", conversation_id).execute()
            sobrando = (db.table("messages").select("id", count="exact")
                        .eq("conversation_id", conversation_id).execute())
            conv_sobrando = (db.table("conversations").select("id", count="exact")
                             .eq("id", conversation_id).execute())
            p("LIMPEZA — mensagens restantes=%s · conversas restantes=%s"
              % (sobrando.count, conv_sobrando.count))
    return resultado


def main():
    ap = argparse.ArgumentParser(description="O canário da SPEC-096")
    ap.add_argument("--vivo", action="store_true", help="executa de verdade")
    ap.add_argument("--dry-run", action="store_true", help="só imprime o plano (padrão)")
    ap.add_argument("--company", default=RESULTA)
    ap.add_argument("--sem-limpeza", action="store_true",
                    help="não apaga o que criou (para inspeção manual)")
    args = ap.parse_args()

    if not args.vivo:
        plano()
        return 0

    import asyncio
    return asyncio.run(vivo(args.company, limpar=not args.sem_limpeza))


if __name__ == "__main__":
    sys.exit(main())
