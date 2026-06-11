---
> **Status:** canonical  
> **Versão:** 1.1 — Refoundation & Design Readiness  
> **Última atualização:** 2026-06-11
> **Produto:** AutoBrokers.ai  
> **Sistema:** AutoBrokers Intelligence OS  
> **Função:** índice da documentação canônica ativa  
> **Lei nova:** [SPEC-002](SPEC-002-auxiliares-runtime-smith.md) — Auxiliares usam **Smith Agents/Subagents como runtime** (produto por cima, motor Smith por baixo, Vault governando). Não criar motor paralelo.
> **Lei nova:** [SPEC-003](SPEC-003-knowledge-rag-memory.md) — arquitetura canônica de **Conhecimento/RAG/Memória** em 8 camadas (global / seguradora / tenant / agent / workflow / case / audit / connector). Reusar o RAG do Smith; **não criar motor de RAG paralelo**.
>
> Esta pasta contém a documentação viva que orienta estratégia, UX, runtime, segurança, design e execução.  
> Documentos históricos em `docs/_archive/` não devem orientar decisões atuais, salvo quando forem explicitamente citados por um documento canônico.


# AutoBrokers Intelligence OS Canon

This folder is the active documentation source of truth for AutoBrokers.ai and the AutoBrokers Intelligence OS.

The project is being refounded around a clear separation:

- AutoBrokers.ai is the product.
- AutoBrokers is the principal broker-facing agent.
- Smith is the invisible technical runtime engine.
- ResultVision is historical domain reference.
- Agent OS / AutoBrokers Intelligence OS V2 is domain brain and architecture reference, not active runtime.

Documents in `docs/audits`, `docs/plans`, `docs/adr`, and `docs/sql` are historical unless they are explicitly migrated into this folder. Archived documents remain available for traceability in `docs/_archive`.

## Canonical Documents

| Document | Purpose |
| --- | --- |
| `PRD-001-visao-produto.md` | Product vision, audience, modules, MVP and naming rules. |
| `ADR-001-runtime.md` | Runtime architecture decision and boundaries. |
| `UX-001-navegacao.md` | Navigation architecture for tenant dashboard and admin global. |
| `DS-001-design-brief.md` | Design direction brief for Claude Design. Not the final design system. |
| `UX-007-auxiliares.md` | Initial product and technical direction for Auxiliares. |
| `ADR-002-vault.md` | Initial decision for Vault, credentials, PII and sensitive data boundaries. |
| `ADR-003-atendimento.md` | Initial decision for Atendimento and curated domain migration. |
| `ROADMAP-001-execucao.md` | Execution sequence and responsibility boundaries. |
| `SPEC-002-auxiliares-runtime-smith.md` | Canonical law: Auxiliares = product; Smith Agents/SubAgents = runtime; Vault = governance. |
| `SPEC-003-knowledge-rag-memory.md` | Canonical Knowledge/RAG/Memory architecture (8 layers, scope/curadoria/versioning, legacy migration). |

## Operating Rule

When canonical docs and historical docs disagree, `docs/canon` wins.
