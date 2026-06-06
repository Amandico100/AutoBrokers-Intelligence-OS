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

## Operating Rule

When canonical docs and historical docs disagree, `docs/canon` wins.
