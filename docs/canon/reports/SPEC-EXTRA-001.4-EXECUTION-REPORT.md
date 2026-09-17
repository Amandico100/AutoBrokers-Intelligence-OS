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
| 1a | BLOCO 0 | este relatório | §1 | 12 premissas remedidas; 1 decisão (D-E0014-01) | `acb6814` |
| 1b | 0-bis | corpus (12 de 16 arquivos mudaram) · `INDICE.md` · `LINHA-DE-BASE-DE-ROTAS.json` | `gerar_corpus_de_telas.py --todas` · `--auditar-pii` · `test_o_corpus_nao_vaza_pii.py` · `medir_rota.py --salvar-linha-de-base` e `--comparar-com` (controle) | 📊 39 s · **4.470 telas, 0 sujas** · guarda exit 0 · máx `2026-09-14` · controle **exit 0** | ver §11 |
| 1b | A | `insurer_dispatch_service.py` (`resolver_tecla`, `opcoes_numeradas`, derivação do ramo, `origem_das_teclas`) · 2 fixtures vencidas | GA-1 `test_a_tecla_tem_a_forma_da_seguradora.py` · GA-2/3 `test_o_menu_numerado_recebe_numero.py` | **22/0 · 22/0** — na base: 17/**5** · `AttributeError` | ver §11 |
| 1b | B | `insurer_dispatch_service.py` (reparo, `menu_pendente`, prompt) · `dispatch_watchdog.py` (por tela) | GB `test_a_opcao_invalida_e_reparada.py` | **25/0** — na 1ª rodada pegou `RecursionError` no Sentinela (um `replace_all` meu), consertado | ver §11 |
| 1b | GR | — | `medir_rota.py --todas --com-espelho --comparar-com …LINHA-DE-BASE…` | **exit 0**: nenhuma rota perdeu respondidas · nenhum passo sem confirmação | — |

**Gate 0-bis, item a item:** ① a sessão `432614de` ESTÁ no corpus pelo ID (**13 telas**), mas em `allianz-auto.jsonl`:
📊 `padroes_de_ramo.classificar_ramo` → `auto | nivel-1-resposta` — ele toma o 1º `out` depois do cardápio, e as respostas do
corredor não entram em `observed_events`; o "1" da atendente no menu do RAMO virou "Automóvel" (P-E0014-01). Os guardas a leem
pelo ID. ② "falta de contato" no corpus: **0** — limitação nomeada, fica para a fatia 2 (D5) medir sobre o texto do banco.
③ máx `2026-09-14` ✓ · ④ linha de base commitada, 📊 **73 rotas** ✓ · ⑤ `INDICE.md` cita **15 de 16**: `tokio-condominio.jsonl` é arquivo antigo que o gerador hoje marca `FORA_DE_ESCOPO:condominio` (junta-se à pendência tokio da proposta §4.1) · ⑥ `--comparar-com` exit 0 ✓. **Bateria parcial** (os 52 testes que leem o corpus, antes × depois): 📊 2 regressões, AS DUAS causadas pelo corpus novo (confirmado com o código antigo): três `notes` com contagem vencida (`desfecho_protocolo_alfa` 10→25 · `escolher_endereco_da_lista` 17→35 · `servico_aberto_ver_ou_abrir` 6→10, redações distintas recontadas no ACERVO do banco) → recontadas → `test_a_regua_nao_tem_furo` 52/0 · `test_o_passo_compartilhado…` 10/0. Restam os 2 vermelhos de antes (`test_a_cobranca_chega_a_quem_deve`; `test_o_protocolo_tem_policia` — só "sem a nota 0–100" deste relatório: SPEC aberta até a entrega).

**Mutações dos guardas novos** (uma vez, worktree próprio, restauração por cópia conferida com `cmp`):

| mutação | guarda | resultado |
|---|---|---|
| M-A1 `resolver_tecla` devolve a palavra crua | GA-2 | 🔴 19/3 |
| M-A2 a camada 1 lê com `_NUMERADA` crua | GA-2/3 | 🔴 11/11 |
| M-A3 palpite ligado | GA-3 | 🔴 20/2 |
| M-A4 derivação do eletricista apagada | GA-1 | 🔴 21/1, nomeando o slot |
| M-B1 sem ④ · M-B2 contagem por SESSÃO · M-B3 o reparo reenvia a palavra · M-B4 prompt sem o bloco | GB | 🔴 24/1 · 21/4 · 21/4 · 23/2 |
| M-B3b sem ③ (só ela) | GB | ⚠️ **verde, por construção**: o casador do Atlas apaga dígitos (dígito nunca casa rótulo) e ④ também bloqueia — ③ é defesa em profundidade, registrada |

**Guardas novos:** 📊 `ls backend/tests/test_*.py | wc -l` = 376 → **378** (GA-2+GA-3 fundidos · GB-1+GB-2+GB-3 fundidos · GA-1 dentro do guarda existente).

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
| **D-E0014-01** | slot `*_opcao` VAZIO numa tela reversível continua indo ao Cérebro (desenho de 19/08), agora com as opções numeradas da tela no prompt; `needs_human` só para a tecla que decide o RAMO (`ramo_indeterminado`) e para `sem_chute`. Palavra que casa 0 opções segue a mesma regra; 2+ → `tecla_ambigua` | Cérebro + opções **88** · `needs_human/slot_opcao_sem_derivacao` geral, como a proposta §5.2 regra 3 **35** (reintroduz o travamento de 19/08 em 29 slots — o oposto do outcome) · `needs_human` reentrável **40** |
| **D-E0014-02** | `MAX_TENTATIVAS_POR_TELA = 2` · `MAX_TENTATIVAS_NA_SESSAO = 6` (env, com default). 📊 telas órfãs que pedem algo, distintas por sessão, no corpus de 17/09: 71 sessões · p50 **2** · p90 **12** · máx 62; **61/71 (86 %) ≤ 6** — a cauda é conversa humana longa, que deve ir a uma pessoa | 6 **85** · 12 (p90) **70** (o dobro de chamadas ao Cérebro em sessão que já vai mal) · 2 por sessão, o de hoje, **30** (é o defeito de 10/09) |
| **D-E0014-03** | teto de guardas: fundir GA-2+GA-3 e GB-1+GB-2+GB-3; GA-1 dentro do guarda existente — fatia 1 cria **2** arquivos | fundir **88** · 13 arquivos com addenda **55** |
| **D-E0014-04** | 🧑 **o Founder decidiu (17/09) rodar a fatia 1b nesta mesma sessão**, "para aproveitar o contexto", contra a regra de sessão nova (D-PROTO-07). Contexto da 1b: ~300 → ~530 k. A fatia 2 volta a sessão nova | decisão do Founder — registrada para a auditoria do A/B |
| **D-E0014-05** | o hub carrega `cartographer` e `atlas.weaver` pelo CAMINHO quando o pacote `app.services` foi montado à mão — 📊 75 testes fazem isso e `test_spec017` quebrou na 1ª rodada; é o mesmo arquivo, nunca uma cópia do parser | carregador **82** · import tardio com `except` que desliga a camada 1 em silêncio **30** · pré-carregar nos 75 testes **40** |

**Pendências novas (numa passada na entrega, fatia 2):** **P-E0014-01** 🤖 o classificador de ramo lê o 1º `out` depois do cardápio e as
respostas do corredor não estão em `observed_events` → sessões residenciais com resposta manual vão para o arquivo auto (📊 `432614de`);
destrava: nível 1 ignora `out` que segue outro menu; custo: a régua do residencial não vê justamente as sessões que erraram ·
**P-E0014-02** 🤖 `test_spec017`: além do defeito desta SPEC (agora verde), 3 checks pré-existentes que o `IndexError` escondia — "aberto
por padrão", plano esperado com 16 passos (hoje 42), `import app.atendimento` sob pacote falso · **P-E0014-03** 🤖 `test_golden_do_eletricista`:
14 → 2 vermelhos; sobram "pergunta de risco em português" e "nenhum passo com lacuna" — o plano de ensaio lista passos condicionais com
`[PENDENTE:]` (`cnpj_condominio`, `uf_do_local`, `escolher_entre_dois_enderecos`) · **P-E0014-04** 🤖 `test_spec031`: fixture sem
`local_seguro` (obrigatório desde 21–23/08) · **P-E0014-05** 🤖 `build_dry_run_plan` mostra a palavra crua no passo do menu numerado
(ele não lê tela; só apresentação).

## 10. Telemetria (§11)

## 11. Entrega

## 12. Handoff — fatia 2 (C + D + E, juiz, entrega), SESSÃO NOVA, mesmo prompt

```
1  Fatia 1 VERDE e commitada (§2). NÃO remeça o §1. Da proposta leia SÓ §7 (C), §8 (D), §9 (E), as linhas GC/GD/GT
   do §10, §12 (canário), §14 (entrega), §19. Pack: não. Base do juiz: `f7b23d7..HEAD`.
2  C · `note_manual_outbound` (dispatch_router.py, ~:2687) abre `pausa_humana` e escreve `silencio_deliberado_ate`
   (o Vigia já honra, dispatch_watchdog.py:~121). `foi_humano=False` não abre. A guarda EXISTE:
   `o_grupo_pode_saber` (o_grupo_so_o_que_importa.py:247) — acrescentar a causa `pausa_humana`, nunca outra guarda.
   Os 9 gatilhos da proposta §7.3: RECONFIRA por grep — a 001.3 moveu os envios para `enviar_ao_grupo`.
3  D · encerramento: regex inline "Seguradora ENCERROU" em `handle_insurer_message` + "falta de contato" (📊 10 ev,
   0 casam) + "vou precisar encerrar a conversa" (§1 item 11). "Isso pode levar alguns instantes" é FILA (item 10).
   Reentrada: o Vigia olha o ESTADO (`_TERMINAL_STATES`); o resumo usa regex inline (~:3350) → `APRESENTACAO_HUMANA`.
4  D6 · `agente.*` = 0 de 48.972 (item 8). Medir a causa: `registrar_ato_do_agente` devolve False sem `work_run_id`
   (dispatch_router.py ~:1011) — e a 001.3 tornou `work_events.work_run_id` NULLável (D-E0013-01).
5  B já grava `menu_pendente`/`ultima_resposta_recusada`/`tentativas_por_tela` na sessão: a pausa (C) e a reentrada (D)
   não podem apagá-los. `registrar_menu_pendente` roda em todo `_emit` — o eco humano (C) NÃO passa por `_emit`.
6  E · P-E0014-01 (classificador de ramo) · homônimos (porto `complemento`, hdi 5 pares) · azul `menu_atendimento` →
   "Novo serviço" (a camada 1 converte) · `medir_rota.py` "acesso ao Espelho" · INVENTÁRIO (`--formato markdown` roda 12
   mutações: não edite produto enquanto roda) · roteiro · `test_spec038` chamar o motor · P-E0014-02..05.
7  Guardas: 378 hoje (teto 12 na SPEC → sobram 10 para C/D/E+GT). GT mora em GC-3.
8  Fim: juiz Fable + lente do dado (`medir_rota.py --todas --com-espelho --comparar-com docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json`,
   hoje exit 0) → conserto → suíte inteira UMA vez, sozinha → PENDENCIAS/DECISIONS/ADDENDA numa passada → push.
```
