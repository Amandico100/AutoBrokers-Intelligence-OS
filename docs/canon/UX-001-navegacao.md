# UX-001 - Navegacao

Status: canonical initial direction
Product: AutoBrokers.ai
Last updated: 2026-06-06

## 1. Principle

The tenant experience starts with AutoBrokers.

Navigation must support a chat-first product, not a traditional card-heavy dashboard. The product should feel calm, fast, focused and operational.

## 2. Tenant Dashboard

The tenant dashboard is for brokerages.

Current canonical rule:

```txt
/dashboard = AutoBrokers chat-first
```

`/dashboard/chat` may continue to work for compatibility, but `/dashboard` must open the main AutoBrokers experience.

## 3. Initial Tenant Surface

The future initial screen should be close in spirit to ChatGPT and Claude:

- AutoBrokers as the main signal;
- centered primary input;
- minimal chrome;
- no dense home of cards;
- at most two shortcuts in the first screen;
- mobile-first behavior.

The currently approved shortcut concepts are:

- Ver atendimentos;
- Novo auxiliar.

Final placement and styling must be defined by Claude Design.

## 4. Sidebar Direction

The sidebar should remain lean. It should not become a full CRM tree before the product surfaces are ready.

Initial/future groups may include:

- AutoBrokers;
- Atendimento;
- Auxiliares;
- Conhecimento;
- Conectores/Canais;
- Configuracoes.

The Admin Global navigation is separate and internal to the AutoBrokers team.

## 5. Admin Global

Admin Global is for internal AutoBrokers operation and governance:

- companies;
- users and approvals;
- agents/templates;
- billing and FinOps;
- logs;
- documents/knowledge;
- legal documents;
- settings.

Do not design Admin Global as the brokerage's daily product home.

## 6. Navigation by Layers

For richer modules, prefer layered navigation:

```txt
gallery -> detail -> configuration -> permissions -> run/history
```

This applies especially to Auxiliares, connectors, knowledge packages and future Atendimento packages.

## 7. Forbidden Patterns

Do not bring back:

- a big brokerage home filled with cards;
- the old Estudos page;
- the old Conversa ao vivo concept;
- visible Smith or Agent Smith product naming;
- ResultVision visual structure as a direct copy.

## 8. Design References

References for future UX:

- ChatGPT and Claude for calm chat-first surfaces;
- Claude Routines for automation setup concepts;
- Apps/Connectors patterns for connection galleries and permission screens.

These are references, not implementations to copy.

## 9. Boundary

This document defines navigation direction. It does not define final visual layout, final component system or final responsive specifications. Claude Design should produce the detailed UX and visual design before major UI implementation.
