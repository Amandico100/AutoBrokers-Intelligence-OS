# A prova do Agger — o que o motor precisa saber, medido

> SPEC-128 · 04/10/2026 · medição AO VIVO das 17:16 às 19:12 (relógio da máquina) com o login da usuária de cada corretora nas contas **Resulta**
> e **AutoFleet** (autorização: D-MC-23 + Founder 04/10; o relógio da máquina está 📊 ~87 s adiantado em relação ao servidor do Agger), mais as 3 gravações de 18/09. Toda escrita no Agger passou por um
> **captador** de lista branca (§7). 📊 **16 cálculos** de 25 permitidos (`grep -c '"m": "POST".*calcularV2' raw/*.jsonl` → 15 + 1).
> Fontes no rascunho do gerente: `MEDICOES.md`, `versoes_auto.json` (227 versões), `calculos_medidos.json`, `alavancas.json`,
> `e3_validacao.json`, `form_auto.json`, `form_resid.json`, `g7.json`. Fixtures saneadas na main: `backend/tests/fixtures/agger/`.

## 1. Em uma tela

| | o que se achava (plano §1.2) | o que se mediu |
|---|---|---|
| tempo do cálculo | fecha em 413–420 s (n = 2) | 📊 **1ª oferta 6 s, 80 % em 25–27 s, fecha em 64 s** (mediana dos 201 de 227 cálculos que fecharam; **26 nunca fecharam**); a cauda (p90 406 s) é 1–2 seguradoras lentas |
| volume | desconhecido | 📊 AutoFleet **8,5 cálculos por dia útil** (1 pessoa); Resulta ≈ 0 de automóvel no Agger |
| ajuste mais pedido | preço (D-MC-14) | 📊 o que mais muda entre versões é **franquia (71), desconto (54), comissão (33)** em 137 recálculos |
| 2 opções num cálculo | hipótese (E20) | 📊 **não**: 1 pacote por cálculo → a proposta de 2 opções custa 2 cálculos (o plano é ilimitado) |
| renovação pela InfoCap | hipótese | 📊 a InfoCap traz veículo e segurado; **faltam** condutor, questionário, CEP de pernoite e os valores de RCF/APP |
| recálculo | pela tela | 📊 reenviar o corpo do pedido com 1 campo trocado cria versão válida (n = 11) |

## 2. Tabela de capacidade

| grandeza | valor | como |
|---|---|---|
| cálculos AUTO por dia útil, AutoFleet | 📊 média 8,5 · mediana 9 · p90 14 · máx 15 (24 dias úteis, 01/09–02/10) + 23 em fins de semana | `analisa_versoes.py` sobre 227 versões |
| cálculos AUTO por dia útil, Resulta | 📊 0,05 (9 versões em 181 dias úteis) | idem |
| recálculos por negócio | 📊 2,52 versões por negócio; 66 de 90 (73 %) têm ≥ 2 | idem |
| 1ª oferta · 80 % · fecha (nossos 16) | 📊 mediana 6 s · 25 s · 37,5 s (máx 11 · 29 · 51 s); 2 de 16 nunca fecharam (seguradora calada > 5–9 min) | `calculos_medidos.json` |
| 1ª oferta · 80 % · fecha (histórico) | 📊 6 s · 27 s · 64 s (p90 13 · 49–51 · 406 s); 26 de 227 nunca fecharam | `analisa_versoes.py` |
| relógio de parede de um cálculo | 📊 ~45 s pelo relógio do servidor; 55 s pela máquina com consulta a cada 10 s (n = 13) | `lev.py` · laudo da lente |
| ofertas por cálculo | 📊 16,2 ofertas em média (mediana 18; máx 30) de 9 seguradoras (mediana; máx 15) | idem |
| simultaneidade na mesma sessão | 📊 2 cálculos disparados juntos (o servidor os registrou a menos de 1 s um do outro): os 2 fecharam 16/16 | E7 |
| licenças | 📊 Resulta 5 · AutoFleet 8 | `cfg/assinatura-aggilizador` |
| cota de cálculos | 📊 "Cálculos ilimitados em 14 ramos" | tela "Meu plano" |

**INFERÊNCIA (para a 129-B):** 💭 um login de robô a ~1 cálculo por minuto faz ~50 cálculos por hora; o volume medido da AutoFleet
inteira (8,5/dia) cabe em minutos. O gargalo não é o Agger: é a cauda de 1–2 seguradoras lentas — o motor entrega aos poucos e
fecha por tempo, nunca espera a última.

## 3. As perguntas, uma a uma

### E0 — volume por dia em cada corretora
📊 AutoFleet: 90 negócios AUTO → 227 cálculos (versões), 8,5 por dia útil (mediana 9, p90 14, máx 15), pico às 11h e 14h, 1 usuária.
Resulta: 8 negócios AUTO e 9 cálculos em 365 dias (841 negócios no total: a Resulta usa o Agger para outros ramos).
Comando: `analisa_versoes.py` sobre `GET pdocs/calculo/cotacao/versoes/{idIntegracao}` de todos os AUTO (17:44).

### E1 — entrar sem derrubar ninguém; quanto dura a sessão
📊 4 logins (17:16–17:45), nunca apareceu o aviso de sessão ativa; formulário de login em 5–22 s, painel em 10–52 s. Token do motor
(JWT) com 10.800 s = **3,0 h** (`iat`/`expires`), e um campo `dataLimiteCalculo` = fim da assinatura. Saída limpa por
`POST usuario/deslogaSessao` (201 às 19:11:56 e 19:12:07). Comando: `sessao.abrir` / decodificação só das datas do JWT.

### E2 — renovação a partir da InfoCap
📊 A InfoCap (`/itens`, `/cliente`, `/documento`; n = 1 apólice por conta) traz veículo, placa, chassi, anos, FIPE, % FIPE, bônus,
nascimento, sexo, CEP. **Faltam** estado civil (vazio), condutor principal e tempo de habilitação, todo o questionário (garagem,
uso, km, jovem condutor), CEP de pernoite e os valores de RCF/APP (`impseg` vazio). O Agger completa sozinho o veículo pela placa
(9,5 s) e nome/nascimento/sexo/estado civil pelo CPF; o questionário vem com padrões da tela.
**Frequência:** 📊 a AutoFleet tem 438 renovações AUTO nos próximos 60 dias e **0** têm negócio no Agger (controle: o mesmo
cruzamento acha 2 de 3 na Resulta). A AutoFleet usa o Agger para negócio novo, não para renovar a carteira. Comando:
`infocap_itens.py` + `infocap_e2.py` (cruzamento por hash de CPF, só contagem). 1 cálculo.

### E3 — seguro novo do zero
📊 Calcular com o formulário vazio: nenhum pedido sai; a tela recusa **16 campos** (CPF, nome, nascimento, sexo, estado civil, CEP,
ano de fabricação, FIPE, combustível, CEP de pernoite + 5 do condutor = 📊 15 com o formulário vazio) **e** o tempo de habilitação, que a tela exige depois, no fluxo. Fluxo: CPF → placa → habilitação →
Calcular; resultado em 36 s, 18 ofertas de 10 seguradoras. Comando: `e3_validacao.json` (Resulta, 18:59). Marcado no contrato
(`contrato.py`, `obrigatorio`).

### E4 — CPF
📊 CPF com dígito inválido → "O documento informado é inválido.". A busca de dados pelo CPF (`GET api-prod/cadastros/cliente`)
devolveu `false` em 4 de 5 chamadas e depois os dados (nome, nascimento, sexo, estado civil) — **instável**. O Agger avisa
"CPF JÁ COTADO" (`seguradoCotadoRecentemente`) até para cotações que a lista não mostra: esse sinal **nunca** chega à pessoa
(plano §1.2). Comando: tela + `raw/autofleet.jsonl`.

### E5 — quanto cada alavanca baixa o preço
📊 2 perfis na AutoFleet (comissão-base 15 %), uma alavanca por vez, com recálculo de controle (as repetições puras deram 18 de 18
com 0,0 %; a **Mapfre deriva com o tempo — +16 % entre a 1ª e a 9ª versão** — e fica fora). Variação do prêmio:

| alavanca | faixa (por seguradora) | observação |
|---|---|---|
| comissão 15 → 10 % | **−1,5 a −7,6 %** (−5,5/−5,6 em 6 de 9 seguradoras; Youse −1,5, Zurich −3 a −4, Tokio −7,6) | Porto e Azul **ignoram** a comissão enviada (0,0 %); a Itaú ficou indeterminada (o mesmo recálculo mudou o desconto dela) |
| desconto 10–15 % → 0 | **+5,9 a +17,6 %** | é a alavanca que Porto, Itaú e Azul obedecem |
| vidros completo → sem | **−2,2 a −27,6 %** | a Allianz recusa sem vidros |
| franquia reduzida → normal | **−2,5 a −18,1 %** | medido por quem calculou; a lente não achou par que mude SÓ isto (P-128-08) |
| carro reserva 15 dias → sem | −1,1 a −7,1 % | idem |
| assistência completa → básica | 0 a −7,6 % | idem |
| FIPE 100 → 90 % | 0 a −6,7 % | |

Tempo de um ajuste isolado: 📊 1ª oferta 4–10 s, fecha 30–51 s (n = 11). Comando: `alavancas.py` (`alavancas.json`).

### E6 — vários pacotes por cálculo
📊 Cada cálculo traz várias ofertas por seguradora (16,2 em média, de 9 seguradoras); "pacote" no sentido de 2 configurações de cobertura
no mesmo cálculo não existe (E20). Gravações: 22 de 12 e 21 de 11 (G3 reproduz).

### E7 — simultaneidade
📊 2 cálculos disparados juntos na mesma sessão (tela + API; o servidor os registrou a menos de 1 s um do outro) fecharam 16/16 em 45 e 44 s; 2 recálculos simultâneos
no mesmo negócio também (versões distintas, sem colisão). Comando: `calculos_medidos.json` (18:42:38 e 18:46:22).
**PARCIAL:** 2 abas pela tela não foram medidas (o captador barrou a troca de token da 2ª aba); 2 usuários robô da mesma conta
exigem um 2º login, que não existe. Consequência: a reserva de hoje (um trabalho por login, `worker.py:1716-1725`) é conservadora
— a sessão aceita 2 cálculos; mudar a reserva espera o 2º login (P-128-02).

### E8 — o preço difere entre corretoras
📊 O mesmo perfil nas duas contas não é comparável: o pacote "Prata" de cada conta é diferente (Resulta: RCF/APP zerados, franquia
normal, vidros básicos, reserva 7 dias; AutoFleet: RCF 200/200/20 mil, APP 5 mil, franquia reduzida, vidros completos, reserva 15).
Por isso a Resulta saiu mais barata e duas seguradoras recusaram ("DMO obrigatória"). **O motor manda as coberturas explícitas,
nunca o pacote da conta** (D-128-05).

### E9 — tempos com n ≥ 10
📊 227 versões, 3.537 tempos: a seguradora responde em 17 s (mediana; p90 50 s). Mais lentas: Bradesco p90 159 s, Aliro p90 114 s,
Yelum p90 110 s. 82 de 3.619 pedidos seguradora × versão nunca voltaram. Comando: `analisa_versoes.py`.

### E10 — famílias de resposta
📊 Oferta · credencial (Bradesco "Login ou senha incorreta" em 39 cálculos da AutoFleet) · permissão · aceitação (Sura "valor abaixo
do mínimo" 165×) · comercial (Mitsui "desconto × comissão fora da abrangência" 76×) · instabilidade · **dado** (família nova,
D-128-02: "calcule como renovação", "DMO obrigatória", "CEP inválido"). O leitor classifica **toda** resposta das fixtures (G5): os 12
cálculos ao vivo com rodadas gravadas (os 4 recálculos feitos pela API não foram consultados rodada a rodada) e as versões das gravações. Comando: `pytest backend/tests/test_contrato_do_calculo_agger.py`.

### E11 — o que fica gravado
📊 Cada cálculo é uma versão nova do mesmo negócio (v1…v10). O 1º pedido vai com os 4 identificadores nulos e a resposta devolve
`{idIntegracao, versao}`; o recálculo leva os 4 preenchidos. Os negócios ficam na conta, não no login.

### E12 — o PDF
📊 "Imprimir" abre "Personalizar impressão" (exibir comissão, observação por oferta, Salvar/E-mail/WhatsApp/Imprimir) e chama
`POST pdocs/calculo/print`, barrado pelo captador → **formato final não medido** (P-128-03). O PDF da **seguradora** existe por
oferta (`quotation-files.aggilizador.com.br`) em 2.594 de 3.677 ofertas (Youse, Azul por Assinatura e Sura: nunca). Comando: `analisa_resultados.py`.

### E13 — o formulário de residencial
📊 Mapeado sem calcular (`form_resid.json`): segurado, endereço, imóvel, vigência e renovação, assistência, verba, valor de novo e
17 limites obrigatórios; 10 seguradoras na AutoFleet, comissão obrigatória por seguradora. Comando: `form_resid.json` (17:52).

### E14 — documento e código por seguradora
📊 Resulta 14 e AutoFleet 15 seguradoras ativas (de 27); o usuário de cada seguradora é CPF, CNPJ, e-mail ou código, conforme a
seguradora (só a classe foi lida, nunca o valor); campo de desconto em 7 seguradoras. Cada login enxerga uma corretora só. Comando: `GET api-prod/cfg/seguradora/config` (classe do valor, nunca o valor).

### E15 — cota e consulta de CPF
📊 "Cálculos ilimitados em 14 ramos" (tela "Meu plano", Resulta); nenhuma cota, saldo ou crédito nas respostas da API; a consulta
de CPF é um GET sem saldo exposto — sem evidência de cobrança.

### E16 — comissão e desconto por cálculo
📊 Dá para mudar por pedido, por seguradora. Na prática, 216 de 227 cálculos da AutoFleet usam uma comissão única (15 % em 89) e 📊 24
a 27 de 66 negócios recalculados mudaram a comissão (conforme se conte a 1ª versão). Efeito: −5 pontos de comissão = −1,5 a −7,6 % do prêmio (−5,6 na maioria); tirar 10 % de desconto encarece
5,9 %. A Mitsui só oferta com desconto 0. Comando: `analisa_versoes.py` + `alavancas.py`.

### E17 — como se apaga um negócio
📊 Menu ⋮ do item → "Excluir cotação" → `DELETE pdocs/calculo/negocio/{id}`. Observado, **nunca executado**.

### E18 — o token de 3 h
📊 O app não trocou o token sozinho em 1h24 de uso; as trocas (`POST login/pdocs`, sempre em pares) acontecem ao navegar ou
recarregar. **O que acontece quando vence: NÃO MEDIDA**, porque as sessões duraram menos de 3 h (P-128-01).

### E19 — o bloqueio por senha errada
📊 O cadastro de usuário tem `tentativasInvalidasSenha`, `bloqueadoAte` e `bloqueioPreventivo` (0 bloqueados nas duas contas). O
limiar **NÃO MEDIDA**, porque testar exige errar a senha de propósito. A guarda do motor: 1 tentativa, e parar com alerta.

### E20 — duas opções num cálculo só
📊 **Não.** A tela tem um seletor de pacote; pela API, 31 entradas (15 seguradoras × 2 pacotes) viraram todas "pacote 0" e cada
seguradora respondeu uma vez só (19 de 31 voltaram; a outra ficou pendente para sempre). Máximo: 1 pacote por cálculo. A proposta
de 2 opções = 2 cálculos (`calculos_medidos.json`, P1 v5, 18:47).

### E21 — quem responde em cada conta
📊 AutoFleet (ofertas ÷ pedidos, 227 cálculos): Tokio 173/223 · Mapfre 167/226 · Youse 155/210 · HDI 146/226 · Allianz 143/226 ·
Bradesco 140/218 · Porto 139/217 · Zurich 133/225 · Itaú 123/217 · Yelum 114/209 · Azul 113/217 · Ezze 88/219 · Azul por
Assinatura 82/210 · Aliro 68/210 · Darwin 56/138 · Sura 26/211 · Mitsui 19/217. Resulta (1 perfil): 10 de 12 com oferta. Comando: `analisa_versoes.py` (as 17 linhas reconferidas pela lente).

## 4. O contrato do cálculo (o que a 129-B implementa)
`backend/portal_worker/multicalculo/` — mora no worker porque o adaptador da 129-B mora lá (a imagem só copia o worker).
- **Entrada** `PedidoDeCalculoAuto` (ramo 31): segurado · veículo · pernoite · condutor · renovação · coberturas, com os 16
  obrigatórios medidos. **Ajuste** `Ajuste(tipo, valor)`: comissão, desconto, assistência, carro reserva, vidros, franquia, % FIPE.
- **Resultado aos poucos** `ler_rodada` → `RodadaDoCalculo` (por seguradora: família + ofertas) e `eventos_entre` → nova oferta ·
  seguradora recusou · conjunto fechado (a narração da D-MC-50 só nasce daqui).
- **Oferta** nunca leva login, senha nem link de PDF; a comissão vai em campo interno.
- Provado contra 5 fixtures saneadas (2 gravações, 1 configuração, 2 capturas ao vivo com 16 cálculos), diferencial 0.

## 5. Decisões que a medição tomou (D-128)
| # | decisão | nota |
|---|---|---|
| D-128-01 | alavancas medidas na AutoFleet (configuração real de automóvel), não na Resulta (comissão 0) | 88 × 60 |
| D-128-02 | família nova **DADO**: pedido a corrigir não é recusa do risco | 85 × ACEITACAO 50 |
| D-128-03 | **o recálculo é o corpo do pedido**: o robô reenvia o corpo com o ajuste, em vez de clicar no formulário. ⚠️ Usa o token do próprio app, de dentro da página — a D-MC-28 exige a autorização do Founder para o PRODUTO. A medição já fez assim 📊 os recálculos da E5, E7 e E20, sob a autorização ampla do Founder de 04/10 para validar | 88 × interceptar e clicar 70 · **pergunta ao Founder** |
| D-128-04 | proposta de 2 opções = 2 cálculos (o plano é ilimitado) | 90 |
| D-128-05 | o motor manda as coberturas explícitas, nunca o pacote da conta | 92 |
| D-128-06 | o motor entrega aos poucos e **fecha por tempo** (💭 90 s), sem esperar a seguradora calada | 88 |
| D-128-07 | renovação = InfoCap + Agger pela placa/CPF + padrões do questionário marcados como "assumido", para o corretor conferir | 80 |
| D-128-08 | o adaptador da 129-B herda a lista branca do captador: a única escrita é o cálculo | 90 |

## 6. 🧑 O portão de preço (D-MC-45) — as perguntas para responder antes da 130-A
> ✅ **RESPONDIDO 05/10 — D-MC-62…65** (`FOUNDER-DECISIONS.md`; ajustáveis depois com os comerciais das corretoras). As perguntas abaixo ficam como registro.

1. **A opção econômica.** Com os números da E5, a proposta é: "econômica" = **franquia normal + vidros básicos + carro reserva de 7
   dias**, mantendo RCF e APP. 💭 Em geral isso fica 10–30 % abaixo da completa. Pode ser esse o padrão?
2. **A comissão.** Baixar 5 pontos de comissão reduz 📊 de 1,5 a 7,6 % do prêmio (5,6 % na maioria), mas Porto e Azul ignoram a comissão (a Itaú ficou indeterminada). Nelas, o que
   baixa o preço é o desconto. Quando o cliente pedir "mais barato", o agente pode propor baixar a comissão? Até quanto (piso)? Quem
   aprova: o corretor, a cada vez?
3. **O desconto.** Hoje vai de 0 a 15 % por seguradora (📊 tirar 10 % encarece 5,9 %). O desconto entra na mesma régua da comissão?
4. **A completa.** O pacote "Prata" é diferente em cada corretora (E8). Qual é a "completa" padrão de cada uma? (A AutoFleet usa
   RCF 200/200/20 mil, APP 5 mil, franquia reduzida, vidros completos e carro reserva de 15 dias.)
5. **A FIPE abaixo de 100 %.** Ela baixa só de 0 a 6,7 %. Fica fora da econômica?

## 7. O captador — as regras do Founder por máquina
Lista branca de escrita: login (1 por contexto), troca de token, logout e cálculo (teto global 25, nunca em negócio que já existia,
foto da conta com menos de 15 min; negócio desconhecido só passa se o servidor disser que ele não existe). Revisado 2× (52 → 70 →
consertos listados aplicados), 31/31 casos, mutações vermelhas, ensaios ao vivo barrados. 📊 Resultado: **0 negócios sumiram**,
**0 dos 98 negócios AUTO de pessoas mudaram de versão**, 3 negócios novos (os de teste) — `g7.json`. Barrou: a telemetria do site,
6 trocas de token de uma 2ª aba e 1 "imprimir".

## 8. Os negócios de teste (para o Founder decidir apagar)
| conta | cliente | criado | versões |
|---|---|---|---|
| AutoFleet | perfil P2 (compacto 2021) | 04/10, 18:17 | 10 |
| AutoFleet | perfil P1 (SUV 2018) | 04/10, 18:42 | 5 |
| Resulta | perfil P1 (SUV 2018) | 04/10, 19:00 | 1 |

Podem ser apagados: a 129-B não depende deles (as fixtures saneadas já estão na main). Os números de cálculo nas seguradoras
continuam lá de qualquer forma.

## 9. 05/10 — o que a 129-B mediu ao vivo
Fonte: `reports/SPEC-129-B-EXECUTION-REPORT.md` §2–§3 e `specs/SPEC-129-B-o-motor-de-multicalculo.md` §4.1 (login da Ellen, captador;
📊 18 cálculos no Agger no dia — 8 no BLOCO 0 + 4 + 1 + 5 no canário —, todos em negócios NOVOS do robô; nada apagado).

- **Calcular sem a tela funciona.** O corpo do `calcularV2` montado DENTRO da página reproduz o da tela 📊 786/786 chaves (AutoFleet)
  e 657/657 (Resulta); ao vivo o servidor respondeu 📊 201 e o menor preço ficou igual ao da tela em 📊 11 de 13 seguradoras. → o 1º
  disparo também vai pelo corpo, sem fallback de tela (as senhas das seguradoras nunca chegam ao Python).
- **🔴 A hipótese do CPF em 2 corretoras NÃO se confirma** (D-MC-56; corpo idêntico nas duas contas, comissão 15, desconto 0): disparo
  simultâneo → menor preço igual em 📊 9 de 10 seguradoras (Zurich 0,981) · sequencial → 📊 10 de 11 (Zurich 0,984) · renovação →
  📊 7 de 8 (Zurich 0,987) · 📊 0 mensagens de "já cotado / outra corretora / prioridade". O nº de cálculo na seguradora difere entre as
  contas (📊 10/10 — não é cache). Não medido: a Tokio (credencial da Resulta recusada, P-129B-04) e a ordem inversa.
- **Econômica ÷ padrão por seguradora** (canário, 3ª rodada, presets da D-MC-62): média 📊 **0,873** (corretora A, 14 seguradoras) e
  📊 **0,872** (corretora B, 11); mín 📊 0,766, máx 📊 1,000. A D-MC-62 estimava 💭 12–20 % abaixo — o medido fica na faixa (~13 %).
- **🔴 Oferta que não é comparável (para a 130-A, P-129B-06):** o menor preço da corretora A (📊 R$ 186,78) veio da **Azul por
  Assinatura**, "plano proteção para terceiros" — **sem casco** e com prêmio de assinatura. Não pode disputar "menor preço" com uma
  apólice completa; a 130-A separa essas ofertas antes de comparar.
