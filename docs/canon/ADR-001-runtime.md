# ADR-001 — Arquitetura de Produto e Runtime

Status: canônico ativo  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Decisão

O AutoBrokers.ai será construído sobre a seguinte composição:

```txt
AutoBrokers.ai = Product Layer + Smith Runtime Engine + AutoBrokers Domain Brain
```

Onde:

- **Product Layer**: experiência visual, navegação, UX, linguagem, módulos e regras de produto do AutoBrokers.ai.
- **Smith Runtime Engine**: infraestrutura técnica herdada do Smith V6.2.
- **AutoBrokers Domain Brain**: conhecimento, políticas, corredores, skills, templates e lógica de seguros curados a partir do Agent OS V2/ResultVision.

---

## 2. O que o Smith representa

Smith é o motor técnico atual.

Componentes aproveitados:

- Next.js App Router;
- FastAPI;
- LangGraph;
- agents;
- subagents;
- delegations;
- tools HTTP;
- MCP;
- RAG;
- Qdrant;
- MinIO;
- Redis;
- Celery/worker;
- Docling;
- billing/custos;
- logs;
- admin multi-tenant;
- chat streaming;
- widget.

Smith não deve ser visível para o cliente final. Strings, README, UI, e-mails, prompts e nomes públicos devem virar AutoBrokers.ai quando apropriado.

---

## 3. O que o ResultVision representa

ResultVision/AutoBrokers antigo é referência de domínio e UX operacional de seguros.

Elementos úteis:

- atendimento;
- filas;
- casos;
- conversas;
- segurados;
- ligações;
- seguradoras;
- corredores;
- canais;
- portais;
- configuração da corretora;
- padrões operacionais de seguro;
- lógica do Agent OS V2.

Não copiar código bruto. Não importar pastas inteiras. Não usar como runtime paralelo sem decisão formal.

---

## 4. O que o Agent OS V2 representa

Agent OS V2 é o cérebro canônico curado.

Ele deve ser transformado em pacotes funcionais e documentos versionados:

- policies;
- skills;
- prompts;
- guardrails;
- corredores;
- templates de atendimento;
- regras de decisão;
- padrões de handoff;
- regras LGPD/PII;
- dossiês e memórias.

Ele não deve ser copiado inteiro para dentro do runtime.

---

## 5. O que o LionClaw/OpenClaw representa

LionClaw/OpenClaw são referências de UX e inteligência agentic.

Uso permitido:

- inspiração para Auxiliares;
- inspiração para execução de tarefas;
- inspiração para experiência estilo copiloto;
- comparação de padrões.

Uso proibido agora:

- virar runtime principal;
- substituir Smith;
- gerar outra base paralela.

---

## 6. Decisão sobre Auxiliares

Auxiliares serão implementados sobre o motor do Smith.

Base técnica provável:

- agents;
- subagents;
- agent_delegations;
- tools HTTP;
- MCP;
- RAG;
- logs;
- usage/costs;
- workers no futuro.

A camada de produto ainda precisa ser criada:

- templates globais;
- galeria;
- instalação por corretora;
- configuração por tenant;
- execuções;
- histórico;
- permissões;
- aprovação humana;
- scheduler.

---

## 7. Decisão sobre Atendimento

Atendimento será reconstruído gradualmente sobre Smith.

Não será feita uma cópia bruta do ResultVision.

Estratégia:

1. mapear conceitos vivos do ResultVision;
2. identificar quais são mockups, quais são código funcional e quais são documentos;
3. criar modelo de dados compatível com Smith;
4. portar uma fatia mínima;
5. só depois trazer corredores, skills e portais.

---

## 8. Decisão sobre n8n

n8n permanece como camada de automação e integração, não como cérebro principal.

Uso previsto:

- webhooks;
- workflows externos;
- integrações com WhatsApp/Evolution;
- integrações com InfoCap/Quiver;
- notificações;
- processos assíncronos.

O cérebro principal e a orquestração de produto devem ficar no Smith/FastAPI/LangGraph.

---

## 9. Decisão sobre dados e conexões

Conexões devem ser reutilizáveis entre módulos.

Exemplo:

```txt
Portal Bradesco conectado uma vez → usado por Atendimento, Auxiliares e AutoBrokers
```

Isso exige um futuro Connection Vault documentado em `ADR-002-vault.md`.

---

## 10. Consequências

### Benefícios

- aproveita infraestrutura pronta;
- reduz risco técnico inicial;
- evita reconstruir RAG, chat, admin e billing do zero;
- mantém domínio de seguros do projeto antigo;
- cria caminho modular para evolução.

### Riscos

- portar Agent OS V2 para LangGraph exige cuidado;
- branding Smith pode vazar;
- documentos antigos podem contradizer decisões novas;
- copiar legado bruto pode recriar bagunça;
- menus e telas podem inflar se não houver governança de UX.

---

## 11. Regra de implementação

Toda implementação deve obedecer:

```txt
Documento canônico → plano técnico → batch pequeno → teste → deploy
```

Claude Code/Codex não devem decidir arquitetura aberta. Eles executam tarefas fechadas.
