# C2-P2 (parte 1) — Docling corrigido de verdade + plano OAuth/Document Evidence

> Data: 2026-06-23. O batch C2-P2 do GPT são 4 frentes grandes (Docling, OAuth Drive, OAuth Notion, Document Evidence).
> Esta entrega fecha a **frente quebrada (Docling)** com qualidade e sequencia o resto sem mega-commit arriscado.

## 1. Docling — causa-raiz e correção (FEITO)
**Causa:** `docling-service/app/config.py` tinha `REDIS_URL = "redis://localhost:6379/0"` como **default**. O Celery (`celery_app.py`) usa `REDIS_URL` para broker E result backend. Se o container **Worker** sobe **sem `REDIS_URL`** (provavelmente você setou só na API), ele cai silenciosamente em `localhost` → o erro que você viu.

**Correção (sem fallback silencioso, fonte única):**
- `REDIS_URL` agora é **a única fonte** (broker+result) e o default é **vazio**.
- Em `ENV=production` (padrão), se `REDIS_URL` estiver **ausente ou apontando para localhost**, o serviço **FALHA no startup com mensagem clara** (em vez de tentar localhost). localhost só é permitido com `ENV=local|dev|test`.
- Aceita aliases legados (`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`) → normaliza para `REDIS_URL`.
- **/health** honesto: `ok` só com ≥1 worker; senão `degraded`.
- **/readyz** novo: `ready` só quando **Redis + ≥1 Worker + MinIO** estão realmente acessíveis (503 caso contrário).

**Sua ação (a real correção em produção):** no EasyPanel, garanta a **mesma `REDIS_URL`** (URL do Redis interno, NÃO localhost) **na API Docling E no Worker Docling**, e `ENV=production`. Redeploy os dois. Depois, `GET /readyz` deve responder `ready:true`.
Envs (só por nome): `REDIS_URL`, `ENV`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `SERVICE_KEY`. No Smith (backend principal): `DOCLING_SERVICE_URL`, `DOCLING_SERVICE_KEY`.

## 2. Arquitetura (confirmada e mantida)
Uma conexão por serviço por corretora (InfoCap/Drive/Notion) no Vault/`tenant_connections`; o **Capability Registry** decide por papel:
- **Core (interno):** leitura ampla dos dados da própria corretora (já descapado no C2-p1).
- **Even (externo):** só evidência do caso/identidade/apólice.
- **Auxiliares:** só quando a capability declarar.
Document Evidence é a camada canônica de leitura de PDF/apólice sobre `documents`+MinIO+Docling — **não** é segundo RAG.

## 3. Próximas execuções (em sequência, eu executo)
**C2-P2 frente 2 — OAuth Google Drive + Notion (creds já configuradas por você):**
- Rotas web `…/api/connectors/{google-drive,notion}/authorize` + `/callback` (state assinado/anti-CSRF, troca de code→token server-side, token cifrado só no Vault, `tenant_connection` única por corretora, status só `connected` após healthcheck real). Capabilities `knowledge.{google_drive,notion}.read/search`. Catálogo → Conectar → OAuth oficial → volta conectado. Sem rascunho-lixo se OAuth não configurado. Reusa `mcp_oauth_service` (URLs/troca) adaptado ao modelo tenant.

**C2-P2 frente 3 — Document Evidence canônico:**
- Camada de evidência sobre `documents`+MinIO+Docling: upload/seleção de apólice → Docling extrai → evidência por página/trecho/policy_ref/origem (isolada por company). Capabilities `document.evidence.read`/`document.policy_evidence.read`. Quando a InfoCap não trouxer coberturas, o Core lê o **PDF da apólice** e responde com **fonte + página** (o que o seu print pediu). Even só evidência do caso; Auxiliar por capability.

## 4. Por que sequenciar (honesto)
Fazer OAuth (2 provedores, Vault, UI) + Document Evidence (schema, pipeline, runtime) **tudo num commit** sem poder testar o round-trip OAuth offline = risco de "não funciona" de novo. Prefiro entregar **Docling sólido agora** (era o quebrado) e executar OAuth e Document Evidence em seguida, cada um verde. Você pode **deployar o Docling já** (setar `REDIS_URL` no Worker) enquanto eu sigo.

## 5. Próximos passos para um produto extraordinário (visão)
1. **C2-P2 frente 2 (OAuth Drive/Notion)** — fontes privadas conectadas.
2. **C2-P2 frente 3 (Document Evidence)** — Core lê apólice/PDF com citação de fonte/página.
3. **Knowledge OS / RAG curado** — Seed Packs + RAG global/privado + evals, usando os MESMOS documentos canônicos.
4. **5 Auxiliares robustos** (pesquisa, resumo, follow-up, cobrança, leitura de docs).
5. **Skills de Portal** (apólice/status/cobrança/assistência/abertura com approval) sobre o Portal Browser.
6. **WhatsApp/Z-API ao vivo** → corredor Eletricista ponta a ponta.
7. **Hardening final** (SEC-001, FinOps por capability, evals contínuos, isolamento) antes do go-live amplo.
