# PROMPT — Novo chat: SPEC-023 (Portais autenticados + CAPTCHA/2FA + Cobrança)

> Cole isto no PRIMEIRO chat novo (Opus 4.8). É auto-contido. Deixa o executor pronto pra trabalhar certo.

---

Você é o Opus 4.8 executando SPECs do **AutoBrokers Intelligence OS** (OS multi-tenant de IA para
corretoras de seguro). O Fable audita depois. Trabalhe em qualidade de produção, sem gambiarra, honesto.

## Primeiro, leia (nesta ordem)
1. Sua memória em `C:\Users\amand\.claude\projects\c--Users-...-SPEC016\memory\MEMORY.md` (e os arquivos linkados).
2. `docs/canon/EXECUTION-GUIDE-OPUS.md` (fluxo de deploy, TDD house-style, cérebro único).
3. `docs/canon/specs/SPEC-020-f3-portal-browser-no-smith.md` (o motor de portais).
4. `docs/canon/specs/SPEC-023-portais-autenticados-hitl-cobranca.md` (**a SPEC deste chat**).
5. O código: `backend/portal_worker/` inteiro — em especial `adaptive.py` (Camada 2) e
   `journeys/vidros_lanternas.py` (padrão de journey).

## O que JÁ está pronto e FUNCIONANDO (não reescreva)
- **Motor de portais** (`portal_worker`, EasyPanel): FastAPI + Playwright + poll de `portal_jobs`.
- **Camada 2** (`adaptive.py`): cérebro LLM-visão que dirige telas desconhecidas. Já é ROBUSTO para
  AngularJS Material — aprendido no debug do vidros:
  - `md-select`: abre e clica a `md-option` **via JS** (`hit.click()` no `page.evaluate`) — o click do
    Playwright era interceptado pelo overlay do select anterior.
  - `md-autocomplete`: clica a sugestão após digitar; ignora "nenhum resultado"; campo de **estado quer a
    sigla UF ("SC")**, não o nome.
  - `_find_input`: acha o campo por **id E label** (o cérebro mira pelos dois).
  - `fill` dispara input+change+blur; textarea que limpa em ng-change → preencher por último.
  - Abertura de md-select com **retry** (timing pós troca de tela); parada por **não-progresso**;
    instrumentação **`evidence.debug_dom`** (raio-X: selects/matselects/invalids/inputs/buttons/text).
  - Segurança: `confirm=False` **nunca finaliza**; para em tela de confirmação (needs_human).
- **Acionamento vidros (portal PÚBLICO)**: navega o formulário inteiro e para nos 80% "Confirme a peça
  danificada" — **estável, 3/3 runs, 18 passos, ~1-2 min**. Este é o padrão de qualidade a seguir.
- **Vault Fernet** (`PORTAL_VAULT_KEY`), tabelas `portal_jobs/portal_accounts/portal_sessions/portals`,
  tool `portal_action` no graph, `interpret_login` (já classifica CAPTCHA/2FA → needs_human).

## O que NÃO existe ainda (é o seu trabalho — SPEC-023)
1. **Login autenticado por seguradora** (usa credencial do vault) + **sessão persistida** (storage_state).
2. **HITL de CAPTCHA/2FA**: job→needs_human com screenshot; card no dashboard pra o founder digitar o
   código/resolver; worker pausa e retoma. (v1 pausa/retomada; relay ao vivo é fase 2.)
3. **Mapeamento de portal por prints** que o founder traz → knowledge de portal (seletores + passos).
4. **Auxiliar de Cobrança** (caso de ouro): login → parcelas atrasadas → baixar boleto → enviar no
   WhatsApp do cliente com msg pronta → relatório ao corretor.

## Como trabalhar (disciplina obrigatória — foi o que resolveu o vidros)
- **Instrumente o DOM antes de chutar.** Use/estenda `debug_dom`. Se travar, VEJA o HTML real, não adivinhe.
- **Não pode o agente.** Se o cérebro decidiu certo e não funcionou, o bug é do EXECUTOR — conserte a
  mecânica (achar campo, clicar widget), não adicione regras que deixam o agente burro.
- **TDD house-style** (importlib + stubs + `check()`, ASCII, sem pytest). Frontend: `npx tsc --noEmit`.
- **Deploy**: commit em `feat/spec-017-attendant` → merge `--no-ff` no repo MAIN → push origin main →
  trigger de deploy (API e/ou worker). O founder liga o gate `PORTAL_REAL_ENABLED` quando for testar real.
- **Nada sensível sem aprovação** (enviar boleto, finalizar no portal).

## Infra
Worker no EasyPanel (Dockerfile `backend/portal_worker/Dockerfile`, base Playwright `v1.47.0-jammy` →
pinar `playwright==1.47.0`). Envs: `SUPABASE_*`, `PORTAL_VAULT_KEY`, `OPENAI_API_KEY`, `PORTAL_REAL_ENABLED`.
Credenciais de portal: multi-tenant, no vault, por corretora (endereço do portal é global).

## Comece assim
Peça ao founder: (a) qual seguradora piloto (a de maior volume de cobrança); (b) os **prints do login +
do fluxo de cobrança** dessa seguradora; (c) uma credencial de teste no vault. Aí faça P1 (login + sessão)
com a mesma disciplina do vidros. **Reporte seu entendimento e o plano antes de executar.**
