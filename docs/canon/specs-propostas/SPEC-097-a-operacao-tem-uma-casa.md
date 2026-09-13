# CANDIDATE SPEC-097 — A OPERAÇÃO TEM UMA CASA
## Operations Workspace · Fila, Casos, Conversas, Segurados e Timeline Operacional

**Produto:** AutoBrokers Intelligence OS  
**Status:** PROPOSTA INICIAL / CANDIDATE SPEC — não é a SPEC definitiva até o warm-up AAA  
**Data:** 03/09/2026  
**HEAD reconfirmado na correção documental:** `67506906f0b8f60d89585878f15958a9ea438f09`  
**Protocolo obrigatório:** AutoBrokers AAA **v11.2**  
**Research Pack obrigatório:** `SPEC-097-a-operacao-tem-uma-casa-RESEARCH-PACK.md`  
**SHA-256 do Research Pack:** `26fda881b20c016d07ff1d9c4b1c04b87bed909a5af5a4a3ca63ab9b89be4ad0`  
**Tipo:** EVOLUÇÃO + CONVERGÊNCIA + CORREÇÃO DE EXPERIÊNCIA OPERACIONAL  
**Nota estratégica:** **99/100**

> **OBSERVAÇÃO DE GOVERNANÇA DA PROPOSTA**  
> Esta é uma proposta inicial para a SPEC-097. Serve de insumo e de inspiração para criarmos uma SPEC definitiva.  
> A SPEC definitiva pode ser modelada, melhorada e modificada em tudo que for melhor para o projeto.  
> Esta observação vale para todas as propostas de SPEC produzidas por esta Foundry.

---

# 0. ⛔ CONTRATO DE DOIS DOCUMENTOS — RP0

Esta Candidate SPEC **não é autossuficiente**.

```text
SPEC-097-a-operacao-tem-uma-casa.md
+
SPEC-097-a-operacao-tem-uma-casa-RESEARCH-PACK.md
=
PACOTE DE PROPOSTA DA SPEC-097
```

A SPEC contém o contrato de produto e execução. O Research Pack contém a pesquisa, evidência, arqueologia do ResultVision, referências externas, decisões ADOPT/ADAPT/REJECT e justificativas.

Antes do warm-up e antes de qualquer alteração de código, o executor registra:

```text
RP0_SPEC_READ = YES
RP0_RESEARCH_PACK_READ = YES
RP0_RESEARCH_PACK_SHA256 = 26fda881b20c016d07ff1d9c4b1c04b87bed909a5af5a4a3ca63ab9b89be4ad0
RP0_SHA_MATCH = YES
RP0_CURRENT_HEAD = <sha vivo>
RP0_STALE_PREMISES = [...]
RP0_RESULTVISION_LEDGER_ACK = YES
RP0_EXTERNAL_REFERENCE_LEDGER_ACK = YES
```

**RP0 falhou → não codificar.**

---

# 1. RESULTADO EM UMA FRASE

> **Transformar Atendimentos em uma casa operacional coerente na qual o corretor consegue descobrir em segundos o que está acontecendo, o que aconteceu, quem está cuidando, de quem estamos esperando, quais documentos existem e qual é a próxima ação — sem criar um ticketing paralelo nem substituir as authorities modernas do AutoBrokers.**

---

# 2. TESTE DO PRODUTO

Uma corretora abre o Dashboard numa manhã movimentada. Sem reconstruir conversas manualmente ela precisa descobrir:

1. o que precisa de uma pessoa agora;
2. o que a IA está fazendo;
3. o que aguarda o cliente;
4. o que aguarda a seguradora;
5. o que está parado há tempo demais;
6. quem assumiu cada atendimento;
7. o que o segurado pediu;
8. a apólice e seguradora envolvidas;
9. o último movimento;
10. o próximo movimento;
11. documentos recebidos e enviados;
12. protocolo externo;
13. Work Run ativo;
14. approval pendente;
15. como o atendimento terminou.

Se isso não ficar claro, a SPEC falhou mesmo que produza um Kanban visualmente bonito.

---

# 3. POR QUE AGORA

O backend evoluiu mais rápido que sua representação operacional. Hoje já existem conversation/messages, dispatch, attendance sessions/executions, Work Runs, Work Events, Work Waits, handoff/claim, resolução, approvals, Artifacts, evidence e Claims Learning Shadow. A navegação ainda apresenta Fila, “Histórico”, Conversas, Segurados e Ficha como superfícies parcialmente desconectadas.

A dívida é de **compreensão operacional**, não de mais um motor.

---

# 4. DE ONDE VÊM AS IDEIAS

A solução combina três famílias, explicadas em profundidade no Research Pack:

```text
AUTOBROKERS MODERNO
SPEC-043 · 046 · 086 · 093-B · Work OS · ownership · waits · resolution

RESULTVISION
Work Queue · Kanban · Case Drawer · Case 360 · Documents · Conversation linking

REFERÊNCIAS EXTERNAS
Intercom · Front · Zendesk · Salesforce Service Cloud · ServiceNow CSM · Linear
```

O ResultVision é arqueologia de produto, não authority arquitetural. Referências externas são padrões a adaptar, não componentes a instalar.

---

# 5. DECISÕES CONGELADAS

## D-097-01 — “Casos” volta a ser conceito visível

```text
Atendimentos
├── Fila
├── Casos
├── Conversas
└── Segurados
```

“Histórico” deixa de ser o nome principal da rota de Casos.

## D-097-02 — Caso não ressuscita automaticamente `attendance_cases`

Caso nasce como **product/read model** sobre authorities atuais. Uma entidade persistente fina só entra se o warm-up provar necessidade real.

## D-097-03 — Fila possui `Lista | Quadro`

Uma mesma query/read model, duas projeções.

## D-097-04 — Kanban não é authority

Drag-and-drop nunca cria estado apenas porque o card mudou de coluna.

## D-097-05 — “Agora” é o topo do Caso

Antes de detalhes técnicos o produto mostra: situação, owner, waiting-on, tempo, atenção, próxima ação e protocolo.

## D-097-06 — Timeline é projeção

Não criar event store paralelo.

## D-097-07 — Documentos são evidence first-class

Fáceis de localizar no Caso e também projetados na Timeline.

## D-097-08 — Conversas permanece communication-first

Case coordena e explica; Conversation comunica.

## D-097-09 — Segurados não vira CRM genérico

É pessoa → apólice → casos → conversas/documentos.

## D-097-10 — Status, ownership, wait e attention são dimensões diferentes

Não criar enum gigante que mistura tudo.

---

# 6. ONTOLOGIA

- **Case:** situação de negócio que precisa chegar a um desfecho e ser compreendida como unidade.
- **Conversation:** thread de comunicação relacionada.
- **Work Run:** trabalho durável sobre a situação.
- **Wait:** dependência temporal explícita.
- **Ownership:** quem possui capacidade operacional/comunicação agora.
- **Attention:** sinal derivado de que algo precisa ser observado/tratado.
- **Approval:** decisão humana obrigatória antes de efeito.
- **Document:** evidência recebida, enviada ou gerada.
- **Artifact:** entregável produzido pelo Work OS.
- **Timeline Event:** representação humana de evento real.
- **Next Action:** próximo movimento derivado/autorizado.

---

# 7. INVARIANTES

1. Nenhum runtime novo.
2. Nenhum Work OS novo.
3. Nenhum event store novo.
4. Nenhum ticketing paralelo.
5. `company_id` nunca é authority escolhida pelo frontend.
6. UUID não é autorização.
7. Case projection nunca cruza tenant.
8. Caso encerrado não permanece na Fila ativa.
9. Ownership exibido corresponde à authority real.
10. Wait exibido corresponde à espera real.
11. Documento exibido possui provenance.
12. Next Action não é ficção de LLM.
13. List e Board mostram a mesma população sob o mesmo filtro.
14. Search não cruza tenant.
15. Timeline humana não vira log técnico.
16. Falha de projection não é mascarada como zero.
17. Contradição de sources vira unknown/contradiction, não escolha silenciosa.
18. Case Workspace permanece útil sem enriquecimento LLM.
19. Mobile não é versão mutilada.
20. Smith/LangGraph/Qdrant permanecem invisíveis para a corretora.

---

# 8. CASE IDENTITY — HIPÓTESE A REFUTAR NO WARM-UP

P0 recomendado: `case_ref` sintético estável ancorado primariamente em conversation. O executor deve medir se uma situação de negócio atravessa múltiplas conversations, canais e Work Runs. Se sim, uma entidade persistente **fina** pode ser superior.

⛔ Proibido restaurar tabela legacy por conveniência.

---

# 9. CASE READ MODEL — CONTRATO SEMÂNTICO

A implementação precisa conseguir responder, independentemente dos nomes concretos:

```text
identity       case_ref · company_id · primary_conversation · conversations[]
customer       customer_ref · insured_display · phone_display
insurance      policy_ref · policy_number · insurer_ref · insurer · line
request        service_type · request_summary
lifecycle      current_phase · resolution_status/reason · opened/resolved/latest
ownership      mode · owner_ref · owner_display
wait           waiting_on · wait_since · wait_due_at
attention      level · reasons[] · time_in_state · sla_state
next           next_action · actor · due_at
evidence       protocol · documents[] · artifacts[]
work           active_work_refs[] · run_count · approval_count
```

---

# 10. DATA PRECEDENCE CONTRACT

Candidate inicial:

```text
RESOLUTION  → authority da SPEC-086
OWNERSHIP   → claim/handoff authority
WAIT        → active work_wait
WORK        → active Work Run(s)
PHASE       → attendance/dispatch state
CUSTOMER    → canonical customer authority
POLICY      → InfoCap/provider authority
DOCUMENTS   → evidence/media/document authorities
NEXT ACTION → deterministic precedence
```

A versão definitiva documenta quem vence em cada conflito.

---

# 11. ATTENTION ENGINE

Attention é derivada, não lifecycle. Reasons candidatas:

```text
human_requested
wait_overdue
sla_at_risk
work_failed
approval_pending
document_missing
followup_due
unread_customer
no_progress
projection_contradiction
```

BLOCO 0 mede quais são observáveis de verdade.

---

# 12. NEXT ACTION

Precedência candidate:

1. ação humana obrigatória;
2. approval pendente;
3. blocker/next step do Work Run;
4. active wait / prazo;
5. dispatch/corridor deterministic next step;
6. follow-up vencido;
7. policy-defined next action.

Sugestão de LLM, se existir, aparece com rótulo de sugestão e nunca como command authority.

---

# 13. NAVEGAÇÃO

```text
Atendimentos
├── Fila
├── Casos
│   ├── Ativos
│   ├── Encerrados
│   └── Todos
├── Conversas
└── Segurados
```

Deep links precisam preservar contexto entre Fila, Case, Segurado, Conversation, Document, Work Run e Artifact.

---

# 14. FILA

Objetivo: **o que merece atenção agora?**

Views candidatas:

```text
Para você
Precisa de atenção
Todos ativos
IA trabalhando
Com humano
Aguardando cliente
Aguardando seguradora
Aguardando documento
Aguardando confirmação
SLA/tempo em risco
Travados
```

Não publicar view que o censo mostre permanentemente vazia.

---

# 15. LISTA E QUADRO

**Lista:** volume, busca, sorting, densidade.  
**Quadro:** distribuição, gargalo, acúmulo, leitura espacial.

Mesmo dataset. Mesmos filtros. Mesmo case_ref.

Colunas não devem misturar ownership, wait e phase. Candidate de board operacional:

```text
Novo / Entendendo
Em trabalho
Aguardando externo
Precisa de humano
Pronto para fechar
```

Encerrado fica fora do active board.

---

# 16. DRAG-AND-DROP

Qualquer drag permitido segue:

```text
visual transition
→ domain command
→ authorization
→ state validation
→ idempotency
→ audit event
→ projection refresh
```

Sem command seguro, card não é draggable ou o drop abre a ação explícita.

---

# 17. CASE WORKSPACE

Topo:

```text
HEADER
segurado · pedido · seguradora · apólice · case ref/protocolo

AGORA
situação · ownership · waiting-on · tempo · attention · next action · deadline

Timeline | Conversas | Documentos | Dados | Trabalhos | Notas
```

Timeline é default recomendado.

---

# 18. TIMELINE OPERACIONAL

Pode projetar eventos como:

- cliente/IA/humano/seguradora enviou mensagem;
- apólice identificada;
- documento recebido/enviado;
- seguradora acionada;
- protocolo recebido;
- Work Run iniciou/mudou milestone;
- wait abriu/satisfez/expirou;
- humano solicitado/assumiu;
- IA retomou;
- approval solicitado/decidido;
- Artifact produzido;
- follow-up criado/executado;
- atendimento encerrado.

Por padrão não exibir node, tool call, SQL, lease, Redis, Qdrant ou retry técnico.

Filters candidates: Tudo · Conversas · Ações · Documentos · Humano · IA · Seguradora · Interno.

---

# 19. DOCUMENTOS

Organização candidate:

```text
Recebidos do segurado
Enviados à seguradora
Apólice / certificado
Fotos
Áudios
Gerados pelo AutoBrokers
Outros
```

Cada item, quando disponível: nome/tipo, preview, origem, ator, horário, extraction status, destination e provenance.

O mesmo arquivo aparece como documento e evento sem duplicar bytes.

---

# 20. CONVERSAS, SEGURADOS, WORK E NOTAS

**Conversas:** mostrar threads relacionadas e abrir a Central completa; não duplicar obrigatoriamente todo composer.  
**Segurados:** nome/telefone, apólices relevantes, casos ativos/encerrados e últimos eventos; sem CRM.  
**Work/Approval/Artifact:** projeções e deep links; não recriar entidades.  
**Notas:** nota interna ≠ mensagem externa; antes de nova tabela, consolidar writers existentes.

---

# 21. PERFORMANCE / REALTIME

Arquitetura de leitura recomendada:

```text
QueueProjection       → campos mínimos + counts
CaseSummaryProjection → AGORA + facts
CaseTimeline          → cursor/pagination
Documents             → lazy
Conversations         → lazy
Work details          → lazy
```

BLOCO 0 mede p50/p95, volume e polls. Realtime é otimização de entrega, nunca authority. Supabase Realtime/SSE/polling fallback só entram após medição.

---

# 22. MULTI-TENANT / IDOR

Cada relação Case→Conversation/Work/Approval/Artifact/Document/Policy precisa ser resolvida dentro do company context autenticado. Teste obrigatório com dois tenants.

---

# 23. UX ACCEPTANCE

Screenshot da Fila em menos de 10s precisa responder: qual precisa de mim, por quê, quem possui, esperando quem, próximo passo, atraso e onde abrir contexto.

Screenshot do Case: o que foi pedido, o que aconteceu, onde está, quem cuida, onde estão documentos/conversa, o que IA/humano fizeram e como termina/terminou.

---

# 24. IMPLEMENTATION BLOCKS — CANDIDATE

## BLOCO 0 — Censo vivo
HEAD/protocolo, schema, UI, volumes, relações, pendências 086/093-B, state distribution e premissas obsoletas.

## A — Case Read Model
Identity, precedence, tenant boundary, contradictions e performance.

## B — Attention + Next Action
Deterministic derivation e controls.

## C — Fila v2
Views, search/filter, List/Board.

## D — Case Workspace
AGORA, facts, navegação.

## E — Unified Timeline
Adapters/projection, provenance, pagination.

## F — Documents
Projection, preview, provenance.

## G — Conversation/Work/Approval/Artifact linking
Deep links e lazy details.

## H — Segurados
Operational profile.

## I — Notes
Consolidar mechanism interno.

## J — Realtime/performance/accessibility/mobile
Medir e otimizar.

## K — Cutover
Histórico→Casos, redirects, dead-code removal, sem dual UI truth.

---

# 25. AAA v11.2 — EXECUTION CARD INICIAL

```text
OUTCOME .............. operação compreensível/navegável por Case
RISCO ................ candidato 6
SUPERFÍCIE ........... 3
PISO APLICADO ........ auth/company_id e possível migration → CRÍTICO
NÍVEL ................ CRÍTICO
UNIDADES ............. recompor após BLOCO 0
COESÃO ............... read model + precedence juntos; UI após contrato
PARALELISMO REAL ..... só arquivos disjuntos depois do contrato
TIME ................. time v11.2 conforme nível; sem painel desnecessário
REFERÊNCIA ........... Research Pack + ResultVision + refs externas
GATES ................ G0–G14
O ELO ................ projection correta → UI correta; provar com fixtures/queries
ORÇAMENTO ............. v11.2: economizar agentes/contexto, nunca mutation/gates
```

O executor recalcula a conta.

---

# 26. GATES

- **G0 Research Pack:** RP0 verde.
- **G1 Case Truth:** cada dimensão aponta authority.
- **G2 No Parallel Truth:** nenhum writer novo duplica lifecycle/ownership/wait.
- **G3 Tenant Isolation:** dois tenants, zero relation leak.
- **G4 List = Board:** mesma população.
- **G5 Resolution Truth:** encerrado sai de ativos preservando história.
- **G6 Ownership Truth:** humano/IA corretos.
- **G7 Wait Truth:** ator correto e satisfação remove wait.
- **G8 Next Action Truth:** deterministic authority.
- **G9 Documents Truth:** provenance e tenant.
- **G10 Timeline Truth:** evento humano corresponde a fato.
- **G11 Search Isolation:** zero cross-tenant.
- **G12 Performance:** p95 definido no warm-up e sem N+1.
- **G13 Accessibility/Mobile:** caminho principal operável.
- **G14 Cutover:** uma única superfície oficial de Caso.

---

# 27. MUTATION / CONTROLS

Mutações candidatas obrigatórias:

1. remover company filter;
2. manter closed em active;
3. trocar owner humano por IA;
4. trocar wait insurer por client;
5. alimentar List/Board com sources diferentes;
6. inserir documento de tenant B;
7. transformar LLM suggestion em next action authority;
8. apagar provenance de event;
9. não invalidar projection após resolution;
10. deep-link case A→conversation B;
11. permitir drag inválido;
12. converter API error em empty state.

Cada controle: verde → mutação → vermelho → restauração → verde.

---

# 28. E2E

1. IA conduz → seguradora → protocolo → wait → resolution.
2. IA → HUMAN_REQUESTED → humano assume → ownership muda → encerra.
3. Espera seguradora sem cobrança errada ao cliente → retorno → progression.
4. Documento inbound → Documents + Timeline → arquivo correto.
5. Work Run relacionado → status/result no Case.
6. Tenant A tenta abrir recursos B → denied.
7. List/Board mesmo filtro → mesma população.
8. Mobile Fila→Case→Documento/Conversa→retorno com contexto.

---

# 29. RED TEAM

Missão: **fazer o dashboard mentir**.

Atacar stale wait, stale owner, stale resolution, wrong policy/doc/protocol, same phone em tenants diferentes, malformed deep link, claim humano concorrendo com IA, realtime ordering, pagination duplicate, search leak, partial API failure.

---

# 30. ROLLBACK / CUTOVER

Preferir expand/cutover:

```text
new projection/API
→ new UI controlada
→ compare old/new
→ cutover
→ redirect
→ remover dead surface depois da prova
```

Migration, se necessária, aditiva e sem destruir legado antes da prova.

---

# 31. SUCCESS METRICS

Produto: time-to-understand-case, clicks-to-conversation/document, cases sem next action, contradictions, waits por ator, time-in-wait/phase, takeover e resolution time.

Engenharia: projection p95, API error, cross-tenant denial, reconciliation e N+1.

---

# 32. DEFINITION OF DONE

- [ ] RP0 verde.
- [ ] BLOCO 0 refez medições.
- [ ] Case ontology definida contra repo vivo.
- [ ] Nenhum parallel truth.
- [ ] Fila possui Lista/Quadro sobre mesma source.
- [ ] Casos substitui “Histórico” como conceito de navegação.
- [ ] Case Workspace passa no teste dos 10 segundos.
- [ ] Timeline unificada/paginada.
- [ ] Documentos localizáveis.
- [ ] Conversation deep-link bidirecional.
- [ ] Segurados liga pessoa→casos.
- [ ] Work/Approval/Artifact relacionados.
- [ ] Dois tenants provados.
- [ ] Mutações críticas vermelhas.
- [ ] E2E e red team executados.
- [ ] Performance medida.
- [ ] Mobile/keyboard verificados.
- [ ] Cutover sem duas verdades.
- [ ] Execution report, commit/push e registry.

---

# 33. FORA DE ESCOPO CONSCIENTE

CRM, saved views altamente customizáveis, advanced SLA builder, bulk operations, capacity planner, global full-text de toda conversa, relationship graph, export dossier avançado e persistent Case entity sem necessidade medida.

---

# 34. WARM-UP QUESTIONS

1. HEAD e protocolo vivos?
2. Quais premissas envelheceram?
3. Há Case entity nova?
4. Quantas conversations ativas?
5. Work Runs por conversation?
6. Active waits?
7. Ownership states reais?
8. Resolution reasons reais?
9. Uma situação atravessa múltiplas conversations?
10. Authority de documento/policy/protocolo/notes?
11. p95 da fila?
12. polls por operador?
13. views candidatas não vazias?
14. dados suficientes para deterministic next action?
15. qual defeito real a Candidate não percebeu?
16. qual proposta técnica deve ser recusada?
17. como provar List=Board?

---

# 35. NEXT — SPEC-098: O QUE DEVE SER INVESTIGADO ANTES DE ESCREVER

A próxima SPEC não deve ser apenas “adicionar Soul”. Ela deve mapear a **Identity & Scope Fabric** inteira:

```text
GLOBAL AUTOBROKERS
CORRETORA
TEAM
USER
ENTITY
RUN
THREAD
```

E separar explicitamente:

```text
Company Facts  ≠ Company Soul
User Profile   ≠ Memory
Agent Role     ≠ Company Soul
Scope Context  ≠ Authorization
Authorization ≠ Tool visibility
```

Perguntas que a 098 precisa responder:

- como o usuário multiempresa escolhe a corretora ativa e como isso chega ao FastAPI;
- quantos seams ainda usam `users_v2.company_id`/`session.companyId` diretamente;
- se Team existe como scope real ou apenas como lista de pessoas;
- como Entity/Run/Thread entram sem explodir ACLs;
- como Company Soul é criada, revisada e injetada sem virar conhecimento nem política;
- como User Profile fica scoped à corretora;
- como o agente recebe identidade correta sem novo cérebro;
- como revogação de acesso durante Work Run bloqueia efeito futuro;
- como jobs longos revalidam scope na hora do commit;
- como 099/100/102/110 consumirão o mesmo Scope Context.

**Referências previstas:** Hermes Agent (SOUL/USER/MEMORY/AGENTS), OpenFGA (organization context/relations), LangGraph/LangMem namespaces, Arkon apenas para stale-scope/concurrency hardening.

---

# 36. RESEARCH PACK

Obrigatório: `SPEC-097-a-operacao-tem-uma-casa-RESEARCH-PACK.md`  
SHA-256: `26fda881b20c016d07ff1d9c4b1c04b87bed909a5af5a4a3ca63ab9b89be4ad0`

O Research Pack contém auditoria atual, ResultVision archaeology, adoption ledger, referências externas, Lentes do Dado, alternativas rejeitadas e source index.

---

# 37. LEI FINAL

> **O corretor não deve precisar ler o sistema para entender o atendimento. O sistema deve ler sua própria verdade e apresentar, com clareza, o que aconteceu, onde está, quem está cuidando, de quem depende e o que acontece depois.**
