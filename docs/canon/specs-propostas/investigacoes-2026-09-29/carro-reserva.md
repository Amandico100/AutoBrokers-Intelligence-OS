# Carro reserva em todas as seguradoras — investigação (só leitura) · 29/09/2026 · main 1fb9db1

**Fontes e comandos.** Banco: `observed_events` lido inteiro por `regua_motor.eventos_observados()` (só SELECT) e salvo no scratchpad → 📊 33.628 eventos, 689 sessões (`dump.py`). Buscas por texto normalizado (sem acento) em `text` + `interactive`, nas duas direções (`in` = URA/central, `out` = nós) com `a1.py`, `a2.py`, `a3.py`; fluxos com `flow.py`/`show2.py`; acervo com um script inline sobre `backend/tests/corpus/telas_reais/*.jsonl`. Nada foi gravado no repo nem no banco; nenhuma mensagem saiu.

## Resposta curta
Não: o carro reserva **aparece** em 8 das 9 seguradoras, mas só **3 o resolvem dentro do WhatsApp** (Yelum, Mapfre e, parcialmente, Zurich). Tokio e Azul **mandam um link**. Allianz e Bradesco **mandam ligar**. A HDI **não oferece** no número que observamos. Porto e Zurich têm a opção no menu, mas ninguém a escolheu. **Isso muda o desenho:** não existe "um corredor de carro reserva". São quatro formas diferentes.

## 1. Por seguradora: banco × acervo
| seguradora | sessões em que a URA fala de carro reserva 📊 | sessões em que **pedimos** carro reserva 📊 | acervo (etiqueta `carro_reserva`) 📊 | canal real |
|---|---|---|---|---|
| **yelum** | 13 | **11** (9 pedidos + 1 consulta de status + 1 desistência no menu) | 5 sessões / 91 telas | **WhatsApp**, formulário da URA → "em análise, 3 h úteis" |
| **mapfre** | 3 | **1** (25/08/2025) | 1 / 14 | **WhatsApp**: URA → atendente → transferida para a Localiza no mesmo chat |
| **tokio** | 3 | **2** | 2 / 21 | **LINK**: WhatsApp de outro número (2025) · link de autoatendimento da Localiza com token + WhatsApp (02/2026) |
| **azul** | 16 (só o menu) | **2** (02 e 03/2026) | 0 (o menu aparece em 10 sessões) | **LINK** `porto.vc/carroreserva` ("fale com um especialista") |
| **porto** | 28 (só o menu) | **0** | 0 (o menu aparece em 15) | a opção existe em *Sinistro de automóvel → Carro reserva*; ninguém a escolheu |
| **zurich** | 9 (menu) | **1** (dentro da abertura de sinistro, "Carro e cobertura") | 0 (o menu aparece em 4) | WhatsApp: "solicite um carro reserva **após abrir o sinistro**"; não se sabe o que vem depois |
| **bradesco** | 14 (menu) | **2** (pedidos digitados à central humana, 2025) | 0 (o menu aparece em 8) | **TELEFONE**: 4004-2757 / 0800 701 2757, opções 2 e 6; corretor → central do corretor. A opção nova do menu (*Serviços de assistência → Carro reserva*) nunca foi escolhida |
| **allianz** | 1 | **3** perguntas à assistência humana (Mondial) | 0 | **TELEFONE**: "por sinistro, ligar 4090-1110 / 0800 777 7243 — SOMENTE POR LIGAÇÃO, SEM WHATSAPP" (📊 31/03/2026). Por pane: "sim, após a entrega do veículo na oficina" |
| **hdi** | **0** em 3.135 eventos | 0 | 0 | o número observado só faz assistência (guincho e residência). O canal do carro reserva é desconhecido |

⚠️ No acervo, os acertos de texto em azul, porto, bradesco e zurich são **só o cardápio**. Nenhuma conversa real de carro reserva dessas quatro está no acervo. O acervo tem 5 das 11 sessões da Yelum.

## 2. Os fluxos (sem dados pessoais)

**YELUM — versão A** (menu *Segurado e Terceiros → YELUM → "4" → lista "Voucher Mob/Carro Res…" → "Carro Reserva"*). O que respondemos em cada tela:
1. Informe seu nome → **nome da atendente** (o de quem pede, não o do segurado)
2. Motivo: 1 Sinistro · 2 Pane mecânica · 3 Reparo em outra seguradora · 4 Alteração de condutor → "1" (📊 9 de 9)
3. Nome de quem fará a retirada → `{NOME}` do condutor
4. CPF de quem retira, **sem ponto e traço** → 📊 em 4 de 9 sessões a URA recusou o CPF formatado e pediu de novo
5. Cidade de retirada → `{CIDADE}`. *Esta tela e a 6 não existiam em 10/2025.*
6. Data e horário desejados → formatos livres ("dd/mm", "dd/mm/aaaa às hh:mm")
7. Número da apólice (só números) → `{APOLICE}`
8. Placa → `{PLACA}`
9. Número do sinistro (só números) → `{SINISTRO}`
10. Telefone de quem retira → `{TEL}`
11. Quantidade de diárias → **15** (📊 5 vezes), 11 (1), 35 (1)
12. **Fim:** *"O processo está em análise e o prazo para retorno é de até 3 horas úteis."*

Resultado: 📊 7 sessões chegaram ao fim; 1 recebeu *"nenhum especialista disponível, retorne das 09h às 17h (seg–sex)"* às 20h, **depois** de todos os dados digitados; 1 parou na placa; 1 foi desistência. 📊 Em 6 das 7 que chegaram ao fim, **a confirmação nunca voltou no WhatsApp observado**: as sessões seguintes são outros atendimentos. Inferência: ela chega por telefone ou SMS a quem retira.

**YELUM — versão B** (📊 1 sessão, 24/08/2026: *Assistência → "1" → "8" → botões Voucher/Carro Reserva*). Muda o seguinte:
- o motivo vem em lista e inclui *"Reparo outra Seguradora"*;
- aparece a pergunta *"Houve a abertura do sinistro? Sim/Não"*;
- aparece a exigência *"é obrigatório o envio do Orçamento de autorização de reparos… em PDF"* (nesse ramo);
- o analista humano entra no mesmo chat e pergunta o horário;
- ele oferece um **upgrade pago** → respondemos *"ele quer o normal mesmo"*.

Fim: **reserva confirmada no chat**, com localizador, grupo MANUAL, 15 diárias, agência Localiza e regras de retirada: CNH original, **cartão de crédito no nome do condutor com limite para pré-autorização**, tolerância de 1 h e diárias sem fracionamento.

**MAPFRE** (📊 1 sessão, 08/2025): *Carro e Moto → Carro reserva → [Solicitar / Liberar / Agendar retirada / Alterar / Cancelar] → Solicitar*. A URA pede placa, CPF do titular e data de nascimento, e depois entrega um protocolo e **transfere para uma pessoa**. A atendente da Mapfre pergunta se somos o segurado ("sou corretor"), código e CPF, e **transfere para a Localiza no mesmo chat**. A Localiza pede, em uma mensagem só:
- cidade/agência e data/hora da retirada;
- nome e CPF do condutor;
- "somente esta pessoa irá dirigir?";
- celular;
- "possui CNH original e válida?";
- **"cartão de crédito em nome próprio com limite mínimo de R$ 500 para pré-autorização?"**

A Localiza oferece 15 diárias de carro básico 1.0 e o upgrade (→ "pode seguir com o básico"). **Fim: RESERVA CONFIRMADA com localizador.** ⚠️ Em 2026 o menu da Mapfre virou texto livre ("Conta pra mim, sobre qual assunto…"), então o fluxo de 2025 pode estar vencido.

**TOKIO** (📊 2): *Outros serviços → Carro reserva →* link. Em 08/2025 era "clique para falar com um atendente" (outro WhatsApp). Em 02/2026 passou a ser o **autoatendimento da Localiza com token** + esse WhatsApp. Fim: fora do canal.

**AZUL** (📊 2): *Carro reserva →* "Fale com um dos nossos especialistas" + `porto.vc/carroreserva`. Fim: fora do canal.

**ZURICH** (📊 1): na abertura de sinistro (colisão), a URA avisa *"Você tem direito ao carro reserva"* e pergunta **Carro e cobertura / Apenas o carro reserva / Apenas cobertura** → "Carro e cobertura". O processo foi aberto, mas **nenhuma instrução de carro reserva apareceu depois** no chat. O menu diz *"você receberá as orientações após o acionamento"*.

**ALLIANZ / BRADESCO:** só telefone (citações na tabela). Nenhuma chegou ao fim pelo WhatsApp.

## 3. Telas que não se deduzem do relato do segurado
| tela | respostas prováveis (nota 0–100) |
|---|---|
| Nome de quem pede (Yelum) | nome da atendente/corretora **95** · nome do segurado 20 |
| Motivo (Yelum) | "Houve sinistro" quando há sinistro aberto **90** · "Pane" só com a regra do corretor 40 · "Reparo outra seguradora" → **pessoa** (exige PDF do orçamento) 90 |
| Condutor que retira (nome + CPF) | o próprio segurado **65**, mas é preciso perguntar: 📊 em 7 de 9 foi outra pessoa ou não deu para saber · outro condutor 35 |
| CPF sem pontuação | tirar pontos e traço **100** (regra técnica, 📊 4 recusas) |
| Número do sinistro | do caso/sinistro já registrado **80** · sem número → não pedir, vai para pessoa 90 |
| Apólice e placa | da base da corretora **95** |
| Telefone de quem retira | celular do condutor **80** |
| Cidade/agência de retirada | cidade do segurado ou da oficina **55**: só o segurado sabe |
| Data e hora de retirada | "amanhã 14h" **30** · perguntar ao segurado **90** |
| Quantidade de diárias | máximo contratado na apólice **75** · "15" fixo **55** (📊 5 de 7) · valor pedido pelo segurado 40 |
| Categoria / upgrade pago | "básico, sem upgrade" **95** (upgrade é cobrança ao segurado → pessoa) |
| "Somente esta pessoa dirige?" (Mapfre) | "sim" **60** · perguntar 80 |
| CNH original e válida? | "sim" **50** → perguntar 85 |
| **Cartão de crédito no nome do condutor, limite ≥ R$ 500** | **só o segurado sabe: 100 % perguntar**; o agente nunca afirma por ele |

## 4. Até 5 perguntas para a atendente de auto
1. **Diárias:** pedimos sempre o máximo da apólice (onde consulto: 7, 15 ou 30?) ou o que o segurado disser? Carro reserva **por pane** está coberto nos planos que vocês vendem?
2. **Quando pedir:** só depois de o sinistro estar aberto e a oficina liberar o reparo (Yelum e Allianz exigem), ou já junto com a abertura do sinistro (Zurich "Carro e cobertura")?
3. **Cartão de crédito e CNH:** a corretora sempre pergunta ao segurado antes? Se ele não tiver cartão com limite, qual é o caminho (a corretora banca a caução, outro condutor, desiste)?
4. **Yelum "em análise 3 h úteis":** por onde chega a confirmação (SMS ou ligação ao condutor? e-mail à corretora?), e quem avisa o segurado?
5. **Allianz, Bradesco e HDI:** vocês pedem carro reserva por telefone, pelo WhatsApp/portal do corretor (Bradesco tem "WhatsApp Corretor") ou outro canal? E a HDI, por onde?

## 5. Recomendação por rota
| rota | decisão | nota |
|---|---|---|
| **yelum/auto/carro_reserva** | **atende sozinho** até "em análise", com três travas: sinistro com número, condutor e diárias confirmados, **horário 9h–17h em dias úteis**. As duas versões de menu (A e B) precisam de passo. O ramo "reparo em outra seguradora" (PDF) e o upgrade vão para pessoa. O acompanhamento é uma fase, não uma confirmação | **78** |
| **tokio/auto/carro_reserva** | **atende sozinho** o trecho curto: navegar, capturar o link da Localiza e entregar ao segurado com a lista "CNH + cartão". A reserva em si fica com o segurado | **75** |
| **azul/auto/carro_reserva** | igual à Tokio: capturar `porto.vc/carroreserva` e entregar | **72** |
| **mapfre/auto/carro_reserva** | **acionamento real**: o fluxo de 2025 é humano + Localiza em texto livre, e o menu mudou em 2026. Depois disso, provavelmente o agente conduz e uma pessoa confirma o cartão | **70** |
| **porto/auto/carro_reserva** | **acionamento real exploratório** (só abrir a opção *Sinistro de automóvel → Carro reserva*); inferência de 60 que dá o mesmo link da Azul | **80** |
| **zurich/auto/carro_reserva** | **acionamento real** da opção "Carro reserva" do menu (só depois de sinistro aberto) | **72** |
| **bradesco/auto/carro_reserva** | **acionamento real exploratório** da opção nova *Serviços de assistência → Carro reserva*. Se der telefone → pessoa | **70** |
| **allianz/auto/carro_reserva** | **pessoa por desenho**: "somente por ligação, sem WhatsApp" | **90** |
| **hdi/auto/carro_reserva** | **pessoa por desenho** até a atendente de auto indicar o canal (pergunta 5) | **85** |

**Fato × inferência.**
- FATO: todas as contagens 📊 acima.
- INFERÊNCIA: a confirmação da Yelum chega fora do chat; o Porto dá o mesmo link da Azul; o fluxo da Mapfre de 2025 está vencido.
- RECOMENDAÇÃO: a tabela da seção 5.

O cartão de crédito da caução aparece em Yelum e Mapfre (e é implícito no autoatendimento da Localiza). É a única tela que **nunca** pode ser respondida pelo agente sem perguntar ao segurado.
