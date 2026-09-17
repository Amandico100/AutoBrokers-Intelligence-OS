# ACABAMENTO 001.3 / 001.4 — a atendente não aprende palavra, o "um instante" só com pessoa, e o isolamento provado

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `259a489`

```
OUTCOME ..............  (T1) 1 fala da atendente = o robô espera 15 s e segue; 2 falas em 15 s = ele
                        sai do acionamento, em silêncio. Nenhuma palavra a decorar, nenhum aviso.
                        (T2) "um instante" só com PESSOA da seguradora; antes de perguntar ao
                        segurado o Cérebro tenta com o que já existe, com prova de origem; o que
                        faltou vira rastro; ninguém fica no vácuo e a resposta tardia não se perde.
                        (T3) o isolamento da 001.3 provado com dois tenants REAIS (P-E0013-08).
RISCO ................  8  (alcance 3 segurado · reversibilidade 3 mensagem à seguradora · frequência 2)
SUPERFÍCIE ...........  1  (um comportamento, em lugares listados)
PISO APLICADO ........  §3.2 "qualquer coisa que ENVIE mensagem" → CRÍTICO, independente da conta
NÍVEL ................  CRÍTICO · executor/builder Opus 5 xhigh · juiz Fable 5.1 (o gerente convoca)
UNIDADES .............  T1 · T2 · T3 — UMA fatia, nesta ordem, um commit por unidade
COESÃO ...............  T1 e T2 tocam `insurer_dispatch_service` · `dispatch_router` ·
                        `dispatch_watchdog` · `webhook` → um dono só (§3.4)
PARALELISMO REAL .....  nenhum — escrita de um só; investigador read-only: não
TIME .................  builder (esta sessão) · juiz fresco pelo gerente · escalação: confirmação
                        §6.1 se o juiz achar blocker em código que ENVIA
REFERÊNCIA ...........  interna `backend/tests/test_a_atendente_na_ura_cala_o_robo.py` ·
                        `test_o_humano_da_seguradora_e_atendido.py` · o G7 de dois tenants ·
                        `backend/scripts/medir_rota.py --com-espelho`
GATES ................  os dois guardas migrados (§9.3) + os PARES novos + o guarda novo de dois
                        tenants + mutação vermelha por regra + `medir_rota --comparar-com` +
                        py_compile + os testes vizinhos que importam esses módulos
O ELO ................  "a atendente perde tempo PORQUE tem de aprender AGENTE/EU CUIDO" — 📊 medi B
                        (o produto mandava um aviso pedindo as duas palavras: `aviso_da_pausa_humana`,
                        único chamador `_depois_da_pausa`), medi que B CHEGA em A (o aviso saía pela
                        porta única a CADA pausa aberta, `TIPO_PAUSA_HUMANA` isento da própria guarda),
                        e o conserto tira a necessidade: 📊 0 envios na abertura e na assunção.
FAIXA DE RELÓGIO .....  declarada 💭 90–120 min · real ≈ 150 min · tetos: turnos ≤ 250 (usados ~95) ·
                        contexto ≤ 400 k
```

**Produto:** AutoBrokers Intelligence OS · **SPEC:** acabamento das EXTRA-001.3 / 001.4 (prompt do gerente) ·
**Branch:** `feat/acabamento-001-3-001-4` ·
**Preflight** 📊 17/09/2026: `HEAD..origin/main` = **0** · `origin/main..HEAD` = **0** · HEAD = `259a489` ·
árvore limpa (dois arquivos soltos, ignorados por instrução) · **Builder:** Opus 5 `xhigh` (sessão nova).

## 1. BLOCO 0 — as premissas que mudariam o desenho

| # | o prompt afirma | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | os leitores de `pausa_humana` / `humano_assumiu` | `pausa_humana`: motor, roteador, grupo, Vigia. `humano_assumiu`: motor `:491`, roteador `:2893/:3023/:3040/:3776`, Vigia `:123`. ⚠️ `claims.humano_assumiu` (painel) é **outro fato** e não foi tocado | `grep -rn "pausa_humana\|humano_assumiu"` | nenhum leitor de fora |
| 2 | quem chama `perguntar_ao_segurado` e o holding do Vigia | **1** chamador (`dispatch_router:3457`, o gatilho D3); holding do Vigia em `_segurar_ou_desistir`, chamado de `dispatch_watchdog:888` | `grep -rn "perguntar_ao_segurado\|HOLDING_A_SEGURADORA"` | dois pontos de envio, os dois consertados |
| 3 | o Cérebro é consultado no estado `ura` para slot faltante? | **NÃO.** `human_reply_provider` só com `state == "human_phase"` (`:3472`, `:3592`); `_adaptive_reply` só pelo Sentinela após 30 s. O slot faltante caía **direto** na pergunta ao segurado | `grep -n "human_reply_provider\|_adaptive_reply"` | a chamada do T2 é **nova** e é **UMA** |
| 4 | como o guarda lê os dois tenants | o molde é `scripts/regua_motor.py` (`tem_banco()`/`supabase()`). 📊 banco alcançável: **5** corretoras; `company_internal_numbers` com **0** linhas | `python -c "import regua_motor as M; M.supabase()…"` | ids reais; a linha de X vem de dublê, e isso está escrito |
| 5 | 🔴 (achado do builder) `state == "human_phase"` prova que há uma pessoa? | **NÃO.** A última linha de `handle_insurer_message` ("Sem âncora de URA") promove **qualquer** tela sem âncora — e a tela que pede um dado fora da ficha é uma delas: 📊 `state` depois de `PEDE` = `human_phase` com `falta=telefone_contato` | script de 12 linhas chamando `handle_insurer_message` sobre a tela do corpus | o critério de "há pessoa" virou `humano_falou_em` / `fronteira_em` |
| 6 | 📊 contagem dos guardas de referência | o card dizia 44 e 45; medido: **50** e **57** asserções na base | `python tests/<arquivo>.py` | o meu número vence (PACOTE-BUILDER §1) |

## 2. As unidades entregues, por fatia

| unidade | arquivos | gate (comando) | saída real | commit |
|---|---|---|---|---|
| **T1** · 1 fala espera 15 s, 2 falas assumem, nada sai | `insurer_dispatch_service.py` · `dispatch_router.py` · `dispatch_watchdog.py` · `test_a_atendente_na_ura_cala_o_robo.py` | `python tests/test_a_atendente_na_ura_cala_o_robo.py` | **57 verdes · 0 vermelhas** (era 50) · exit 0 | `6a74c20` |
| **T2** · holding só com pessoa · Cérebro antes do segurado · rastro · ninguém no vácuo | `dispatch_router.py` · `dispatch_watchdog.py` · `test_o_humano_da_seguradora_e_atendido.py` | `python tests/test_o_humano_da_seguradora_e_atendido.py` | **84 verdes · 0 vermelhas** (era 57) · exit 0 | `10b2304` |
| **T3** · isolamento com dois tenants reais | `test_os_numeros_da_casa_nao_atravessam_corretoras.py` (novo) · `PENDENCIAS.md` · `PENDENCIAS-FECHADAS.md` | `python tests/test_os_numeros_da_casa_nao_atravessam_corretoras.py` | **19 verdes · 0 vermelhas** · exit 0 | (este commit) |

**Regressão dirigida** — `medir_rota.py --todas --com-espelho --comparar-com docs/canon/reports/LINHA-DE-BASE-DE-ROTAS.json` (base commit `acb6814`): **exit 0**, `OK nenhuma rota perdeu respondidas (R3 satisfeita)` · `OK nenhum passo responde sem confirmacao`. 📊 A saída é **byte a byte idêntica** à medida ANTES da primeira edição (`diff` vazio) — a linha de controle desta regressão.

**Vizinhos** (todos exit 0): `a_anotacao_da_atendente` · `a_atendente_fala_e_o_robo_cala` · `ninguem_fala_com_o_segurado_sem_o_agente_ligado` · `o_grupo_so_fala_de_quem_precisa` (33) · `o_numero_da_casa_nao_e_cliente` (20) · `o_travamento_vira_evidencia` · `o_sinistro_deixa_rastro` (**249 ok · 0 falhas**) · `a_maquina_de_lavar_vai_ate_o_fim` (**112**). `py_compile` verde nos quatro módulos.

**As mutações — cada regra nova fica VERMELHA** (restauradas por cópia, nunca `git checkout`; árvore conferida no fim):

| # | mutação | ficou vermelha em |
|---|---|---|
| M1 | `PAUSA_HUMANA_S` volta a 60 | `a janela é de 15 s` |
| M2 | a 2ª fala RENOVA em vez de assumir | `(b) 2 falas em 15 s → needs_human/HUMANO_ASSUMIU` + o rastro |
| M3 | o aviso ao grupo é reintroduzido | **5** asserções, entre elas `(b) EM SILÊNCIO: 0 envios` e `NENHUM ponto do produto manda um aviso de pausa ao grupo` |
| M4 | ⚠️ `needs_human` sai de `_TERMINAL_STATES` | **ficou VERDE** — mutação equivalente para esta forma de sessão. Substituída por → |
| M4b | o Vigia ignora `humano_assumiu` (`_preservar_a_atendente`) | `ela ASSUMIU enquanto o Cérebro pensava: o Sentinela NÃO envia` — asserção **acrescentada por causa da M4** |
| M5 | o holding sai com robô (roteador) | `` `robô`: 0 'um instante' à seguradora `` |
| M6 | o Cérebro não é consultado | `o Cérebro achou: ZERO perguntas ao segurado` + 2 |
| M7 | a prova de origem desligada | `valor que não está em fonte nenhuma é RECUSADO` + a função pura |
| M8 | o rastro `acionamento.dado_faltou` some | `o rastro diz origem_da_resposta=cerebro` |
| M9 | a espera vencida não é guardada | **4** asserções da resposta tardia |
| M10 | o Vigia manda holding com robô | `` o Vigia em `robô`: esperou_calado — 0 envio `` |
| M11 | o filtro `company_id` some da leitura de `company_internal_numbers` | `TODA consulta leva company_id no filtro do CÓDIGO` |
| M12 | a guarda ignora os números da casa | `em X, o aviso CALA` |

## 3. Migrations — nenhuma

Nada de SQL. `company_internal_numbers` (`20260916_01`) foi **só lida** (SELECT de contagem).

## 4-6. Juiz fresco · conserto único · bateria — do gerente

O builder não julga o próprio trabalho (§4). Aqui rodaram: os 3 guardas do escopo, 8 vizinhos, a regressão de rota com linha de controle e as 13 mutações.

## 7. O que ficou fora, e o gatilho que o faz voltar

- **A reabertura automática da URA depois da resposta tardia** — `P-E0014-19`. 📊 o corredor só reentra quando **alguém da seguradora fala**; não há caminho nosso para reabrir uma URA fechada, e `pode_retomar` existe para impedir um segundo acionamento (dois prestadores). A resposta tardia é **guardada** (ficha + `work_events`, `retomada=guardada`). **Não inventei a reabertura.**
- **A apólice não viaja na sessão** — `P-E0014-18`.
- **G4 do T3 é prova estrutural** (a rota é TypeScript, sem harness aqui), com controle que a mostra vermelha e o limite escrito no teste.
- **A agregação do `acionamento.dado_faltou`** é de uma SPEC futura, por instrução do card.

## 8. 📋 Caixa do Founder

1. **Implantar** depois do merge (EasyPanel constrói a `main`).
2. **Canário**: (a) a atendente digita UMA mensagem na conversa com a URA → nada chega ao grupo e, 15 s depois, o robô segue; (b) ela digita DUAS em 15 s → o robô some do acionamento, em silêncio; (c) uma tela pede um dado que só está na conversa com o segurado → o robô responde sozinho, sem incomodá-lo.
3. **Decisão de produto** em `P-E0014-19`: a resposta tardia deve virar um re-acionamento automático (risco: dois prestadores) ou uma linha à pessoa que já tem o caso?
4. **Variáveis de ambiente** — nenhuma nova obrigatória. Alteradas/novas, todas opcionais: `PAUSA_HUMANA_S` (**padrão mudou de 60 → 15**; `0` desliga a janela e a assunção) · `PAUSA_HUMANA_MAX_RENOVACOES` **removida** (não existe mais renovação) · `CEREBRO_ANTES_DO_SEGURADO` (**nova**, padrão `1`; `0` volta ao comportamento anterior).

## 9. Pendências e decisões

**Fechada:** `P-E0013-08` → `PENDENCIAS-FECHADAS.md`, com a prova e o que ficou por provar.
**Abertas novas:** `P-E0014-18` (apólice na sessão) · `P-E0014-19` (retomada da resposta tardia).

| D | decisão | opções e nota | por quê |
|---|---|---|---|
| D1 | `PAUSA_HUMANA_MAX_RENOVACOES` **sai**, e `abrir_ou_renovar_pausa` vira `uma_fala_da_atendente` | apagar **92** × virar 0 com significado novo **58** | CLAUDE.md §12.1: o nome mentia sobre o que guardava. "Renovação" não existe mais; manter a constante ensinaria a regra velha a todo leitor seguinte |
| D2 | AGENTE / EU CUIDO **ficam**, como atalho opcional | manter e re-documentar **88** × apagar e migrar **70** | custam uma comparação de string, já têm guarda, e apagar removeria a única saída de quem já as usa. A trava virou: nenhum texto, comentário ou docstring do produto diz que a atendente precisa delas — e um guarda AST prova que nada manda `TIPO_PAUSA_HUMANA` ao grupo |
| D3 | `estado/motivo_antes_de_eu_cuido` → `_antes_do_humano` | renomear **90** × manter **45** | o campo passou a ser escrito pela 2ª fala, não pela palavra: o nome mentia (§12.1) |
| D4 | o `reason` de máquina continua `segurado_nao_respondeu`; o texto humano entra no **dossiê**, com o rótulo | rótulo no dossiê **90** × `reason` novo **40** | `segurado_nao_respondeu` está em `REENTRAVEIS`: trocar a chave mataria a reentrada da seguradora — um defeito, não um acabamento |
| D5 | "há uma pessoa" = `humano_falou_em` / `fronteira_em`, não `state == "human_phase"` | sinal do hub **95** × estado **20** | 📊 medido: o motor promove a `human_phase` qualquer tela sem âncora de URA — o card pedia o estado, e o estado estava errado |
| D6 | a resposta tardia com o caso já entregue é **guardada**, não levada | guardar + pendência **85** × reabrir por conta própria **35** | reabrir é abrir um segundo acionamento; `pode_retomar` existe para impedir isso |

## 10. Telemetria (§11) — o gerente preenche

```
relógio total · por fase ①–⑥ ........
turnos · contexto de pico ...........
ctx-tokens · saída ..................
US$ API-equivalente .................
agentes além do executor ............  nenhum
achados por mecanismo ...............  builder: 2 (o `state` que não prova pessoa · a M4 equivalente)
rodadas da bateria ..................
nota da execução ....................
```

## 11. Entrega

⛔ **Sem push** — instrução do gerente. Commits na branch `feat/acabamento-001-3-001-4`, a partir de `origin/main` (`259a489`).

## 12. Handoff

Verde: T1, T2 e T3, com mutação por regra e a regressão de rota com linha de controle. Resta: o juiz fresco (Fable 5.1), o conserto único, a bateria inteira e o push. Nada ficou pela metade; o que não foi feito está em §7 com número de pendência.
