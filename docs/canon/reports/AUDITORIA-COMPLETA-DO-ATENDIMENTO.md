# Auditoria completa do Atendimento

> **02/08/2026** · HEAD `c28daff` · projeto Supabase `dcajcvlzcjbmyapmklil`
> Cinco investigações paralelas em Opus 5 + medição direta no banco de produção.
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1) · FATO / INFERÊNCIA separados.
>
> **Motivo:** o Founder travou qualquer mudança no atendimento até existir
> entendimento completo. *"VC NAO PODE ESTRAGAR OS ATENDIMENTOS POR FALTA DE
> INFORMAÇÃO OU PORQUE NAO ENXERGOU DIREITO."* Ele estava certo — eu tinha
> afirmado que "faltava só um corredor". Faltam todos.

---

## Sumário em dez linhas

```
o atendimento hoje ........... NÃO acontece. Os 4 agentes de atendimento
                               estão is_active=false. Nenhum está ligado.
o que executa acionamento .... corridor_playbooks.py — 11 roteiros de WhatsApp
o que a tela chama de corredor  corridor_templates — 2 linhas, motor apagado
telefone / URA discada ....... NÃO EXISTE. Zero telefonia no repositório.
aprovação humana no envio .... NÃO EXISTE. O rótulo na tela é estático.
estado do acionamento ........ só no Redis, TTL 6h. Nenhuma tabela.
estado do atendimento ........ NÃO EXISTE. Nem fase, nem slot, nem coleta.
o que o agente sabe .......... só o RAG. Os 12 playbooks destilados não chegam.
o Atlas ...................... parado desde 29/07. Quatro dias mudo.
o que segura tudo hoje ....... uma allowlist com UM número de telefone.
```

---

## 1 · O caminho real de um atendimento, salto a salto

FATO, lido no código:

```
SEGURADO no WhatsApp
  ↓ POST  4 portas: /webhook/z-api · /z-api/{token} · /evolution/{token}
  ↓                 · /evolution-go/{token}   ← a oficial
  ↓ auth por hash do token → resolve o TENANT
  ↓        ⚠️ a porta legada tem auth DESLIGADA por padrão e resolve o tenant
  ↓           pelo `connectedPhone` do CORPO — forjável
  ↓
OBSERVER TAP           atlas/observer_intake.py — captura e nunca fala
  ↓                    número de seguradora → observed_*
  ↓                    número de segurado   → attendance_*
  ↓
NORMALIZA + DEDUPE     descarta from_me / grupo / broadcast / sem texto
  ↓
BUFFER (Redis)         agrupa 8s, teto 25s   ⚠️ chave SEM tenant
  ↓
PROCESSA               resolve integração → company_id, agent_id
  ↓   ├─ é a SEGURADORA respondendo? → dispatch_router, e RETORNA
  ↓   ├─ allowlist de entrada (hoje: UM número)
  ↓   ├─ humano assumiu? → PARA
  ↓   ├─ portão de observação: agente desligado → só espelha e RETORNA
  ↓   └─ porteira de billing
  ↓
MONTA O TURNO          graph.py — prompt base + identidade + data
  ↓                    + prompt do banco + memória (vazia) + RAG
  ↓
MODELO + TOOLS         insurer_dispatch · infocap · portal · handoff
  ↓
RESPOSTA               balões de 0,7s   ⚠️ sem governador de vazão
  ↓
SEGURADO recebe
```

**Em paralelo, o corretor humano vê** `/dashboard/atendimentos` — fila, ficha,
conversas, segurados — com 8 "estágios" **derivados por requisição e nunca
persistidos**. O agente não os lê nem os escreve.

---

## 2 · As fases: as que existem no papel e as que existem no código

O Founder perguntou pelas fases: primeiro contato, coleta, acionamento,
acompanhamento, resolução. Existem **três respostas diferentes** no produto, e
elas não conversam.

### 2.1 As 12 fases do corredor — declaradas, nunca executadas

📊 `corridor_templates.phases` do subcorredor Eletricista:

```
 1 intake              7 prepare_dispatch
 2 identify_insured    8 waiting_approval
 3 identify_policy     9 action_prepared
 4 select_subcorridor 10 follow_up
 5 collect_slots      11 closed
 6 readiness_check    12 handoff
```

FATO: **zero leitores** desta coluna, em qualquer linguagem. O motor que a lia
foi apagado em 20/07 (commit `d88ac70`, "remove runtime TS do MVP — 30 módulos").

### 2.2 As 6 etapas do prompt — em prosa, sem estado

FATO: `core/prompts.py` instrui o modelo em seis passos numerados —
*entenda · identifique · confirme · colete · acione · repasse*. São **instruções
que o modelo lê**, não estado que o sistema guarda ou verifica.

📊 `grep -niE "\bfase|phase|etapa|stage|slot" backend/app/agents/*.py` → **zero**.
O `AgentState` não tem campo de fase, de slot preenchido, de dado confirmado nem
de objetivo do atendimento.

**Consequência citável:** a tool de acionamento obriga o modelo a **re-declarar
15+ campos a cada chamada**, reconstruídos do texto da conversa. A memória do
que já foi coletado é a janela de contexto — 60 mensagens. Passou disso, o que
foi coletado nas primeiras 20 some. O código registra que isso **já quebrou em
produção** com janela de 20: o agente repediu o CPF do mesmo cliente.

### 2.3 A máquina de estados que EXISTE de verdade

FATO: só o **acionamento** tem máquina de estados real, em
`insurer_dispatch_service.py`:

```
preparing → ready_to_send → [GATE] → ura → human_phase → captured → monitoring
     └────────────────── needs_human ←──────────────────────┘
     └── test_aborted  (quando o freio de finalização está fechado)
```

E ela vive **só no Redis**, chave `dispatch:active:{corretora}:{telefone}`,
TTL 6h (24h em `monitoring`). **Nenhuma tabela guarda esse estado.**

> ⚠️ Viola o CLAUDE.md §6 — Supabase é a verdade durável, Redis é transitório.
> Restart de Redis ou 6h de silêncio perdem um acionamento em voo, sem
> reconciliação. Também não passa por Work Run (SPEC-055).

### 2.4 "Resolvido" não existe

FATO: `'resolved'` aparece **apenas num comentário**. O único escritor real é
`status='closed'`, acionado por **botão manual** na tela. Não há motivo de
encerramento, desfecho nem outcome.

E o "concluído" da fila é **um cronômetro**: `agora - última_mensagem > 48h`.
Uma conversa abandonada aparece como concluída.

📊 `attendance_sessions`: 8.872 linhas, **todas `closed`** — fechadas por
varredura de silêncio de 6h, não por desfecho.

---

## 3 · As peças, uma a uma

### 3.1 Corredor — **são duas coisas com o mesmo nome, e não se tocam**

| | `corridor_templates` (banco) | `corridor_playbooks.py` (código) |
|---|---|---|
| o que é | fases, slots, guardrails, golden tests | 11 roteiros: âncora regex → resposta |
| quantos | 📊 **2** | 📊 **11** (1 residencial + 10 auto) |
| origem | SPEC-005 / SPEC-006 | SPEC-017 / 031 / 034 |
| motor | **apagado em 20/07** | **vivo** |
| executa? | ❌ | ✅ |
| ramo | `line_kind='residential'` | normaliza só `'residencial'` |

**Não há import, join nem chave comum entre os dois.** E as chaves são
intraduzíveis: `problem_description` × `problema_descricao`,
`allianz_residential_assistance` × `allianz-residencial-whatsapp`.

📊 **22 das 28 colunas de `corridor_templates` não têm leitor de runtime.**
`phases`, `required_slots`, `guardrails` e `golden_tests`: **zero leitores**.
As 6 lidas viram texto de card na galeria.

📊 As tabelas de execução estão no schema `graveyard`:

```
graveyard.corridor_runs ...... 50 · TODAS 'active' · 13/06 a 17/06
graveyard.dispatch_packets .... 7 · ready_for_approval 3 · missing_data 3
                                    awaiting_approval 1 · ZERO enviados
graveyard.attendance_cases ... 52
```

**Em cinco dias de vida, aquele motor nunca despachou nada — nem em dry-run.**

#### A tela mente para a corretora

`app/dashboard/personalizacao/seguradoras/InsurersClient.tsx:161-162`:

> *"Sua corretora tem N corredor(es) ativo(s) nesta seguradora — **o atendente já
> aciona por eles**."*

FATO: falso. `InsurerDispatchTool` resolve o playbook por `insurer_key` +
`line_kind` contra dicionários **em memória** — nunca abre o banco. **Ativar ou
pausar corredor na tela não muda nada.** A regra que tornaria a ativação real —
`isCorridorOperable()` — **existiu e foi apagada** no mesmo commit `d88ac70`.

📊 Cobertura de corredor hoje: `line_kind` existente = `residential`, e só.
**Zero corredores de auto na tabela.** Os 2 estão instalados só na Resulta.

### 3.2 Playbook de conduta — destilado e órfão

📊 16 registros (12 `active`, 4 `draft`), por **(ramo, serviço)** — não por
seguradora. Gerados por `claude-opus-5` em 29-30/07 a partir de **297
atendimentos humanos reais**, com ficha de coleta de até 19 campos.

| ramo | serviços | sessões que ensinaram |
|---|---|---|
| auto | consulta · guincho · sinistro · vidros · ~~pneu~~ | 30 · 28 · 30 · 16 · 6 |
| residencial | consulta · eletricista · encanador · sinistro · ~~chaveiro~~ · ~~vidros~~ | 24 · 20 · 22 · 30 · 3 · 5 |
| vida | consulta · sinistro | 7 · 30 |
| outro | consulta · sinistro · ~~vidros~~ | 30 · 30 · 3 |

FATO — **nenhuma palavra deles chega ao turno.** Todos os leitores da tabela:
o juiz que aprova (`playbook_gate.py`), o otimizador semanal, o destilador que
os escreve, e as telas de admin. `grep "conduct_playbook" backend/app/agents/graph.py`
→ **zero**.

> Ativar um playbook hoje muda uma string de status e um contador no painel.
> Os 19 campos da ficha de sinistro de auto, sintetizados de 30 atendimentos
> humanos, não influenciam uma palavra do que o agente diz.

### 3.3 Cartas e RAG — o único conhecimento que chega

📊 `knowledge_cards`: 9.699 linhas — **8.916 published**, 468 superseded,
310 rejected_pii, 5 rejected_absoluto. Publicadas entre 29 e 30/07.
📊 **6.507 (67%) não têm seguradora atribuída.**

Nascem de `attendance_transcripts` → sessão fechada → mascaramento
(`templatize`) → destilação em 2 estágios → curadoria (junta quase-cópias,
barra promessas absolutas) → Qdrant `autobrokers_global`.

**É a única fonte de conhecimento que efetivamente entra no prompt**, colada
crua com 4 instruções genéricas. RAG global **está ligado para atendimento**.

### 3.4 O que chega ao turno — lista exata

```
ESTÁTICO   ATTENDANCE_BASE_PROMPT (~7,5 KB, escrito à mão)
           identidade (nome + corretora) · data e hora
           agents.agent_system_prompt (do banco)
           expansões de HTTP tools / MCP / subagentes

DINÂMICO   memória          📊 VAZIA — user_memories 0, company_memories 0
           RAG              ← o único canal real de conhecimento
```

**O que existe e NÃO chega:** os 12 playbooks de conduta · `company_memories`
(0 linhas, e o único escritor não tem chamador) · `knowledge_candidates` (0) ·
`ura_maps` · e **toda a camada de procedência da SPEC-052 §6.4** — precedência
de fontes, orçamento de contexto, cabeçalhos de vigência e o aviso
`exige_apolice`, que impede o agente de confirmar cobertura de apólice concreta
a partir de condição geral. Só os testes a chamam.

> O próprio módulo se descreve como *"a diferença entre um sistema útil e um
> passivo"*. Está escrito, testado, e sem nenhum chamador em produção.

**`CONTEXT_ASSEMBLY_MODE=shadow`**: virar para `on` entrega **a metade que
economiza** (pular fonte por intenção) e **nenhuma parte da que protege** —
porque essa metade não tem chamador em nenhum modo.

### 3.5 Atlas — a única peça que aprendeu, e está parada

📊 `ura_maps`: **10 mapas vivos** (`status='observed'`), um por seguradora,
tecidos em 29/07 · 238 versões aposentadas · 3 retired.

📊 `observed_sessions` 479 · `observed_events` 17.490 — por seguradora:
porto 139 · allianz 116 · yelum 86 · hdi 41 · tokio 36 · azul 19 · bradesco 15.

**FATO — o Atlas parou.** Último evento observado **29/07 18:48**; última sessão
observada **28/07 19:21**. Quatro dias mudos, com três integrações `observer`
ativas e `channel_status='connected'`. **Nenhum documento registra isso.**

**INFERÊNCIA:** o `last_seen_at` congelou no mesmo minuto do último evento — é
compatível com o backend ter parado de receber webhooks (instância caída ou
processo reiniciado sem reconectar), não com "não houve conversa". **Causa não
determinada.**

E: as 479 sessões de seguradora **não produzem carta nenhuma** — só mapas de
URA. As 8.916 cartas vieram das conversas com segurados.

### 3.6 Canais das seguradoras — informação, não ação

📊 Moram em `lib/attendance/insurer-contacts-global-seed.ts` — **22 seguradoras**,
vindas de `docs/intake/sinistro e assistencias - contatos.xlsx`. **Globais e
corretamente globais**: o telefone da assistência é o mesmo para toda corretora.

O campo guarda o caminho da URA no próprio número: `"40901110 - 1-1-2"` =
*liga, tecla 1, tecla 1, tecla 2*.

**FATO — não existe telefonia.** Varredura por `twilio|vonage|plivo|asterisk|
dtmf|voip`: **zero ocorrências**. "URA" neste produto significa o **menu de
WhatsApp** da seguradora — o sistema escolhe opção mandando texto. O código
prova: remove marcadores de negrito do WhatsApp dos menus e limita títulos a 24
caracteres porque é o limite de lista do WhatsApp.

**Os telefones exibidos na tela não são discados por nenhuma linha de código.**
Para seguradora sem WhatsApp (Youse), o sistema não age.

⚠️ **Duas listas telefônicas cravadas, sem sincronia.** A tela mostra Tokio
`11 95302-2395`; o motor usa `5511995786546`, com nota de 14/07: *"o número
OFICIAL agora é 11 99578-6546 (o antigo virou reserva)"*. **A tela já exibe
número desatualizado.**

`insurer_action_channels` não é tabela: é um array em
`tenant_connections.connection_config`. Todos os providers têm
`send_real_allowed: false` **como tipo literal**. `grep backend/app/` → zero.

### 3.7 Portais

📊 `portals` 17 · `portal_accounts` 1 · `portal_jobs` 91 —
**needs_human 67 · failed 5 · done 19**. Três em cada quatro pedem socorro.
O portal serve cobrança/consulta, não acionamento de assistência.

---

## 4 · Aprovação humana: não existe no acionamento

O sistema HITL existe e é sério — fingerprint do payload, expiração de 24h,
exceções próprias. **Nunca alcança o despacho.** Verificado por quatro caminhos:

```
o serviço de aprovação é instanciado em ......... 1 arquivo (smith_worker)
a tool de acionamento roda em ................... LangGraph, outro caminho
grep "approval|aprova" em agents/nodes.py ....... ZERO
o gancho session["finalize_approved"] ........... só um TESTE o escreve
a rota que executa aprovação ..................... 2 ações, ambas dry-run
```

📊 As **8** linhas de `approval_requests` são todas de Auxiliar (rascunho de
WhatsApp, junho). **Zero de atendimento, na vida inteira do produto.**

**"Ação externa requer aprovação"** é um rótulo estático derivado de um booleano
do template. Não consulta nada, não bloqueia nada.

O que existe no lugar é **auto-atestação do modelo**: a tool exige
`dados_confirmados=true`, e quem marca é o próprio LLM. Freio de conduta, não
porteira.

---

## 5 · Os P0

| # | Defeito | Estado |
|---|---|---|
| **1** | **Buffer sem tenant na chave** — `whatsapp_buffer:{phone}`. O mesmo segurado falando com 2 corretoras em 8-25s tem as mensagens **fundidas** e processadas sob a integração da última | ativo |
| **2** | **Webhook legado sem auth por padrão** — tenant vem do corpo, forjável | ativo |
| **3** | **`observer_number` não é telefone** — são os dígitos do nome da instância. 📊 O valor-constante `attendance-channel` **já apareceu 1 vez**. Busca de sessão e índice de dedupe **não filtram `company_id`** | risco demonstrado |
| **4** | **Nenhum agente de atendimento ativo** — e `_get_raw_agent` pega o primeiro ativo por data, sem olhar papel: o **core**, cujo prompt manda entregar CPF sem mascarar. A Resulta tem integração `attendance` **ativa** | segurado só pela allowlist |
| **5** | **Suporte humano compartilhado** — Resulta e AutoFleet no mesmo grupo `120363427334937446@g.us` | ativo |
| **6** | **Handoff não avisa ninguém** — só `UPDATE conversations`. Zero envio, zero contexto anexado. E declara sucesso mesmo quando o UPDATE não acha a conversa | ativo |
| **7** | **Sem governador de vazão** — o único controle é `sleep(0.7)` entre balões | ativo |
| **8** | **69.150 transcrições de segurado em texto claro**, sob RLS sem policy, com purge de 90 dias agendado que **não roda desde 29/07**. `observed_events` **não tem retenção nenhuma** | ativo |
| **9** | **Guardrails de entrada desligados por padrão** no caminho do segurado externo | ativo |
| **10** | **Destilador cross-tenant por desenho** — atendimento da corretora A vira carta global que o agente da B consome. Controle único: mascaramento + revisão | por desenho |

E as cicatrizes no código, deixadas por quem consertou:

```
"incidente 2026-07-10: placa e telefone inventados FORAM PARAR na seguradora"
"teste Allianz 12/07: '1' fixo pegou o carro ERRADO"
```

⚠️ Com a InfoCap fora e o portão de envio aberto, **nada no código impede
acionar uma apólice que nunca foi confirmada**: a busca de placa é best-effort
e, se falhar, o agente pergunta ao cliente.

---

## 6 · Contradições do canon — incluindo as minhas

| # | Contradição |
|---|---|
| **C-1** | 📊 **"251 mapas de URA"** no GLOSSARIO e no PORTAIS-E-CORREDORES era contagem de **linhas**, não de mapas. São **10 vivos**. **Erro meu**, com marca 📊, atravessando dois documentos canônicos — o defeito exato que a §12.1 existe para impedir. **Corrigido em 02/08.** |
| **C-2** | Os documentos chamam `ura_maps` de *"matéria-prima pronta"* implicando conexão. **Não existe caminho de código** entre o mapa e quem atende. **Corrigido em 02/08.** |
| **C-3** | `observed_sessions.summary` **não é um resumo** — guarda `{marker, source}` da importação. Quem lê o nome conclui que há 479 sessões resumidas. Há zero. |
| **C-4** | `observed_sessions.ramo` e `.servico` **NULL em 100%** das 479 linhas. O PENDENCIAS registra o gêmeo em `attendance_sessions`, não este. |
| **C-5** | Duas migrations de 28/07 (`_02`, `_04`) **apagaram dado de produção e não existem no repositório** — nunca foram commitadas. Sem APPLY/VERIFY/ROLLBACK, contra o CLAUDE.md §8. |
| **C-6** | O canon declara *"PII vive só aqui e nunca vai ao RAG"* — verdadeiro sobre o RAG, **incompleto sobre o banco**. |
| **C-7** | `EXECUTION-MASTER-PLAN.md` cobre só as SPECs 052–062. **Nenhuma das 26 SPECs de atendimento tem linha de estado nele** — nem a 063. |
| **C-8** | `FOUNDER-DECISIONS.md` e `specs/README.md` ainda dizem **"Não será criada SPEC-063"**. Ela nasceu em 01/08. |
| **C-9** | **SPEC-038, autoridade do Atlas**, citada no topo de todo `services/atlas/`, **não está em `docs/canon/specs/`**. O código executa uma SPEC fora do diretório canônico. |
| **C-10** | `SPEC-034` está marcada como "superada", mas é a **única** fonte do schema de `ura_maps`, dos timers da Sentinela e da escada de recuperação. Seguir o README literalmente descarta os únicos requisitos de vigilância que existem. |

---

## 7 · O que ninguém neste repositório sabe

Perguntas cuja resposta **não está no código nem no banco** — vão para o chat
anterior e para o Founder:

1. **Por que o Atlas parou em 29/07?** É a pergunta mais urgente.
2. **Qual é a intenção sobre `corridor_templates`?** Ressuscitar como registro
   governável (é o desenho da SPEC-005, e é bom) ou aposentar como as irmãs?
   **CLAUDE.md §10(3) — conflito canônico. Não é decisão minha.**
3. **Os valores de produção** de `INSURER_DISPATCH_LIVE`, `DISPATCH_FINALIZE_MODE`,
   `CARTOGRAPHER_MODE`, `WHATSAPP_WEBHOOK_AUTH_MODE`, `ATTENDANT_INBOUND_ALLOWLIST`.
   Nenhuma está no `.env.example`.
4. **Por que os 4 agentes de atendimento estão desligados?** Decisão, gate de
   go-live, ou efeito colateral?
5. **O conteúdo das duas migrations sem arquivo.**
6. **Se algum corredor já completou um acionamento real ponta a ponta.**

---

## Declaração

Auditoria **somente leitura**. Nenhum dado alterado, nenhuma migration aplicada,
nenhuma mudança em código de atendimento. As duas únicas edições foram a
correção do número errado que **eu** havia escrito no GLOSSARIO e no
PORTAIS-E-CORREDORES.

Nenhum motor paralelo foi criado — nada foi construído nesta passagem.
