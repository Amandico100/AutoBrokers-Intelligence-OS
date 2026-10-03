# SPEC-126 — O atendimento quase sem erro

> Relatório de execução · 02–03/10/2026 · rito AAA v13 · 🔴 CRÍTICO · branch `spec/126-o-atendimento-quase-sem-erro`
> base `fbdecec` (= origin/main) · último código `8f63452` + o conserto da bateria · commit final: §12 (ENTREGA)
> SPEC `specs-propostas/SPEC-126-o-atendimento-quase-sem-erro.md` · medições `reports/SPEC-126-LINHA-DE-BASE.md` (U0) e
> `reports/SPEC-126-DEPOIS.md` (G1) · sessão `8fef6a21` (a SPEC-127 corre no mesmo chat).

## 0. O EXECUTION CARD (definitivo, ajustado ao que aconteceu)

```
OUTCOME ........  ENTREGUE COM RESSALVAS: o "ok" claro aciona e o não-ok não aciona (regex E classificador); o parente
                  aciona sem ver dado da apólice; cancelar depois de acionar = pessoa na hora com dossiê; apresentação
                  1×; DEDUZIR só religa calibrado (0/40 religadas). 📊 Luna 77,8 → 88,9 % (meta 90: NÃO); críticos Luna
                  12/12; Sol críticos 11/12 (o 12º é vermelho falso da régua); bancada do ok 179 casos, 0/294 falso ok
RISCO ..........  8 (segurado 3 · acionamento irreversível 3 · todo atendimento 2)
SUPERFÍCIE .....  3 (portão, prompt, cancelamento, parente/abuso, diário, DEDUZIR, Model Router)
PISO APLICADO ..  §3.2 — envia mensagem, decide acionar, avisa grupo, migration → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · conserto Y ‖ X · confirmação ·
                  consertos 2–4 · escalação · conserto 5 · bateria
O FIO ..........  "pode deixar" depois de "Posso acionar?" → webhook → buffer → modelo → insurer_dispatch →
                  prova_da_confirmacao (regex E classificador, fail-closed) → NADA acionado (nasceu vermelho)
PARALELISMO ....  U0 ‖ U6 ‖ U4, depois U2a (arquivos disjuntos) → U3 → U1 → U3-B ‖ U2-B → U5 → U2-C (HUB)
UNIDADES .......  BLOCO 0 · U0 · U1 · U2a · U2-B · U2-C · U3 · U3-B · U4 · U5 · U6 · G1 · Y ‖ X · consertos 2–5 · bateria
COESÃO .........  "um portão, uma régua do assunto, uma porta de cancelamento à pessoa"
TIME ...........  investigador · 11 builders · juiz ‖ red team · 2 builders de conserto · confirmação · 4 consertos ·
                  escalação · triagem da bateria · lente do dado no G1 · atualizador
REFERÊNCIA .....  interna: test_spec125_juiz_final.py, test_spec125_endurecimento.py, SPEC-125-DEPOIS.md, a U0 ·
                  externa: SPEC §7 (τ-bench, Decagon, Anthropic evals, arXiv 2203.11171 e 2207.05221)
GATES ..........  G1–G9 (§4)
O ELO ..........  C13: chamou pessoa (A) ← confirm_first sem linha pronta (B) → U1 deu a linha → C13 Sol 0/2 → 2/2
                  (B→A medido); C2/C4/C11: régua com falso (P-125-08) → transcrição lida → régua consertada
FAIXA DE RELÓGIO  💭 1–1,5 dia (SPEC) · 📊 02/10 18:49Z → último código 03/10 04:36Z ≈ 9 h 47 min + bateria (1:53:47)
nota da execução  88/100 (§11)
MIGRATIONS .....  20261002_10 (versão 20261002202210) · 20261002_11 (versão 20261002202302) — APLICADAS (§6)
ORÇAMENTO ......  📊 ledger `service_type='bancada'` desde 02/10 18:50Z: OpenAI US$ 4,2796 (teto 4,50, 126+127) ·
                  Anthropic US$ 0,0002
```
① Lentes: lente do dado no G1 (transcrições lidas). ② Auditoria: juiz ‖ red team cegos, confirmação, escalação (§5).
③ Valor marginal: 📊 0 de 4 agentes de atendimento ativos → a bancada N3 (segurado simulado) é a régua.

## 1. O QUE MUDOU (em linguagem clara)

- **U0 (`eb56b09`)** — a linha de base no modelo de produção (GPT-6.1 Sol, prompt v2) ANTES de mexer: 📊 13/17 = 76,5 %,
  críticos 5/6 nas duas tentativas, o C13 (acionamento confirmado) falhou 2/2.
- **U2a (`abd0221` gabarito ANTES · `1024f7c` · `e18a1da`)** — o **classificador da confirmação** é um papel do Model Router
  (`confirmacao`: gpt-6-luna medium, reserva claude-sonnet-5-5 low) com saída `{ok · nao · outra_coisa}`, fail-closed.
- **U2-B (`8d603df`)** — o portão do acionamento passa a exigir **a regex E o classificador**: "pode deixar", "prefiro
  amanhã", "não, pode acionar o outro", "só se…" e o "sim" que troca o serviço não acionam; "fechou", "vai lá", "👍" acionam.
  Botões de resposta rápida (`send_buttons`) no protocolo do provedor, **desligados** (nenhum canal provado em aparelho).
- **U4 (`076bb53`)** — **cancelar depois de acionar vai à pessoa na hora**, com dossiê (K3 amplo, `_SEMPRE_DE_GENTE`);
  "cancelei" sem ferramenta é reescrito. 📊 O pós-acionamento era INVISÍVEL em produção: 0 de 1.174 fichas tinham a chave
  que o código lia — consertado (a ficha real tem `acionamento.protocolo`).
- **U3 / U3-B (`9019783`, `50334f6`)** — **o parente aciona** sem o titular junto e sem ver dado da apólice (inclusive no
  turno seguinte); **aviso de abuso**: a 3ª apólice distinta no mesmo celular em 5 dias avisa o grupo da corretora dona
  (rastro HMAC em `tool_invocations`, sem tabela nova); CPF completo à URA e ao portal, mascarado só ao segurado (teste);
  "sou eu sim" libera o CPF; 🔴 a **senha da assistência residencial** ia a todo segurado — agora só no playbook dela.
- **U1 (`f6f087d`)** — a linha pronta do resumo no `confirm_first` (o modelo copia, não inventa); acostamento = orientar a
  segurança + guincho (C13); exemplos no v2; protocolo exige dígito; a régua sem os falsos da P-125-08.
- **U5 (`a803215`)** — apresentação **uma vez por assunto**, por intenção ("Aqui é a Clara, da Corretora X" conta); o diário
  registra `deduziu` e `nao_chamou_pessoa` + 3 sinais (corrigiu, repetiu, pediu pessoa); conhecimento com escopo da ficha.
- **U2-C (`f44526c`)** — a bancada de conversa mede o classificador DENTRO do teto; o conftest falha alto se um teste chamar o
  papel pago.
- **U6 (`16d9a68`)** — o DEDUZIR só religa por seguradora com prova gravada em `cerebro_modos` (n ≥ 10, ≥ 90 %, Wilson ≥ 70 %,
  controle "tecla 1" batido; CHECK no banco); homônimo Curitiba/Curitibanos recusado em código. 📊 0 de 40 religadas: a porta
  tem 32 casos, **≤ 5 por seguradora** (`scratchpad/casos_cal.txt`), abaixo do n = 10 → rodada paga não feita (D-126-E).
- **Consertos** — Y (`a5b1dac`, +38 casos `c05630d`): a rede lê todas as falas (negação no fim "manda não", adiamento "daqui 1
  hora", retirada, rajada); o mesmo sim não aciona 2× (`already_dispatched` pelo estado); `acionamento.enviado_em` gravado no
  envio. X (`8ddba57`): "Pronto, cancelado!"/"desmarquei" reescritos; "esquece/deixa pra lá/dispensa" = K3 → pessoa; parente
  sem "dele" (motorista, genro, "o carro do meu pai") é terceiro. 2 (`67742fb`): o acionamento de um assunto ANTERIOR não trava
  o caso novo do mesmo telefone. 3 (`1f6f1a7`) e 4 (`14eb941`): fase, pós-acionamento e prompt olham o ASSUNTO atual
  (`ficha_do_assunto`). 5 (`8f63452`): "esquece... o guincho" volta a K3; "o guincho foi cancelado pela seguradora" sem
  ferramenta é reescrito. Bateria: as 5 regressões da triagem (§3).

## 2. COMMITS
📊 `git rev-list --count fbdecec..8f63452` (03/10) → **21 commits** + o conserto da bateria: 9 de unidade com código (`1024f7c` U2a · `16d9a68` U6 ·
`076bb53` U4 · `9019783` U3 · `f6f087d` U1 · `50334f6` U3-B · `8d603df` U2-B · `a803215` U5 · `f44526c` U2-C) · 4 de medição/gabarito (`abd0221`, `eb56b09`, `e18a1da`, `a8665b9`) · 2 da
bancada do ok (`c05630d`, `44e0f1a`) · 6 consertos (`a5b1dac`, `8ddba57`, `67742fb`, `1f6f1a7`, `14eb941`, `8f63452`).
📊 `git diff --shortstat fbdecec..HEAD` → 83 arquivos, +66.240 / −295 (a maior parte são os JSON mascarados da bancada);
31 arquivos `test_spec126_*`. Nada fora de `backend/` além dos dois relatórios.

## 3. BATERIA
📊 Suíte inteira **UMA rodada** em `8ddba57` (worktree `C:\wt126bat`), `pytest tests -q -p no:cacheprovider`:
```
52 failed, 4635 passed, 2 skipped, 33 xfailed, 1 xpassed in 1:53:47
```
Triagem NOMINAL contra `BATERIA-LINHA-DE-BASE.txt` (28 ids, SPEC-125): **28 iguais · 24 fora da base**. As 24 rodadas
isoladas no HEAD `14eb941` e na base `fbdecec` (worktrees com `node_modules` por junção; saídas `isolados-wt126tri.txt` /
`isolados-wt126base.txt`):
| veredito | quantos | ids |
|---|---|---|
| **REGRESSÃO da 126** | **5** | `test_spec116_reserva_p0::…reserva_do_mapa` (o papel `confirmacao` nasceu com reserva; o mapa do teste não sabia) · guarda `test_o_atendimento_soa_humano` (U1 cortou 2 desvios e 2 formas do handoff do v2) · guarda `test_o_contrato_alcanca_o_portao` (`slots_deduzidos` é metacampo) · guarda `test_o_vocabulario_viaja_na_imagem` (`bancada_confirmacao.py` `parents[3]`) · guarda `test_todo_import_aponta_para_algo_que_existe` (o varredor não lê `A, B = …`) |
| ordem, pré-existente (já na bateria da 125) | 9 | `test_spec125_conserto_y::test_y4_…` e os 8 de `test_spec125_s5_uma_resposta_por_rajada` |
| ambiente (`node_modules` ausente no worktree) | 6 | `test_o_nome_do_agente_nao_confunde`, `test_spec123_diario_fio`, guardas da tabela de rotas, do diagnóstico e do número da casa, `test_um_clique_liga_os_corredores` |
| ordem/carga | 3 | guarda do corredor da Porto e a árvore limpa (mutação de outro guarda), `test_uma_corretora_nao_trava_a_outra` (p95 sob carga) |
| pré-existente, igual na base | 1 | guarda `test_a_mesma_verdade_em_duas_vozes` (base real fora do alcance) |
As 5 regressões foram tratadas em `6880e62` (o teste muda com a lição migrada, §9.3, ou o produto é consertado —
nunca afrouxado): 4 verdes; o guarda `test_o_vocabulario_viaja_na_imagem` ficou verde na LÓGICA mas estoura o teto de 120 s
do runner — 📊 a linha de controle com o guarda da base `fbdecec` mediu 151,2 s / 107,5 s × HEAD 133,3 s / 108,3 s (carga da
máquina, não regressão; P-126-25). 📊 Depois do conserto: `test_spec126_*` + `test_spec125_*` + `test_spec116_reserva_p0` →
**1771 passed**. ⚠️ O conserto da bateria **não passou por juiz fresco** nem por nova rodada inteira. `BATERIA-LINHA-DE-BASE.txt`
**não** foi regravada. Antes da bateria: juiz `test_spec126_*` **766 passed, 8 skipped** · confirmação **491 passed** ·
escalação **301 passed** (comandos nos laudos). `npm run test:rotas-montam`/`next start`: **não se aplica** (📊 nenhum arquivo
fora de `backend/` mudou além dos relatórios, `git diff --name-only fbdecec..HEAD`).

## 4. GATES
| gate | estado |
|---|---|
| **G1** U0 antes; final ≥ U0 em todo crítico; metas | 🟡 **parcial.** U0 publicada (`eb56b09`) antes da 1ª mudança no atendimento (U4/U1). 📊 Final (`SPEC-126-DEPOIS.md`, `scripts/bancada.py --resumo-conversa`): **Luna 32/36 = 88,9 %** (U0 da Luna rejulgada 77,8 %) — **meta 90 % NÃO, faltou 1 tentativa**; críticos Luna **12/12**. **Sol** críticos: C13 **0/2 → 2/2**, C10 t1 F = vermelho FALSO da régua ("informe o endereço" ao 193; juiz LLM 5/5), C16 t2 rodado depois do conserto → PASS (`scratchpad/c16_sol_pos_conserto.json`) → **11/12**. Sol ≥ 95 % no conjunto da U0: **NÃO medido** (os não-críticos não rodaram — teto). Mutação do G1 (final com o prompt e o portão da U0): **não rodada** (orçamento). 📊 0 acionamento sem o sim em 14 · 0 dado a terceiro (C16 3/3) · 0 apresentação repetida em 47 conversas |
| **G2** 0 falso ok | ✅ 📊 bancada do ok **179 casos** (141 + 38), gabarito commitado ANTES de cada rodada (`abd0221` 17:28 → `e18a1da` 17:39; `c05630d` → `44e0f1a`); Luna medium k=3: **combinado 0/294 falso ok, 97,9 % ok aceito**, US$ 0,048. "pode deixar" pelo motor → nada acionado. Mutações: juiz M1 "só a regex" → 1 failed/27 passed; red team M1 portão sem classificador → 6 failed, M2 `_arun` sem prova → 27 failed, M3 ok sem trecho → 3 failed (controle 93 passed) |
| **G3** parente | ✅ "sou o filho dele…" aciona pelo motor sem dado; "me passa a apólice do meu pai" negado; conserto X fechou o parente sem "dele" (juiz B2, red team B4). Mutação "voltar a exigir o titular" declarada em `test_spec126_u3_d1_parente_aciona.py`; parente sem "dele": mutação → casos do juiz/RT vermelhos |
| **G4** abuso | ✅ 3 apólices distintas em 5 dias → 1 aviso ao grupo DA corretora; 2 → nenhum; o próprio titular conta 1 (D-126-C); não bloqueia. Mutação (juiz M2) sem `company_id` na contagem → **1 failed** |
| **G5** CPF completo à URA/portal | ✅ `test_spec126_u3_d3_cpf_completo.py`; mutação "mascarar os argumentos no `tool_node`" → (ii)–(iv) vermelhos |
| **G6** cancelamento | ✅ K3 → pessoa com dossiê; "cancelar a vistoria" continua `C`; "cancelei" reescrito. Mutação (juiz M3) fora do `_SEMPRE_DE_GENTE` → **1 failed**. Escalação: BE-1/BE-2 do conserto 2 consertados no 5 (sondas determinísticas viraram guardas) |
| **G7** DEDUZIR | ✅ mecanismo: 📊 `cerebro_modos` 40 linhas, **0** `deduzir_calibrado=true`, CHECK `ck_cerebro_modos_deduzir_so_com_prova` vivo (SELECT 03/10). Mutação M1 limiar 0 → **2 failed** (`scratchpad/mutacao_u6.txt`; restaurado por cópia → 4 passed). ⚠️ nenhuma seguradora religada: n ≤ 5 |
| **G8** travas da 125 | ✅ juiz: `test_spec123/124/125_*` (43 arquivos) **1135 passed**; `test_a_maquina_de_lavar_vai_ate_o_fim` 112 asserções verdes; `test_golden_do_eletricista` + bancada 47 passed; v1 sha256 `2713eee75b689c7b` igual; testes alterados migram a lição (ex.: "acho que sim" virou teste que exige NÃO). ⚠️ `test_golden_do_eletricista` tem 3 checks vermelhos pré-existentes (P-126-23) |
| **G9** custo + bateria | ✅ custo: 📊 `select model_name, count(*), round(sum(total_cost_usd)::numeric,6) from token_usage_logs where service_type='bancada' and created_at >= '2026-10-02T18:50:00Z' group by 1` (03/10 ~05:10Z) → `gpt-6-luna 2202 ch 0.787807` · `gpt-6.1-sol 140 ch 3.491823` · `claude-opus-5-5 1 ch 0.000168` = **OpenAI US$ 4,2796 de 4,50** (126 + 127 juntas). 🟡 bateria: 5 regressões, consertadas sem nova rodada (§3) |

## 5. JULGAMENTO — 4 rodadas
- **Juiz (Opus 5.5 fresco, `f44526c`): REPROVA, 80** — B1 a rede dizia SIM para "manda não", "daqui 1 hora", "pode mandar, já
  resolvi" (0 casos assim na bancada); B2 "o carro do meu pai quebrou" + CPF solto não era terceiro. 3 números 📊 reproduzidos
  por caminho próprio (U0, ledger, bancada 0/222).
- **Red team (Opus 5.5, cego): QUEBREI, 60** — B1 "Pronto, cancelado!" saía intacto; B2 "esquece o guincho" ganhava a segunda
  chance; B3 a mesma confirmação acionava 2×; B4 motorista/genro/caseiro recebiam a apólice.
- **Conserto Y ‖ X → confirmação: FAIL, 74** — os 6 blockers fechados; **BN-1 novo**: o `enviado_em` de um caso de 30 dias
  atrás travava o caso novo do mesmo telefone ("já está com a seguradora" e nada saía).
- **Consertos 2, 3, 4 → escalação: FAIL, 76** — BN-1 fechado; **BE-1** "esquece... o guincho" (pontuação) voltava à segunda
  chance; **BE-2** "o guincho foi cancelado pela seguradora" deixou de ser reescrito (9 de 9 frases). Estimou ≈ 86 com o conserto 5.
- **Conserto 5 (`8f63452`)** — os dois, com as sondas da escalação como guardas determinísticos. ⚠️ **DECLARADO: os consertos 5
  e da bateria não passaram por juiz fresco** (a escalação dispensou nova rodada por serem sondas determinísticas).

## 6. MIGRATIONS
📊 `select version, name from supabase_migrations.schema_migrations where version in ('20261002202210','20261002202302')` (03/10):
| arquivo | versão | o que faz |
|---|---|---|
| `20261002_10_spec126_u6_deduzir_calibrado.sql` | `20261002202210` | `cerebro_modos.deduzir_calibrado` + `calibracao` + função `cerebro_modos_prova_vale` + CHECK `ck_cerebro_modos_deduzir_so_com_prova` (sem prova não liga) |
| `20261002_11_spec126_papel_confirmacao.sql` | `20261002202302` | papel `confirmacao` em `llm_papeis` (gpt-6-luna medium · reserva claude-sonnet-5-5 low) |
APPLY / VERIFY / ROLLBACK escritos no cabeçalho das duas ANTES de aplicar (o VERIFY da `_10` é um bloco DO que desfaz tudo; o
ROLLBACK da `_11` é `delete … where papel='confirmacao'` + regerar o snapshot). 📊 VERIFY 03/10 (SELECT): papel `confirmacao` 1
linha · `cerebro_modos` 40 `on`, 0 calibradas · 4 agentes `attendance`, 0 ativos, `v2`. ⚠️ `backend/supabase/migrations/MANIFEST.md`
**não tem** as linhas das duas (📊 `Select-String '20261002_1[01]'` → 0): fica para o gerente (P-126-24).

## 7. A DRENAGEM
| P | estado |
|---|---|
| P-125-01 | ✅ FECHADA — os críticos C10/C13/C15/C16 medidos no Sol na U0 e na final; o que falta (não-críticos) vira P-126-02 |
| P-125-02 | ✅ FECHADA — C13 Sol 0/2 → 2/2, Luna 2/2 |
| P-125-03 | 🟡 CONTINUA — a R9 K1/K2/L em código (U4); Luna C8 t1 ainda chama pessoa sem oferecer (→ P-126-01) |
| P-125-04 | ✅ FECHADA — apresentação por intenção (U5); 📊 0 repetida em 47 conversas |
| P-125-06 | ✅ FECHADA — 4 momentos + 3 sinais; `deduziu` depende de o modelo preencher `slots_deduzidos` (P-126-04) |
| P-125-08 | ✅ FECHADA — régua consertada (U1); o resto (C10 instrução a terceiro, R2 pessoa aceita) vira P-126-03 |
| P-123-01 | 🟡 CONTINUA — o mecanismo está pronto (U6); falta n ≥ 10 por seguradora + a rodada paga (P-126-06) |
| P-124-14 | ✅ FECHADA em código — homônimo Curitiba/Curitibanos recusado (U6); outros chamadores → P-126-08 |

## 8. O QUE FICOU FORA
P-126-01…24 em `PENDENCIAS.md`: Luna 88,9 % < 90 % (C8, C2) · Sol nos não-críticos · a régua do C10 · auto-checagem não
implementada (📊 0 de 6 falhas medidas eram do tipo que ela pega) · botões em aparelho real · corpus do DEDUZIR · placa ausente
na ficha em produção · `rotulo_de` por prefixo · CPF em `work_steps.output_summary` e telefone em `tool_invocations.trace_id` ·
os furos do aviso de abuso · reserva do classificador nunca medida · 2 processos enfileiram 2 · "cancela" com o pedido só
enfileirado · vigias sem o corte do assunto · espera antiga torna o caso pós · resíduos da rede e do fiscal · janela de N dias
da plataforma · instruções duplicadas no resumo · o `portal_action` sem o portão (→ SPEC-127 P1) · golden do eletricista ·
consertos 5/bateria sem juiz · MANIFEST. O que a SPEC já tirava: cancelar sozinho (D4) e baratear (D6). Decisões D-126-A…J.

## 9. A CAIXA DO FOUNDER
`TAREFAS-DO-FOUNDER.md`, bloco S126 e T-91 a T-98: Implantar `smith-api` → `smith-worker` → `smith-web` (migrations já
aplicadas; nenhuma variável nova) · conferir o papel `confirmacao` e o DEDUZIR (SQL pronto) · no aparelho real: "pode deixar"
não aciona, "pode mandar" aciona, "esquece o guincho" depois de acionar chama a pessoa, o parente aciona sem ouvir a apólice ·
o grupo recebe o aviso de abuso · botões (quando houver o corpo do `/send/button`) · decidir o orçamento da calibração.
**Desfazer:** o portão vive no código; o desfazer é o deploy anterior. Apagar o papel `confirmacao` NÃO desfaz: o
classificador cai em `outra_coisa` e **nada mais aciona** (falha fechada).

## 10. RISCOS REMANESCENTES (FATO · INFERÊNCIA)
- **FATO:** a meta da Luna ficou em 88,9 % (falta 1 tentativa) e o Sol fora dos críticos não tem número depois da SPEC.
- **FATO:** o classificador custa uma chamada por acionamento (📊 14 chamadas = 14 acionamentos, US$ 0,001167); a reserva
  (Sonnet 5.5) nunca foi medida — se o Luna cair, quem decide o "ok" é um modelo sem bancada.
- **FATO:** o rastro do abuso usa o telefone da sessão como está (sem normalizar o 55) e, com o Redis fora, o aviso pode repetir.
- **FATO:** os consertos 5 e da bateria têm guarda determinístico, mas nenhum juiz fresco os leu.
- **INFERÊNCIA:** com o português falado real, a rede (regex) ainda terá frases novas em que só o classificador segura; o lado
  seguro é UMA confirmação a mais, não um acionamento a mais (as duas camadas têm de concordar).
- **INFERÊNCIA:** o "cancelado pela seguradora" com sujeito que não é o serviço ("o guincho do seu SEGURO") ainda passa.

## 11. NOTA E TELEMETRIA
**NOTA DO GERENTE: 88/100.** Critério: as 5 decisões do Founder (D1–D5) estão em CÓDIGO com teste pelo motor e mutação
vermelha; 0 falso ok na bancada de 179 casos; críticos 12/12 na Luna e 11/12 no Sol (o 12º é vermelho falso da régua). Perde
por: Luna 88,9 % < 90 %; Sol nos não-críticos sem medida; consertos 5 e da bateria sem juiz fresco; 4 rodadas de julgamento
até fechar. Juiz 80 · red team 60 → confirmação 74 → escalação 76 (≈ 86 estimada com o conserto 5).

📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (03/10 ~05:10Z, sessão `8fef6a21`, 126 e 127 juntas):
```
EXECUTOR (sessao principal)   02/10 18:49   612 min  turnos 136  pico 458k  ctx 40.0M  saida 151k  US$ 27.50  opus-5-5
agentes SPEC-126 (US$): BLOCO 0 11,26 · U0 9,60 · U4 17,80 · U6 23,86 · U2-A 9,93 · U3 19,16 · U1 33,28 · U2-B 23,36 ·
  U3-B 21,40 · U5 19,04 · U2-C 9,38 · juiz 12,66 · red team 4,92 · G1 6,45 · X 7,45 · Y 14,98 · confirmação 2,00 ·
  conserto 2 6,07 · 3 3,49 · 4 2,53 · escalação 3,77 · 5 3,22 · triagem 4,80 · bateria 1,96 · atualizador 4,45 (em curso)
agentes SPEC-127 (até aqui): BLOCO 0 10,09 · P1 24,31 · P2 18,99 · P4+P8/P5 23,15 · juiz 5,65 · red team 6,37
TOTAL  agentes alem do executor: 31 . turnos 2841 . ctx 661.0M . saida 0.38M . US$ 392.88
```
Derivado: agentes da SPEC-126 ≈ **US$ 276,82** (25 agentes) · da 127 até aqui ≈ US$ 88,56 · executor (126 + 127) US$ 27,50.
APIs do produto (bancada): OpenAI US$ 4,2796 · Anthropic US$ 0,0002 (G9). Relógio: 📊 02/10 18:49Z → último código 03/10
04:36Z ≈ 9 h 47 min, com a 127 intercalada; + bateria 1:53:47. Achados por mecanismo: BLOCO 0 (o pós-acionamento invisível,
0/1.174) · U0 (C13 Sol 0/2) · U3-B (a senha da assistência residencial a todo segurado) · juiz 2 blockers · red team 4 (2 do
mecanismo da 125: B3 idempotência, B2 K3) · confirmação 1 (BN-1, criado pelo conserto Y) · escalação 2 (BE-1/BE-2, criados
pelo conserto 2) · bateria: 5 regressões, 1 rodada.

## 12. ENTREGA
```
git fetch origin ; git rev-list --count HEAD..origin/main   → (o gerente cola)
git rev-list --count origin/main..HEAD                      → (o gerente cola)
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
(o gerente cola a saída do push)
```

**Nenhum motor paralelo foi criado.** O classificador é um papel do Model Router (`llm_papeis`), chamado pelo MESMO portão da
125 (`prova_da_confirmacao`); o cancelamento usa a R9 (`pos_acionamento.classificar_turno`) e a porta única do handoff; o rastro
do abuso usa o gravador único `tool_invocations` (sem tabela nova); o aviso usa `o_grupo_so_o_que_importa.enviar_ao_grupo`; a
régua do assunto é uma só (`attendance_ficha.ficha_do_assunto`); a calibração do DEDUZIR é coluna de `cerebro_modos`; a
bancada do ok é um nível da `evals/bancada.py` da SPEC-116; o diário é o `diario_de_decisoes` da SPEC-123.
