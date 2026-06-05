# BATCH 35C1 - Brand Plural and DB Cleanup

Date: 2026-06-05
Scope: product naming cleanup, sandbox SQL cleanup artifact, recent docs alignment.
Repository: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Intelligence-OS`

## 1. Resumo executivo

Este batch consolida a decisao de produto de usar **AutoBrokers** no plural como nome visivel do agente principal/chat da corretora.

O patch troca textos user-facing e defaults seguros que ainda usavam o singular ou nomes antigos. Nao houve rename agressivo de rotas, tabelas, colunas, componentes ou servicos. O runtime Smith permanece como motor tecnico por baixo.

Tambem foi criado um SQL manual e idempotente para limpar registros existentes do banco sandbox, sem apagar dados e sem mexer em creditos, usuarios, empresas, documentos ou custos.

## 2. Decisao de nome

| Area | Nome aprovado |
| --- | --- |
| Produto/plataforma | AutoBrokers Intelligence OS |
| Produto publico | AutoBrokers.ai |
| Agente principal/chat da corretora | AutoBrokers |
| Agente temporario de sandbox | AutoBrokers Sandbox |

O nome do agente principal e fixo e nao deve ser personalizado por corretora.

## 3. Onde "Sandbox" fica temporariamente

`Sandbox` pode continuar aparecendo apenas em dados e fluxos tecnicos do ambiente de teste, especialmente no agente criado pelo bootstrap de tenant.

Antes de producao, `AutoBrokers Sandbox` deve virar apenas `AutoBrokers` nos dados finais e prompts finais.

## 4. Arquivos alterados

### UI e defaults TypeScript/React

- `components/UnifiedSidebar.tsx`
- `components/Sidebar.tsx`
- `components/EmptyState.tsx`
- `components/HeroSection.tsx`
- `components/admin/AgentConfigModal.tsx`
- `components/admin/UCPConfigTab.tsx`
- `app/admin/companies/page.tsx`
- `app/admin/conversations/page.tsx`
- `app/api/admin/sandbox/bootstrap-tenant/route.ts`

### Backend Python

- `backend/app/__init__.py`
- `backend/app/api/agent_config.py`
- `backend/app/api/agents.py`
- `backend/app/api/webhook.py`
- `backend/app/core/constants.py`
- `backend/app/core/prompts.py`
- `backend/app/factories/llm_factory.py`
- `backend/app/mcp_servers/__init__.py`
- `backend/app/services/langchain_service.py`
- `backend/app/services/mcp_oauth_service.py`
- `backend/app/services/memory_service.py`

### Docs recentes

- `docs/adr/ADR-001-runtime.md`
- `docs/audits/35A-inventory.md`
- `docs/audits/35B-branding.md`
- `docs/plans/35C-home-plan.md`

### Novo artefato SQL

- `docs/sql/35C1-brand-plural-cleanup.sql`

## 5. Ocorrencias trocadas

| Antes | Depois | Tipo |
| --- | --- | --- |
| AutoBroker | AutoBrokers | Textos visiveis, prompts defaults, fallbacks |
| AutoBroker Sandbox | AutoBrokers Sandbox | Agente sandbox/bootstrap |
| Slug `autobroker-sandbox` | `autobrokers-sandbox` | Bootstrap sandbox |
| Nomes antigos de agente nos docs recentes | AutoBrokers ou "nome legado" | Documentacao recente |
| Smith visible fallback/defaults | AutoBrokers / AutoBrokers Intelligence OS | UI/defaults seguros |

## 6. Ocorrencias mantidas por seguranca

| Ocorrencia | Motivo |
| --- | --- |
| `public/widget.js` / `SmithWidget` | API global do widget; renomear agora pode quebrar embeds. |
| `backend/supabase/migrations/*` | Migrations historicas; nao editar nem rodar neste batch. |
| `SmithGuardrail` | Nome tecnico de classe/import; trocar exige refactor real. |
| `LangSmith` | Nome de ferramenta externa de observabilidade. |
| Headers `Smith-*` em UCP/storefront/Shopify | Nomes tecnicos de integracoes herdadas; deixar para cleanup tecnico futuro. |
| Docs de ADR/audits que mencionam Smith como runtime | Permitido: Smith continua motor tecnico por baixo. |

## 7. SQL criado

Arquivo:

```txt
docs/sql/35C1-brand-plural-cleanup.sql
```

O SQL inclui:

- SELECTs de diagnostico para `public.agents`;
- SELECTs de diagnostico para `public.conversations`;
- SELECT diagnostico para `public.conversation_logs`;
- UPDATE idempotente de `public.agents`;
- UPDATE idempotente de `public.conversations.agent_name`;
- UPDATE restrito de `public.conversations.title` apenas para titulos tecnicos automaticos;
- SELECTs pos-update para conferir sobras.

O SQL nao deve ser rodado automaticamente. Ele deve ser copiado manualmente para o Supabase SQL Editor do sandbox.

## 8. Instrucoes para executar no Supabase

1. Abrir o projeto Supabase sandbox, nao o banco antigo/producao.
2. Abrir SQL Editor.
3. Copiar todo o conteudo de `docs/sql/35C1-brand-plural-cleanup.sql`.
4. Rodar e revisar os SELECTs de diagnostico.
5. Confirmar que nenhum update toca usuarios, empresas, creditos, documentos ou custos.
6. Verificar os SELECTs pos-update.
7. Fazer novo teste no chat tenant.

## 9. Checks executados

| Check | Resultado | Observacao |
| --- | --- | --- |
| `git diff --check` | OK | Sem erro de whitespace; Git avisou apenas CRLF futuro em docs. |
| `npm run typecheck` | OK | `tsc --noEmit` concluiu com exit 0. |
| `npm run build` | OK com env dummy local | Primeira execucao sem dummy travou por timeout; segunda passou com placeholders locais, sem gravar `.env` e sem segredo real. |
| `python -m py_compile ...` | OK | Arquivos Python alterados compilaram sem erro. |
| `rg` de nomes antigos | OK com sobras classificadas | Sobras apenas em migrations historicas, SQL manual, widget/global API, LangSmith e nomes tecnicos internos. |

Avisos nao bloqueantes do build:

- `SendGrid API key not configured`; esperado no sandbox.
- `Browserslist` desatualizado; nao bloqueia este batch.
- warnings de cache webpack por strings grandes; nao relacionados ao branding.

## 10. Testes manuais pos-deploy

Depois de redeploy Web/API, testar:

1. `/dashboard/chat` nao deve mostrar nome antigo.
2. Sidebar deve mostrar `AutoBrokers`.
3. Empty state deve mostrar `Bem-vindo ao AutoBrokers`.
4. Bootstrap sandbox deve criar/mostrar `AutoBrokers Sandbox`.
5. Chat deve continuar respondendo.
6. `/admin/companies` deve continuar funcionando.

## 11. Riscos restantes

| Risco | Severidade | Observacao |
| --- | --- | --- |
| Dados antigos no Supabase ainda exibirem nome antigo antes do SQL manual | P1 | Corrigir executando o SQL sandbox. |
| Widget global ainda se chamar `SmithWidget` | P2 | Exige plano de compatibilidade/alias futuro. |
| Assets ainda usarem nome de arquivo `smith-logo.png` | P2 | Arquivo tecnico; troca visual fica para branding visual futuro. |
| Migrations historicas citarem Smith | P3 | Nao afeta UI; nao editar migrations antigas. |
| Build demorado | P2 | Passou, mas levou varios minutos; investigar depois se virar gargalo. |

## 12. Proximo batch recomendado

Seguir para:

```txt
BATCH_35D_AUTOBROKERS_HOME_PATCH
```

Objetivo: implementar a primeira Home AutoBrokers em `/dashboard`, mantendo `/dashboard/chat` funcional e sem mexer em RAG, Worker, Docling, WhatsApp, InfoCap, n8n ou migrations.
