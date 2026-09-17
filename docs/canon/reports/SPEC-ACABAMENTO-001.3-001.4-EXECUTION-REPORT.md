# ACABAMENTO 001.3 / 001.4 — a atendente não aprende palavra, o "um instante" só com pessoa, e o isolamento provado

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `259a489`

```
OUTCOME ..............  (T1) 1 fala da atendente = o robô espera 15 s; 2 falas em 15 s = ele sai do
                        acionamento, em silêncio. Nenhuma palavra a decorar, nenhum aviso.
                        (T2) "um instante" só com PESSOA; o Cérebro tenta com o que já existe (com
                        prova de origem) antes do segurado; o que faltou vira rastro; ninguém fica
                        no vácuo e a resposta tardia não se perde.
                        (T3) o isolamento da 001.3 provado com dois tenants REAIS (P-E0013-08).
RISCO ................  8  (alcance 3 segurado · reversibilidade 3 mensagem à seguradora · frequência 2)
SUPERFÍCIE ...........  1  (um comportamento, em lugares listados)
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE mensagem" → CRÍTICO, independente da conta
NÍVEL ................  CRÍTICO · executor/builder Opus 5 xhigh · juiz Fable 5.1 (o gerente convoca)
UNIDADES .............  T1 · T2 · T3 — UMA fatia, nesta ordem, um commit por unidade
COESÃO ...............  T1 e T2 tocam motor · roteador · Vigia · webhook — um dono só (§3.4)
PARALELISMO REAL .....  nenhum — escrita de um só; investigador read-only: não
TIME .................  builder · juiz Fable 5.1 · confirmação §6.1 (o gatilho DISPAROU: blocker em código que ENVIA)
REFERÊNCIA ...........  interna: os dois guardas do escopo · `scripts/medir_rota.py --com-espelho`
GATES ................  os guardas migrados (§9.3) + os PARES + o guarda de dois tenants + mutação por regra + `medir_rota --comparar-com` + py_compile + vizinhos
O ELO ................  "a atendente perde tempo PORQUE tem de aprender AGENTE/EU CUIDO" — 📊 medi B
                        (`aviso_da_pausa_humana`), e que B CHEGA em A (saía a CADA pausa, pela porta
                        única, isento da própria guarda). Conserto: 📊 0 envios.
FAIXA DE RELÓGIO .....  declarada 💭 90–120 min · real ≈ 150 + 60 (conserto) + 30 (confirmação)
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** acabamento das EXTRA-001.3 / 001.4 (prompt do gerente) ·
**Branch:** `feat/acabamento-001-3-001-4` ·
**Preflight** 📊 17/09/2026: `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `259a489` ·
árvore limpa (dois arquivos soltos, ignorados por instrução) · **Builder:** Opus 5 `xhigh` (sessão nova).

## 1. BLOCO 0 — as premissas que mudariam o desenho

| # | o prompt afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | leitores de `pausa_humana`/`humano_assumiu` | motor, roteador, grupo, Vigia. ⚠️ `claims.humano_assumiu` (painel) é outro fato | `grep -rn` | nenhum leitor de fora |
| 2 | chamadores de `perguntar_ao_segurado` e do holding do Vigia | **1** cada (`dispatch_router:3457` · `dispatch_watchdog:888`) | `grep -rn` | dois pontos de envio, os dois consertados |
| 3 | o Cérebro é consultado no estado `ura`? | **NÃO.** `human_reply_provider` só em `human_phase`; `_adaptive_reply` só pelo Sentinela após 30 s | `grep -n` | a chamada do T2 é **nova** e é **UMA** |
| 4 | como o guarda lê os dois tenants | molde `regua_motor.py`. 📊 **5** corretoras; `company_internal_numbers` com **0** linhas | `python -c "import regua_motor…"` | ids reais, linha de dublê (P-E0014-21) |
| 5 | 🔴 (achado do builder) `state == "human_phase"` prova que há pessoa? | **NÃO.** A última linha de `handle_insurer_message` promove qualquer tela sem âncora de URA | script sobre a tela do corpus | o critério virou `humano_falou_em`/`fronteira_em` |
| 6 | 📊 contagem dos guardas de referência | o card dizia 44 e 45; medido **50** e **57** | `python tests/<arq>.py` | o meu número vence |

## 2. As unidades entregues, por fatia

| unidade | gate (comando) | saída real | commit |
|---|---|---|---|
| **T1** · 1 fala espera 15 s, 2 falas assumem, nada sai | `python tests/test_a_atendente_na_ura_cala_o_robo.py` | **57 verdes · 0** (era 50) · exit 0 | `6a74c20` |
| **T2** · holding só com pessoa · Cérebro antes do segurado · rastro · ninguém no vácuo | `python tests/test_o_humano_da_seguradora_e_atendido.py` | **84 · 0** (era 57) | `10b2304` |
| **T3** · isolamento com dois tenants reais | `python tests/test_os_numeros_da_casa_nao_atravessam_corretoras.py` | **19 verdes · 0** · exit 0 | `f039291` |
| conserto do juiz (3 blockers + P1/P3/P5) | idem T2 | **108 · 0** | `27bc82b` |
| confirmação (D1 + P-a) | idem T2 | **128 · 0** | (este commit) |

**Regressão dirigida** — `medir_rota.py --todas --com-espelho --comparar-com docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json` (base `acb6814`): **exit 0**, "OK nenhuma rota perdeu respondidas (R3 satisfeita)" · "OK nenhum passo responde sem confirmacao". 📊 Saída **byte a byte idêntica** à medida ANTES da 1ª edição e à de depois do conserto (`diff` vazio) — a linha de controle.

**Vizinhos** (todos exit 0): `a_anotacao_da_atendente` · `a_atendente_fala_e_o_robo_cala` · `ninguem_fala_com_o_segurado_sem_o_agente_ligado` · `o_grupo_so_fala_de_quem_precisa` (33) · `o_numero_da_casa_nao_e_cliente` (20) · `o_travamento_vira_evidencia` · `o_sinistro_deixa_rastro` (**249 ok · 0**) · `a_maquina_de_lavar` (**112**).

**As mutações da construção — cada regra nova fica VERMELHA** (restauradas por cópia, nunca `git checkout`; árvore conferida no fim): **M1** janela de 60 s · **M2** a 2ª fala renova em vez de assumir · **M3** o aviso ao grupo volta (5 asserções) · **M4b** o Vigia ignora `humano_assumiu` · **M5** holding com robô · **M6** Cérebro não consultado · **M7** prova de origem desligada · **M8** rastro `dado_faltou` some · **M9** espera vencida não guardada · **M10** o Vigia fala com robô · **M11** o filtro `company_id` some · **M12** a guarda ignora os números da casa.

⚠️ **M4** (`needs_human` fora de `_TERMINAL_STATES`) ficou **VERDE** — mutação equivalente para esta forma de sessão. Foi ela que fez nascer a asserção do Sentinela, e a **M4b** passou a pegá-la.

## 3. Migrations — nenhuma

Nada de SQL. `company_internal_numbers` (`20260916_01`) foi **só lida** (SELECT de contagem).

## 4. O juiz fresco (Fable 5.1, sobre `f039291`) — VEREDITO **FAIL** · nota **58/100**

T1 e T3 passaram; os três blockers e as cinco pendências são todos do **T2**.

| # | achado do juiz | teste do produto | classe | conserto |
|---|---|---|---|---|
| **B1** | `o_cerebro_ja_sabe` espera até 20 s e responde/grava **sem reler o Redis** — 2 falas nesse intervalo e a gravação stale deixa `state=ura, humano_assumiu=False` | **SIM** | BLOCKER | `_a_atendente_entrou` **antes** de qualquer envio/gravação |
| **B2** | `valor_tem_origem` usava `substring` com `len ≥ 2`: `"10"` em `100`, `"20"/"21"` em `2021`, `"999"` no telefone, `"casa as"` colando campos | **SIM** — valor inventado chega à seguradora com "prova" | BLOCKER | sequência de **tokens** dentro de **UMA linha**; CPF/telefone/documento/e-mail fora das fontes |
| **B3** | prazo do segurado 180 s contra os ≈ 103 s da Allianz: o encerramento apagava a espera e a retomada reabria sem o dado | **SIM** — a resposta se perde e a pergunta repete | BLOCKER | `espera_vencida` no encerramento; a retomada carrega `perguntado_ao_segurado`; a resposta tardia vai ao **SLOT** |
| P1 | busca `user_phone` numa forma só — 📊 ~100 conversas com LID de 15 dígitos e 66 com 13 invisíveis ao Cérebro | SIM (a "pergunta óbvia") | → **consertada** | `in_(..., _variantes_do_telefone(...))` |
| P3 | a mesma fala entregue 2× pelo canal virava assunção silenciosa (a Evolution não deduplica; só a Z-API) | SIM | → **consertada** | `message_id` + Redis `SET NX`/15 min |
| P5 | `_preservar_a_atendente` não copiava `motivo_antes_do_humano` | SIM (AGENTE devolvia a sessão travada sem o motivo) | → **consertada** | o campo entrou na lista |
| P2 | `fronteira_em` é escrito pelo anúncio do robô — o holding sai para a fila | baixo | **registrada** | `P-E0014-20` |
| P4 | o T3 usa ids reais com dublê de banco (0 linhas na tabela) | não | **registrada** | `P-E0014-21` |

## 5. O conserto único — tudo junto, uma passada

Arquivos: `dispatch_router.py` (B1·B2·B3·P1·P3) · `insurer_dispatch_service.py` (B3) · `dispatch_watchdog.py` (P5) · `webhook.py` (P3, passa o `message_id`) · o guarda do T2 (**84 → 108** asserções). A docstring de `perguntar_ao_segurado`, que afirmava o contrário do código sobre a inatividade da URA, foi corrigida.

**Gates rerodados** — **57/0** · **108/0** · **19/0** · `o_grupo_so_fala_de_quem_precisa` **33/0** · `o_sinistro_deixa_rastro` **249 ok · 0** · `a_maquina_de_lavar` **112/0** · `py_compile` 5 · `medir_rota --comparar-com` **exit 0**, `diff` vazio.

**As mutações do conserto — todas VERMELHAS:** **M13** a releitura depois do Cérebro some (B1) · **M14** `substring` sobre o texto achatado (B2) · **M15** CPF/telefone voltam a ser fonte (B2) · **M16** a espera não sobrevive ao encerramento (B3, 5 asserções) · **M17** a retomada não carrega `perguntado_ao_segurado`/espera (B3, 6) · **M18** a resposta tardia vai para a tela errada (B3) · **M19** uma forma só do número (P1) · **M20** sem dedupe da fala reentregue (P3) · **M21** `motivo_antes_do_humano` não preservado (P5).

### 5.1 A confirmação §6.1 (juiz novo, só o diff do conserto) — **CONFIRMADO COM PENDÊNCIAS** · nota **80/100**

| # | achado | teste do produto | classe | o que foi feito |
|---|---|---|---|---|
| **D1** | criado pelo B3: `no_slot` valia sempre que a espera vinha de outro acionamento, sem olhar a tela de AGORA — 📊 ninguém responde a tela, a URA fecha por inatividade e o retry único já foi queimado; cai em pessoa | **SIM** (muda byte) | BLOCKER | `na_tela_do_slot`: com `state=="ura"` e `falta_para_a_ura.slot == espera.slot`, a resposta é **`levada`** à URA **e** vai ao slot |
| **P-a** | `_CAMPOS_FORA_DA_FONTE` casava por substring: `fone` excluía `interfone`; `rg` excluía `orgao_emissor`, `cargo`, `largura`, `energia` | latente | pendência → **consertada** | casamento por **token** sobre o nome normalizado |
| P-b | o índice cliente→seguradora expira em 420 s no ramo `seguradora_encerrou` (o Vigia estende +3600, esse ramo não) | sim, depois de 7 min | **registrada** | `P-E0014-22` |
| P-c | valor multi-token repartido em duas mensagens é recusado pela prova de origem | não — falha para o lado seguro | **registrada** | `P-E0014-23` |

**Gates da confirmação** — **57/0** · **128/0** (era 108) · **19/0** · `o_sinistro_deixa_rastro` **249 ok · 0** · `py_compile` 4 módulos. Mutações: **M22** (sem a condição da tela, o caso (a) fica vermelho) · **M23** (P-a volta a substring, 5 asserções).

## 6. A bateria — o gerente roda

Aqui rodaram: os 3 guardas do escopo, 8 vizinhos, a regressão de rota com linha de controle e **22** mutações (13 da construção + 9 do conserto).

## 7. O que ficou fora, e o gatilho que o faz voltar

- **Reabrir a URA pelo nosso lado** (`P-E0014-19`): 📊 o corredor só reentra quando alguém da seguradora fala, e `pode_retomar` impede um segundo acionamento. Com o caso já entregue a uma pessoa, a resposta tardia é **guardada**. **Não inventei a reabertura.**
- **A apólice não viaja na sessão** (`P-E0014-18`) · **`fronteira_em` vem do anúncio do robô** (`P-E0014-20`) · **T3 com dublê de banco** (`P-E0014-21`, o teste declara o limite) · **índice de 420 s no ramo do encerramento** (`P-E0014-22`) · **valor multi-token em duas mensagens** (`P-E0014-23`, falha para o lado seguro).
- **A agregação do `acionamento.dado_faltou`** é de uma SPEC futura, por instrução do card.

## 8. 📋 Caixa do Founder

1. **Implantar** depois do merge (EasyPanel constrói a `main`).
2. **Canário**: (a) UMA mensagem dela na conversa com a URA → nada ao grupo e, 15 s depois, o robô segue; (b) DUAS em 15 s → o robô sai, em silêncio; (c) uma tela pede um dado que só está na conversa com o segurado → o robô responde sozinho; (d) a URA fecha com pergunta no ar e o segurado responde depois → o dado entra na ficha e ele **não** é perguntado de novo.
3. **Decisão de produto** em `P-E0014-19`: a resposta tardia deve virar um re-acionamento automático (risco: dois prestadores) ou uma linha à pessoa que já tem o caso?
4. **Variáveis**: nenhuma nova obrigatória. `PAUSA_HUMANA_S` padrão **60→15** · `PAUSA_HUMANA_MAX_RENOVACOES` **removida** · `CEREBRO_ANTES_DO_SEGURADO` **nova**, padrão `1`.

## 9. Pendências e decisões

**Fechada:** `P-E0013-08` → `PENDENCIAS-FECHADAS.md`, com a prova e o que ficou por provar.
**Abertas novas:** `P-E0014-18` · `P-E0014-19` · `P-E0014-20` · `P-E0014-21` · `P-E0014-22` · `P-E0014-23`.

| D | decisão | opções e nota | por quê |
|---|---|---|---|
| D1 | `PAUSA_HUMANA_MAX_RENOVACOES` **sai**; `abrir_ou_renovar_pausa` vira `uma_fala_da_atendente` | apagar **92** × virar 0 **58** | — |
| D2 | AGENTE / EU CUIDO **ficam**, como atalho opcional | manter **88** × apagar **70** | — |
| D3 | `estado/motivo_antes_de_eu_cuido` → `_antes_do_humano` | renomear **90** × manter **45** | — |
| D4 | o `reason` de máquina continua `segurado_nao_respondeu`; o texto humano entra no dossiê | rótulo no dossiê **90** × `reason` novo **40** | — |
| D5 | "há uma pessoa" = `humano_falou_em`/`fronteira_em`, não `state` | sinal do hub **95** × estado **20** | 📊 o motor promove a `human_phase` qualquer tela sem âncora de URA |
| D6 | a resposta tardia com o caso já entregue é **guardada** | guardar **85** × reabrir **35** | — |
| D7 | a resposta tardia numa URA **reaberta** vai para o SLOT, não à tela | `no_slot` **92** × mandar à URA **35** | a conversa nova está noutra tela: mandar o valor lá é responder a pergunta errada (juiz, B3) |
| D8 | a resposta tardia numa URA reaberta que ESTÁ na tela do slot é `levada` | condicionar à tela **92** × `no_slot` sempre **40** | senão ninguém responde a tela, a URA fecha por inatividade e o retry único já foi queimado (confirmação, D1) |

## 10. Telemetria (§11) — o gerente preenche

```
relógio · turnos · contexto · US$ · rodadas ..  <gerente>   · agentes além do executor: nenhum
achados por mecanismo .........................  builder 2 · juiz 3 blockers + 5 pendências · confirmação 1 blocker + 3
nota ........................................... <gerente> · juiz 58/100 · confirmação 80/100
```

## 11. Entrega

⛔ **Sem push** — instrução do gerente. Branch `feat/acabamento-001-3-001-4`, a partir de `origin/main` (`259a489`).

## 12. Handoff

Verde: T1, T2 e T3 com **24** mutações (13 construção + 9 conserto + 2 confirmação) e a régua de rota com linha de controle; os 3 blockers do juiz, o D1 da confirmação e as 4 pendências baratas consertados na mesma branch. Resta: a bateria inteira e o push. O que não foi feito está em §7 com número de pendência.
