# RELATÓRIO — SPEC-129-A · A espera durável

**04/10/2026** · branch `spec/129-A-a-espera-duravel` · commit inicial `89e1a00` (= `origin/main`, 📊 `git rev-list --count HEAD..origin/main` → 0) ·
gerente Opus 5.5 · rito CRÍTICO (a ponte das rotinas — cobrança, que ENVIA — está ligada em produção) · SPEC: [`specs/SPEC-129-A-a-espera-duravel.md`](../specs/SPEC-129-A-a-espera-duravel.md)

## EXECUTION CARD

```text
OUTCOME .............. um trabalho do Work OS espera minutos (o cálculo do Agger leva 📊 413–420 s) sem perder nada: dorme, acorda
                       sozinho, sobrevive a reinício, nunca roda duas vezes; os presos velhos expiram sem rodar; cancelar cancela;
                       Reprocessar funciona; o CPF sai do rastro
RISCO ................ 7 — alcance segurado 3 · reversibilidade 3 (cobrança enviada) · frequência 1
SUPERFÍCIE ........... 3 — runs.py, smith_worker.py, workflows.py, gateway.py, api/work_runs.py, approvals.py + 3 migrations
PISO APLICADO ........ CRÍTICO (§3.2: o caminho ENVIA cobrança; migration que altera dado e estrutura)
NÍVEL ................ CRÍTICO · redator + revisor cego · builders Opus 5.5 por fatia · juiz ‖ red team · conserto único · confirmação
O FIO ................ portal.operation :criar → gateway (ENFILEIRAR, to_thread) → portal_jobs → :aguardar → runs.dormir (waiting_input
                       + wake_at/wait_for) → laço de órfãos: despertar_vencidos / redespachar_parados → outbox → fila → worker →
                       executar_passo (CAS, efeito, guardar) → concluir com o token do lease
PARALELISMO REAL ..... F1 (runs, worker) ‖ F4 (migrations) · F2 (workflows, gateway) ‖ F3 (api/work_runs, approvals) · F0 antes · F5 depois
UNIDADES ............. F0 teste do fio · F1 núcleo · F2 passos e portal · F3 as portas · F4 migrations · F5 costura
COESÃO ............... o contrato (Esperando, EfeitoIncerto, dormir, despertar_*) mora em runs.py e foi entregue pela F1 antes da F2
TIME ................. 6 builders · juiz ‖ red team · conserto único · confirmação. Escalação: nenhuma
REFERÊNCIA ........... interna: CLAUDE.md §9.3/§9.4; externa (SPEC §10): Temporal durable timers, AWS Step Functions callback,
                       transactional outbox, Postgres SKIP LOCKED, Redis Streams XAUTOCLAIM
GATES ................ fio 7/7 · guardas novos com controle e mutação · migrations VERIFY · bateria triada · confirmação
O ELO ................ "não roda duas vezes" = CAS no lease E passo externo sem prova não roda E retomada de running vira EfeitoIncerto
                       — medido nos três (ataques do juiz e do red team re-rodados: 1 envio)
FAIXA DE RELÓGIO ..... 💭 4–6 h · real ver telemetria
```

## 1. O que mudou

- **A espera durável existe.** Um trabalho que espera o portal (e, na 129-B, o Agger) dorme em `waiting_input` com `wake_at`; o laço de
  órfãos que já existia o acorda; nada de `time.sleep` no loop; o "pedido já existe" devolve o job sem esperar.
- **Nunca duas vezes.** Toda mudança de estado é condicional (CAS com o token do lease) e filtra `runtime_kind='smith'` + `company_id`
  da própria linha. Passo com efeito externo (a cobrança) interrompido vira `efeito_incerto` e não repete; sem prova de estado, nem roda.
- **A fila que perdia mensagem se cura:** 📊 21 trabalhos estavam parados desde 28/07 com o outbox publicado e nenhum lease; o re-despacho
  os devolve, e os velhos (> 2 h) expiram sem rodar com evento legível.
- **Cancelar cancela; Reprocessar funciona;** aprovação já decidida não se troca; cobrança que expira deixa aviso visível e destrava o
  `routine_runs`.
- **O CPF sai do rastro** (migration `_03`, a aplicar — §4).

## 2. Julgamento

| peça | veredito | o que achou |
|---|---|---|
| revisor cego da SPEC | 76 → 8 consertos aplicados antes do build | sombras sem lease pegas pelo despertador; relógios indefinidos; brecha no gatilho; 3 linhas vivas sem justificativa |
| juiz | REPROVADO · **78** | B1 passo externo roda sem prova (cobrança 2×); B2 cancelar vira laço |
| red team | QUEBREI · **62** | Q1/Q2 cobrança 2× (INSERT ou releitura falhando); Q3 cancelar em laço |
| conserto único | 6 commits | `EtapaNaoVerificada`, `running` regravado antes de `fn()`, `CancelamentoPedido`, cerca em `_fechar_sem_fila`, `or_` provados no PostgREST real (📊 21 = 21, 0 = 0) |
| confirmação (§6.1) | **CONFIRMA · 89** | 0 blocker novo; ataques re-rodados: 1 envio, `cancelled` |

## 3. Testes (saída real)

- `pytest tests/test_spec129a_*.py tests/test_o_run_sem_fila.py` → **102 passed** (o fio C1–C7 dá 7/7; nasceu 6 falhas + 1 controle)
- `test_spec055_work_os` todas as garantias · `test_spec020_worker_hardening` 15/0 · `test_spec075` 151/0 · `test_f2_routines` 17/0 · `test_spec078` 39/0
- mutações: F1 4 · F2 7 · F3 8 · F4 3 · costura 2 · conserto 8 — todas vermelhas, restauradas por cópia
- bateria: §5

## 4. Migrations

| migration | estado | VERIFY |
|---|---|---|
| `20261004_01_spec129a_presos_expiram` | ✅ APLICADA 04/10 | 📊 21 · 21 · 6 · 0 (esperado 21·21·6·0) |
| `20261004_02_spec129a_espera_duravel` | ✅ APLICADA 04/10 | 📊 2 · 1 · 2 (esperado 2·1·2) |
| `20261004_03_spec129a_retrato_mascarado` | 🧑 **NÃO APLICADA** — a ferramenta recusou (dado irreversível pede confirmação humana) | antes: 📊 17 · 0 · 0 · 0 (esperado depois 0·17·2·1) |

ROLLBACK de cada uma escrito no cabeçalho do arquivo e provado em transação desfeita (F4). O código funciona sem a `_03`.

## 5. Bateria

Worktree limpo `C:/wt129`, HEAD `72b8b56`, `pytest tests -q -p no:cacheprovider` → 📊 **50 failed · 5150 passed · 8 skipped · 31 xfailed ·
1 xpassed em 1:22:50**. Triagem nominal contra a base (35): 35 iguais · 0 sumiram · 15 novas → isoladas: **9 da SPEC-125 passam** (📊 9 passed,
carga — as mesmas da rodada do passo 0.5) · **3 `or_` no PostgREST real passam** (carga) · `test_a_arvore_ficou_limpa_no_fim` (carga, já visto
no 0.5) · **2 reais, consertadas** (`3d616fc`, `918dd4f`): o dublê do `test_e001101_c` não tinha `.neq` (a cerca nova do `_fechar_sem_fila`)
→ 54/0; o guarda da `_01` assumia os 21 presos vivos e a `_01` foi aplicada → mede pela diferença, 7 passed. Depois: `test_spec129a_*` +
`test_o_run_sem_fila` → 📊 **103 passed**. **0 regressões.**

## 6. O que ficou fora

P-129A-01…08 em `PENDENCIAS.md`. Decisões D-129A-1…10 em `FOUNDER-DECISIONS.md`.

## 7. Declaração

Nenhum motor paralelo: o despertador e o re-despacho rodam no laço de órfãos que já existia e escrevem no outbox que já existia. Nenhum
segredo em arquivo versionado. Canário: `backend/scripts/canario_espera_duravel.py` (não envia mensagem, não toca portal), roda depois do Implantar.

## 8. Telemetria — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`

```text
129-A: redator 39 min US$ 14.26 · revisor cego 8 min US$ 3.58 · F0 24 min US$ 5.27 · F1 31 min US$ 7.62 · F4 19 min US$ 4.27 ·
  F2 63 min US$ 13.38 · F3 38 min US$ 5.42 · F5 30 min US$ 5.99 · juiz 13 min US$ 5.31 · red team 16 min US$ 8.65 · conserto único e
  confirmação (ver sessão) · conserto da bateria 20 min US$ 2.17 (todos opus-5-5)
sessão inteira (validação do plano + passo 0.5 + 129-A): executor pico 697k · 27 agentes · 1.767 turnos · US$ 231.45 (equivalente de API
  do Claude Code — NÃO é a verba do produto)
verba de API do PRODUTO (US$ 4,00): US$ 0,00 gasto
achados por mecanismo: revisor cego 8 (antes do build) · costura 1 (cas_perdido falso) · juiz 2 blockers · red team 3 blockers (Q1/Q2
  exclusivos sobre o INSERT) · confirmação 0 blocker · bateria 2 (dublê sem .neq; guarda vencido pela migration aplicada)
rodadas da bateria: 1 (+ isolamento das 15 novas)
nota do executor: 90 (critério: os blockers fechados com prova e ataques re-rodados; a _03 ficou para o Founder)
nota do juiz 78 · red team 62 · confirmação 89
⚠️ pico do executor 697k > teto — a sessão carregou três trabalhos; a 128 vai para chat novo (decisão do gerente)
```

## 9. Entrega

```text
$ git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
   89e1a00..6e13bb2  HEAD -> main
$ git rev-list --count origin/main..HEAD
0
```
