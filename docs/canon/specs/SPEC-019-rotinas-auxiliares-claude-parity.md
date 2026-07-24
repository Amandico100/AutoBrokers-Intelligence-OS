> [!WARNING]
> **STATUS: PARCIALMENTE SUPERADA PELA SPEC-053.**  
> O motor de Rotinas, scheduler, ferramentas conversacionais e UI descritos aqui continuam válidos como fundação existente. A equivalência histórica “Auxiliares = Rotinas” foi revogada. Pela SPEC-053: **Auxiliar = trabalhador instalado; Rotina = gatilho/agendamento; Skill = procedimento; Workflow = fases; Work Run = execução universal**. Em qualquer conflito, as SPECs 052 e 053 prevalecem.

# SPEC-019 — Rotinas & Auxiliares: paridade com Claude Rotinas + reorganização

**Autor**: Fable (líder técnico) · 2026-07-05 · **Status**: CANÔNICO HISTÓRICO, subordinado à SPEC-053  
**Leia antes**: SPEC-052 e SPEC-053.

## Visão histórica
Rotinas permitem que o Chat Principal crie, edite e gerencie agendamentos por conversa, com UI manual completa. Se faltar peça, o chat explica o que deve ser conectado. Templates prontos podem pré-configurar uma Rotina.

> Decisão atual: um template de Rotina não substitui um template de Auxiliar. Um Auxiliar pode possuir uma ou mais Rotinas.

## O que JÁ existe e é REAL — preservar e evoluir
- Motor: `backend/app/services/routine_engine.py` — agenda daily/interval, executor pelo cérebro Smith, session `routine:<id>`, entrega WhatsApp/none, claim atômico, auto-desativação após falhas, scheduler asyncio.
- Tabelas: `routines`, `routine_runs`.
- Tools do chat: `create_routine`, `list_routines` e gestão relacionada.
- UI: `/dashboard/auxiliares/rotinas` e API correspondente.
- Entrega WhatsApp por integração ativa da company.

> Pela SPEC-053, `routine_runs` é história legada/compatível até migração progressiva para `work_runs`. O motor existente deve ser aproveitado; não criar scheduler paralelo.

## O que era MOCK/GAMBIARRA
- `lib/mock/tenant-modules.ts` e páginas baseadas em dados fake devem ser substituídos por dados reais.
- A antiga decisão de transformar toda Galeria de Auxiliares em catálogo de Rotinas está revogada.
- Blueprint Studio continua servindo à configuração/publicação de Agents e componentes técnicos, mas deve se integrar ao modelo canônico de Auxiliares/Skills/Work Runs.

## Decisões históricas ainda válidas
1. **Número dedicado para rotinas/outreach:** pode existir por `purpose=auxiliary`, governado por Vault e políticas atuais.
2. **Contexto próprio por rotina:** conteúdo específico pode ser associado ao agendamento, sem substituir RAG, memória ou Skill.
3. **Proatividade:** pedidos repetíveis podem gerar oferta de automação.
4. **Dependências:** a criação deve verificar WhatsApp, web, InfoCap, portal ou outro conector necessário.
5. **Idempotência:** claim de execução deve ser preservado e evoluído para Work Run.

## Entregáveis históricos

### A — Tools completas do chat — feita
- criar, atualizar, pausar, ativar e excluir rotina;
- pré-checar dependências;
- responder de forma instrutiva;
- testar validações.

### B — UI de Rotinas — feita no essencial
- criar e editar;
- agenda;
- entrega;
- status;
- execuções;
- conectores informativos.

### C — Templates de Rotina
- `routine_templates` continua válido para modelos de agenda/instruções;
- template de Rotina não deve se passar por Auxiliar;
- a Galeria futura deve diferenciar claramente:
  - Auxiliares instaláveis;
  - Skills;
  - templates de Rotina;
  - workflows;
  - conexões necessárias.

### D — Robustez do executor
- timeout;
- retenção governada;
- falhas;
- retries;
- migração para worker durável e Work Run pela SPEC-055.

### E — Contexto/conhecimento da Rotina
- pode existir como parâmetro operacional;
- não deve se transformar em segundo RAG;
- procedimentos reutilizáveis devem migrar para Skills;
- fatos duráveis devem seguir a SPEC-052.

## Modelo canônico atual

```text
Auxiliar
├── Skill(s)
├── runtime Smith/executor/workflow
├── Connector(s)
├── policy
├── Rotina(s), quando recorrente
└── Work Runs
```

Exemplo:

```text
Auxiliar: Analista Executivo
Skill: Relatório Executivo Semanal
Rotina: sexta-feira às 17h
Work Run: execução da semana 30
Artifacts: relatório web + PDF
Delivery: WhatsApp e e-mail
```

## Regras atuais

- Não criar motor paralelo.
- Não tratar Rotina como Auxiliar.
- Não tratar o prompt de uma Rotina como Skill completa quando houver procedimento reutilizável.
- Não criar nova história de execução após a implantação de Work Run.
- Não apagar `routine_runs` antes de inventário, backfill e validação.
- Não colocar segredo em instruções/contexto.
- Ações externas passam por capability, Vault e approval executável.
- Toda futura mudança deve declarar Admin Projection.
- A execução durável será governada pela SPEC-055.
- A Factory de Auxiliares e Rotinas será governada pela SPEC-058.

## Migração futura

```text
routines
→ permanecem como gatilhos/schedules

routine_templates
→ permanecem como templates de gatilho

routine_runs
→ compatibilidade histórica
→ backfill para work_runs
→ leitura canônica por work_runs
```

Nenhum dado deve ser apagado durante a primeira fase de consolidação.
