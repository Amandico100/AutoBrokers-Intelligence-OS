---
> **Status:** relatório de execução sob o **PROTOCOLO AAA v12 · AAA FAST** · EXTRA-001.4 · experimento B do A/B (D-PROTO-02)
> **Teto:** 15 KB (CRÍTICO); 25 KB quando o excesso for medição (D-PROTO-07)
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `f7b23d7`

```
OUTCOME ..............  menu numerado recebe NÚMERO lendo a tela real; "opção inválida" é reparada pelo motor
                        antes do Sentinela, uma vez por tela; humano da corretora na URA pausa o robô 60 s;
                        humano da seguradora é atendido mesmo com a sessão em needs_human; encerramento reconhecido;
                        a tela "qual seguro" responde pelo RAMO DA APÓLICE (🧑 decisão do Founder, 17/09)
RISCO ................  8   alcance SEGURADO 3 + "saiu do prédio" 3 (mensagem à URA) + TODO atendimento 2
SUPERFÍCIE ...........  2   vários comportamentos, lugares listados (proposta §3.2) e reconferidos por grep
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE" — a resposta à URA sai do prédio
NÍVEL ................  CRÍTICO · executor Opus 5 max (experimento B) · juiz Fable 5.1
UNIDADES .............  6 — fatia 1: 0-bis (acervo e linha de base) · A (regra B, tecla) · B (regra A, reparo)
                        fatia 2 (sessão nova): C (humano da corretora) · D (humano da seguradora) · E (adjacentes)
                        + F (o ramo da apólice vira a tecla — decisão do Founder de 17/09, entrou na fatia 2)
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

📊 (1) `parse_options` no menu real: cru **3** · `_norm` **3** · `_NUMERADA` sozinha **0** (`C.parse_options`/`C._NUMERADA.finditer`
nas 15 telas "3 - Empresarial") → a camada 1 usa `parse_options`, nunca a regex · (2) `*_opcao` **52** usados · **23** derivados ·
**29** órfãos (AST, 805 passos) · (3) `o_grupo_pode_saber` **existe** (`grep -rn "def o_grupo_pode_saber"`) · (4) slot vazio
"fica calado": **falso** desde 19/08, tela reversível vai ao Cérebro → D-E0014-01 · (5) a recusa **não** repete o menu (2 bolhas,
`observed_events` de `432614de`) · (6) recusas de menu: allianz **26 ev/14 sess** · porto **15** · mapfre **7** · azul 2 · bradesco 3 ·
hdi 2 · tokio 1 (`direction='in'`, `group by`) · (7) `sentinela_attempts` por sessão, nunca zerado (`grep -rn`) · (8) `agente.*`
**0** de 48.972 e sem CHECK em `event_type` (`pg_constraint`) → **sem migration** · (9) "falta de contato" **10** ev, **0** casam
(Postgres `~*`) · (10) "Isso pode levar alguns instantes" existe no banco (3×, 10/09): é fila · (11) "vou precisar encerrar a
conversa" porto 6/azul 1 não casava · (12) `observed_events` **32.817**, **1.048** em setembro (`count(*)`).

**Triagem nominal (item 9)** — `python tests/<arquivo>.py` na base `f7b23d7` e em `cffaa0e` (07/09, antes das 5 entregas sem SPEC): 📊 os 4 vermelhos já o eram em 07/09 — nenhum é regressão de 08–10/09. `test_spec017_dispatch` (IndexError em `qual_seguro_opcao`) era **defeito desta SPEC** e ficou com só os 3 pontos antigos (P-E0014-02); `test_spec031_auto_dispatch` é fixture vencida (P-E0014-04); `test_o_corredor_conhece_a_tela_que_esta_na_frente` e `test_spec034_onda1` (import quebrado no próprio teste) são **anteriores** (vermelhos na base e em 07/09); a triagem por diff da bateria (§6) diz se esta SPEC os mudou.

### 1-bis. BLOCO 0 da fatia 2 (sessão nova, 📊 17/09, preflight `HEAD..origin/main` = 0 · HEAD `ecf91e2` · base `f7b23d7`)

| # | premissa (handoff · proposta) | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | a fala manual da atendente chega a `note_manual_outbound` | chega com o agente ligado (`observer_intake.py:820-829`; ramo `fromMe` do webhook) | leitura da linha 1 + `grep` | C mora no roteador |
| 2 | AGENTE/EU CUIDO "lidos na entrada do grupo" | 🔴 toda instância nasce com `ignoreGroups: True` (3 lugares) e o grupo é `skip` na normalização | `grep -rn ignoreGroups app/` | D-E0014-08 · P-E0014-06 |
| 3 | os 9 gatilhos de grupo (§7.3) | a 001.3 os reduziu a 4 (pedido de ajuda, aviso de protocolo, `never_started`, dossiê do Sentinela) | leitura | GC-3 + AST de `sessao=` |
| 4 | `agente.*`=0 porque falta `work_run_id` | **falso** (`travamento.assumido` de 10/09 gravou com o run): só o ACERTO gravava; 📊 6 runs, 3 `sentinela_stall`; `agente.%` **0** de 49.038 | SELECT em `work_events`/`work_runs` | D6 grava todo desfecho |
| 5 | a regex inline do resumo × a tabela | 📊 19.023 ev `in`: na zona HUMANO, **as mesmas sessões** (allianz 113 · porto 19 · yelum 17 · mapfre 13 · hdi 12 · azul 2 · bradesco 2); na zona URA a inline casa **77**; dialeto: **43** ev mudam | script `zonas()` × `_norm` | uma fonte só |
| 6 | "falta de contato" 10 ev | allianz 9 é encerramento; a hdi (1) é "colocada em ESPERA". Mais 4 redações de encerramento não reconhecidas: porto 6 + azul 3, zurich 9, porto 40, porto 7; e avisos que NÃO encerram: bradesco 11, mapfre 19, porto 9 | `norm_para_classificar` sobre `observed_events` | `ENCERRAMENTO_DA_SEGURADORA` |
| 7 | 🧑 o ramo da apólice | só ao vivo na InfoCap (`Apolice.ramo`); ficha **1 de 942**; a ferramenta não o recebia | investigador read-only + SELECT | D-E0014-07 |
| 8 | `test_spec038_sentinela` guarda o Sentinela | é o **Sentinela de Rotas** (drift) e chama o motor dele | leitura | D-E0014-15 |
| 9 | homônimos | hdi-residencial: 5 pares com resposta **idêntica**; porto-auto `complemento`: "não tem" (índice 11) × `{local_complemento}` (39) | motor (`_PLAYBOOKS`) | D-E0014-12 |
| 10 | — (achado) | 🔴 `pyflakes` sobre `f7b23d7`: `dispatch_router.py:3321: undefined name 'get_supabase_client'` (desde `21f2243`) → o dossiê do roteador derrubava o bloco `needs_human` | `python -m pyflakes` | BLOCKER, consertado |
| 11 | a apresentação humana está no corpus | **0**: o corpus guarda só a zona URA; a redação mais frequente da allianz no banco tem **8** ev | script | GD usa a estrutura com nome fictício |

## 2. As unidades entregues, por fatia

| fatia | unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|---|
| 1a | BLOCO 0 | este relatório | §1 | 12 premissas remedidas; 1 decisão (D-E0014-01) | `acb6814` |
| 1b | 0-bis | corpus (12 de 16 arquivos mudaram) · `INDICE.md` · `LINHA-DE-BASE-DE-ROTAS.json` | `gerar_corpus_de_telas.py --todas` · `--auditar-pii` · `test_o_corpus_nao_vaza_pii.py` · `medir_rota.py --salvar-linha-de-base` e `--comparar-com` (controle) | 📊 39 s · **4.470 telas, 0 sujas** · guarda exit 0 · máx `2026-09-14` · controle **exit 0** | ver §11 |
| 1b | A | `insurer_dispatch_service.py` (`resolver_tecla`, `opcoes_numeradas`, derivação do ramo, `origem_das_teclas`) · 2 fixtures vencidas | GA-1 `test_a_tecla_tem_a_forma_da_seguradora.py` · GA-2/3 `test_o_menu_numerado_recebe_numero.py` | **22/0 · 22/0** — na base: 17/**5** · `AttributeError` | ver §11 |
| 1b | B | `insurer_dispatch_service.py` (reparo, `menu_pendente`, prompt) · `dispatch_watchdog.py` (por tela) | GB `test_a_opcao_invalida_e_reparada.py` | **25/0** — na 1ª rodada pegou `RecursionError` no Sentinela (um `replace_all` meu), consertado | ver §11 |
| 1b | GR | — | `medir_rota.py --todas --com-espelho --comparar-com …LINHA-DE-BASE…` | **exit 0**: nenhuma rota perdeu respondidas · nenhum passo sem confirmação | — |
| 2 | F 🧑 ramo | `nodes.py` (a família do ramo da apólice selecionada → `ramo_da_apolice`) · `insurer_dispatch_tool.py` · `attendance_ficha.py` · `corridor_playbooks._COMO_PERGUNTAR` · hub (`rotulo_do_ramo_da_apolice`) | GA-1 | **25/0**: `resi/cond/empr` → **1/2/3** pelo motor, lendo a tela real; o ramo vence a palavra da atendente; o relato não decide | `ff74680` |
| 2 | C | hub (pausa pura) · roteador (`note_manual_outbound`, `ler_palavra_da_equipe`) · guarda única (causa `pausa_humana` + índice) · Vigia · webhook | GC + GT `test_a_atendente_na_ura_cala_o_robo.py` | **44/0** | `ff74680` · `7346cdc` |
| 2 | D | `quem_fala_na_seguradora.py` (tabelas, 📊 44.700 classificações idênticas às do script) · hub (encerramento, reentrada, âncora positiva, resumo) · roteador (pergunta ao segurado, rastro) · Vigia (dois relógios, holding, rastro, releitura) | GD + D3 `test_o_humano_da_seguradora_e_atendido.py` | **45/0** | idem |
| 2 | E | `corridor_playbooks.py` (porto sem o `complemento` morto; azul pelo rótulo) · `medir_rota.py` (📊 `grep -c "acesso ao Espelho"` = **0**) · homônimos na régua | `test_a_regua_nao_tem_furo.py` · `test_o_corpus_nao_vaza_pii.py` | verde · exit 0 | `ff74680` |
| 2 | GR | — | a mesma régua sobre `7346cdc` | **exit 0** (📊 5 s): nenhuma rota perdeu respondidas · nenhum passo sem confirmação | — |

**Mutações da fatia 2** (cópia conferida byte a byte): 📊 **20/20 vermelhas** — C (abertura/renovação sem silêncio, sem teto, eco pausa, dossiê sem `sessao=`, motor/EU CUIDO respondendo, `_key` sem corretora, import do dossiê, Vigia sem a pausa, Sentinela sem releitura) · D (controle do robô na regra e na tabela, `insurer_closed` reentrável, relógios fundidos, sem "falta de contato", Cérebro sem rastro, regex inline, pergunta desligada) · E (`complemento` morto). ⚠️ Três ficaram verdes na 1ª rodada e mostraram furos, fechados em `7346cdc` (o Vigia só lia o silêncio; a regra e a tabela se mascaravam).
**Guardas novos:** 📊 `ls backend/tests/test_*.py | wc -l` = **376** na base → **380** (fatia 1: 2 · fatia 2: 2 · teto 12).

**Gate 0-bis:** ① a sessão `432614de` está no corpus pelo ID (📊 13 telas), mas em `allianz-auto.jsonl` (o classificador lê o 1º `out` depois do cardápio — P-E0014-01) · ② "falta de contato" no corpus: 0 (a frase é de setembro; a D5 mediu no banco) · ③ máx `2026-09-14` · ④ linha de base commitada, 📊 73 rotas · ⑤ `INDICE.md` 15 de 16 (P-E0014-10) · ⑥ `--comparar-com` exit 0. Bateria parcial (52 testes do corpus): 📊 2 regressões, as duas do corpus novo — três `notes` recontados (10→25 · 17→35 · 6→10).

**Mutações da fatia 1** (worktree próprio, cópia conferida com `cmp`): 📊 M-A1 palavra crua 🔴19/3 · M-A2 `_NUMERADA` crua 🔴11/11 · M-A3 palpite 🔴20/2 · M-A4 sem a derivação do eletricista 🔴21/1 · M-B1…B4 🔴 · M-B3b sem ③ ⚠️ verde por construção (dígito nunca casa rótulo; ④ também bloqueia). Guardas: 376 → 378 na fatia 1.

🔴 A fatia 1a fechou no BLOCO 0 pelo teto de contexto (📊 300 k antes da 1ª linha de produto); a 1b rodou na mesma sessão por ordem do Founder (D-E0014-04). ⚠️ `gerar_corpus_de_telas.py --todas --auditar-pii` não regenera (`--auditar-pii` retorna antes, `:495`): a ordem certa é `--todas` e depois `--auditar-pii`.

## 3. Migrations — nenhuma (BLOCO 0 item 8: `work_events.event_type` não tem CHECK)

## 4. O juiz fresco (Fable 5.1, sobre `7346cdc`, 73 chamadas, 20 min) — VEREDITO **FAIL** · nota **84**

| # | achado | teste do produto | medição (do juiz) | classe | conserto |
|---|---|---|---|---|---|
| B1 | o Cérebro do roteador não relia a sessão entre pensar e falar | a URA recebe tecla por cima da atendente; a gravação apaga a pausa e a fala dela | corrida com dublês: com ela no meio, saída `['Centro']` e `pausa_humana=null`; controle sem ela, `[]` | **BLOCKER** · EXCLUSIVO do juiz | `_a_atendente_entrou` depois de cada chamada |
| P1 | 📊 "805" → 804; "porto 40" → 45 | comentário | contagem | pendência | corrigido |
| P2 | a resposta do segurado não apaga `falta_para_a_ura` | dossiê diria "falta X" já respondido | leitura `build_handoff_dossier` | blocker (byte à corretora) | corrigido |
| P3 | `ambigua` engolida pelo webhook | a palavra da equipe some sem rastro | `webhook.py` | blocker | corrigido |
| P4 | `apartamento/loja/comercial` sem família | a pergunta do ramo volta | `familia_de_ramo` | blocker | sinônimos na autoridade |
| P5 | resposta vai verbatim à URA | "como assim?" viraria referência | leitura | pendência + filtro mínimo (`?`) | P-E0014-13 |
| P6 | a D3 não obedecia o portão `live` de `_emit` | em ensaio, a pergunta sairia de verdade | leitura | blocker | `ao_vivo` nos 4 envios |
| P7 | AGENTE depois de EU CUIDO perdia o motivo | sessão travada sem motivo não reentra | leitura | blocker (banco) | corrigido |

**Lente do dado** (Opus 5, cega, 26 min) — **nota do dado 70**, confiança 90. BATEM: GR exit 0 (e acusa a âncora do tronco
quebrada) · agente.% 0 de 49.071 · 6 runs, 3 `sentinela_stall` · 43 ev de dialeto · as mesmas 178 sessões humanas, 1º disparo no
mesmo evento · tabelas idênticas (190.230 classificações no banco, 0 diferentes) · ficha 1/942 · ramo → 1/2/3 em 21/21 telas.
NÃO BATEM: **L1** 🔴 `conversa ser[áa] encerrada` marcava **51 avisos condicionais** (hdi 26 · yelum 22 · mapfre 2 · porto 1; a
conversa seguia) — anterior à SPEC, EXCLUSIVO · **L2** 🔴 3 sessões humanas que só a regex antiga pegava (itálico; "continuidade
AO") — nasce da SPEC, EXCLUSIVO · comentários (77 do robô eram 26 pessoas; porto 45 + azul 8; a allianz diz "sou da", 233/239).
Limite: a régua não vê o VALOR da resposta (P-E0014-14).

## 5. O conserto único (`a583a0a`) — B1, P2–P7, L1, L2 e os comentários

B1 → `_a_atendente_entrou` (Redis puro) depois das DUAS chamadas ao Cérebro. L1 → o futuro "será encerrada" só encerra se não for condicional: 📊 **183** encerramentos marcados (eram 232), as **16** telas condicionais do corpus não encerram e o motor não fecha a sessão. L2 → `_?` antes do nome e `(em|no|ao)`: 📊 a zona humana segue com as mesmas **178** sessões; as 3 recuperadas estão na zona URA (sem fronteira; 30 ev, eram 26). **Gates rerodados:** GA-1 27/0 · GA-2/3 22/0 · GB 25/0 · GC 48/0 · GD 56/0 · PII e GR exit 0 · guardas do `fromMe` exit 0. **Mutações do conserto:** 📊 **8/8 vermelhas**. Total da fatia 2: **30 mutações, 30 vermelhas** (20 do build · 5 do juiz · 3 da lente · 2 da confirmação).
**Confirmação** (§6.1, disparada por B1 em código que envia; Fable 5.1, 31 chamadas, 14 min, nota **84**): conserto CONFIRMADO nos 8 ataques e **1 defeito residual**: a tela do turno entrava DEPOIS da fala dela → vencida a pausa, o Sentinela a responderia de novo. Consertado em `22aa479` (grava com espelho e reordena no Redis) + o infinitivo "dar continuidade ao" recusa instrução do robô (📊 zona humana 178, zona URA 30). 📊 **2/2 mutações vermelhas**; GC **50/0** · GD **57/0**. Sem 2ª confirmação: o teto de agentes da sessão foi atingido (hook, 4 de 4).

## 6. A bateria — 📊 1 rodada inteira no HEAD (+ 1 na base, como linha de base) · triagem por DIFF

Mesmo ambiente nos dois lados (worktree com `.env`): base `f7b23d7` **376 arquivos · 331 verdes · 45 vermelhos · 1.859 s** ·
HEAD `22aa479` **380 · 329 · 51 · 1.742 s**. Os 4 guardas novos: verdes. **Verde→vermelho: 6**, e a triagem nominal:
`test_a_atendente_sabe_conduzir_um_acionamento` e `test_a_cobertura_tem_lastro_no_acervo` (o rótulo novo do ramo levou o bloco
de conhecimento a 📊 7.195 de 7.000; a base estava em 6.997 → rótulo curto, **6.990**) · `test_ninguem_fala_com_o_segurado_sem_o_agente_ligado`
(o "um instante" do Vigia, nomeado como isenção, com o motivo do Sentinela) · `test_o_contrato_alcanca_o_portao` (`ramo_da_apolice`
nomeado como metacampo) · `test_o_sinistro_deixa_rastro` (a fatia 1 consertou o golden — 14→2 problemas, `gold_007` não explode:
a linha de base migrou, §9.3) · `test_o_protocolo_tem_policia` (esperava a nota deste relatório). Os 5 consertados em `4476891`
e rerodados: exit 0. **Vermelho→verde: 0** na suíte (o golden melhorou por dentro, 14→2, e segue vermelho pelos 2 antigos). Os
45 vermelhos dos dois lados são anteriores (P-E0014-02/03/04 entre eles).

## 7. O que ficou fora, e o gatilho que o faz voltar

AGENTE/EU CUIDO digitados **no grupo** (o canal não entrega grupos → P-E0014-06, 🧑) · inventário `--formato markdown` e roteiro
(mutam o produto; depois do Implantar → P-PILOTO-06) · o classificador de ramo do corpus (P-E0014-01) · derivar os 28 órfãos à mão
(a camada 1 cobre) · canário vivo (🧑 número de teste + Implantar, §8).

## 8. 📋 Caixa do Founder

| item | o que faz | custo de esquecer | bloqueia? |
|---|---|---|---|
| **Implantar** o serviço do atendimento/dispatch (o que roda `buffer_processor` e o Vigia) | põe a pausa, a reentrada, o encerramento, a pergunta ao segurado, o ramo da apólice e o conserto do dossiê no ar | 📊 desde 16/09 o dossiê do roteador não sai (NameError) | não |
| **Decidir o canal do grupo** (P-E0014-06) | ligar grupos na instância (medir volume: 240/min) **ou** botões AGENTE/EU CUIDO na Fila | a atendente que responde no grupo não é ouvida; hoje vale o privado do número de suporte e dos números da casa | não |
| **Canário** (§12 da proposta) com TESTE-A/TESTE-B | 1 coleta dirigida até a confirmação e RECUSA · a pausa (digitar à mão) · AGENTE e EU CUIDO pelo número de suporte · uma tela que pede dado fora da ficha · `select event_type, count(*) from work_events where event_type like 'agente.%'` sai de 0 | "testado" continua sendo só suíte | não |
| Validação com Saionara e Regina (§13) | copy da pausa, 60 s, pergunta ao segurado, "retomei" | aceite só se recebido | não |
| variáveis novas (todas com padrão) | `PAUSA_HUMANA_S`=60 · `PAUSA_HUMANA_MAX_RENOVACOES`=2 · `REENTRADA_FASE_HUMANA`=1 · `FILA_ALERTA_S`=1200 · `PERGUNTA_AO_SEGURADO_HOLDING_S`=60 · `…_HOLDINGS`=2 · `MAX_TENTATIVAS_POR_TELA`=2 · `…_NA_SESSAO`=6; desligar: `PAUSA_HUMANA_S=0`, `REENTRADA_FASE_HUMANA=0` | — | não |

## 9. Pendências e decisões

D-E0014-01…05 (fatia 1) e D-E0014-06…16 (fatia 2): `FOUNDER-DECISIONS.md`, fim do arquivo.

**Registradas na entrega** — `PENDENCIAS.md`: P-E0014-01…16 · P-PILOTO-05 e P-PILOTO-06 `CONTINUA` (com o que destrava) · `FOUNDER-DECISIONS.md`: D-E0014-06…16 (fatia 2) · `CHANGE-ADDENDA.md`: 4 entradas (1 BLOCKER, 2 ESSENCIAIS, 1 VALIOSA). As da fatia 1: **P-E0014-01** 🤖 o classificador de ramo lê o 1º `out` depois do cardápio e as
respostas do corredor não estão em `observed_events` → sessões residenciais com resposta manual vão para o arquivo auto (📊 `432614de`);
destrava: nível 1 ignora `out` que segue outro menu; custo: a régua do residencial não vê justamente as sessões que erraram ·
**P-E0014-02** 🤖 `test_spec017`: além do defeito desta SPEC (agora verde), 3 checks pré-existentes que o `IndexError` escondia — "aberto
por padrão", plano esperado com 16 passos (hoje 42), `import app.atendimento` sob pacote falso · **P-E0014-03** 🤖 `test_golden_do_eletricista`:
14 → 2 vermelhos; sobram "pergunta de risco em português" e "nenhum passo com lacuna" — o plano de ensaio lista passos condicionais com
`[PENDENTE:]` (`cnpj_condominio`, `uf_do_local`, `escolher_entre_dois_enderecos`) · **P-E0014-04** 🤖 `test_spec031`: fixture sem
`local_seguro` (obrigatório desde 21–23/08) · **P-E0014-05** 🤖 `build_dry_run_plan` mostra a palavra crua no passo do menu numerado
(ele não lê tela; só apresentação).

## 10. Telemetria (§11) — `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (📊 17/09 05:14 UTC)

```
relógio total · por fase ①–⑥ ........  ~2h50 (02:37→05:27 UTC) · ① leitura+BLOCO 0 23 min · ② build 39 · ③ mutações+GR 15
                                        · ④ juiz+lente 27 · ⑤ conserto+confirmação 29 · ⑥ bateria 29 + triagem e entrega 21
turnos · contexto de pico ...........  executor 249 · 882 k · investigador 73 · 199 k · juiz 18 · 273 k · lente 57 · 242 k
                                        · confirmação 14 · 163 k  (🧑 D-E0014-06: fatia 2 inteira na sessão, por ordem do Founder)
ctx-tokens · saída ..................  166,9 M · 0,41 M  (executor 143,0 M · 396 k)
US$ API-equivalente .................  executor 86,30 · investigador 2,57 · juiz 4,04 · lente 6,14 · confirmação 2,17 · total 101,23
agentes além do executor ............  4 (hook: 4 de 4)
achados por mecanismo ...............  executor: dossiê sem import (BLOCKER, EXCLUSIVO) · canal sem grupos · causa do agente.* ·
                                        prova mecânica: 3 mutações verdes → 2 furos reais + 1 guarda que não falhava (EXCLUSIVOS) ·
                                        juiz: B1 (EXCLUSIVO) + 5 pendências que mudavam byte · lente: L1, L2 (EXCLUSIVOS) + 6 números ·
                                        confirmação: 1 residual (EXCLUSIVO) · bateria: 5 regressões minhas (EXCLUSIVAS) · canário: não rodou
rodadas da bateria ..................  inteiras 1 (HEAD) + 1 (base, linha de base) · parciais: os guardas da SPEC e os 129 dirigidos
nota da execução ....................  85/100 — critério: todo o outcome no código, provado pelo motor sobre o acervo com 30
                                        mutações vermelhas e 8 defeitos de produto achados fora do build e fechados; −5 o grupo
                                        não chega (canal), −5 canário não rodado, −5 teto de contexto · nota do juiz 84/100
```

## 11. Entrega — push e o que Implantar

📊 17/09 ~05:35 UTC, `git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main`:
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   f7b23d7..f442965  HEAD -> main
origin/main = f442965 = HEAD local · origin/main..HEAD = 0
```
(este parágrafo sobe num commit de documentação logo depois, com o mesmo comando). **Implantar:** o serviço do atendimento/dispatch (o que roda `buffer_processor` e o Vigia) —
um só; nenhuma migration; nenhum arquivo de `app/`/`middleware`/`next.config` do painel (rotas-montam não se aplica; o
backend foi provado por import de todos os módulos tocados, sem subir o servidor com o `.env` de produção, que ligaria o Vigia).
Variáveis novas: §8. **Nenhum motor paralelo** (CLAUDE.md §5): a guarda do grupo é a da 001.3 (causa nova), as tabelas de quem
fala mudaram de casa (o script as importa), a espera é a sessão + o Vigia, o registro é `_evento`, o ramo é
`familia_de_ramo`, o parser é `cartographer.parse_options`.

## 12. Handoff

Sem próxima fatia: a fatia 2 fechou a SPEC. O handoff da fatia 1 foi cumprido item a item (§1-bis, §2, §7).
