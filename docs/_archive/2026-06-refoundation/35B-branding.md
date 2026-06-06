# BATCH 35B - Branding base AutoBrokers

Data: 2026-06-05  
Escopo: patch controlado de textos visiveis, labels, prompts default e branding base.  
Repositorio: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Intelligence-OS`

## 1. Resumo do que foi alterado

Este batch removeu branding visivel Smith/nome legado das rotas principais e fixou a nomenclatura de produto:

- Produto/sistema: `AutoBrokers Intelligence OS`
- Produto publico: `AutoBrokers.ai`
- Agente central: `AutoBrokers`
- Agente sandbox: `AutoBrokers Sandbox`

Nao houve redesign, criacao de paginas, alteracao de infraestrutura, migrations, Supabase, EasyPanel, RAG, Worker, Docling, WhatsApp, InfoCap, n8n, corredores, Agent OS V2 ou Auxiliares.

## 2. Arquivos alterados

| Arquivo | Tipo de alteracao |
| --- | --- |
| `app/layout.tsx` | Metadata do app para AutoBrokers Intelligence OS |
| `app/admin/layout.tsx` | Branding lateral do Admin |
| `app/admin/login/page.tsx` | Branding do login Admin |
| `app/admin/page.tsx` | Subtitulo do dashboard Admin |
| `app/admin/companies/page.tsx` | Fallback do alerta de bootstrap sandbox |
| `app/admin/conversations/page.tsx` | Fallback de nome de agente |
| `app/admin/billing/page.tsx` | Texto de plano/billing |
| `app/api/admin/sandbox/bootstrap-tenant/route.ts` | Nome, slug e prompt do agente sandbox |
| `app/embed/[agentId]/page.tsx` | Powered by do embed |
| `app/login/page.tsx` | Alt text do logo |
| `app/register/page.tsx` | Alt text do logo |
| `app/forgot-password/page.tsx` | Alt text do logo |
| `app/reset-password/page.tsx` | Alt text do logo |
| `app/pending-approval/page.tsx` | Alt text do logo |
| `components/UnifiedSidebar.tsx` | Branding do tenant sidebar |
| `components/Sidebar.tsx` | Branding de sidebar legado |
| `components/EmptyState.tsx` | Estado vazio do chat |
| `components/HeroSection.tsx` | Landing/hero branding |
| `components/admin/AgentConfigModal.tsx` | Prompt default de agente |
| `components/admin/WidgetConfigTab.tsx` | Powered by do widget |
| `components/admin/UCPConfigTab.tsx` | Texto visivel do UCP |
| `lib/email.ts` | E-mails gerados pelo frontend/server routes |
| `backend/app/main.py` | Titulo/descricao/health service da API |
| `backend/app/api/webhook.py` | Fallback de nome de agente webhook |
| `backend/app/core/prompts.py` | Prompt base tecnico do agente |
| `backend/app/services/langchain_service.py` | Prompt default backend |
| `backend/app/services/email_service.py` | Rodape de e-mails backend |
| `backend/app/services/billing_service.py` | Assinatura de e-mail billing |
| `backend/app/workers/billing_core.py` | Rodape de e-mails do worker |

## 3. Ocorrencias trocadas

| Antes | Depois | Motivo |
| --- | --- | --- |
| `Smith` em UI de chat/empty state | `AutoBrokers` | Agente central fixo da corretora |
| Nome legado do agente | `AutoBrokers` ou `AutoBrokers.ai` | Remover marca/persona antiga da UI final |
| `AutoBrokers Intelligence OS` | `AutoBrokers Intelligence OS` | Nome visivel do sistema |
| `AutoBrokers v6.2` | `AutoBrokers Intelligence OS` | Login/landing/Admin |
| `Bem-vindo ao Smith` | `Bem-vindo ao AutoBrokers` | Experiencia tenant |
| `Seu assistente pessoal com IA` | `Seu copiloto operacional para seguros` | Posicionamento AutoBrokers |
| Nome sandbox legado | `AutoBrokers Sandbox` | Manter sufixo sandbox apenas no ambiente de teste |
| `autobrokers-sandbox` | `autobrokers-sandbox` | Slug do agente sandbox futuro |
| `Smith Agent` fallback | `AutoBrokers` fallback | Nome default visivel |
| `Equipe Smith` | `Equipe AutoBrokers` | E-mails |

## 4. Ocorrencias mantidas por serem tecnicas

| Ocorrencia | Motivo para manter |
| --- | --- |
| `public/widget.js` com `SmithWidget` | Nome de API global do widget; renomear agora pode quebrar embeds existentes. |
| `backend/supabase/migrations/*` | Migrations historicas do Smith; nao devem ser editadas neste batch. |
| `backend/app/agents/guardrails.py` / `SmithGuardrail` | Nome de classe tecnica; renomear exigiria refactor/imports. |
| `LangSmith` | Produto externo de observabilidade da LangChain, nao branding Smith do produto. |
| `User-Agent: Smith-*` em UCP/Shopify/storefront | Header tecnico de integracao; deixar para fase de cleanup tecnico. |
| `backend/app/core/constants.py` e docstrings internas | Comentarios tecnicos internos; nao aparecem na UI principal. |
| `X-Title: AutoBrokers` em chamadas LLM/OpenRouter | Header tecnico; pode ser revisado depois sem bloquear branding visual. |
| `schema_completo.sql` default `Smith Agent` | Schema historico; nao rodar/editar migration neste batch. |

## 5. Checks executados

Comandos executados:

```txt
rg -n "Smith|AutoBrokers|nome-legado|Sistema Smith" app components lib public backend --glob '!node_modules' --glob '!.next'
npm run typecheck
npm run build
git diff --check
python -m py_compile backend/app/main.py backend/app/api/webhook.py backend/app/core/prompts.py backend/app/services/billing_service.py backend/app/services/email_service.py backend/app/services/langchain_service.py backend/app/workers/billing_core.py
```

Resultados:

| Check | Resultado | Observacao |
| --- | --- | --- |
| `rg` | OK com sobras tecnicas classificadas | Sobras apenas em widget API, migrations, LangSmith, classes/headers tecnicos e comentarios internos. |
| `git diff --check` | OK | Sem erro de whitespace; Git reportou apenas avisos CRLF em alguns arquivos. |
| `npm run typecheck` | OK | `tsc --noEmit` concluiu com exit 0. |
| `npm run build` | OK com env dummy local | Primeiro build falhou por falta de env local; segundo build passou com placeholders locais de Supabase/Stripe sem segredo real e sem gravar `.env`. |
| `python -m py_compile` | OK | Arquivos Python alterados compilaram sem erro. |

## 6. Riscos restantes

| Risco | Severidade | Observacao |
| --- | --- | --- |
| Branding tecnico Smith ainda em simbolos internos | P2 | Mantido para evitar refactor amplo. |
| Widget global ainda se chama `SmithWidget` | P2 | Requer plano de compatibilidade/alias. |
| Migrations historicas citam AutoBrokers | P3 | Nao afeta UI; nao editar migrations antigas agora. |
| Assets ainda usam arquivo `smith-logo.png` | P2 | Conteudo/arquivo do logo deve ser tratado em branding visual posterior. |
| Slug antigo `autobrokers-sandbox` pode existir em dados ja criados | P2 | Novo bootstrap usa `autobrokers-sandbox`; dados antigos podem precisar ajuste manual depois. |

## 7. Proximo batch recomendado

Proximo batch:

```txt
BATCH_35C_AUTOBROKER_HOME_PLAN
```

Objetivo:

- Definir a Home AutoBrokers sem implementar pesado.
- Decidir cards, atalhos, menu lateral final e o que fica para fase 2.
- Manter RAG, Auxiliares, Docling, Worker, WhatsApp, InfoCap, n8n e Agent OS V2 fora do escopo.
