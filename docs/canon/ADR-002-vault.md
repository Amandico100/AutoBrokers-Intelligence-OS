# ADR-002 - Vault, Credentials and Sensitive Data

Status: accepted initial canon
Product: AutoBrokers.ai
Last updated: 2026-06-06

## 1. Decision

AutoBrokers.ai needs a Vault layer for connections, credentials, permissions and sensitive data boundaries.

Vault is not only a place to store secrets. It is the governance layer that decides who can use which connection, for what action, under which approval rule.

## 2. Scope

Vault must eventually govern:

- insurer portal credentials;
- API keys;
- WhatsApp/channel credentials;
- InfoCap and Quiver access;
- MCP/OAuth connections;
- tenant-specific tools;
- sensitive documents;
- permissioned actions;
- audit events.

## 3. Reuse Rule

A connection should be configured once and reused safely by:

- AutoBrokers;
- Atendimento;
- Auxiliares;
- future corridor packages;
- approved tools.

Do not duplicate credentials across modules.

## 4. Intake Boundary

Raw intake material must not be ingested into RAG before curation.

This includes `AUTOBROKERS_RESULTA_INTAKE` and any similar folders containing:

- policies;
- claims;
- WhatsApp exports;
- client conversations;
- screenshots;
- audio;
- video;
- PDFs;
- spreadsheets;
- credentials;
- portal access notes.

## 5. Minimum Safety Requirements

Before raw intake can be used:

1. classify files by sensitivity;
2. detect PII and credentials;
3. separate public, tenant, client and secret data;
4. redact or tokenize sensitive values where needed;
5. define source authority;
6. create curated knowledge packages;
7. keep provenance;
8. test retrieval leakage;
9. define retention and deletion rules;
10. approve ingestion explicitly.

## 6. No Vault, No Raw RAG

Until Vault, classification, redaction and curation rules are in place:

```txt
No raw intake folder can become runtime RAG.
```

Manual reading for architecture and domain understanding is allowed when secrets are not printed and data is not copied into runtime.

## 7. Future Decisions

Future ADRs or implementation specs must define:

- credential storage provider;
- encryption model;
- per-tenant permission model;
- audit log schema;
- approval gates;
- connector lifecycle;
- secret rotation;
- break-glass/admin access policy.
