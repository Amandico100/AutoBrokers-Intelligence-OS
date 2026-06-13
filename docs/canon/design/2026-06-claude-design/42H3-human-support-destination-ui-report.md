# 42H3 — Human Support Destination UI Report

> **Status:** concluído · typecheck verde · build verde · `git diff --check` limpo · **só Web/Next** (sem banco/SQL/schema, sem backend Python, sem RAG/prompts/agentes/WhatsApp/envio externo) · sem deploy automático.
> **Data:** 2026-06-13 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Arquivos criados/alterados
- `app/dashboard/personalizacao/corretora/suporte-humano/page.tsx` (**novo**) — server wrapper.
- `app/dashboard/personalizacao/corretora/suporte-humano/HumanSupportSettingsClient.tsx` (**novo**) — CRUD de destinos humanos.
- `app/dashboard/personalizacao/corretora/page.tsx` (**alterado**) — placeholder → índice com card **"Suporte humano"** linkando para a nova tela.
- `lib/attendance/support-destination-labels.ts` (**novo**) — rótulos/placeholders/options de tipo e provider.
- `docs/canon/design/2026-06-claude-design/42H3-human-support-destination-ui-report.md` (este).

## 2. Rota criada e onde acessar
- **Rota:** `/dashboard/personalizacao/corretora/suporte-humano` (local **oficial** decidido no 42H1P).
- **Acesso:** Dashboard → **Personalização → Corretora → card "Suporte humano" → Configurar**. A página Corretora deixou de ser placeholder e agora mostra o card.

## 3. API consumida (42H2 — não alterada)
- `GET /api/attendance/support-destinations?active=all` (lista).
- `POST` (criar) · `PATCH /[id]` (editar) · `DELETE /[id]` (soft disable).
Client **só** chama a API; **nunca** Supabase direto.

## 4. Decisões de UX
- Header com breadcrumb Personalização / Corretora / Suporte humano, subtítulo pedido e badge **"MVP ativo · sem envio real"**.
- **Alerta informativo:** "Neste MVP, o destino humano será usado para preparar e copiar dossiês. Nenhuma mensagem é enviada automaticamente."
- **Formulário** criar/editar único (controlado por `editingId`): name, tipo (whatsapp_group/individual/email/internal_queue/webhook), provider (manual/zapi/evolution/meta_cloud), **destino/ref** (placeholder contextual por tipo), prioridade, silêncio (min), checkboxes **principal/fallback/ativo**. Botão **"Preencher exemplo"** (só preenche, não salva). Defaults enviados: `active_hours:{}`, `escalation_rules:[]`, `metadata:{source:'dashboard'}`.
- **Lista** (cards): name, `display_ref` mascarado, badges (tipo, provider, **Principal**, **Fallback**, **Ativo/Inativo**), silêncio e prioridade; botões **Editar** e **Desativar** (com `window.confirm`).
- Reuso dos padrões-mestre (`DetailHeader`, `StatusPill`, `Icon`, `GalleryCard`), dark/limpo/compacto, responsivo, coerente com Fila/Casos/Detalhe.
- Estados: loading / error (retry) / empty / loaded / saving / deleting / success (notice).

## 5. Como evita expor `destination_ref` cru
- A lista usa `display_ref` (mascarado pela API) — o componente **nunca** recebe nem mostra o `destination_ref` cru (a API retorna `has_destination_ref` + `display_ref`).
- **Edição:** o campo de destino é **"Novo destino / ref (opcional)"** — em branco = manter o atual (valor não exibido por segurança). Só envia `destination_ref` no PATCH se o usuário preencher; aí a API recalcula o `display_ref`.
- Nada de token/secret/`tenant_connection` secret/service role na UI ou logs.

## 6. Integração com navegação
Card "Suporte humano" adicionado em **Personalização → Corretora** (descrição "Destino para dossiês e transferências quando o agente precisar escalar um atendimento.", status "MVP ativo"). Navegação global **não** foi alterada drasticamente — só a página Corretora virou um índice com o card.

## 7. O que ficou fora (proposital)
`active_hours`/`escalation_rules` avançados no form (defaults enviados); envio WhatsApp/externo; `handoff_dossier`; `approval_request`; testar destino em dry-run (futuro 42H5); alteração de banco/Supabase/backend.

## 8. Checks
| Check | Resultado |
|---|---|
| `npm run typecheck` | ✅ OK |
| `npm run build` | ✅ OK |
| `git diff --check` | ✅ limpo |
| SQL/migration/schema | ✅ nenhum |
| backend Python / Supabase no client | ✅ nenhum |
| RAG/prompts/agentes/WhatsApp/envio externo | ✅ nenhum |
| token/segredo/`destination_ref` cru exposto | ✅ nenhum |

## 9. Deploy recomendado
- **Web apenas** (Next/UI). Sem backend Python, sem SQL/migration.

## 10. Testes manuais (após deploy Web)
1. **Personalização → Corretora → Suporte humano** → aparece o destino existente: "Suporte humano principal", WhatsApp grupo, Manual, `display_ref 120363****6552@g.us`, **Principal**, **Fallback**, silêncio 15 min.
2. **Criar** novo: WhatsApp individual, manual, `5547999999999`, fallback true, primary false → aparece com `display_ref` mascarado (`5547****9999`).
3. **Editar** o novo: silêncio = 20 → salva.
4. **Desativar** o novo → fica "Inativo" (continua na lista com `active=all`).
5. **Chat Core** inalterado: CORE-001 (interno), CORE-007 (Resumo + Follow-up), CORE-006 (NEVOA-791).

## 11. Próximos passos
1. **42H4** — gerador de `handoff_dossier` (read-only do caso).
2. **42H5** — copiar/dry-run de handoff no detalhe do caso (HITL via `approval_requests`), usando o destino primário/fallback configurado aqui.
3. Depois: **42B5B** (Corridor Runtime Step Engine), **42B6** (Dispatch + WhatsApp dry-run/HITL).
