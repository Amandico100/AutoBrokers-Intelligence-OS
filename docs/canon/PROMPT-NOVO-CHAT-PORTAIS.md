# PROMPT — Novo chat de PORTAIS (SPEC-024 vidros ponta-a-ponta → depois SPEC-023 autenticados/cobrança)

> Cole isto no chat novo (Opus 4.8). Auto-contido. Este chat faz DUAS specs de portais, nesta ordem:
> **1º SPEC-024** (consertar o acionamento de vidros ponta a ponta no WhatsApp — a ponte está quebrada),
> **2º SPEC-023** (portais com login/CAPTCHA/2FA + Auxiliar de Cobrança).

---

Você é o Opus 4.8 executando SPECs do **AutoBrokers Intelligence OS** (OS multi-tenant de IA para
corretoras). O Fable audita depois. Qualidade de produção, sem gambiarra, honesto. Reporte seu
entendimento e um plano ANTES de mexer em código.

## Leia primeiro (nesta ordem)
1. Sua memória: `C:\Users\amand\.claude\projects\c--Users-...-SPEC016\memory\MEMORY.md` + linkados
   (em especial `exec-progress-2026-07-06.md` — tem TODO o aprendizado do motor de portais).
2. `docs/canon/EXECUTION-GUIDE-OPUS.md` (deploy, TDD house-style, cérebro único).
3. `docs/canon/specs/SPEC-020-f3-portal-browser-no-smith.md` (o motor).
4. **`docs/canon/specs/SPEC-024-acionamento-vidros-ponta-a-ponta-whatsapp.md`** ← comece por ela.
5. `docs/canon/specs/SPEC-023-portais-autenticados-hitl-cobranca.md` (2ª parte).
6. Código: `backend/portal_worker/adaptive.py` (Camada 2), `journeys/vidros_lanternas.py`,
   `backend/app/agents/tools/portal_tool.py` + `portal_params.py`, `backend/app/core/prompts.py`.

## Estado atual — leia com atenção (é o que evita repetir os erros)
**O MOTOR do portal FUNCIONA e é estável.** Com dados REAIS, o worker navega o formulário inteiro do portal
de vidros e para nos 80% ("Confirme a peça danificada") — 3/3 runs, 18 passos. Toda a mecânica AngularJS já
foi resolvida (NÃO reescreva): md-select via JS-click, md-autocomplete (estado = sigla UF), `_find_input`
por id **e** label, fill com input/change/blur, retry-open, parada por não-progresso, freio dos 80%
(`confirm=False` nunca finaliza), e **instrumentação `evidence.debug_dom`** (raio-X da tela).

**O QUE ESTÁ QUEBRADO (SPEC-024): a PONTE atendente→portal manda dados INVENTADOS.** No teste real do
WhatsApp, a `portal_action` montou o job com `insurer:"Liberty"` (portal usa "Yelum"), `placa:"ABC1D23"`
(inventada), `local: São Paulo/SP/01000-000` (inventado) e **sem os dados da apólice** (`segurado` vazio) —
enquanto os testes que chegam nos 80% têm placa/apólice/endereço REAIS da InfoCap. Resultado: o cérebro do
portal escolheu a peça errada ("vidro da porta" → "VIDRO PARABRISA"), a causa errada, e travou. A SPEC-024
tem o diagnóstico completo com arquivos e linhas.

## Sua missão
### Parte 1 — SPEC-024 (faça primeiro, é rápido e destrava o teste do founder)
Conserte a ponte (detalhes/arquivos na SPEC-024):
- **C1**: `portal_action`/`build_portal_params` deve preencher `params.segurado` com os dados REAIS da
  InfoCap (placa, apólice, chassi, veículo, cep, endereço, cidade, estado) — **server-side, o LLM NÃO
  fornece placa/local**. O LLM só decide: qual apólice, peça/como/onde (da conversa), data.
- **C2**: normalizar nome de seguradora (Liberty→Yelum) antes de montar o job.
- **C3**: `_apply_mdselect` deve casar item/causa por **similaridade de tokens**, não cair na 1ª opção às
  cegas (foi o que escolheu a peça errada). Se o melhor score for fraco em campo crítico, devolva as opções
  ao cérebro (needs_human) em vez de chutar.
- **C4**: atendente (`prompts.py`) — filtrar apólices AUTO ativas (não listar vencidas), e não entrar em
  loop de "um momento" quando a tool falha.
- **Meta**: teste no WhatsApp → identifica → "tô abrindo" → ~1-2 min → 80% com peça/loja CERTAS.

### Parte 2 — SPEC-023 (depois do vidros ok)
Portais com login/CAPTCHA/2FA (HITL) + Auxiliar de Cobrança. Ver a SPEC-023.

## Disciplina obrigatória (foi o que resolveu o vidros — não repita o ciclo de chute)
- **Instrumente antes de chutar.** Use `evidence.debug_dom` / `adaptive_steps` / `mdselect_overlay` do
  `portal_jobs`. **Compare um job falho com um que chega nos 80% — a diferença nos `params` é o bug.**
- **Não pode o agente.** Se o cérebro decidiu certo e falhou, o bug é do EXECUTOR ou dos DADOS de entrada —
  conserte isso, não adicione regras que deixam o agente burro.
- **TDD house-style** (importlib+stubs, `check()`, ASCII, sem pytest). Frontend: `npx tsc --noEmit`.
- **Deploy**: commit em `feat/spec-017-attendant` → merge `--no-ff` no repo MAIN → push origin main →
  trigger de deploy (API p/ `prompts.py`/tool; worker p/ `adaptive.py`). Gate `PORTAL_REAL_ENABLED` liga o
  founder. Ciclo de build do worker ≈ 4 min.
- **Nada sensível sem aprovação.** `confirm=False` nunca finaliza.

## Infra
Worker no EasyPanel (Dockerfile `backend/portal_worker/Dockerfile`, base Playwright `v1.47.0-jammy` →
pinar `playwright==1.47.0`). Envs: `SUPABASE_*`, `PORTAL_VAULT_KEY`, `OPENAI_API_KEY`, `PORTAL_REAL_ENABLED`.
Tabelas: `portal_jobs` (params/status/evidence/error), `portal_accounts`, `portal_sessions`, `portals`.
Para testar sem InfoCap real, enfileire um `portal_job` direto (ver `scratchpad` do chat anterior:
`test1_worker.py`, `diag_dom.py`, `stability.py` — replique-os).

**Comece reportando seu entendimento da SPEC-024 + o plano dos 4 fixes, e só então execute.**
