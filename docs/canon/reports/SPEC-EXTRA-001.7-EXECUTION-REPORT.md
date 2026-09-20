# SPEC-EXTRA-001.7 · O piloto medido — RELATÓRIO DE EXECUÇÃO

> 20/09/2026 · segunda SPEC sob o **núcleo do AAA v13 em teste** (D-PROTO-10). Base `3ae6af8`.
> Branch `feat/extra-001-7-o-piloto-medido`. Proposta: `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §0, bloco 001.7, §12.

## 0.0 🔴 EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `3ae6af8`
```
OUTCOME ..............  o Founder roda UM comando e sabe se dá para ligar o agente hoje (com o motivo de cada trava); e roda
                        OUTRO e recebe, por dia × corretora, os números do piloto e a nota 0–100 de cada dimensão do §0 do
                        diagnóstico — ou "NÃO AVALIADA" quando o dado não existe. As notas deixam de ser palpite
RISCO ................  3   (a corretora/Founder lê e decide 2 · nada fica depois de desfazer 0 · todo dia de piloto 1)
SUPERFÍCIE ...........  2   (uma peça nova: a medição + régua; e a extensão do checklist)
PISO APLICADO ........  nenhum: nada envia, nenhuma migration, só SELECT. O /health ganha 1 sinal de CONTAGEM (sem número)
NÍVEL ................  PADRÃO · builders Opus 5 xhigh · juiz generalista Fable 5.1 ‖ red team Fable 5.1
UNIDADES .............  3 em 2 fatias paralelas: ① A checklist de ligar ‖ ② B medição diária + C régua por dimensão
COESÃO ...............  B e C juntas: a régua consome o contrato que a medição define. A é disjunta (outro arquivo)
PARALELISMO REAL .....  fatias ① e ② ao mesmo tempo (arquivos disjuntos, sem commit); juiz ‖ red team; investigador read-only: sim (1)
TIME .................  gerente Fable · 1 investigador Opus · 2 builders Opus · juiz + red team Fable · confirmação por gatilho (blocker material)
REFERÊNCIA ...........  interna: `backend/app/services/os_modelos_do_grupo.py` (`contagens_do_dia`/`eficiencia_do_dia`: o motor
                        que o produto já usa às 19h, com "sem escritor = não medido") e `backend/scripts/regua_0971.py` (régua que
                        IMPORTA o motor) · externa: a da proposta (§7.3: na execução não se repesquisa)
GATES ................  G1 checklist REPROVA com trava fechada e PASSA com todas abertas (par) · G2 medição sobre o banco real,
                        dia × corretora, 2 rodadas idênticas · G3 zero PII na saída · G4 isolamento com as DUAS corretoras reais ·
                        G5 dimensão sem dado sai "NÃO AVALIADA" (mutação) · G6 menos dado NUNCA melhora a nota
O ELO ................  "a nota da dimensão é X PORQUE o banco tem Y": o teste do fio afirma a NOTA FINAL a partir das linhas do
                        banco (dublê gerado do schema real), atravessando o motor importado — não a função da régua solta
FAIXA DE RELÓGIO .....  150 min (teto 1,5× = 225) · início 20/09 07:44 UTC · tetos: 24 agentes · 2 simultâneos
```

### O FIO
```
ENTRA  banco de produção: messages(role, payload.origem/direcao/wa_message_ids) · conversations(company_id, status,
       resolvido_em, resolucao_motivo) · work_events(grupo.enviado/calado, vigia.*, handoff.*) · agent_activities
       (handoff entregue/falhou; silêncios) · platform_sends(kind) · work_runs(runtime_kind='acionamento')
  →    backend/scripts/medir_o_piloto.py:ler_o_dia        SELECT paginado, filtro company_id, dia no fuso da corretora
  →    MOTOR importado: os_modelos_do_grupo.contagens_do_dia · eficiencia_do_dia · o_fim_do_atendimento.classe_do_silencio ·
       e_origem_humana · human_handoff.TITULO_HANDOFF_* · platform_outbound.fuso_da_corretora
  →    medir_o_piloto.py:medir_o_dia                      o número por métrica × dia × corretora (só contagens)
  →    medir_o_piloto.py:regua_por_dimensao               nota 0–100 com o critério ao lado, ou NÃO AVALIADA
SAI    JSON + markdown em linguagem de gente → relatório em docs/canon/reports/ e a aba "O piloto" do artefato do Founder

CHECKLIST  /health (main.py:_sinais_do_codigo) + banco → conferir_o_que_esta_no_ar.py --ligar (motores: resolver_destino_de_suporte ·
           numeros_da_casa · CANAL_FORA_DO_AR do porteiro) → PODE LIGAR / NÃO PODE, motivo por trava · exit 0/1/2
```

**Preflight** 📊 20/09/2026 07:40 UTC: `HEAD..origin/main` = 0 · `origin/main..HEAD` = 0 · HEAD = `3ae6af8` · árvore com 1 teste modificado e
5 arquivos soltos do Founder (intocados) · **Gerente:** Fable 5.1 · **Builders:** Opus 5 · **Juízes:** Fable 5.1 · **Início / fim:** 20/09 07:44 → 10:15 UTC

## 1. BLOCO 0 — as premissas que mudaram o desenho (📊 20/09/2026)
| # | premissa | medido 📊 | comando | consequência |
|---|---|---|---|---|
| 1 | "não há medidor do dia" | **há**: `contagens_do_dia` (resumo das 19h); e `payload.origem` (agente × pessoa) só existe desde 14/09 | `grep -rn "def .*eficiencia" app` · `webhook.py:1778` | a medição IMPORTA o motor (CLAUDE.md §5); dias < 14/09 saem "NÃO MENSURÁVEL" |
| 2 | o banco tem o dado do piloto | `grupo.*` = 7 eventos em setembro; agentes ligados = **0** nas duas | `select … from work_events … group by` · `agents where agent_role='attendance'` | quase tudo sai NÃO AVALIADA hoje: opção **A 90** × B (pular para a 001.10) 45 |
| 3 | "apólice certa em 1 rodada" é mensurável (e silêncios/handoffs moram em `agent_activities`, não em `work_events`; a classe do silêncio vem do MOTOR em memória) | **SEM ESCRITOR** (só um booleano sobrescrito) | investigador: `grep apolice_confirmada`, 0 `work_events apolice.*` | NÃO AVALIADA + P-E0017-03; adicionar o escritor agora **55** × pendência **80** (toca o atendimento: piso CRÍTICO, fora da faixa) |
| 6 | já existe checklist de ligar | há o porteiro `pode_ligar_o_atendimento`, **fail-open sem sinal** | `porteiro_do_agente.py:83-85,103-105` | o checklist reusa os motores e a constante dele, mas o que não confere REPROVA (P-E0017-06) |
| 7 | destinos de alerta ativos | **desativados nas duas desde 10/09** | `select is_active from human_support_destinations` | achado de produto nº 1 da SPEC: P-E0017-01 (🧑) |

## 2. As unidades entregues (📊 medido em 20/09/2026)
| fatia | unidade | arquivos | gate (comando) | saída real | commits |
|---|---|---|---|---|---|
| ① | A · checklist de ligar | `scripts/conferir_o_que_esta_no_ar.py` (estendido: `--ligar`, `--modo piloto\|canario`, `--corretora`) · `app/main.py` (+2 contagens no `/health`) · `tests/test_o_checklist_de_ligar.py` · captura REAL do `/health` | `python tests/test_o_checklist_de_ligar.py` | **76 verdes · 0 vermelhas**; modo antigo 16 · 0; corrida real: **NÃO PODE LIGAR — 3 travas fechadas e 1 não conferida**, exit 1 | `09f79a3` `aad7d74` |
| ② | B · medição diária + C · régua | `scripts/medir_o_piloto.py` · `scripts/gerar_recorte_do_piloto.py` · `tests/test_o_piloto_e_medido.py` · `tests/corpus/piloto/recorte.json` (gerado do banco, anonimizado) | `python tests/test_o_piloto_e_medido.py` | **66 verdes · 0 vermelhas**; 2 rodadas 08–19/09: `sha256` idêntico; PII: 0 em md/json/recorte | `ff97b43` `fc5a6e5` `6da6e09` |

**Gates:** G1 ✅ par por trava (7 travas + allowlist nos 2 modos) · G2 ✅ banco real, dia × corretora, hash igual em intervalo fechado (12 dias em 📊 1 min 07 s) · G3 ✅ dublê
envenenado (nome, telefone, CPF, placa) não vaza; varredura 0 · G4 ✅ Resulta e AutoFleet reais: junto = separado; 14 linhas da B não mexem na A;
sem `company_id` → vermelho · G5 ✅ as duas direções por mutação · G6 ✅ linha a linha, e **falha de leitura em cada uma das 8 tabelas: nenhuma nota sobe**.
**Lente do dado** (SELECT independente × medidor, 8 células por 3 autores diferentes): AutoFleet 17/09 **64=64**, 18/09 **53=53** · Resulta 17/09 **25=25**, 18/09 **38=38** ·
gerente: AutoFleet 15–16/09 **68/65**, Resulta **27/42** — todas batem.
**O que a medição diz hoje** (📊 08–19/09): 0 conversas com fala do agente; só com pessoa — Resulta 157, AutoFleet 306 (14–18/09); as 11 dimensões NÃO AVALIADA,
salvo **chat · velocidade da Resulta = 0** (29 perguntas, p90 do tempo do modelo 40,5 s; 💭 palpite 60). É o resultado honesto: o agente está desligado.

## 3–4. Migrations: nenhuma (só SELECT). O julgamento — UMA rodada paralela + confirmação (trava: `rodada 2/2`)
Builders (teste do fio): 1 achado — o `/health` diz `healthy` com Redis caído. ⚖️ Juiz Fable **FAIL 62** (📊 5 min): B1 · B2 · B3/B6, achou o B1 por lente do dado.
🗡️ Red team Fable **QUEBREI 58** (📊 16 min): os mesmos + **B4 e B5 exclusivos** + 5 mutações que o teste do fio não via. 🏁 Confirmação Fable **86** (📊 8 min): 1 resíduo (exclusivo).

| # | achado (todos mudam número, nota ou decisão que chega ao Founder: BLOCKER pelo §2) | medição | conserto |
|---|---|---|---|
| B1 | conversa escolhida por `updated_at`: o dia D perdia o que foi tocado em D+1 | publicado **3** × real **53** (AutoFleet 18/09) | o dia sai da data da MENSAGEM; recorte regerado sem o viés; 4 células fixadas |
| B2 | "velocidade do chat" misturava o agente do WhatsApp | AutoFleet 35 linhas = 13 do chat + 22 do atendimento → 16 virou NÃO AVALIADA | filtro `agent_role='core'`; critério diz que é o tempo do MODELO |
| B3 | p90 do "pior dia" com n=1 decidia o período | 25×1 s + 1×31 s: 100 → 0 | p90 do período, método escrito |
| B4 | leitura que FALHA virava zero, e a nota SUBIA | timeout em `work_runs`: aciona 50 → 100 | LEU / PAROU NO TETO / NÃO CONSEGUI LER; dimensão dependente NÃO AVALIADA; célula e prosa "NÃO LIDO" |
| B5 | checklist dizia PODE LIGAR com a allowlist de entrada ativa | ativa(1) e `None` → exit 0 | trava própria + `--modo`; ausente = não conferida |
| B6 | contagem do chat sobrescrevia em vez de somar | "(1)" × real 38 | soma, com asserção de 2 dias |

Causa-raiz do B1: **o dublê nasceu com o mesmo filtro do código** (§9.4). Lição para o v13: outcome-número pede a lente do dado DENTRO do gate do builder.

## 5. O conserto único
Dois builders retomados (contexto quente), em paralelo; depois o resíduo. Rerodados: os 2 testes do fio, G2–G4, 8 de 9 mutações vermelhas (a 9ª é inerte: o corte do dia passou a ser em memória). Pendências: P-E0017-03…08.

## 6. A bateria — 📊 1 rodada inteira, em 2º plano, DEPOIS do conserto único
📊 20/09/2026, `cd backend && python -m pytest tests -q`, 1 rodada inteira: **35 failed · 1187 passed · 34 xfailed · 1 xpassed · 0 errors** em 2.897 s
(linha de base de 20/09, 001.5.2: 42 failed · 48 errors). Os dois testes novos passaram dentro dela. Triagem por DIFF: nenhuma das 35 cita
`conferir_o_que_esta_no_ar`, `medir_o_piloto`, `_sinais_do_codigo` nem os testes novos (`grep` no log = 0); dos arquivos que falharam, só
`test_todos_os_guardas_script_rodam` e `test_o_travamento_vira_evidencia` leem `main.py`/documentos — retriados dirigidos com a árvore parada (📊 41 testes, 62 s): 40 passam; `test_C3` falha contando `agente="cerebro"` em `dispatch_router.py` (5 × 2), arquivo que este diff não toca: pré-existente.
`test_o_protocolo_tem_policia` falhou DENTRO da bateria porque este relatório ainda estava só com o card; rerodado no fechamento: 📊 **77 ok, 0 falhas**.
`test_a_arvore_ficou_limpa_no_fim` = o resíduo sendo consertado e os documentos sendo escritos durante a rodada (desvio declarado, §10).
❓ Não há lista nominal da linha de base para provar, teste a teste, que as outras 31 são as mesmas de ontem (só a contagem: 35 ≤ 42) — P-E00152-06 continua.

## 7. O que ficou fora, e o gatilho que o faz voltar
Os 3 dias de piloto e o canário da 001.5.2 (🧑 P-E0017-09) · os escritores de 7 das 11 dimensões (P-E0017-03/04): voltam como SPEC pequena se o Founder quiser as notas por máquina (D-E0017-04) · "aciona" cruza coortes (`platform_sends` não guarda o `work_run`): limitação escrita na página, clamp visível.

## 8. 📋 Caixa do Founder
1. **Reativar os grupos de suporte** das duas corretoras (desativados desde 10/09) — P-E0017-01.
2. **Implantar** smith-api · smith-worker · smith-web; rodar `python scripts/conferir_o_que_esta_no_ar.py --ligar` até "PODE LIGAR".
3. O canário da 001.5.2 (apólice real por seguradora) e os **3 dias de piloto**, pelo roteiro P1–P4 em `SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md`.
4. Decidir os cortes do veredito do piloto (D-E0017-03) e se os escritores que faltam entram antes dos 3 dias (D-E0017-04).

## 9. Pendências e decisões
`P-E0017-01…09` em `PENDENCIAS.md`. Tocadas: P-PILOTO-06 **CONTINUA** (a medição diária existe; a rotina automática de fim de dia não) · P-PILOTO-10 **CONTINUA** (agora as duas corretoras estão sem destino ativo) · P-E00152-07 **CONTINUA** (canário). Decisões `D-E0017-01…04` em `FOUNDER-DECISIONS.md`.

## 10. Desvios declarados
- O conserto do RESÍDUO rodou com a bateria em andamento (nota 80 × esperar 45 min 60); os testes afetados foram retriados dirigidos com a árvore parada (§6).
- Fatias ① e ② em paralelo, contra o "sequencial" do v12 §5.2 — autorizado pelo prompt (v13 em teste). · `app/main.py` ganhou +38 linhas no `/health` (só contagem, sob `try`). · Sem `next start`: nada de frontend, `middleware` ou env foi tocado.

## 11. Telemetria (`medir_execucao_claude_code.py --sessao atual`)
```
relógio total ....................... 📊 07:44 → 10:15 UTC = 151 min (faixa 150 · teto 225) · bateria 48 min em 2º plano
turnos · contexto de pico ........... gerente 71+ turnos · pico 399 k · builder ② 125 turnos · pico 304 k · builder ① 72 · 189 k
ctx-tokens · saída .................. agentes 66,3 M · saída 0,16 M · gerente 16,5 M
US$ API-equivalente ................. investigador 5,08 · builder ① 6,27 · builder ② 16,56 · juiz 2,27 · red team 2,47 · confirmação 1,67 · gerente ≈ 12,4 → ≈ US$ 47
agentes além do executor ............ 6 de 24 (1 investigador · 2 builders · juiz · red team · confirmação)
achados por mecanismo ............... builders 1 · juiz 3 (0 exclusivos) · red team 6 (B4 e B5 EXCLUSIVOS) · confirmação 1 (EXCLUSIVO) · gerente 2 (contagem incoerente 1×38; bloco com 3/6) · canário: —
rodadas da bateria .................. 1 inteira · 0 parciais (só testes dirigidos)
nota da execução .................... 86/100 · juiz 62 → red team 58 → confirmação 86 (antes do resíduo fechado)
```
**Nota da execução: 86/100** — critério: o instrumento inteiro está entregue, provado sobre o banco real por 8 células contra SELECT independente, e **7 defeitos materiais morreram antes do push** (o pior publicaria 3 conversas onde houve 53). Perde pontos porque a 1ª versão chegou ao juiz com esse defeito (o dublê concordava com o código por construção), porque 3 das 6 notas do atendimento continuam sem fonte no produto (o piloto vai depender de uma folha de papel), porque a triagem da bateria é por contagem e não nominal, e porque o conserto do resíduo rodou com a bateria em andamento.

## 12. Entrega
```
__PUSH__
```
Implantar: smith-api → smith-worker → smith-web. Variáveis novas: nenhuma. Nenhum motor paralelo foi criado: o checklist ESTENDE `conferir_o_que_esta_no_ar.py` e reusa os motores do porteiro; a medição IMPORTA `contagens_do_dia`, `eficiencia_do_dia`, `classe_do_silencio` e `e_origem_humana`.
