# Índice rápido — Pacote Claude Design (2026-06)

Consulta de 1 linha por arquivo. Detalhe e regras: ver `README.md` e `37A1-adapted-execution-plan.md`.

| Arquivo | Conteúdo (resumo) |
|---|---|
| `Leva 1 - Fundacao Visual.html` | Paleta **Névoa** (`bg #0a0b0d`, `surface #14161a/#1c1f24`, `border #272b31`, `text #f1f3f5`, `muted #828a93`, `accent #6fa6c9`, `success #6ba088`, `warning #c6a065`, `danger #c98585`), **Geist/Geist Mono**, radius ~14px; home chat-first ("Como posso ajudar sua corretora hoje?" + 2 atalhos); sidebar desktop (4 pilares) + bottom-nav mobile. |
| `Leva 2 - Padroes-Mestre.html` | Padrão A **Galeria** (busca + filtros + grid de cards + StatusBadge); Padrão B **Página de detalhe** (breadcrumb + header + tabs + corpo 2 colunas + side card); Padrão C **Modal de permissão** (pode/não pode + RiskBar + faixa HITL); estados (vazio/loading/erro/approval). |
| `Leva 3 - Modulos.html` | Aplicação dos padrões: **Auxiliares** (Meus/Galeria/Execuções), **Auxiliar de Resumo de Atendimentos** (flagship, sem envio externo), **Seguradoras** (lista + detalhe em camadas), **Atendimentos** (lista de casos + caso com timeline + faixa HITL). |
| `HANDOFF-001-engenharia.html` | Contrato técnico: tokens Névoa, Geist, componentes, sistema de status (6 tons), specs por tela e ordem de implementação (B0→B6). Fonte canônica de tokens/specs. |
| `BATCHES-001-claude-code.html` | Cards B‑ICONS + B0→B6 (originais). **Desatualizado quanto ao repo (pnpm, lib/cn.ts, Button.tsx, rotas sem /dashboard).** Usar `37A1-adapted-execution-plan.md` no lugar. |
| `BRIEF-001-claude-design.md` | Brief de entrada do Claude Design (em `../`). |

**Rotas nos mockups:** as Levas 2/3 usam rotas sem `/dashboard` (ex.: `/auxiliares`, `/personalizacao/seguradoras`, `/atendimentos/casos`). **Decisão do Architect: tudo sob `/dashboard/*`** — tratar como inconsistência de mockup.
