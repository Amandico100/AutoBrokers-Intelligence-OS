# AutoBrokers Intelligence OS

AutoBrokers Intelligence OS is the technical and product foundation for AutoBrokers.ai, a multi-tenant SaaS for insurance brokerages.

The product gives each brokerage a principal internal agent named AutoBrokers and will organize service operations, Auxiliares, curated knowledge, connectors, permissions and governance around that agent.

## Status

This repository is the official sandbox/runtime repository for the new AutoBrokers.ai product.

Current status:

- sandbox under active construction;
- Smith-based runtime installed and adapted;
- tenant chat-first experience active at `/dashboard`;
- Supabase sandbox schema/storage already prepared outside this documentation batch;
- EasyPanel sandbox services already created outside this documentation batch;
- canonical documentation now starts in `docs/canon`.

Do not treat this repository as production infrastructure unless a future release document explicitly promotes it.

## Architecture

AutoBrokers.ai is organized in three layers:

```txt
AutoBrokers.ai = Product Layer + Smith Runtime Engine + AutoBrokers Domain Brain
```

### Product Layer

The Product Layer owns visible product identity, UX, navigation, modules, naming, tenant experience and Admin Global behavior.

Visible product names:

- public product: AutoBrokers.ai;
- system/runtime project: AutoBrokers Intelligence OS;
- principal broker-facing agent: AutoBrokers.

### Smith Runtime Engine

Smith is the invisible technical runtime engine. It is not the product brand.

The runtime currently provides:

- Next.js frontend;
- FastAPI backend;
- LangGraph agent runtime;
- chat streaming;
- agents, subagents and delegations;
- tools, MCP and HTTP integrations;
- RAG;
- Qdrant;
- MinIO;
- Redis;
- Supabase;
- billing/cost tracking;
- logs;
- document ingestion/sanitization paths;
- multi-tenant admin foundations.

### AutoBrokers Domain Brain

The domain brain is the curated insurance intelligence layer. It will be built from:

- ResultVision as historical domain and atendimento reference;
- Agent OS / AutoBrokers Intelligence OS V2 as architecture and brain reference;
- future curated packages for corridors, skills, guardrails, templates, knowledge and evals.

Raw legacy folders must not be copied directly into this runtime.

## Canonical Documentation

The active documentation source of truth is:

```txt
docs/canon/
```

Start here:

- `docs/canon/README.md`
- `docs/canon/PRD-001-visao-produto.md`
- `docs/canon/ADR-001-runtime.md`
- `docs/canon/UX-001-navegacao.md`
- `docs/canon/DS-001-design-brief.md`
- `docs/canon/UX-007-auxiliares.md`
- `docs/canon/ADR-002-vault.md`
- `docs/canon/ADR-003-atendimento.md`
- `docs/canon/ROADMAP-001-execucao.md`

Historical documents are archived under `docs/_archive/` when superseded. They are kept for traceability, not as current source of truth.

## Product Boundaries

Important boundaries:

- AutoBrokers is plural and is the fixed name of the principal broker-facing agent.
- JARVYS must not be used.
- Agent Smith and Smith must not be visible product brands.
- Smith remains the technical runtime only.
- ResultVision is a domain/reference repository, not runtime.
- Agent OS / AutoBrokers Intelligence OS V2 is brain/architecture reference, not active runtime.
- Rotinas are called Auxiliares.
- `/dashboard` must remain chat-first.
- Do not bring back a large card-based brokerage home.
- Do not bring back the old Estudos page.
- Do not bring back the old Conversa ao vivo concept.
- Raw intake data must not enter RAG before Vault, classification, redaction and curation.

## Repository Structure

Important folders:

```txt
app/                         Next.js app routes
components/                  React components
lib/                         Frontend/server helper libraries
backend/app/                 FastAPI backend
backend/app/agents/          LangGraph agent runtime
backend/app/api/             Backend API routers
backend/app/services/        Runtime services
backend/supabase/migrations/ Historical sandbox SQL migrations
docling-service/             Document conversion/sanitization service
docs/canon/                  Active canonical docs
docs/_archive/               Historical documentation archive
public/                      Static assets and widget files
```

## Development Commands

Confirmed frontend scripts:

```bash
npm run dev
npm run build
npm run start
npm run lint
npm run typecheck
```

Backend dependencies are listed in:

```txt
backend/requirements.txt
```

Do not run migrations, seed scripts, workers, Docling, deploy commands or external integrations unless a specific operational batch authorizes them.

## Runtime Infrastructure

The sandbox runtime uses:

- Next.js;
- FastAPI;
- Supabase;
- Qdrant;
- MinIO;
- Redis;
- LangGraph;
- MCP/tooling paths;
- EasyPanel sandbox services.

This README intentionally does not contain secrets or live environment values.

## Technical Provenance

The current runtime foundation was adapted from the Agent Smith V6.2 technical base. That provenance explains some remaining technical names in code, migrations, queues, assets or compatibility surfaces.

Those names are not product branding. Future cleanup should happen through scoped technical batches so compatibility, migrations and deployed services are not broken accidentally.

Do not alter licensing files without explicit legal/product direction.

## Safety Rules

- Do not commit `.env` files or secrets.
- Do not print credential values in logs or reports.
- Do not run Supabase migrations without explicit approval.
- Do not deploy from documentation batches.
- Do not copy ResultVision, Agent OS, intake or quarantine folders into this repository without explicit approval.
- Treat raw customer documents, WhatsApp exports, policies, screenshots, audio and portal credentials as sensitive.
