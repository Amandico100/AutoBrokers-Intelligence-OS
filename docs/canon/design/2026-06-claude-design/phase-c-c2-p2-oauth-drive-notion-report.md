# C2-P2 frente 2 — OAuth oficial Google Drive + Notion (conectar estilo ChatGPT)

> Data: 2026-06-23. Tenant-scoped (modelo `tenant_connections`+Vault), reusando encryption/Vault/connector_templates. Sem estrutura paralela.

## O que entrou
Fluxo OAuth oficial no Dashboard: **Catálogo → Conectar → tela oficial do provedor → volta Conectado ✓**. Sem login/senha do Google/Notion dentro do AutoBrokers; **sem aprovação para conectar**; **sem rascunho-lixo** se o provedor não estiver habilitado.

- **Next (web):**
  - `lib/connectors/oauth-providers.ts` — config de Google Drive (scope `drive.readonly`) e Notion (lê envs do serviço web).
  - `app/api/connectors/[provider]/authorize/route.ts` — inicia OAuth com **state assinado em cookie httpOnly** (anti-CSRF) + company; se não configurado → volta com aviso "não habilitado".
  - `app/api/connectors/[provider]/callback/route.ts` — valida state, **troca code→token server-side**, grava CIFRADO via backend, redireciona com aviso de sucesso. Token nunca vai ao browser/logs.
  - `conectores/page.tsx` — card Drive/Notion abre o OAuth (não cria rascunho); aviso de retorno (`?connected`/`?connector_error`).
- **Backend (Python):**
  - `app/api/oauth_connectors.py` — `POST /connectors/oauth/store` (chave interna): cifra `{access_token, refresh_token}` (Fernet) e faz **upsert de UMA `tenant_connection`** por corretora+template (status `connected`), respeitando o índice singleton. Reusa `encryption_service` + `tenant_connections` (nada paralelo).

## Arquitetura (mantida)
Uma conexão Drive/Notion por corretora (token no Vault). Core lê/usa conforme Registry; Even não recebe acesso cru; Auxiliar só por capability. As capabilities `tenant.google_drive.read` e `tenant.notion.read_write` já existem no catálogo (SPEC-014).

## 🔑 Suas tarefas (para o OAuth funcionar de verdade)
1. **Redis do Docling** (pendente do passo anterior): mesma `REDIS_URL` na API + Worker + `ENV=production`; `/readyz` deve dar `ready:true`.
2. **Envs OAuth no serviço WEB** (você já configurou — confira os NOMES):
   - Google: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`.
   - Notion: `NOTION_OAUTH_CLIENT_ID`, `NOTION_OAUTH_CLIENT_SECRET`, `NOTION_OAUTH_REDIRECT_URI`.
   - Internas: `BACKEND_INTERNAL_API_KEY` (ou `ADMIN_API_KEY`) no WEB, e `ENCRYPTION_KEY` estável no backend.
3. **Redirect URIs cadastradas EXATAMENTE** nos apps (Google Cloud + Notion):
   - `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host/api/connectors/google-drive/callback`
   - `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host/api/connectors/notion/callback`
   *(Se sua redirect URI cadastrada for diferente, ajuste o env `*_REDIRECT_URI` para a MESMA string cadastrada no provedor.)*
4. **Deploy** web + backend.

## 🧪 Teste
1. Dashboard → Conectores → Catálogo → **Google Drive → Conectar** → autoriza no Google → volta "Conectado ✓".
2. Notion → Conectar → autoriza workspace/páginas → volta "Conectado ✓".
3. Em Minhas conexões aparece a conexão **Conectado**, com menu ⋯ (Testar/Desconectar/Arquivar).
4. Cancelar no provedor → volta sem criar conexão (aviso "cancelada").

## Limitações reais (honesto) — próxima frente
- O **Core LER/buscar arquivos do Drive/páginas do Notion** (usar o token) é a **frente 3 (Document Evidence)**: anexar a tool de leitura ao Core via Registry usando o token salvo. Esta frente entrega a **conexão** (token no Vault + status connected); o **uso** vem em seguida, junto com a leitura de PDF de apólice (que resolve o caso do seu print).
- **Refresh automático de token** (Google) e **revogação no provedor** ao desconectar: estrutura pronta (refresh_token salvo); o refresh on-demand entra na frente 3 quando o Core consumir.
- Escrita/edição em Drive/Notion: só depois (ação sensível, com aprovação).

## Verificação
py_compile OK; tsc=0; build verde. Reusa Vault/tenant_connections/encryption; nenhuma estrutura paralela.
