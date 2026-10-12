# LAUDO I1 — o motor e a madrugada (SPEC-131 · o aplicativo de Renovação)

> 🔍 Investigador I1 · modo INVESTIGAÇÃO (protocolo v13 §3.3/§8) · 12/10/2026 · árvore `AutoBrokers-FIX`, branch
> `investigacao/2026-10-12-renovacao` · SÓ LEITURA: código lido, banco por SELECT (MCP, projeto `dcajcvlzcjbmyapmklil`), 1 script
> Python local sem rede. Nenhuma chamada ao Agger, à InfoCap, ao WhatsApp ou a modelo. Nenhum dado pessoal neste arquivo.
> Cobre o pedido do Founder ([PEDIDO-DO-FOUNDER-2026-10-12.md](PEDIDO-DO-FOUNDER-2026-10-12.md)) parte B itens 1–7, 10 e a parte C sobre o Agger.
> Marcas: 📊 medido (com o comando) · 💭 estimativa/hipótese, nunca citável como fato.

## 0. Em uma tela

| # | pergunta | resposta curta | recomendação · nota |
|---|---|---|---|
| 1 | o fio da renovação | as peças existem e foram testadas SEPARADAS; **nenhum elo as liga** (📊 0 pedidos `servico='renovacao'` no banco); falta o orquestrador do dia, a lista congelada e o estado por apólice. 🔴 1 defeito latente: ramo desconhecido vira AUTO | construir o orquestrador sobre o Work OS + tabela de itens · **90** |
| 2 | tempo e horário | 📊 RE 46–48 s do POST ao último preço; 61–134 s da reserva ao fim; AUTO histórico fecha em 64 s (p90 406 s); teto de leitura 480 s. Um login = um pedido por vez; logins diferentes em paralelo; sem teto de sessões simultâneas | **começar às 02:00**, tudo enfileirado de uma vez, serial por login, paralelo entre logins, teto de sessões · **88** |
| 3 | nunca esquecer | hoje não existe nada que conte "esperadas × feitas" | lista do dia congelada + estado por item + conferência INDEPENDENTE às 05:30 sobre uma leitura NOVA da InfoCap + alerta · **92** |
| 4 | ramos que não cotamos | hoje nada acontece (ninguém chama `de_apolice`); ligado como está, 📊 NAUT/RCPR/GOC/CAPI/MOBI/FROT/PQRE/CTVE **viram pedido de AUTO** | na 131: pendência visível ao comercial + consertar o mapa · **92**; depois: SPEC por ramo (vida, moto) · **80** |
| 5 | Agger conectado / madrugada | o código CANCELA sempre e falha na 3ª vez (90 min); a regra antiga "nunca Prosseguir" conflita com o Founder | Prosseguir só de madrugada, só renovação, 1 vez por conta por noite, depois de MEDIR o que o botão envia · **88** |
| 6 | negociação e emissão | negociação pura existe (QCM); nada de estado de renovação, nada de emissão | a 131 cria a máquina de estados inteira, liga só até "calculada/enviada" · **86** |
| 7 | a fila | 📊 InfoCap conectada em **0** das 2 corretoras reais; 0 Aggers de comercial; 0 vínculos produtor↔pessoa; o Agger da corretora está ligado nas 2 | 9 itens do Founder (§7); constrói-se sem eles, liga-se com eles |

---

## 1. O fio, elo a elo — o que está pronto, o que é só teste, o que não existe

```
InfoCap /renovacoes ─► dono (/prod_docs) ─► ficha (130-B) ─► de_apolice ─► porta.calcular ─► qual_agger ─► motor ─► pedido ─► resultado
```

| elo | onde | estado | prova |
|---|---|---|---|
| **a lista do que renova** | `backend/app/comercial/fonte_infocap.py:453` `renovacoes_cruas` · `:571` `carteira_a_vencer` | ✅ código pronto (usado pelo BI/radar `renewal.exposure`). ❌ **ninguém o usa para renovar**: não há lista congelada nem estado por apólice | 📊 `Grep "carteira_a_vencer\|renovacoes_cruas" backend/app` → só `fonte_infocap.py`, `infocap_analytics_provider.py:872` (BI) e `dono.medir_regra` |
| **a fonte da corretora** | `dono.abrir_fonte` (`sistema_de_gestao/dono.py:476`) → `infocap_analytics_provider._abrir` | ✅ código · ❌ **dado**: 📊 nenhuma InfoCap `connected` nas corretoras reais | 📊 `select ... from tenant_connections where name ilike '%infocap%'` → Resulta `disconnected` · AutoFleet `disconnected` · Amandus (ensaio) `connected` "InfoCap AUTOFLEET" (o banco da AutoFleet, D-131-0-27) |
| **o dono** (D-131-0-03) | `dono.dono_da_apolice` `dono.py:493` · régua `medir_regra` `:537` | ✅ código + 🧪 testes (`test_spec1310_f2_dono.py`, `test_spec1310_o_fio.py`) + 📊 régua real 99/99 e 217/217 (BLOCO 0 da 131-0) · ❌ **vínculos vazios** | 📊 `select count(*) from membro_produtores` → **0** linhas · `regras_de_dono` → **0** (vale o padrão do sistema em JSON). Hoje TODA renovação daria `sem_membro` |
| **a ficha** (130-B) | `policy_document_evidence_service` + `/documento_anexos` | ✅ código + 📊 régua 24/28 com PDF (RESI 7/7 · COND 6/8 · EMPR 5/7 · AUTO 6/6) · ⏳ não implantado (T-154) | `reports/SPEC-130-B-EXECUTION-REPORT.md` §1 |
| **o pedido** | `multicalculo/pedido.py:702` `de_apolice(…, ficha=, config=, exigir_completo=)` | 🧪 **só teste** (`test_spec130b_renovacao_le_a_ficha.py`, 📊 16 testes: `Select-String "^def test_"` → 16). Ninguém o chama no produto | 📊 `Grep "de_apolice\(" backend/app` → só a definição |
| 🔴 **o ramo do pedido** | `pedido.py:687-699` `_ramo_do_agger` | ❌ **defeito latente**: família desconhecida (`None`) → `RAMO_AUTO` | 📊 script local (`_ramo_do_agger(S(ramo=r))`, 12/10): AUTO→31 · RESI→2 · COND→16 · EMPR→18 · VIND/VGRP/VIAG→`RamoIndisponivel` · **NAUT, RCPR, GOC, CAPI, MOBI, FROT, PQRE, CTVE, TRAN, RISC → 31** |
| **a porta** | `porta.py:413` `calcular(…, servico='renovacao', dono_user_id, vence_em_dias)` | ✅ código + 🧪 testes (131-0-A F3) · origem `auxiliar`, prioridade 5, expira em 24 h (`porta.py:73-75`) | 📊 `select servico, origem, count(*) from multicalculo_pedidos` → **só 6 pedidos, todos `servico=null/origem=teste`** (canários) |
| **qual Agger** | `qual_agger.py:203-239` (renovação) | ✅ código + 🧪 testes: dono com Agger pronto → o dele; sem dono/sem membro/sem conta/desconectado/pausado → o da corretora **com aviso**; senha recusada → recusa, global só se vence em < 5 dias | 📊 `portal_accounts portal_key='agger'`: **2 `global/ativo` com senha** (Resulta e AutoFleet) · 2 `teste/pausado` · **0 `membro`** |
| **o motor** | `portal_worker/multicalculo/motor.py` | ✅ real, 📊 canário AO VIVO RE 11/10 (3 ramos, 3 `calcularV2`, HTTP 201) e AUTO 05/10 · ⏳ nasce DESLIGADO (`MULTICALCULO_MOTOR_LIGADO`, `motor.py:139`) — valor em produção **não medido** daqui | `129-C/CANARIO-AO-VIVO.md` §2 |
| **o pedido gravado** | `multicalculo_pedidos` / `_calculos` / `_ofertas` / `_eventos` | ✅ esquema · 📊 17 cálculos no banco, todos de canário | 📊 `select p.ramo, c.opcao, c.status, count(*) … group by` (§2) |
| **o resultado ao comercial** | — | ❌ não existe: nem painel de renovações, nem estado por apólice, nem aviso das 7h. O `conta_motivo` (o aviso do `qual_agger`) é gravado e **ninguém o entrega** (SPEC-131-0-A §5.3: "quem o entrega é a 131/132") | `qual_agger.py:51-55` |
| **o agendamento** | o laço de manutenção do `smith-worker` a cada 5 min (`intelligence/tick.py:1-21`, idempotência por `idempotency_key` com o período) | ✅ existe e roda (📊 `work_runs` 60 dias: `intelligence.daily_briefing` 179, `detect_signals` 4.299 completed) · ❌ nenhum trabalho de renovação nele | 📊 `select workflow_key, status, count(*) from work_runs where created_at > now()-'60 days'` |

**INFERÊNCIA:** a 131 não precisa de motor, porta, leitor nem decisão de conta novos (CLAUDE.md §5). O que falta é o **orquestrador do dia**
(um Work Run por corretora por dia, enfileirado pelo tick), a **entidade "renovação"** com estado (ela vive além da madrugada: vai a
apresentação, negociação, emissão — §6) e a **conferência**. O defeito do ramo (`None → AUTO`) é BLOCKER no instante em que a 131
chamar `de_apolice` sobre a lista da InfoCap: 📊 na Resulta, de 99 renovações em 30 dias, CAPI 5 + RCPR 3 + GOC 3 + NAUT 2 = **13 viram
pedido de carro** (BLOCO0-INFOCAP-A-CONEXAO-TROCADA §3); na AutoFleet, MOBI 5 + FROT 1. Elas não chegam a calcular (falta placa →
`PedidoIncompleto`), mas o motivo mostrado seria "falta a placa", que é mentira.
**RECOMENDAÇÃO:** `familia None` → `RamoIndisponivel("não sei que ramo é")`, nunca AUTO, com teste que use as 10 siglas acima e mutação
que devolva o AUTO (nota **95**; a outra opção, mapear sigla a sigla e manter o padrão AUTO, nota 40).

---

## 2. O tempo de um cálculo e o paralelismo — e o horário de início

### 2.1 O que foi medido
| grandeza | valor | fonte / comando |
|---|---|---|
| RE, do POST ao último preço | 📊 COND 46 s · RESI 48 s · EMPR 47 s (fecha o conjunto em 70 s e 82 s) | `129-C/CANARIO-AO-VIVO.md` §2 (`t_s` do robô) |
| RE, da reserva ao `fechado` (com login de 📊 54 s no 1º) | 📊 134 s · 90 s · 61 s | idem; e 📊 `select ... extract(epoch from fechado_em - disparado_em)` → ramo 16: 134 s · 2: 90 s · 18: 61 s |
| AUTO, histórico de 227 cálculos | 📊 1ª oferta 6 s · 80 % em 27 s · fecha em 64 s (p90 406 s) · **26 de 227 nunca fecharam** | A-PROVA §2 (`analisa_versoes.py`) |
| AUTO, os nossos 16 da 128 | 📊 fecha mediana 37,5 s (máx 51 s); 2 de 16 nunca fecharam | A-PROVA §2 |
| relógio de parede de um cálculo AUTO | 📊 ~45 s (servidor) · 55 s (máquina) | A-PROVA §2 |
| canário AUTO 129-B no banco | 📊 fecha p50 317 s, máx 425 s — ⚠️ inclui a morte proposital e a espera da lease (relatório 129-B §2 linha 71) | `select ... where ramo=31` |
| login · logout pela tela | 📊 entrar 34–54 s · sair 12–14 s | A-PROVA §11 e canário 129-C |
| teto de leitura de um cálculo | 📊 480 s (`agger_robo.py:915` `teto_s: float = 480`) | código |
| "**~7 min**" dos HAR antigos | 📊 413–420 s (n = 2), o que o plano achava — é a CAUDA (p90 406 s), não o típico | A-PROVA §1 |

### 2.2 O que o motor faz em paralelo hoje (FATO, código)
- **Um login = um pedido por vez.** A lease é por conta (`robos.py:295-310`, CAS em `portal_accounts.robo_dono`); `_reservar` diz:
  "Corretoras diferentes saem em PARALELO; a mesma conta, um grupo por vez" (`motor.py:505-508`).
- **Dentro de um pedido**, as opções (padrão, econômica, completa+ — as 3 da renovação) saem em SÉRIE no mesmo negócio e são LIDAS em
  paralelo (`motor.py:1064-1125` `_disparar_todos`; `motor.py:881` `asyncio.gather` das leituras). 📊 2 simultâneos na mesma sessão:
  16/16 fecharam (A-PROVA E7). 3 simultâneos: **não medido**.
- **Logins diferentes da MESMA corretora** (o Agger de cada comercial + o da corretora) rodam em paralelo — cada um é uma conta com
  lease própria. ⚠️ 📊 A-PROVA E7 "PARCIAL": dois usuários da mesma conta do Agger calculando juntos **nunca foi medido**; e as
  credenciais das seguradoras são da CORRETORA (📊 `compartilhada` em 15/15 e 14/14, A-PROVA §11) → N logins em paralelo = N pedidos
  em paralelo na MESMA credencial de cada seguradora.
- **Não há teto de sessões simultâneas**: 📊 `Grep "MAX_SESS|MAX_GRUPOS|MAX_CONC|SIMULT" backend/portal_worker` → 0. Cada conta abre
  um contexto do Chromium. Os freios que existem são por HORA: conta 60/h (`robos.py:61`), corretora 120/h e geral 400/h
  (`motor.py:96-97`, por variável de ambiente).
- **O Agger de uma pessoa faz logout depois de CADA pedido** (`motor.py:742-750`, `login_de_pessoa` → `_fechar_sessao`). Um comercial
  com 8 renovações = 8 logins e 8 logouts na noite (💭 +~1 min por renovação e 8 chances de cair no aviso de sessão ativa).
- **Prioridade:** renovação e cotação têm a MESMA origem `auxiliar`, prioridade 5 (`porta.py:63,73`). Se a madrugada transbordar para
  a manhã, a cotação pedida no chat espera na fila atrás das renovações (ordem `prioridade, criado_em`, `motor.py:514`).

### 2.3 O volume e o pico
- 📊 Resulta 99 renovações em 30 dias (RESI 34 · EMPR 20 · COND 14 · VIND 6 · CAPI 5 · VIAG 4 · RCPR 3 · VGRP 3 · GOC 3 · NAUT 2 · …),
  9 donos (maiores 40 · 33 · 11) · AutoFleet 217 (AUTO 210 · MOBI 5 · FROT 1 · RESI 1), 9 donos (maiores 83 · 29 · 28) —
  BLOCO0-INFOCAP-A-CONEXAO-TROCADA §3–§4 (`GET /renovacoes` 11/10→10/11). 📊 E2 (04/10): AutoFleet 438 AUTO em 60 dias (= 7,3/dia).
- Média por dia corrido: 💭 Resulta 3,3 · AutoFleet 7,2 · maior dono 2,8 (AutoFleet) e 1,3 (Resulta).
- **O pico diário NÃO foi medido** (não há cópia de `/renovacoes` no banco: 📊 nenhuma tabela `*renov*`/`*renewal*` em
  `information_schema.tables`). 💭 Para dimensionar, uso pico = 3 × média: Resulta ~10/dia, AutoFleet ~22/dia, maior dono ~8/dia.

### 2.4 A conta (💭, a partir dos 📊 acima)
Um pedido de renovação de 3 opções num login de pessoa: login 34–54 s + leitura até fechar + logout 12–14 s →
💭 **típico ~2,5 min** (cálculo fecha em ~60–80 s) · **p90 ~8 min** (cauda de 1–2 seguradoras, p90 406 s) · **pior ~9,5 min** (teto 480 s).

| fila (serial, um login) | renovações no pico | típico | p90 | pior |
|---|---:|---:|---:|---:|
| maior dono (AutoFleet), no Agger dele | 💭 8 | 💭 20 min | 💭 64 min | 💭 76 min |
| **Agger da corretora AutoFleet, HOJE (0 vínculos → todas caem nele)** | 💭 22 | 💭 55 min | 💭 2 h 56 | 💭 3 h 29 |
| + a pessoa no próprio Agger (3 × 30 min, `motor.py:70,114`) | — | — | — | +💭 1 h 30 |

Freios: 💭 22 × 3 = 66 cálculos/h na AutoFleet < 120/h da corretora; < 400/h geral até ~6 corretoras desse porte no mesmo minuto.

### 2.5 RECOMENDAÇÃO — horário e lotes
| opção | nota | porquê |
|---|---:|---|
| **02:00 início dos cálculos** (preparação 00:30, conferência 05:30, aviso 06:45) | **88** | 5 h até as 7h cobrem o PIOR caso do login mais carregado (💭 3 h 29) + 1 volta de retentativas; a madrugada já foi usada sem incidente (📊 canário 129-C às 03:15, 129-B/§10 às 04:23) |
| 03:00 | 78 | cobre o p90 com folga, o pior caso fica sem tempo para a retentativa e a conferência |
| 00:00 | 70 | pega gente ainda logada e janela de Implantar; ganha tempo que não é preciso |
| 04:00 | 55 | não cobre o p90 do Agger da corretora |

**Lotes:** "de 5 em 5 pelo relógio" **55** × **enfileirar tudo de uma vez; o motor serializa por login e paraleliza entre logins**
**86**, com três acréscimos pequenos: (a) teto de sessões simultâneas por processo e por corretora (💭 6 e 3, configuráveis; hoje não
existe) — protege a máquina e a credencial compartilhada da seguradora; (b) **manter a sessão do Agger de uma pessoa entre os pedidos DELA
na mesma madrugada** e sair no fim da fila dela (nota 80; hoje é logout por pedido); (c) prioridade própria da renovação, abaixo da
cotação (💭 7), para a cotação do dia nunca esperar uma madrugada atrasada (nota 85). **Por ramo** (auto antes, depois RE): ordenar o
enfileiramento por (ramo, vencimento) — custo zero, deixa o Agger organizado (nota 75; não muda o tempo).
**Dias:** rodar **7 dias por semana** (nota 85) — o Agger não tem horário (D-129C-01) e a segunda-feira não acumula 3 dias.
**Antecedência:** 📊 o padrão do produto é **15** dias (`config.py:57` `"antecedencia_dias": 15`) e o Founder pede **10**; já é editável por
corretora (`config.py:597`). Trocar o padrão para 10 (decisão registrada).

---

## 3. A garantia de completude — "nunca esquecer uma renovação"

**FATO:** hoje não existe contagem "esperadas × feitas". O `multicalculo_pedidos` só conhece o que VIROU pedido — a renovação esquecida
é justamente a que nunca virou (📊 `multicalculo_pedidos` sem coluna de apólice/vencimento; o esquema é pedido × cálculo).

**O mecanismo recomendado (nota 92)** — tudo sobre peças que existem (tick do `smith-worker`, Work Runs com `idempotency_key`, espera
durável `work_runs.wake_at`/`work_waits` da 129-A, a porta e o motor):

```
00:30  PREPARAR (Work Run "renovacao.preparar", 1 por corretora por dia, chave company:data)
       /renovacoes [hoje, hoje + antecedência + margem] → LISTA CONGELADA: 1 item por (company_id, sistema, codfil, nosnum, fimvig)
       — upsert, nunca duplica; endosso que muda o fim de vigência = item novo e o velho "substituído"
       por item: dono (/prod_docs, EM SÉRIE — 📊 "10 paralelas → um 500", dono.py:489) → ficha (130-B) → de_apolice →
       estado `pronta` ou `pendente(motivo)`: ramo não cotado · falta dado X · sem conexão · sem PDF
02:00  CALCULAR ("renovacao.calcular"): porta.calcular(servico='renovacao', dono_user_id, vence_em_dias) para todo item `pronta`
       com fimvig − antecedência ≤ HOJE (não "= hoje": o que ficou para trás por falha entra hoje — o atraso se recupera sozinho)
       → item `calculando` (pedido_id) → motor → `calculada` (≥ 1 oferta) | `falhou(motivo)` | `aguardando_agger` (a pessoa no login)
05:30  CONFERIR ("renovacao.conferir", OUTRO caminho de código): lê /renovacoes DE NOVO (nunca a lista congelada), monta o conjunto
       ESPERADO e cruza com os itens. Cada esperada tem de estar num estado TERMINAL DO DIA: calculada · pendente com motivo visível.
       Falta item → cria e marca "esquecida pela preparação" (defeito, alerta vermelho). Falhou por causa passageira → 1 retentativa
       até 06:15; depois o desvio de conta do §5.
06:45  AVISAR: painel do aplicativo + aviso a cada comercial e ao admin: "N prontas no seu Agger · M pendentes (porquê) · K falharam"
```

Guardas (§9.5 do CLAUDE.md — o guarda tem de ficar VERMELHO): tirar 1 item da lista congelada → a conferência acusa; a conferência
lendo a lista congelada em vez da InfoCap → teste vermelho; item `calculando` às 05:30 sem batida → não conta como feito. Medida diária
gravada: **completude = (calculadas + pendentes com motivo) ÷ esperadas = 100 %**, e à parte **calculadas ÷ esperadas cotáveis**.

| alternativa | nota | porquê |
|---|---:|---|
| **lista congelada + estado por item + conferência independente sobre leitura nova + alerta** | **92** | conta o que NÃO virou pedido; a 2ª leitura pega o que a 1ª perdeu (InfoCap instável: 📊 502 em janela grande, `fonte_infocap.py:639`); o item vive até a emissão (§6) |
| só Work Runs filhos por apólice, sem tabela | 70 | o `work_runs` é genérico; painel/Kanban por estado de renovação e a vida longa do item (negociação, emissão) pedem entidade própria |
| derivar dos `multicalculo_pedidos` | 35 | a esquecida nunca vira pedido — não há o que contar |
| "juiz" com modelo conferindo | 20 | completude é contagem determinística; modelo erra e custa |

⚠️ A CONFERÊNCIA depende da InfoCap às 05:30; InfoCap fora = estado `sem_conexao` do dia inteiro → alerta ao admin (nunca "0 renovações").

---

## 4. Ramos que não cotamos

**O que acontece HOJE:** nada — o produto não processa renovação (§1). Se a 131 ligar `de_apolice` como está: VIND/VGRP/VIAG → recusa
`RamoIndisponivel` (honesta); NAUT/RCPR/GOC/CAPI/MOBI/FROT/PQRE/CTVE/TRAN/RISC → **pedido de AUTO** (📊 script do §1). A porta ainda
recusa RE fora de `RAMOS_RE` (`porta.py:457-459`), mas AUTO passa a porta e só para em `PedidoIncompleto`.

**O tamanho:** 📊 Resulta, 30 dias: dos 99, cotáveis pelo motor = RESI 34 + EMPR 20 + COND 14 = **68**; **≥ 31 não cotáveis** (VIND 6 · CAPI 5 ·
VIAG 4 · RCPR 3 · VGRP 3 · GOC 3 · NAUT 2 · + o "…" não listado). AutoFleet: 210 AUTO + 1 RESI cotáveis; MOBI 5 · FROT 1 não.
(BLOCO0-INFOCAP-A-CONEXAO-TROCADA §3.)

**O que o Agger cota:** 📊 13 entradas no "Nova Cotação" (A-PROVA §10, mesmas nas duas contas): Carro · Caminhão · Motocicleta ·
Residencial · Condomínio · Empresarial · Vida Individual · Vida Global · Acidentes Pessoais · Viagem · Aluguel · Bike · Celular
("Cálculos ilimitados em 14 ramos" na tela do plano). Código: 31 = Carro, Caminhão E Motocicleta (📊 links do código 31); 91 = Vida;
69/93/46/100 sem nome medido. 📊 Vida Individual: formulário de 47 campos, 12 obrigatórios (A-PROVA §10). **Fora do Agger:** RC
profissional, náutico, risco de engenharia, transporte, garantia, capitalização, consórcio (💭 pela lista; nenhum deles aparece nas 13).

| solução | quando | nota |
|---|---|---:|
| **pendência visível ao comercial**: o item nasce `pendente(ramo_nao_cotado)` com o vencimento, o dono e "renove manualmente"; conta na completude; aparece no painel e no aviso das 6:45 | **nesta SPEC (131)** | **92** |
| consertar `None → AUTO` (§1) | **nesta SPEC — é pré-condição** | **95** |
| nova SPEC por ramo, pelo volume e por estar no Agger: **Vida Individual/Global** (📊 9/mês na Resulta, formulário medido) e **Motocicleta** (o mesmo código 31; 💭 MOBI pode ser outra coisa — medir) | depois da 132 (129-D) | **80** |
| "cálculo genérico pelo Agger" | — | **20** — não existe modo genérico: cada ramo é um formulário com contrato próprio (o precedente da 129-C: um pedido + um preset por ramo) |
| ramos fora do Agger (náutico, RC prof., garantia…) | portal da seguradora, SPEC própria se o volume pedir | 💭 60 |

---

## 5. Agger conectado · sessão única · madrugada · férias · admin sem Agger · cliente sem dono

### 5.1 O que o código da 131-0 já faz (FATO)
| situação | comportamento | onde |
|---|---|---|
| aviso de "sessão ativa" | o robô clica SÓ "Cancelar" (seletor de texto exato) | `agger_sessao.py:44-47, 226-227, 263-276` |
| a guarda de rede | barra login cujo corpo tenha `derrub|forç|prosseg|encerr|nova sessão`; 1 login por contexto | `agger_guarda.py:47, 183-188` |
| Agger de PESSOA ocupado | `ocupada` 30 min, volta à fila; na **3ª vez** o cálculo FALHA ("agger_da_pessoa_em_uso"), **nunca cai calado no da corretora** | `motor.py:951-963, 114-119` |
| Agger de pessoa: senha recusada | bloqueado na 1ª, o cálculo falha | `motor.py:1017-1023` |
| Agger de pessoa: login sem desfecho | pausado na 1ª, falha | `motor.py:917-928` |
| fim do pedido no Agger de pessoa | logout sempre | `motor.py:742-750` |
| renovação sem dono / dono fora da equipe / dono sem Agger / desconectado / pausado | Agger da corretora + aviso | `qual_agger.py:207-239` |
| dono com senha recusada | recusa; o da corretora só se vence em < 5 dias | `qual_agger.py:220-232`, `config.py:183-186` |
| cotação: quem pediu sem Agger (o admin) | Agger da corretora + aviso | `qual_agger.py:180-201` — já é a regra do Founder |
| QCM | sempre o da corretora | `qual_agger.py:175-177` — já é a regra |
| substituto de férias | **não existe** (D-131-0-33 o deixou para a 131/135) | — |
| sessão fantasma | 📊 o aviso de sessão ativa **apareceu 3 h depois** de uma sessão sem logout (A-PROVA §10, adendo 07:36) | — |

### 5.2 O confronto: "nunca Prosseguir" × "de madrugada entra mesmo conectado"
A regra antiga (ESTADO §2/§2.2, D-131-0-05) nasceu para os TESTES no login da Ellen e para não derrubar uma pessoa trabalhando. O
pedido do Founder (B5) a muda para a madrugada. **INFERÊNCIA:** sem a mudança a promessa das 7h quebra: a sessão esquecida (📊 a
fantasma sobrevive horas) faz o robô cancelar às 02:00, 02:30, 03:00 e falhar — a renovação some do Agger dela.

| opção | nota |
|---|---:|
| **Prosseguir só quando: madrugada (janela da corretora, 💭 padrão 01:00–06:30 de Brasília) E serviço renovação E conta `membro` E 1 vez por conta por noite. Se a sessão do robô cair depois (a pessoa voltou), NÃO prossegue de novo: Cancelar, esperar 20–30 min (espera durável), tentar até 06:15; às 06:15 o que sobrou vai pelo Agger da corretora COM aviso nomeado ao comercial ("calculada no Agger da corretora porque o seu estava em uso")** | **88** |
| manter "nunca Prosseguir" | 40 — falha exatamente no caso comum (sessão esquecida) |
| Prosseguir sempre, sem limite | 30 — briga de sessão em laço, derruba quem trabalha de dia |
| Prosseguir na cotação do chat (a pessoa pediu no próprio Agger) | 💭 70 — ela é a dona da sessão; mas derruba a tela dela: perguntar no chat antes ("vou entrar no seu Agger; a sua tela vai sair") vale **82** |

**Pré-condições (sem elas, nota 0):** (1) **medir o que o "Prosseguir" envia** — nunca foi clicado (📊 `Grep -i Prosseguir docs/canon`:
só proibições). Medir com o login `cotador@` da própria corretora em dois contextos: nenhuma pessoa é derrubada (nota 90 para o BLOCO 0
da 131). (2) A guarda ganha a exceção ESTREITA (um sinal no `EstadoDaGuarda` que só a política da madrugada liga) + mutação: a exceção
ligada fora da janela → VERMELHO. (3) O texto da **T-141** muda — hoje promete ao comercial "nunca derruba a sessão dela"
(`TAREFAS-DO-FOUNDER.md` T-141): o aceite precisa ser refeito com a regra nova. (4) Registrar a decisão nova que revê a D-131-0-05.

⚠️ Mesmo derrubado no meio, o cálculo já POSTado fica no Agger dela (o negócio existe; 📊 E11): o comercial encontra a renovação calculada
no Agger; o que falta é a leitura para a apresentação, que a retomada faz pelo MESMO login depois (V20, `motor.py:479-486`).

### 5.3 Os outros casos
- **Substituto de férias (nota 85):** uma linha `substituicoes(company_id, user_id, substituto_user_id, de, ate)`; `qual_agger.decidir` da
  renovação usa o Agger do substituto no período (se ele tem; senão o da corretora com aviso). Trocar o vínculo produtor↔pessoa
  temporariamente: **45** (perde o histórico do dono). Novo login e senha: **20** (o Founder não quer).
- **Cliente sem dono (`sem_dono`/`sem_membro`/`ambiguo`):** já vai ao Agger da corretora com aviso (nota 85). Falta o aviso CHEGAR (§1) e
  o painel mostrar "sem dono" para o admin distribuir. 📊 Hoje seria 100 % (0 vínculos).
- ⚠️ **Por medir — o que mata o desvio:** o comercial ENXERGA, no Agger dele, um negócio calculado pelo `cotador@`? 📊 O robô enxerga 0
  negócios das pessoas (A-PROVA §11) e a Ellen enxergava a conta toda — a visibilidade parece ser por perfil. Se o comercial não vê,
  o desvio para o Agger da corretora cumpre "calculada" mas não "no Agger DELE" (liga-se à P-1310-06, transferir negócio).

---

## 6. Negociação e "Emissão e registro" — o que existe e o que a 131 deixa pronto

**Existe:** `multicalculo/negociacao.py` (a régua da margem, pura: `ordem_do_mais_barato`, `planejar`, `escolher`, `proxima_etapa`,
`texto_da_alavanca`) e `manual_de_negociacao.py` (contexto `carteira` = renovação de quem já é cliente) — feitos para o QCM, 130-A/130-A.1;
o modo por serviço `calcular · calcular_entregar · calcular_entregar_negociar` com `pode_entregar`/`pode_negociar` (`config.py:178-186`,
renovação nasce `calcular`); D-1311-06 dá o nome "Emissão e registro"; D-1311-04: **nunca escrever na InfoCap sem homologação**, e
📊 a InfoCap NÃO tem homologação (ESTADO §2.9) → a etapa terá de propor como escrever em produção com segurança (P-INFOCAP-INCORP).
**Não existe:** estado de renovação, eventos, a 135 (a proposta conversa), qualquer emissão.

**RECOMENDAÇÃO (nota 86):** a 131 cria a máquina INTEIRA e liga só o começo — os estados futuros existem no CHECK e no desenho, sem
transição que os alcance (teste: nenhum caminho de código grava um estado reservado):
```
ligados na 131:  listada → pronta | pendente(motivo) → calculando → calculada | falhou(motivo) | aguardando_agger
                 → apresentada (o comercial abriu) → enviada (o comercial clicou enviar)
reservados:      vista (cliente abriu) → em_negociacao → recalculo → aceita → emissao_pendente → emitida → registrada
                 | recusada | perdida (renovou com outro) | substituida (endosso/vencimento mudou)
```
Eventos (1 linha por transição, quem, quando, porquê) — a mesma forma de `multicalculo_eventos`. Nota 60 para "só o estado sem eventos"
(perde o porquê, que a 135 e o Kanban precisam).

---

## 7. O problema da fila — o que é do Founder

📊 Estado no banco (12/10, SELECTs acima): InfoCap `connected` nas corretoras reais = **0**; Agger da corretora `global/ativo` com senha =
**2 de 2** (a T-120/T-135 está feita de fato, embora desmarcada em TAREFAS); Agger de comercial (`membro`) = **0**; vínculos produtor↔pessoa
= **0**; membros ativos 📊 4 por corretora contra 📊 9 donos distintos por mês em cada.

| # | o que é | trava CONSTRUIR? | trava LIGAR? |
|---|---|---|---|
| T-144 | conectar a InfoCap na Resulta e na AutoFleet | não (dublê + a conexão da Amandus = banco da AutoFleet) | **sim** |
| T-154 · T-139 | Implantar a 130-B e a 131-0-A | não | **sim** |
| — | `MULTICALCULO_MOTOR_LIGADO=1` e `MULTICALCULO_HMAC_KEY` no portal-worker (D-129B-09: nasce desligado) | não | **sim** |
| T-140 | funções e "quem é quem" (o vínculo produtor↔pessoa) | não | não (tudo vai ao Agger da corretora com aviso) |
| T-141 | o Agger de cada comercial, **com o aceite novo** (Prosseguir de madrugada, §5.2) | não | para o "no Agger DELE" |
| T-136 | Resulta no Agger: HDI inválida, Mitsui ausente, Tokio sem serviço web, **licença com data 13/10/2026** (amanhã — 📊 A-PROVA §11 item 4) | não | **sim, se a licença vencer** |
| P-129C-04 | credenciais de RE da Porto, Mapfre e HDI (recusam no RE) | não | qualidade |
| decisão | Prosseguir de madrugada (revê D-131-0-05) · antecedência 10 × 15 · reajuste 15 × 10 % (P-129C-03) | sim (o BLOCO 0 mede antes) | — |

**INFERÊNCIA:** a 131 se CONSTRÓI e se prova inteira sem nada disso (dublê da InfoCap com a forma real, a conexão da Amandus, o Agger da
corretora ligado). O que o Founder faz decide só quando ela LIGA e se a renovação sai no Agger de cada comercial ou no da corretora.

---

## 8. O que ficou POR MEDIR
1. **O pico diário de renovações** por corretora e por dono (só a média de 30 dias existe). Comando: `renovacoes_cruas(hoje, hoje+90)` →
   contagem por `fimvig` e por dono, sem nome (pede InfoCap conectada ou a conexão da Amandus para a AutoFleet).
2. **O que o botão "Prosseguir" envia** (corpo/rota) — com o `cotador@` em dois contextos.
3. **3 opções simultâneas** na mesma sessão (medido: 2) e **2+ logins da mesma corretora calculando juntos** (E7 PARCIAL).
4. **O comercial vê o negócio calculado pelo `cotador@`?** (decide o valor do desvio para o Agger da corretora).
5. **A sessão fantasma:** quanto tempo a sessão sem logout bloqueia o próximo login (P-128-01; 📊 ≥ 3 h uma vez).
6. **O tempo por apólice da preparação** (`/prod_docs` em série + `/documento_anexos` + leitura 130-B) para 22 apólices.
7. **O valor de `MULTICALCULO_MOTOR_LIGADO`** no portal-worker em produção (variável do EasyPanel).
8. **O que é "MOBI"** na InfoCap da AutoFleet (💭 moto?) e os códigos 69/93/46/100 do Agger.
9. **Memória por contexto do Chromium** no portal-worker (dimensiona o teto de sessões).
