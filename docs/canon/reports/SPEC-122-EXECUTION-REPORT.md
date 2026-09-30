# SPEC-122 — O agente pensa, com prova (+ o GPT-6.1 Sol sucede o Sol 6)

> Relatório de execução · 30/09/2026 · rito AAA v13 · branch `spec/122-o-agente-pensa-com-prova`
> commit inicial `2f1859d` · commit final: ver §8 · SPEC `specs-propostas/SPEC-122-o-agente-pensa-com-prova.md`
> Resultado da bancada: `reports/SPEC-122-BANCADA.md`

## 0. O EXECUTION CARD (definitivo, depois do BLOCO 0)

```
OUTCOME ........  o GPT-6.1 Sol sucede o Sol 6 no Model Router, com o MESMO esforço por papel; o cérebro da fase humana
                  do acionamento é MEDIDO pela 1ª vez numa bancada com casos reais e com CONTROLE do cérebro de produção;
                  a saída estruturada (responder · perguntar ao segurado · recusa · pessoa · silêncio) só onde a bancada
                  provar; o cérebro novo entra em MODO SOMBRA por corretora × seguradora × ramo (off → sombra; `on` recusado)
FAIXA DE RELÓGIO  💭 1 dia; 📊 ≈ 11 h de relógio (BLOCO 0 → push), inclusive 3 rodadas de bateria de ~1 h
nota da execução  86/100 (§9)
RISCO ..........  9  (ALCANCE seguradora e segurado 3 · REVERSIBILIDADE resposta enviada 3 · FREQUÊNCIA todo acionamento 3)
SUPERFÍCIE .....  2  (catálogo de modelos · cérebro da fase humana + sem_chute)
PISO APLICADO ..  §3.2 — o modelo passa a poder responder à seguradora; migration que altera dado → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto (2 partes) · confirmação
O FIO ..........  webhook.py:1099 _human_reply_provider → insurer_dispatch_service.build_human_phase_messages →
                  llm_factory.invocar_com_reserva("dispatch") → guard_human_phase_reply → dispatch_router (decide o destino)
                  · sem_chute: insurer_dispatch_service.sem_chute_ao_segurado → dispatch_router.perguntar_ao_segurado →
                    traduzir_resposta_do_segurado → resolver_tecla contra a tela ATUAL → URA (ou pessoa)
                  · sombra: dispatch_router (deepcopy da sessão, depois do envio) → acao_do_cerebro.agendar_sombra →
                    modo_do_cerebro (cerebro_modos) → só o primário → acao_do_cerebro.decidir → work_events cerebro.sombra
PARALELISMO ....  F0 (catálogo 6.1: migration, snapshot, docling, agent_council) ‖ F1 (bancada: evals/bancada.py,
                  scripts/bancada.py, corpus) → F2 (sem_chute: insurer_dispatch_service, dispatch_router) → F3 (sombra)
UNIDADES .......  4 fatias (F0 · F1 · F2+F3 num builder, arquivos cruzados) + conserto em 2 partes disjuntas (Z corpus e
                  medição · X sem_chute e sombra)
COESÃO .........  "o modelo só ganha autonomia onde a bancada provar; até lá ele decide ao lado, e o que vai à seguradora
                  não muda"
TIME ...........  investigador BLOCO 0 + pesquisador de modelos · 4 builders · juiz ‖ red team · confirmação · atualizador
REFERÊNCIA .....  interna: 📊 176 telas reais sem passo com resposta humana (grupo A) · 1.877 telas que o motor responde
                  (grupo B) · as armadilhas reais · a bancada da SPEC-116 · externa: Anthropic building-effective-agents,
                  Anthropic develop-tests, Fowler Dark Launching, página oficial do gpt-6.1-sol
ORÇAMENTO ......  teto do Founder US$ 2 POR PROVEDOR, lido do ledger (token_usage_logs service_type='bancada'), parando sozinho
GATES ..........  G1–G9, §4
O ELO ..........  "a camada sem_chute segura o grave que o modelo comete" — 📊 re-decisão das saídas BRUTAS gravadas, sem
                  chamar modelo: o grave sem_chute-hdi-074 vira abstenção correta (`proibicao=passo_sem_chute`), o resto
                  idêntico ao gravado (juiz, `juiz_redecide.py`)
```

## 1. O QUE MUDOU

### 1.1 O GPT-6.1 Sol sucede o Sol 6 (F0, `29b0b76`) — decisão do Founder
- 📊 `GET /v1/models/gpt-6.1-sol` (30/09) → 200, criado em 27/09, sem data de desligamento. Preço igual ao Sol 6
  (US$ 2 entrada / US$ 10 saída por milhão de tokens); a entrada em cache cai à metade (US$ 0,10 — multiplicador **0,05**
  no catálogo). ⚠️ O 6.1 **não aceita** o esforço `none`: 📊 HTTP 400 medido; a porta do catálogo recusa antes da rede.
- Migration `20260930_01`: `gpt-6.1-sol` APPROVED; `gpt-6-sol` **DEPRECATED** → 6.1 (não BLOCKED: a OpenAI não o
  desligou). 📊 8 linhas de `llm_papeis_historico` (juiz, SELECT 30/09): os **7 papéis primários** (atendimento high;
  chat_principal, juiz_eval, portal_decisao, subagente, visao, visao_documento medium) **e a reserva do dispatch** (high)
  trocados com o **mesmo esforço** em todas. O **Opus 5.5 continua primário do dispatch** e reserva de atendimento, chat e
  portal. Luna, Astra, Opus e Sonnet intactos. `docling-service` e `agent_council`: default 6.1 (o docling ainda não lê a
  rota — P-122-01).
- 📊 Smoke real pelo caminho do produto (atendimento com ferramenta em 2 turnos, chat, portal estruturado, visão e o
  **failover do dispatch para o 6.1**): **US$ 0,0073**, conferido no ledger. Guarda `test_o_sol_6_1_sucede_o_sol_6`:
  19 verdes, **7 mutações vermelhas** (esforço trocado, cache 0,10, `none` aceito, reserva de volta ao Sol 6…).

### 1.2 As novidades da OpenAI (DevDay 29/09) — só o 6.1 entrou
📊 Laudo do pesquisador (30/09, `GET /v1/models`, páginas oficiais reabertas, US$ 0,0047 de canário):

| novidade | veredito | por quê |
|---|---|---|
| **GPT-6.1 Sol** | **AGORA** — feito | mesmo preço, mesmo payload; a única quebra (`none`) já barrada pelo catálogo |
| Ultrafast | descartar agora | 📊 `gpt-6.1-sol-ultrafast` → 404; é *service tier*, só existe no Astra (6× o preço) |
| Agents API | **descartar** | seria um 2º runtime, executor e cofre de segredos (CLAUDE.md §5) |
| Computer Use | depois | as duas docs oficiais divergem sobre o 6.1; senha de portal num navegador de terceiro |
| Decisions API | não verificado | preview restrito; 📊 `/v1/decisions` → 404 |
| Plugins · Extensions · MCP Apps · MCP Events | descartar / depois | canal do ChatGPT; MCP Apps não é novidade; MCP Events é rascunho |
| Private Intelligence · ZDR com Private Safety Processing | depois | contrato e aprovação da OpenAI — decisão comercial |
| Private Inference | não saiu | "preview coming this fall" |
| Batch/Flex do 6.1 (50%) | depois | vale para trabalho sem pressa, pela fila que já existe |

Afirmações do texto externo conferidas: "6.1 Ultrafast disponível" **errada**; "Private Inference disponível" **errada**;
"MCP Apps lançado hoje", "ZDR para todos", "Decisions API disponível", "MCP Events como API" **imprecisas**; "Computer
Use no 6.1" **não verificada**; "6.1 com o mesmo preço" **certa** (e o cache ficou mais barato).

### 1.3 O cérebro medido pela primeira vez (F1, `b53ba5a` + conserto Z `9bcf816`)
- 📊 BLOCO 0: o cérebro da fase humana **nunca** tinha sido medido — 6 `work_runs` em que o agente conduziu URA; a bancada
  da SPEC-116 media o **localizador**, não o cérebro, e saiu inválida.
- A bancada usa o prompt e o conferente **do produto** (importados, nunca copiados). Corpus: **92 casos reais mascarados**
  (as armadilhas entram **sem** o arnês, para medir o julgamento do modelo). Braços: **Opus 5.5 V0 (controle = o de
  produção)**, 6.1 V0, 6.1 V2 (saída estruturada + contexto + proibições em código). Sonnet 5.5, V1 e V3 não couberam no teto.
- 📊 Tabela recalculada sem chamar modelo (`pytest tests/test_spec122_bancada_do_cerebro.py -k recalculada`, 30/09):

| braço · variante | erros graves nas armadilhas | abstenção correta | formato inválido |
|---|---|---|---|
| Opus 5.5 · V0 (controle) | **6** em 15 | 60,0 % | 0 |
| GPT-6.1 Sol · V0 | **14** em 31 (7 nas mesmas 15 do Opus) | 41,9 % | 4 |
| GPT-6.1 Sol · V2 | **2** em 31 (`091`, `092`: trocou o titular num menu reaberto) | **90,3 %** | 0 |

- **G1 (zero grave) falha em todos → nenhuma autonomia.** O dispatch **continua Opus 5.5**; o 6.1 fica reserva. A V2 só roda
  em sombra. Acerto dos grupos A (31–37 %) e B está deprimido **igualmente** para todos: o acervo não guarda a ficha do caso.
- 📊 Gasto do ledger (SELECT independente, juiz e builder): **OpenAI US$ 1,7557** (148 chamadas) · **Anthropic US$ 1,7383**
  (Opus 63 + Sonnet 2 do probe) — dentro do teto de US$ 2 por provedor. ⚠️ O teto cortou o Opus em 15 das 32 armadilhas
  (o arquivo tinha as armadilhas por último; a ordem foi corrigida).

### 1.4 🔴 O incidente de dados, declarado
- A 1ª versão do corpus deixou um **primeiro nome** de pessoa do piloto em vocativo em **5 casos**, e ele foi às **duas APIs**
  nas três rodadas. O guarda da SPEC-116 acusou; o gerador passou a trocar por `{NOME}`.
- O juiz achou mais: **1 número de processo de sinistro** (formato pontuado, que a varredura não via), e o builder Z achou o
  **código de corretor** do piloto em 4 casos, 2 códigos de acesso de uso único e 1 saldo. Todos mascarados; as duas varreduras
  ganharam 4 padrões com linha de controle; 📊 corpus inteiro da bancada = **0**. ⚠️ O que já foi às APIs não se desfaz.
- ⚠️ Fora desta SPEC e já na `main`: o mesmo número de processo e o mesmo código de corretor seguem em 4 arquivos (P-122-11).

### 1.5 O sem_chute pergunta ao segurado (F2, `582caf3` + conserto X `501e0ca`) — decisão D2
- Antes: tela de passo `sem_chute` sem o dado → **pessoa**, sempre. Agora, na Porto, HDI, Yelum e Zurich (onde a URA espera
  o bastante), um passo de **DADO** pergunta ao segurado com as opções da tela; a resposta só vira tecla se casar **uma**
  opção, **contra a tela atual**. Allianz e Alfa (URA com pressa) → pessoa, como antes (controle byte a byte).
- Navegação (`Voltar`, `Sair`, `Menu`…) **nunca** é oferecida nem aceita; passos que **decidem** (serviço aberto da Porto,
  táxi, submenu de bateria, veículo, motivo) → pessoa. Nenhum slot `*_opcao` guarda resposta crua.
- Endereço em **BR / rodovia estadual / estrada / km** nunca vira "Nenhuma das anteriores" sozinho. Bradesco pergunta
  via ou rodovia quando o endereço não resolve. Aceite de custo é recusado também quando o **valor** do modelo aceita.

### 1.6 O cérebro em sombra (F3 + conserto X)
- Migration `20260930_02`: `cerebro_modos` (corretora × seguradora × ramo), `off` | `sombra`; **`on` recusado** pela
  constraint do banco e pelo código. Tabela nasce **vazia** = tudo desligado. RLS ligada, 0 policy, filtro por
  `company_id` no código, teste com duas corretoras.
- Em sombra: o sistema envia **exatamente** o de hoje; depois do envio, só o modelo primário decide ao lado (sem reserva,
  fora do disjuntor e da cota da produção), e a divergência vai para `work_events` `cerebro.sombra` com o rastro higienizado.
  Custo no ledger como `cerebro_sombra`, na conta da corretora. 📊 Hoje: 0 linhas e 0 eventos (chave desligada).

### 1.7 O número
📊 `python scripts/simular_corredor.py --todas --formato json`, antes e depois do conserto X (30/09):
**ATENDE SOZINHO 31 · VAI PARA UMA PESSOA 4 · FALTA CAPTURA 41 · 76 rotas** — os dois arquivos **idênticos byte a byte**
(`cmp`), **0 rotas mudadas**. É o esperado: a SPEC não liga autonomia nenhuma.

## 2. COMMITS
`29b0b76` F0 · `b53ba5a` F1 · `582caf3` F2+F3 · `9bcf816` conserto Z · `501e0ca` conserto X · docs/relatório: ver o push (§8).

## 3. BATERIA
📊 Suíte inteira em worktree limpo, triada nominalmente contra a linha de base da SPEC-121 (`b0aff49`, 40 failed):
```
501e0ca ......... 72 failed · 2418 passed → 32 NOVAS: 1 de PRODUTO (via_ou_rodovia_opcao sem rótulo na ficha)
                  + 31 testes da 122 contaminados por módulos trocados em sys.modules por 7 carregadores
                  e 4 testes de outras áreas (medido com uma sentinela de módulos — P-121-28 ampliada)
d07dc6c (final) . 40 failed · 2451 passed (3.563 s) → lista IDÊNTICA à base: 0 novas, 0 sumiram
```

## 4. GATES
| gate | estado |
|---|---|
| G1 zero grave nas armadilhas | ❌ nenhuma variante (V2: 2 em 31) → **nenhuma autonomia**, só sombra |
| G2 abstenção ≥ 90 % · A ≥ 85 % · B ≥ 97 % | ❌ parcial: V2 abstenção **90,3 %** ✅ · A 31 % ❌ · B 31 % ❌ (corpus sem ficha — P-122-05) |
| G3 0 formato inválido · 90 % < 30 s | ✅ V2 (0; 100 %) · ❌ 6.1 V0 (4 vazias) |
| G4 controle Opus V0 na mesma bancada | ⚠️ PARCIAL — medido, 15 de 32 armadilhas (teto) — P-122-03 |
| G5 ≤ US$ 2 por provedor, do ledger | ✅ 1,7557 · 1,7383 |
| G6 nenhuma rota que atende sozinha muda | ✅ 31/76 antes e depois, arquivo idêntico |
| G7 tirar a proibição de custo → grave | ✅ `test_G7_tirar_a_proibicao_de_custo_do_parser_vira_erro_grave` |
| G8 F0 esforço, reserva, smoke, failover | ✅ 8 linhas de histórico com esforço igual; 7 mutações vermelhas; smoke US$ 0,0073; failover provado |
| G9 sombra: zero efeito novo | ✅ teste byte a byte; `on` recusado no banco; sem caminho de envio (juiz e red team) |

## 5. JULGAMENTO
- **Juiz: PASS COM PENDÊNCIAS, 78** (confiança 82). 3 números reproduzidos por caminho independente (ledger, tabela lida
  dos JSON crus, 30 passos `sem_chute`). **B1** o endereço "BR 282" + "local seguro" fazia o **motor** responder "Nenhuma das
  anteriores" numa tela que oferece "Rodovia" (antes ia a pessoa) — **EXCLUSIVO do juiz**. **B2** número de processo de
  sinistro no corpus commitado — **EXCLUSIVO do juiz**. Gate vermelho: o guarda dos chamadores do dispatch não conhecia a sombra.
- **Red team: QUEBREI, 62** (confiança alta). **B1** "Voltar" oferecido ao segurado como resposta, com laço na URA ·
  **B2** Porto "serviço aberto": pergunta errada e o caso gravava "Não" como serviço · **B3** resposta crua do segurado
  indo à URA quando ela reabre (o juiz achou a mesma como pendência). B1 e B2 **EXCLUSIVOS do red team**.
- Achados dos dois lados sobre a sombra dividir disjuntor e cota com a produção (juiz P2 = red team P4): consertados.
- **Conserto único em 2 partes** de arquivos disjuntos: Z (`9bcf816`, corpus e medição) e X (`501e0ca`, sem_chute e sombra;
  📊 37 testes novos, 16 mutações vermelhas). Todos os blockers fechados.
- Confirmação: Confirmação (juiz novo, só o diff do conserto): os 5 blockers FECHADOS (J-B1, J-B2, RT-B1/B2/B3) e o teste vermelho;
achou 1 defeito NOVO criado pelo conserto — N1: o veto largo de rodovia escolhia "Rodovia" na Bradesco para "ap 101" —
consertado em `18a8110` (forma forte só para escolher; teste com controle, mutação vermelha). Nota da confirmação: 84 (≈ 88 com o N1).

## 6. MIGRATIONS
- `20260930_01_spec122_gpt_6_1_sol.sql` — APPLY/VERIFY/ROLLBACK no cabeçalho, escritos antes; aplicada 30/09 (versão
  `20260930085813`). O juiz conferiu por SELECT e leu o ROLLBACK (não ensaiado — P-122-15).
- `20260930_02_spec122_cerebro_modos.sql` — aplicada 30/09 (versão `20260930103232`); VERIFY inclui a prova de que o
  CHECK **consegue** recusar `on` (erro 23514, em transação desfeita). Juiz: constraint lida do `pg_constraint`.

## 7. O QUE FICOU FORA
P-122-01…18 em `PENDENCIAS.md` (as principais: o docling ler a rota, as variáveis do EasyPanel, completar o controle Opus,
Sonnet/V1/V3, corpus com a ficha do caso, os dados do piloto ainda em 4 arquivos da `main`, e a decisão de ligar a sombra).
Anotadas: P-S116-01 e P-S116-09 🟡, P-121-07 e P-121-10 🟡 (absorvidas).

📋 **A CAIXA DO FOUNDER** — `TAREFAS-DO-FOUNDER.md`, bloco S122: Implantar `smith-api` → `smith-worker` → `docling-service`
(o catálogo já está no banco; o Implantar leva o sem_chute novo, a sombra e o default do docling) · conferir 3 variáveis
pelo nome · ligar a
sombra quando quiser (SQL pronto) · os testes da S121 continuam pendentes, como ele decidiu.

## 8. ENTREGA
📊 30/09/2026, `git push origin HEAD:main`:
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   2f1859d..c266381  HEAD -> main
```
`git rev-list --count origin/main..HEAD` → 0. Depois do push o Founder clica **Implantar** (smith-api → smith-worker → docling-service).

## 9. NOTA E TELEMETRIA
86

📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (30/09): sessão inteira (SPEC-121 + 122) — executor 1.133 min, pico 681 k, US$ 65,59; 29 agentes (todos Opus 5.5), US$ 460,71; pela diferença contra o fechamento da 121 (US$ 297,54, 15 agentes), a SPEC-122 ≈ 13 agentes, ≈ US$ 163 (derivado). APIs do produto: bancada OpenAI US$ 1,7557 + Anthropic US$ 1,7383; canários US$ 0,0047 + 0,0073. Rodadas de bateria: 3 (72 → 40 failed; 0 novas no fim).
achados por mecanismo: pesquisador (6.1 real; 4 afirmações externas erradas) · investigador (cérebro nunca medido; autoridade escondida no docling) · bancada (nenhuma variante passa G1) · juiz 2 blockers · red team 3 blockers EXCLUSIVOS · confirmação 1 blocker novo · bateria 1 defeito de produto

Nenhum motor paralelo foi criado: a bancada estende `evals/bancada.py` (Eval Fabric da SPEC-062/116), o cérebro continua
`build_human_phase_messages` + `guard_human_phase_reply`, a sombra usa `invocar_com_reserva` e `work_events`, e a chave
é uma tabela governada — não env. A sombra chama só o primário do dispatch, fora do disjuntor (a reserva fica com a produção).
