# PRD-001 - Visao de Produto

Status: canonical initial version
Product: AutoBrokers.ai
System: AutoBrokers Intelligence OS
Last updated: 2026-06-06

## 1. Vision

AutoBrokers.ai is a multi-tenant SaaS for insurance brokerages. It should feel less like a traditional CRM and more like an intelligence operating system for brokers.

The principal experience is a clean conversation with AutoBrokers, the internal operational agent of the brokerage. Around it, the product will organize Atendimento, Auxiliares, Knowledge, Connectors/Channels, and Settings.

## 2. Audience

Primary users:

- brokerage owners;
- managers;
- insurance operations teams;
- support and service operators;
- future AutoBrokers internal administrators.

The product should help brokerages operate faster, answer better, reduce manual work, and safely use AI with their own data and insurance workflows.

## 3. Problem

Brokerages handle fragmented work across WhatsApp, insurer portals, policy documents, renewals, claims, assistance requests, spreadsheets, internal knowledge, and human follow-up.

The current pain is not only answering customers. It is coordinating the brokerage's operational intelligence across people, systems, documents, channels, and recurring tasks.

## 4. Promise

AutoBrokers.ai gives every brokerage an operational AI layer:

- a central broker-facing agent named AutoBrokers;
- curated service knowledge and insurance workflows;
- future Auxiliares for repeatable tasks;
- controlled access to documents, tools and connectors;
- traceable execution with permissions and auditability.

## 5. Main Modules

| Module | Purpose |
| --- | --- |
| AutoBrokers | Principal internal chat and operational copilot for the brokerage. |
| Atendimento | Operational service module for external conversations, insureds, cases and handoff. |
| Auxiliares | Productized automations/subagents for repeatable brokerage tasks. |
| Conhecimento | Curated knowledge, documents, RAG packages and memory. |
| Conectores/Canais | Vault-backed connections to insurer portals, WhatsApp, systems and APIs. |
| Configuracoes | Tenant setup, users, company preferences and operational limits. |
| Admin Global | Internal AutoBrokers team area for templates, companies, billing, logs and governance. |

## 6. AutoBrokers, Atendimento and Auxiliares

AutoBrokers is the central internal agent of the brokerage. It talks to the broker, manager or operator.

Atendimento is the operational service module for customers, insureds, leads, assistance and claims. It is separate from the central AutoBrokers chat.

Auxiliares are automations or subagents that help the brokerage perform specific tasks. They are not a separate runtime. They should use the existing Smith runtime capabilities: agents, subagents, delegations, tools, MCP and RAG.

## 7. MVP Definition

The current MVP direction is:

1. stabilize canonical documentation and project boundaries;
2. define UX/design direction through Claude Design;
3. keep `/dashboard` as chat-first;
4. evolve the tenant experience without bringing back the card-heavy home;
5. create an Auxiliares MVP with gallery, activation and manual execution;
6. add curated knowledge and controlled RAG;
7. later migrate Atendimento through curated packages.

## 8. Out of Scope Now

The following are not part of this documentation batch:

- redesigning the runtime UI;
- creating a new dashboard layout;
- changing backend behavior;
- running migrations;
- changing Supabase, EasyPanel, Docker, workers or deploy;
- ingesting raw intake material into RAG;
- copying ResultVision or Agent OS folders into the runtime;
- renaming `SmithWidget` or technical assets;
- implementing the Atendimento pilot.

## 9. Naming and Branding Rules

- Product: AutoBrokers.ai.
- System: AutoBrokers Intelligence OS.
- Principal broker-facing agent: AutoBrokers.
- Use AutoBrokers in plural.
- Do not use JARVYS.
- Do not use Agent Smith or Smith as visible product branding.
- Smith is the invisible runtime engine.
- ResultVision is reference, not product identity.
- Agent OS is reference brain/architecture, not active runtime identity.
- Rotinas are called Auxiliares.
- Pages named Estudos must not exist in the final product.
- The old Conversa ao vivo concept must not return.
