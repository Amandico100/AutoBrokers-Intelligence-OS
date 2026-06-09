# 38B — Auxiliar de Follow-up WhatsApp (modo rascunho) Report

> **Status:** concluído, **commitado e pushado** · py_compile/typecheck/build verdes · **gera rascunho, NÃO envia** · sem portal/Evolution/n8n/scraping.
> **Data:** 2026-06-08 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Resumo executivo
Segundo Auxiliar funcional do AutoBrokers: **Follow-up WhatsApp**. Dado um atendimento (opcional) e um objetivo, gera com IA um **rascunho humano** de mensagem de retorno e cria um **`approval_request`** (`whatsapp_send_message_dry_run`) vinculado à conexão WhatsApp **connected** da corretora. A execução acontece depois pelo fluxo HITL do 39A4.3 (aprovar → **executar simulação dry-run**) — **nenhuma mensagem real é enviada**. Reusa 100% do padrão do Auxiliar de Resumo (Next→FastAPI, `auxiliary_runs`, gate de saldo, custo) e do Vault/HITL.

## 2. Arquivos alterados
**Backend:** `backend/app/api/auxiliaries.py` (endpoint `/follow-up-whatsapp/draft` + `_draft_followup` + prompt/modelo).
**Next (novo):** `app/api/auxiliaries/follow-up-whatsapp/draft/route.ts`; `app/dashboard/auxiliares/galeria/follow-up-whatsapp/page.tsx`.
**Next (alterado):** `lib/auxiliaries/api.ts` (`draftFollowUpWhatsapp`), `lib/auxiliaries/types.ts` (`FollowUpDraftResponse`), `app/dashboard/auxiliares/galeria/page.tsx` (card no catálogo).
**SQL (draft, opcional):** `docs/sql/38B-follow-up-whatsapp-seed.sql`.
**Docs:** este relatório.

## 3. Auxiliar criado
- **Nome:** Follow-up WhatsApp · **Slug:** `follow-up-whatsapp` · **Categoria:** Comunicação · **Risco:** Médio · **Envio externo:** Não (dry-run).
- **Função:** gerar rascunho de follow-up + criar pedido de aprovação humana. Casos futuros: renovação, proposta pendente, documento faltando, sinistro, cobrança, assistência, reativação.

## 4. API de rascunho
`POST /api/auxiliaries/follow-up-whatsapp/draft` (backend, chave interna): exige chave interna + **gate de saldo**; resolve `tenant_auxiliary` (slug+empresa+active) **se existir** (opcional); lê mensagens da conversa **se** `conversation_id` (validada por `company_id`); gera **uma** mensagem com `ChatOpenAI` (prompt seguro, ~500 chars, texto puro); registra `auxiliary_runs` (quando instalado) + `track_cost_sync` (token_usage_logs por empresa). Retorna `{success, draft:{message}, run_id?, model}`. **Tolerante:** funciona mesmo sem o `tenant_auxiliary` seedado (ainda gera o rascunho). A rota Next delega com `company_id` da sessão (anti-IDOR) e trata `402` (créditos).

## 5. UI criada
`/dashboard/auxiliares/galeria/follow-up-whatsapp` (DetailShell, abas Rascunho/Como funciona): seletor de atendimento (opcional), **Telefone de destino**, **Objetivo**, botão **Gerar rascunho** → **textarea editável** → **Criar aprovação** + link para Aprovações. Cards de segurança: "Nenhuma mensagem é enviada automaticamente" e "Usa aprovação humana e simulação WhatsApp (dry-run)". Catálogo de Auxiliares agora mostra o card (merge DB + locais, sempre visível).

## 6. Integração com approval_requests
Ao "Criar aprovação", o front chama `POST /api/vault/approvals` (`createApprovalRequest`) com:
`action_type='whatsapp_send_message_dry_run'`, `tenant_connection_id=<conexão WhatsApp connected>`, `risk_level='medium'`,
`preview={titulo:'Follow-up WhatsApp', to_number, message}`, `request_payload={to_number, message, dry_run:true, source:'auxiliary_follow_up_whatsapp'}`.
A auditoria `approval_requested` é gravada pela rota existente. Depois: aprovar → **Executar simulação** (39A4.3) → `whatsapp_dry_run_executed`.

## 7. Como evita envio real
- O Auxiliar **só gera texto** e cria um pedido; **nunca** chama a Z-API.
- A execução usa a rota dry-run **forçada** do 39A4.3 (`force_dry_run=True`, sem `requests.post`).
- Scan confirma: **sem** `requests.post`/`send-text` em `auxiliaries`/UI.

## 8. Como usa WhatsApp connected
O front resolve a conexão WhatsApp do template `whatsapp_zapi` com `status='connected'` (ou `technical_ref_id`) via `fetchConnectorTemplates`+`fetchTenantConnections`; usa o `tenant_connection_id` dela na aprovação. Se não houver conexão conectada, avisa para configurar em Conectores (sem bloquear a geração do rascunho).

## 9. Como registra auxiliary_runs/custo
Reuso do padrão do Resumo: `_create_run` (running) → `_succeed_run`/`_fail_run`, com `token_usage` e `cost_usd`; `usage_service.track_cost_sync(service_type='auxiliary_run', company_id=...)` alimenta `token_usage_logs` (débito assíncrono via Celery, já existente). Quando o `tenant_auxiliary` ainda não foi instalado, o run não é registrado (best-effort), mas custo e rascunho funcionam.

## 10. Checks executados
| Check | Resultado |
|---|---|
| `python -m py_compile` (auxiliaries.py, whatsapp_integrations.py, zapi_provider.py) | ✅ OK |
| `npm run typecheck` | ✅ passou |
| `npm run build` (env dummy) | ✅ passou (rota `follow-up-whatsapp/draft` + página registradas) |
| `git diff --check` | ✅ limpo |
| scan `requests.post`/`send-text` em auxiliares | ✅ sem ocorrências |
| scan credenciais na UI de auxiliares | ✅ sem credenciais (sem token/secret) |

## 11. Como testar manualmente (pós-deploy API + Web)
1. `/dashboard/auxiliares/galeria` → card **Follow-up WhatsApp** → "Ver detalhes".
2. (Opcional) selecionar um atendimento; informar **Telefone de destino**; **Objetivo**: "retomar contato sobre a cotação de seguro auto".
3. **Gerar rascunho** → revisar/editar o texto.
4. **Criar aprovação** → "Aprovação criada".
5. `/dashboard/personalizacao/conectores/aprovacoes` → **Aprovar** → **Executar simulação** → status **executed**.
6. **Auditoria** → `approval_requested`, `approval_approved`, `whatsapp_dry_run_executed`.
7. Confirme: **nenhuma** mensagem real enviada. (Opcional) rode `docs/sql/38B-follow-up-whatsapp-seed.sql` para registrar o run em Execuções.

## 12. Riscos/remanescentes
- **Seed opcional:** sem o `tenant_auxiliary` o Auxiliar funciona, mas o run não aparece em "Execuções". Rodar o SQL draft (revisado) habilita o histórico.
- **Telefone manual:** muitas conversas são web; o telefone de destino é informado manualmente (sem hardcode). Quando houver telefone na conversa, dá para pré-preencher (evolução).
- **Rotação de `ENCRYPTION_KEY`** antes de produção continua pendente (não afeta este batch; o Auxiliar não toca segredo).
- Envio real segue fora de escopo (próximo marco, com gate explícito).

## 13. Próximo batch recomendado
- **Deploy API + Web** e teste manual (§11); rodar o seed se quiser histórico de execuções.
- **38B.1 (opcional):** pré-preencher telefone a partir da conversa WhatsApp quando disponível; permitir tom/idioma.
- **39A5 — Envio real controlado:** flag explícita por conexão + gate de saldo + confirmação dupla, só depois da rotação de chaves.
