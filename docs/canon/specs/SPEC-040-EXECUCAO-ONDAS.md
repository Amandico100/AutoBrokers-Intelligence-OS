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

## Próximas ondas (plano aprovado)

- **ONDA 2 — Visão Operacional do Core:** tools determinísticas
  `resumo_atendimentos` + `atlas_rotas` no Chat Principal; ingestão global do
  RAG (encanamento que falta) + mapa InfoCap no `global_autobrokers`;
  authority map atualizado.
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
