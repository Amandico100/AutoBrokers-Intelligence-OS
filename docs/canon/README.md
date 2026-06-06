# AutoBrokers Intelligence OS — Documentação Canônica

Status: fonte oficial de produto, UX, runtime e roadmap  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Objetivo desta pasta

Esta pasta substitui os documentos antigos de batches, auditorias e planos temporários criados durante a instalação do Smith sandbox.

A partir de agora, qualquer IA, dev, designer, Claude Code, Codex ou colaborador deve começar por estes documentos antes de propor ou implementar mudanças.

Os documentos antigos em `docs/audits/`, `docs/plans/` e `docs/adr/` foram úteis como histórico, mas não devem mais ser usados como fonte de decisão quando conflitarem com esta pasta.

---

## 2. Ordem obrigatória de leitura

1. `PRD-001-visao-produto.md`
2. `ADR-001-runtime.md`
3. `UX-001-navegacao.md`
4. `DS-001-design-system.md`
5. `UX-007-auxiliares.md`
6. `ADR-002-vault.md`
7. `ADR-003-atendimento.md`
8. `ROADMAP-001-execucao.md`

---

## 3. Decisões principais já fechadas

- O produto se chama **AutoBrokers.ai**.
- O sistema operacional interno se chama **AutoBrokers Intelligence OS**.
- O agente central da corretora se chama **AutoBrokers**, no plural.
- Não usar `JARVYS`, `Smith`, `Agent Smith` ou `LionClaw` como nome visível para cliente.
- A experiência da corretora é **chat-first**.
- `/dashboard` deve ser o chat principal, não uma home de cards.
- A home deve ser limpa, estilo ChatGPT/Claude, com no máximo dois atalhos iniciais: **Ver atendimentos** e **Novo auxiliar**.
- O Smith é o runtime técnico, não o produto.
- O ResultVision/AutoBrokers antigo é referência de domínio e atendimento, não fonte para cópia bruta.
- O Agent OS V2 é o cérebro canônico curado, não uma pasta a ser copiada inteira para o runtime.
- O motor de Auxiliares deve usar a infraestrutura do Smith: agents, subagents, delegations, tools, MCP, RAG, logs e custos.
- O LionClaw/OpenClaw/Claude Routines são referências de inteligência e UX, não runtime principal.

---

## 4. Regra de governança

Nenhuma nova tela, módulo, sidebar ou fluxo deve ser implementado apenas por intuição do Codex/Claude Code.

Fluxo correto:

```txt
Arquitetura/Produto documentado → Design/UX aprovado → Batch técnico pequeno → Teste → Deploy
```

---

## 5. O que fazer com documentos antigos

Documentos antigos devem ser tratados como histórico, não como fonte de verdade.

Recomendação operacional:

- mover para `docs/_archive/` ou excluir após validação do fundador;
- manter apenas esta pasta `docs/canon/` como documentação ativa;
- quando houver conflito, prevalece `docs/canon/`.
