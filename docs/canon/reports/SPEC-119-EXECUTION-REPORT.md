# SPEC-119 — Os corredores ficam prontos para a vida real

> **CONCLUÍDA e EMPURRADA em 28/09/2026.** `origin/main` = **`e5c0a00`** (base `ff711bd`), 97 commits.
> Juiz **71** ‖ red team **58** (cegos um ao outro) → três consertos → **nota final 90/100**.

## 0. O EXECUTION CARD

```
OUTCOME ........  o Founder recebe uma lista por rota — ATENDE SOZINHO / VAI A UMA PESSOA /
                  FALTA CAPTURA — provada por simulação sobre telas REAIS, e sabe, com número
                  datado, o que liga hoje e o que só um acionamento da corretora destrava

RISCO ..........  8  (ALCANCE o SEGURADO 3 · REVERSIBILIDADE saiu do prédio 3 · FREQUÊNCIA 2)
SUPERFÍCIE .....  3  (73 rotas, o classificador do acervo, uma classe nova de passo, cinco
                  baterias de simulação e a página do Founder)
PISO APLICADO ..  §3.2 — qualquer coisa que ENVIE mensagem/acionamento → CRÍTICO no mínimo
NÍVEL ..........  🔴 CRÍTICO · 7 builders Opus 5 xhigh · juiz Opus 5 ‖ red team Opus 5 (cegos,
                  UMA vez) · 3 consertos · 1 conserto do gerente

O FIO ..........  §2 da SPEC
PARALELISMO ....  F1 → F2 em série ‖ F3 → F4a ‖ F4b → F5 → juiz ‖ red team → A ‖ B → C
UNIDADES .......  5 fatias + 3 consertos, §5
COESÃO .........  o classificador e o gerador do corpus são o mesmo domínio → F1 e F2 vizinhas
TIME ...........  builders frescos, dono único por arquivo; juiz e red team cegos um ao outro
REFERÊNCIA .....  interna: o retrato de 27/09 (25/2/46) · externa: CLAUDE.md §9.3 e §9.5
GATES ..........  §6 — G1 e G2 NÃO cumpridos e declarados; G4 com 4 quedas explicadas
O ELO ..........  a afirmação-título era "rotas ficam SEM CORPUS porque o CLASSIFICADOR é cego".
                  📊 MEDIDA NAS TRÊS PONTAS E REFUTADA: 43 → 42 rotas com corpus, ZERO saíram
                  do vazio. O conserto deu FUNDO (+1.620 telas em 11 rotas que já tinham),
                  não LARGURA. Escrito na SPEC §3.1 e no CHANGE-ADDENDA.
FAIXA DE RELÓGIO  💭 sem teto declarado pelo Founder ("não precisa de limite de tempo").
                  📊 Real: ~22 h de relógio, 2 quedas de internet, 97 commits.
ORÇAMENTO ......  📊 US$ 1,9984 de 4,00 na OpenAI (50%) · US$ 0,0927 de 5,00 na Anthropic (1,9%)
```

---

## 1. O QUE MUDOU PARA O CORRETOR E PARA O SEGURADO

### 1.1 🔴 Dois defeitos que CHEGAVAM ao segurado, e ninguém sabia

**O cérebro do acionamento estava 100% fora do ar.** Quando o robô trava numa tela que não
reconhece, quem destrava é o Sentinela, pedindo ajuda ao modelo. A rota `dispatch` passou a usar
um modelo de raciocínio (SPEC-116) e o código lia a resposta com `str(content)` — que devolvia o
**raciocínio cifrado** em vez do texto. O fiscal recusava por `too_long`, a escada esgotava, e
**todo** travamento virava handoff. 📊 Medido: **2 de 2** falharam antes; **2 de 2** destravaram
depois. O sintoma parecia "a URA é difícil".
⚠️ E o que nos salvava era o COMPRIMENTO, não o fiscal: 📊 `guard_human_phase_reply` com um blob
cifrado CURTO devolve `{'ok': True}` — aprovaria e mandaria estrutura serializada à URA.

**O robô aceitava custo em nome do segurado.** Numa tela da Allianz que oferece oficina
referenciada *"com desconto de até {VALOR} na franquia"*, o corredor mandava a uma pessoa — mas o
Sentinela, trinta segundos depois, respondia **"1"**. Mesma tela, veredito oposto, e quem chegava
à seguradora era o caminho errado.

### 1.2 Condomínio, empresarial e sinistro vão a uma pessoa — nas DUAS telas
Com apólice de condomínio, o robô traduzia `"Condomínio"` para a tecla `"2"`, **seguia** para o
galho de áreas comuns e `cnpj_condominio` respondia sozinho — na tela que **prova** que o caso é de
áreas comuns, com cobertura e prestador diferentes. Consertado. E o red team achou uma **segunda**
tela de três opções (`1-Residência 2-Condomínio 3-Empresa`, sessão `2540f42f`) que ninguém olhava
(📊 `grep -rln menu_solicitar_para backend/tests/` → nenhum arquivo): ali o robô respondia `"1"` fixo.

### 1.3 O acervo parou de vazar dado de gente
📊 17 primeiros nomes de segurado em ~90 linhas (`Saionara` ×17, `Maria` ×12, `Carlos` ×11) e 27
endereços reais, num arquivo **global de produto** versionado em git. Agora **zero** dos dois.

### 1.4 A página passou a responder DUAS perguntas
> **De 73 rotas medidas, o sistema resolve sozinho 33% (24), 3% (2) vão para uma pessoa por desenho
> da seguradora, e 64% (47) ainda não dão para ligar.** Das 47, **31 não têm conversa gravada**
> (🧑 acionamento da corretora) e **16 têm** (🤖 código nosso).

---

## 2. COMMITS E ARQUIVOS

```
commit inicial (base) .... ff711bd   commit final ............. e5c0a00
commits .................. 97        arquivos de produto ...... 9
```

| fatia | o que entregou |
|---|---|
| **F1** | o classificador deixa de ser cego: +5 padrões-ouro, +9 entradas de menu |
| **F2** | o acervo inteiro entra: 4.470 → **6.048** telas; o teto de 5 por rota vira PISO |
| **F3** | a classe de passo: DECIDE × CONDUZ; a tela desconhecida para de travar por bobagem |
| **F4a** | o simulador das 73 rotas com telas reais + condomínio/empresarial/sinistro a uma pessoa |
| **F4b** | apelidos contra o agente real, o formulário da HDI, e o cérebro do acionamento |
| **F5** | demanda POR ROTA do banco, nota em %, as três faixas, a aba gerada |
| **A** | o acervo sem PII, o guarda do §13.9 por REGRA, o ELO refutado escrito |
| **B** | a 2ª tela de três opções, a 2ª pergunta do §9.5 passa a REPROVAR, o extrator, o fiscal |
| **C** | dez guardas com verdade vencida — e a 11ª, que era regressão real |


---

## 3. OS TESTES, COM SAÍDA REAL

### 3.1 A bateria completa (G8) — em `git worktree` separado, triada contra o COMMIT BASE

```
BASE   ff711bd (= o que está no ar)   52 failed · 1708 passed · 32 xfailed   1:38:22
FINAL  3dbc286                        48 failed · 2054 passed · 32 xfailed   1:11:26
```

📊 **−4 falhas e +346 testes passando.** Triagem nominal:

- **7 falhas antigas SUMIRAM**, entre elas a vermelha permanente da triagem de travamento.
- **3 nomes aparecem que não estão na base**, e os três têm controle:
  `test_o_timeout_mata_o_neto` → **5 passed** isolado · `test_uma_corretora_nao_trava_a_outra` →
  **1 passed** isolado (4min11) — disputa de ordem/tempo na bateria longa, a família que o próprio
  `BATERIA-LINHA-DE-BASE.txt` já documenta. O terceiro, `test_a_arvore_ficou_limpa_no_fim`, foi
  provado vermelho **na própria base**, sozinho, com a mesma frase (P-119-18).

⇒ 🔴 **ZERO falha nova real.**

### 3.2 As MUTAÇÕES (G7)

🔴 **Seis mutações ficaram VERDES nesta SPEC, e uma ficou MUDA.** Todas foram achadas e consertadas.
É o mesmo padrão da SPEC-118 (duas verdes), e por isso cada saída está colada nos relatórios das fatias.

| mutação | quem achou | estado final |
|---|---|---|
| M9 · a atribuição do achado deixa de rodar o motor | F4a, na própria fatia | vermelha |
| M10 · o passo do teste não é do próprio ofício | F4a | vermelha |
| M2 · o guarda lia o COMENTÁRIO do conserto, não o código | F4b | vermelha |
| M4 · `classe_da_tela` sobrevive no import e nos comentários | F4b | vermelha, virou guarda de MOTOR |
| M-RT1c · palavra de conteúdo entra no vocabulário da navegação | **red team** | vermelha |
| M-RT6 · tecla fixa `3` num menu → 126 asserções verdes | **red team** | vermelha, nas duas formas |
| MUT-2 · defeito §9.5 reintroduzido → rota seguia `ATENDE SOZINHO` | **juiz** | vermelha |
| MUT-3 · nome de gente como VALOR e dentro do HTML | **juiz** | vermelha nas duas |
| M5 · mutação quebrada parecia guarda mudo | F5 | refeita, vermelha |

### 3.3 Os guardas do gerente

```
a triagem de travamento (a vermelha PERMANENTE, fechada)
   CONTROLE 32 passed · M1 familia nova 1 failed · M2 familia apagada 1 failed
   M3 motivo dinamico 32 passed  (e' ruido, nao e' familia)

o patamar (deixa de CONTAR e passa a dizer QUEM caiu)
   CONTROLE 26 passed · M1 baixa sem explicacao 1 failed · M2 OUTRA rota cai 1 failed

o Sentinela nao da um SEGUNDO handoff (P-119-19)
   base 57/0 · antes 54/3 · so a releitura 54/3 · releitura + guarda migrado 60/0
   MUTACAO (o ramo deixa de reler) 59/1, e a vermelha e a assercao certa
```

### 3.4 O PII, com o par que dá direito à conclusão

```
guarda NOVO   x acervo ANTIGO .....  6048 linhas, 134 sujas   EXIT=1   VERMELHO
guarda ANTIGO x o MESMO acervo ....  6048 linhas,   0 sujas   EXIT=0   era CARIMBO
guarda NOVO   x acervo REGERADO ...  6048 linhas,   0 sujas   EXIT=0   VERDE
```

📊 Conferido por mim, por uma terceira via: **17 nomes / ~90 linhas → 0**; `{NOME}` 217 → **411**.
Logradouro real **27 → 0**, com as 18 linhas de exemplo da URA preservadas.

🔴 A causa era pior do que parecia: em 20 das 27 linhas **a própria seguradora já mascarava** o fim da
rua e o número (`Av. Caetano Silveir#, #, Palhoça, SC`), e o nosso mascarador não reconhecia o `#`.
**Meia máscara é o pior estado: a linha parece tratada.**

---

## 4. OS GATES — dois NÃO cumpridos, declarados com evidência

| gate | veredito | evidência |
|---|---|---|
| **G1** nenhuma seguradora > 25% sem etiqueta | 🔴 **NÃO** | 5 de 16 arquivos. ⚠️ O total caiu a **11%** e 11 dos 16 estão em ≤21% → P-119-02 |
| **G2** `mapfre/auto/guincho` sai de SEM_CORPUS | 🔴 **NÃO** | ausente no corpus **E** no banco. **Não é classificador cego, é ausência de material** → P-119-01 |
| **G3** o teste do FIO verde, e vermelho antes | ✅ | §3.2 |
| **G4** nenhuma rota perde patamar | ⚠️ 4 quedas, as 4 explicadas | 3 são o acervo crescendo; a 4ª é `bradesco/auto/bateria` → P-119-10 |
| **G5** as oito respostas erradas continuam vermelhas | ✅ | 51 passed, chamando o motor sobre tela real |
| **G6** as 5 baterias, cada uma com controle | ✅ | §5 |
| **G7** mutação dos guardas novos | ⚠️✅ | §3.2 |
| **G8** bateria em worktree separado, contra o base | ✅ | §3.1 |
| **G9** `conferir_o_que_esta_no_ar.py` BATE depois do push | ⏳ | depende do **Implantar**, que é do Founder |
| **G10** a aba com a lista por rota, zero data sem rótulo | ✅ | 7 conferências verdes; 9 datas, **todas 28/09**; `72 pedidos` → **0** |
| **G11** gasto dentro de US$ 4 / US$ 5 | ✅ | US$ 1,9984 (50%) · US$ 0,0927 (1,9%) |

⛔ **Nenhum gate foi afrouxado.** Onde não fechou, virou pendência com o que custa esquecer.

---

## 5. AS CINCO BATERIAS (F4), com a linha de CONTROLE de cada uma

| # | bateria | resultado | o CONTROLE |
|---|---|---|---|
| 1 | apelidos contra o agente **REAL** | 📊 **20 de 22** certos | "dedetizador" recusado 3/3 · colisão → humano 1/1 · 🔴 "portão eletrônico" acionou `eletricista` **3/3** |
| 2 | o simulador das 73 rotas, com as duas perguntas do §9.5 | 24 / 2 / 47 | 4 casos plantados, cada um sai com a letra certa |
| 3 | o formulário da HDI vs o **clique humano** | 5 de 5 idênticas | 4 controles, inclusive "os dois lados CONSEGUEM diferir" |
| 4 | Vigia → Sentinela → Cérebro, travamento forçado | 🔴 **não destravava; agora 2/2** | a atendente na conversa → cérebro 0×, gasto US$ 0,00 |
| 5 | condomínio · empresarial · sinistro → handoff com dossiê | 13 telas, **0 furadas** (eram 6) | a apólice Residencial na mesma tela segue sozinha (9 rotas protegidas) |

🔴 **O que CONTINUA sem prova, e é honesto dizer:** **nenhuma seguradora recebeu até hoje uma resposta
de formulário nossa.** A prova de 26/09 (HTTP 200) foi **entre dois números nossos** — prova o
transporte, não a aceitação. A bateria 3 acrescenta que o **conteúdo** é igual ao do clique que a HDI
aceitou. É o máximo que se prova sem uma seguradora do outro lado.

---

## 6. O QUE FICOU FORA, E O QUE CUSTA ESQUECER

| # | o que | de quem |
|---|---|---|
| **P-119-01** | `mapfre/auto/guincho` exige acionamento real — não há uma conversa de guincho da Mapfre no acervo | 🧑 |
| **P-119-05** | `carro_reserva` **não tem corredor nenhum**: 126 telas, 13 pedidos, zero passos | 🤖 |
| **P-119-10** | `bradesco/auto/bateria` — a URA da Bradesco despacha **técnico**; o nome da rota mente | 🤖 |
| **P-119-12** | o fiscal não confere que a resposta **pertence às opções da tela** | 🤖 |
| **P-119-13** | `_canal_da_conversa` pode falar com o SEGURADO pelo canal observador, contornando `pode_enviar` | 🧑 |
| **P-119-14** | a fronteira de zona: 10 telas de `porto/auto/bateria` são **uma pessoa conversando** | 🤖 |
| **P-119-17** | falta `npm ci` em três worktrees — 5 vermelhas por rodada que não são do produto | 🧑 |

🔴 **A DECISÃO QUE SOBRA PARA O FOUNDER:** o agente aciona **eletricista** para *"meu portão eletrônico
da garagem parou de abrir"*, **3 de 3**. Não foi consertado porque exige decidir se motor de portão é
assistência elétrica residencial — **decisão comercial**, CLAUDE.md §10, condição 2.
**Custa esquecer:** um prestador vai à casa do segurado para um serviço que a apólice pode não cobrir,
e a recusa acontece **no local**.

---

## 7. CANÁRIO E RISCOS REMANESCENTES

**Canário Amandus → Resulta → AutoFleet: NÃO RODOU.** Esta SPEC foi de instrumento e de conserto; o
canário que falta é o **da Porto com o pin de localização**, herdado da SPEC-118, e depende do
Founder clicar Implantar.

- 📊 O fiscal aprova **5 de 10** rascunhos defeituosos (eram 8). O pior é uma frase em português
  perfeita pedindo o CPF do titular **à seguradora**.
- 📊 `backend/scripts/regua_motor.py:287` tem um UUID de corretora escrito à mão (§13.9, pré-existente).
- ⚠️ `yelum-auto.jsonl` está em 80% do teto de bytes por arquivo.
- ⚠️ `BATERIA-LINHA-DE-BASE.txt` continua vencida (lista 35 nomes, o cabeçalho diz 47) — por isso a
  triagem desta SPEC foi contra o **commit base**, não contra o arquivo.

---

## 8. DECLARAÇÃO DE MOTOR PARALELO

⛔ **Nenhum motor paralelo foi criado.** Conferido por `grep` e pelos DOIS julgadores, de forma
independente. Cada pergunta tem um dono único: `familia_de_ramo` em `policy_data_provider` ·
`classe_da_tela` em `insurer_dispatch_service` · `extract_text_from_content` em `agents/utils` ·
`_anunciar_o_handoff_no_feed` em `dispatch_watchdog` · a aba em `pagina_dos_corredores.py` (📊 escritor
único). Os cinco scripts novos **delegam**: `simular_corredor` importa `conferir_respostas`,
`regua_motor` e `replay`, e não tem `re.compile` próprio.

🔴 **E uma correção ao meu próprio pacote:** eu mandei construir as três sub-perguntas A/B/C. A F4a
mediu e me corrigiu — **elas já existiam** em `conferir_respostas.py` desde a P-084-14. Construí-las
teria sido motor paralelo, e mediria a si mesmo. O que faltava era a **atribuição à rota**.

---

## 9. A NOTA DA EXECUÇÃO — 90/100

| dimensão | peso | nota | por quê |
|---|---:|---:|---|
| o outcome, reproduzível e datado | 30 | 28 | as três faixas saem de três retratos datados; a aba é gerada, e o gerador recusa gravar com defeito |
| defeitos de PRODUTO achados e consertados | 25 | 25 | o cérebro do acionamento fora do ar · o custo aceito em nome do segurado · as duas telas de condomínio · o segundo handoff |
| honestidade de declaração | 20 | 19 | G1/G2 não cumpridos e o **ELO refutado**, com número |
| guardas que ficam vermelhos | 15 | 12 | 6 mutações verdes por engano — achadas por julgadores, não pelos autores |
| §13.9 · PII · dado de gente | 10 | 6 | o vazamento foi **ampliado** antes de ser consertado, e o auditor era carimbo |

⚠️ **O que puxa a nota para baixo é honesto:** a SPEC **refutou a própria tese**. Destapar os olhos do
classificador deu **fundo** (+1.620 telas), não **largura** — **zero** rotas saíram do vazio. O valor
entregue não some (o acervo ficou 43% mais fundo, a classe de passo é nova, quatro defeitos graves de
produto foram achados e consertados), mas *"destravou rota parada"* não pode ser escrito.
