# Auditoria factual — Recon de capacidades para a Fase C (leitura real de código)

> Data: 2026-06-23. Método: leitura direta do código (backend Python + frontend Next) e dos seeds. Suporta a [SPEC-014](../../SPEC-014-capability-registry-knowledge-os.md). Sem suposição: cada item aponta arquivo real.

## Resumo executivo
A maior parte da "Fase C" **já está construída**. O trabalho real é **governar** (Capability Registry) e **ligar em produção**, não recriar. Nenhum item abaixo justifica novo motor/serviço paralelo.

## A. Busca / Conhecimento / Memória
- **Busca web** — `backend/app/agents/tools/web_search.py` (`WebSearchTool`) + `backend/app/services/tavily_service.py` (Tavily). **Pronto, desligado**: depende de `settings.TAVILY_API_KEY` (`core/config.py:28`) e da flag `allow_web_search` por agente/empresa (`agents/graph.py:209-215, 245`). Ligar = env + flag. **Não criar Firecrawl agora.**
- **RAG / Knowledge** — `services/search_service.py`, `services/qdrant_service.py` (Qdrant, dim 1536), `services/rerank_service.py` (Cohere), `services/ingestion_service.py`, `services/knowledge_scope.py` (global vs privado), `services/minio_service.py`. `KnowledgeBaseTool` sempre anexada (`graph.py:204`). RAG global controlado por `include_global` (visto na Fase B/P0). **Pronto.**
- **Memória** — `services/memory_service.py` (+ tabelas de memória/sumário de sessão). **Pronto.**
- **Control Plane Read (estado da corretora)** — ainda **não** existe como capability única; hoje o Core tem "consciência de auxiliares" (42A7) e o admin tem `agent-health`. C1 unifica como `control_plane.read` (read-only, sem RAG, sem cross-tenant).

## B. Documentos / OCR / Evidência
- **Docling** — microserviço externo (`services/sanitization_service.py`, `_docling_parse` via `DOCLING_SERVICE_URL` default `http://localhost:8001`, `core/config.py:103-107`), usado na **ingestão de conhecimento** (PDF/DOCX→markdown+OCR+tabelas) com fila/worker (`workers/sanitization_tasks.py`) + MinIO. **Pronto p/ KB**; precisa estar **deployado/saudável** no EasyPanel. **Mídia de atendimento** (`api/attendance_media.py:206`) ainda é **placeholder** — extração madura entra como `platform.document.extract`. **Não criar Azure/Google Document AI.**

## C. InfoCap / Apólice (o ponto que o Founder não aceita refazer — e está certo)
- `backend/app/api/infocap_connector.py` — **completíssimo, chamada real à CorpAPI** (`api.corpnuvem.com`): 4 endpoints internos (chave `X-AutoBrokers-Internal-Key`):
  - `POST /attendance/connectors/infocap/secret` — cifra credencial (Fernet) no Vault (`tenant_connections.encrypted_secret_ref`); nunca loga segredo.
  - `POST .../lookup` — login→token→busca cliente (CPF `/cliente_cpf`, nome `/lista_clientes`)→`/cliente_ligacoes`→`/documentos`→`/documento`; sanitiza (mascara CPF/nome/apólice), ordena por vigência, multiple-matches→humano, monta `coverage_evidence`.
  - `POST .../probe` — descobre endpoint/param/shape sem expor valores.
  - `POST .../policy-detail` — carrega 1 apólice e monta `policy_evidence_pack` (coberturas, sinais residencial/eletricista/assistência, confiança, limitações).
- **Já ligado ao atendimento**: `app/api/attendance/cases/[caseId]/runtime/policy-lookup`, `policy-select`, `reply`, `step`; + `connectors/infocap/{diagnostics,probe,secret,setup}`.
- Classificação: **(1) pronto e real** = todo o código. **(2) pronto sem credencial** = Resulta precisa de credencial+`base_url`. **(3)/(4)** não há reconstrução a fazer.
- C1 promove a `operational.infocap.policy_lookup.read` reutilizável pelo **Core** (governado, com contexto/escopo/auditoria), além do Atendimento.

## D. Execução Smith
- **HTTP Tool Router** — `agents/tools/http_request.py` (`HttpToolRouter`, `create_dynamic_tool`) sobre `agent_http_tools` (`graph.py:252-265`).
- **MCP** — `services/mcp_gateway_service.py` (servers **internos**: `google-calendar`, `google-drive`, `slack`, `github`), `services/mcp_oauth_service.py`, `mcp_servers/*`, `agents/tools/mcp_factory.py` (`graph.py:274-279`).
- **Subagentes/Delegação** — `agents/tools/subagent_tool.py` + `agent_delegations` (`graph.py:312-357`).
- **UCP** — `agents/tools/ucp_factory.py`, `services/ucp_*`.
- **Montagem por agente**: KB (sempre) · web/handoff/csv (flag) · HTTP · MCP · subagentes → `llm.bind_tools(tools)` (`graph.py:367`). **Risco atual**: habilitação por flag solta espalhada (sem governança central) — o Registry resolve.

## E. Conectores / Vault
- **Backend** — Vault completo: `tenant_connections`, `connector_templates`, `permission_grants`, `approval_requests`, `vault_audit_log` (modelo 39A1).
- **Frontend** — `app/api/vault/*` (connections, templates, approvals approve/execute/reject, audit, permissions, whatsapp) + UI `app/dashboard/personalizacao/conectores` (+ `aprovacoes` + `auditoria`). `app/admin/connectors`, `app/admin/integrations`.
- **Templates semeados** (docs/sql): `infocap`, `quiver`, `zapi`/`whatsapp`, `google_drive`, `notion`, `github`, `browserbase`, `insurance_portal`.
- **Gap**: a UI de conectores do tenant hoje é **centrada em WhatsApp**; **não há fluxo OAuth de MCP exposto** ao tenant (os servers MCP existem no backend). C2 adiciona a **galeria categorizada + connect OAuth** (estilo ChatGPT) sobre o que já existe.
- Classificação dos conectores: `platform_owned` (Tavily, Docling) · `tenant_owned` (Drive/Calendar/Slack/GitHub/Notion/Gmail) · `operational_sensitive` (InfoCap/Quiver/Z-API/portais) · `internal_capability` (RAG/memória/control plane).

## F. FinOps / Segurança / Produção
- **FinOps** — `services/usage_service.py`, `token_usage_logs`/`credit_transactions` com `agent_id`; `/api/dashboard/usage` agrupa por agente (TA2-C). Falta propagar **por capability** (C1).
- **Segurança** — `services/encryption_service.py` (Fernet), `services/presidio_service.py` (PII), `services/llama_guard_service.py`, `services/sanitization_service.py`; gates de WhatsApp (`ATTENDANCE_WHATSAPP_ENABLED`, webhook auth), Portal Browser gated/HITL, approvals.
- **Postura de produção (decisão do Founder)**: ligar tudo; manter só guardrails legais/segurança (consentimento WhatsApp, approval p/ ação que escreve/abre sinistro, não afirmar cobertura sem evidência). Esses são **parte do "feito"**.

## Conclusão (1 página)
- **Existe e será reutilizado**: Tavily, Docling, InfoCap (4 endpoints), Vault+UI, MCP servers+OAuth (Drive/Calendar/Slack/GitHub), RAG (Qdrant/MinIO/rerank), memória, atendimento/corredores, WhatsApp/Z-API, FinOps, segurança.
- **Será descartado/recusado**: Composio+Nango juntos; Firecrawl agora; novo OCR; recriar InfoCap/Tavily/Docling; qualquer estrutura paralela.
- **Decisão Composio/Nango/direto**: **direto/interno** (MCP+Vault próprios). Composio/Nango só como provider futuro atrás do Registry, se a superfície SaaS crescer muito.
- **Dois batches**: **C1** Registry+Knowledge OS+Core ligado (produção). **C2** Conectores tenant OAuth+Auxiliares+Skills de Portal (produção).
