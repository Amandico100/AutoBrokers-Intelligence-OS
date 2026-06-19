# SEC-001A — Supabase Security Apply, Verify & Production Gate Live Validation Report

> **Status:** concluído (parte de código) · **bug 403 corrigido** · testes offline verdes · `typecheck` EXIT=0 · build verde · **apply do SQL no Supabase = runbook para o Founder** (sem acesso MCP ao banco a partir deste ambiente). Nenhum recurso real ativado; gates seguem bloqueando.
> **Data:** 2026-06-19 · **Modelo:** Claude Opus 4.8 · **Branch:** main · **project_ref alvo:** dcajcvlzcjbmyapmklil

## 0. Diagnóstico do teste live (o "erro" que você apontou)
| Rota | Resultado | Veredito |
|---|---|---|
| `GET /api/admin/security/production-gates` | 200, tudo `false`, flags só booleanas | ✅ ok |
| `GET .../skill-factory/candidates` | 200, 9 candidatos | ✅ ok (o 404 anterior **era** lag de deploy — resolvido) |
| `POST .../skill-factory/evaluate` | **403** | ❌ **bug — corrigido** |
| `POST .../relay/start` | **403** | ❌ **bug — corrigido** |
| `POST .../security/production-gates` | 405 | ✅ esperado (rota é GET-only; não vaza nada) |

**Causa raiz:** as rotas **GET** só exigiam `userId`; as **POST** exigiam `companyId`. Nesta sessão o admin é **master admin sem company vinculada** → `getPortalAdminContext` devolvia `companyId=null` → `403 No company associated`. (Nos testes 42X/43P anteriores a sessão já trazia company, por isso passavam.)

## 1. Correção aplicada (de uma vez por todas)
Reescrevi `getPortalAdminContext` (`lib/attendance/portal-admin-context.ts`) com **fallback seguro de company**:
1. usa a company da sessão (admin ou user) se existir;
2. senão, `users_v2.company_id` do `userId`;
3. senão, se houver **exatamente uma** company (piloto single-tenant), usa-a;
4. múltiplas companies sem vínculo → `null` (não adivinha — força escopo explícito).
Como é central, corrige **todas** as rotas POST de portal-browser/skill-factory/security de uma só vez. O `companyId` continua isolando o tenant (sem cross-tenant).

## 2. Por que o SQL não foi aplicado por mim
Este ambiente **não tem acesso MCP ao Supabase** (as ferramentas `mcp__claude_ai_Supabase__*` foram desconectadas). Portanto **não executei SQL no banco real** `dcajcvlzcjbmyapmklil`. O apply/verify é um **runbook** (abaixo) para você rodar no SQL editor do Supabase. Os arquivos SQL do SEC-001 foram revisados e estão **idempotentes e seguros**.

## 3. Revisão de segurança do SQL (pronto para aplicar)
- `SEC-001-supabase-security-diagnostics.sql` — **READ-ONLY** (só `SELECT`); zero risco.
- `SEC-001-security-hardening-migration.sql` — **idempotente e guardada**:
  - PK em `memory_processing_locks` só se a tabela/coluna existirem e não houver PK;
  - índices `IF NOT EXISTS` guardados por existência de coluna;
  - `ENABLE RLS` + policy de isolamento por `company_id` nas 3 tabelas de memória **só se a coluna existir**.
- **Por que é seguro:** RLS habilitado **sem policy** (estado atual via RAG0.1) = **deny-all** para não-service-role. Adicionar a policy de company **só amplia** (mantém service role, que ignora RLS, e opcionalmente libera authenticated com company correta). Ou seja: **não quebra o backend** (service role) nem o que hoje já funciona.
- **Não toca** em `messages`/buckets/funções `SECURITY DEFINER` (alto risco → follow-up manual §6).

## 4. Runbook de apply/verify no Supabase (Founder)
1. **Diagnostics (antes):** rode `docs/canon/design/2026-06-claude-design/SEC-001-supabase-security-diagnostics.sql` no SQL editor. Guarde a saída (policies de memória, anon em `messages`, buckets públicos, SECURITY DEFINER, PK de locks, RLS de `tenant_connections`, governança de `documents`).
2. **Apply (staging primeiro):** rode `SEC-001-security-hardening-migration.sql`. Observe os `RAISE NOTICE` (PK/índices/RLS criados só onde aplicável; tabelas sem `company_id` são "puladas — tratar manualmente").
3. **Verify (depois):** rode o diagnostics de novo → confirmar: memory tables com `policy_count ≥ 1`; `memory_processing_locks` com `pk_count = 1`; índices presentes.
4. **App:** confirmar que o backend (service role) segue normal (RLS não afeta service role).
5. **Prod:** repetir após validar staging.

## 5. Validação live dos gates (após o deploy desta correção)
```js
const g = await (await fetch('/api/admin/security/production-gates')).json();
// global_kill_switch=true; todos *_allowed=false; flags só booleanas
const ev = await (await fetch('/api/admin/portal-browser/skill-factory/evaluate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ portal_id:'allianz__allianznet_corretor_portal_do_corretor', skill_key:'login_check' })})).json();
// agora 200 (era 403): evidence_score ~85, real_action_allowed=false
const r = await (await fetch('/api/admin/portal-browser/relay/start', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ owner_key:'porto', journey:'login', provider:'browserbase' })})).json();
// agora 200 (era 403): production_gate presente, allowed=false
```
**Esperado:** evaluate/relay **200** (403 corrigido); `production_gate` presente; tudo `real_action_allowed=false`.

## 6. Follow-ups manuais de alto risco (NÃO aplicados — plano)
- **`messages` (anon SELECT/realtime):** restringir por company/sessão sem quebrar Realtime. Testar em staging com um cliente realtime antes; manter fallback.
- **Buckets `avatars`/`chat-media`/`voice-messages` públicos:** migrar para privado + **signed URLs**, atrás da flag `MEDIA_PUBLIC_URLS_ENABLED` (default false) e com transição no frontend.
- **Funções `SECURITY DEFINER`:** fixar `set search_path = public, pg_temp` e revisar grants, confirmando assinaturas exatas via diagnostics.

## 7. Flags que continuam false / o que ainda impede o real
`global_kill_switch=true`; `portal_real_action_enabled/portal_login_real/portal_session_capture/external_action_real/insurer_whatsapp_real_send/rag_publish_to_attendance/memory_long_term/web_search_*/media_public_urls` = **false**. `evaluatePortalRealActionGate`/`evaluateExternalActionRealSendGate` retornam `allowed=false` mesmo com todas ligadas. Nada de portal/WhatsApp/Browserbase/credencial real.

## 8. Pode ir para 43P4?
**Código:** sim, após o deploy desta correção (POST routes voltam a 200). **Banco:** somente depois de **você aplicar+verificar** o diagnostics/migration no Supabase (passo §4) e planejar os follow-ups manuais (§6). Recomendação: aplicar o SQL → confirmar verify → então 43P4 (login assistido por humano, com approval + kill switch). **Não** iniciar 43P4 antes do verify do banco.

## 9. Arquivos alterados
- `lib/attendance/portal-admin-context.ts` — `getPortalAdminContext` robusto (fallback de company) + `resolveCompanyFallback`.
- `docs/canon/design/2026-06-claude-design/SEC-001A-...report.md` (este).
(SQL do SEC-001 inalterado — já estava idempotente/seguro; revisado e aprovado para apply.)

## 10. Testes / checks
- `security-production-gates` **31**, `portal-skill-factory` **46**, `portal-skill-dryrun` **39**, `browser-relay-sandbox` **47**, `action-outbox` **42** — verdes.
- `npx tsc --noEmit` EXIT=0 · `npm run build` verde · `git diff --check` limpo.
- Nenhum recurso real ativado; nenhuma chamada a Supabase live a partir deste ambiente.

## 11. Critério de pronto
| Critério | Status |
|---|---|
| diagnostics prontos para rodar | ✅ (runbook §4) |
| migration segura (aplicar/justificar) | ✅ idempotente/guardada; apply = Founder (sem MCP) |
| memory RLS/policies endereçadas | ✅ no SQL (apply pendente no banco) |
| production gates seguem bloqueando | ✅ |
| bug 403 das rotas POST corrigido | ✅ |
| app build/test passa | ✅ |
| follow-ups manuais documentados | ✅ §6 |
| decisão sobre 43P4 | ✅ §8 (após verify do banco) |
