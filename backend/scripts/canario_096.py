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
    p("  4. Q2 MIMETIZA A TELA: mesmo client_request_id E mesmo assistantMessageId")
    p("     (R3: repetir a pergunta e nova TENTATIVA do mesmo turno) → tem de")
    p("     sobrar UMA resposta, com o conteudo da 2a e `attempt` somado")
    p("  5. Q3 abandonando o consumo no 5º evento → espera e confere `complete`")
    p("  6. CONTROLE (E.2), duas linhas que CONSEGUEM falhar:")
    p("     (a) sem chave, companyId INEXISTENTE + agentId real da Resulta →")
    p("         o turno é servido para a corretora DO AGENTE (o corpo é ignorado,")
    p("         log `trust=widget_company_ignored`)")
    p("     (b) sem chave, userId qualquer → modo widget, userId descartado")
    p("         (resposta legada `{token}`, log `[STREAM] modo=widget`)")
    p("  7. VERIFY procura as respostas pelos client_request_id em QUALQUER")
    p("     conversa (e avisa se o backend gravou noutra); imprime o `persisted`")
    p("     de cada turno; apaga por client_request_id + a conversa + a sessao,")
    p("     e prova count=0")
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


def _responde(host, porta, prazo=1.0):
    import socket
    try:
        with socket.create_connection((host, int(porta)), timeout=prazo):
            return True
    except Exception:  # noqa: BLE001
        return False


def ambiente_incompleto():
    """O que nao responde nesta maquina. Devolve a lista de ausentes.

    📊 05/09/2026, 1ª rodada --vivo: TTFT deu **607 s**. O log mostrou o
    download dos modelos do spacy (`pt_core_news_md`, `en_core_web_lg`) DENTRO
    do turno e retentativas de Redis e Qdrant que nao existem nesta maquina.
    Nada disso e defeito de produto — mas uma regua de tempo medida sobre
    isso nao mede o produto. Entao o canário diz isso ANTES, e a regua vira
    INFORMATIVA em vez de reprovar o que ela nao mediu.
    """
    from app.core import settings

    ausentes = []
    endereco = str(getattr(settings, "REDIS_URL", "") or "")
    if endereco:
        try:
            from urllib.parse import urlparse
            partes = urlparse(endereco)
            if not _responde(partes.hostname or "localhost", partes.port or 6379):
                ausentes.append("Redis (%s:%s)" % (partes.hostname, partes.port or 6379))
        except Exception:  # noqa: BLE001
            ausentes.append("Redis (endereco ilegivel)")
    qhost = str(getattr(settings, "QDRANT_HOST", "") or "localhost")
    qporta = getattr(settings, "QDRANT_PORT", 6333)
    if not _responde(qhost, qporta):
        ausentes.append("Qdrant (%s:%s)" % (qhost, qporta))
    return ausentes


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


def persisted_do_corpo(texto):
    """O `persisted` que o `turn.completed` daquele turno declarou."""
    for evento in eventos_do_corpo(texto):
        if evento.get("type") == "turn.completed":
            return (evento.get("payload") or {}).get("persisted")
    return None


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

    # 📊 05/09/2026, 1ª rodada --vivo: `AttributeError: 'State' object has no attribute
    # 'supabase_async'`. O ASGITransport NÃO dispara o lifespan do app, e é o lifespan
    # (`app/main.py:53-66`) que cria `app.state.supabase_async`. Entramos no ciclo de
    # vida à mão: é o MESMO startup de produção, sem servidor. (Uma saída limpa ao fim
    # não é necessária: o script é one-shot e o processo morre.)
    _ciclo = app.router.lifespan_context(app)
    await _ciclo.__aenter__()

    transporte = httpx.ASGITransport(app=app)
    resultado = 0
    ids_das_mensagens = []
    crid1 = crid3 = crid4 = crid5 = None

    try:
        async with httpx.AsyncClient(transport=transporte, base_url="http://canario",
                                     timeout=120.0) as cliente:

            def corpo(crid, com_user=True, amid=None):
                # 🔴 `amid` existe para o Q2 poder MIMETIZAR A TELA. R3: repetir
                # a pergunta e uma nova TENTATIVA do mesmo turno, e a tela reusa
                # o mesmo `assistantMessageId` e o mesmo `client_request_id`.
                # 📊 05/09/2026: com um id novo a cada POST, a 2ª tentativa
                # batia no indice (`409 Conflict`) e o canário "provava" um
                # defeito que era dele, nao do backend.
                dados = {
                    "chatInput": PERGUNTA,
                    "sessionId": session_id,
                    "companyId": company_id,
                    "agentId": agent_id,
                    "client_request_id": crid,
                    "assistantMessageId": amid or str(uuid.uuid4()),
                }
                if com_user:
                    dados["userId"] = user_id
                return dados

            faltando = ambiente_incompleto()
            if faltando:
                p("")
                p("⚠️  AMBIENTE INCOMPLETO: %s nao respondem nesta maquina."
                  % " e ".join(faltando))
                p("   A regua de tempo vira INFORMATIVA. 📊 05/09/2026: sem eles, o TTFT")
                p("   deu 607 s — com download de modelo do spacy e retentativa de conexao")
                p("   DENTRO do turno. Isso mede a maquina, nao o produto.")
                p("")

            # ---------- Q1 ---------------------------------------------------
            crid1 = str(uuid.uuid4())
            d1 = corpo(crid1)
            ids_das_mensagens.append(d1["assistantMessageId"])
            comeco = time.monotonic()
            ttfse = ttft = None
            persisted_visto = None
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
                    if ev.get("type") == "turn.completed":
                        persisted_visto = (ev.get("payload") or {}).get("persisted")
                    if ev.get("type") == "assistant.content.delta" and ttft is None:
                        ttft = time.monotonic() - comeco
            total = time.monotonic() - comeco
            p("Q1 ORDEM: %s" % " → ".join(tipos))
            p("Q1 turn.completed.persisted = %s" % persisted_visto)
            p("Q1 TTFSE=%.2fs  TTFT=%s  T_COMPLETE=%.2fs"
              % (ttfse or -1, ("%.2fs" % ttft) if ttft else "—", total))
            teto = TTFT_DE_REFERENCIA_S * 1.3
            if faltando:
                p("Q1 régua: INFORMATIVA (TTFT ≤ %.2fs · T_COMPLETE < %.2fs) — "
                  "este ambiente nao tem %s; o tempo medido aqui nao reprova nada."
                  % (teto, DONE_DE_REFERENCIA_S, " nem ".join(faltando)))
            else:
                p("Q1 régua: TTFT ≤ %.2fs → %s · T_COMPLETE < %.2fs → %s"
                  % (teto, "OK" if (ttft or 99) <= teto else "ESTOUROU",
                     DONE_DE_REFERENCIA_S, "OK" if total < DONE_DE_REFERENCIA_S else "ESTOUROU"))

            # ---------- Q2: a MESMA tentativa, de novo (como a tela faz) ------
            d2 = corpo(crid1, amid=d1["assistantMessageId"])
            r2 = await cliente.post("/chat/stream", json=d2, headers={"X-Internal-Key": chave})
            p("Q2 status HTTP: %s (mesmo client_request_id E mesmo assistantMessageId)"
              % r2.status_code)
            p("Q2 turn.completed.persisted = %s" % persisted_do_corpo(r2.text))

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
        # 🔴 O VERIFY procura pelos `client_request_id` do canario, EM QUALQUER
        # conversa — nao so na que ele criou.
        # 📊 05/09/2026: a rodada imprimiu "mensagens na conversa canario: 0"
        # enquanto o backend tinha gravado QUATRO respostas noutra conversa (ele
        # a criou sozinho, porque a do canario havia sumido no meio da rodada).
        # Um VERIFY que so olha a propria conversa mente nos dois sentidos: nao
        # ve o que foi gravado, e a limpeza deixa orfa a linha que ele nao viu.
        crids = [x for x in (crid1, crid3, crid4, crid5) if x]
        gravadas = []
        vistos_ids = set()
        for procurado in crids:
            achadas = (db.table("messages")
                       .select("id, role, type, conversation_id, payload")
                       .eq("payload->>client_request_id", procurado)
                       .execute()).data or []
            for linha in achadas:
                if linha["id"] not in vistos_ids:
                    vistos_ids.add(linha["id"])
                    gravadas.append(linha)
        p("")
        p("VERIFY — respostas do canario (por client_request_id, em qualquer conversa): %d"
          % len(gravadas))
        conversas_tocadas = {str(m.get("conversation_id")) for m in gravadas if m.get("conversation_id")}
        for outra in sorted(conversas_tocadas - {str(conversation_id)}):
            p("   ⚠️  o backend gravou na conversa %s, que NAO e a do canario" % outra[:8])
        for m in gravadas:
            turno = ((m.get("payload") or {}).get("turn") or {})
            p("   %s · status=%s attempt=%s ttft=%s total=%s stages=%s crid=%s"
              % (m["role"], turno.get("status"), turno.get("attempt"), turno.get("ttft_ms"),
                 turno.get("total_ms"), turno.get("stages"),
                 str((m.get("payload") or {}).get("client_request_id"))[:8]))
        repetidas = [m for m in gravadas
                     if str((m.get("payload") or {}).get("client_request_id") or "") == crid1]
        tentativa = ((repetidas[0].get("payload") or {}).get("turn") or {}).get("attempt") if repetidas else None
        p("VERIFY Q2 — respostas com o MESMO client_request_id: %d (attempt=%s) %s"
          % (len(repetidas), tentativa,
             "— UMA linha, com a resposta da 2a tentativa (A.1 + upsert)" if len(repetidas) == 1
             else "— ⛔ o banco aceitou mais de uma"))
        abandonado = [m for m in gravadas
                      if str((m.get("payload") or {}).get("client_request_id") or "") == crid3]
        p("VERIFY Q3 — o turno abandonado: %s"
          % (("gravado, status=%s (A.4: a task nao morreu com a conexao)"
              % (((abandonado[0].get("payload") or {}).get("turn") or {}).get("status")))
             if abandonado else "⛔ NAO gravado"))

    finally:
        if limpar:
            # ⛔ Apaga o que o canario criou — e SO isso: as linhas com os
            # `client_request_id` dele, as mensagens da conversa dele, e toda
            # conversa da sessao dele (inclusive a que o backend criou sozinho).
            for procurado in [x for x in (crid1, crid3, crid4, crid5) if x]:
                db.table("messages").delete().eq("payload->>client_request_id", procurado).execute()
            db.table("messages").delete().eq("conversation_id", conversation_id).execute()
            db.table("conversations").delete().eq("session_id", session_id).execute()

            restantes = 0
            for procurado in [x for x in (crid1, crid3, crid4, crid5) if x]:
                resposta = (db.table("messages").select("id", count="exact")
                            .eq("payload->>client_request_id", procurado).execute())
                restantes += (resposta.count or 0)
            sobrando = (db.table("messages").select("id", count="exact")
                        .eq("conversation_id", conversation_id).execute())
            conv_sobrando = (db.table("conversations").select("id", count="exact")
                             .eq("session_id", session_id).execute())
            p("LIMPEZA — por client_request_id restantes=%s · mensagens da conversa=%s "
              "· conversas da sessao=%s"
              % (restantes, sobrando.count, conv_sobrando.count))
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
