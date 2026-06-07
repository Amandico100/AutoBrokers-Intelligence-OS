# Claude Design — Pacote de Design (2026-06)

> **Status:** referência de design + baseline de execução
> **Última atualização:** 2026-06-07
> **Produto:** AutoBrokers.ai · **Sistema:** AutoBrokers Intelligence OS
> **Regra de autoridade:** as **Decisões do Architect** (ver `37A1-adapted-execution-plan.md`) **prevalecem** sobre qualquer rota, comando ou nome de arquivo que apareça nos HTML/batches abaixo.

Esta pasta contém a fundação visual e os handoffs de engenharia produzidos pelo Claude Design.
Os arquivos HTML são **mockups e contratos de referência** — não são código a ser copiado literalmente.
Antes de qualquer implementação, leia o **plano adaptado** (`37A1-adapted-execution-plan.md`), que reconcilia este pacote com o **repositório real**.

## O que existe nesta pasta

| Arquivo | Tipo | Papel |
|---|---|---|
| `Leva 1 - Fundacao Visual.html` | Mockup visual | Fundação: paleta **Névoa**, tipografia **Geist/Geist Mono**, chat-first, sidebar desktop + bottom-nav mobile. **Referência visual.** |
| `Leva 2 - Padroes-Mestre.html` | Mockup visual | 3 padrões reutilizáveis: **Galeria**, **Página de detalhe**, **Modal de permissão** + estados. **Referência visual.** |
| `Leva 3 - Modulos.html` | Mockup visual | Aplicação dos padrões a Auxiliares, Auxiliar de Resumo, Seguradoras e Atendimentos. **Referência visual.** |
| `HANDOFF-001-engenharia.html` | Contrato técnico | Tokens, paleta Névoa, Geist, componentes, status, specs por tela e ordem de implementação. **Fonte dos tokens/specs.** |
| `BATCHES-001-claude-code.html` | Cards de batch (original) | B‑ICONS + B0→B6. **Foi escrito sem inspeção do repo real e PRECISA ser adaptado** — ver colisões no plano adaptado. **Não executar verbatim.** |
| `BRIEF-001-claude-design.md` | Brief de entrada | Material que originou o trabalho do Claude Design (em `../`). |
| `README.md` | Índice (este arquivo) | Explica a pasta e aponta para o plano adaptado. |
| `37A1-adapted-execution-plan.md` | Plano de execução | **Documento operacional**: estado real do repo, decisões do Architect e batches adaptados (B0–B4). |
| `INDEX.md` | Índice rápido | Resumo de 1 linha por arquivo HTML para consulta rápida. |

## Como usar este pacote

1. **HTML = referência visual/contrato**, nunca cópia literal. As telas validam o resultado; não ditam caminhos de arquivo.
2. **`BATCHES-001` está desatualizado** quanto ao repo: cita `pnpm`, `lib/cn.ts`, `Button.tsx`, `tailwind.config.js` e rotas sem `/dashboard`. **Use o `37A1-adapted-execution-plan.md` no lugar dele.**
3. **As Decisões do Architect prevalecem** sobre o pacote (resumo abaixo; detalhe no plano adaptado).

## Decisões do Architect que prevalecem (2026-06-07)

1. **AppShell tenant entra em `app/dashboard/layout.tsx`** — nunca em `app/layout.tsx` (quebraria Admin/Login/Landing/Embed).
2. **Package manager = `npm`** — ignorar `pnpm`. Checks: `npm run typecheck` + `npm run build`.
3. **Tokens Névoa → HSL nas variáveis ShadCN existentes** (`--background`, `--foreground`, `--card`, `--primary`, `--border`, …). Não criar sistema paralelo de tokens; não quebrar Admin/Login/Landing.
4. **Todas as rotas tenant sob `/dashboard/*`** — qualquer rota de mockup sem `/dashboard` é inconsistência e deve ser corrigida.
5. **B5 e B6 estão BLOQUEADOS** — B5 (Auxiliar de Resumo funcional) depende de modelo de execuções/runs; B6 (Atendimento real/HITL) depende de modelo de casos. Por ora, somente shells/mocks visuais (B4).
6. **Pastas externas** (`ResultVision`, `AUTOBROKERS_RESULTA_INTAKE`, `AUTOBROKERS_AGENT_OS_WORKSPACE`, `QUARENTENA_LEGADO_2026-04-27`) **não devem ser copiadas, ingeridas, abertas em PII nem importadas**. Têm PII e credenciais. Uso futuro só via Vault + curadoria + redaction.

## Próximo batch executável

**BATCH 37B0 — `B-ICONS` + `B0_ADAPTED_TOKENS_PRIMITIVES`** (primeiro batch de código real: tokens Névoa→HSL, Geist via `next/font`, set de ícones Lucide e sandbox visual; **sem** chat, **sem** AppShell, **sem** módulos). Detalhes e arquivos prováveis no `37A1-adapted-execution-plan.md`.
