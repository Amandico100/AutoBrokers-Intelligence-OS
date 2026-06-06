# ROADMAP-001 - Execucao

Status: canonical initial roadmap
Product: AutoBrokers.ai
Last updated: 2026-06-06

## 1. Phase 0 - Stabilization and Canon

Goal: remove ambiguity before more implementation.

Deliverables:

- create `docs/canon`;
- update project README;
- archive obsolete docs;
- document runtime boundaries;
- document Vault and raw intake restrictions;
- document Auxiliares and Atendimento initial decisions.

## 2. Phase 1 - Claude Design / UX Architecture

Goal: define the actual product experience before another major UI pass.

Deliverables:

- tenant chat-first UX;
- navigation architecture;
- visual direction;
- empty state;
- Auxiliares gallery/detail/permissions flow;
- mobile-first behavior;
- Admin Global refinement direction.

## 3. Phase 2 - Tenant Chat-First UX

Goal: evolve the current working chat into the final tenant first surface.

Deliverables:

- polished `/dashboard`;
- central AutoBrokers experience;
- minimal shortcuts;
- responsive sidebar behavior;
- no card-heavy home.

## 4. Phase 3 - Auxiliares MVP

Goal: create the first product layer over the Smith agents/subagents engine.

Deliverables:

- Auxiliares gallery;
- activation;
- minimal configuration;
- manual execution;
- basic run history/logs;
- permission placeholders.

## 5. Phase 4 - Curated Knowledge/RAG

Goal: make knowledge useful without leaking sensitive data.

Deliverables:

- curated knowledge package structure;
- source classification;
- Vault-aware ingestion plan;
- RAG tests;
- provenance and retrieval checks.

## 6. Phase 5 - Atendimento Pilot

Goal: rebuild service intelligence through curated packages.

Deliverables:

- controlled pilot scope;
- likely Allianz Residencial package;
- corridors and templates;
- handoff rules;
- evals;
- no raw copy from ResultVision or Agent OS.

## 7. Phase 6 - Advanced Connectors/Vault

Goal: allow safe reuse of connections across modules.

Deliverables:

- Vault model;
- permission guard;
- connection gallery;
- approval gates;
- audit logs;
- connector lifecycle.

## 8. Phase 7 - Admin Global Refinement

Goal: turn Admin Global into the internal factory and governance layer.

Deliverables:

- templates;
- companies and users;
- billing and FinOps;
- logs;
- knowledge governance;
- auxiliary templates;
- release gates.

## 9. Execution Rules

- No large code batch before canon docs and design direction.
- Claude Design defines layout and visual system.
- Claude Code executes closed frontend/product implementation tasks when approved.
- Codex audits, performs mechanical patches, documentation syncs and checks.
- No Supabase/EasyPanel/deploy changes inside documentation-only batches.
- No raw intake RAG before Vault approval.
