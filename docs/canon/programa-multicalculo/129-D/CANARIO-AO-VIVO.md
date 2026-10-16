# SPEC-129-D — o canário AO VIVO da vida individual (ramo 91)

> 📊 16/10/2026, 12:02–12:20 UTC (09:02–09:20 de Brasília), relógio desta máquina. Branch `spec/129-D-vida`, HEAD `09042af`.
> Operador: Opus 5.5 (subagente do gerente). Script do produto: `backend/scripts/multicalculo_canario.py --ramo 91`,
> chamado por um embrulho fora do git (`scratchpad/129d-canario/rodar.py`) que só (a) põe as 4 chaves no processo sem
> imprimir, (b) grava o log `portal_worker.multicalculo` em INFO num arquivo e (c) interrompe a execução se o motor
> registrar "ocupado por uma pessoa". Nada no produto foi editado.
> ⛔ Este documento não tem CPF, nome, login, senha nem token: só ids internos, códigos de seguradora e valores.
> 📊 = medido (com o horário e a fonte) · 💭 = inferência/estimativa.

## 0. Em uma tela
| | resultado |
|---|---|
| deu preço? | ✅ **sim, 1 seguradora**: Porto Seguro, "Porto Vida", 📊 **R$ 227,16/ano** (12 × R$ 18,93), comissão 10 % |
| conta que calculou | AutoFleet (`624cc84d…`, `uso=global`) — a da Resulta deu **sessão ocupada** e foi abandonada sem forçar (§1) |
| `calcularV2` no total | 📊 **1** (contador do robô = 1; guarda da sessão = 1) |
| seguradoras | 📊 8 da conta → **3 entraram** (Bradesco 1, HDI 4, Porto 8) · **5 saíram** pela profissão (Mapfre 3, Allianz 5, Zurich 7, Tokio 11, Yelum 12) |
| recusas | 📊 Bradesco **CREDENCIAL** (filial/sucursal) · HDI **"INSTABILIDADE"** que na verdade é **dado faltando: peso** (§4.1) |
| o leitor | leu prêmio, prêmio mensal, 21 parcelamentos, pacote, comissão. **NÃO leu o capital** nem nenhuma cobertura com valor (§3) |
| trocas de token (`login/pdocs`) | 📊 **2** (o teto do rito) |
| prazo de 5 s da licença | 📊 **disparou**: "licença: 1 leitura(s) sem resposta em 5s — segue sem ela" e o login entrou em 23,9 s |
| logout | 📊 `deslogaSessao` **201** às 12:18:04 UTC |
| negócio de teste no Agger | AutoFleet · `negocio_ref` **`fb24d27e-f343-483d-8060-45371b317bb3`** · versão 1 |
| pedido preso na fila | Resulta · pedido `14d37653-95de-43b7-b43e-1f288e387cec` · cálculo `2eecc2e5-1530-4f2e-8740-bdf58c3bfca1` · `na_fila` (§1) |

## 1. Entrada a entrada (relógio desta máquina, UTC)
| entrada | quando | o que houve | `calcularV2` | logout |
|---|---|---|---|---|
| 0 | 12:02:14 | o embrulho rodou fora de `backend/` e o `Settings` do app não achou o `.env` (`ValidationError`, 5 campos) — morreu **na 1ª importação**, antes de criar pedido ou abrir navegador | 📊 0 | não se aplica |
| 1 · Resulta (`f64ea768…`) | 12:03:01 → 12:07:05 | 📊 pedido `14d37653…` enfileirado 12:04:30. 1ª tentativa de login: `[MC] a sessão do robô … não abriu (TimeoutError)` às 12:05:44 — um timeout do Playwright (página, campo de e-mail ou botão), **antes** do POST de login (💭 se o POST tivesse saído sem desfecho, o erro seria `SessaoIndefinida`, com logout — `agger_sessao.py:403-419`). 2ª tentativa: **aviso de sessão ativa** → o produto clicou **só "Cancelar"** (`SessaoOcupada`) → `[MC] robô f64ea768… ocupado por uma pessoa — afastado por 30 min` às 12:07:03 → o embrulho **interrompeu** às 12:07:04 (não esperou os 600 s) | 📊 0 | não se aplica (não entrou) |
| 2 · AutoFleet (`624cc84d…`) | 12:10:42 → 12:18:09 | 📊 pedido `fc1d9065-b9b3-4078-a358-258e8583b6d2` enfileirado 12:11:24 · entrou em **23,9 s** (12:11:57, com o prazo de 5 s da licença disparando) · sem aviso de sessão ativa · cálculo `fechado` · logout 201 às 12:18:04 · `rc 0` | 📊 **1** | ✅ 201 |

💭 O aviso de sessão ativa da Resulta pode ser a sessão fantasma da madrugada (BLOCO 0, entrada 1, 06:51 UTC — nunca saiu) ou
uma pessoa da Resulta usando o login do robô às 09:07 de Brasília (horário comercial). Não dá para distinguir daqui. O canário
não criou essa sessão (a entrada 1 não chegou ao POST de login).

### O que ficou da entrada 1 (Resulta) — o pedido de teste PRESO na fila
- 📊 SELECT 12:19:54 UTC: cálculo `2eecc2e5-1530-4f2e-8740-bdf58c3bfca1` · `status na_fila` · `tentativas 2` · `dono null` ·
  `conta_exigida_id f64ea768…` · `negocio_ref null` · 0 eventos · 0 ofertas · `expira_em 12:34:29 UTC`.
- 📊 A conta da Resulta ficou `robo_estado = ocupada` até **12:37:03 UTC** (o próprio motor, 30 min); depois volta a `ativo`.
- Risco: nenhum. O motor do serviço ignora pedido `origem = teste` sem o canário ligado (`motor.py:620/693`), e o cálculo já
  passou da validade. Nada saiu para o Agger da Resulta. 🧑 O Founder pode apagar o pedido se quiser; não precisa.

## 2. O resultado da AutoFleet
| | valor |
|---|---|
| pedido de teste | "TESTE AUTOBROKERS", CPF GERADO (semente fixa do script), 10/05/1985, M, casado(a), CEP 89201-000, não fumante, renda 8.000, sem esporte radical, "Analista de sistemas", capital de Morte R$ 100.000, só a opção `padrao`, comissão **10 % explícita** (`--comissao 10`; as contas têm `percComissaoVida` 0) |
| seguradoras da conta | 📊 8 (as mesmas do BLOCO 0 §5.1) |
| **entraram** | 📊 3: **Bradesco 1** (não exige profissão) · **HDI 4** ("Analista de sistemas", igual) · **Porto 8** ("ANALISTA DE SISTEMAS", igual na caixa) |
| **saíram antes do cálculo** | 📊 5, todas com o evento `sem_atividade_compativel` e o motivo *"nenhuma profissão da lista desta seguradora é igual à do pedido (busca do Agger)"*: **Mapfre 3** (busca vazia no BLOCO 0) · **Allianz 5 · Zurich 7 · Tokio 11 · Yelum 12** (a única opção era "Analista de sistemas de automação" — a regra de igualdade da D-129D-06 funcionou como desenhada) |
| saíram pela comissão | 📊 **0** (a comissão de 10 % foi a todas) |
| oferta | 📊 **Porto Seguro · pacote "Porto Vida" · `premio_total` R$ 227,16 · `premio_mensal` R$ 18,93** · `comissao_percentual` 10 · `tem_pdf true` · `pdf_path null` |
| parcelamentos lidos | 📊 21 linhas em 3 formas de pagamento (`tipo_pagamento` 1, 2 e 3): à vista 📊 **R$ 204,44** (tipo 1) ou **R$ 215,80** (tipos 2 e 3); 12 × **R$ 18,93** (tipos 2 e 3); tipo 1 vai até 11 × R$ 19,61 |
| recusas | 📊 **Bradesco · CREDENCIAL** — *"A filial/sucursal deve ser informada corretamente. Confira suas credenciais de acesso."* (t_s 96,1 s) · **HDI · INSTABILIDADE** — *"Peso deve ser informado corretamente. Houve uma instabilidade ao realizar o cálculo nesta seguradora, tente novamente em breve."* (t_s 2,9 s) |
| tempos (`t_s`, relógio do robô a partir do POST) | 📊 HDI recusou em 2,9 s · Bradesco em 96,1 s · **a oferta da Porto em 339,1 s (5 min 39 s)** · conjunto fechado em 339,1 s. Do enfileirar ao logout: 📊 6 min 40 s (12:11:24 → 12:18:04) |
| licença do Agger (evento `licenca_agger`) | 📊 `dataLimiteCalculo = 2026-10-27` · **11 dias para o limite** (conta da AutoFleet) |
| guarda | 📊 31 barradas (telemetria de terceiros: google-analytics, clarity, refiner, mpulse e `json.agger.com.br/json/login-V2.json`) |
| varredura das linhas do pedido (senha, token, url, o CPF de teste, fumante, renda) | 📊 **0** |

⚠️ Os relógios: o banco está 📊 ~75 s **atrás** desta máquina (o pedido tem `criado_em` 12:10:09 no banco e foi enfileirado
às 12:11:24 aqui; o evento da HDI tem `criado_em` 12:11:07 no banco com `t_s` 2,9). Os tempos acima usam `t_s` ou só o
relógio desta máquina. Não se misturam os dois.

## 3. O que o leitor leu, e o que NÃO conseguiu ler
**Leu certo** (📊 linha `multicalculo_ofertas` `a96ea051-bb58-49d3-a2f1-404e98efcb81`): seguradora e código, pacote
("Porto Vida", `tipo_de_pacote 0`), `premio_total`, `premio_mensal`, os 21 parcelamentos com primeira e demais parcelas,
a comissão e o `tem_pdf`. A recusa e o motivo das duas outras foram gravados por inteiro.

**NÃO leu:**
1. 🔴 **O capital.** As coberturas gravadas da oferta são só 📊 `{"DIT": "Não Contratada", "isDoencasGravesGrupo": "Selecione"}`.
   Não há `isAppMorte` (nem Morte acidental, IPA, DIH, funeral). O leitor procura `resultados[].coberturas.<chave do pedido>`
   (`leitor_agger.py:179-201`, a lista `COBERTURAS_DA_OFERTA_VIDA`, que o próprio código marca 💭 "o canário da V3 confere os
   rótulos reais"). A Porto **não ecoou o capital nessas chaves**. O corretor vê o preço sem ver de quanto é o seguro.
2. 🔴 **"Selecione" e "Não Contratada" gravados como cobertura.** "Selecione" é o texto vazio da caixa de seleção da tela, não
   um valor. Hoje ele vai para a oferta como se fosse cobertura.
3. **Os rótulos reais da resposta de vida com preço continuam sem gravação.** O canário roda o robô do produto, que não guarda
   a resposta crua. Para saber onde a Porto põe o capital, é preciso gravar UMA resposta com preço, saneada, como fixture
   `vida_resultado_com_preco.json`. Isso não estava no roteiro deste canário (1 cálculo, sem gravador).
4. 💭 **Qual número é "o preço".** `premio_total` 227,16 é exatamente 12 × 18,93. O à vista é menor (204,44 ou 215,80, conforme
   a forma de pagamento). Não dá para saber, sem a resposta crua, se 227,16 é o `premio` da Porto ou uma conta. Se a tela
   mostrar "R$ 227,16" como preço anual e o corretor fechar à vista, a diferença é de 📊 até R$ 22,72.
5. **O PDF.** `tem_pdf true`, `pdf_path null`. O log diz `pdfs: 0 não copiados {'so_nome': 1}`: veio só o nome do arquivo.
   💭 Este processo não tem as variáveis do MinIO, então não se sabe se no serviço o PDF chegaria (o mesmo da 129-C §3.7).

## 4. O que divergiu do que os testes previam
1. 🔴 **HDI: a família da recusa está errada.** A mensagem começa com *"Peso deve ser informado corretamente"* (falta dado) e
   termina com *"Houve uma instabilidade…"*. O leitor casou a regra de INSTABILIDADE (`leitor_agger.py:334`,
   `instabilidade|tente novamente mais tarde`), porque nenhuma regra de DADO cobre "deve ser informado" (a de
   `leitor_agger.py:350` só pega o plural "devem ser preenchidos"). INSTABILIDADE convida a repetir o mesmo pedido, que vai
   falhar de novo. É o mesmo padrão já consertado para os vidros (o comentário em `leitor_agger.py:329-330`).
   E a causa de fundo: **a HDI exige o peso** (📊 o corpo do BLOCO 0 manda `altura null, peso null`). O pedido de vida não
   coleta peso nem altura, então a HDI vai recusar todo pedido de vida. 💭 Ou o pedido passa a pedir peso e altura, ou a
   HDI sai antes do cálculo com "falta dado: peso", como a profissão.
2. **Bradesco: credencial de vida.** *"A filial/sucursal deve ser informada corretamente"*, com a família CREDENCIAL certa.
   🧑 É configuração da conta da AutoFleet no Agger (Configurações → Seguradoras → Bradesco → filial/sucursal), não do
   produto. No BLOCO 0 a Bradesco aparecia `credenciaisValidas`: a validação geral passa, a de vida não.
3. **A profissão derrubou 5 de 8.** A regra de igualdade funcionou como decidido (nenhum código errado foi mandado), mas só
   sobraram 2 seguradoras com profissão (HDI e Porto) e 1 sem (Bradesco). Com a HDI recusando por peso e a Bradesco por
   credencial, sobrou **uma** oferta. 💭 Para "Analista de sistemas", 4 seguradoras só têm "Analista de sistemas de
   automação". Ou o corretor escolhe a profissão por seguradora, ou o pedido de teste usa uma profissão mais comum.
4. **A "instabilidade" das 7 da madrugada não se repetiu** às 12:12 UTC: a Porto cotou e as outras 2 deram motivos reais. 💭 A
   recusa idêntica nas 7 do BLOCO 0 era a hora (madrugada) ou o Agger, não o corpo.
5. **O prazo de 5 s da licença disparou de verdade** na 1ª vez que rodou ao vivo: 📊 1 leitura sem resposta, o login seguiu e
   entrou em 23,9 s. Sem ele, pelo BLOCO 0, a sessão ficaria presa 16–20 min.
6. **O primeiro login da Resulta deu `TimeoutError`** (📊 12:05:44). 💭 Página lenta na hora. O motor tratou como "não abriu" e
   tentou de novo, como desenhado.

## 5. O fim
- `calcularV2` no total desta tarefa: 📊 **1** (AutoFleet). Resulta: 📊 0. Nenhuma emissão, nenhum "Salvar", nada a cliente.
- Logout: 📊 AutoFleet `deslogaSessao` **201** às 12:18:04 UTC. Resulta: não entrou, logo não há sessão do canário.
- Navegadores do robô abertos no fim: 📊 0 (processos do Playwright Chromium).
- Contas, 📊 SELECT 12:19:54 UTC: AutoFleet `ativo`, sem dono · Resulta `ocupada` até 12:37:03 (o motor, pela `SessaoOcupada`).
- O arquivo temporário de chaves (`scratchpad/canario.env`) foi **apagado** no fim. As saídas brutas ficam fora do git, em
  `scratchpad/129d-canario/` (sem valores de chave: só "presente").

### Os pedidos de teste criados (origem `teste`)
| corretora | `multicalculo_pedidos.id` | `multicalculo_calculos.id` | status | negócio no Agger (`negocio_ref`) |
|---|---|---|---|---|
| AutoFleet | `fc1d9065-b9b3-4078-a358-258e8583b6d2` | `04634654-5257-4d86-a94a-af0f40a9cf9c` | `fechado` | **`fb24d27e-f343-483d-8060-45371b317bb3`** (versão 1, segurado "TESTE AUTOBROKERS") |
| Resulta | `14d37653-95de-43b7-b43e-1f288e387cec` | `2eecc2e5-1530-4f2e-8740-bdf58c3bfca1` | **`na_fila` (preso, expirado 12:34:29)** | nenhum |

Eventos 📊 445–450 e 456–459 (AutoFleet). Oferta 📊 1.

## 6. RECOMENDAÇÃO ao gerente (sem consertar nada aqui)
1. **O capital da oferta de vida** (`backend/portal_worker/multicalculo/leitor_agger.py`, `COBERTURAS_DA_OFERTA_VIDA` e a
   leitura em `:556-613`): gravar uma resposta com preço, saneada, e mapear onde a Porto põe o capital. E não gravar
   "Selecione" como cobertura.
2. **A família "deve ser informado(a) corretamente" → DADO** (`leitor_agger.py`, antes da regra de INSTABILIDADE da `:334`), com
   o teste da mensagem real da HDI. ⚠️ A mensagem da Bradesco tem a mesma frase mais "credenciais": a regra de CREDENCIAL tem de
   continuar vencendo.
3. **Peso e altura no pedido de vida** (`backend/portal_worker/multicalculo/contrato.py`, o contrato de vida perto da `:661`, e
   `backend/app/services/multicalculo/pedido.py`), ou a HDI sai antes do cálculo com "falta dado: peso". É decisão de produto.
4. 🧑 **Bradesco filial/sucursal** na conta da AutoFleet (Founder ou corretora).
5. 🧑 **A licença do Agger da AutoFleet vence o cálculo em 27/10/2026** (📊 11 dias).
6. 💭 Qual prêmio mostrar (anual de 12 × mensal ou à vista), e o PDF que veio só com o nome.
