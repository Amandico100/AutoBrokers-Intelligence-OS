# ADR-003 - Atendimento

Status: accepted initial canon
Product: AutoBrokers.ai
Last updated: 2026-06-06

## 1. Decision

Atendimento is an operational module separate from the central AutoBrokers chat.

AutoBrokers is the broker-facing internal agent. Atendimento is the customer/insured-facing operational service area for conversations, cases, handoff and insurance workflows.

## 2. Reference Sources

Atendimento should be designed from curated reference material:

- ResultVision for historical product and domain workflows;
- Agent OS for brain, skills, guardrails, corridors and service intelligence;
- raw intake only after Vault and curation.

None of these sources should be copied into the runtime as raw folders.

## 3. Domain Concepts

Future Atendimento packages may include:

- insurers;
- branches;
- corridors;
- subcorridors;
- channels;
- WhatsApp scripts;
- portal flows;
- claim and assistance workflows;
- required documents;
- handoff rules;
- templates;
- guardrails;
- evals.

## 4. Curated Migration

Atendimento must be migrated through packages, not through bulk copying.

Each package should define:

- source;
- scope;
- insurer/branch/channel;
- status;
- assumptions;
- required data;
- actions allowed;
- human approval rules;
- templates;
- tests/evals;
- owner approval.

## 5. Pilot Direction

A future first pilot may focus on a controlled Allianz Residencial flow.

This is not an implementation decision for this batch. It only records the likely pilot direction so future work does not start from a blank page.

## 6. Explicit Non-Goals Now

This batch does not:

- rewrite corridors;
- build the Atendimento UI;
- connect WhatsApp;
- connect insurer portals;
- ingest intake data;
- run n8n;
- run migrations;
- change backend runtime.

## 7. Safety Principles

Atendimento must:

- avoid inventing coverage;
- collect minimum necessary data;
- protect PII;
- respect tenant boundaries;
- separate draft from execution;
- require human approval for risky actions;
- keep audit trails;
- use templates for final customer-facing messages when possible.
