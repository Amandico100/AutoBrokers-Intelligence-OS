# SPEC-035 — Reorg do Portal Admin + Superfícies do SPEC-034 + Aba Memórias

**Status:** proposta (founder pediu 13/07 — "gestão total pelo portal admin")
**Relação:** absorve a intenção da SPEC-022 (que é do DASHBOARD do corretor — Personalização→Seguradoras) e cria a irmã dela para o ADMIN. Executar em fatias, com deploy por fatia.

---

## 1. Realidade auditada (13/07)

O admin tem **24 rotas** com sobreposições que confundem a gestão:

| Grupo confuso hoje | Rotas | Alvo |
|---|---|---|
| Conversas/logs | `conversations`, `conversation-logs`, `logs` | UMA página "Conversas" com abas (Ao vivo / Logs / Sistema) |
| Financeiro | `billing`, `costs`, `finops` | UM hub "FinOps" com abas (Cobrança / Custos & Tokens / Planos) |
| Conectores | `integrations`, `connectors`, `insurer-action-channels` | UM hub "Conexões" (WhatsApp / Conectores / Canais de seguradora) |
| Conhecimento | `documents`, `knowledge-base` | UMA página "Conhecimento (RAG)" |
| Agentes/prompt | `agent`, `prompt-effective`, `auxiliares`, `routine-templates`, `blueprint-center` | Hub "Inteligência" (Agentes / Prompts / Auxiliares / Rotinas / Blueprints) |
| Usuários | `all-users`, `pending-users`, `team` | UM hub "Pessoas" com abas |

Páginas saudáveis: `companies` (vira o coração — ver §3), `settings`, `legal-documents`, `portal-browser`, `login`.

## 2. Superfícies NOVAS (o backend do SPEC-034 já grava tudo; falta mostrar)

1. **Central de Agentes** — quem são Espelho/Vigia/Sentinela/Cérebro/Cartógrafo/Alfaiate/Auditor/Garimpo/Sugestões, status de cada task (último run, ações do dia), e o glossário vivo (founder: "não só pra mim — para operadores e para as LLMs").
2. **Acionamentos ao vivo** — sessões ativas por corretora (estado, tempo, transcript via Espelho), alertas do Vigia, intervenções da Sentinela.
3. **Insights (Garimpo + Sugestões)** — tabela `broker_insights`: dores/desejos/pedidos ranqueados por corretora + agregado global anonimizado; o que a IA de Sugestões enviou (source=sugestoes_ia) e as respostas.
4. **Qualidade (Auditor)** — `conversation_scorecards`: nota média por corretora/semana, piores conversas com link, flags mais comuns.
5. **Mapas de URA & Alfaiate** — mapas ativos/propostos por seguradora, diff legível, botão **Aprovar (1 clique)** para a classe "approval", histórico de overlays auto-aplicados.
6. **Registro de Seguradoras** — a UI do `insurer_registry` (números ativos, alternativos não confirmados, botão "confirmar troca").

## 3. Princípio organizador: a página da CORRETORA como cockpit

`companies/[id]` vira o cockpit de gestão por corretora com abas: Visão geral (saúde, nota do Auditor, acionamentos) / Tokens & custos / Cobrança / Conexões / Conhecimento / Insights / Configurações. O admin ganha **gestão total** sem caçar em 24 páginas.

## 4. Fatias de execução (ordem)

1. **F1 (backend-first, já dá pra fazer):** endpoints admin de leitura para as superfícies novas (insights, scorecards, sessões ativas, overlays, registry) — leves, dados já existem.
2. **F2 (design):** Claude Design gera os layouts (junto com a aba Memórias do dashboard — mesmo pacote de design; prompt em `PROMPT-CLAUDE-DESIGN-MEMORIAS.md`).
3. **F3 (frontend):** consolidação dos grupos confusos (redirects das rotas antigas — NUNCA quebrar link) + superfícies novas + cockpit da corretora.
4. **F4:** aba Memórias no dashboard do corretor (grafo).

Regras herdadas: `/admin` usa componentes nativos (portais Radix vazam tema); `npx tsc --noEmit` antes de commit; rotas antigas viram redirect, nada de rota paralela nova.

## 5. Relação com a SPEC-022 (dashboard)
A SPEC-022 continua válida e independente (Personalização→Seguradoras do CORRETOR). Recomendação: executá-la na F3/F4 junto com este reorg — mesmo canteiro de frontend, mesma leva de design.
