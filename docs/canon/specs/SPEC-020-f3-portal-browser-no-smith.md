# SPEC-020 — F3: Portais (browser) DENTRO do Smith — robusto e persistente

**Autor**: Fable · 2026-07-05 · **Status**: pronta para chat novo (janela dedicada, contexto limpo)
**Prioridade do founder**: portal de VIDROS/LANTERNAS primeiro; depois portais de seguradoras.
Caso de ouro: **Auxiliar de Cobrança** (entrar nos portais, achar boletos atrasados, enviar no
WhatsApp do cliente + relatório) — é o produto mais valioso da lista do founder.

## Veredito sobre o que existe (avaliado por Fable)
- Portal Lab (Admin → Portal Lab) + páginas "Portal Browser — Registry & Contas": é
  SCAFFOLDING DE HOMOLOGAÇÃO (43P1) — tudo mock/dry-run, catálogo de 189 portais, contas com
  CredentialRef/SessionRef opacos, canary com Browserbase GATED. NÃO executa nada real.
  Estrutura de DADOS aproveitável (catálogo, contas, refs); fluxo de EXECUÇÃO inexistente.
- Browserbase: caro para o volume alvo (~240 acessos/mês por corretora). DECISÃO: motor
  próprio **Playwright em worker dedicado** (container novo no EasyPanel), Browserbase
  opcional atrás de flag para casos difíceis. Custo ~fixo (1 container) vs por-sessão.
- Founder AUTORIZOU refazer o que for gambiarra. Não construir sobre o fluxo mock.

## Arquitetura alvo (cérebro único — regra inviolável)
1. **portal-worker** (novo serviço EasyPanel, mesmo repo `backend/portal_worker/`):
   FastAPI fino + Playwright (chromium headless) + fila via tabela `portal_jobs`
   (id, company_id, portal_key, journey, params jsonb, status queued/running/needs_human/
   done/failed, evidence jsonb, screenshots paths, created/finished). Polling na tabela
   (30s) — sem Redis novo. Sessões persistidas: storage_state cifrado por conta de portal
   (tabela `portal_sessions`: company_id, portal_key, account_label, storage_state_encrypted,
   verified_at, health). Chave de cifra: env `PORTAL_VAULT_KEY` (Fernet).
2. **Journeys = código versionado por portal** (`backend/portal_worker/journeys/<owner>/<journey>.py`),
   contrato: `run(page, params, evidence) -> JourneyResult{status, captured, screenshots}`.
   Primeiras: `vidros_lanternas.login_check` e `vidros_lanternas.abrir_pedido` (founder informa
   qual portal de vidros: abraseuatendimento.com.br — confirmar com ele), depois
   `allianz.boletos_atrasados`.
3. **HITL obrigatório** (CAPTCHA/2FA/login novo): job vira `needs_human`; dashboard mostra
   card "Portal precisa de você" com passo a passo; humano faz login numa janela VNC?
   NÃO no v1 — v1: humano insere credencial na UI (vault) e worker loga com user/senha;
   CAPTCHA → job falha com screenshot + instrução (fase 2: relay).
4. **Tool do Smith** `portal_action` (roles core/auxiliary; attendance NÃO no v1):
   enfileira job e (rotina) aguarda com timeout; capability `tenant.portal.execute`
   (seed nova). Rotina de Cobrança usa essa tool.
5. **Gates**: `PORTAL_REAL_ENABLED` default OFF (como INSURER_DISPATCH_LIVE); kill switch
   existente do Portal Lab é respeitado. Nunca ação de escrita sem approval por conta
   (tabela já tem conceito de approval no Lab — reaproveitar coluna/semântica).

## Fases
- **P1**: worker + tabela jobs + journey login_check do portal de vidros + UI mínima
  (Personalização → Conectores → card Portal) + credencial no vault (cifrada, nunca em log).
- **P2**: sessão persistida (storage_state) + `boletos_atrasados` (Allianz) + evidências
  (screenshot em bucket privado `portal-evidence`).
- **P3**: tool `portal_action` no graph + capability + rotina de Cobrança na galeria
  (SPEC-019 C) ligando tudo: portal → boletos → WhatsApp do cliente → relatório ao corretor.
- **P4**: aposentar páginas mock do Portal Lab (manter catálogo/contas como dados), Admin
  ganha visão de jobs/health por corretora.

## Regras duras
- Credenciais de portal: NUNCA em código/log/LLM. Worker recebe id da conta, lê do vault.
- LGPD: evidence/screenshots só em bucket privado; retenção 30 dias.
- TDD: journeys testadas com páginas HTML fixture locais (playwright contra file://).
- Migrations expand-only. Nada de segundo cérebro: decisões de negócio ficam no Smith
  (a rotina decide; o worker só executa journey determinística).

## Founder precisa
1. Confirmar portal de vidros exato + criar credencial de teste da corretora.
2. Criar serviço `portal-worker` no EasyPanel (mesmo repo, Dockerfile
   `backend/portal_worker/Dockerfile` que a fase P1 entrega) + envs (PORTAL_VAULT_KEY,
   SUPABASE_*). O chat da SPEC gera instruções exatas de deploy.
