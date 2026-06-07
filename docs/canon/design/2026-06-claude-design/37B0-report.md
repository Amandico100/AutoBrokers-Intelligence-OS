# 37B0 — Tokens, Icons and Visual Foundation Report

> **Status:** implementação concluída, **commitada e pushada** · build validado com variáveis **dummy temporárias** no shell (processo único, sem `.env.local`, sem secrets reais) — ver §10/§13.
> **Data:** 2026-06-07 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Fundação visual do AutoBrokers aplicada sobre o sistema de tokens ShadCN existente: paleta **Névoa** (convertida hex→HSL nas variáveis ShadCN), tipografia **Geist/Geist Mono** via `next/font/google`, wrapper de ícones (base Lucide), mark provisório do AutoBrokers, limpeza do `EmptyState` (sem `smith-logo.png`) e rota interna `/sandbox` para inspeção visual. **`typecheck` verde** e **webpack compila com sucesso**. Sem `.env.local`, o **`build` falhava** num motivo **pré-existente e não relacionado a este batch**: a rota de admin `/api/admin/change-password` instancia o Supabase em module-scope e lança `supabaseUrl is required` na fase "Collecting page data". Conforme decisão do fundador, rodei o `build` com **variáveis dummy temporárias** no shell (processo único, **sem criar `.env.local`**, **sem secrets reais**): **passou de ponta a ponta**, gerando todas as rotas, incluindo `/sandbox`. Em seguida: commit `feat(ui): add AutoBrokers visual foundation` + `git push origin main`.

## 2. Arquivos alterados
**Modificados:**
- `app/globals.css` — tokens Névoa (HSL) em `:root`/`.dark`; remove `@import` Plus Jakarta; body usa Geist; vars extras Névoa; preserva resets/utilities/scrollbar/legacy gradient vars.
- `tailwind.config.ts` — adiciona cores Névoa (surface, surface-2/3, foreground-2, faint, success, warning, danger, brand, border.soft), `fontFamily` Geist, `boxShadow` card/modal/frame, radius xl/2xl. **Aditivo** — não remove mapeamentos existentes.
- `app/layout.tsx` — Geist + Geist_Mono via `next/font/google` (CSS vars no `<html>`); favicon `→ /autobrokers-mark.svg`; mantém ThemeProvider/Toaster.
- `components/EmptyState.tsx` — remove dependência de `smith-logo.png`; usa BrandMark geométrico inline (herda cor do tema). Sem mudança de lógica/chat.

**Criados:**
- `components/ui/Icon.tsx` — wrapper de ícone (size, strokeWidth=1.6, a11y, `cn`).
- `lib/icons.ts` — mapa lógico nome→ícone Lucide (pilares, áreas, ações, status, domínio).
- `public/autobrokers-mark.svg` — mark geométrico provisório (monograma abstrato, accent `#6fa6c9`).
- `app/sandbox/page.tsx` — showcase técnico (tokens, tipografia, botões, status, ícones, prévias). **Ver §7 sobre o nome da rota.**
- `docs/canon/design/2026-06-claude-design/37B0-report.md` — este relatório.

## 3. O que foi implementado
Tokens Névoa→HSL mantendo o contrato ShadCN; Geist/Geist Mono; wrapper + mapa de ícones; mark provisório; EmptyState sem branding Smith; sandbox visual. Nenhuma alteração em chat, AppShell, backend, Supabase, admin ou dashboard.

## 4. Tokens — antes/depois (dark, tema ativo)
| Token | Antes (roxo/Smith) | Depois (Névoa) |
|---|---|---|
| `--background` | `247 100% 4%` (#030014) | `220 13% 5%` (#0a0b0d) |
| `--foreground` | `0 0% 100%` | `210 17% 95%` (#f1f3f5) |
| `--card`/`--popover` | `247 100% 4%` | `220 13% 9%` (surface #14161a) |
| `--primary` | `262 80% 50%` (roxo) | `203 45% 61%` (accent #6fa6c9) |
| `--primary-foreground` | `210 40% 98%` | `210 22% 5%` (#07090b) |
| `--secondary`/`--muted`/`--accent` | `217 33% 17%` | `218 13% 13%` (surface-2 #1c1f24) |
| `--muted-foreground` | `250 8% 60%` | `212 8% 54%` (#828a93) |
| `--destructive` | `0 63% 31%` | `0 39% 65%` (danger #c98585) |
| `--border`/`--input` | `217 33% 17%` | `216 11% 17%` (#272b31) |
| `--ring` | `221 83% 53%` | `203 45% 61%` (accent) |
| Extras novos | — | `--surface`, `--surface-2/3`, `--border-soft`, `--foreground-2`, `--faint`, `--success`, `--warning`, `--danger`, `--brand-accent`, `--brand-accent-soft` |

`:root` (light, não prioritário) recebeu um neutro sóbrio com o mesmo accent, para o ThemeToggle não exibir roxo residual.

## 5. Fonte — antes/depois
- **Antes:** `Inter` (em `app/layout.tsx`) + `Plus Jakarta Sans` (`@import` no `globals.css`) — duplicidade/conflito.
- **Depois:** `Geist` (sans) + `Geist Mono` (mono) via `next/font/google`, expostas como `--font-geist-sans` / `--font-geist-mono`; `body` e `font-sans`/`font-mono` (Tailwind) apontam para elas. `@import` Plus Jakarta removido; `Inter` removido.

## 6. Ícones criados
`components/ui/Icon.tsx` (wrapper) + `lib/icons.ts` (mapa Lucide): pilares (autobrokers, atendimentos, auxiliares, personalizacao), áreas (conectores, seguradoras, conhecimento, equipe), ações (novaConversa, buscar, enviar, avancar, voltar), status (success, warning, danger, pendente, aprovacao, alerta) e domínio (whatsapp, email, documento, renovacao, filtros). Não foram refatorados os usos diretos de `lucide-react` já existentes (fora do escopo).

## 7. Sandbox visual criado
`app/sandbox/page.tsx` (rota `/sandbox`) — header com mark, linha dos 4 pilares, swatches de tokens, tipografia, botões (via `components/ui/button.tsx`), 6 tons de status, ícones via wrapper, e duas prévias (mini chat + mini card de auxiliar) sem lógica.

**⚠️ Desvio justificado:** o prompt pedia `app/_sandbox/page.tsx`. No Next.js App Router, pastas com prefixo `_` são **privadas (não roteáveis)** — `app/_sandbox` compilaria mas **não abriria no navegador**, anulando o objetivo de inspeção visual. Criei em `app/sandbox/` (roteável) para você poder abrir `/sandbox`. É uma rota interna sem dados; recomendo removê-la/protegê-la antes de produção. Se preferir o nome `_sandbox` (não navegável), renomeio.

## 8. O que NÃO foi alterado
`app/layout.tsx` **não recebeu AppShell** (só fonte/favicon). Não toquei: `app/dashboard/layout.tsx`, `app/dashboard/page.tsx`, `app/dashboard/chat/page.tsx`, `/api/chat/stream`, `backend/`, Supabase/migrations, `package.json`. Não criei `Button.tsx`/`Tabs.tsx`/`Skeleton.tsx` PascalCase; reuso `lib/utils.ts` (`cn`). Nenhum acesso/cópia/ingestão de `ResultVision`/`INTAKE`/`AGENT_OS`/`QUARENTENA`.

## 9. Branding residual encontrado
- ✅ `Plus Jakarta` e import de `Inter` (fonte) **removidos**.
- ✅ Sem `JARVYS`/`Agent Smith`/`Smith AI`/`Sistema Smith` no código.
- ⚠️ `/smith-logo.png` ainda referenciado (pré-existente, **fora do escopo B0**): `app/admin/layout.tsx`, `app/admin/login/page.tsx`, `app/reset-password/page.tsx` (e demais páginas de auth: forgot-password/register/no-company/pending-approval). `public/widget.js` (`SmithWidget`) e `agentsmith.ai` no embed. → batch de cleanup dedicado (37A/37B).

## 10. Checks executados e resultado
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ **passou** (Geist/Geist_Mono válidos; novos arquivos OK) |
| `npm run build` | ✅ **passou** com variáveis **dummy temporárias** (Supabase/URLs/etc., só no processo do comando — sem arquivo, sem secrets reais). Gerou todas as rotas, incluindo `○ /sandbox`. Sem env, falhava em `/api/admin/change-password` (`supabaseUrl is required`) — bloqueio **pré-existente de ambiente**, não do B0. |
| `git diff --check` | ✅ limpo (apenas avisos benignos `LF→CRLF`) |
| branding scan | ✅ Plus Jakarta/Inter font removidos; smith-logo remanescente listado em §9 |

## 11. Riscos/remanescentes
- **Build local depende de `.env.local`** (Supabase etc.). Sem ele, `next build` não conclui — afeta qualquer batch, não só este. Recomenda-se rodar o build no ambiente com env (EasyPanel/sandbox) ou prover `.env.local` local.
- `bg-blue-600` hardcoded em admin/chat-header não herda o accent Névoa (cleanup futuro).
- `/sandbox` é rota pública sem auth (sem dados) — remover/proteger antes de produção.
- `smith-logo.png` visível em admin/auth (cleanup futuro).
- Radius base mantido (`--radius` 0.5rem) para não alterar admin; novos componentes podem usar `rounded-xl`/`2xl` (14/18px) da Névoa.

## 12. Próximo batch recomendado
**37B1 — AppShell tenant em `app/dashboard/layout.tsx`** (sidebar desktop + bottom-nav mobile), reutilizando tokens/ícones desta fundação. Não tocar `app/layout.tsx` raiz; preservar `TermsAcceptanceModal`.

## 13. Commit e push
**Executados.** Após o `build` verde (com variáveis **dummy temporárias** no shell): commit `feat(ui): add AutoBrokers visual foundation` e `git push origin main`. **Nenhum `.env.local` criado; nenhum secret real usado, impresso ou commitado; código não foi alterado para contornar env; EasyPanel/webhooks não acionados.**
