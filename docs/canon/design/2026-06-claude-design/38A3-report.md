# 38A3 — UI Wiring do Auxiliar Resumo de Atendimentos

> **Status:** concluído, **commitado e pushado** · typecheck/build verdes · **frontend apenas** (sem backend/SQL/migration).
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
O Auxiliar **Resumo de Atendimentos** agora roda **pela interface** — sem DevTools. A página de detalhe tem botão **"Executar resumo agora"** que chama a API real, mostra loading, renderiza o resultado estruturado e trata erros de forma amigável. **Meus Auxiliares**, **Galeria** e **Execuções** consomem dados reais (`installed`/`templates`/`runs`). Tudo em Névoa, reusando os padrões do 37B3/37B4; nenhum backend/SQL tocado.

## 2. Arquivos alterados
**Criados:**
- `components/auxiliaries/ResumoResult.tsx` — renderiza o output estruturado (resumo + tópicos/decisões/pendências/próximos passos + confiança), sem JSON cru.
- `docs/canon/design/2026-06-claude-design/38A3-report.md`.
**Reescritos (mock → funcional, client components):**
- `app/dashboard/auxiliares/galeria/resumo-atendimentos/page.tsx` — execução real + estados.
- `app/dashboard/auxiliares/meus/page.tsx` — consome `installed`.
- `app/dashboard/auxiliares/galeria/page.tsx` — consome `templates` (+ seção "Em breve").
- `app/dashboard/auxiliares/execucoes/page.tsx` — consome `runs` (lista + expandir detalhe).
**Não alterado:** `app/dashboard/auxiliares/page.tsx` (índice já coerente, links corretos) — mantido como server component para não arriscar.

## 3. Telas ligadas ao backend
| Tela | API | Comportamento |
|---|---|---|
| Resumo (detalhe) | `POST /api/auxiliaries/resumo-atendimentos/run` | Executa, mostra loading e renderiza o resultado |
| Meus Auxiliares | `GET /api/auxiliaries/installed` | Lista instalados com StatusPill |
| Galeria | `GET /api/auxiliaries/templates` | Catálogo ativo + "Em breve" |
| Execuções | `GET /api/auxiliaries/runs` (+ `templates` p/ nome) | Lista runs, status, data, resumo curto, tokens, expandir |

## 4. Fluxo do usuário implementado
1. `/dashboard/auxiliares` → **Galeria**.
2. Abrir **Resumo de Atendimentos**.
3. Clicar **"Executar resumo agora"** → loading → **resultado real** (resumo, pendências, próximos passos).
4. Ir em **Execuções** → ver a execução salva (status Concluído, data, resumo curto) e **expandir** para o detalhe.
Esse é o critério de sucesso do batch. Sem seleção de conversa no primeiro corte (o backend escolhe automaticamente).

## 5. APIs consumidas
Via `lib/auxiliaries/api.ts` (já criado no 38A2): `runResumoAtendimentos()`, `fetchInstalled()`, `fetchTemplates()`, `fetchRuns()`. Todas same-origin (cookie de sessão enviado automaticamente). Tipos de `lib/auxiliaries/types.ts`.

## 6. Tratamento de loading/erro/sucesso
- **Loading:** spinner (`renovacao` animate-spin) com texto, em todas as telas.
- **Sucesso:** `ResumoResult` (detalhe e expand de execução).
- **Erros amigáveis (sem stack trace):**
  - Sem conversas (422) → "Ainda não encontramos conversas suficientes para resumir…"
  - 401/403 → "Sua sessão não tem permissão para executar este auxiliar."
  - 500/erro de rede → "Não foi possível executar este auxiliar agora. Tente novamente…"
  - Output inesperado → "Resumo gerado, mas o formato retornado foi inesperado."
  - Falha de listagem → fallback "Não foi possível carregar… Tente novamente." (página não quebra)
- **Vazios:** "Você ainda não ativou nenhum Auxiliar." (Meus) / "Nenhuma execução ainda." (Execuções).
- A Galeria tem **fallback estático** com o card do Resumo, garantindo navegação mesmo se a API falhar.

## 7. Segurança e escopo multi-tenant preservados
- Nenhuma chamada nova ao backend Python; a UI só usa as rotas Next já endurecidas no 38A2.1 (auth por sessão, `company_id` derivado no servidor, chave interna Next↔Backend).
- **Sem IDs fixos** de company/tenant/user/conversation/agent no código. Listagens são escopadas por empresa no servidor.
- Resultado renderizado sem JSON cru; erros sem stack trace/secrets.

## 8. O que NÃO foi alterado
Backend Python, Supabase/migrations/SQL, chat/streaming/RAG/billing/agents/documents/Qdrant/MinIO/Redis/workers, AppShell/layout, `app/dashboard/chat`, admin/auth/landing/public, `package.json`. Sem dependências novas.

## 9. Checks executados
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ passou |
| `npm run build` (env dummy) | ✅ passou (`✓ 92/92`; 5 páginas de auxiliares compiladas) |
| `git diff --check` | ✅ limpo (só `LF→CRLF`) |
| scan azul/branding (auxiliares UI) | ✅ **sem ocorrências** |

## 10. Resultado dos testes possíveis
- **Build/typecheck:** validados localmente (env dummy). As páginas compilam como shells estáticos que buscam dados no client (sob `/dashboard`, atrás de auth).
- **Teste de UI real:** requer ambiente logado + backend no ar (não disponível no shell de build). O caminho funcional foi montado conforme o teste manual de API já aprovado pelo fundador (`{ success: true, run: {...} }`). Validação visual final deve ser feita no deploy (ver §10 do roteiro abaixo).

## 11. Riscos/remanescentes
- **Nomes de colunas em `runs`:** a UI lê `output`, `status`, `created_at`, `template_id`, `token_usage`, `error_message` (com `select('*')` no backend Next). Se algum nome divergir do schema real, a UI degrada graciosamente (campos ausentes simplesmente não aparecem).
- **Nome do auxiliar nas Execuções:** mapeado por `template_id`→nome via `templates`; sem match, usa rótulo padrão "Auxiliar de Resumo de Atendimentos" (não é ID fixo).
- **Índice** (`/dashboard/auxiliares`) ainda usa cards mock de navegação (sem contagens reais) — decisão de não arriscar; pode ganhar contagens depois.
- **Sem seleção de conversa** ainda (backend escolhe a mais recente). Seletor é evolução futura.
- Páginas viraram `'use client'` (perderam `metadata`) — esperado para data-fetching.

## 12. Próximo batch recomendado
1. **Deploy Web** e **smoke test pela UI** (roteiro §4): Galeria → Resumo → Executar → resultado → Execuções.
2. **38A4** (opcional, hardening/produto): seletor de conversa no detalhe; contagens reais no índice; débito de crédito por execução (`credit_transactions`); token interno dedicado (`BACKEND_INTERNAL_API_KEY`).
3. **38B** (segundo Auxiliar): Cobrança com rascunhos aprováveis (introduz HITL real), conforme UX-007.
