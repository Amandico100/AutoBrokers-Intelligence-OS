# SPEC-023 — Portais Autenticados (login/CAPTCHA/2FA com HITL) + Auxiliar de Cobrança

> Constrói SOBRE a SPEC-020 (motor `portal_worker` + Camada 2 `adaptive.py` + vault + `portal_jobs`).
> NÃO reescreve o motor. Adiciona: **login autenticado por seguradora**, **CAPTCHA/2FA com humano no
> loop**, **mapeamento de portal por prints do founder**, e a primeira tarefa de negócio de alto valor:
> **Auxiliar de Cobrança** (entra no portal → acha parcela atrasada → baixa boleto → envia no WhatsApp
> do cliente com mensagem pronta → relatório ao corretor).

## 1. Objetivo

Hoje o motor já dirige portal **público** (vidros — acionamento vidros funcionando e estável, para nos
80% sem enviar). Falta habilitar os portais **com login**, que é o que destrava os auxiliares de verdade
(cobrança, 2ª via, endosso, sinistro). O portal autenticado tem 3 obstáculos que o público não tem:
**login (usuário/senha), CAPTCHA e 2FA**. A LLM precisa entrar nesses portais — com a ajuda do humano
quando o portal exigir — e executar a tarefa **sem errar e sem travar**.

## 2. O que JÁ existe (reusar, não reinventar)

- **Motor** `backend/portal_worker/` (FastAPI + Playwright + poll de `portal_jobs`) — deployado no EasyPanel.
- **Camada 2** (`adaptive.py`): cérebro LLM-visão que dirige telas desconhecidas (capture_state → decide →
  apply → loop). Já robusto para AngularJS Material (md-select via JS-click, md-autocomplete, `_find_input`
  por label, retry-open, parada por não-progresso, instrumentação `debug_dom`). **Reusar como está.**
- **Vault Fernet** (`PORTAL_VAULT_KEY`): credenciais de portal por corretora, cifradas. UI em
  Personalização → Conectores → Portais (multi-tenant: mesmo endereço, login/senha por corretora).
- **`interpret_login`** (`journeys/vidros_lanternas.py`): já classifica login OK / FALHA / **HITL
  (CAPTCHA/2FA/código → `needs_human`)**. É o ponto de partida do login autenticado.
- **Tabelas**: `portal_jobs`, `portal_accounts`, `portal_sessions` (storage_state), `portals` (registro).
- **`portal_action`** (tool no graph, capability `tenant.portal.execute`).

## 3. O que esta SPEC adiciona

### P1 — Login autenticado + sessão persistida
- `journey <insurer>.login`: abre o portal, preenche usuário/senha do **vault** (nunca do LLM), submete.
  Usa `interpret_login` + Camada 2 para telas novas.
- **Sessão persistida** (`portal_sessions.storage_state`): depois do 1º login bem-sucedido, reusa cookies
  para não relogar (nem re-CAPTCHA) toda vez. Expira → relogar.

### P2 — HITL de CAPTCHA/2FA (humano no loop, sem gambiarra)
- Quando o portal pede CAPTCHA/2FA/código: job vira `needs_human` **com screenshot + instrução clara**.
- **Dashboard**: card "🔐 Portal precisa de você" mostrando o print + o campo pra você digitar o código /
  resolver o CAPTCHA. O worker **pausa** a sessão (mantém o browser vivo N minutos) e **retoma** com o que
  você mandou. v1 = pausa/retomada por código; **fase 2** = relay ao vivo (stream da tela).
- Nunca burla CAPTCHA. O humano resolve; a LLM faz todo o resto.

### P3 — Mapeamento de portal por prints
- Você traz **prints do portal** (o passo a passo real). Vira **knowledge do portal** (seletores +
  sequência), guardada por seguradora. A journey determinística usa o que for estável; a Camada 2 cobre o
  resto. Cada decisão nova vira caminho rápido (integra com **SPEC-021 Camada 3 / learning_notes**).

### P4 — Auxiliar de Cobrança (o caso de ouro)
Rotina na galeria (SPEC-019): **login → listar clientes/apólices com parcela ATRASADA → baixar o boleto
(PDF) → enviar no WhatsApp do cliente com mensagem pronta → relatório ao corretor.** Reusa `portal_action`
+ o motor + o envio WhatsApp (mesmo seam do atendente). Confirmação humana antes de enviar em massa.

## 4. Regras de ouro (herdadas do debug do vidros)
1. **Nunca chutar**: instrumentar o DOM real (`debug_dom`) antes de qualquer fix.
2. **Não podar o agente**: o cérebro decide; o executor tem que HONRAR a decisão (achar campo por id **e**
   label, clicar widget do jeito certo). Bug quase sempre é do executor, não da inteligência.
3. **Nada sensível sem aprovação**: enviar boleto ao cliente / finalizar no portal = passo de aprovação.
4. **Multi-tenant**: credenciais por corretora, no vault. Endereço do portal é global.

## 5. Infra / envs (já provisionado no worker)
`SUPABASE_*`, `PORTAL_VAULT_KEY`, `OPENAI_API_KEY` (Camada 2), `PORTAL_REAL_ENABLED` (gate).
Dockerfile: `backend/portal_worker/Dockerfile`. Base Playwright `v1.47.0-jammy` (pinar `playwright==1.47.0`).

## 6. Fases
- **P1** login + sessão persistida (1 seguradora piloto que o founder escolher).
- **P2** HITL CAPTCHA/2FA (card no dashboard + pausa/retomada).
- **P3** mapeamento por prints → knowledge de portal.
- **P4** Auxiliar de Cobrança ponta a ponta (portal → boleto → WhatsApp → relatório).

## 7. Fora de escopo (v1)
Relay VNC ao vivo (fase 2), resolução automática de CAPTCHA (nunca — sempre humano), portais que proíbem
automação por ToS (checar caso a caso com o founder).
