# SPEC-021 — F4 (aprendizado 3 camadas) + F5 (metering/conectores) + autoria de corredores

**Autor**: Fable · 2026-07-05 · **Status**: pronta para chat novo. Ler memória RODADAS 13-18.
> **EXECUTOR**: Opus 4.8 — leia ANTES `docs/canon/EXECUTION-GUIDE-OPUS.md` (obrigatório).
> **Pesquisa prévia obrigatória (founder)**: antes de implementar F4, PESQUISE na web como
> o OpenClaw/"Hermes" estrutura auto-aprendizado/self-improvement e "segundo cérebro"
> (memória persistente em arquivos: diário, lições, MEMORY curado; heartbeat/cron; skills).
> Traduza os padrões para NOSSO desenho (learning_notes 3 escopos + curadoria) — adote o
> que for melhor, cite no PR o que veio de onde. O erro do próprio agente vira
> error_lesson AUTOMÁTICA (needs_human do dispatch, guard-rejeição, rotina failed).

## F4 — Aprendizado em 3 camadas (visão Hermes: o sistema fica mais forte todo dia)
Camadas: **global AutoBrokers** (todas as corretoras se beneficiam) · **corretora** ·
**usuário**. Princípio: aprendizado = FATOS CURADOS + PLAYBOOKS, nunca fine-tune nem lixo
de conversa crua.

1. Tabelas (expand): `learning_notes(id, scope global|company|user, company_id?, user_id?,
   kind fact|preference|playbook|error_lesson, content text, source (conversa/rotina/caso),
   confidence, approved bool default false p/ global, created_by, embeddings via pipeline RAG
   existente do Qdrant)`.
2. Captura: tool `remember_note` (core+attendance) — o agente registra quando aprender algo
   ("corretora prefere X", "cliente Y = tom formal", "na Allianz o passo Z mudou");
   pós-caso do dispatch grava error_lesson automático quando needs_human.
3. Injeção: prompt dinâmico já tem memória — adicionar busca em learning_notes por escopo
   (user > company > global aprovadas) no _build_initial_state (top 5 por relevância, curtas).
4. Curadoria: Admin (master) tela "Aprendizado global" aprova/edita notas globais propostas
   (promoção company→global). NUNCA PII em nota global (validador: regex CPF/telefone bloqueia).
5. Métrica: contagem de notas usadas/execução no log_node (ver se ajuda de verdade).

## F5 — Metering por ferramenta + conectores
1. `tool_usage_events(company_id, agent_id, tool, provider, units, unit_cost_estimate,
   created_at)` — registrar em tool_node (wrapper) p/ Firecrawl/vision/portal/whisper.
   Cobrança REAL fica p/ depois (founder: primeiro funcionar, depois cobrar) — só MEDIR agora.
2. **Firecrawl connector** (founder quer muito): template de conector (api_key no vault) +
   tool `web_scrape` (capability `tenant.firecrawl.execute`) usando a API deles; fallback
   httpx+readability quando não conectado (rotinas de notícias ficam melhores).
3. Escolha de modelo pela corretora: Configurações da corretora → dropdown modelo (forte/
   médio/econômico) gravando em companies.llm_model (JÁ é lido pelo LLMFactory — só UI).

## Autoria de corredores (passo a passo p/ LLMs)
Criar `docs/canon/PLAYBOOK-AUTHORING.md`: como nasce um corredor novo (ex.: Porto Auto):
1) minerar conversas reais (docs/intake) → URA anchors exatas; 2) adicionar playbook em
`corridor_playbooks.py` (dados versionados @vN, NUNCA lógica); 3) golden replay test
(padrão test_spec017_dispatch: URA passo a passo, capturas, handoffs); 4) subservices +
slots mínimos + handoff_triggers; 5) gate INSURER_DISPATCH_LIVE continua único.
Incluir CHECKLIST copy-paste para o chat que for criar o corredor.

## Guia de arquitetura para chats novos (resumo do que é REAL vs legado)
- CÉREBRO ÚNICO: tudo executa via graph Smith (`create_agent_graph`/`process_message`).
  Proibido runtime paralelo (SPEC-002/decisão founder).
- REAL: whatsapp seam (providers/registry/balloons — SendResult usa **.ok**!), dispatch
  engine+router, routine_engine, vision_service, capability Registry + strict mode,
  prompt_effective, Central de Conversas, claim.
- LEGADO/MOCK (não construir em cima): lib/mock/tenant-modules.ts, Portal Lab (fluxo),
  bridge TS de atendimento (flag OFF), z-api legacy provider (compat).
- Envs sensíveis do smith-api que importam: POLICY_INTELLIGENCE_V2=true,
  ATTENDANT_INBOUND_ALLOWLIST (piloto), INSURER_DISPATCH_LIVE=off,
  ROUTINES_ENGINE_ENABLED, BUFFER_* (piso 8s/25s no código), EVOLUTION_*,
  INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H (setar ao abrir gate).
- Regras invioláveis: P0 identidade InfoCap (numapo humano SEMPRE visível ao titular;
  nosnum técnico só via locator); PII do sócio nunca em fixture/commit/log; migrations
  expand-only; TDD house-style; deploy = gatilhos EasyPanel + smoke /health.
