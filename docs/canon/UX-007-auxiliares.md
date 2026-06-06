# UX-007 - Auxiliares

Status: canonical initial direction
Product: AutoBrokers.ai
Last updated: 2026-06-06

## 1. Naming Decision

Rotinas are called Auxiliares in AutoBrokers.ai.

The term Auxiliar is more product-native for brokerages and can cover both recurring automations and specialist subagents.

## 2. Definition

Auxiliares are operational automations or subagents that help a brokerage perform specific tasks.

Examples:

- organize pending documents;
- prepare daily summaries;
- monitor renewals;
- help with follow-ups;
- prepare claim status updates;
- consult allowed knowledge and systems;
- draft messages for human approval.

## 3. Technical Base

Auxiliares should use the Smith runtime foundation:

- agents;
- subagents;
- delegations;
- tools;
- MCP;
- RAG;
- documents;
- logs;
- costs and usage tracking.

They should not introduce a second agent runtime.

## 4. UX Inspiration

Claude Routines are a useful UX reference for:

- a gallery of reusable automations;
- clear activation;
- configuration;
- connectors;
- schedule/event/API concepts;
- run history;
- human approval.

This is inspiration only. The AutoBrokers product language is Auxiliares.

## 5. MVP Direction

The first Auxiliares MVP should be:

```txt
gallery -> detail -> activate -> configure minimal fields -> manual run
```

Recommended MVP capabilities:

- global template gallery;
- tenant activation;
- simple configuration;
- manual execution;
- visible run result;
- basic logs;
- disabled or limited risky actions.

## 6. Later Phases

Later phases may include:

- creation by prompt;
- scheduler;
- webhook/API triggers;
- autonomous event execution;
- multi-step routines;
- connector permissions;
- run replay;
- evals;
- tenant-specific custom Auxiliares.

## 7. Permission and HITL Requirements

Auxiliares must eventually declare:

- required connections;
- allowed actions;
- risk level;
- whether human approval is required;
- whether scheduled execution is allowed;
- output type;
- audit events;
- kill switch behavior.

Actions that send messages, change external systems, open protocols, download sensitive documents or use credentials must go through Vault and permission guard.

## 8. Relationship with AutoBrokers

AutoBrokers can explain, recommend, trigger or help configure Auxiliares.

In the MVP, AutoBrokers should not freely create or activate arbitrary automations without a review surface and human approval.
