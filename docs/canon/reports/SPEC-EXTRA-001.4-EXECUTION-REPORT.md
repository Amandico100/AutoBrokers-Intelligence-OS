---
> **Status:** relatório de execução sob o **PROTOCOLO AAA v12 · AAA FAST** · EXTRA-001.4 · experimento B do A/B (D-PROTO-02)
> **Teto:** 15 KB (CRÍTICO); 25 KB quando o excesso for medição (D-PROTO-07)
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `f7b23d7`

```
OUTCOME ..............  menu numerado recebe NÚMERO lendo a tela real; "opção inválida" é reparada pelo motor
                        antes do Sentinela, uma vez por tela; humano da corretora na URA pausa o robô 60 s;
                        humano da seguradora é atendido mesmo com a sessão em needs_human; encerramento reconhecido
RISCO ................  8   alcance SEGURADO 3 + "saiu do prédio" 3 (mensagem à URA) + TODO atendimento 2
SUPERFÍCIE ...........  2   vários comportamentos, lugares listados (proposta §3.2) e reconferidos por grep
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" — a resposta à URA sai do prédio
NÍVEL ................  CRÍTICO · executor Opus 5 max (experimento B) · juiz Fable 5.1
UNIDADES .............  6 — fatia 1: 0-bis (acervo e linha de base) · A (regra B, tecla) · B (regra A, reparo)
                        fatia 2 (sessão nova): C (humano da corretora) · D (humano da seguradora) · E (adjacentes)
COESÃO ...............  A+B: o hub `insurer_dispatch_service.py` — `resolver_tecla` grava o `menu_pendente` que o
                        reparo lê; e o contador do Sentinela. C+D+E: `dispatch_router.py` + `dispatch_watchdog.py`.
                        0-bis ANTES do código: a linha de base tem de ser medida sobre o motor SEM a mudança
PARALELISMO REAL .....  nenhum — escrita de um só; investigador read-only: não
TIME .................  executor · juiz Fable (fim da fatia 2) · lente do dado SIM (a régua é NÚMERO) ·
                        confirmação SIM se o juiz achar blocker em envio · red team NÃO
REFERÊNCIA ...........  interna `backend/scripts/medir_rota.py --com-espelho` · `backend/tests/corpus/telas_reais/` ·
                        externa https://www.w3.org/TR/voicexml20/ (contagem por prompt, reset na reentrada) ·
                        https://www.erlang.org/doc/apps/stdlib/gen_statem.html · https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
GATES ................  G0 · G0-bis · GA · GB · GR (régua sem regressão) · [fatia 2] GC · GD · GE · GT
O ELO ................  "respondeu 'residência' PORQUE o slot nunca virou tecla": medi A (10/09 14:12:48 menu →
                        14:13:07 "Opção inválida.") · medi B (`qual_seguro_opcao` ∉ 23 derivados, AST) · medi que B
                        CHEGA em A (`render_reply` interpola cru → `_emit`, insurer_dispatch_service.py:2813) — e o
                        guarda GA-2 reproduz pelo motor sobre a tela do acervo
FAIXA DE RELÓGIO .....  declarada fatia 1 ≤ 1h15 · fatia 2 ≤ 1h15 · juiz+conserto+entrega ≤ 45 min ·
                        tetos: 250 turnos e 300 k por fatia · real: ver §10
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** `docs/canon/specs-propostas/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md`
(executada como está, D-PROTO-05) · **Branch:** `feat/spec-extra-001-4-corredor-nao-trava` · **Preflight** 📊 17/09 00:05 UTC:
`HEAD..origin/main` = 0 · `origin/main..HEAD` = 0 · HEAD = `f7b23d7` · árvore com 3 renomes de prompt do Founder (não tocados) ·
**Executor:** Opus 5 max (sessão nova) · **Juiz:** Fable 5.1

## 1. BLOCO 0 — as premissas que mudariam o desenho (📊 17/09, de dentro de `backend/`, utf-8)

| # | a proposta afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | `parse_options` no menu real: cru → 0 · normalizado → 3 | **cru 3 · `_norm` 3 · `_NUMERADA` sozinho 0** — `parse_options` já chama `_sem_negrito` (cartographer.py:196, :376) | `C.parse_options(t)` · `C._NUMERADA.finditer(t)` sobre as 15 telas "3 - Empresarial" do corpus | a camada 1 chama `parse_options`, NUNCA a regex; GA-3 afirma `_NUMERADA`=0 × `parse_options`=3 |
| 2 | 52 usados · 23 derivados · 29 órfãos | **52 · 23 · 29** (805 passos, 14 corredores); derivado sem dono: 0 | AST do RESEARCH-PACK §4 ① | a camada 1 é o conserto dos 29 |
| 3 | `o_grupo_pode_saber` existe? | **existe** — `o_grupo_so_o_que_importa.py:247` | `grep -rn "def o_grupo_pode_saber" backend/app/` | fatia 2 CHAMA e acrescenta a causa `pausa_humana` |
| 4 | slot `*_opcao` vazio "fica CALADO" hoje | **falso desde 19/08**: tela reversível → o Cérebro assume (`insurer_dispatch_service.py:2775-2793`) | leitura de `handle_insurer_message` da linha 1 (2439-2936) | **D-E0014-01**: vazio NÃO vira `needs_human` geral |
| 5 | a recusa repete o menu | **não repete**: "Opção inválida." + "Vamos tentar novamente." em 2 bolhas (sessão `432614de`, 14:13:07/08 e 14:18:09/10 BRT) | `observed_events` por `session_id`, texto mascarado | o reparo lê o `menu_pendente`, não a tela atual |
| 6 | frases de recusa de menu | allianz "Opção inválida." **26 ev/14 sess** · porto 6 redações (**15 ev**) · mapfre 3 (**7**) · azul 2 · bradesco 3 · hdi 2 · tokio 1 | `observed_events`, `direction='in'`, regex de recusa, `group by` | `RECUSA_DE_MENU` nasce desta tabela |
| 7 | `sentinela_attempts` por sessão, nunca zerado | **confirmado**; as linhas mudaram: leitura :387/:391, incrementos :430 :439 :444 :474 | `grep -rn sentinela_attempts backend/app/` | GB-2 |
| 8 | `agente.*` = 0; CHECK em `event_type`? | **0 de 48.972**; CHECK só em `actor_type` e `severity` | `pg_constraint` de `work_events` | **sem migration** nesta SPEC |
| 9 | "falta de contato" 10 ev, 0 casam | **10 · 0** (Postgres `~*`); o controle em Python roda no corpus regenerado | consulta da proposta §8.5 | fatia 2 (D5) |
| 10 | "Isso pode levar alguns instantes" não existe | **existe no banco** (10/09, 3×) — a proposta mediu só o corpus de agosto | linha do tempo `432614de` | fatia 2: é fila (`AVISO_DE_ESPERA`), não transferência |
| 11 | — (achado novo) | "Ainda não consegui entender e **vou precisar encerrar a conversa**" — porto 6 ev/4 sess, azul 1 — **não casa** `insurer_closed` | mesma consulta do item 6 | fatia 2 (D5): segunda frase de encerramento |
| 12 | banco | `observed_events` **32.817** · máx 2026-09-16 18:00 · **1.048** em setembro | `count(*)`, `max(wa_timestamp)` | o 0-bis traz setembro |

**Triagem nominal (item 9 da proposta)** — `python tests/<arquivo>.py`, na head `f7b23d7` e num worktree de 07/09 (`cffaa0e`, antes das 5 entregas sem SPEC). 📊 **Os 4 já eram vermelhos em 07/09 — nenhum é regressão de 08–10/09:**

| teste | head | 07/09 | veredito |
|---|---|---|---|
| `test_spec017_dispatch.py` | exit 1 — `sessão pronta: ['qual_seguro_opcao']` → `preparing` → IndexError :158 | exit 1 (mesmo `IndexError`) | `qual_seguro_opcao` entrou em `required_slots` em 21–22/08 (`e2dfd5c`, `4dc6ab0`) sem derivação: **defeito desta SPEC (A)** |
| `test_spec031_auto_dispatch.py` | exit 1 — `missing_slots: ['local_seguro']` | exit 1 (mesmo `local_seguro`) | `local_seguro` obrigatório desde 21–23/08 (`1132f6e`…`4430647`): fixture vencida, fora do escopo |
| `test_o_corredor_conhece_a_tela_que_esta_na_frente.py` | exit 1 — 2 falhas | exit 1 | vermelho antes de 08/09: **não é regressão das entregas sem SPEC**; fatia 2 (E) diz se é desta SPEC |
| `test_spec034_onda1.py` | exit 1 — `ModuleNotFoundError` | exit 1 (mesmo erro) | vermelho antes de 08/09: import quebrado no próprio teste; fatia 2 (E) |
| `test_spec038_sentinela.py` · `test_a_tecla_tem_a_forma_da_seguradora.py` | exit 0 · exit 0 (`12 assercoes verdes`, com o defeito vivo) | — | o retrato do problema |

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|---|
| 1a | BLOCO 0 | este relatório | §1 | 12 premissas remedidas; 1 decisão (D-E0014-01) | este commit |

🔴 **A fatia 1 fechou no BLOCO 0, pelo teto de contexto** (§10 · D-PROTO-07): 📊 o hook `teto-de-contexto.py` mediu
**300 k antes da primeira linha de produto**. Leitura integral pedida pelo Founder (proposta 112 KB ≈ 51 k tokens + research
pack + protocolo) somada ao raciocínio em effort `max`. Nenhum código de produto foi escrito. A fatia 1b (0-bis + A + B)
abre em sessão nova, com o handoff do §12.

⚠️ **O comando do 0-bis na proposta §4.1 não regenera:** 📊 `gerar_corpus_de_telas.py --todas --auditar-pii` levou 2,8 s
e só auditou (`auditoria de PII: 4279 linhas, 0 sujas`), porque `--auditar-pii` retorna antes de gerar
(`gerar_corpus_de_telas.py:495`). A ordem certa é `--todas` e depois `--auditar-pii`.

## 3. Migrations — nenhuma (BLOCO 0 item 8: `work_events.event_type` não tem CHECK)

## 4. O juiz fresco — roda uma vez, no fim da fatia 2

## 5. O conserto único

## 6. A bateria

## 7. O que ficou fora, e o gatilho que o faz voltar

## 8. 📋 Caixa do Founder

## 9. Pendências e decisões

| ID | decisão | opções e notas |
|---|---|---|
| **D-E0014-01** | slot `*_opcao` VAZIO numa tela reversível continua indo ao Cérebro (desenho de 19/08), agora com as opções numeradas da tela no prompt; `needs_human` só para a tecla que decide o RAMO (`ramo_indeterminado`) e para `sem_chute` | Cérebro + opções **88** · `needs_human/slot_opcao_sem_derivacao` geral, como a proposta §5.2 regra 3 **35** (reintroduz o travamento de 19/08 em 29 slots — o oposto do outcome) · `needs_human` reentrável **40** |

## 10. Telemetria (§11)

## 11. Entrega

## 12. Handoff — fatia 1b (0-bis + A + B), sessão nova, mesmo prompt

```
1  NÃO remeça o §1 (vale até o HEAD mudar). Da proposta leia SÓ §4.1, §5, §6 e as linhas GA/GB do §10. Pack: não.
2  0-bis: `gerar_corpus_de_telas.py --todas` (SEM --auditar-pii) → `--auditar-pii` → `tests/test_o_corpus_nao_vaza_pii.py`
   → `432614de` em allianz-residencial.jsonl + "falta de contato" no corpus → `medir_rota.py --todas --com-espelho
   --salvar-linha-de-base docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json` ANTES de tocar o motor (não roda mutação;
   o `--formato markdown` roda 12 e fica para a fatia 2) → commit do corpus + INDICE + linha de base.
3  A · onde: ramo `rendered ok` (insurer_dispatch_service.py:2805-2813) chama `resolver_tecla` se o reply interpola
   `{*_opcao}`. Opções = `cartographer.parse_options(tela)` filtradas por `numero_da_opcao` (palpite fora). Casamento =
   `atlas.weaver.labels_match` (📊 "residência" casa só "1 - Residencial"). 1 → dígito, origem menu_lido · 2+ →
   needs_human/tecla_ambigua · 0 → ramo do Cérebro (`falta_para_a_ura`, :2775), D-E0014-01 · sem menu → a palavra (porto).
4  A · `qual_seguro_opcao` decide o RAMO: vazio ou sem casamento → needs_human/ramo_indeterminado (§9.5, escrito ao lado).
   Camada 2 no topo de `_derivar_teclas_do_caso` (:394): só se vazio, por fronteira de palavra; casa E condomínio = nada.
5  A · prova de produto: `test_spec017_dispatch.py` (hoje exit 1 por `qual_seguro_opcao`) fica verde pela derivação.
6  B · `menu_pendente` gravado em `_emit` (:4096) a partir da última bolha `in`, e no envio do Sentinela
   (dispatch_watchdog.py:444). Reparo ANTES de `match_ura_step` (:2626). A recusa real NÃO repete o menu (§1 item 5):
   as opções vêm do pendente. `RECUSA_DE_MENU` = tabela do §1 item 6 sobre `_norm`, sem "encerrar a conversa".
7  B · `tentativas_por_tela[hash do _norm]` + `sentinela_attempts` como teto de sessão, nos 4 incrementos
   (:430 :439 :444 :474). `MAX_TENTATIVAS_NA_SESSAO` sai do replay (telas órfãs funcionais distintas por sessão).
   `test_spec034_onda1.py:239` codifica o teto por sessão: muda junto (CLAUDE.md §9.3).
8  B · `build_human_phase_messages` (bloco `ajuda_do_passo`, ~:3218) ganha `ultima_resposta_recusada` e
   `tela_com_menu_pendente`. O roteador chama o motor POR BOLHA (dispatch_router.py:2908): teste com as DUAS bolhas.
9  Fatia 2 herda os itens 3, 9, 10 e 11 do §1. Guardas novos: `ls backend/tests/test_*.py | wc -l` = 📊 376 antes.
10 Triagem de 07/09 FEITA (§1): os 4 vermelhos são anteriores a 08/09. 017 é desta SPEC (A); 031, 034 e "conhece a tela" → fatia 2 (E).
```
