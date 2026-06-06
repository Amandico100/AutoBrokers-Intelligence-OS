# ADR-001 - Runtime Architecture

Status: accepted initial canon
Product: AutoBrokers.ai
System: AutoBrokers Intelligence OS
Last updated: 2026-06-06

## 1. Decision

AutoBrokers.ai will be built as:

```txt
AutoBrokers.ai = Product Layer + Smith Runtime Engine + AutoBrokers Domain Brain
```

This decision preserves the working technical runtime while separating product identity and domain intelligence from legacy naming and raw historical material.

## 2. Product Layer

The Product Layer owns:

- visible product identity;
- tenant dashboard UX;
- admin global UX;
- navigation;
- module language;
- broker-facing rules;
- product workflows for AutoBrokers, Atendimento, Auxiliares, Knowledge, Connectors and Settings.

The visible product is AutoBrokers.ai. The broker-facing principal agent is AutoBrokers.

## 3. Smith Runtime Engine

Smith is the technical runtime engine inherited from Agent Smith V6.2. It is kept because it already provides:

- Next.js frontend;
- FastAPI backend;
- LangGraph agent runtime;
- chat streaming;
- agents and subagents;
- delegations;
- tools;
- MCP;
- RAG;
- Qdrant;
- MinIO;
- Redis;
- Supabase;
- billing/costs;
- logs;
- document processing and sanitization paths;
- multi-tenant admin foundations.

Smith must remain invisible as product branding.

## 4. AutoBrokers Domain Brain

The Domain Brain is the curated insurance intelligence layer. It will come from:

- ResultVision as domain and atendimento reference;
- Agent OS / AutoBrokers Intelligence OS V2 as architecture and brain reference;
- future curated packages for corridors, skills, templates, guardrails, knowledge and evals.

The Domain Brain must be transformed into safe runtime artifacts. It must not be copied as raw folders into the official runtime.

## 5. ResultVision Boundary

ResultVision is useful for:

- atendimento concepts;
- WhatsApp/service workflows;
- insurer protocol packs;
- operational queues;
- review engine ideas;
- broker channel and portal research;
- policy and claim domain examples.

ResultVision is not runtime. Do not copy its code, UI, names, routes or data into AutoBrokers Intelligence OS without a specific approved batch.

## 6. Agent OS Boundary

Agent OS / AutoBrokers Intelligence OS V2 is reference brain and architecture. It is not active runtime.

Known risk: the local workspace currently has naming confusion between `AUTOBROKERS_INTELLIGENCE_OS_V2` and `AUTOBROKERS_INTELLIGENCE_V2`. This must be resolved in a future dedicated batch before using it as a canonical runtime source.

## 7. Auxiliares Decision

Auxiliares will use the Smith runtime foundation:

- `agents`;
- subagents;
- `agent_delegations`;
- HTTP tools;
- MCP tools;
- RAG;
- documents;
- logging and costs.

LionClaw, OpenClaw and Claude Routines are inspiration for UX, intelligence patterns and operational behavior. They are not the primary runtime.

## 8. Tenant Dashboard Decision

`/dashboard` must be chat-first.

Do not recreate the rejected card-heavy brokerage home. The initial tenant screen should be clean, similar in spirit to ChatGPT or Claude: AutoBrokers centered, primary input, and at most two shortcuts when UX is defined.

The old Estudos page and old Conversa ao vivo concept must not return.

## 9. Security Decisions

- Do not ingest raw intake material before Vault, classification, redaction and curation.
- Do not run migrations without explicit operational batch approval.
- Do not connect live services from documentation batches.
- Do not print secrets.
- Keep EasyPanel and Supabase changes outside documentation batches.
- Keep historical migrations intact unless a future ADR explicitly approves a migration cleanup.

## 10. Consequences

This architecture lets the project move quickly without creating a second runtime.

It also creates a responsibility: every future product feature must distinguish between technical engine, product language, and curated domain brain.
