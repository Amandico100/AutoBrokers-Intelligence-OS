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

## Próximas ondas (plano aprovado)
- **ONDA 3 — Destilação:** job noturno (Sonnet 5, lote) sobre transcripts →
  playbooks de conduta por ramo + knowledge cards SEM PII (filtro 2 camadas +
  fila de aprovação) → RAG global; Auditor v2 pontua atendimentos humanos
  (baseline admin-only).
- **ONDA 4 — Nunca regredir:** suíte dourada + replay noturno + gate de
  regressão p/ mudança de playbook/prompt + modo sombra + Conselho de Agentes
  (pronto, desligado, env; Fable líder + GPT/Opus/Kimi/Grok).
- **ONDA 5 — Central classe mundial:** memória por agente (sleep-time batch),
  replay/observabilidade na Central, onboarding automático de corretora com
  contribuição/custo por corretora.
