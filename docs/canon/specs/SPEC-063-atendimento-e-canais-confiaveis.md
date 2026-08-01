---
> **Status:** canônica · pronta para execução
> **Versão:** 1.0 · **Criada em:** 01/08/2026
> **Autoridade superior:** CLAUDE.md · SPEC-052 · SPEC-053 · SPEC-055 · SPEC-056
> **Origem:** CA-020 (parcial), auditoria de atendimento ponta a ponta de 31/07,
> auditoria de canais de 31/07, e a confirmação de 01/08 de que a API da InfoCap
> responde 500
> **Branch:** `feat/spec063-atendimento-canais`
---

# SPEC-063 — Atendimento e Canais Confiáveis

> **A frase que resume:** hoje, se o agente de atendimento for ligado, quem
> responde o segurado é o copiloto interno do corretor — com um prompt que manda
> entregar CPF sem mascarar. Esta SPEC existe para que ligar o agente seja um
> lançamento, e não um incidente.

---

## 1. Por que esta SPEC existe

Três auditorias independentes, em 31/07/2026, encontraram **doze bloqueios** no
caminho do atendimento. Cinco são P0. Nenhum foi inferido — todos têm arquivo,
linha e dado de banco.

Em 01/08 acrescentou-se um décimo terceiro, de terceiro: **a API da InfoCap
responde HTTP 500 para as duas corretoras**, o que significa que o agente não
consegue consultar apólice nenhuma. Isso não é resolvido aqui — é registrado,
e o sistema passa a falhar de forma honesta em vez de silenciosa.

### 1.1 O que esta SPEC entrega

Ao final, o agente de atendimento **pode ser ligado** na Resulta e na AutoFleet:

```
sem risco de vazamento de dado de segurado
sem prometer o que não consegue cumprir
sem queimar o número de WhatsApp da corretora
sem misturar conversa de duas corretoras
com o humano sendo avisado de verdade quando é chamado
com o ciclo de acionamento fechando: aciona → avisa → acompanha → confirma
```

### 1.2 O que esta SPEC NÃO faz

| Fora do escopo | Onde vai |
|---|---|
| API oficial da Meta, e-mail transacional, proxy | SPEC-069 |
| Reorganização de Auxiliares, Rotinas e menu | SPEC-064 |
| Leitura agregada da carteira, detectores de dinheiro | SPEC-065 |
| Ingestão de SUSEP e condições gerais | SPEC-066 |
| Middleware `/api/**` (CA-020) | SPEC-068 |
| Consertar a API da InfoCap | terceiro — ação do Founder |

---

## 2. Estado factual antes da execução

Medido em 31/07 e 01/08/2026, banco `dcajcvlzcjbmyapmklil`.

```
agentes de atendimento .................... 3 (Saionara, Maria Regina, JOANA)
todos com is_active ....................... FALSE
tools_config dos três ..................... {} (vazio)
integrações WhatsApp ativas ............... só purpose='observer'
conexões InfoCap com last_used_at ......... 0 (nenhuma jamais usada)
corredores implementados .................. 11 (1 residencial + 10 auto)
playbooks de conduta ...................... 16, nenhum chega ao prompt
varreduras de portal em needs_human ....... 34 contra 18 concluídas
transcrições capturadas ................... 69.150
```

**O observador funciona.** É o único subsistema de atendimento que trabalha hoje.

---

## 3. Ordem de execução dos blocos

```
A → B → H → C → D → E → F → G
```

A precede tudo porque é o P0. H (higiene de plataforma) vem cedo porque o
`time.sleep` bloqueante e o buffer sem tenant afetam todos os blocos seguintes.

---

# BLOCO A — Quem atende é quem deve atender

**Grau: P0.** É o bloco que impede o vazamento.

## A.1 O defeito

`backend/app/services/whatsapp/pairing_orchestrator.py:493`

```python
"agent_id": None if purpose == "observer" else None,
```

O ternário devolve `None` nos dois ramos. **Toda integração nasce sem agente
vinculado**, inclusive as de `purpose='attendance'`.

Sem `agent_id`, `backend/app/services/langchain_service.py:188-217` faz:

```python
.eq("is_active", True).order("created_at").limit(1)
```

**Devolve o agente ativo mais antigo da corretora.**

## A.2 A prova

| Corretora | Agente CORE | Agente atendimento | Quem responde |
|---|---|---|---|
| Resulta | 21/06 **00:36** · ATIVO | 21/06 04:45 · desligado | **CORE** |
| Amandus | 05/06 **17:16** · ATIVO | 12/06 23:32 · desligado | **CORE** |
| AutoFleet | 21/07 18:18:05.395942 | **idêntico ao milissegundo** | **sorteio** |

E `backend/app/core/prompts.py:34`, no prompt do CORE:

> *"Esta é uma conversa INTERNA com o DONO da corretora... **É PROIBIDO recusar
> dado alegando 'privacidade', 'LGPD'**... repasse-o por completo (ex.: o CPF do
> segurado, **sem mascarar**)."*

**O segurado conversaria com um agente que se acha em reunião interna com o dono
da corretora.**

## A.3 A correção

**A.3.1 — Resolver por papel, não por antiguidade.**

Em `backend/app/api/webhook.py:286`, quando `integration.get("agent_id")` for
nulo, resolver o agente com `agent_role='attendance'` **da mesma corretora**.
O padrão já existe em `backend/app/services/whatsapp/whatsapp_channel.py:623-652`
— reusar, não reescrever.

**A.3.2 — Matar o ternário.**

`pairing_orchestrator.py:493` passa a resolver o agente de atendimento quando
`purpose='attendance'`, e `None` só quando `purpose='observer'`.

**A.3.3 — Nunca sobrescrever vínculo existente.**

`pairing_orchestrator.py:497-503` faz `update(record)` em linha existente.
Re-parear a integração de atendimento da Resulta **zeraria** o `agent_id` que ela
tem hoje. O `update` passa a preservar `agent_id` quando o valor novo é nulo.

**A.3.4 — Silêncio por omissão.**

`backend/app/services/atlas/attendance_capture.py:284`:

```python
bool(rows) and ... is False
```

Corretora **sem** linha de agente `attendance` devolve `False` — ou seja, **não
entra em modo observação** e cai no fluxo de IA. Inverter: **ausência de agente
provisionado = silêncio.** A função correta (`attendance_agent_active`, `:228`)
já existe e não é usada aqui.

**A.3.5 — Recusa explícita.**

Se, depois de tudo, o agente resolvido não for `agent_role='attendance'`, o
sistema **não responde** e registra `agent_role_mismatch`. Fail-closed.

## A.4 Testes

`backend/tests/test_quem_atende_o_segurado.py`

| # | Prova |
|---|---|
| A1 | integração sem `agent_id` → resolve o agente `attendance`, nunca o CORE |
| A2 | corretora com CORE mais antigo e ATIVO → ainda assim escolhe o `attendance` |
| A3 | corretora sem agente `attendance` → devolve silêncio, não escolhe outro |
| A4 | `update` de integração com `agent_id` nulo → preserva o vínculo existente |
| A5 | agente resolvido com papel errado → recusa, e o motivo é registrado |
| A6 | o ternário morto não existe mais no arquivo |

## A.5 Verificação

```sql
select c.company_name, i.purpose, i.is_active,
       a.name, a.agent_role
from integrations i
join companies c on c.id = i.company_id
left join agents a on a.id = i.agent_id
where i.provider = 'evolution-go' and i.is_active;
```

**Verde quando:** toda integração `purpose='attendance'` ativa tem `agent_id`
apontando para um agente `agent_role='attendance'` da mesma corretora.

---

# BLOCO B — O handoff que funciona de verdade

**Grau: P0.** Sem ele, o agente promete humano e não entrega.

## B.1 Os quatro defeitos

**B.1.1 — A ferramenta não está anexada.**

`backend/app/agents/graph.py:245-257` só anexa `HumanHandoffTool` se
`tools_config["human_handoff"]["enabled"] == true`
(`backend/app/services/tool_authority.py:54-57`).

**Dado:** `agents.tools_config` = `{}` nos três agentes de atendimento.

E `backend/app/core/prompts.py:120-121` **manda** o agente chamar humano.
**Ele vai dizer que chamou e não vai chamar.**

**B.1.2 — Ninguém é avisado.**

`backend/app/agents/tools/human_handoff.py:87-99` faz **um único efeito**:

```sql
UPDATE conversations SET status='HUMAN_REQUESTED'
```

Zero import de envio. **O humano só descobre olhando a tela.**

**B.1.3 — A tela e o backend leem tabelas diferentes.**

```
backend lê ..... companies.acionamento_profile.suporte_humano_whatsapp
                 (dispatch_router.py:216-242)
UI grava em .... human_support_destinations
                 (HumanSupportSettingsClient.tsx:97)
```

`human_support_destinations` **não aparece uma única vez** em `backend/app/`.

**Prova:** a Amandus cadastrou pela tela → o dossiê nunca chega. Resulta e
AutoFleet funcionam porque o campo certo foi preenchido por SQL manual.

**B.1.4 — Duas corretoras, um grupo só.**

Resulta e AutoFleet apontam para **o mesmo grupo** de suporte. Dossiê com dado de
segurado da Resulta cai no mesmo lugar que o da AutoFleet.

## B.2 A correção

**B.2.1** — Ligar `human_handoff` no `tools_config` dos três agentes, via
migration idempotente. E fazer o `graph.py` **falhar alto** se o prompt promete
humano e a ferramenta não está anexada — hoje falha em silêncio.

**B.2.2** — A ferramenta passa a **notificar**. Reusa o caminho de envio que o
`dispatch_router` já usa (`dispatch_router.py:544-554`); não cria caminho novo.

**B.2.3** — O backend passa a ler `human_support_destinations` — a tabela que a
UI escreve —, com `acionamento_profile` como fallback durante a transição.
Migration de backfill copia o que existe hoje para a tabela nova.

**B.2.4** — **Uma corretora, um destino.** Constraint no banco e teste de
isolamento com duas corretoras reais (CLAUDE.md §7).

**B.2.5 — O dossiê.** O handoff de atendimento passa a montar o mesmo pacote que
o corredor já monta (`insurer_dispatch_service.py:509-548`): quem é o cliente, o
que ele pediu, o que já foi capturado, **as últimas 6 mensagens**, e o aviso de
que ele já foi informado de que a equipe vai assumir.

**B.2.6 — A volta.** `claimed_at` é gravado
(`20260704_01_spec017_conversations_claim.sql:12-15`) e **nunca lido**. Passa a
existir prazo: conversa parada em `HUMAN_REQUESTED` além do limite volta para a
IA, com registro e aviso.

## B.3 Testes

`backend/tests/test_handoff_chega_em_alguem.py`

| # | Prova |
|---|---|
| B1 | a ferramenta está anexada aos três agentes |
| B2 | chamar humano dispara envio, não só `UPDATE` |
| B3 | o destino lido é o que a UI grava |
| B4 | duas corretoras nunca compartilham destino |
| B5 | o dossiê tem os campos obrigatórios e as últimas mensagens |
| B6 | conversa parada além do prazo volta para a IA |
| B7 | prompt promete humano **e** a ferramenta existe — se não, o teste quebra |

---

# BLOCO H — Higiene de plataforma

**Executado cedo porque afeta todos os blocos seguintes.**

## H.1 O `time.sleep` bloqueante — P1

`backend/app/services/whatsapp/whatsapp_service.py:56`

```python
time.sleep(0.7)   # entre balões
time.sleep(1.2)   # no retry (:63)
```

Chamado **sem `to_thread`** de dentro de função async
(`backend/app/api/webhook.py:681`). Resposta de 4 balões **congela o processo
inteiro por ~2,1 segundos**.

**Correção:** `await asyncio.sleep`, ou `to_thread` se a função tiver de
continuar síncrona.

**Teste:** medir que duas respostas simultâneas de corretoras diferentes não se
bloqueiam.

## H.2 O buffer sem tenant — P0 cross-tenant

`backend/app/services/message_buffer_service.py:36-38`

```python
chave = f"whatsapp_buffer:{phone}"   # só o telefone
```

E `add_message:60-62` faz `data["messages"].append(...)` mas **sobrescreve**
`data["payload"]`.

**Consequência:** o mesmo cliente falando com duas corretoras dentro da janela de
debounce tem as mensagens de A somadas ao combinado, e o `payload` — que carrega
`_integration_id` — vira o de B.

**Correção:** chave passa a incluir a integração. E `payload` deixa de ser
sobrescrito — vira lista, ou o buffer é fatiado por integração.

**Teste:** dois clientes com o mesmo número em corretoras diferentes → dois
buffers, dois payloads, zero mistura.

## H.3 As variáveis que ninguém audita

Nenhuma destas está em `backend/.env.example`:

```
ATTENDANT_INBOUND_ALLOWLIST     se preenchida, o agente ignora todo mundo fora
INSURER_DISPATCH_LIVE           sem ela, acionamento é simulação
DISPATCH_FINALIZE_MODE          test = executa e cancela antes de abrir
AUTHORITY_STRICT_MODE
TOOL_GATEWAY_MODE
WORK_RUNS_ROUTINE_BRIDGE
```

**Correção:** todas entram no `.env.example` com comentário do que fazem, e o
`/health` passa a reportar **o modo de cada uma** — nunca o valor de segredo,
só o modo.

## H.4 A imagem do Evolution Go

Confirmar que a versão corrigida está no ar, e **travar isso como teste**:

```
GET /server/ok  →  version deve conter 'autobrokers'
```

Se responder a versão upstream, o vazamento de pool volta, e parear uma corretora
derruba as outras.

---

# BLOCO C — O governador de envio

**Peça nova. Não existe hoje, e é o que impede queimar o número.**

## C.1 O defeito

Varredura de `backend/app/services/whatsapp/` e `platform_outbound.py`:
**não existe limitação de taxa em lugar nenhum.**

`backend/app/services/billing_collection.py:520` percorre **até 50
destinatários sem nenhuma pausa**, mandando **duas** mensagens cada — texto e
PDF do boleto.

```
50 cobranças = 100 mensagens em rajada
```

**É esse o comportamento que queima número.** E o único espaçamento existente é
`time.sleep(0.7)` entre balões da mesma resposta — que não é limitação de taxa, é
humanização.

## C.2 O desenho

Um **governador** único, no caminho de saída, que toda mensagem fria atravessa.

### C.2.1 Quem passa por ele

```
mensagem FRIA .......... para quem não escreveu antes → PASSA
                         (cobrança, campanha, aviso proativo)
resposta em conversa ... dentro de conversa aberta → NÃO PASSA
                         (atendimento reativo é a zona segura)
```

### C.2.2 Os parâmetros

Configuráveis por corretora, com estes padrões:

| Parâmetro | Padrão | Razão |
|---|---|---|
| intervalo entre destinatários | **4 a 8 minutos, aleatório** | com 3 a 5 boletos/dia, folgado. Intervalo fixo é assinatura de robô |
| nunca redondo | segundos sempre variáveis | `4:35`, `6:08`, nunca `5:00` |
| teto por hora | 12 | |
| teto por dia, número novo | 20 | conta com menos de 30 dias |
| teto por dia, número maduro | 200 | |
| janela | 08:00 – 20:00 | fuso da corretora |
| domingo | bloqueado para envio frio | |

### C.2.3 A fila

**Persistente e retomável.** Se o processo cair no meio de uma varredura de
cobrança, o que faltou continua depois — não recomeça, não duplica.

Reusa `work_runs` e a fila que já existe (SPEC-055). **Não cria fila nova.**

### C.2.4 O registro

Toda saída fria grava: **para quem, quando, por qual número, com qual intervalo,
qual o resultado.** Sem isso não há como investigar um bloqueio depois.

Nunca grava o conteúdo da mensagem em claro se ele contiver dado do segurado —
usa o mesmo `templatize` do resto do sistema.

### C.2.5 A parada de emergência

Um interruptor por corretora que **para todo envio frio imediatamente**, sem
derrubar o atendimento reativo. Acessível no dashboard e no admin.

## C.3 Testes

`backend/tests/test_governador_de_envio.py`

| # | Prova |
|---|---|
| C1 | 5 destinatários → 4 intervalos, todos entre 4 e 8 minutos |
| C2 | nenhum intervalo é redondo |
| C3 | dois intervalos consecutivos nunca são iguais |
| C4 | teto diário respeitado; o excedente fica na fila, não é descartado |
| C5 | fora da janela → não envia, agenda para a abertura |
| C6 | domingo → não envia frio |
| C7 | resposta dentro de conversa aberta **não** passa pelo governador |
| C8 | processo cai no meio → retoma sem duplicar e sem pular |
| C9 | parada de emergência interrompe frio e preserva reativo |
| C10 | toda saída fria deixa registro com os cinco campos |

---

# BLOCO D — O segundo número

## D.1 O problema

Cobrança e atendimento saem hoje pelo mesmo canal — e pior: **podem sair pelo
`observer`**, que é o celular espelhado do corretor.

`backend/app/services/billing_collection.py:403-414`

```python
rank = {"auxiliary": 0, "attendance": 1}
rows.sort(key=lambda r: rank.get(str(r.get("purpose") or ""), 2))
return rows[0] if rows else None
```

`observer` recebe prioridade 2 e **ainda assim é devolvido se for a única ativa**.
Hoje, na Resulta e na AutoFleet, **as únicas integrações ativas são `observer`**.

Mesmo padrão em `backend/app/services/routine_engine.py:196-198`.

## D.2 A correção

**D.2.1 — A guarda dura.**

`observer` **nunca** pode ser canal de saída. Não é prioridade baixa: é proibição.
Se não houver canal apropriado, a operação **falha com motivo claro** — não cai no
espelhado.

**D.2.2 — O card de pareamento, com três posições.**

```
[ conectado ]  WhatsApp de Atendimento     o segurado escreve aqui
[ conectar  ]  WhatsApp de Cobrança        nós escrevemos daqui
[ em breve  ]  WhatsApp Oficial (Meta)     SPEC-069
```

Cada posição grava `purpose` correto: `attendance`, `auxiliary`, e a terceira
fica visível e desabilitada, com a explicação do que virá.

**D.2.3 — Fallback consciente.**

Se a corretora não tiver número de cobrança, o sistema **pergunta** antes de usar
o de atendimento — e registra a escolha. Nunca decide sozinho.

## D.3 Testes

| # | Prova |
|---|---|
| D1 | `observer` nunca é escolhido como saída, nem como último recurso |
| D2 | cobrança sem número próprio → falha explicativa, não usa o espelhado |
| D3 | pareamento de cobrança grava `purpose='auxiliary'` |
| D4 | a posição Meta existe, está visível e desabilitada |

---

# BLOCO E — Cobrança que conversa

## E.1 O buraco

O cliente recebe o boleto e responde *"já paguei"*. **Quem recebe essa mensagem
não sabe que houve boleto.**

A corrente foi construída inteira e está partida num elo:

| Elo | Estado |
|---|---|
| `webhook.py:623-629` injeta *"[CONTEXTO DA PLATAFORMA] Este cliente recebeu recentemente..."* | ✅ |
| `context_note_for` lê a tabela `platform_sends` (`platform_outbound.py:215`) | ✅ |
| quem escreve em `platform_sends` é `send_to_client_guarded` (`:137`) | ✅ |
| **a cobrança chama `send_to_client_guarded`?** | ❌ **não** — chama `send_message` direto (`billing_collection.py:536`) |
| o que a cobrança registra | `billing_sent_log` — outra tabela, que `context_note_for` não lê |

**Dado:** `platform_sends` = **0 linhas**. `send_to_client_guarded` tem **zero
chamadores de produção**.

E não há como responder mesmo que soubesse: `corridor_playbooks.py` **não menciona
`cobrança`, `boleto`, `inadimpl` nem `2ª via` uma única vez**, e nenhuma das 20
skills registradas é de cobrança.

## E.2 A correção

**E.2.1 — Fechar o elo.** A cobrança passa a sair por `send_to_client_guarded` —
**o próprio código pede isso, em comentário** (`billing_collection.py:676-680`).
Isso alimenta `platform_sends` e liga a nota de contexto.

**E.2.2 — O agente de cobrança.** Agente próprio, papel `billing`, **no número da
cobrança**, com prompt específico. Não é o agente de atendimento respondendo
sobre boleto — é outro trabalhador, na conversa que ele mesmo iniciou.

**E.2.3 — A skill de cobrança.** Construída sobre as centenas de cartas de
cobrança que o RAG já tem:

```
2ª via ................ como obter, e o que fazer se o link expirou
"já paguei" ........... como conferir, quanto tempo leva a baixa
prazo ................. o que acontece depois do vencimento
                        (POR APÓLICE — nunca número fixo)
cancelamento .......... o que já foi cancelado e o que só venceu
negociação ............ o que a corretora pode e não pode oferecer
```

**Regra dura, herdada da campanha de destilação:** prazo pós-vencimento **varia
por apólice e por seguradora**. A skill ensina a verificar, nunca afirma número.

**E.2.4 — Vínculo de thread.** `conversations` ganha origem e referência de
campanha. Hoje o schema não tem nenhum campo desses — a conversa que nasce de uma
cobrança é indistinguível de uma que nasce do nada.

**E.2.5 — Handoff da cobrança.** Quando o cliente pede algo que exige humano
— parcelamento, reclamação, cancelamento — o agente de cobrança faz handoff, pelo
mesmo caminho do Bloco B, e **o dossiê diz que a conversa nasceu de uma cobrança.**

## E.3 Testes

| # | Prova |
|---|---|
| E1 | cobrança enviada registra em `platform_sends` |
| E2 | resposta do cliente traz a nota de contexto ao agente |
| E3 | quem responde é o agente de cobrança, no número da cobrança |
| E4 | a skill não afirma prazo fixo — o teste procura número de dias cravado |
| E5 | handoff de cobrança carrega a origem no dossiê |

---

# BLOCO F — Os corredores completos

## F.1 O que existe

`backend/app/services/corridor_playbooks.py` — **1.199 linhas, código Python
versionado por git**, não tabela. Registro em `:802-817`: **11 corredores**,
1 residencial (Allianz) + 10 auto.

**Não competem com o RAG.** A auditoria estabeleceu:

```
RAG (8.916 cartas) ..... conversa do agente com o SEGURADO
corredor ............... conversa do motor com a URA DA SEGURADORA
```

O que o corredor tem e o RAG não pode ter:

- **âncoras de captura** (`:175-179`) — protocolo e senha só são extraídos se
  casarem com regex real. Sem isso o modelo inventa protocolo.
- **freio de finalização** (`:170-173`) — `DISPATCH_FINALIZE_MODE=test` executa
  o fluxo inteiro e cancela antes de abrir. **Um RAG não sabe cancelar.**
- **política de tela desconhecida** (`:201`) — para e chama humano, nunca
  responde às cegas.

## F.2 O que falta

**F.2.1 — Mapear.** Levantar **todas** as seguradoras que Resulta e AutoFleet
atendem, por ramo, e cruzar com os 11 que existem. O acervo de 8.916 cartas e as
69.150 transcrições dizem exatamente quais são.

**F.2.2 — Criar os que faltam**, por canal:

```
WhatsApp .... o que já existe (11)
portal ...... vidros, pequenos reparos — o portal worker já faz
telefone .... o que só tem 0800; hoje é dado morto
              (insurer_registry.py:27-97, zero consumidores)
```

**F.2.3 — Fechar o ciclo.** Acionar **não é o fim do atendimento**:

```
1. aciona a seguradora
2. captura protocolo e senha
3. AVISA O CLIENTE com o que ficou decidido
4. ACOMPANHA — pergunta se o prestador chegou
5. CONFIRMA que foi resolvido, ou reabre
```

Os passos 3 e 4 existem parcialmente (`dispatch_followup.py`). **O passo 5 não
existe.** E falta o texto da janela entre "iniciei" e "saiu o protocolo" — hoje,
se o modelo não gerar, **o cliente fica em silêncio.**

**F.2.4 — O documento de instruções.**
`docs/canon/COMO-CRIAR-UM-CORREDOR.md`, com: pré-requisitos, âncoras
obrigatórias, política de tela desconhecida, como testar sem acionar, e os erros
já cometidos. **Padrão escrito, para a LLM seguinte não inventar.**

**F.2.5 — Sinistro.** Hoje sinistro é **freio, não fluxo** — cai direto em
handoff (`corridor_playbooks.py:285-288`). Isso **permanece** nesta SPEC: sinistro
continua indo para humano, mas **com o dossiê completo** do Bloco B, e com a lista
de documentos que o acervo já sabe montar.

## F.3 Testes

| # | Prova |
|---|---|
| F1 | toda seguradora presente na carteira tem corredor ou registro explícito de ausência |
| F2 | corredor novo passa no modo teste sem acionar de verdade |
| F3 | protocolo capturado casa com a âncora — nunca é gerado pelo modelo |
| F4 | tela desconhecida → pausa e handoff, nunca resposta às cegas |
| F5 | o ciclo fecha: o acompanhamento chega e a confirmação é registrada |
| F6 | existe texto de espera entre "iniciei" e "protocolo saiu" |

---

# BLOCO G — Os playbooks de conduta chegam ao prompt

## G.1 O desperdício

`conduct_playbooks` — **16 registros**, destilados de atendimento humano real,
com **portão anti-regressão** (`playbook_gate.py:123-195`) e **otimizador
semanal** (`prompt_optimizer.py:161-203`).

**Lidos apenas por `admin_atlas.py`.** O prompt do atendente
(`graph.py:810-944`) recebe: prompt base, data, instruções do cliente, memória,
RAG e auxiliary awareness. **Nenhum ramo lê conduta.**

**Toda essa máquina de qualidade não tem consumidor em runtime.**

## G.2 A correção

O playbook de conduta aplicável entra no prompt do turno, **selecionado pelo
serviço/ramo da conversa**, e passa pelo portão que já existe.

**Regra de tamanho:** conduta não pode empurrar o RAG para fora do contexto.
Teto explícito, e o que não couber fica de fora com registro.

## G.3 Testes

| # | Prova |
|---|---|
| G1 | o playbook aplicável aparece no prompt montado |
| G2 | playbook que não passa no portão não entra |
| G3 | o teto de tamanho é respeitado e o descarte é registrado |

---

# 4. O que fica registrado e não é resolvido aqui

## 4.1 A API da InfoCap responde 500

**Medido em 01/08/2026**, pelo caminho de produção:

```
/attendance/connectors/infocap/lookup  →  provider_error · network_error
api.corpnuvem.com/login (direto)       →  HTTP 500, 3 tentativas, 2 contas
senha errada (controle)                →  HTTP 400
e-mail inexistente (controle)          →  HTTP 403
```

**As credenciais estão corretas e o servidor deles quebra.** É ação de terceiro.

**O que esta SPEC faz a respeito:** o agente passa a **falhar honestamente**.
Quando a consulta de apólice não responde, ele diz que não conseguiu consultar —
**nunca responde sobre cobertura sem ter consultado.** Isso já é a regra soberana
da SPEC-052 §6.4, que hoje existe como constante que nenhuma rota chama.

**Teste:** simular InfoCap fora do ar e provar que o agente não afirma cobertura.

## 4.2 A AutoFleet não tem conexão InfoCap

Nenhuma linha em `tenant_connections` para ela. Precisa ser cadastrada — **depois
que a API voltar**, porque hoje o cadastro não teria como ser validado.

---

# 5. Migrations

Todas idempotentes, expand-first, com APPLY/VERIFY/ROLLBACK escritos **antes** de
rodar. **Ler `docs/canon/MIGRATIONS-AUTHORITY.md` antes de qualquer SQL.**

| Migration | O que faz |
|---|---|
| `..._063_01_handoff_tools_config.sql` | liga `human_handoff` nos agentes de atendimento |
| `..._063_02_support_destinations_backfill.sql` | copia `acionamento_profile` para `human_support_destinations` |
| `..._063_03_conversation_origin.sql` | origem e referência de campanha em `conversations` |
| `..._063_04_outbound_governor.sql` | fila e registro de envio frio |

---

# 6. Gate final da SPEC

Verde quando **todos** passarem:

```
[ ] os 6 testes do Bloco A
[ ] os 7 testes do Bloco B
[ ] os 10 testes do Bloco C
[ ] os 4 testes do Bloco D
[ ] os 5 testes do Bloco E
[ ] os 6 testes do Bloco F
[ ] os 3 testes do Bloco G
[ ] a suíte inteira verde (102+ arquivos)
[ ] /health verde nos sinais de mídia e de template
[ ] /server/ok do Evolution Go com a versão corrigida
```

## 6.1 A prova viva, no número do Founder

Executada com o WhatsApp pareado no número pessoal, **antes** de qualquer
corretora:

```
1. mensagem de teste          → responde a SAIONARA, não o AutoBrokers
2. pedir humano               → notificação chega no grupo certo, com dossiê
3. 5 cobranças de teste       → saem espaçadas de 4 a 8 min, do número certo
4. responder ao boleto        → quem responde sabe que houve boleto
5. acionar assistência        → percorre o corredor e cancela antes de abrir
6. perguntar sobre cobertura  → com InfoCap fora, diz que não conseguiu consultar
```

---

# 7. Riscos

| Risco | Mitigação |
|---|---|
| ligar `human_handoff` muda o comportamento dos 3 agentes de uma vez | agentes estão desligados; a mudança só vale quando forem ligados |
| corredor novo mal escrito aciona de verdade | `DISPATCH_FINALIZE_MODE=test` obrigatório até o corredor passar |
| governador atrasa cobrança legítima | teto é configurável; parada de emergência existe |
| conduta empurra o RAG para fora do contexto | teto explícito com registro do descarte |
| a InfoCap volta durante a execução | nada quebra — o agente passa a consultar |

---

# 8. O que NÃO pode acontecer nesta SPEC

Por CLAUDE.md §5:

```
✗ segundo motor de envio ao lado do que existe
✗ segunda fila ao lado de work_runs
✗ segundo caminho de handoff ao lado do corredor
✗ tabela de corredor no banco — corredor é código versionado
✗ segundo registro de agente ao lado do Registry
```
