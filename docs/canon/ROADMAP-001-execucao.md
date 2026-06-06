# ROADMAP-001 — Execução do AutoBrokers Intelligence OS

Status: canônico ativo
Owner: AutoBrokers.ai Architect
Última atualização: 2026-06-06

---

## 1. Regra principal

Nada deve ser implementado por intuição. O fluxo correto é:

```txt
Documento canônico → revisão estratégica → design aprovado → batch técnico pequeno → testes → deploy
```

---

## 2. Fase atual

Estamos na fase de consolidação estratégica e UX. A instalação técnica do Smith sandbox já funcionou. O chat do tenant já respondeu. Agora o foco é transformar o runtime em produto AutoBrokers.ai sem bagunçar o código.

---

## 3. Ordem de trabalho

### Fase 0 — Limpeza e documentação

- Consolidar docs canônicos em `docs/canon/`.
- Parar de usar docs antigos como fonte de decisão.
- Limpar nomes visíveis antigos: Smith, Agent Smith, JARVYS.
- Manter runtime funcional.

### Fase 1 — UX base tenant

- Definir sidebar enxuta.
- Garantir `/dashboard` como chat-first.
- Criar tela inicial limpa do AutoBrokers.
- Manter apenas dois atalhos iniciais: Ver atendimentos e Novo auxiliar.
- Não criar home de cards.

### Fase 2 — Design system

- Criar tokens visuais.
- Definir componentes base.
- Definir padrões de galeria, detalhe e modal de permissão.
- Planejar mobile-first.

### Fase 3 — Auxiliares MVP

- Desenhar galeria de Auxiliares.
- Definir template global no Admin.
- Permitir ativação por corretora.
- Criar execução manual.
- Criar histórico simples.
- Exigir aprovação humana para ações externas.

### Fase 4 — Atendimento MVP

- Reaproveitar conceitos do ResultVision.
- Criar página Atendimentos limpa.
- Listar fila/casos/conversas em sandbox.
- Separar operação de configuração.
- Não portar runtime antigo bruto.

### Fase 5 — Knowledge/RAG mínimo

- Testar upload simples.
- Testar consulta via AutoBrokers.
- Só depois ativar Docling completo.

### Fase 6 — Vault e conectores

- Documentar modelo.
- Criar UI de conectores.
- Começar com conexão simples.
- Evoluir para seguradoras/portais.

---

## 4. Quem faz o quê

### ChatGPT Architect

- decisões estratégicas;
- PRD;
- ADRs;
- UX specs;
- roadmap;
- prompts para Claude/Claude Code/Codex.

### Claude estratégico/design

- revisar docs;
- propor arquitetura visual;
- criar design system;
- criticar navegação;
- desenhar fluxos.

### Claude Code

- executar tarefas fechadas;
- editar código;
- rodar testes;
- fazer commits.

### Codex

- patches mecânicos;
- auditorias;
- limpeza;
- ajustes pequenos.

---

## 5. Critério para liberar Claude Code

Claude Code só deve executar quando existir:

- documento canônico;
- escopo fechado;
- arquivos prováveis;
- fora de escopo explícito;
- critérios de sucesso;
- rollback claro.

---

## 6. Próximos batches recomendados

1. `36A_CANON_DOCS_SYNC`
2. `36B_LEGACY_DOCS_ARCHIVE`
3. `36C_BRANDING_RESIDUAL_CLEANUP`
4. `36D_CLAUDE_DESIGN_BRIEF`
5. `36E_CHAT_FIRST_UI_SPEC`
6. `36F_AUXILIARES_UX_SPEC`
7. `36G_CONNECTION_VAULT_PLAN`
8. `36H_ATTENDANCE_MVP_PLAN`

---

## 7. Proibições atuais

Não implementar agora:

- nova home de cards;
- sidebar gigante;
- scheduler de Auxiliares;
- portal real de seguradora;
- automação externa sem aprovação;
- reescrita do Admin Global;
- cópia bruta do ResultVision;
- cópia bruta do Agent OS V2.
