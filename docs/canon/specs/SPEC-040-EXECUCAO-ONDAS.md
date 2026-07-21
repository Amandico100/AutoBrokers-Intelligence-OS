# SPEC-040 — Registro de execução das ondas (chat líder Fable)

> Execução liberada pelo founder em 19/07/2026 (respostas às 5 perguntas da
> FASE 1 no chat). Este doc é o REGISTRO; o relato vivo acontece no chat.

## Decisões do founder (19/07, FASE 2)

1. **Sequência:** executar onda por onda, na ordem que o líder decidir; o
   pareamento de segunda PODE ser adiado se necessário — qualidade primeiro.
2. **Retenção dos transcripts crus:** líder decide (decidido: 90 dias a partir
   da INGESTÃO, env `ATTENDANCE_RETENTION_DAYS`; o destilado é permanente).
3. **Conselho de Agentes:** construir PRONTO mas DESLIGADO por default (avaliar
   custo antes de ligar). Modelos: **Fable (líder) + GPT + Opus 4.8 +
   Kimi K3 + Grok 4.5**. Uso: decisões raras/estruturais, prompts enxutos
   (nunca volumes de documentação). Futuro: modo conselho p/ o Chat Principal
   (estratégia/pesquisa de mercado) — bem controlado por custo.
4. **Nota dos atendimentos humanos (baseline):** SIM, mas SÓ no portal admin
   (interno AutoBrokers). NUNCA exposta à corretora no dashboard.
5. **Inteligência é da AutoBrokers, não da corretora:** playbooks de conduta,
   cards e mapas destilados são GLOBAIS (por seguradora/ramo) e servem todas
   as corretoras presentes e futuras. Dado pessoal continua isolado por
   corretora e NUNCA vai ao conhecimento global.
6. **Custo da destilação:** founder pediu explicação melhor + modelo de fases
   (intensa na observação, manutenção depois) — respondido no relatório da
   Onda 1 no chat.

## ONDA 1 — Espelho de Atendimento: borda de captura (ENTREGUE 19/07)

Main `449937e` (feat `5f4330f`). Bateria 45/45. Migração
`20260719_01_spec040_attendance_transcripts.sql` APLICADA no Supabase.

- Tabelas `attendance_transcripts` + `attendance_sessions` (schema idêntico a
  `observed_*` de propósito — storage compartilhado parametrizado; RLS ON,
  service-only, sem policy = dashboard da corretora não lê o cru).
- 2º destino na borda do Observador (`observer_intake`): conversa com número
  individual não-seguradora → Espelho de Atendimento QUANDO a integração
  observer tem `observer_scope=insurers_and_clients` (vive em
  `integrations.alert_target`). Default global = `insurers_only` (integrações
  existentes, incl. 4743 do founder, não mudam NADA). Grupos/status: sempre
  descartados. Falha do Espelho NUNCA quebra a borda (try/except).
- HistorySync (`history_ingest`): conversas de segurado também ingerem
  (recência-primeiro, sessões por janela de 2h, dedupe determinístico, cap
  `ATTENDANCE_HISTORY_MAX_EVENTS`=50k). Retorno ganhou contadores
  `client_conversations`/`client_events_stored`.
- Mídia: SÓ metadados (mimetype/filename/caption) — nunca bytes/base64.
- Retenção: purge diário no APScheduler (check horário + marcador Redis
  `attendance:purge:last_run`), corte por `created_at` (ingestão).
- Central de Agentes: 14º agente **espelho_atendimento** (pulsa na captura,
  na ingestão de histórico e no purge).
- Onboarding `/atlas/onboarding/pair`: aceita `scope` (default
  `insurers_and_clients` p/ pareamento de atendente); `onboarding/status`
  expõe o escopo por instância.

## ONDA 2 — Visão Operacional do Core + seed global (ENTREGUE 19/07)

Main `cd80b1c`. Bateria 46/46 (20 checks novos).

- `operational_view.py`: digests determinísticos e token-eficientes —
  `operations_summary` (ativos no Redis + movimento via agent_activities +
  qualidade via scorecards; escopo por corretora; fail-soft por seção) e
  `atlas_routes_summary` (lista de mapas c/ cobertura; detalhe c/ tela de
  entrada + opções; caminho BFS até um serviço; estrutura global sem dado de
  cliente).
- Tools `resumo_atendimentos` (company_id injetado pelo runtime) e
  `atlas_rotas` ligadas no `graph.py` SÓ para o papel core.
- `global_knowledge_seed.py`: ingestão idempotente (hash+Redis) dos docs
  canônicos embarcados (`app/data/global_knowledge/*.md`) na coleção
  `autobrokers_global` (dense+BM25, scope publicado; substitui versão
  anterior). Job horário, 1ª rodada ~2min pós-boot. 1º seed: mapa
  InfoCap/CorpAPI — o Core "sabe navegar" no ERP por conhecimento.
- `KNOWLEDGE_GLOBAL_SEARCH` default LIGADO (env ainda desliga).
- Authority map atualizado (2 tools read-only novas, capabilities alvo
  `operations.summary.read` / `atlas.routes.read` p/ R2).

**Decisão de arquitetura da conversa da Parte 1 (pergunta do founder 19/07):**
NÚCLEO GLOBAL DE CONDUTA (fixo, no prompt do atendente — tom, empatia, FICHA,
nunca re-perguntar, InfoCap-primeiro, confirmar antes de acionar) + FICHA DE
COLETA POR TIPO DE SERVIÇO como DADO versionado (o que coletar em guincho vs
vidro vs sinistro; pré-checks; ordem). Hoje as fichas vivem inline no prompt
(auditado 19/07: forte); na Onda 3 viram dados destilados pelo Espelho com
gate — o prompt permanece estável e as fichas evoluem com segurança.

## ONDA 3 — Destilador do Espelho (ENTREGUE 19/07)

Main `22e4608`. Bateria 47/47 (19 checks novos). Migração `20260719_02`
APLICADA (conduct_playbooks + knowledge_cards, globais, RLS service-only).

- `attendance_distiller.py`: Estágio 1 (braçal, `DISTILLER_LLM_MODEL` default
  claude-sonnet-5) — extração por sessão sobre transcript MASCARADO
  (templatize antes de QUALQUER LLM; PII real nunca sai do cofre): tipo/ramo/
  serviço, conduta, perguntas na ordem, fatos reutilizáveis, score humano.
  Estágio 2 (estrutural, `DISTILLER_STRONG_MODEL` default claude-opus-4-8 —
  decisão do founder: estrutural merece o modelo mais forte) — síntese do
  playbook de conduta por (ramo, serviço), DRAFT versionado (nada auto-aplica
  antes do gate da Onda 4). `ja_temos_na_apolice=true` ⇒ confirmar, nunca
  perguntar.
- Knowledge cards: filtro PII 2 camadas + dedupe md5 + fila pending_review;
  aprovação publica como CHUNK ATÔMICO no `autobrokers_global` (card já é o
  formato ideal de RAG — sem chunking pesado no caminho automático).
- Endpoints admin `/api/admin/atlas/espelho/*`: resumo (baseline humano por
  corretora — ADMIN-ONLY), cards, decide (approve publica/reject), playbooks,
  run manual.
- Agendador: check horário, roda 1x/dia na janela UTC 03-09 (madrugada BRT),
  teto `DISTILLER_MAX_SESSIONS_PER_RUN`=40, zero LLM sem sessão nova. Custo
  no FinOps via LLMFactory por company.
- Prompt do atendente: seção "SISTEMA LENTO OU FORA DO AR" — indisponibilidade
  de InfoCap/gestor NUNCA trava a conversa (coleta, 1 retry, transparência
  leve, acionamento ou dossiê com o que houver).

**Respostas ao founder (19/07):** RAG automatizado usa formato certo por tipo
(cards=chunk atômico; docs canônicos=chunking markdown determinístico;
chunking semântico/agentic fica p/ uploads humanos grandes); tiering: braçal=
Sonnet 5, estrutural (playbooks)=Opus 4.8, tudo por env; recomendação de
upgrade opcional: `DISPATCH_LLM_MODEL` p/ Opus nos desvios do Cérebro v2.

## ONDA 4 — Nunca regredir + Conselho (ENTREGUE 19/07)

Main `60a93e7`. Bateria 48/48 (18 checks novos). Sem migração nova (usa
conduct_playbooks.status + scorecards existentes).

- `playbook_gate.py`: gate de ativação de playbook — checks determinísticos
  (ficha completa, ZERO PII via templatize — PII bloqueia SEMPRE), juiz com
  modelo forte comparando candidato × ativo × condutas douradas humanas (só
  ativa se nota_candidato >= nota_atual — regredir é impossível por este
  caminho; sem ativo, piso 70), Conselho opcional; flip versionado
  (ativo→retired) + rollback de 1 chamada; decisões em Atividades.
- `agent_council.py`: Conselho de Agentes — OFF por default
  (`COUNCIL_ENABLED=0`); membros `COUNCIL_MEMBERS` default gpt-5.5 +
  claude-opus-4-8 + kimi-k3 + grok-4.5 (sem chave = pulado com nota, nada
  quebra); líder `COUNCIL_LEADER_MODEL` (opus) consolida pareceres paralelos
  curtos em veredito JSON; contexto cap 3000 chars; heartbeat "conselho"
  (15º agente da Central); telemetria `council:last_convening`.
  NOTA: Kimi K3/Grok exigem chave + suporte de provider no LLMFactory — até
  lá são pulados; founder cola as chaves quando quiser os 4 votos.
- `regression_sentinel.py`: nota média 24h × 7 dias anteriores POR corretora
  (scorecards do Auditor, determinístico, zero LLM); queda >=
  `REGRESSION_DROP_POINTS` (10) com >= `REGRESSION_MIN_SAMPLES` (5) →
  alerta no canal de suporte (mesmo caminho do Vigia) + Atividades.
- Endpoints: `/espelho/playbooks/{id}/activate`, `/espelho/playbooks/rollback`,
  `/conselho/status`, `/conselho/convene` (manual).
- Founder ligou `DISPATCH_LLM_MODEL=claude-opus-4-8` (Cérebro v2 nos desvios).

## ONDA 5 — Memória por agente + Replay + Contribuição (ENTREGUE 19/07)

Main `c041047`. Bateria 49/49 (13 checks novos). Migração `20260719_03`
APLICADA (agent_memories, RLS service-only).

- `agent_memory.py`: blocos de memória por agente da Central ("o que cada um
  sabe"), reescritos 1x/dia dos dados REAIS — padrão sleep-time
  DETERMINÍSTICO, zero LLM (observador: cobertura/seguradora; tecelão: mapas
  vivos; sentinela: drifts; espelho: capturas+destiladas+baseline interno;
  auditor: qualidade 7d; garimpo: insights; alfaiate: playbooks por status;
  conselho: última convocação). Upsert por (agent_task, block_key), marcador
  diário, rebuild manual.
- Replay/observabilidade: `/replay/acionamentos` + `/replay/acionamento/{id}`
  (timeline persistente espelhada + scorecard — sobrevive ao TTL do Redis) e
  `/replay/atendimento/{session_id}` (sessão do Espelho com transcript
  MASCARADO — PII fica no cofre — + resumo destilado).
- `/onboarding/contribuicao`: efeito rede visível — por corretora: sessões de
  URA observadas, sessões da Parte 1 capturadas/destiladas, primeira/última
  atividade. Custo por corretora já sai no FinOps (LLMFactory rastreia).
- Endpoints `/central/memorias` (+ `/rebuild`); scheduler `agent_memory_check`.

## PÓS-ONDAS — SPEC-041 + SPEC-042 (ENTREGUES 19/07, main `9a96f71`)

Founder aprovou executar na espera do pareamento (20/07). Bateria 50/50.

- **SPEC-042 Lapidador** (`prompt_optimizer.py`): otimização reflexiva de
  conduta no padrão GEPA, na nossa stack (sem dependência nova): feedback
  TEXTUAL das falhas reais (sessões fracas + flags do Auditor, dedupe) →
  reflexão com modelo FORTE sobre o playbook ativo + condutas douradas →
  DRAFT otimizado que SÓ assume via gate nunca-regredir. Semanal por grupo
  ativo com feedback novo (`LAPIDADOR_MIN_FEEDBACK`=5) + manual
  `POST /espelho/optimize`; PII no candidato reprova; custo zero ocioso.
  Fase 2 registrada: calibração do LLM-judge (Nubank), Chat Principal.
- **SPEC-041 Painéis** (frontend /admin): página nova **/admin/espelho**
  (resumo vivo, fila de aprovação de cards 1-clique → RAG global, playbooks
  com Ativar-gate/lapidar/rollback + conteúdo, replay MASCARADO de sessões,
  contribuição por corretora, rodar destilação); **central-agentes** com
  blocos de MEMÓRIA por agente; **acionamentos** com Histórico (replay
  persistente + nota); item "Espelho de Atendimento" no nav. tsc limpo.
- Endpoint novo `GET /espelho/sessoes` (lista p/ o painel).

## PÓS-ONDAS 2 — SPEC-043 Central de Atendimentos do corretor (ENTREGUE 19/07 noite, main `9c6f59b`)

- **Fix do teste A do founder:** tools `resumo_atendimentos`/`atlas_rotas`/
  `buscar_veiculo` ganharam ponte sync→async real (o runtime do chat invocava
  o caminho síncrono e o placeholder vazava "consulta deve ser assíncrona").
- **Dashboard do corretor (mobile-first, linguagem humana, zero LLM):**
  APIs Next `/api/dashboard/atendimentos` (pipeline unificado: conversas +
  dispatch ativo do backend + sessões do Espelho; estágio determinístico;
  score interno NUNCA exposto) e `/atendimentos/segurados` (clientes
  derivados). Fila = pipeline ao vivo por estágio colorido (Precisa de você
  vermelho no topo, Acionando azul, Protocolo/Prestador verde, Em conversa,
  Com a equipe âmbar, Observação); Casos → Histórico com busca+filtros;
  Segurados = lista real; Conversas = wrapper padrão (header alinhado) +
  modo WhatsApp no mobile (lista OU thread + voltar) + deep-link `?open=`.
  Sandbox antigo (attendance_cases/"caso teste") saiu das superfícies.

## PÓS-ONDAS 3 — SPEC-044 Três Camadas ENTREGUE (20/07, main `34c48c6`)

Bloco 1 da trinca 044-046. Migração `20260720_01` APLICADA. Bateria 51/51,
tsc limpo, 24 checks novos.

- **Restrição-mestra descoberta na auditoria e respeitada em tudo:** o grafo
  do agente é CACHEADO por (company, agent) e compartilhado entre usuários —
  identidade NUNCA no construtor; viaja POR REQUISIÇÃO (state→tool_node;
  ContextVar→cost_callback).
- **Custos por pessoa:** `request_context.py` (ContextVar) setado no
  process_message; cost_callback grava `details.user_id`; Custos e Uso mostra
  quebra por pessoa (tokens + % do uso, 30d).
- **Conhecimento pessoal:** SCOPE_PERSONAL + owner no payload Qdrant; busca
  padrão EXCLUI personal (à prova de vazamento — nem atendimento nem colegas
  veem); busca pessoal extra só com user_id da requisição; upload com escolha
  "Da corretora / Só para mim" (dono SEMPRE da sessão); lista esconde docs
  pessoais alheios (nem o nome vaza).
- **Rotinas com dono:** criadas NO CHAT = pessoais do autor (default);
  galeria/manual = corretora; List/Manage filtram por execução; pessoal de
  terceiro é invisível e imutável (404 sem oráculo de existência).
- **Conectores pessoais (padrão ChatGPT Enterprise):** conexão da corretora e
  pessoal COEXISTEM por template (índices parciais no lugar do singleton);
  modal de escolha no conectar; owner assinado no state anti-CSRF do OAuth.

## PÓS-ONDAS 4 — SPEC-045 ENTREGUE (20/07, main `4b00c60`)

Bloco 2 da trinca. Migração `20260720_02` (platform_sends) APLICADA.
Bateria 52/52, tsc limpo, 24 checks novos.

- **Modo observação + toggle (o fluxo do founder):** agente de atendimento
  DESLIGADO = número segue pareado, equipe humana atende, sistema captura
  (inbound salvo/espelhado + cofre do Espelho; fromMe da atendente também).
  LIGAR no dashboard = o agente responde NO MESMO número, sem re-parear.
  O OBSERVADOR NUNCA DESLIGA (correção do founder aplicada). Gate no webhook
  antes de billing/IA; helper cacheado 60s; toggle attendance-only
  (Core sempre ativo) via PATCH {is_active}.
- **Fila de cortesia + nota de contexto:** platform_outbound — envio de
  auxiliar a cliente OCUPADO (dispatch vivo ou conversa recente) espera na
  fila (retry 10min, expira 24h, Atividades); envio registrado em
  platform_sends; quando o cliente responde a uma cobrança, o atendente
  recebe a nota de contexto SÓ no texto da IA (mensagem salva limpa).
  Corretora pequena com 1 número = suportada com segurança.
- **Blueprint v2:** pronome/gênero REMOVIDOS; abertura padrão
  "Olá! Sou {{attendant_name}}, da {{company_name}}..." com render aninhado.
- **Superfícies:** card "AutoBrokers — Chat Principal" DIRETO (etapa Agentes
  morta, rota redireciona); hub Corretora (Dados · Agente de Atendimento ·
  WhatsApp · Suporte humano · Equipe · Conhecimento · Custos e Uso); hub
  WhatsApp por FUNÇÃO (Atendimento completo; Auxiliares default = mesmo
  número + fila; número dedicado GO = SPEC-046); toggle UI com estados
  humanos; "MVP ativo · sem envio real" trocado pela verdade atual.

## TODAS AS 5 ONDAS ENTREGUES (19/07/2026)

Estado final: 15 agentes na Central; ciclo completo captura → destilação →
gate → produção → vigilância de regressão → rollback; RAG global
auto-alimentado; Core com visão operacional; Conselho pronto (OFF).
Pendências de founder: pareamento das atendentes; aprovação dos primeiros
cards/playbooks; chaves Kimi/Grok se quiser 4 votos no Conselho; testes E2E
guiados (roteiro no chat).
