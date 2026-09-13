# SPEC-097 — RESEARCH PACK
## A OPERAÇÃO TEM UMA CASA
### Operations Workspace · Fila, Casos, Conversas, Segurados e Timeline Operacional

**Produto:** AutoBrokers Intelligence OS  
**Tipo:** COMPANION NORMATIVO DE EVIDÊNCIA — leitura obrigatória junto da Candidate SPEC-097  
**Data da pesquisa:** 03/09/2026  
**Repo atual:** `Amandico100/AutoBrokers-Intelligence-OS`  
**Baseline profundo da pesquisa:** `57f8511228f6ea05bb614daa1ab28deae8a485ba`  
**HEAD reconfirmado na correção documental:** `67506906f0b8f60d89585878f15958a9ea438f09`  
**Repo histórico:** `Amandico100/ResultVision` · `main`  
**Protocolo:** AutoBrokers AAA **v11.2**  
**Candidate SPEC associada:** `SPEC-097-a-operacao-tem-uma-casa.md`

> **OBSERVAÇÃO DE GOVERNANÇA DA PROPOSTA**  
> Esta é uma proposta inicial para a SPEC-097. Serve de insumo e de inspiração para criarmos uma SPEC definitiva.  
> A SPEC definitiva pode ser modelada, melhorada e modificada em tudo que for melhor para o projeto.  
> Esta observação vale para todas as propostas de SPEC produzidas por esta Foundry.

---

# 0. CONTRATO DE LEITURA — ESTE DOCUMENTO NÃO É OPCIONAL

Este Research Pack faz parte da unidade de execução da SPEC-097.

A SPEC define principalmente:

```text
O QUE construir
POR QUE construir
LIMITES
AUTORIDADES
CONTRATOS
GATES
TESTES
DEFINITION OF DONE
```

Este Research Pack define principalmente:

```text
DE ONDE vieram as ideias
O QUE existe de verdade no repo
O QUE existia no ResultVision
O QUE produtos externos fazem
O QUE foi adotado
O QUE foi adaptado
O QUE foi rejeitado
QUAL evidência sustenta cada decisão
QUAL é a qualidade da fonte
```

> **A SPEC-097 e este Research Pack formam um único pacote lógico. Ler apenas um deles significa ler o trabalho pela metade.**

## Gate RP0 — Research Pack Receipt

Antes de warm-up, design ou código, o executor registra:

```text
RP0_RESEARCH_PACK_READ = YES
RP0_CURRENT_REPO_SOURCES = [...]
RP0_RESULTVISION_SOURCES = [...]
RP0_EXTERNAL_SOURCES = [...]
RP0_ADOPTION_LEDGER_ACKNOWLEDGED = YES
RP0_STALE_OR_CONTRADICTED_PREMISES = [...]
RP0_DATA_LENS_ACKNOWLEDGED = YES
```

**RP0 falhou → não codificar.**

O executor não precisa concordar com este Research Pack. Precisa lê-lo, confrontá-lo com o `main` vivo e discordar com evidência.

---

# 1. POR QUE A SPEC-097 EXISTE

O AutoBrokers evoluiu de uma aplicação centrada em atendimento para um Intelligence OS com Smith/LangGraph, Work OS, Work Runs, handoff humano↔IA, waits, follow-up, corredores, Atlas, Research, Artifacts, Intelligence Fabric e Claims Learning Shadow.

A camada operacional do dashboard não evoluiu com a mesma profundidade.

Hoje existem superfícies reais para:

```text
Fila
“Histórico”
Conversas
Segurados
Ficha
```

mas elas ainda não apresentam todo o estado operacional moderno como **uma história inteligível do atendimento**.

A pergunta da SPEC é:

> **Se um corretor abrir o AutoBrokers agora e quiser saber o que está acontecendo, o que aconteceu e o que precisa acontecer em cada atendimento, ele consegue responder isso em segundos?**

O produto precisa permitir que uma pessoa que não acompanhou o atendimento desde o início descubra:

1. quem é o segurado;
2. o que ele pediu;
3. qual apólice/seguradora está envolvida;
4. em que fase está;
5. quem tem a posse agora;
6. se a IA está trabalhando ou esperando;
7. de quem estamos esperando;
8. qual é a próxima ação;
9. quais documentos entraram e saíram;
10. quais conversas ocorreram;
11. quais ações o AutoBrokers executou;
12. quais ações humanas ocorreram;
13. se existe aprovação pendente;
14. se existe protocolo;
15. se há trabalho em andamento;
16. se terminou;
17. como terminou;
18. quanto tempo ficou parado;
19. por que merece atenção;
20. onde está a evidência.

---

# 2. TESE DE PRODUTO

A 097 não cria CRM genérico nem help desk genérico.

Ela cria a:

# **CAMADA DE LEITURA E CONTROLE DA OPERAÇÃO DA CORRETORA**

Estrutura mental:

```text
FILA
= o que precisa de atenção agora

CASO
= a situação de negócio completa

CONVERSA
= a comunicação

SEGURADO
= a pessoa e seu histórico operacional

WORK RUN
= trabalho durável executado sobre a situação

TIMELINE
= o que aconteceu entre cliente, IA, humano, seguradora e sistemas

DOCUMENTOS
= evidência ligada à história

NEXT ACTION
= o que deve acontecer a seguir
```

---

# 3. DISTINÇÃO CRÍTICA — “CASO” DE PRODUTO ≠ TABELA LEGADA

A SPEC-043 e a SPEC-046 fizeram uma escolha arquitetural correta para o runtime moderno: não ressuscitar `attendance_cases` como autoridade.

A verdade moderna se distribui por authorities reais:

```text
conversation
messages
attendance_sessions
attendance_executions
dispatch
handoff / ownership
resolution
work_runs
work_events
work_waits
approvals
artifacts
documents / media / evidence
```

A SPEC-093-B mediu em produção em 03/09/2026 que não havia tabela canônica de case/claim de atendimento e que a tela “casos” era uma view derivada de `conversations + attendance_sessions`; também mediu que Work Runs já carregam `conversation_id` e que `work_events`/`work_waits` já formam parte importante do ledger operacional.

Por isso:

# **CASO NASCE COMO PRODUCT/READ MODEL. NÃO COMO NOVA FONTE DE VERDADE PARALELA.**

Uma entidade persistente fina só será criada se o warm-up provar necessidade real, especialmente quando uma única situação de negócio atravessar múltiplas conversas e múltiplos Work Runs.

---

# 4. FONTES INTERNAS — AUTOBROKERS ATUAL

## 4.1 Protocolo AAA v11.2

`docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`

O HEAD reconfirmado confirmou v11.2 com:
- profundidade máxima no ponto certo;
- **Lente do Dado**;
- pares mínimos;
- conserto salvo completo;
- Candidate Specs;
- gates;
- mutation;
- E2E;
- blocker test;
- referências externas;
- context diet.

A 097 toca UI, API, read models, multi-tenant, Work OS, documentos, ownership e estado operacional. A Lente do Dado é obrigatória.

## 4.2 SPEC-043 — Central de Atendimentos

`docs/canon/specs/SPEC-043-central-atendimentos-corretor-mobile.md`

Princípios que permanecem:
- Atendimentos = operação, não configuração;
- mobile-first;
- linguagem humana;
- progressive disclosure;
- **Fila → Detalhe → Ação**;
- não reviver `attendance_cases`;
- conversation/session/execution/timeline como bases vivas.

## 4.3 SPEC-046 — Ficha do Atendimento

`docs/canon/specs/SPEC-046-ficha-atendimento-limpeza-admin.md`

Já pretendia uma ficha com:
- identificação;
- resumo;
- seguradora;
- apólice;
- corredor;
- estado;
- documentos;
- notas;
- timeline;
- auditoria leve.

A 097 não descarta essa direção. Ela a transforma num **Case Workspace** compatível com tudo que surgiu depois.

---

# 5. NAVEGAÇÃO ATUAL

`app/dashboard/atendimentos/page.tsx` usa ModuleIndex.

`lib/mock/tenant-modules.ts` hoje define:

```text
Fila      → /dashboard/atendimentos/fila
Histórico → /dashboard/atendimentos/casos
Conversas → /dashboard/atendimentos/conversas
Segurados → /dashboard/atendimentos/segurados
```

Há uma contradição semântica:

```text
rota = casos
nome visível = Histórico
```

“Histórico” é dimensão temporal. “Caso” é unidade operacional.

### Recomendação

```text
Atendimentos
├── Fila
├── Casos
├── Conversas
└── Segurados
```

Em Casos:

```text
Ativos | Encerrados | Todos
```

Histórico passa a ser uma dimensão dentro do Caso/timeline, não um pilar principal.

---

# 6. FILA ATUAL

`app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx`

É uma lista agrupada por stages:

```text
precisa_de_voce
acionando
monitorando
protocolo
em_conversa
com_equipe
observacao
concluido
```

Pontos bons:
- urgência primeiro;
- linguagem humana;
- stage canônico;
- protocolo;
- click abre Ficha;
- concluídos do dia separados;
- mobile-first.

Lacunas para o produto atual:
- só uma projeção em lista;
- não apresenta waits/ownership/Work/approval como dimensões próprias;
- comparação visual limitada;
- sem views de atenção;
- sem Board/Kanban;
- sem SLA/tempo em estado como first-class;
- next action pouco explícita;
- poucos filtros operacionais.

---

# 7. “HISTÓRICO” ATUAL

`app/dashboard/atendimentos/casos/HistoricoClient.tsx`

Hoje:
- título “Histórico de atendimentos”;
- filtros Todos, Em andamento, Precisa de você, Acionamentos, Concluídos;
- busca cliente/telefone/protocolo;
- click abre Ficha.

Problema:
> a área chamada “Histórico” contém inclusive coisas em andamento e ocupa a rota `/casos`.

Ela não é um Case Workspace; é uma lista cronológica/operacional.

---

# 8. FICHA ATUAL — A BASE É MELHOR DO QUE PARECE

`app/dashboard/atendimentos/ficha/[conversaId]/FichaClient.tsx`

Já contém:
- cliente/telefone;
- stage;
- protocolo;
- `assumido_por`;
- ações de abrir conversa/assumir/ver seguradora;
- “O que aconteceu”;
- apólice;
- seguradora/produto/vigência;
- veículo;
- timeline;
- anexos;
- dossiê;
- contagem de mensagens.

Logo o problema não é “não temos dados”.

O problema é:
- organização;
- navegação;
- integração com authorities mais novas;
- legibilidade de estado;
- ownership;
- waits;
- Work Run;
- approvals;
- next action;
- documentos como evidência operacional.

---

# 9. CONVERSAS ATUAL

`app/dashboard/atendimentos/conversas/ConversasClient.tsx`

Já possui uma direção boa:
- lista + thread;
- linha de posse;
- Você atendendo / colega / aguardando humano / equipe pelo WhatsApp / IA;
- Assumir;
- Devolver à IA;
- Encerrar;
- espelho da seguradora;
- deep links.

Regra da 097:
> **Conversas continua communication-first. Não vira o Case Workspace.**

Mas Case e Conversation precisam ser navegáveis nos dois sentidos.

---

# 10. SEGURADOS ATUAL

`app/dashboard/atendimentos/segurados/SeguradosClient.tsx`

Hoje é uma visão leve:
- nome/telefone;
- número de atendimentos;
- último contato;
- histórico que abre Ficha.

Regra:
> **Segurados não vira CRM.**

Evolução útil:
- apólices relevantes;
- casos ativos;
- últimos casos;
- documentos/interações recentes;
- links para o Case Workspace.

---

# 11. SPEC-086 — FIM E ESPERA AGORA EXISTEM COMO VERDADE

`docs/canon/reports/SPEC-086-EXECUTION-REPORT.md`

A execução mediu que, antes da SPEC, havia 671 conversas e nenhuma marcada como resolvida.

Depois consolidou:
- `resolvido_em`;
- `resolucao_motivo`;
- `work_waits`;
- waits por humano/cliente/seguradora;
- satisfação/expiração;
- watchdog;
- contadores de terminado/esperando/morreu esperando.

Implicação:
> a 097 não pode usar `conversation.status` isoladamente para afirmar que um caso terminou ou está esperando.

---

# 12. SPEC-093-B — O LEDGER OPERACIONAL EVOLUIU

`docs/canon/specs/SPEC-093-B-o-sinistro-deixa-rastro.md`

Medições relevantes:
- nenhuma tabela canônica `case` de atendimento;
- Work Runs têm `conversation_id`;
- `work_events` têm ator/tipo/mensagem humana/payload redacted;
- `work_waits` modela dependências temporais;
- media/evidence existe em volume;
- Claims Shadow transforma trabalho humano em rastro estruturado.

Implicação:
> **Timeline do Case deve projetar events existentes; não criar um segundo event log.**

---

# 13. RESULTVISION — COMO USAR O LEGADO

Repo: `Amandico100/ResultVision`

O ResultVision é:

# **ARQUEOLOGIA DE PRODUTO, NÃO AUTORIDADE ARQUITETURAL.**

Cada ideia recebe:

```text
PRESERVAR
ADAPTAR
REJEITAR
```

Objetivo:
```text
recuperar clareza
sem recuperar acoplamento antigo
```

# 14. RESULTVISION — NAVEGAÇÃO

`client/src/App.tsx`

Rotas relevantes:

```text
/fila
/board → /fila?view=kanban
/conversations
/clients
/history
/timeline
/followups → /fila?tab=retornos
/exceptions → /fila?tab=travados
/evidence → /fila?tab=documentos
```

Insight importante:

> necessidades diferentes de operação convergiam para uma fila com views/tabs, sem transformar cada sinal em item permanente de menu.

### Veredito
**ADAPTAR.**

Não copiar os tabs literalmente. Recuperar o princípio.

---

# 15. RESULTVISION — WORK QUEUE

`client/src/pages/work-queue.tsx`

Existia:

```text
Tabs:
Todos
Travados
Retornos
Documentos
Áudios

Views:
Kanban
Lista

Filters:
tipo de serviço
ramo
busca
```

Também agregava source types:

```text
case
followup
exception
evidence
audio
```

## O que era bom
- List/Board no mesmo espaço.
- Atenção operacional agrupada.
- Documento/retorno não exigia trocar de módulo.
- Busca e filtros úteis.

## O que era perigoso
A própria UI possuía heurísticas como:

```text
inferServiceType()
inferInsuranceBranch()
```

com base em strings.

### Veredito
- `Lista | Quadro`: **PRESERVAR/ADAPTAR**
- views de atenção: **PRESERVAR/ADAPTAR**
- heurística textual como truth: **REJEITAR**
- mistura de sources sem autoridade de tipo: **ADAPTAR**

---

# 16. RESULTVISION — BOARD / KANBAN

`client/src/pages/board.tsx`

Havia:
- colunas;
- cards;
- status;
- tipo;
- cliente;
- seguradora;
- waiting-on;
- alertas;
- corredor/autonomia;
- detalhes;
- sequência operacional;
- bloqueio;
- próximo movimento.

Um detalhe de desenho é particularmente bom:

> o próprio código pausava drag-and-drop de cases enquanto as mutations seguras não estavam consolidadas.

### Veredito
**ADAPTAR FORTEMENTE.**

Na 097:

```text
Board = projection
Authority/state machine = truth
```

Drag somente para transições:
- autorizadas;
- semanticamente válidas;
- auditáveis;
- idempotentes.

---

# 17. RESULTVISION — CASE DRAWER

`client/src/components/work-queue/case-drawer.tsx`

Estrutura:
- header/protocolo/severity;
- Conversar / Documentos / Caso completo;
- status box;
- tabs `O que fazer` e `Atendimento`;
- Aguardando;
- Etapa;
- Tipo;
- Canal;
- checklist;
- resumo;
- dados faltantes;
- bloqueio;
- docs;
- retornos;
- problemas.

O conceito mais valioso é:

# **“O QUE FAZER”**

Na 097 ele evolui para:

# **AGORA**

```text
Situação atual
Quem está com o caso
Aguardando quem
Por que está parado
Próxima ação
Prazo/tempo
```

### Veredito
**PRESERVAR A IDEIA, NÃO O COMPONENTE.**

---

# 18. RESULTVISION — CASE 360

`client/src/pages/history.tsx`

A página era chamada **Casos** e tinha master-detail:

```text
lista lateral
search
caso selecionado
Case 360

Tabs:
Resumo
Conversa
Documentos
Histórico
```

Também ligava:
- follow-ups;
- exceptions;
- evidence;
- activity;
- protocol execution;
- live assist.

### Pontos fortes
- contexto sem navegar por páginas;
- busca;
- case selecionado no URL;
- conversa/documentos/histórico relacionados;
- leitura operacional em uma casa.

### O que não copiar
- ontology antiga;
- `Case 360` como nome obrigatório;
- excesso de detalhe técnico;
- dados de runtime internos demais.

### Veredito
**ADAPTAR FORTEMENTE.**

É uma das melhores referências internas de UX.

---

# 19. RESULTVISION — CONVERSATIONS

`client/src/pages/conversations.tsx`

Possuía:
- list + thread;
- status/handoff/assigned/period/sort/tag filters;
- case link;
- internal note;
- assignment;
- attachments;
- paginação de mensagens;
- details panel.

### Veredito
**ADAPTAR SELETIVAMENTE.**

A Conversas atual do AutoBrokers já é mais coerente com a arquitetura moderna.

Não substituí-la pela antiga.

---

# 20. RESULTVISION — CLIENTS / SEGURADOS

`client/src/pages/clients.tsx`

Mostrava:
- segurado;
- seguradora;
- apólice;
- protocolo;
- tipo;
- etapa;
- waiting-on;
- update;
- documentos;
- abrir atendimento.

### Veredito
**ADAPTAR.**

Insight:
> o perfil do segurado deve servir para navegar pela operação, não apenas funcionar como agenda.

---

# 21. MATRIZ DE ARQUEOLOGIA

| Ideia antiga | Veredito | Evolução na 097 |
|---|---|---|
| Kanban | **ADAPTAR** | `Lista / Quadro` sobre o mesmo read model |
| Drag-and-drop | **RESTRINGIR** | apenas state transitions autorizadas |
| Lista operacional | **PRESERVAR** | default de alto volume |
| Travados/Retornos/Docs | **ADAPTAR** | views de atenção |
| Case Drawer | **ADAPTAR** | Quick Case Preview |
| “O que fazer” | **PRESERVAR** | bloco `Agora` |
| Case 360 | **ADAPTAR** | Case Workspace |
| Conversation ↔ Case | **PRESERVAR** | deep link bidirecional |
| Documents no case | **PRESERVAR** | evidence first-class |
| Cliente+seguradora+apólice no card | **PRESERVAR** | facts essenciais |
| waiting-on | **PRESERVAR** | Work Wait / authority atual |
| alerts | **ADAPTAR** | attention reasons |
| checklist | **ADAPTAR** | milestones reais apenas |
| inferência de ramo/tipo na UI | **REJEITAR** | facts/authorities |
| tickets fallback | **REJEITAR** | sem dual truth |
| status arbitrário | **REJEITAR** | transition contract |
| dashboard carregado de KPIs | **REJEITAR** | operação limpa |
| raw protocol internals | **REJEITAR** | progressive disclosure |

---

# 22. REFERÊNCIA EXTERNA — INTERCOM INBOX

Documentação oficial consultada:

- https://www.intercom.com/help/en/articles/6258745-the-inbox-explained
- https://www.intercom.com/help/en/articles/6588834-organize-your-inbox-with-custom-views-and-folders
- https://www.intercom.com/help/en/articles/6561699-assign-conversations-to-teammates-and-teams
- https://www.intercom.com/help/en/articles/6546152-set-slas-for-conversations-and-tickets
- https://www.intercom.com/help/en/articles/13334840-conversation-events-in-the-inbox

Padrões:
```text
Unassigned
Assigned
custom views
filters
SLA
waiting
assignment
conversation events
AI events
```

### Adotamos
1. Views por atenção.
2. Ownership explícito.
3. SLA/urgência visível na lista.
4. Timeline/eventos filtráveis.
5. “Todos” como view, não como estado.

### Não adotamos
- inbox genérica como ontology;
- ticket de suporte como core;
- workflow configurável complexo no workspace.

---

# 23. REFERÊNCIA EXTERNA — FRONT

Documentação oficial:

- https://help.front.com/en/articles/2344
- https://help.front.com/en/articles/2256
- https://help.front.com/en/articles/2243
- https://help.front.com/en/articles/2099
- https://help.front.com/en/articles/2057

Padrões:
```text
one clear owner
shared inbox
internal comments
views
custom fields
rules
```

### Adotamos
- owner humano claro;
- nota interna privada;
- views;
- contexto sem poluir conversa.

### Rejeitamos
- email-first;
- custom field livre como domain model;
- tags como state authority.

---

# 24. REFERÊNCIA EXTERNA — ZENDESK

Documentação oficial:

- https://support.zendesk.com/hc/en-us/articles/4408836526362-Using-the-context-panel
- https://support.zendesk.com/hc/en-us/articles/4408828503450-Configuring-the-context-panel-in-the-Zendesk-Agent-Workspace
- https://support.zendesk.com/hc/en-us/articles/4408829170458-Viewing-customer-context-for-user-history-and-device-information
- https://support.zendesk.com/hc/en-us/articles/4408832852122-Viewing-and-understanding-SLA-targets

Padrões:
```text
ticket + customer context
interaction history
SLA in view/detail
context without leaving work
```

### Adotamos
- context rail;
- histórico do cliente;
- SLA/tempo em atenção.

### Rejeitamos
- formulário denso;
- dezenas de campos sempre visíveis;
- burocracia de ticket.

---

# 25. REFERÊNCIA EXTERNA — SALESFORCE SERVICE CLOUD

Fontes oficiais:

- https://help.salesforce.com/s/articleView?id=service.cases_set_up_and_manage_the_case_timeline.htm
- https://help.salesforce.com/s/articleView?id=service.case_interaction_overview.htm
- https://help.salesforce.com/s/articleView?id=service.case_interaction_case_detail_page.htm
- https://help.salesforce.com/s/articleView?id=service.omnichannel_routing_targets.htm

Padrões:

## Case Timeline
Uma visão unificada/curada substitui feeds e related lists fragmentados.

Pode reunir:
```text
conversation events
case history
milestones
documents
voice
tasks
```

## Case Feed / Highlights
Reúne:
- emails;
- calls;
- comments;
- status;
- files;
- milestones;
- tasks.

## Omni-Channel
Roteia trabalho para:
```text
queue
rep
skill
AI agent
bot
```

### Adotamos
- unified timeline;
- highlights/top facts;
- distinção case vs routed work.

### Rejeitamos
- CRM object explosion;
- field-heavy page;
- omnichannel engine genérico agora.

---

# 26. REFERÊNCIA EXTERNA — SERVICENOW CSM

Fontes oficiais:

- https://www.servicenow.com/docs/r/customer-service-management/csm-config-workspace-interface.html
- https://www.servicenow.com/docs/r/customer-service-management/csm-playbooks-using-activity-stream.html
- https://www.servicenow.com/docs/r/api-reference/rest-apis/case-api.html

Padrões:
```text
complete customer history
record details
activity stream
work notes
comments
emails
attachments
field changes
filters
```

### Adotamos
- activity/timeline unificada;
- nota interna distinta de comunicação;
- filtros de activity;
- contexto enquanto opera.

### Rejeitamos
- formulário enterprise pesado;
- generic task-table;
- ruído de field changes por default.

---

# 27. REFERÊNCIA EXTERNA — LINEAR

Fontes oficiais:

- https://linear.app/docs/display-options
- https://linear.app/docs/board-layout
- https://linear.app/docs/custom-views
- https://linear.app/docs/peek
- https://linear.app/docs/search
- https://linear.app/docs/assigning-issues

Padrões:
```text
same data → list or board
saved views
grouping
filtering
display properties
peek
search
single assignee
compact density
```

### Adotamos
- lista/board como projeções;
- views;
- propriedades de display;
- peek;
- ownership claro.

### Rejeitamos
- issue/developer semantics;
- drag arbitrário como business truth;
- shortcuts como P0.

---

# 28. REFERENCE ADOPTION LEDGER

| Fonte | Padrão | Decisão | AutoBrokers |
|---|---|---|---|
| SPEC-043 | Fila→Detalhe→Ação | ADOPT | backbone |
| SPEC-046 | Ficha agregada | ADAPT | Case Workspace |
| SPEC-086 | waits/resolution | ADOPT | operational truth |
| SPEC-093-B | Work event ledger | ADOPT | timeline |
| ResultVision WorkQueue | List/Kanban | ADAPT | uma fila, duas views |
| ResultVision CaseDrawer | “O que fazer” | ADAPT | Agora |
| ResultVision History | Case 360 | ADAPT | master-detail |
| ResultVision Clients | docs/apólice/caso | ADAPT | Segurados |
| Intercom | attention views | ADOPT | official views |
| Intercom | SLA | ADAPT | time/urgency |
| Front | one owner | ADOPT | human ownership |
| Front | internal comments | ADAPT | Notas |
| Zendesk | context panel | ADAPT | context rail |
| Salesforce | unified timeline | ADOPT | Operational Timeline |
| Salesforce | highlights | ADOPT | Agora + facts |
| ServiceNow | activity filters | ADOPT | timeline filters |
| Linear | list/board same data | ADOPT | toggle |
| Linear | peek | ADAPT | Quick Case Preview |
| generic help desk | ticket form | REJECT | — |
| old tickets | authority | REJECT | — |
| tags as state | lifecycle | REJECT | — |

---

# 29. ONTOLOGIA RECOMENDADA

## Case
A situação de negócio que precisa chegar a um desfecho e ser compreendida como unidade.

## Conversation
Thread de comunicação associada.

Pode haver mais de uma:
```text
segurado
seguradora
operador
outro canal
```

## Work Run
Trabalho durável executado sobre o Case.

## Wait
Dependência temporal explícita.

## Ownership
Quem possui comunicação/decisão operacional agora.

## Approval
Decisão humana obrigatória antes de efeito.

## Document
Evidência recebida, enviada ou gerada.

## Artifact
Entregável versionado.

## Timeline Event
Evento humano que explica o que aconteceu.

## Next Action
Próximo movimento derivado de state/work/wait/policy.

---

# 30. O QUE CASE NÃO É

Case não é:
```text
ticket genérico
conversation
Work Run
agent
CRM contact
workflow
pasta de documentos
```

Ele relaciona essas dimensões sem duplicar suas authorities.

# 31. CASE READ MODEL — CANDIDATE

Shape semântica:

```text
case_ref
company_id

primary_conversation_id
conversation_refs[]

customer_ref
insured_display
phone_display

policy_ref
policy_number_display
insurer_ref
insurer_display
insurance_line

request_summary
service_type

current_phase
operational_status
resolution_status
resolution_reason

ownership
owner_user_ref
owner_display

waiting_on
wait_since
wait_due_at

attention_level
attention_reasons[]
sla_state
time_in_state

next_action
next_action_actor

protocol
last_external_result

latest_activity_at
opened_at
resolved_at

message_count
document_count
work_run_count
pending_approval_count

active_work_refs[]
document_refs[]
artifact_refs[]
```

Não é prescrição de migration. O warm-up reduz/reusa o que já existe.

---

# 32. READ MODEL, NÃO SNAPSHOT GIGANTE

Evitar copiar para uma nova row:
- cliente inteiro;
- apólice inteira;
- mensagens;
- Work Runs;
- documentos;
- approvals.

Preferir:
```text
refs
+
minimal display snapshot quando história exige
```

---

# 33. FILA — OBJETIVO

Responder:

> **O que merece minha atenção agora?**

Não:
> “mostre tudo numa lista enorme”.

Candidate official views:

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
SLA em risco
Travados
```

A lista final depende da distribuição real.

Não criar view decorativa que permanece vazia.

---

# 34. FILA — LISTA E QUADRO

```text
[ Lista ] [ Quadro ]
```

Mesma query/read model.

## Lista
Melhor para:
- volume;
- busca;
- sorting;
- densidade;
- comparação horizontal.

## Quadro
Melhor para:
- distribuição;
- gargalo;
- acúmulo por fase;
- visão espacial.

Preferência pode ser persistida por usuário.

Recomendação P0:
- Lista como default operacional de alto volume.
- Quadro/Kanban disponível com um clique.

---

# 35. BOARD — COLUNAS NÃO PODEM MISTURAR DIMENSÕES

Errado:

```text
IA
Esperando cliente
Em andamento
Com humano
```

porque mistura owner, wait e phase.

Candidate P0 de “situação”:

```text
Novo / Entendendo
Em trabalho
Aguardando externo
Precisa de humano
Pronto para fechar
```

`Encerrado` vive fora do active board.

Outros groupings podem vir depois:
```text
owner
insurer
service
SLA
```

---

# 36. DRAG-AND-DROP

Regra:

# **A UI nunca muda a verdade só porque o usuário arrastou um card.**

Drag só existe quando corresponde a command real.

Exemplo aceitável:
```text
Precisa de humano
→ Assumir
```
se a authority de claim aceita.

Exemplo não aceitável:
```text
Aguardando seguradora
→ Concluído
```
sem evidência/desfecho.

Se não houver command seguro:
- card não é draggable;
- ou drop abre ação/confirm.

---

# 37. CASE LIST — SCAN FIELDS

Candidate:
- segurado;
- pedido;
- seguradora;
- apólice;
- fase;
- owner;
- waiting-on;
- next action;
- última atividade;
- tempo no estado;
- SLA/urgência;
- docs;
- reason de atenção.

Não mostrar tudo simultaneamente.

Display/density pode adaptar padrão Linear.

---

# 38. CASE WORKSPACE — TESTE DOS 10 SEGUNDOS

Topo deve responder:

```text
QUEM?
O QUÊ?
ONDE ESTÁ?
QUEM TEM?
ESPERANDO QUEM?
O QUE FAZER?
```

Exemplo conceitual:

```text
JOÃO DA SILVA · Assistência Auto
Porto · apólice 123...
────────────────────────────────

AGORA
Aguardando a seguradora há 1h42
IA acompanha automaticamente
Próxima ação: consultar retorno às 14:30
Dentro do prazo

Protocolo: 849320
```

---

# 39. CASE WORKSPACE — ESTRUTURA

Recomendação:

```text
HEADER
AGORA / CURRENT STATE
QUICK ACTIONS

Timeline      ← default
Conversas
Documentos
Dados
Trabalhos
Notas
```

No desktop, facts estáveis podem morar num context rail.

No mobile, sections/tabs progressivas.

---

# 40. QUICK CASE PREVIEW

Inspirado no CaseDrawer/Linear Peek.

Fila → click leve pode abrir preview:

```text
Agora
próxima ação
owner
wait
protocol
docs count
Abrir caso completo
```

Não carregar toda timeline.

Se a navegação direta para Case Workspace for suficientemente rápida/boa, o peek pode ser deferido.

---

# 41. TIMELINE OPERACIONAL

Unifica projeções úteis de:

```text
mensagem segurado
mensagem IA
mensagem humana
mensagem/retorno seguradora
dispatch
Work Run milestone
Work Wait abriu/satisfeito/expirou
handoff
ownership
approval
document received
document sent
protocol
Artifact
follow-up
resolution
```

Não é novo event store.

---

# 42. TIMELINE NÃO É LOG TÉCNICO

Default humano:

```text
10:14 · Segurado enviou uma foto
10:15 · AutoBrokers identificou a apólice
10:17 · Seguradora acionada
10:23 · Protocolo recebido: 12345
10:24 · Aguardando prestador
11:02 · Ana assumiu o atendimento
```

Não:
```text
LangGraph node
tool call
Redis
worker lease
Qdrant
SQL
raw webhook
```

---

# 43. TIMELINE FILTERS

Candidate:

```text
Tudo
Conversas
Ações
Documentos
Humano
IA
Seguradora
Interno
```

Só habilitar filtro quando event type/provenance é confiável.

---

# 44. DOCUMENTOS — PRIMEIRA CLASSE

O usuário explicitamente precisa encontrar documentação rapidamente.

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

Cada item:
- nome/tipo;
- preview;
- origem;
- quem enviou;
- quando;
- status de extração;
- destination quando outbound;
- event relation.

---

# 45. DOCUMENTO TAMBÉM APARECE NA TIMELINE

Mesmo objeto, duas projeções:

```text
Documents → arquivo
Timeline  → “Segurado enviou foto do veículo”
```

Não duplicar bytes.

---

# 46. CONVERSAS

Case Workspace pode:
- resumir threads;
- mostrar mensagens recentes;
- abrir thread do segurado;
- abrir thread da seguradora;
- navegar à Central de Conversas.

Não é obrigatório duplicar composer completo no Case P0.

Regra:
> **Conversation surface owns comunicação; Case surface owns compreensão/coordenação.**

---

# 47. SEGURADOS

Visão candidate:

```text
nome/telefone
apólices relevantes
casos ativos
últimos casos encerrados
última interação
documentos recentes
```

Click:
```text
Segurado → Caso → Case Workspace
```

Não:
- funil comercial;
- lead score;
- CRM fields arbitrários.

---

# 48. NOTAS INTERNAS

Padrões Front/ServiceNow reforçam:

```text
comunicação externa ≠ nota interna
```

AutoBrokers precisa de nota first-class:
- privada para a corretora;
- autor/data;
- relacionada ao case;
- timeline interna;
- auditável;
- não enviada externamente.

Se hoje há mecanismos diferentes/prefixos, warm-up consolida sem duplicar writer.

---

# 49. OWNERSHIP

Consumir a authority moderna da continuidade/handoff.

Estados conceituais:

```text
AI_OWNED
HUMAN_REQUESTED
HUMAN_OWNED
WAITING_EXTERNAL
RESUMING_AI
RESOLVED
```

O warm-up usa nomes efetivamente implementados.

Não criar uma nova state machine só para UI.

---

# 50. ATTENTION ≠ STATUS

Attention é derivada.

Candidate reasons:

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
```

Exemplo:
```text
status = running
attention = high
```

Isso é normal.

---

# 51. NEXT ACTION — ORDEM DE AUTORIDADE

A informação mais importante do workspace.

Precedência candidate:

1. ação humana obrigatória;
2. approval pendente;
3. Work Run state;
4. active wait;
5. dispatch/corridor next step;
6. follow-up vencido;
7. policy/deterministic next action.

LLM pode sugerir depois:

```text
Sugestão do AutoBrokers
```

mas não substituir authority.

---

# 52. SLA / TIME IN STATE

Intercom/Zendesk validam:
- SLA visível na fila;
- ordenar pelo target próximo;
- waiting pode pausar certos timers.

P0 AutoBrokers não precisa de engine enterprise de SLA.

Pode começar por:
```text
tempo em espera
tempo na fase
overdue segundo policy existente
```

e deixar contrato para SLA configurável futuro.

---

# 53. SEARCH

Busca operacional deveria encontrar por:

```text
segurado
telefone
apólice
seguradora
protocolo
service/request
case ref
```

Busca full-text da conversa:
- avaliar índices;
- custo;
- privacy;
- volume;
- tenancy.

Não fazer LIKE irrestrito em milhões de mensagens como solução rápida.

---

# 54. REALTIME

Hoje há polling com frequências diferentes nas telas.

097 deve medir:
- queries por operador;
- volume;
- atraso real.

Caminhos:
- Supabase Realtime;
- server events;
- polling fallback.

Realtime é atualização; não authority.

---

# 55. PERFORMANCE

Objetivos:
- Fila mostra dados úteis rápido;
- Case abre `Agora` antes da timeline completa;
- timeline pagina;
- documents lazy;
- conversations lazy;
- Work detail lazy.

Não carregar em cada card:
```text
todas mensagens
todos Work Events
todos docs
```

---

# 56. SECURITY / TENANCY

O Case agrega múltiplos domínios, aumentando superfície de IDOR.

Contrato:

```text
authenticated principal
→ derive company
→ resolve case/read model within company
→ resolve each related ref within same company
```

UUID não é autorização.

Testar:
- conversation B;
- Work Run B;
- Approval B;
- Artifact B;
- document B;
- case synthetic B.

---

# 57. PRIVACY / LGPD

No tenant dashboard, PII necessária pode aparecer segundo policy atual.

Mas:
- platform logs;
- learning;
- analytics;
- admin global;
- cross-tenant aggregates
devem respeitar redaction/provenance.

Timeline precisa de visibility/event classification.

---

# 58. LENTE DO DADO — STATUS DO CASE

```text
OBJECTIVE
dizer onde o caso está.

SOURCES
resolution
dispatch
attendance state
Work Run
active wait
ownership

OPTIONS
copy status into new case table
vs derive projection

DECISION
derive under precedence contract;
materialize only if performance proves need.

GAINS
no dual truth.

TRADEOFFS
projection complexity.

REQUIREMENTS
tenant/ref/time/provenance.

VISIBILITY
tenant.
```

---

# 59. LENTE DO DADO — DOCUMENTOS

```text
OBJECTIVE
mostrar evidência do atendimento.

SOURCES
message media
attendance media/transcript metadata
document/evidence authorities
Artifacts

DECISION
Document Projection with refs/provenance.

DO NOT
copy bytes into case.
```

---

# 60. LENTE DO DADO — NEXT ACTION

```text
OBJECTIVE
dizer o que fazer agora.

SOURCES
ownership
approval
Work
wait
dispatch/corridor
follow-up

DECISION
deterministic precedence first.

AI
se existir, separately labelled suggestion.

RISK
wrong action in UI.
```

---

# 61. LENTE DO DADO — CASE IDENTITY

Pergunta:
> o que identifica um Case quando não existe table Case?

Options:

## A — Conversation ID
Pró: já existe.
Contra: uma situação pode atravessar threads.

## B — Work Run ID
Rejeitar: trabalho ≠ situação.

## C — Synthetic Case Read Ref
Exemplo:
```text
case:{primary_conversation_id}
```
com resolver/projection.

## D — New thin `operational_cases`
Só se dado real exigir vida própria.

Recomendação inicial:
# **C**

Mover para D somente se warm-up provar multi-conversation/multi-work lifecycle que não cabe de forma segura em refs.

---

# 62. QUANDO UMA ENTIDADE CASE PERSISTENTE SE JUSTIFICA

Se fatos:
- pertencem à situação;
- não pertencem à conversation;
- não pertencem ao Work Run;
- precisam sobreviver a troca de channel/thread.

Exemplo:
```text
um sinistro
→ WhatsApp segurado
→ conversa seguradora
→ ligação
→ múltiplos Work Runs
→ um único lifecycle
```

Se isso já acontece de forma relevante, criar entidade **fina**.

Nunca importar schema legacy `attendance_cases`.

---

# 63. DATA PRECEDENCE CONTRACT — CANDIDATE

```text
RESOLUTION
conversation resolution authority

OWNERSHIP
claim/handoff authority

WAIT
active work_wait

WORK
active Work Run(s)

PHASE
dispatch / attendance state

REQUEST
structured service facts;
fallback safe summary

CUSTOMER/POLICY
InfoCap/canonical authority

DOCUMENTS
evidence/media authorities
```

Se duas fontes contradizem:
- não escolher silenciosamente;
- projection marca contradiction/unknown;
- observability registra.

---

# 64. FAILURE MODES

1. Case em duas colunas.
2. Encerrado continua ativo.
3. Humano possui, UI diz IA.
4. Esperando seguradora, UI diz cliente.
5. Work falhou, Case parece saudável.
6. Documento enviado desaparece.
7. Documento cross-tenant.
8. Protocolo de outro dispatch.
9. Resumo stale.
10. Next action stale.
11. Drag corrompe state.
12. Realtime reordena enquanto usuário lê.
13. Search vaza tenant.
14. Case abre conversation errada.
15. Closed case perde timeline.
16. Approval resolvido continua pendente.
17. Artifact de outro run aparece.
18. Wait expirado não gera attention.
19. Ownership transition duplica action.
20. List e Board mostram estados diferentes.

---

# 65. MÉTRICAS DE PRODUTO

```text
time_to_understand_case
clicks_to_conversation
clicks_to_document
cases_needing_attention
waiting_by_actor
time_in_wait
time_in_phase
resolution_time
human_takeover_rate
AI_owned_rate
reopen_rate
cases_without_next_action
cases_without_policy_ref
cases_without_document_relation
projection_contradictions
```

Não usar métricas de vaidade como “cards renderizados”.

---

# 66. VISUAL ACCEPTANCE

Screenshot da Fila deve responder em <10s:
1. qual precisa de mim?
2. por quê?
3. quem possui?
4. esperando quem?
5. próximo passo?
6. há atraso?
7. como abrir contexto?

Screenshot do Case:
1. o que foi pedido?
2. o que aconteceu?
3. onde está agora?
4. quem cuida?
5. onde estão documentos?
6. onde está conversa?
7. o que IA/humano fez?
8. como termina/terminou?

---

# 67. REJECTED ARCHITECTURES

- ressuscitar ResultVision wholesale;
- ressuscitar `attendance_cases` por nostalgia;
- ticketing subsystem novo;
- Case = Work Run;
- Case = Conversation como ontology definitiva sem medir;
- Kanban como state authority;
- tags como lifecycle;
- LLM-generated state sem evidence;
- full dashboard de KPIs;
- technical execution details por default.

---

# 68. P0 RECOMENDADO

```text
Atendimentos
├── Fila
│   ├── attention views
│   ├── Lista
│   └── Quadro
├── Casos
│   ├── Ativos
│   ├── Encerrados
│   └── Todos
├── Conversas
└── Segurados

Case Workspace
├── Agora
├── Timeline
├── Conversas
├── Documentos
├── Dados
├── Trabalhos
└── Notas
```

---

# 69. P1 / DEFER

- custom saved views;
- custom columns;
- bulk actions;
- advanced SLA configuration;
- case relationship graph;
- capacity routing;
- export dossier;
- global conversation full-text;
- persistent Case entity se need proven.

---

# 70. WARM-UP QUESTIONS OBRIGATÓRIAS

1. Current `HEAD`?
2. Protocol still v11.2?
3. SPECS executed since this pack?
4. 086 states unchanged?
5. 093-B live and final?
6. Work Runs linked to conversation in current production?
7. Case UI still derived from `/api/dashboard/atendimentos`?
8. `work_waits` current volume/distribution?
9. Current resolution authority?
10. Current claim/handoff authority?
11. Current evidence/document authorities?
12. `conversation_files` still relevant?
13. Media in `messages`/transcripts enough?
14. Active conversation volume?
15. p95 queue size?
16. Largest timeline/event set?
17. Docs/media per conversation?
18. One business situation spans multiple conversations?
19. Insurer mirror can map to same situation?
20. One/many Work Runs per conversation?
21. Approval refs linked to Work?
22. Artifacts linked to Work?
23. Current note writers/readers?
24. Current realtime mechanisms?
25. How many polling requests/operator/min?
26. Current mobile screenshots?
27. Which ResultVision assets still illustrate desired clarity?
28. Any old routes accidentally in production?
29. Real stage distribution?
30. Which attention views would have nonzero rows?
31. Enough data for deterministic next action?
32. Enough data for attention?
33. Materialized projection needed?
34. Cross-tenant seams?
35. Any client-authoritative company_id?
36. Protocol truth source?
37. Policy truth source?
38. Customer identity truth?
39. Insurer truth?
40. What can be deleted rather than extended?

---

# 71. SOURCE INDEX — AUTOBROKERS

1. `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`
2. `docs/canon/UX-001-navegacao.md`
3. `docs/canon/specs/SPEC-043-central-atendimentos-corretor-mobile.md`
4. `docs/canon/specs/SPEC-046-ficha-atendimento-limpeza-admin.md`
5. `docs/canon/reports/SPEC-086-EXECUTION-REPORT.md`
6. `docs/canon/specs/SPEC-093-B-o-sinistro-deixa-rastro.md`
7. `app/dashboard/atendimentos/page.tsx`
8. `lib/mock/tenant-modules.ts`
9. `app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx`
10. `app/dashboard/atendimentos/casos/HistoricoClient.tsx`
11. `app/dashboard/atendimentos/ficha/[conversaId]/FichaClient.tsx`
12. `app/dashboard/atendimentos/conversas/ConversasClient.tsx`
13. `app/dashboard/atendimentos/segurados/SeguradosClient.tsx`
14. `app/api/dashboard/atendimentos/route.ts`
15. `app/api/dashboard/atendimentos/ficha/[id]/route.ts`
16. `lib/attendance/dispatch-states.ts`
17. Work Run / Work Events / Work Wait.
18. Approval / Artifact authorities.

---

# 72. SOURCE INDEX — RESULTVISION

1. `client/src/App.tsx`
2. `client/src/pages/work-queue.tsx`
3. `client/src/pages/board.tsx`
4. `client/src/components/work-queue/case-drawer.tsx`
5. `client/src/pages/history.tsx`
6. `client/src/pages/conversations.tsx`
7. `client/src/pages/clients.tsx`

Repo:
https://github.com/Amandico100/ResultVision

---

# 73. SOURCE INDEX — EXTERNAL

## Intercom
https://www.intercom.com/help/en/articles/6258745-the-inbox-explained  
https://www.intercom.com/help/en/articles/6588834-organize-your-inbox-with-custom-views-and-folders  
https://www.intercom.com/help/en/articles/6561699-assign-conversations-to-teammates-and-teams  
https://www.intercom.com/help/en/articles/6546152-set-slas-for-conversations-and-tickets  
https://www.intercom.com/help/en/articles/13334840-conversation-events-in-the-inbox

## Front
https://help.front.com/en/articles/2344  
https://help.front.com/en/articles/2256  
https://help.front.com/en/articles/2243  
https://help.front.com/en/articles/2099  
https://help.front.com/en/articles/2057

## Zendesk
https://support.zendesk.com/hc/en-us/articles/4408836526362-Using-the-context-panel  
https://support.zendesk.com/hc/en-us/articles/4408828503450-Configuring-the-context-panel-in-the-Zendesk-Agent-Workspace  
https://support.zendesk.com/hc/en-us/articles/4408829170458-Viewing-customer-context-for-user-history-and-device-information  
https://support.zendesk.com/hc/en-us/articles/4408832852122-Viewing-and-understanding-SLA-targets

## Salesforce
https://help.salesforce.com/s/articleView?id=service.cases_set_up_and_manage_the_case_timeline.htm  
https://help.salesforce.com/s/articleView?id=service.case_interaction_overview.htm  
https://help.salesforce.com/s/articleView?id=service.case_interaction_case_detail_page.htm  
https://help.salesforce.com/s/articleView?id=service.omnichannel_routing_targets.htm

## ServiceNow
https://www.servicenow.com/docs/r/customer-service-management/csm-config-workspace-interface.html  
https://www.servicenow.com/docs/r/customer-service-management/csm-playbooks-using-activity-stream.html  
https://www.servicenow.com/docs/r/api-reference/rest-apis/case-api.html

## Linear
https://linear.app/docs/display-options  
https://linear.app/docs/board-layout  
https://linear.app/docs/custom-views  
https://linear.app/docs/peek  
https://linear.app/docs/search  
https://linear.app/docs/assigning-issues

---

# 74. QUALIDADE DAS FONTES

```text
T0 = repo atual + schema/production measurements
T1 = documentação oficial de produto
T2 = ResultVision antigo
T3 = comunidade/reviews
T4 = blogs/secundário
```

Decisão arquitetural crítica:
- T0/T1 necessários.
- T2 é inspiração.
- T3/T4 no máximo reforço.

---

# 75. LIMITAÇÕES

- O repo muda enquanto outras SPECS são executadas.
- Baseline deve ser reconfirmado.
- Medições da 093-B são snapshot de 03/09/2026.
- Multi-conversation Case precisa ser medido.
- Data model de docs precisa ser auditado live antes de migration.
- Não foi pré-decidido criar `operational_cases`.
- Views finais de Fila dependem de distribuição real.

---

# 76. CONCLUSÃO

O ResultVision prova que o produto já teve mais **legibilidade espacial/contextual**:
- Kanban;
- Case Drawer;
- Case 360;
- docs;
- waiting-on;
- next action;
- relationship com conversation.

O AutoBrokers atual prova que a arquitetura é hoje muito mais forte:
- conversation truth;
- dispatch;
- Work OS;
- waits;
- human/AI ownership;
- resolution;
- Artifacts;
- structured events.

As referências externas validam:
- Intercom → views/attention/SLA;
- Front → ownership/notas internas;
- Zendesk → context;
- Salesforce → unified Case Timeline;
- ServiceNow → activity stream;
- Linear → list/board como projeções.

A 097 combina:

```text
ARQUITETURA MODERNA DO AUTOBROKERS
+
CLAREZA PERDIDA DO RESULTVISION
+
PADRÕES EXTERNOS VALIDADOS
```

e rejeita:

```text
legacy data model
generic ticketing
CRM bloat
visual-only Kanban
fake state
parallel truth
```

> **O corretor não precisa entender como o AutoBrokers funciona por dentro. Ele precisa abrir um atendimento e entender, em segundos, o que aconteceu, onde está, quem está cuidando e o que acontece depois — com cada afirmação sustentada pela authority correta.**
