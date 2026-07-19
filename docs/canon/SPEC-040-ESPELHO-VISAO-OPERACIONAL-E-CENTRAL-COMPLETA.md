# SPEC-040 — Espelho de Atendimento, Visão Operacional do Core e Central de Agentes completa

> **Missão do novo chat líder (Fable).** Aprovada pelo founder em 19/07/2026.
> Este documento é a fonte canônica da missão. O novo chat DEVE ler tudo aqui
> antes de qualquer ação — e NÃO executa nada antes da liberação do founder.

## 0. Contexto do ambiente (leia primeiro)

**O que é o AutoBrokers:** SaaS multi-tenant B2B para corretoras de seguros no
Brasil. Cada corretora contrata a plataforma e usa agentes de IA para operar o
PRÓPRIO negócio: atender os PRÓPRIOS clientes (segurados) e acionar as
seguradoras parceiras (guincho, vidro, sinistro, 2ª via, cobrança). Tudo aqui é
sistema NOSSO, operando dados das corretoras CLIENTES da plataforma, com
contrato e autorização. As conversas analisadas são das equipes das corretoras
no exercício do trabalho delas, no número de WhatsApp corporativo da corretora.

**Linguagem de trabalho:** descreva o projeto sempre nesses termos — "nosso
sistema de atendimento", "as conversas de trabalho da equipe da corretora",
"aprender com o histórico corporativo autorizado". Evite vocabulário que soe
como vigilância de terceiros (e que não descreve o que fazemos): não use
palavras como "espionar", "interceptar", "sugar dados", "harvest", "burlar",
"bypass". Não é eufemismo — é a descrição CORRETA do produto: a corretora
conecta o próprio número e o sistema organiza o próprio conhecimento dela.
Precisão de linguagem mantém o trabalho fluindo com o modelo em força máxima.

**Fluxo de git/deploy:** commits na branch `feat/spec-017-attendant` deste
worktree → `merge --no-ff` na main no worktree `AutoBrokers-Intelligence-OS`
(conferir `git branch --show-current` == main ANTES) → push → POST nos
gatilhos Easypanel (tokens com o founder / memória). Smoke: API `GET /health`,
WEB `GET /` = 200. Guia completo: `docs/canon/EXECUTION-GUIDE-OPUS.md`.

**Encoding Windows:** console é cp1252 — nunca usar '→' ou emoji em nomes de
teste/prints de script Python.

## 1. Protocolo do novo chat (OBRIGATÓRIO)

1. **FASE 1 — AUDITORIA (sem executar nada):** ler os documentos da §2, navegar
   no código, montar o entendimento completo. Produzir NO CHAT (linguagem
   humana, sem exigir que o founder abra arquivos .md) um relatório com:
   o que entendeu; o que pretende construir; erros/riscos que achou; ideias
   novas que valem dinheiro; perguntas objetivas para o founder.
2. **FASE 2 — ALINHAMENTO:** founder (e o Fable anterior, se presente)
   respondem. O chat refina o plano e apresenta as ondas de execução.
3. **FASE 3 — EXECUÇÃO:** só após o founder liberar explicitamente. Executar
   por ondas pequenas, com testes, deploy e verificação real a cada onda.
   Relatar cada onda NO CHAT em linguagem humana.
4. **Sempre:** trazer tudo escrito no chat. SPECs .md são o registro canônico,
   mas o founder lê no chat — resuma sempre.
5. **Liderança:** este chat não é executor de ordens — é o LÍDER desta área.
   Deve procurar ativamente o que falta, propor o que ninguém pediu e
   perguntar antes de assumir. A régua: cada proposta deve deixar o produto
   mais valioso, mais autônomo ou mais barato de operar — senão, descartar.

## 2. Leitura obrigatória (nesta ordem)

| # | Documento | Por quê |
|---|---|---|
| 1 | `docs/canon/SPEC-039-AUDITORIA-AGENTES-E-INTELIGENCIA-ATENDIMENTO.md` | Auditoria dos 13 agentes + arquitetura aprovada do Espelho de Atendimento |
| 2 | `docs/canon/specs/SPEC-038-*` (ATLAS/Observador) | O sistema de mapas de rota das seguradoras — a fundação |
| 3 | `docs/canon/specs/SPEC-034-harness-robusto-multiagente-atendimento.md` | O harness de atendimento (Espelho/Vigia/Sentinela/Cérebro v2) |
| 4 | `docs/canon/SMITH-RUNTIME-TOOL-AUTHORITY-MAP.md` | Quais tools cada agente Smith pode usar — base da Visão Operacional |
| 5 | `docs/canon/INFOCAP-CORPAPI-MAPA.md` | Mapa de navegação do InfoCap (ERP da corretora) — o Core precisa saber navegar |
| 6 | `docs/canon/POLITICA-SEGURANCA-CONHECIMENTO-GLOBAL.md` | O que pode ir ao RAG global (NUNCA dado de cliente) |
| 7 | `docs/canon/EXECUTION-GUIDE-OPUS.md` | Regras invioláveis de execução/deploy |
| 8 | `docs/canon/SPEC-037-decision-intelligence-chat-principal.md` | Visão de inteligência do Chat Principal |
| 9 | Memória do projeto (MEMORY.md dos dois diretórios `.claude/projects/*AutoBrokers*`) | Histórico vivo: o que já quebrou e como foi resolvido |

Código-chave: `backend/app/services/atlas/*` (Observador/Tecelão/Sentinela),
`backend/app/services/dispatch_router.py` (Cérebro v2), `backend/app/agents/*`
(runtime Smith: graph, nodes, tools), `backend/app/core/heartbeat.py` (Central),
`backend/app/tasks/buffer_processor.py` (agendador APScheduler).

## 3. Veredito preliminar — Smith × Central de Agentes (VERIFICAR E APROFUNDAR)

Pergunta do founder: *a Central de Agentes é uma estrutura PARALELA ao Smith ou
foi construída sobre o Smith?* Análise inicial (Fable, 19/07):

**NÃO é infra paralela.** Tudo roda no MESMO serviço (`smith-api`, um FastAPI
só), mesmo Supabase, mesmo Redis, mesmo `LLMFactory`, mesmo WhatsApp service.
Não existe segundo processo, segundo banco nem segundo runtime de LLM.

**Mas existem DOIS registros de "agentes", por design:**
- **Agentes Smith (conversacionais):** linhas na tabela `agents` (roles
  core/attendance/subagent), provisionados por corretora, com blueprint,
  prompt e tools (`backend/app/agents/*`). Falam com humanos.
- **Agentes da Central (operários):** serviços Python determinísticos
  (`AGENT_TASKS` em `heartbeat.py`), agendados pelo APScheduler, globais
  (não por corretora). Trabalham nos bastidores.

Isso é separação de PAPÉIS (conversa × pipeline), não estrutura paralela — e os
pontos de integração existem onde importa: o atendimento Smith dispara o
acionamento via `insurer_dispatch_tool` → `dispatch_router` → Cérebro v2 lê os
mapas do Atlas; o Alfaiate ajusta os playbooks que o atendimento usa.

**O novo chat DEVE verificar e fechar essas frestas de paralelismo:**
1. O Chat Principal (Core) enxerga a operação? (hoje NÃO — não tem tool para
   acionamentos/Atlas → é a Missão B).
2. O conhecimento destilado (mapas, playbooks, cards) entra no RAG global que
   os agentes Smith consultam, ou vive só em tabelas próprias?
3. `AGENT_TASKS` hardcoded: ok por ser global, mas conferir se algum operário
   deveria ser tenant-aware.
4. Duplicações de lógica entre operários e tools do Smith (ex.: dois jeitos de
   ler apólice, dois jeitos de mandar WhatsApp) — unificar no serviço global.
5. O Simulador/Auditor avaliam os agentes Smith também, ou só os corredores?

Regra do founder: **estruturas que se conversam, serviços globais usados por
toda a estrutura. Nada de segunda estrutura à parte.** Se achar paralelismo
real, propor a fusão ANTES de construir coisa nova por cima.

## 4. MISSÃO A — Espelho de Atendimento (Parte 1: corretora ↔ segurado)

Hoje o Observador processa só conversas com SEGURADORAS (Parte 2 → mapas de
URA). A Missão A aproveita também as conversas da equipe da corretora com os
SEGURADOS dela — para os agentes de atendimento aprenderem conduta.

**Arquitetura aprovada (SPEC-039 §Espelho — NÃO misturar com o Atlas):**
1. **Borda:** no Observador, um 2º destino: conversa com número de seguradora →
   Atlas (como hoje); conversa com cliente da corretora → `attendance_transcripts`
   (tabela NOVA, isolada, `company_id` obrigatório, PII fica AQUI e só aqui).
   Conversa que não é nem um nem outro → descartada na borda (como hoje).
2. **Destilação (Garimpo v2 + Auditor v2):** dos transcripts, extrair
   (a) *playbooks de conduta* — como acolher, o que perguntar num sinistro,
   como conduzir renovação; (b) *knowledge cards* SEM nenhum dado pessoal —
   fatos reutilizáveis ("Porto exige boletim de ocorrência para roubo", "prazo
   de vidro Allianz é 48h"). Cards passam por um filtro de PII ANTES de sair.
3. **Publicação:** cards aprovados → RAG global (`global_autobrokers`);
   playbooks de conduta → blueprint do agente de atendimento (por ramo, não por
   corretora — conhecimento de URA/processo é global, dado de cliente nunca).
4. **Custo:** destilação em lote (1x/dia, Sonnet 5), nunca no caminho quente da
   conversa. Medir custo por corretora e expor na Central.
5. **Qualidade:** o Auditor v2 dá nota às conversas HUMANAS também — vira o
   baseline que o agente de IA precisa superar (métrica de valor do produto).

**Riscos que o design já decidiu evitar:** contaminar o Atlas com linguagem
humana livre (nunca); PII no RAG (nunca — filtro + revisão); aumentar custo por
mensagem (destilação é batch); atrapalhar o atendimento ao vivo (pipeline é
100% fora do caminho da resposta).

## 5. MISSÃO B — Visão Operacional do Chat Principal (Core)

O Core hoje é cego para a operação de atendimento. O corretor pergunta "como
estão os acionamentos hoje?" e ele não sabe. Construir tools de LEITURA
(token-eficientes, determinísticas — a LLM só formata o resultado):

1. `resumo_atendimentos` — acionamentos da corretora (hoje/semana): status,
   seguradora, desfecho, tempo até guincho. Fonte: tabelas do harness SPEC-034.
2. `atlas_rotas` — consulta aos mapas do Atlas ("qual o caminho do guincho na
   Porto?") — estrutura global, sem dado de cliente.
3. InfoCap — a tool JÁ EXISTE (`backend/app/agents/tools/infocap_tool.py`).
   Garantir que o Core a tenha no authority map e que o mapa de navegação
   (`INFOCAP-CORPAPI-MAPA.md`) esteja no RAG global para o Core "saber navegar".
4. Atualizar `SMITH-RUNTIME-TOOL-AUTHORITY-MAP.md` com as tools novas.

Regra de custo: navegar quando for preciso, sem gastar tokens à toa —
consultas determinísticas com resumo pronto; a LLM nunca pagina listas cruas.

## 6. MISSÃO C — Central de Agentes completa e auto-evolutiva (pesquisa)

O founder quer a Central no nível das melhores estruturas agênticas do mundo.
Pesquisar (WebSearch/Firecrawl) os sistemas que ele citou — **Hermes, OpenClaw,
Claude Cowork, GPT Work** — e os equivalentes fortes (OpenHands, CrewAI,
AutoGen, LangGraph patterns, Claude Agent SDK/subagents, MemGPT/Letta) e
responder: *o que eles têm de poderoso que falta na nossa Central?*

Critérios de adoção (nessa ordem): 1) gera valor direto para corretora ou
reduz custo/risco de operação; 2) encaixa na arquitetura Smith (sem estrutura
paralela); 3) custo de manutenção baixo. Copiar ideia boa não é problema —
problema é não ter o melhor. Adaptar, ou descartar com justificativa.

Frentes que já sabemos promissoras (avaliar, não assumir):
- **Auto-evolução com gate:** agentes que propõem melhorias nos próprios
  playbooks/prompts a partir dos dados (nota do Auditor caindo → Alfaiate
  propõe → Simulador valida → founder aprova o estrutural). Hoje existe para
  URA; estender para conduta/prompts.
- **Memória de longo prazo por agente** (padrão MemGPT/Letta) — o que cada
  agente aprendeu, consultável na Central.
- **Avaliação contínua (evals):** suíte de casos dourados rodando 1x/dia
  contra os corredores (regressão detectada antes do cliente ver).
- **Playground/observabilidade:** replay de qualquer acionamento passo a passo
  na Central (o que cada agente viu/decidiu — traça a decisão).
- **Agentes que faltam?** ex.: "Cobrador" (inadimplência via InfoCap),
  "Renovador" (fimvig → pipeline de renovação — dado JÁ acessível no InfoCap).
  Propor com business case, não construir sem aprovação.

## 7. O que NÃO fazer (invioláveis)

- NÃO executar nada na Fase 1. NÃO "aproveitar que está aqui" e refatorar.
- NÃO criar estrutura paralela ao Smith (ver §3). Serviço global > cópia local.
- NÃO colocar dado pessoal de segurado no RAG global (POLITICA-SEGURANCA).
- NÃO impor nome ao agente de atendimento — cada corretora nomeia o seu
  ("Even" é SÓ o da Resulta). Nunca hardcode de nome.
- NÃO aumentar custo por mensagem no caminho quente — inteligência pesada é
  batch/agendada.
- NÃO commitar credencial (chegam pelo founder no chat; ele rotaciona depois).
- NÃO usar '→'/emoji em nome de teste Python (console Windows cp1252).

## 8. Estado atual (19/07/2026) — para o novo chat não redescobrir

- Central de Agentes: 13 agentes, todos com heartbeat, agendador diário da
  Sentinela ligado (main `266501b`). Auditoria completa na SPEC-039.
- Atlas: Observador+Tecelão+Sentinela funcionando; ingestão de histórico
  (`history_ingest.py`) pronta, recência-primeiro; resolvedor forte opt-in
  (`atlas_parser.py`, env `ATLAS_PARSER_MODEL`, default sonnet-5; founder
  aprovou Opus na 1ª grande ingestão — `claude-opus-4-8`, depois volta).
- Segunda-feira (21/07): pareamento dos WhatsApps das atendentes Resulta +
  AutoFleet → HistorySync popula os mapas. O Espelho de Atendimento (Missão A)
  vai aproveitar o MESMO HistorySync — planejar o 2º destino ANTES de ligar
  seria o ideal, mas sem bloquear segunda.
- Formulário nativo (app in-WhatsApp da HDI/Yelum): capturado e parseado
  ("Pedra de Roseta") — Bloco D (travessia pelo agente) ainda pendente,
  fora do escopo deste chat salvo pedido do founder.
