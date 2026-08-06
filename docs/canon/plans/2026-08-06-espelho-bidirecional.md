# Espelho bidirecional — plano de execução

> **Para quem executar:** use `superpowers:subagent-driven-development` ou
> `superpowers:executing-plans`. Os passos usam `- [ ]` para marcação.

**Objetivo:** a conversa que acontece no WhatsApp da corretora aparece no chat do
dashboard em tempo real, a corretora responde de lá como se fosse WhatsApp Web, e
quem responde primeiro — pessoa ou agente — silencia o outro **naquela conversa**,
sem desligar o agente nas demais.

**Arquitetura:** nada de motor novo. O que falta é **uma ponte**: hoje a mensagem
capturada morre em `attendance_transcripts` (o acervo do Observador) e nunca vira
`conversations` + `messages` (o chat). A ponte é uma função nova chamada de
dentro do `observer_tap`, no ponto onde ele já grava. Todo o resto — chat, envio,
assumir, devolver, pausa por conversa — **já existe e está em produção**.

**Pilha:** FastAPI + Supabase (backend) · Next.js App Router (dashboard) ·
Evolution GO (WhatsApp). Testes: Python solto em `backend/tests/`, sem pytest.

---

## 1. O que já existe (📊 auditado em 06/08/2026, não presumido)

| Peça | Onde | Estado |
|---|---|---|
| Captura ao vivo do WhatsApp | `observer_intake.observer_tap` → `attendance_capture.capture_client_message` | ✅ **funcionando** — 124 msgs/hora medidas |
| Chat com histórico | `conversations` + `messages` | ✅ existe |
| Tela de chat da corretora | `app/dashboard/atendimentos/conversas/` | ✅ existe |
| Enviar do dashboard → WhatsApp | `POST /api/dashboard/conversas/[id]` `action:'send'` → `/api/webhook/send-message` | ✅ existe |
| Assumir / devolver / encerrar | mesma rota, `action:'claim'` / `'release'` / `'close'` | ✅ existe |
| **Pausa da IA POR CONVERSA** | `conversations.status='HUMAN_REQUESTED'` + `claimed_by` | ✅ **existe** — é por linha de conversa, exatamente a regra 4 |
| Auto-claim ao enviar | `route.ts` `action:'send'` já marca `HUMAN_REQUESTED` | ✅ existe |
| Agente respeita a pausa | `chat.py:136,331` · `webhook.py:503` | ✅ existe |
| Vigia do handoff | `tasks/handoff_watchdog.py` | ✅ existe |
| Envio sai pelo número da corretora | `integration_service.get_whatsapp_integration(company, agent_id=None)` e 📊 as três linhas de observer têm `agent_id = null` | ✅ correto |

**Veredito: as seis regras do Founder são possíveis.** Nenhuma exige peça nova de
infraestrutura. O que falta são três costuras.

## 2. O que falta — o gap real, e só ele

1. **A conversa não nasce.** `observer_tap` consome o evento enquanto o agente
   está desligado (`observer_intake.py:597`), e é o pipeline consumido que criaria
   `conversations`. Sem conversa, não há o que mostrar no chat.
2. **A resposta pelo celular não entra no chat.** O `fromMe` é capturado no
   acervo (`webhook.py:1206`) mas não vira `messages`.
3. **A resposta pelo celular não pausa o agente.** Aquele bloco só roda
   `if not await attendance_agent_active(_company)` — ou seja, **só quando o
   agente já está desligado**, que é justamente quando não há nada a pausar.

## 3. Decisões de arquitetura, e por que

**A ponte é chamada de dentro do `observer_tap`, não de um laço novo.** Ali a
mensagem já está normalizada, com empresa, contraparte, direção e `message_id`.
Um segundo caminho lendo `attendance_transcripts` seria um motor paralelo
(CLAUDE.md §5) e chegaria sempre atrasado.

**A conversa nasce `status='open'`, não `HUMAN_REQUESTED'`.** `HUMAN_REQUESTED`
significa "uma pessoa pediu para assumir" e alimenta o vigia de handoff. Uma
conversa espelhada não pediu nada. Nascer `open` também é o que faz o dia de
ligar o agente funcionar sem migração: a conversa já existe e ele simplesmente
passa a responder.

**Criar a conversa NÃO faz o agente falar.** Quem faz o agente responder é o
pipeline do webhook, e o `observer_tap` continua consumindo o evento enquanto o
agente está desligado. A ponte grava e devolve; não altera o `consumed`.
Há teste para isso (Tarefa 8).

**Dedup por `message_id`.** A mensagem enviada pelo dashboard vai ao WhatsApp e
**volta** como `fromMe`. Sem dedup, cada resposta apareceria duas vezes no chat.

**A ponte usa a MESMA chave de conversa que o pipeline do agente.** 🔴 Este é o
ponto mais fácil de errar do plano inteiro, e a primeira versão dele errou.

📊 `webhook.get_or_create_conversation` procura por
`company_id` + `user_id` + `channel` + `agent_id IS NULL`, e monta
`session_id = f"whatsapp:{telefone}:{company_id}:default"` — determinístico.
📊 `agent_id = integration.get("agent_id")`, e as três linhas de observer em
produção têm `agent_id = null`.

Se a ponte procurasse por `user_phone` (o caminho óbvio), ela criaria uma
conversa que o pipeline **não encontraria** no dia de ligar o agente — e o mesmo
cliente apareceria em duas conversas, uma com o histórico do espelho e outra com
o do agente. O defeito só apareceria no dia mais caro possível: o do go-live.

Por isso a ponte resolve o usuário com a **mesma** `integration_service.get_or_create_user`
e busca pela **mesma** chave. Convergência provada por teste na Tarefa 2.

⚠️ **O que garante a convergência é o `user_id`, não o `session_id`.** A busca do
pipeline é por `company_id` + `user_id` + `channel` + `agent_id`; o `session_id`
é apenas gravado. Montá-lo igual é higiene — um `session_id` divergente na mesma
conversa confundiria quem for depurar —, mas quem impede a conversa duplicada é
usar a mesma resolução de usuário. Os dois testes existem, e é o do `user_id` que
não pode ser removido.

**Regra 2 (agente ligado, tudo continua espelhado) sai de graça, e isso foi
verificado:** 📊 `observer_intake.py:805-827` grava no acervo dentro de
`if is_observer:`, que **não depende** de o agente estar ligado — só o `consumed`
depende. Com o agente ligado, a ponte roda igual e o evento **segue** para o
pipeline. Nenhuma tarefa é necessária para essa regra além do ensaio do Bloco 3.

**Janela de 7 dias — na LISTA, não na gravação.** Decisão do Founder, 06/08.

A distinção importa e a primeira versão do plano a errou. Mensagem ao vivo tem
idade ~0: uma janela aplicada na gravação nunca barraria nada dela. O que a
janela precisa filtrar é **o que aparece na lista** de conversas.

Então são duas coisas:

- **Lista do chat: 7 dias.** `last_message_at > agora - 7d`. 📊 A AutoFleet tem
  681 contrapartes; sem isso a mesa de trabalho abre com conversa morta em cima
  da de hoje.
- **Gravação: janela larga (30 dias), e ela existe por outro motivo.** Não é
  para esconder conversa: é para o HISTORY_SYNC de um pareamento novo não
  despejar meses de histórico no chat de uma vez. Mensagem ao vivo passa sempre.

**E abrir uma conversa mostra o histórico INTEIRO dela.** A janela some ali —
`messages` não expira. Um sinistro que arrasta 45 dias continua legível do
começo quando o cliente volta.

**A memória do agente é outra coisa ainda, e já existe.** 📊
`graph.py:886` chama `build_memory_context_async(max_facts=10, max_summaries=3)`:
fatos do segurado (`user_memories`) e resumos de sessão (`session_summaries`),
carregados **por relevância e sem prazo de validade**. É isso que faz o agente
lembrar do sinistro de 45 dias — não a mensagem estar na tela. 📊 Hoje estão
vazias (1 resumo, 0 fatos) porque a captura estava morta e o agente nunca rodou;
elas se enchem sozinhas quando o Bloco 1 subir.

O acervo cru do Espelho tem `ATTENDANCE_RETENTION_DAYS = 90` dias
(`attendance_capture.py:337`) — e não precisa mudar: o que precisa durar mais que
90 dias é o fato destilado, e o fato não expira.

## 4. Restrições globais

- **O agente de atendimento permanece DESLIGADO** durante toda a execução.
  📊 Os quatro `agents.agent_role='attendance'` estão `is_active=false`. Nenhuma
  tarefa altera isso, e a Tarefa 8 prova que continuam.
- **O Observador continua mudo.** Nenhuma tarefa acrescenta caminho de envio ao
  `observer_intake` / `attendance_capture`. Há teste de ausência.
- **Nada existente pode quebrar.** Cada bloco termina com a bateria inteira verde
  (hoje **183**) e `npm run test:rotas-montam`.
- **Multi-tenant:** toda leitura e escrita filtra `company_id`. O backend usa
  service role — RLS sem filtro no código não protege nada (CLAUDE.md §7).
- **Sem segredo em log.** Telefone só mascarado (`numero_pareado.mascarar`).
- **Testes:** Python solto, docstring narrativa, helper `checar()`, `main()` → 0/1,
  sem pytest. Todo guarda com linha de CONTROLE (§9.3).
- **Nada de `git checkout` para desfazer experimento.** Backup por cópia.

## 5. Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `backend/app/services/atlas/espelho_chat.py` **(criar)** | A ponte. Decide (puro) se uma mensagem vira conversa e faz o upsert de `conversations` + `messages`. Único lugar que escreve o chat a partir da captura. |
| `backend/app/services/atlas/observer_intake.py` **(modificar)** | Chama a ponte depois de gravar no acervo. Não muda `consumed`. |
| `backend/app/api/webhook.py` **(modificar)** | O ramo `from_me` passa a espelhar no chat e a pausar a conversa — sempre, não só com agente desligado. |
| `backend/tests/test_o_espelho_vira_conversa.py` **(criar)** | Guarda a ponte e o silêncio. |
| `backend/tests/test_quem_fala_primeiro_cala_o_outro.py` **(criar)** | Guarda a pausa por conversa, nas duas direções. |
| `app/dashboard/atendimentos/conversas/ConversasClient.tsx` **(modificar)** | Rótulo de origem da mensagem (celular × dashboard × agente). |

---

# BLOCO 1 — A conversa aparece e a corretora responde

Entrega a **regra 1** por inteiro. Ao fim deste bloco a Regina vê no dashboard as
conversas que estão acontecendo no WhatsApp dela e pode responder de lá, com o
agente desligado e sem que ele faça nada.

### Tarefa 1: A decisão pura — esta mensagem vira conversa?

**Arquivos:**
- Criar: `backend/app/services/atlas/espelho_chat.py`
- Teste: `backend/tests/test_o_espelho_vira_conversa.py`

**Interfaces:**
- Produz: `def deve_espelhar(*, counterparty: str, texto: str, msg_type: str, e_grupo: bool, e_seguradora: bool, idade_horas: float, limite_horas: float = 720.0) -> bool`
- Produz: `JANELA_DA_LISTA_DIAS = 7`

- [ ] **Passo 1: escrever o teste que falha**

```python
def teste_o_que_vira_conversa_e_o_que_nao():
    print("\n[1] Nem toda mensagem capturada vira conversa no chat")
    EC = _carregar_espelho()

    checar(EC.deve_espelhar(counterparty="554799956540", texto="Bom dia",
                            msg_type="text", e_grupo=False, e_seguradora=False,
                            idade_horas=0.1),
           "cliente falando agora: vira conversa")

    # CONTROLE — sem estes, tudo viraria conversa e a tela ficaria inutilizável.
    checar(not EC.deve_espelhar(counterparty="5511999999999", texto="Bom dia",
                                msg_type="text", e_grupo=False, e_seguradora=True,
                                idade_horas=0.1),
           "CONTROLE — seguradora NAO vira conversa de atendimento")
    checar(not EC.deve_espelhar(counterparty="123@g.us", texto="oi",
                                msg_type="text", e_grupo=True, e_seguradora=False,
                                idade_horas=0.1),
           "CONTROLE — grupo NAO vira conversa")
    checar(not EC.deve_espelhar(counterparty="554799956540", texto="oi",
                                msg_type="text", e_grupo=False, e_seguradora=False,
                                idade_horas=5000.0),
           "CONTROLE — historico de meses nao entra de uma vez",
           "e o HISTORY_SYNC de um pareamento novo que esta janela contem")
    checar(EC.deve_espelhar(counterparty="554799956540", texto="oi",
                            msg_type="text", e_grupo=False, e_seguradora=False,
                            idade_horas=200.0),
           "conversa de 8 dias AINDA grava — a janela de 7 dias e da LISTA",
           "esconder na lista e diferente de nao gravar; abrir a conversa mostra tudo")
    checar(EC.deve_espelhar(counterparty="554799956540", texto="",
                            msg_type="audio", e_grupo=False, e_seguradora=False,
                            idade_horas=0.1),
           "audio sem texto AINDA vira conversa",
           "a atendente precisa ver que chegou algo, mesmo sem transcricao")
    checar(not EC.deve_espelhar(counterparty="", texto="oi", msg_type="text",
                                e_grupo=False, e_seguradora=False, idade_horas=0.1),
           "CONTROLE — sem contraparte nao ha conversa a criar")
```

- [ ] **Passo 2: rodar e confirmar que falha**

```
PYTHONIOENCODING=utf-8 python backend/tests/test_o_espelho_vira_conversa.py
```
Esperado: `ModuleNotFoundError` ou `AttributeError: deve_espelhar`.

- [ ] **Passo 3: implementar o mínimo**

```python
# Quantos dias de conversa aparecem NA LISTA do chat. Decisão do Founder, 06/08.
JANELA_DA_LISTA_DIAS = 7

# Até onde uma mensagem ainda merece entrar no chat. Larga de propósito: não é
# para esconder conversa (disso cuida a lista), é para o HISTORY_SYNC de um
# pareamento novo não despejar meses de histórico de uma vez só.
LIMITE_DE_RECENCIA_HORAS = 720.0  # 30 dias


def deve_espelhar(*, counterparty: str, texto: str, msg_type: str,
                  e_grupo: bool, e_seguradora: bool, idade_horas: float,
                  limite_horas: float = LIMITE_DE_RECENCIA_HORAS) -> bool:
    """Esta mensagem capturada merece uma conversa no chat da corretora? PURO.

    O chat da corretora é a mesa de trabalho dela, não o acervo. O acervo
    (`attendance_transcripts`) guarda TUDO — inclusive seguradora, grupo e
    conversa de três meses atrás. A mesa guarda o que está aberto agora.

    ⚠️ Esta janela NÃO é a que a atendente vê. Mensagem ao vivo tem idade ~0 e
    passa sempre. Quem esconde conversa velha da mesa de trabalho é a LISTA, que
    filtra `JANELA_DA_LISTA_DIAS`. Esta aqui existe para um caso só: o
    HISTORY_SYNC de um pareamento novo, que chega com meses de conversa de uma
    vez e entupiria o chat.

    E abrir uma conversa mostra o histórico INTEIRO — `messages` não expira. Um
    sinistro que arrasta 45 dias continua legível do começo.

    Áudio sem texto passa de propósito: a atendente precisa VER que chegou algo.
    Uma conversa que aparece vazia é melhor que uma que não aparece.
    """
    if not str(counterparty or "").strip():
        return False
    if e_grupo or e_seguradora:
        return False
    if idade_horas > float(limite_horas):
        return False
    return bool(str(texto or "").strip()) or msg_type in ("audio", "image", "document", "video")
```

- [ ] **Passo 4: rodar e confirmar que passa**

- [ ] **Passo 5: commit**

```bash
git add backend/app/services/atlas/espelho_chat.py backend/tests/test_o_espelho_vira_conversa.py
git commit -m "feat(espelho): a decisao pura de o que vira conversa no chat"
```

---

### Tarefa 2: A ponte — capturar vira conversa + mensagem

**Arquivos:**
- Modificar: `backend/app/services/atlas/espelho_chat.py`
- Teste: `backend/tests/test_o_espelho_vira_conversa.py`

**Interfaces:**
- Consome: `deve_espelhar` (Tarefa 1)
- Produz: `def session_id_do_chat(company_id: str, telefone: str) -> str`
- Produz: `async def espelhar_no_chat(*, company_id: str, counterparty: str, texto: str, msg_type: str, direcao: str, message_id: str, quando_iso: str, nome: str | None = None, db=None) -> str | None` — devolve o `conversation_id` ou `None`

A função de sessão, que precisa existir antes do resto:

```python
def session_id_do_chat(company_id: str, telefone: str) -> str:
    """A MESMA sessão que o pipeline do agente monta (`webhook.py:491`).

    📊 Lá: `f"whatsapp:{payload.phone}:{company_id}:{agent_suffix}"`, com
    `agent_suffix = "default"` quando a integração não tem agente vinculado — que
    é o caso das três linhas de observer em produção (`agent_id = null`).

    Só dígitos, porque o mesmo número chega ora `+55 (47) 9995-6540`, ora
    `554799956540`. Um hífen de diferença criaria uma segunda conversa para o
    mesmo cliente, e ninguém desconfiaria de um hífen.
    """
    digitos = "".join(ch for ch in str(telefone or "") if ch.isdigit())
    return f"whatsapp:{digitos}:{company_id}:default"
```

- [ ] **Passo 1: escrever o teste que falha**

```python
def teste_a_ponte_cria_conversa_e_mensagem():
    print("\n[2] A mensagem capturada vira conversa + mensagem no chat")
    import asyncio
    EC = _carregar_espelho()
    banco = BancoFalso()   # dublê definido no topo do arquivo de teste

    cid = asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="Bom dia",
        msg_type="text", direcao="in", message_id="MSG1",
        quando_iso=_agora_iso(), db=banco))
    checar(cid is not None, "criou a conversa")
    checar(len(banco.linhas("conversations")) == 1, "uma conversa")
    checar(len(banco.linhas("messages")) == 1, "uma mensagem")
    checar(banco.linhas("conversations")[0]["status"] == "open",
           "nasce 'open', nunca HUMAN_REQUESTED",
           "HUMAN_REQUESTED significa 'alguem pediu' e alimenta o vigia de handoff")
    checar(banco.linhas("conversations")[0]["channel"] == "whatsapp",
           "canal whatsapp — e o filtro que a tela usa")

    # A segunda mensagem da MESMA pessoa entra na MESMA conversa.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="tudo bem?",
        msg_type="text", direcao="in", message_id="MSG2",
        quando_iso=_agora_iso(), db=banco))
    checar(len(banco.linhas("conversations")) == 1, "nao duplicou a conversa")
    checar(len(banco.linhas("messages")) == 2, "duas mensagens na mesma conversa")

    # CONTROLE — o mesmo message_id NAO entra duas vezes. Sem isto, toda
    # resposta enviada pelo dashboard apareceria em dobro: ela vai ao WhatsApp
    # e VOLTA como fromMe.
    asyncio.run(EC.espelhar_no_chat(
        company_id="autofleet", counterparty="554799956540", texto="tudo bem?",
        msg_type="text", direcao="in", message_id="MSG2",
        quando_iso=_agora_iso(), db=banco))
    checar(len(banco.linhas("messages")) == 2,
           "CONTROLE — message_id repetido nao duplica")

    # CONTROLE — corretora diferente, conversa diferente. Multi-tenant (§7).
    asyncio.run(EC.espelhar_no_chat(
        company_id="resulta", counterparty="554799956540", texto="oi",
        msg_type="text", direcao="in", message_id="MSG3",
        quando_iso=_agora_iso(), db=banco))
    checar(len(banco.linhas("conversations")) == 2,
           "CONTROLE — mesmo telefone em outra corretora e outra conversa")


def teste_a_ponte_e_o_agente_acham_a_MESMA_conversa():
    print("\n[2b] A conversa do espelho é a MESMA que o agente vai usar")
    EC = _carregar_espelho()

    # 📊 `webhook.py:491` monta assim, e é determinístico.
    esperado = "whatsapp:554799956540:autofleet:default"
    checar(EC.session_id_do_chat("autofleet", "554799956540") == esperado,
           "o session_id é montado igual ao do pipeline do agente", esperado)
    checar(EC.session_id_do_chat("autofleet", "+55 (47) 9995-6540") == esperado,
           "e a formatação do telefone não muda o resultado",
           "senão o mesmo cliente teria duas conversas por causa de um hífen")

    # CONTROLE — este é o guarda que impede o defeito mais caro do plano.
    # Se a chave divergir, o espelho cria uma conversa e o agente cria OUTRA
    # para o mesmo cliente, e isso só apareceria no dia de ligar o agente.
    fonte = _fonte("backend/app/api/webhook.py")
    checar('f"whatsapp:{payload.phone}:{company_id}:{agent_suffix}"' in fonte,
           "CONTROLE — o pipeline ainda monta o session_id desta forma",
           "se esta linha mudar, a ponte precisa mudar junto — e este teste avisa")
    cmd = _comandos("backend/app/services/atlas/espelho_chat.py")
    checar("get_or_create_user" in cmd,
           "CONTROLE — a ponte resolve o usuário pela MESMA função do pipeline",
           "chave diferente = duas conversas para o mesmo cliente")
```

- [ ] **Passo 2: rodar e confirmar que falha**

- [ ] **Passo 3: implementar**

```python
async def espelhar_no_chat(*, company_id: str, counterparty: str, texto: str,
                           msg_type: str, direcao: str, message_id: str,
                           quando_iso: str, nome: Optional[str] = None,
                           db: Any = None) -> Optional[str]:
    """Põe a mensagem capturada no chat da corretora. Devolve o id da conversa.

    ⚠️ Esta função NÃO faz o agente falar. Quem faz o agente responder é o
    pipeline do webhook, e o `observer_tap` continua consumindo o evento
    enquanto o agente está desligado. Aqui só se grava o que aconteceu.

    Idempotente por `message_id`: a resposta enviada pelo dashboard vai ao
    WhatsApp e VOLTA como `fromMe`. Sem esta guarda, cada resposta apareceria
    duas vezes no chat da própria pessoa que a escreveu.
    """
    if db is None:
        from app.core.database import get_supabase_client
        db = get_supabase_client()
    cliente = getattr(db, "client", db)
    telefone = "".join(ch for ch in str(counterparty or "") if ch.isdigit())
    if not telefone or not company_id:
        return None

    def _trabalho() -> Optional[str]:
        # 1) já existe esta mensagem? (dedup)
        ja = (cliente.table("messages").select("id")
              .eq("payload->>wa_message_id", message_id).limit(1).execute().data or [])
        if ja:
            return None
        # 2) o MESMO usuário e a MESMA chave que o pipeline do agente usa.
        #    Ver §3: chave divergente = duas conversas para o mesmo cliente no
        #    dia de ligar o agente.
        from app.services.integration_service import integration_service

        # ⚠️ A ordem é (phone, company_id, name) — conferida na assinatura real
        # em `integration_service.py:370`. Trocar os dois primeiros criaria
        # usuários com o id da empresa como telefone, em silêncio.
        usuario = integration_service.get_or_create_user(
            phone=telefone, company_id=company_id, name=nome)
        if not usuario:
            return None
        linhas = (cliente.table("conversations").select("id, status")
                  .eq("company_id", company_id).eq("user_id", usuario)
                  .eq("channel", "whatsapp").is_("agent_id", "null")
                  .limit(1).execute().data or [])
        if linhas:
            conversa_id = linhas[0]["id"]
        else:
            nova = (cliente.table("conversations").insert({
                "company_id": company_id, "channel": "whatsapp",
                "user_id": usuario, "agent_id": None,
                "user_phone": telefone, "user_name": nome or f"WhatsApp {telefone[-4:]}",
                "session_id": session_id_do_chat(company_id, telefone),
                "status": "open", "status_color": "green",
                "agent_name": "Espelho", "unread_count": 0,
            }).execute().data or [])
            if not nova:
                return None
            conversa_id = nova[0]["id"]
        # 3) a mensagem
        cliente.table("messages").insert({
            "conversation_id": conversa_id,
            "role": "user" if direcao == "in" else "assistant",
            "content": texto or f"[{msg_type}]",
            "type": msg_type or "text", "topic": "whatsapp", "extension": "espelho",
            "payload": {"wa_message_id": message_id, "origem": "espelho",
                        "direcao": direcao},
        }).execute()
        cliente.table("conversations").update({
            "last_message_preview": (texto or f"[{msg_type}]")[:100],
            "last_message_at": quando_iso,
        }).eq("id", conversa_id).eq("company_id", company_id).execute()
        return conversa_id

    try:
        return await asyncio.to_thread(_trabalho)
    except Exception as erro:  # noqa: BLE001
        # O espelho é um bônus: falhar aqui não pode derrubar a CAPTURA, que é
        # a obrigação. O acervo já foi gravado antes desta chamada.
        logger.warning("[ESPELHO] não consegui espelhar no chat (%s)", type(erro).__name__)
        return None
```

- [ ] **Passo 4: rodar e confirmar que passa**
- [ ] **Passo 5: commit**

---

### Tarefa 3: Ligar a ponte ao Observador — sem quebrar o silêncio

**Arquivos:**
- Modificar: `backend/app/services/atlas/observer_intake.py` (dentro de `observer_tap`, logo após `stored = await capture_client_message(...)`, ~linha 817)
- Teste: `backend/tests/test_o_espelho_vira_conversa.py`

**Interfaces:**
- Consome: `espelhar_no_chat` (Tarefa 2)

- [ ] **Passo 1: escrever o teste que falha**

```python
def teste_a_ponte_esta_ligada_e_nao_muda_o_silencio():
    print("\n[3] Ligada ao Observador — e o silêncio intacto")
    fonte = _fonte("backend/app/services/atlas/observer_intake.py")
    cmd = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("espelhar_no_chat(" in cmd, "o tap chama a ponte")
    # CONTROLE — a linha que decide o silêncio NAO pode ter mudado. Ela é a
    # regra do Founder: o Observador não fala, e o agente só fala com o botão.
    checar('consumed = {"status": "observed"} if (is_observer and not _agente_ligado) else None' in cmd,
           "CONTROLE — a regra do silêncio esta intacta, palavra por palavra")
    # CONTROLE — e a ponte nao pode ter trazido caminho de ENVIO junto.
    for proibido in ("send_text(", "send_media(", "/send/", "send_message("):
        checar(proibido not in cmd,
               f"CONTROLE — o Observador continua sem como falar ({proibido})")
```

- [ ] **Passo 2: rodar e confirmar que falha**

- [ ] **Passo 3: implementar** — logo depois do `if stored:` existente:

```python
                        if stored:
                            # ESPELHO: a mesma mensagem que entrou no acervo
                            # entra no chat da corretora. Não altera `consumed`
                            # — o silêncio continua sendo decidido lá em cima,
                            # e esta linha não tem opinião sobre ele.
                            try:
                                from app.services.atlas.espelho_chat import espelhar_no_chat

                                await espelhar_no_chat(
                                    company_id=str(integration.get("company_id") or ""),
                                    counterparty=jid, texto=texto, msg_type=tipo,
                                    direcao="in", message_id=str(msg_id or ""),
                                    quando_iso=quando, nome=push_name)
                            except Exception:  # noqa: BLE001
                                logger.warning("[ESPELHO] chat não recebeu a mensagem")
                            return consumed
```

- [ ] **Passo 4: rodar e confirmar que passa**
- [ ] **Passo 5: rodar a bateria inteira** — `183 verdes` esperados
- [ ] **Passo 6: commit**

---

### Tarefa 4: A resposta pelo dashboard não aparece em dobro

**Arquivos:**
- Modificar: `app/api/dashboard/conversas/[id]/route.ts` (bloco `action === 'send'`, ~linha 152)
- Teste: `backend/tests/test_o_espelho_vira_conversa.py`

- [ ] **Passo 1: escrever o teste que falha**

```python
def teste_a_resposta_do_dashboard_nao_volta_em_dobro():
    print("\n[4] Resposta enviada do dashboard não aparece duas vezes")
    rota = _fonte("app/api/dashboard/conversas/[id]/route.ts")
    checar("wa_message_id" in rota,
           "o envio guarda o id do WhatsApp para o espelho reconhecer",
           "sem isto a resposta volta como fromMe e aparece de novo no chat")
    ec = _fonte("backend/app/services/atlas/espelho_chat.py")
    checar('payload->>wa_message_id' in ec,
           "CONTROLE — e a ponte procura por esse id antes de gravar")
```

- [ ] **Passo 2: rodar e confirmar que falha**

- [ ] **Passo 3: implementar** — no `action === 'send'`, guardar o id devolvido
      pelo backend no `payload` da mensagem já inserida:

```ts
        // O id que o WhatsApp deu a esta mensagem. Ela vai VOLTAR pelo webhook
        // como `fromMe`, e é por este campo que o espelho a reconhece e não a
        // grava de novo. Sem isto, cada resposta apareceria duas vezes no chat
        // de quem acabou de escrevê-la.
        const waId = (await res.json().catch(() => ({})))?.message_id ?? null;
        if (waId && newMessage?.id) {
          await supabase.from('messages')
            .update({ payload: { wa_message_id: waId, origem: 'dashboard' } })
            .eq('id', newMessage.id);
        }
```

- [ ] **Passo 4: `npx tsc --noEmit` limpo e teste passa**
- [ ] **Passo 5: commit**

---

### Tarefa 5: Prova por mutação e fechamento do Bloco 1

- [ ] **Passo 1:** quebrar `deve_espelhar` (sempre `True`) → o teste reprova
- [ ] **Passo 2:** remover o dedup por `message_id` → o teste reprova
- [ ] **Passo 3:** alterar a linha do silêncio no `observer_tap` → o teste reprova
- [ ] **Passo 4:** restaurar por CÓPIA (nunca `git checkout`) → verde
- [ ] **Passo 5:** bateria inteira + `npm run test:rotas-montam` + `npx tsc --noEmit`
- [ ] **Passo 6:** commit e push para a `main`

**Gate do Bloco 1:** abrir `Atendimentos → Conversas` na AutoFleet e ver as
conversas de hoje. Responder uma e conferir que chegou no WhatsApp. 📊 Conferir no
banco que `agents.is_active` continua `false` nos quatro agentes.

---

# BLOCO 2 — Quem fala primeiro cala o outro

Entrega as **regras 2, 3 e 4**. Ao fim deste bloco, a resposta da Regina pelo
celular aparece no chat e pausa o agente **naquela conversa**, e o agente segue
trabalhando nas demais.

### Tarefa 6: A mensagem da atendente pelo celular entra no chat

**Arquivos:**
- Modificar: `backend/app/api/webhook.py:1180-1215` (ramo `skip_reason == "from_me"`)
- Teste: `backend/tests/test_quem_fala_primeiro_cala_o_outro.py`

- [ ] **Passo 1: escrever o teste que falha**

```python
def teste_a_resposta_pelo_celular_aparece_no_chat():
    print("\n[1] A Regina responde pelo celular e a mensagem entra no chat")
    cmd = _comandos("backend/app/api/webhook.py")

    checar("espelhar_no_chat(" in cmd and 'direcao="out"' in cmd,
           "o ramo fromMe espelha a resposta da atendente no chat")
    # CONTROLE — e isso passa a valer SEMPRE, nao so com o agente desligado.
    # O bloco antigo rodava dentro de `if not await attendance_agent_active(...)`,
    # ou seja: so quando nao havia agente para pausar. Era o unico caso em que
    # a informacao nao servia para nada.
    trecho = cmd.split('skip_reason") == "from_me"')[1][:2500]
    checar("espelhar_no_chat(" in trecho,
           "e o espelho acontece dentro do ramo fromMe")
    checar(trecho.find("espelhar_no_chat(") < trecho.find("attendance_agent_active"),
           "CONTROLE — o espelho vem ANTES do teste de agente ligado",
           "depois dele, a resposta so entraria no chat quando nao ha agente")
```

- [ ] **Passo 2: rodar e confirmar que falha**

- [ ] **Passo 3: implementar** — no início do ramo `from_me`, antes de qualquer
      teste de agente ligado:

```python
            # A resposta da atendente pelo CELULAR entra no chat do dashboard.
            #
            # Sempre — e não só quando o agente está desligado, como era antes.
            # O bloco antigo rodava dentro de `if not attendance_agent_active`,
            # que é exatamente o caso em que a informação não serve para nada:
            # sem agente, não há o que pausar. Com agente ligado é que a
            # intervenção humana precisa ser vista e obedecida.
            try:
                from app.services.atlas.espelho_chat import espelhar_no_chat

                await espelhar_no_chat(
                    company_id=str(integration.get("company_id") or ""),
                    counterparty=str(normalized["phone"]),
                    texto=str(normalized.get("text") or ""),
                    msg_type="text", direcao="out",
                    message_id=str(normalized.get("message_id") or ""),
                    quando_iso=datetime.now(timezone.utc).isoformat())
            except Exception:  # noqa: BLE001
                logger.warning("[ESPELHO] resposta manual não entrou no chat")
```

- [ ] **Passo 4: rodar e confirmar que passa**
- [ ] **Passo 5: commit**

---

### Tarefa 7: A intervenção humana pausa o agente NAQUELA conversa

**Arquivos:**
- Modificar: `backend/app/services/atlas/espelho_chat.py`
- Modificar: `backend/app/api/webhook.py` (mesmo ramo da Tarefa 6)
- Teste: `backend/tests/test_quem_fala_primeiro_cala_o_outro.py`

**Interfaces:**
- Produz: `async def pausar_por_intervencao_humana(*, company_id: str, counterparty: str, quem: str = "atendente pelo celular", db=None) -> bool`

- [ ] **Passo 1: escrever o teste que falha**

```python
def teste_a_pausa_e_por_conversa_e_nao_global():
    print("\n[2] Pausar é POR CONVERSA — o agente segue nas outras")
    import asyncio
    EC = _carregar_espelho()
    banco = BancoFalso()
    banco.semear("conversations", [
        {"id": "c1", "company_id": "autofleet", "user_phone": "554799956540",
         "channel": "whatsapp", "status": "open", "claimed_by": None},
        {"id": "c2", "company_id": "autofleet", "user_phone": "554788887777",
         "channel": "whatsapp", "status": "open", "claimed_by": None},
    ])

    ok = asyncio.run(EC.pausar_por_intervencao_humana(
        company_id="autofleet", counterparty="554799956540", db=banco))
    checar(ok is True, "pausou a conversa em que a pessoa falou")
    checar(banco.por_id("conversations", "c1")["status"] == "HUMAN_REQUESTED",
           "aquela conversa fica com a pessoa")

    # CONTROLE — a que MAIS importa. Sem esta linha, uma intervencao numa
    # conversa calaria o agente em todas, e a regra 4 do Founder seria violada:
    # "ele apenas para aquela conversa e se aparecer outra, ele fala na outra".
    checar(banco.por_id("conversations", "c2")["status"] == "open",
           "CONTROLE — a OUTRA conversa segue com o agente",
           "o agente so para de vez pelo botao Ligar/Desligar agente")

    # CONTROLE — corretora diferente nao e tocada (§7).
    banco.semear("conversations", [
        {"id": "c3", "company_id": "resulta", "user_phone": "554799956540",
         "channel": "whatsapp", "status": "open", "claimed_by": None}])
    asyncio.run(EC.pausar_por_intervencao_humana(
        company_id="autofleet", counterparty="554799956540", db=banco))
    checar(banco.por_id("conversations", "c3")["status"] == "open",
           "CONTROLE — mesmo telefone noutra corretora nao e pausado")


def teste_o_agente_respeita_a_pausa():
    print("\n[3] E o agente OBEDECE a pausa")
    # O gate ja existe e este guarda impede que ele suma numa refatoracao.
    for arquivo in ("backend/app/api/chat.py", "backend/app/api/webhook.py"):
        checar('HUMAN_REQUESTED' in _comandos(arquivo),
               f"{arquivo} consulta o estado antes de o agente falar")
```

- [ ] **Passo 2: rodar e confirmar que falha**

- [ ] **Passo 3: implementar em `espelho_chat.py`**

```python
async def pausar_por_intervencao_humana(*, company_id: str, counterparty: str,
                                        quem: str = "atendente pelo celular",
                                        db: Any = None) -> bool:
    """Uma pessoa respondeu: o agente cala NESTA conversa, e só nesta.

    Decisão do Founder, 06/08/2026: *"ele precisa parar a conversar com aquele
    cliente naquele número, mas ele deve continuar ligado e fazendo o trabalho
    dele nas outras conversas... ele só para totalmente se o agente for
    desligado no botão do dashboard"*.

    Por isso o `UPDATE` é por LINHA de conversa e nunca toca `agents.is_active`.
    Duas pessoas respondendo o mesmo cliente é o defeito que isto evita; um
    agente mudo na corretora inteira seria um defeito maior.
    """
    if db is None:
        from app.core.database import get_supabase_client
        db = get_supabase_client()
    cliente = getattr(db, "client", db)
    telefone = "".join(ch for ch in str(counterparty or "") if ch.isdigit())
    if not telefone or not company_id:
        return False

    def _trabalho() -> bool:
        resposta = (cliente.table("conversations").update({
            "status": "HUMAN_REQUESTED", "claimed_by_name": quem,
            "claimed_at": _agora_iso(),
        }).eq("company_id", company_id).eq("channel", "whatsapp")
          .eq("user_phone", telefone).neq("status", "closed").execute())
        return bool(getattr(resposta, "data", None))

    try:
        return await asyncio.to_thread(_trabalho)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] não consegui pausar a conversa (%s)", type(erro).__name__)
        return False
```

- [ ] **Passo 4: chamar no `webhook.py`**, logo após o `espelhar_no_chat` da Tarefa 6:

```python
                await pausar_por_intervencao_humana(
                    company_id=str(integration.get("company_id") or ""),
                    counterparty=str(normalized["phone"]))
```

- [ ] **Passo 5: rodar e confirmar que passa**
- [ ] **Passo 6: commit**

---

### Tarefa 8: Os guardas do que NÃO pode mudar

**Arquivos:**
- Teste: `backend/tests/test_quem_fala_primeiro_cala_o_outro.py`

- [ ] **Passo 1: escrever os guardas**

```python
def teste_nada_disto_liga_agente_nenhum():
    print("\n[4] Nenhuma peça nova liga agente nenhum")
    for arquivo in ("backend/app/services/atlas/espelho_chat.py",
                    "backend/app/services/atlas/observer_intake.py"):
        cmd = _comandos(arquivo)
        checar('"is_active": True' not in cmd and "'is_active': True" not in cmd,
               f"{arquivo} nunca liga um agente")
        checar('table("agents")' not in cmd,
               f"CONTROLE — {arquivo} nao escreve na tabela de agentes")

    # E o Observador continua sem boca.
    cmd = _comandos("backend/app/services/atlas/espelho_chat.py")
    for proibido in ("send_text(", "send_media(", "/send/", "send_message("):
        checar(proibido not in cmd,
               f"CONTROLE — a ponte nao tem caminho de envio ({proibido})")
```

- [ ] **Passo 2: rodar — deve passar de primeira** (é um guarda de ausência)
- [ ] **Passo 3: prova por mutação** — inserir `table("agents")` na ponte e
      confirmar que o teste reprova; restaurar por cópia
- [ ] **Passo 4: bateria inteira + rotas + tsc**
- [ ] **Passo 5: commit e push**

**Gate do Bloco 2:** com o agente **ainda desligado**, responder pelo celular da
Regina e ver a mensagem aparecer no chat. 📊 Conferir no banco que a conversa
daquele cliente virou `HUMAN_REQUESTED` e que **as outras continuam `open`**.

---

# BLOCO 3 — O dia de ligar o agente (só quando o Founder mandar)

Não é código novo: é o **ensaio** da regra 2, e ele só roda quando o Founder
autorizar ligar o agente em uma corretora.

### Tarefa 9: Ensaio com o agente ligado

- [ ] **Passo 1:** ligar o agente de UMA corretora pelo botão do dashboard
- [ ] **Passo 2:** cliente manda mensagem → o agente responde
- [ ] **Passo 3:** 📊 conferir que a mensagem do cliente E a resposta do agente
      aparecem no chat e no WhatsApp da Regina
- [ ] **Passo 4:** a Regina responde pelo celular no meio → 📊 conferir que a
      conversa virou `HUMAN_REQUESTED` e o agente parou **nela**
- [ ] **Passo 5:** outro cliente manda mensagem → 📊 conferir que o agente
      **responde normalmente** nessa outra
- [ ] **Passo 6:** desligar o agente pelo botão → 📊 conferir que ele para em todas
- [ ] **Passo 7:** registrar as seis medições no relatório da SPEC

---

## 6. O que este plano NÃO faz, e por quê

- **Não liga agente nenhum.** Restrição global; a Tarefa 8 prova.
- **Não mexe no Observador além da chamada da ponte.** A regra do silêncio é
  verificada palavra por palavra na Tarefa 3.
- **Não traz meses de histórico para o chat de uma vez.** A lista mostra 7 dias
  (decisão do Founder) e a gravação aceita até 30. Abrir uma conversa mostra o
  histórico inteiro dela — a janela é da lista, não do conteúdo.
- **Não mexe na memória de longo prazo do agente.** Ela já existe, já é
  consultada por relevância e não expira. Ver §3.
- **Não mexe em mídia no chat.** Áudio e imagem aparecem como `[audio]` /
  `[imagem]` — a mensagem existe e é visível. Reproduzir mídia no chat é
  trabalho próprio: registrado em `PENDENCIAS.md` P-119.
- **Não toca no patch 0007 nem no Evolution Go.** Decisão do Founder: guardado.

## 7. Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Volume: 124 msgs/h viram muitas conversas | Janela de 72 h + `limit 200` que a rota já tem. Medir na primeira hora após o Bloco 1. |
| Resposta em dobro no chat | Dedup por `message_id` (Tarefa 2) + o id gravado no envio (Tarefa 4). Ambos com CONTROLE. |
| A ponte falhar e derrubar a captura | A ponte roda **depois** de o acervo ser gravado e tem `try/except` próprio. Falhar ali não perde conversa. |
| Duas pessoas respondendo | `claimed_by` já existente + pausa por conversa (Tarefa 7). |
| `messages.topic`/`extension` são NOT NULL | Valores fixos `"whatsapp"` / `"espelho"` na Tarefa 2. |
