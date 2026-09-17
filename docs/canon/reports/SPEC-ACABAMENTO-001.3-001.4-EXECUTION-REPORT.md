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
                        (`aviso_da_pausa_humana`, chamador único `_depois_da_pausa`), medi que B CHEGA
                        em A (saía pela porta única a CADA pausa, isento da própria guarda), e o
                        conserto tira a necessidade: 📊 0 envios na abertura e na assunção.
FAIXA DE RELÓGIO .....  declarada 💭 90–120 min · real ≈ 150 min + 60 min de conserto · tetos: turnos ≤ 250 (usados ~95) ·
                        contexto ≤ 400 k
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** acabamento das EXTRA-001.3 / 001.4 (prompt do gerente) ·
**Branch:** `feat/acabamento-001-3-001-4` ·
**Preflight** 📊 17/09/2026: `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `259a489` ·
árvore limpa (dois arquivos soltos, ignorados por instrução) · **Builder:** Opus 5 `xhigh` (sessão nova).

## 1. BLOCO 0 — as premissas que mudariam o desenho

| # | o prompt afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | os leitores de `pausa_humana` / `humano_assumiu` | motor, roteador, grupo, Vigia (`humano_assumiu` em `:491`, `:2893/:3023/:3040/:3776`, `:123`). ⚠️ `claims.humano_assumiu` (painel) é outro fato | `grep -rn` | nenhum leitor de fora |
| 2 | quem chama `perguntar_ao_segurado` e o holding do Vigia | **1** chamador (`dispatch_router:3457`); holding em `_segurar_ou_desistir`, de `dispatch_watchdog:888` | `grep -rn` | dois pontos de envio, os dois consertados |
| 3 | o Cérebro é consultado no estado `ura`? | **NÃO.** `human_reply_provider` só em `human_phase` (`:3472`, `:3592`); `_adaptive_reply` só pelo Sentinela após 30 s | `grep -n` | a chamada do T2 é **nova** e é **UMA** |
| 4 | como o guarda lê os dois tenants | molde `scripts/regua_motor.py`. 📊 **5** corretoras; `company_internal_numbers` com **0** linhas | `python -c "import regua_motor…"` | ids reais; a linha de X vem de dublê (P-E0014-21) |
| 5 | 🔴 (achado do builder) `state == "human_phase"` prova que há pessoa? | **NÃO.** A última linha de `handle_insurer_message` promove qualquer tela sem âncora de URA: 📊 `state` depois de `PEDE` = `human_phase` | script chamando `handle_insurer_message` sobre a tela do corpus | o critério virou `humano_falou_em`/`fronteira_em` |
| 6 | 📊 contagem dos guardas de referência | o card dizia 44 e 45; medido: **50** e **57** asserções na base | `python tests/<arquivo>.py` | o meu número vence (PACOTE-BUILDER §1) |

## 2. As unidades entregues, por fatia

| unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|
| **T1** · 1 fala espera 15 s, 2 falas assumem, nada sai | motor · roteador · Vigia · guarda | `python tests/test_a_atendente_na_ura_cala_o_robo.py` | **57 verdes · 0** (era 50) · exit 0 | `6a74c20` |
| **T2** · holding só com pessoa · Cérebro antes do segurado · rastro · ninguém no vácuo | roteador · Vigia · guarda | `python tests/test_o_humano_da_seguradora_e_atendido.py` | **84 verdes · 0** (era 57; **108** após o conserto) · exit 0 | `10b2304` |
| **T3** · isolamento com dois tenants reais | guarda novo · `PENDENCIAS*` | `python tests/test_os_numeros_da_casa_nao_atravessam_corretoras.py` | **19 verdes · 0** · exit 0 | `f039291` |

**Regressão dirigida** — `medir_rota.py --todas --com-espelho --comparar-com docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json` (base `acb6814`): **exit 0**, "OK nenhuma rota perdeu respondidas (R3 satisfeita)" · "OK nenhum passo responde sem confirmacao". 📊 Saída **byte a byte idêntica** à medida ANTES da 1ª edição e à de depois do conserto (`diff` vazio) — a linha de controle.

**Vizinhos** (todos exit 0): `a_anotacao_da_atendente` · `a_atendente_fala_e_o_robo_cala` · `ninguem_fala_com_o_segurado_sem_o_agente_ligado` · `o_grupo_so_fala_de_quem_precisa` (33) · `o_numero_da_casa_nao_e_cliente` (20) · `o_travamento_vira_evidencia` · `o_sinistro_deixa_rastro` (**249 ok · 0**) · `a_maquina_de_lavar_vai_ate_o_fim` (**112**). `py_compile` verde nos cinco módulos.

**As mutações da construção — cada regra nova fica VERMELHA** (restauradas por cópia, nunca `git checkout`; árvore conferida no fim): **M1** janela de 60 s · **M2** a 2ª fala renova em vez de assumir · **M3** o aviso ao grupo volta (5 asserções) · **M4b** o Vigia ignora `humano_assumiu` · **M5** holding com robô · **M6** Cérebro não consultado · **M7** prova de origem desligada · **M8** rastro `dado_faltou` some · **M9** espera vencida não guardada · **M10** o Vigia fala com robô · **M11** o filtro `company_id` some · **M12** a guarda ignora os números da casa.

⚠️ **M4** (`needs_human` fora de `_TERMINAL_STATES`) ficou **VERDE** — mutação equivalente para esta forma de sessão. Foi ela que fez nascer a asserção do Sentinela, e a **M4b** passou a pegá-la.

## 3. Migrations — nenhuma

Nada de SQL. `company_internal_numbers` (`20260916_01`) foi **só lida** (SELECT de contagem).

## 4. O juiz fresco (Fable 5.1, sobre `f039291`) — VEREDITO **FAIL** · nota **58/100**

T1 e T3 passaram; os três blockers e as cinco pendências são todos do **T2**.

| # | achado do juiz | teste do produto | medição do juiz | classe | conserto |
|---|---|---|---|---|---|
| **B1** | `o_cerebro_ja_sabe` espera até 20 s e depois responde/grava **sem reler o Redis** | **SIM** — o robô fala por cima da atendente **e** apaga a assunção | atendente digita 2× durante o Cérebro → a sessão gravada tem `humano_assumiu=True`, mas a gravação stale deixa `state=ura, humano_assumiu=False` | BLOCKER | `_a_atendente_entrou` + `_gravar_a_sessao_dela` **antes** de qualquer envio ou gravação |
| **B2** | `valor_tem_origem` usava `substring` com `len ≥ 2` | **SIM** — valor inventado chega à seguradora com "prova" de origem | `"10"` em `endereco_numero: 100`, `"20"/"21"` em `2021`, `"35"` em `350`, `"999"` no telefone, `"casa as"` colando dois campos | BLOCKER | sequência de **tokens** dentro de **UMA linha**; CPF/telefone/documento/e-mail saem das fontes |
| **B3** | prazo do segurado 60×3 = **180 s** contra os ≈ **103 s** da Allianz: o encerramento fazia `pop("esperando_do_segurado")` e a retomada reabria sem o dado | **SIM** — a resposta se perde e o segurado recebe a mesma pergunta duas vezes | resposta 50 s depois do fechamento → `responder_pergunta_do_acionamento` = `False`; nenhum handoff | BLOCKER | o encerramento move a espera para `espera_vencida`; a retomada carrega `perguntado_ao_segurado` + a espera `de_acionamento_anterior`; a resposta tardia entra no **SLOT** (`retomada="no_slot"`) |
| P1 | busca `user_phone` numa forma só | SIM (é a causa da "pergunta óbvia") | 📊 ~100 conversas com LID de 15 dígitos e 66 com 13 ficavam invisíveis ao Cérebro | → **consertada** | `in_("user_phone", _variantes_do_telefone(...))` |
| P3 | a mesma fala entregue 2× pelo canal virava assunção silenciosa | SIM | a Evolution **não** deduplica por `messageId` (só a Z-API, `webhook.py:1938`) | → **consertada** | `note_manual_outbound(message_id=…)` + Redis `SET NX`, TTL 15 min; Redis mudo não bloqueia |
| P5 | `_preservar_a_atendente` não copiava `motivo_antes_do_humano` | SIM (AGENTE devolvia a sessão travada sem o motivo) | só `estado_…` estava na lista | → **consertada** | o campo entrou na lista |
| P2 | `fronteira_em` é escrito pelo **anúncio do robô**, então o holding sai para a fila | baixo | — | **registrada**, não consertada | `P-E0014-20` |
| P4 | o T3 prova com ids reais mas dublê de banco (`company_internal_numbers` com 0 linhas) | não | — | **registrada** (o teste já declara o limite) | `P-E0014-21` |

## 5. O conserto único — tudo junto, uma passada

Arquivos: `dispatch_router.py` (B1·B2·B3·P1·P3) · `insurer_dispatch_service.py` (B3) · `dispatch_watchdog.py` (P5) · `webhook.py` (P3, passa o `message_id`) · o guarda do T2 (**84 → 108** asserções). A docstring de `perguntar_ao_segurado`, que afirmava o contrário do código sobre a inatividade da URA, foi corrigida.

**Gates rerodados** — **57/0** · **108/0** · **19/0** · `o_grupo_so_fala_de_quem_precisa` **33/0** · `o_sinistro_deixa_rastro` **249 ok · 0** · `a_maquina_de_lavar` **112/0** · `py_compile` 5 módulos · `medir_rota --comparar-com` **exit 0** com `diff` vazio.

**As mutações do conserto — todas VERMELHAS:** **M13** a releitura depois do Cérebro some (B1) · **M14** `substring` sobre o texto achatado (B2) · **M15** CPF/telefone voltam a ser fonte (B2) · **M16** a espera não sobrevive ao encerramento (B3, 5 asserções) · **M17** a retomada não carrega `perguntado_ao_segurado`/espera (B3, 6) · **M18** a resposta tardia vai para a tela errada (B3) · **M19** uma forma só do número (P1) · **M20** sem dedupe da fala reentregue (P3) · **M21** `motivo_antes_do_humano` não preservado (P5).

## 6. A bateria — o gerente roda

Aqui rodaram: os 3 guardas do escopo, 8 vizinhos, a regressão de rota com linha de controle e **22** mutações (13 da construção + 9 do conserto).

## 7. O que ficou fora, e o gatilho que o faz voltar

- **A reabertura automática da URA pelo nosso lado** — `P-E0014-19`. 📊 o corredor só reentra quando alguém da seguradora fala; `pode_retomar` existe para impedir um segundo acionamento (dois prestadores). Com o caso já entregue a uma pessoa, a resposta tardia é **guardada**. **Não inventei a reabertura.**
- **A apólice não viaja na sessão** — `P-E0014-18`.
- **G4 do T3 é prova estrutural** (rota TypeScript, sem harness aqui), com controle vermelho e o limite escrito no teste — `P-E0014-21`.
- **A agregação do `acionamento.dado_faltou`** é de uma SPEC futura, por instrução do card.

## 8. 📋 Caixa do Founder

1. **Implantar** depois do merge (EasyPanel constrói a `main`).
2. **Canário**: (a) UMA mensagem dela na conversa com a URA → nada ao grupo e, 15 s depois, o robô segue; (b) DUAS em 15 s → o robô sai, em silêncio; (c) uma tela pede um dado que só está na conversa com o segurado → o robô responde sozinho; (d) a URA fecha com pergunta no ar e o segurado responde depois → o dado entra na ficha e ele **não** é perguntado de novo.
3. **Decisão de produto** em `P-E0014-19`: a resposta tardia deve virar um re-acionamento automático (risco: dois prestadores) ou uma linha à pessoa que já tem o caso?
4. **Variáveis de ambiente** — nenhuma nova obrigatória. Alteradas/novas, todas opcionais: `PAUSA_HUMANA_S` (**padrão mudou de 60 → 15**; `0` desliga a janela e a assunção) · `PAUSA_HUMANA_MAX_RENOVACOES` **removida** (não existe mais renovação) · `CEREBRO_ANTES_DO_SEGURADO` (**nova**, padrão `1`; `0` volta ao comportamento anterior).

## 9. Pendências e decisões

**Fechada:** `P-E0013-08` → `PENDENCIAS-FECHADAS.md`, com a prova e o que ficou por provar.
**Abertas novas:** `P-E0014-18` (apólice na sessão) · `P-E0014-19` (retomada da resposta tardia).

| D | decisão | opções e nota | por quê |
|---|---|---|---|
| D1 | `PAUSA_HUMANA_MAX_RENOVACOES` **sai**; `abrir_ou_renovar_pausa` vira `uma_fala_da_atendente` | apagar **92** × virar 0 **58** | §12.1: o nome mentia. "Renovação" não existe mais |
| D2 | AGENTE / EU CUIDO **ficam**, como atalho opcional | manter **88** × apagar **70** | custam uma comparação de string e já têm guarda; a trava virou: nenhum texto do produto as pede, e um guarda AST prova que nada manda `TIPO_PAUSA_HUMANA` ao grupo |
| D3 | `estado/motivo_antes_de_eu_cuido` → `_antes_do_humano` | renomear **90** × manter **45** | quem escreve agora é a 2ª fala, não a palavra (§12.1) |
| D4 | o `reason` de máquina continua `segurado_nao_respondeu`; o texto humano entra no dossiê | rótulo no dossiê **90** × `reason` novo **40** | a chave está em `REENTRAVEIS`: trocá-la mataria a reentrada da seguradora |
| D5 | "há uma pessoa" = `humano_falou_em`/`fronteira_em`, não `state` | sinal do hub **95** × estado **20** | 📊 o motor promove a `human_phase` qualquer tela sem âncora de URA |
| D6 | a resposta tardia com o caso já entregue é **guardada** | guardar **85** × reabrir **35** | reabrir é abrir um segundo acionamento (`pode_retomar`) |
| D7 | a resposta tardia numa URA **reaberta** vai para o SLOT, não à tela | `no_slot` **92** × mandar à URA **35** | a conversa nova está noutra tela: mandar o valor lá é responder a pergunta errada (juiz, B3) |

## 10. Telemetria (§11) — o gerente preenche

```
relógio · turnos · contexto · US$ · rodadas ...  <gerente>
agentes além do executor ....................  nenhum
achados por mecanismo .......................  builder 2 (o `state` que não prova pessoa · a M4 equivalente) · juiz 3 blockers + 5 pendências
nota da execução .............................  <gerente> · nota do juiz 58/100 (pré-conserto)
```

## 11. Entrega

⛔ **Sem push** — instrução do gerente. Branch `feat/acabamento-001-3-001-4`, a partir de `origin/main` (`259a489`).

## 12. Handoff

Verde: T1, T2 e T3 com mutação por regra (22 no total) e a regressão de rota com linha de controle; os 3 blockers e as 3 pendências baratas do juiz consertados na mesma branch. Resta: confirmação §6.1 (o juiz achou blocker em código que ENVIA — o gatilho disparou), a bateria inteira e o push. O que não foi feito está em §7 com número de pendência.
