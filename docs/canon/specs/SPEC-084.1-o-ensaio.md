# SPEC-084.1 — O ENSAIO

> **O protocolo que leva cada uma das 73 rotas ao nível da máquina de lavar — não o de 19/08, mas o de depois do que aprendemos com ela.**
>
> Autor: execução · **v4, 22/08/2026** · ✅ LIBERADA pelo juíz · base `10abc94` · branch da SPEC-084
> Precondição: SPEC-083 ✅ · SPEC-084 blocos 0–5 ✅

---

## 0. PREFLIGHT

```bash
git rev-parse --show-toplevel        # AutoBrokers-FIX
git status --short                   # limpo

export PYTHONIOENCODING=utf-8        # 🔴 sem isto o cp1252 mata a saída no Windows
cd backend && python scripts/medir_rota.py --seguradora allianz \
       --ramo residencial --servico maquina_de_lavar
# 60/96, E a lista "O QUE FALTA" com 5 itens. Se a LISTA não sair, PARE.
```

📊 **Sem `PYTHONIOENCODING`, medido nas duas shells:** `bash` →
`UnicodeEncodeError: 'charmap' codec can't encode` · `pwsh` → imprime `PRONTIDAO 60/96`
e **morre antes da lista**, exit 255. Um chat novo pararia na primeira linha da SPEC.

🔴 **E leia a §7 antes de começar.** Ela diz como esta SPEC é executada: os papéis, os juízes, e o laço que só para quando o juiz libera.

---

## 1. POR QUE ESTA SPEC EXISTE

📊 Em **19/08/2026 às 16:35 BRT**, `allianz × residencial × maquina_de_lavar` foi do "oi" do segurado ao **protocolo 52955490 em 5min55**, sem humano nenhum.

📊 Em **21/08**, uma auditoria achou **quatro furos dentro dela**. Nenhum tinha derrubado o atendimento — todos foram cobertos pelo cérebro adaptativo ou pela atendente.

> ## 🔴 FURO COBERTO É FURO QUE NINGUÉM VÊ.
>
> **Um acionamento que dá certo não prova nada sobre a rota.** Os quatro furos
> conviveram com 5min55, zero `needs_human`, zero retentativas e 72 asserções verdes.

E a causa raiz está escrita no controle das SPECs: 📊 **não existe SPEC-082.** A rota validada foi construída sem SPEC — *"trabalho sem SPEC é trabalho sem gate. Esta é a evidência."*

**As outras 72 rotas não podem repetir isso.** Elas têm de nascer **com** as lições, não descobri-las ao vivo.

### 1.1 O estado, medido

```
o corredor fala com a URA .............. 41 de 73    média 47,7 pontos
a atendente sabe conduzir o cliente ....  2 de 73    regras_para_o_cliente
o cliente recebe protocolo+dia+período .  0 de 73    client_summary
alguém provou ponta a ponta ............  1 de 73    ⚠️ fato histórico, não item de régua

apelidos, os 11 destinos:
   maquina_de_lavar 11 · socorro_mecanico 10 · guincho 6 · vidros 5
   ar_condicionado 5 · limpeza_caixa_dagua 5 · consulta_veterinaria 4
   encanador 2 · eletrodomesticos 1 · eletricista 1 · desentupimento 1
   🔴 chaveiro 0 · bateria 0 · pneu 0
   📊 35 de 73 rotas têm ≥1 apelido. Das 38 sem, 34 são chaveiro(14),
      bateria(10) e pneu(10)
```

⚠️ 🔴 **E `/96` não é um denominador único.** 📊 Entre as 41 rotas medidas:
`96 ×30 · 86 ×6 · 84 ×3 · 74 ×2`. **Toda nota desta SPEC carrega o denominador dela** — a
média de pontos crus (47,7) não é comparável entre denominadores diferentes.

📊 **E 96 é o teto, nunca 100:** `medir_rota.py` jamais passa `tem_espelho=True`, então o
item dos apelidos (4 pts) sai **sempre** como `SEM_ESPELHO`. Ver G5/C6.

🔴 **Zero apelidos significa que o acionamento morre antes de começar.** Comentário no
próprio código: *"Sem estes apelidos, `canonical_subservice` devolve o próprio texto,
`subservices` não acha, e o acionamento morre antes de começar."*

### 1.2 O teto é 96/96 — 94 pela régua + rota, e os 2 finais pela E2

📊 Simulado em memória com a rubrica real, na rota de referência:

```
dos 36 pontos que faltam:
   36  são TRABALHO      a evidência JÁ ESTÁ no corpus
    0  são COLETA
    0  são ARQUITETURA

60/96  hoje
83/96  só com trabalho de ROTA        (+23)
94/96  + consertos da RÉGUA           (+11)   📊 C1+C2 = +5 · C3 = +6
96/96  + as `notes` recontadas (E2)   (+2)    ⚠️ é trabalho de ROTA, não de régua
```

---

## 2. 🔴 FASE 0 — A RÉGUA PRIMEIRO, EM COMMIT SEPARADO

**Antes de tocar em qualquer rota.** 📊 Dois itens da rubrica falham em **73 de 73** — não porque ninguém fez, mas porque **a ferramenta não consegue passar**. São o defeito que a SPEC-083 §3.3 nomeia, dentro da própria régua.

### 2.1 Os SEIS consertos

⚠️ **Nomeados `C1..C4`, não `R1..R4`** — 📊 `--comparar-com` já imprime *"🔴 R3 violada"*
para outra coisa (*"nenhuma rota perdeu respondidas"*). Dois `R3` no mesmo relatório é
armadilha.

| # | onde | o defeito | 📊 ganho |
|---|---|---|---|
| **C1** | `rubrica.py:289` | monta a chave `"capture"`; `client_summary_from_capture` lê `session["captured"]` (`insurer_dispatch_service.py:2378`) → devolve `None` **sempre** | 0/5 → 5/5 em **21 rotas** |
| **C2** | `insurer_dispatch_service.py:2384-2390` | lê `schedule["from"/"to"/"at"/"day"]` e **nunca** `schedule["periodo"]`. A captura tem `'periodo': 'tarde das 13:00 as 18:00'` e ele é descartado | (junto com C1) |
| **C3** | `rubrica.py:363-377` | 🔴 **reimplementa** a origem de tecla e diverge nas DUAS direções | 9/41 → **36/41** zeram o item |
| **C4** | `rubrica.py:436` | `sub.get(...) or pb.get(...)` — o fallback credita a regra do CORREDOR a **toda rota dele** | 9 recebem, **2 têm regra**. 🔴 **SUBTRAI −3 em 7 rotas** |
| **C5** | `rubrica.py:441-455` | procura os 40 chars em **qualquer** comentário 📊 do bloco, não dentro de `regras_para_o_cliente` → 📊 regra inventada tira 3/3 | 3 pts que hoje são falsos |
| **C6** | `medir_rota.py` | não existe `--com-espelho`; 📊 ninguém passa `tem_espelho=True` → os 4 pts ficam `SEM_ESPELHO` **para sempre** | destrava a E8 nas 73 · ⚠️ **é FERRAMENTA NOVA, ver §2.3** |

🔴 **C2 é o furo nº 3 da Clarissa, ainda aberto.** É por ele que ela recebeu *"Prontinho! ✅
Sua assistência foi aberta"* **sem data e sem período** — e depois ficou escondido atrás de
um item que não sabia medi-lo.

### 🔴 C3 — e ele NÃO é "acrescentar um filtro"

📊 A v1 desta SPEC dizia *"não filtra `only_subservices`"*. **Medido, isso conserta 2 das 5
teclas e o item continua 0/6.** A causa real é maior: `rubrica.py:363-377` **reimplementa** a
origem, e diverge nos dois sentidos ao mesmo tempo —

```
FROUXA   `re.search('"chave"', fonte_inteira)` aceita a chave citada
         em qualquer lugar do arquivo, inclusive num COMENTÁRIO
ESTRITA  não conhece `required_slots` (coleta) nem `_slots_com_padrao_do_motor`
         — as origens 3 e 4 que a própria §E4 desta SPEC lista
```

📊 As 5 "teclas órfãs" da rota de referência **têm origem**, e quem sabe é o produto:

```
conferir_respostas.origens_do_slot →
   caixa_litros_opcao ............. ['coleta']
   caixas_dagua_quantidade_opcao .. ['coleta']
   idade_aparelho_opcao ........... ['coleta']   ← a tela de COBERTURA da §3.1
   profissional_opcao ............. ['constante-por-subservico']
   qual_seguro_opcao .............. ['coleta']
```

**É o motor paralelo que o `CLAUDE.md` §5 proíbe, dentro da régua.** O conserto é **usar
`conferir_respostas.origens_do_slot`** e aplicar o filtro `only_subservices` — os dois juntos:

```
rubrica hoje ................... 9/41 rotas zeram o item
+ só o filtro .................. 25/41
+ só origens_do_slot ........... 23/41
+ os dois .................... 36/41   ← o certo
```

### ⚠️ O que a v1 mandava fazer e ESTAVA INVERTIDO

📊 A v1 tinha um `R3`: *"`rubrica.py:325` reconta contra o acervo inteiro, não contra o
corpus"*. **É o contrário** — `rubrica.py:325` já reconta contra `r.telas`, e `replay.py:133`
já filtra por serviço. A §E2 desta SPEC diz a versão certa; a §2.1 dizia a invertida.

🔴 **E o controle matou as duas leituras:**

```
passo                          declara  corpus da rota(102)  ramo inteiro(781)
menu_tipo_servico                 64           4                  32
menu_categoria_eletrodomestico    14           2                   4
aparelho_marca                     6           2                   3
menu_profissional                 13           1                  10
```

**Nenhum reproduz em nenhum dos dois denominadores.** Os números declarados vieram **do
banco**, não do corpus — e o corpus é amostra (43 de 140 sessões). **O conserto é reescrever
as `notes`, e elas moram no playbook**, que o gate da §2.2 exige LIMPO.

> **Reconciliar as `notes` é trabalho de rota (E2), não conserto de régua.** Vale os 2
> pontos lá.

### 2.2 Por que separado, e é regra da SPEC-083

> *"Medir a coisa e mudar a coisa no mesmo commit é como se perde a régua. Se a nota
> subir, ninguém sabe se foi a rota que melhorou ou a medida que afrouxou."*

```
GATE DA FASE 0
· C1, C3, C4 e C5 em UM commit que não toca nenhum playbook
    🔴 `git status backend/app/services/corridor_playbooks.py` LIMPO
    ⚠️ C2 é em `insurer_dispatch_service.py` — motor, não corredor. Commit
       próprio, com mutação.
    🔴 O C6 NÃO entra aqui: ele é a FASE 0.5 (§2.3). A v3 criou a fase e
       deixou este gate agendando o C6 dentro da Fase 0 — o gate e a fase
       nova se contradiziam.
· `--todas --salvar-linha-de-base .baseline/fase0-<commit>.json` — 🔴 a v1 dizia
  *"é a LINHA DE BASE"* sem dizer como gravá-la. A flag existe (`medir_rota.py`).
· ⚠️ e as `MUTACOES` moram em `tests/test_a_regua_nao_tem_furo.py`, que
  `verificar_mutacoes.py:150` assume por padrão
· 📊 e o relatório diz, rota a rota, quanto subiu SÓ pelo conserto da régua
    ⚠️ esperado, MEDIDO: **+5 nas 21 rotas** que capturam protocolo (C1+C2) ·
       **+6 nas 16** que o C3 destrava · **−3 nas 7** que o C4 deixa de creditar
       indevidamente. Ordem de **~215 pontos de leitura**, não 511.
    🔴 O `7 × 73 = 511` da v1 era falso em três lugares: só **41 rotas têm corpus**,
       C1+C2 ajuda 21, C3 ajuda 16 — e o C4 **subtrai**.
· mutação em cada conserto, EXECUTADA e vermelha
```

⚠️ **E o que NÃO é permitido na Fase 0:** afrouxar limiar, remover item, renormalizar
nota. **C1–C5 são bugs de leitura** — se algum exigir mudar a régua para passar, **não é
Fase 0**, é mudança de rubrica e vai para o juiz.

### 2.3 🔴 FASE 0.5 — o C6 não é conserto, é ferramenta nova

**C1–C5 são bugs de leitura em linhas conhecidas.** O C6 é *"criar `--com-espelho` lendo o
Supabase" — construir um leitor que não existe.*

📊 O orçamento da Fase 0 é ~70 min, e a §2.2 fecha com *"se algum exigir mudar a régua para
passar, não é Fase 0"*. **Construir leitor novo é mais que isso.**

```
FASE 0.5 — o leitor do Espelho
   entrega:  `medir_rota.py --com-espelho`
   gate:     roda nas 73 e o item dos apelidos DEIXA de sair SEM_ESPELHO
   🔴 e o JUIZ 0 confere: nenhuma rota mudou de nota EXCETO pelos apelidos
```

🔴 **E ele tem duas travas que não são negociáveis** (ver §E8): o filtro de `company_id`
e a **exclusão nomeada da Amandus**. Sem elas, o C6 semeia `_SUBSERVICE_ALIASES` com
vocabulário de **conversas fictícias** — e a E8 contaria isso como prova.

---

## 3. 🔴 FASE 1 — A VARREDURA DE SEGURANÇA, NAS 73, ANTES DE QUALQUER ROTA

**Esta fase existe porque o defeito que ela caça não aparece em medição nenhuma.**

📊 CLAUDE.md §9.5: **casar a tela não é responder certo.** Oito passos casavam a tela,
respondiam, e respondiam errado. **Apareciam verdes em toda medição** — o comparador
perguntava *"alguma rota parou de responder?"* e eles respondiam.

### 3.1 A classe: perguntas de cobertura disfarçadas

📊 Achadas até hoje, e a lista **não está fechada**:

| tela | o que o corredor fazia | o dano |
|---|---|---|
| `aviso_fora_da_garantia` | respondia `"1"` onde 1 = *"Até 10 anos"* | **afirmava a idade do aparelho sem perguntar** — e é a tela que decide a cobertura |
| a mesma âncora, 2ª tela | respondia `"1"` = *"Conserto do ar condicionado"* | 📊 errado em **100%** das telas que casava. Num caso de máquina de lavar, abria ar-condicionado |
| `menu_qual_seguro` | respondia `"1"` num menu de 3 onde **2 é Condomínio** | não travava: **abria o chamado que será recusado no local** |
| `vazamento_aparente` | — | vazamento não aparente é caça-vazamento, **não coberto** pelo próprio texto da Allianz |
| `pneus_quantidade_opcao` | — | 📊 **mais de um pneu MUDA O SERVIÇO para guincho** |
| `servico_aberto_ver_ou_abrir` | — | `1` = ver chamado antigo → **o caso morre sem acionamento** |
| `escolher_entre_dois_enderecos` | — | escolher fixo **manda o prestador para a casa de outra pessoa** |
| `cpf_anterior` | — | 📊 os humanos responderam `"1"` (continuar com o CPF anterior). **O corredor responde `"2"` e está certo:** o WhatsApp da corretora atende muitos segurados |

> ## 🔴 `constante_justificada`
>
> **Navegar** (`Continuar`, `Voltar`, `Sair`) e **decidir** (`Até 10 anos`, `Condomínio`)
> têm **a mesma forma no código** — e resultados opostos na vida do segurado.
>
> 📊 45 ocorrências de `constante_justificada` hoje. **Toda constante nova precisa de
> uma**, e ela diz *por que aquela tecla não decide nada em nome do cliente*.

### 3.2 A ferramenta, e as três perguntas

`backend/scripts/conferir_respostas.py` já existe. Cada pergunta nasceu de um defeito que
as outras duas **não pegam**:

```
A · o slot tem origem?            → passo que fica CALADO      (📊 2min22 medidos)
B · a constante está na tela?     → rótulo que a URA rejeita ·
                                     dígito que DECIDE pelo cliente
C · o passo é do ofício da tela?  → passo de um ofício respondendo tela de outro
```

📊 Primeira rodada: **94 achados**, hoje zerados.

### 3.3 O que a Fase 1 entrega

⚠️ 📊 **`conferir_respostas.py --todas` já devolve ZERO no commit base** (exit 0). **A Fase 1
não é rodar a varredura — ela já está limpa.** É o relatório e o gate de cegueira:

```
1. 🔴 o RELATÓRIO: para cada constante que decide algo em nome do cliente,
   a `constante_justificada` que a autoriza — ou o passo que a substituiu
   por coleta. 📊 Hoje há 45 `constante_justificada`; o relatório diz se
   elas cobrem TODAS as constantes que decidem.
2. 🔴 o GATE DE CEGUEIRA: reintroduza um dos 8 defeitos históricos.
   Se a ferramenta ficar VERDE, ela está cega e a fase não fecha.
3. e a LINHA DE BASE do E13 gravada: 📊 **122 TELAS DISTINTAS** (257 ocorrências)
   em 39 rotas, cada uma com **a ONDA que a paga**. Tela sem onda é entrada
   inválida. 🔴 A v3 corrigiu a unidade na E13 e deixou 257 aqui — no lugar
   onde o arquivo é efetivamente produzido.
```

🔴 **Diga isto ao executor**, senão ele procura trabalho que não existe.

🔴 **Nenhuma rota vai a teste ao vivo antes desta fase fechar.**

---

## 4. 🔴 O PROTOCOLO — as 14 estações, uma rota por vez

**Toda rota passa pelas 14 — E13 e E14 inclusas. Sem exceção, sem "esta é simples".**

🔴 **E13 e E14 nasceram na v2 e o gate da v2 continuou certificando "as 12".** Um
executor cumpriria 12, pularia a E13, plantaria o `noop` largo, tiraria 80/96, e
`--comparar-com`, `conferir_respostas` e o freio passariam todos — **com o gate
assinando embaixo.** A cura tem de estar no gate, não só no texto.

Cada estação diz: **o que fazer · onde está a evidência · o controle que prova · a armadilha medida.**

---

### E1 · A SESSÃO-OURO

**O quê:** achar, no acervo, **uma sessão desta rota que chegou ao desfecho** — protocolo,
ou o desfecho que aquela seguradora dá (link, ordem de serviço, confirmação).

**Onde:** `observed_events` filtrado pela marca da rota (a chave `_opcao` única, ou
`subservice_menu_map[rota]`, ou um passo com `only_subservices` que a cite) · o corpus em
`backend/tests/corpus/telas_reais/`.

🔴 **A armadilha, medida:** *"Menu que LISTA o serviço não é prova de que o serviço foi
PERCORRIDO."* 📊 As quatro rotas da alfa aparecem nas **mesmas 5 sessões**, porque a tela de
menu lista os quatro de uma vez.

**Controle:** a sessão escolhida **responde ≥1 passo com uma marca desta rota**, verificado
pelo motor.

**Se não houver:** `SEM_CORPUS` → lista de coleta. 🔴 **Mas antes**, pergunte as duas coisas
(`lista_de_coleta.py`): *o corpus está vazio?* **E** *o acervo também não a tem?* 📊 `tecnico`
aparecia `SEM_CORPUS` com **109 linhas** escondidas atrás do balde de não-classificado.
**Coletar o que já está coletado é caro:** entrada demais nos portais nos bloqueia.

---

### E2 · A TRANSCRIÇÃO, TURNO A TURNO

**O quê:** no comentário do bloco do subserviço, a sequência **na ordem em que a URA usou**,
com `📊 sessão <8 hex>` e **contagem por tela**.

📊 Modelo: `corridor_playbooks.py:377-394` — 11 telas da sessão `b2bf40e7`, protocolo 51022010.

**Por que importa:** é o que permite auditar sem voltar ao banco, e vale **4 pontos do eixo A**.

🔴 **A armadilha, e ela é maior do que parecia.** 📊 Medido: **nenhuma** das contagens
declaradas reproduz — nem contra o corpus da rota (102 telas), nem contra o ramo (781):

```
passo                          declara   corpus rota   ramo
menu_tipo_servico                 64          4         32
menu_categoria_eletrodomestico    14          2          4
aparelho_marca                     6          2          3
menu_profissional                 13          1         10
```

**Os números vieram do banco, e o corpus é amostra** (43 de 140 sessões). Reconciliar é
trabalho **desta** estação.

**Controle:** para cada `notes` com contagem, `medir_rota.py` reconta contra o corpus da
rota e a diferença fica dentro de ±20%. 🔴 **E o denominador vai escrito na própria `notes`**
— *"14 ocorrências no corpus desta rota (43 sessões, 22/08/2026)"* — porque número sem
denominador é o defeito que criou este item.

⚠️ E o exemplar citado acima (`corridor_playbooks.py:377-394`) **tem as 11 telas na ordem e
não tem contagem por tela**. Ele é modelo da sequência, não do controle.

---

### E3 · AS ÂNCORAS — do acervo, nunca de cabeça

**O quê:** cada tela vira `anchor`, extraída **do texto real**.

🔴 **A armadilha nº 1, e ela custou semanas:** 📊 `numero_residencia` exigia
*"informe o número da residência"* — **ZERO ocorrências em 28.092 eventos**. A URA escreve
*"me CONFIRME o número"* — **180 mensagens, 72 sessões**. A tela caía no cérebro toda vez,
custando ~14s numa URA que 📊 **encerra por inatividade a partir de 103s**.

> **REGRA: ampliar âncora é seguro. Trocar não é.**
> `r"(?:informe|confirme) o n[úu]mero"` — o verbo vira opcional, a redação antiga continua
> casando. **É o que o CONTROLE do teste prova.**

🔴 **A armadilha nº 2 — MOTOR DE REGEX TEM DIALETO** (CLAUDE.md §9.4). 📊 Três instâncias na
mesma execução:

```
medido em SQL, aplicado em Python      `.` casa \n no Postgres, não em Python
                                       4 padrões: 37/26/4/3 sessões → ZERO, em silêncio
medido em texto CRU, aplicado sobre    `_norm` remove o `*`
   texto NORMALIZADO                   `\*servi[çc]o\*?:` → de 112 sessões para ZERO
medido com acento, aplicado depois     `necess[áa]rio` funciona; `necessário` perde metade
   do `_norm`
+ `_norm` deixa minúsculo              exigir `[A-Z_]` casa ZERO
+ a URA quebra linha no meio           `[^\n]` bloqueia · `[\s\S]` é obrigatório fora
                                        do `match_ura_step`, o único com DOTALL
```

> **Antes de confiar num número que veio de outra ferramenta, rode-o na ferramenta que vai usá-lo.**

🔴 **A armadilha nº 3 — duas telas que se parecem.** 📊 *"Qual eletrodoméstico precisa de
conserto?"* (CATEGORIA, 4 opções) vs *"Selecione o eletrodoméstico…"* (APARELHO, 15 opções).
Âncoras que **se excluem**, e a ordem da lista é proteção — `match_ura_step` devolve o
primeiro que casa. 📊 Mutação M4: as duas colidindo *"faz o 14 ir para um menu de 4, e engole
o RESUMO junto"*.

🔴 **A armadilha nº 4 — o `noop` largo.** Ele entra **DEPOIS** da confirmação final.
📊 Mutação M2: âncora gulosa casando "agendar" fez o teste responder `1` no RESUMO —
*"abriria chamado de verdade achando que era ensaio"*.

🔴 **A armadilha nº 5 — âncora com máscara.** 📊 **41,1% dos nós `fase='ura'` da allianz**
contêm `{ENDERECO}` ou `###` (147 de 358). ⚠️ Nos 10 mapas inteiros são **26,3%** — a v1
dizia *"41% dos nós do Atlas"*, e o 41 vale só para o recorte allianz × URA.
**Uma âncora com máscara nunca casa tráfego vivo.**

**Controle obrigatório:** toda âncora nova casa **≥1 tela do corpus**, verificado **pelo
motor**. Âncora que casa zero **não entra**.

---

### E4 · AS TECLAS — três fontes, e DEFAULT obrigatório

**O quê:** todo slot `*_opcao` exigido por um passo tem de ter **origem declarada**.

```
1. CONSTANTE no subserviço      + `constante_justificada` se decidir algo
2. DERIVAÇÃO do relato          `_derivar_teclas_do_caso`, com DEFAULT
3. COLETA do cliente            entra em `required_slots`
   (4ª, inline em `new_dispatch_session` — existe, é legítima, precisa ser lida da FONTE)
```

🔴 **Por que o DEFAULT é obrigatório:** 📊 transcript real, 18/08 — a URA pergunta
*"O que aconteceu? 1-Casa sem energia 2-Curto circuito"* → **2 minutos e 22 segundos de
silêncio** → o Founder clicou "1" do próprio celular.

> **Passo que exige slot sem origem não responde E NÃO AVISA. Fica calado.**
> *"A alternativa é o silêncio, e o silêncio custou 2 minutos e 22 segundos."*

🔴 **E o default é a opção HONESTA da própria URA, nunca a primeira tecla.**
📊 `"Não sei"` (8), `"Outros"` (7) — nunca `"Problemas no motor"`, nunca `"Dedetização"`.
📊 `pet_especie_opcao` → `"3 - Outros"`, *"nunca 'Cachorro', que inventaria a espécie"*.

**Três regras de ordem, cada uma paga com um controle vermelho:**
```
a peça NOMEADA vence o sintoma   "não entra marcha, problema no câmbio" dava embreagem
"telhado" CONTÉM "telha"         destelhamento abria troca de telhas em vez de
                                 cobertura provisória — a que impede a casa de
                                 encher de água na mesma noite
o default é a opção honesta      ver acima
```

🔴 **E há slot que NÃO TEM ORIGEM POSSÍVEL.** 📊 `endereco_opcao`: a lista muda, o relato não
diz "opção 1", a corretora não viu a tela. **`fallback_adaptive` é o único caminho honesto, e
falhando ele é handoff — nunca posição fixa.**

**Controles:** um **negativo** (slot que ninguém preenche → reprova) e um **positivo** (slot
que vem da coleta → é achado). 🔴 E a lista de derivados é lida **da FONTE, por AST** —
📊 *"uma lista paralela escrita à mão envelhece calada. É a terceira vez que este repositório
paga por isso."*

---

### E5 · 🔴 A VARREDURA DE COBERTURA DISFARÇADA

**Rode `conferir_respostas.py` nesta rota.** As três perguntas da §3.

**E some a pergunta que só um humano responde:**

> **Esta tecla decide alguma coisa em nome do segurado?**
> Se decide — idade, ramo, endereço, quantidade, aceitar custo — **ela não é constante.**
> Ou vira coleta, ou vira derivação com default honesto, ou vira handoff.

**Controle:** o relatório lista, da rota, **as três coisas que decidem sem perguntar**:

```
toda CONSTANTE          → `constante_justificada` ou a fonte que a substituiu
todo `noop` sobre tela  → `noop_justificado`                          (E13)
   que PEDE algo
todo HANDOFF            → `handoff_justificado`                       (E14)
```

🔴 **Qualquer um dos três sem justificativa reprova.** ⚠️ A v3 criou o `noop_justificado` e
o `handoff_justificado` e deixou este controle — **o único inventário de justificativas da
SPEC** — conhecendo só o irmão mais velho.

---

### E6 · O ISOLAMENTO — `only_subservices`

**O quê:** todo passo exclusivo de uma rota **declara** `only_subservices`.

🔴 **Por que é o item mais replicável de todos:** 📊 os nove passos de eletrodoméstico
nasceram **sem** o filtro. `missing_slots_for_subservice` percorre **todos** os `ura_steps`
recolhendo `requires`, pulando só os que declaram filtro de outra rota.

> **Passo sem filtro vale para todo mundo.**

📊 O estrago medido: `missing_slots_for_subservice(pb, "eletricista", caso)` devolvia
`['periodo_preferido', 'risco_confirmado_sem_fumaca', 'aparelho_marca', 'aparelho_modelo']`
→ `missing_data` → **acionamento de ELETRICISTA bloqueado pedindo a marca de um
eletrodoméstico.** Golden do eletricista: **60 verdes / 15 vermelhas → 86 / 0**.

*"E ninguém viu, porque o guarda da máquina de lavar só olhava o lado certo."*

**Controle:** `test_as_rotas_nao_se_borram.py` já existe e confere a **invariante** em todos
os playbooks: *para cada par de subserviços, um caso preenchido com o que a rota A exige não
pode ficar preso pedindo dado que só a rota B usa.*

---

### E7 · O FREIO E O HANDOFF

**O freio** (`finalize_anchors`) é a última porta antes de mandar um prestador ao endereço
errado — ele arma `_conferir_antes_de_confirmar`.

🔴 **A auditoria obrigatória:** 📊 `allianz-auto` tinha `dados a seguir estão corretos` **desde
sempre**; o residencial não tinha. **154 mensagens / 64 sessões passaram pela conferência SEM
freio.**

> **Diffe `finalize_anchors` entre auto e residencial da MESMA seguradora, item a item.**
> *"Duas famílias da mesma seguradora com listas diferentes é o defeito que ninguém vê,
> porque cada uma parece completa sozinha."*

🔴 **E âncora que só freia e nunca responde é meio passo.** 📊 `_HDI_FAMILY_AGORA_OU_AGENDAR`
estava nos `finalize_anchors` dos dois residenciais e **em nenhum havia `ura_step`**. Em TESTE
o freio dispara e parece correto; **em LIVE o corredor fica calado no ponto de não-retorno.**
**Cruze `finalize_anchors` × `ura_steps`.**

**O handoff:** 📊 na Allianz, *"Vou transferir seu caso para um especialista"* aparece em
**209 eventos / 99 sessões** — e o corredor **não a reconhece**.

> 🔴 **Ele continua falando com um humano achando que é robô.** Uma linha em
> `handoff_triggers`, e vale 3 pontos.

**Controle:** cada âncora de freio e de handoff casa **≥1 tela real do corpus**. Zero
casamentos = não entra.

---

### E8 · OS APELIDOS — do ESPELHO, não do corpus

**O quê:** as palavras que o segurado usa. 📊 A máquina de lavar tem **11**;
`chaveiro`, `bateria` e `pneu` têm **zero**.

🔴 **A armadilha, e ela é sutil:** os apelidos vêm do **Espelho** (`conversations`/`messages`
— o que o CLIENTE escreveu), **não do corpus da URA**.

> 📊 *"'lavadora' marca 23 vezes no corpus da Allianz porque a URA escreve
> **'Lavadora de louças'** no menu Linha Branca — outro eletrodoméstico."*

**Onde minerar:** as conversas da corretora com o segurado, procurando o que ele escreveu
**antes** de a atendente identificar o serviço.

**Controle:** ≥3 apelidos, cada um conferido no Espelho com a contagem. 🔴 E um **controle
negativo**: o apelido não pode casar o nome de **outro** serviço do mesmo menu.

⚠️ 🔴 **E a ferramenta não sabe rodar este controle hoje.** 📊 `rubrica.py:402` tem
`tem_espelho: bool = False` e **ninguém no repositório passa `True`** — não há flag em
`medir_rota.py`. Os 4 pontos ficam permanentemente `SEM_ESPELHO`, e `medir_rota.py:511`
classifica o item como 🧑 **Founder**, enquanto esta estação o entrega ao executor.

```sql
-- ENTREGA DA FASE 0.5 (C6): `medir_rota.py --com-espelho`
-- as mensagens do SEGURADO anteriores ao primeiro acionamento da sessão
select m.content
  from messages m
  join conversations c on c.id = m.conversation_id
 where m.role = 'user'
   and c.company_id = :company_id          -- 🔴 TENANT, sempre
   and c.company_id <> :amandus_id         -- 🔴 A EXCLUSÃO NOMEADA
   and m.created_at < :primeiro_acionamento_da_sessao;
```

🔴 **As duas travas não são negociáveis, e o precedente está escrito no código**
(`canais_observados.py:111`):

> *"a guarda que o juiz exigiu contra a AMANDUS: … se aprendesse do acervo sozinho,
> ingeriria os ensaios da corretora de teste como se fossem prova sobre seguradora real —
> **e a env var que exclui a Amandus é do destilador e não cobriria isto**."*

**O C6 é exatamente outro leitor.** Minerar apelidos sem excluir a Amandus semeia
`_SUBSERVICE_ALIASES` com vocabulário de **conversas fictícias**, e a E8 contaria isso como
prova. 📊 Toda leitura real dessas tabelas no produto já filtra `company_id`
(`human_handoff.py:593`, `admin_atlas.py:964`).

🔴 **Sem a flag, a E8 não tem como fechar e o item fica 🧑, não 🤖.**

---

### E9 · O QUE A ATENDENTE DIZ

**Dois campos, e nenhum é opcional:**

```
regras_para_o_cliente      o que avisar ANTES
                           📊 Allianz: 10 anos · fora da garantia · peças por conta do
                           cliente · 2 utilizações por vigência · o técnico pode levar
                           o aparelho
                           🔴 as cinco existiam SÓ EM COMENTÁRIO. "Comentário não chega
                           a lugar nenhum: nem ao prompt do atendente, nem ao cliente."

expectativa_do_desfecho    o que prometer no fim
                           📊 "conserto AGENDADO: escolhe-se uma data entre os próximos
                           7 dias úteis e um período. NÃO É HOJE."
                           🔴 "Um cliente que ouviu 'vou acionar' e esperava alguém em
                           uma hora liga de volta bravo."
```

🔴 **NÃO reuse `coverage_guardrails`.** Ele existe em três corredores como **lista de
observações internas** marcadas 📊, escritas para quem MANTÉM o corredor. *"Mesmo nome com
dois formatos e dois significados seria o oposto de CLAUDE.md §6."*

**E o conhecimento chega à atendente sozinho:** `conhecimento_de_assistencia()` **gera** o
bloco a partir dos próprios corredores, e o `graph.py` o anexa **só** para
`agent_role == "attendance"` — o mesmo gate que anexa a ferramenta de acionamento.

> 🔴 **GERADO, nunca escrito.** Texto fixo seria segunda fonte de verdade — *"e foi
> literalmente o que aconteceu quando `aparelho_marca_modelo` virou dois campos."*

⚠️ **Três defeitos do próprio gerador, achados gerando e medindo** — o executor tem de
reconferir depois de cada rota nova: (a) agrupar **antes** de deduplicar, senão rotas somem;
(b) agrupar **por rota**, não por corredor×rota — 📊 7.763 → 5.194 caracteres; (c) peneira de
identidade: nome cru de slot e observações internas **não** vão para a fala com o cliente.

**Controle:** `regras_para_o_cliente` tem **≥1 trecho de ≥40 caracteres que CASA o corpus**.

🔴 **E o controle de hoje é FALSO.** 📊 Provado por mutação:

```
HOJE               3/3   trecho: 'seguro automotivo com servicos residenci'
REGRA INVENTADA    3/3   ("O CLIENTE DEVE TRAZER UM ELEFANTE ROSA")  ← NÃO reprovou
SEM REGRA NENHUMA  0/3   ← a linha de CONTROLE: o guarda CONSEGUE ficar vermelho
```

Motivo: `rubrica.py:441-455` procura os 40 caracteres em **qualquer linha de comentário 📊
do bloco**, não dentro de `regras_para_o_cliente`. 🔴 E o trecho que aprova a rota de
referência **nem é uma regra** — é a descrição da apólice.

> **Conserto (entra na FASE 0 como C5):** o trecho tem de ser procurado **dentro do valor
> de `regras_para_o_cliente` da ROTA**, e casar o corpus **dela**.

---

### E10 · O DESFECHO CHEGA AO CLIENTE

**O quê:** protocolo **+ dia + período**. 📊 Hoje: **0 de 73**.

🔴 **A lição de arquitetura, e ela se repetiu três vezes neste repositório:**

> ## O LEITOR NASCE JUNTO COM A CHAVE.
>
> 📊 `schedule_agendado` existia desde 18/08 com **72 asserções em volta**.
> `extract_capture_anchors` lia cinco chaves e **nunca essa**.
> **A Clarissa recebeu *"Prontinho! ✅ Sua assistência foi aberta"* — sem data, sem período.**
>
> Mesma classe: `TETO_DE_INDEFINIDO` declarado e nunca lido · `ticket_de_entrada`.

**Controle:** para cada chave de captura declarada, uma asserção que prova que **o motor a
lê** — não que a regex funciona. 📊 Mutação (renomear a chave) → 6 vermelhas.

⚠️ **E o item de 5 pontos valida a MÁSCARA, não a data.** 📊 A captura devolve
`{'day': 'quinta-feira, {data}'}` e o corpus tem **61 ocorrências de `{DATA}`**. O guarda
prova o encanamento — que o motor lê a chave —, **não que uma data real chega ao cliente**.
É artefato do mascaramento do corpus, **não defeito de produto**; mas o relatório tem de
dizer isso, senão alguém lerá 5/5 como "a Clarissa teria recebido a data".

⚠️ **E um latente, para citar e não consertar às cegas:** 📊 `rubrica.py:325` usa `re.I`; o
motor usa `re.I | re.DOTALL` (`corridor_playbooks.py:5897`). É o dialeto da §9.4 dentro da
régua. **Medido: hoje não muda nenhuma contagem.**

⚠️ **Lacuna aberta que atinge as 73:** o desfecho da URA chega em **bolhas** e o resumo é
montado no primeiro sinal. 📊 Protocolo `16:41:22`, senha `16:41:24` — **a senha chegou
depois do resumo**. Vai para `PENDENCIAS.md`; **não bloqueia esta SPEC.**

---

### E11 · A PROVA

```
✅  CP.extract_capture_anchors(playbook, tela_real)
❌  re.search(playbook["capture_anchors"]["schedule"], tela_real)
```

🔴 **CLAUDE.md §9.4.** 📊 O teste da máquina de lavar tinha **ZERO chamadas ao motor em 401
linhas** — dois helpers próprios, um deles **reimplementando** `match_ura_step`.

**Exceção declarada:** regex sobre a âncora **como texto**, para conferir a FORMA da
declaração, é legítimo.

**Ferramenta:** `detector_do_eixo_e.py` desqualifica o arquivo automaticamente.

**A mutação é EXECUTADA, não declarada.** *"A v1 dava 3 pontos por um COMENTÁRIO dizendo que
a mutação ficou vermelha. **Comentário não fica vermelho.**"*

🔴 **Restauração por CÓPIA, conferida por HASH — nunca `git checkout`**, que apaga trabalho
não commitado; e `git diff --quiet` **nem vê arquivo untracked**.

🔴 **E a armadilha que pegou doze vezes:** 📊 a mutação M1 (remover o derivador) **ficou VERDE
na primeira tentativa** — as 13 asserções chamavam a função **direto**, provando que ela
funciona, não que está **LIGADA**.

> **Função certa e desligada é exatamente o defeito do clique manual.**
> Toda asserção de peça nova prova que ela está **chamada** no caminho real.

---

### E12 · O ENSAIO SECO

**O quê:** do "oi" do segurado ao desfecho, **sem tocar a seguradora**.

```
1. o segurado escreve o apelido → `canonical_subservice` reconhece
2. a atendente sabe o que perguntar → `conhecimento_de_assistencia` traz os slots
3. `missing_slots_for_subservice` devolve VAZIO com o caso completo
4. o replay percorre as telas do corpus e responde todas
5. `client_summary_from_capture` devolve protocolo + dia + período
6. e a última tela do corpus é o desfecho — não uma pergunta sem resposta
```

**Controle:** o ensaio roda **em modo TESTE**, e o freio de finalização **dispara**. 🔴 Se ele
não disparar, a rota **não passou** — o freio é o que impede o ensaio de virar acionamento.

🔴 **E "modo TESTE" tem nome, são três variáveis, e uma delas abre por padrão:**

```
INSURER_DISPATCH_LIVE            portão externo · 📊 FECHADO por padrão
                                 (insurer_dispatch_service.py:320, desde 14/08)
ACIONAMENTO_FREIO_DE_EMERGENCIA  o freio geral
DISPATCH_FINALIZE_MODE           🔴 portão interno · ABRE POR PADRÃO
                                 (l.369: getenv(..., "live"))
```

⚠️ **Confira as três antes de cada ensaio, e cole a saída no relatório.** Numa SPEC cuja
regra é *"nenhuma mensagem enviada"*, um padrão que abre sozinho é a diferença entre ensaio
e acionamento real na casa de um segurado.

---

### E13 · 🔴 O `noop` NÃO É RESPOSTA — e sem esta estação o protocolo se compra

**Esta estação existe porque o item de 20 pontos, o maior da rubrica, tem preço de cinco
linhas.**

📊 Medido pelo juiz, mutação em memória na rota de referência:

```
HOJE                     4 órfãs →  0/20 pts    nota 60/96
COM UM `noop` LARGO      0 órfãs → 20/20 pts    nota 80/96      (+20)
    determinismo ......... 95% → 100%
    respondidas .......... 77 → 77              🔴 INALTERADO
    conferir_respostas ... 0 achados
    --comparar-com ....... VERDE
```

🔴 **Cinco linhas. E o guarda de regressão é cego por construção:** `medir_rota.py:349-356`
só reprova se `respondidas` **cair**. Ficou em 77. Passa.

E o que se compraria é justamente o pior: 📊 duas das quatro órfãs da rota de referência são
o **RESUMO** — o ponto de não-retorno que a armadilha nº 4 da §E3 protege — e
*"1-Cancelar serviço 2-Alterar data/hora"*. **Um `noop` ali faz o corredor ficar calado
exatamente onde a §E4 mediu 2min22 de silêncio.**

> ## A REGRA
>
> **Um `noop` sobre uma tela que PEDE ALGO é silêncio comprado, não cobertura.**

**Controle:** para cada tela classificada `NOOP`, rodar
`tela_pede_alguma_coisa(pb, texto)` (`regua_motor.py:71` — 🔴 **sem** underscore; `_tela_pede_alguma_coisa` é o nome privado do produto). Se `True`, o passo exige um **`noop_justificado`**
escrito — o mesmo padrão de `constante_justificada`.

⚠️ 🔴 **E ele NÃO nasce como gate absoluto.** 📊 Medido nas 73: **257 de 1.066 telas hoje
classificadas `NOOP` já pedem algo.** Ligá-lo como gate reprovaria tudo no primeiro dia.

```
NASCE COMO LINHA DE BASE CONGELADA:
   📊 122 TELAS DISTINTAS (257 ocorrências) em 39 rotas.
      🔴 A unidade é a TELA, como manda a §6.2. A v2 escreveu 257 e foi a
         PRIMEIRA REINCIDENTE da regra que ela mesma acabara de criar.
   o guarda falha só em `noop`-sobre-pergunta NOVO.

🔴 ISTO NÃO É REGRESSÃO DA E13. É defeito PRÉ-EXISTENTE que ela revela.
   Sem ela, os 122 seguiriam invisíveis — e o 123º seria comprado de graça.

🔴 E A DÍVIDA PRECISA DE DONO, senão o guarda CONGELA em vez de consertar:
   📊  63 telas caem em A–E   → saem quando a rota passar pela E13
   📊  59 telas caem FORA     → sem onda, sem pagador  (48%)

   as maiores devedoras estão fora de toda onda nomeada:
      porto × residencial × encanador   23   ← a MAIOR do produto
      azul  × auto × guincho            18   ← azul não está em onda nenhuma
      azul  × auto × bateria            10
      hdi   × residencial × eletricista  8   ← a ONDA C é hdi × AUTO
      yelum × residencial × encanador    8   ← a ONDA D é yelum × AUTO

   → 🔴 A ONDA F deixa de ser "o resto que pontua" e passa a ser
     "o resto que pontua + TODA rota com dívida de linha de base".
   → e o arquivo da linha de base carrega, POR TELA, a ONDA que a paga.
     Tela sem onda no arquivo é entrada inválida.

📊 CONTROLE POSITIVO: com o `noop`-compra plantado, o guarda acende em
   6 telas → VERMELHO. Ele pega.
```

### E14 · 🔴 A ÓRFÃ QUE DEVE CONTINUAR ÓRFÃ

**O item de 20 pontos empurra o executor a responder toda tela. Algumas não devem ser
respondidas.**

📊 Duas das quatro órfãs da rota de referência são:

```
"Caso deseje alterar o atendimento: 1-Cancelar serviço 2-Alterar data/hora
 3-Voltar 4-Sair"
"Esta opção permite alterar apenas data e horário do serviço já solicitado.
 Podemos seguir?"
```

**É a mesma classe que a §3.1 já condena** — `servico_aberto_ver_ou_abrir`, onde responder
"ver o chamado antigo" faz *"o caso morrer sem acionamento"*.

> **A saída legítima existe e tem de estar escrita:** a tela recebe um passo com
> **`outcome` de encaminhamento** e `handoff_justificado` — o corredor **para e avisa**,
> em vez de navegar num galho que não é o dele.
>
> 🔴 **E isso conta como órfã resolvida**, porque o corredor deixou de estar mudo. O que
> não conta é o `noop` (E13).

📊 **A boa notícia, medida:** *"responder `3` (Voltar)"* e *"noop + referral + ENCAMINHA"*
dão **o mesmo 83/96, 0 órfãs, 100% determinismo**. **A escolha certa e a que pontua são a
mesma.** Não há tensão.

⚠️ **Duas ressalvas, e a primeira é a E13 valendo aqui também:** o `noop` desta saída **é
sobre uma tela que pede algo** — ele exige `noop_justificado` como qualquer outro. O que o
autoriza é o `referral` + `ENCAMINHA` ao lado, não o `noop` sozinho.

⚠️ E o `83/96` desta medição contra o `80/96` da §6.2 para o mesmo `n=0`: 📊 a diferença são
os **3 pontos do handoff** (§E7), que a simulação da E14 já tinha ligado. **Não são duas
medições do mesmo estado.**

---

## 5. 🔴 O ATLAS — como usar, e as quatro travas

📊 Auditado em 22/08. **O Atlas é confiável como registro do que a URA disse.**

```
nós no Atlas (allianz) ............ 1.244
nós recalculados do acervo cru .... 1.244
nós INVENTADOS .................... 0        ✅ reproduzido por dois caminhos
âncoras de `ura_steps` sem lastro . 0 de 63  ✅
🔴 âncoras SEM LASTRO no total .... 5 de 76
      finalize:  "posso confirmar" · "deseja confirmar"
      handoff:   "não localizamos" · "cpf.*inválido" · "não foi possível"
```

🔴 **As cinco violam a regra da própria §E3** — *"âncora que casa zero não entra"*. Elas
vivem em `finalize_anchors` e `handoff_triggers`, que a v1 não contava ao dizer "0 de 48".
📊 **E o `48` não existe em nenhum commit** — o playbook tem 63 `ura_steps` (o número foi
45 → 47 → 58 → 63 ao longo de 22/08). **As cinco entram na ONDA A como conserto, ou saem.**

⚠️ E um achado que a v1 não tinha: 📊 **9 dos 358 nós `fase='ura'` da allianz têm
`id ≠ node_hash(texto guardado)`** — o texto gravado derivou do que gerou a chave. Não
invalida o lastro, mas é inconsistência interna real. `PENDENCIAS`.

**Mas:**

> ## 🔴 O ATLAS REGISTRA O QUE FOI FEITO. NÃO SABE O QUE DEVE SER FEITO.
>
> 📊 Tela: *"Em nossa última conversa utilizamos o CPF `708.###.###-34`. Continuar? 1-Sim 2-Não"*
> Os humanos responderam **"1"**. O corredor responde **"2"** — **e o corredor está certo**:
> o WhatsApp da corretora atende muitos segurados, e o CPF anterior é quase sempre de outra
> pessoa. **Copiar a maioria abriria o chamado no CPF do cliente errado.**

### As quatro travas

```
1. só nós `fase='ura'`                    886 dos 1.244 são conversa humana
2. só opções `confidence='confirmed'`     101 das 659 da allianz passam
3. a resposta vem da ARESTA, nunca de `options[].reply`
   📊 em 659/659 o `reply` é cópia byte a byte do `label` — usá-lo mandaria
      "1 - RECARGA DE BATERIA/PANE ELÉTRICA;" onde a URA espera "1"
4. 🔴 revisão humana em toda tela de IDENTIDADE ou de ESCOLHER-ENTRE-EXISTENTE-E-NOVO
```

**E o que o Atlas entrega de melhor:** 📊 a lacuna residencial real da Allianz é de **178
nós** (leitura generosa, todos os subserviços) ou **213** (estrita) — dominada por
**variantes de redação** de telas já cobertas. ⚠️ A v1 dizia 133 e 194; 📊 **nenhum dos dois
reproduz em 224 combinações de casamento testadas**. Dos 178, **59 são de auto** — esse
número reproduz exato.

```
casa:      "informe o complemento do endereço (se houver), e/ou referência do local"  n=91
NÃO casa:  "informe uma referência do local e/ou o complemento do endereço, se houver" n=24
```

> **O ganho é ALARGAR âncora, não escrever passo novo.** E alargar é seguro (E3).

⚠️ **Antes de usar o Atlas de hdi e yelum:** o primeiro nome entra no hash e **parte a
mesma tela em vários nós**. 📊 Medido com o vocativo mascarado e reagrupado:
**hdi + yelum = 6 telas reais partidas em 17 nós** (hdi 4 · yelum 13). ⚠️ A v1 dizia
*"38 nós, hdi 17 → 13 telas"* — o 17 é a soma das duas, e são **6** telas.

📊 E o `templatize` de hoje **não altera nenhum** dos 668 nós URA de hdi+yelum — mascarar é
trabalho a fazer, não conferência. **A allianz não é afetada.**

⚠️ **E os 10 mapas são `ramo='todos'`.** Não existe mapa residencial: 📊 59 dos 194 nós URA sem
resposta da allianz são de **auto**.

---

## 6. A ORDEM DE EXECUÇÃO

### 6.1 As ondas

```
FASE 0    a régua (C1·C3·C4·C5 + C2)                  ~70 min   ← antes de tudo
FASE 0.5  o leitor do Espelho (C6)                              ← destrava a E8;
                                                                  sem ela os apelidos
                                                                  ficam SEM_ESPELHO
FASE 1    a varredura de segurança nas 73              ~2 h      ← antes de qualquer rota
ONDA A    allianz × residencial   (9)      ─┐
ONDA B    allianz × auto          (4)       │  🔴 as 31 PRIORITÁRIAS
ONDA C    hdi × auto              (5)       │  📊 hoje 4 chegam a 60
ONDA D    yelum × auto            (5)       │     e 6 delas são SEM_CORPUS
ONDA E    porto × auto            (8)      ─┘
ONDA F    as 16 fora de A–E que pontuam
          🔴 e 15 das 16 são OBRIGATÓRIAS: carregam as 59 telas da dívida
             do E13. A única opcional é yelum × residencial × eletrodomesticos.
             📊 "o resto" deixou de ser resto.
ONDA G    as 26 SEM_CORPUS fora de A–E              só lista de coleta
```

🔴 **A ONDA A está DENTRO das 31 prioritárias.** 📊 A chave do diagrama da v1 abrangia só
B–E, que soma 27 — e o "31" e o "4" só fecham com A incluída: `9+4+5+5+8 = 31`, e
`≥60 em A–E = 4` (contra **2** em B–E).

🔴 **E as ondas NÃO são uma partição.** 📊 **6 das 31 rotas de A–E são elas mesmas
`SEM_CORPUS`** (B 1 · C 1 · D 1 · E 3) — a ONDA G as reivindicaria de novo. Fora de A–E há
**42** rotas: **16 pontuadas + 26 SEM_CORPUS**.

⚠️ **E as duas melhores rotas do produto ficam fora de todas as ondas nomeadas:**
📊 `alfa × auto × guincho` **73/96** e `alfa × auto × pneu` **71/96** caem na ONDA F.
**Leia as duas antes de começar a ONDA A** — elas são o modelo do que uma rota bem feita
parece hoje.

🔴 **Dentro de cada onda, por demanda medida** (escolha real, nunca cardápio):

🔴 **A lista da v1 desta SPEC estava errada em 9 de 10.** 📊 A fonte real é
`padroes_de_servico.py:478` (`DEMANDA_MEDIDA`), lida por `medir_rota.py:423`:

```
                  a v1 dizia   📊 ESCOLHIDO   (cardápio)
guincho                65           72           197
bateria                18           16           106
encanador              18           14           132
eletricista            13           12           109
pneu                   10           10           101
eletrodoméstico         5            9           102
socorro mecânico       24            7            70
chaveiro               12            5           210
vidros                  2            1            77
🔴 carro reserva       16            0            75
```

🔴 **`carro reserva` é o erro que carrega peso: ZERO escolhas no acervo inteiro.** E o
cabeçalho do próprio `padroes_de_servico.py` existe literalmente para avisar disso:

> *"carro reserva e martelinho de ouro aparecem em 75 e 57 sessões de cardápio e em **ZERO**
> escolhas no acervo inteiro. São itens de menu, não demanda."*

**A v1 escrevia *"por demanda medida, nunca cardápio"* e colocava em 5º lugar o exemplo
canônico de contaminação por cardápio.**

⚠️ E `vidros` mede 0 no inventário por outro motivo: 📊 a chave do código é `vidro`,
singular, e a rota se chama `vidros`. **É defeito de chave, não ausência de demanda** —
vai para `PENDENCIAS`.

**A ordem correta, do código:**

```
guincho 72 · bateria 16 · encanador 14 · eletricista 12 · pneu 10
eletrodoméstico 9 · socorro mecânico 7 · chaveiro 5 · vidros 1 · carro reserva 0
   e a cauda, que a ONDA A precisa:
ar_condicionado 2 · limpeza_caixa_dagua 2 · pet 2 · desentupimento 1
```

🔴 **E a ONDA A — a PRIMEIRA — não tem ordem para 5 das suas 9 rotas.** 📊
`maquina_de_lavar` **não tem chave própria em `DEMANDA_MEDIDA`**: ela está diluída dentro de
`eletrodomestico 9`. **A rota de referência desta SPEC inteira não tem entrada de demanda.**

⚠️ Vai para `PENDENCIAS` junto com o `vidro`/`vidros`: são os dois defeitos de **chave** do
`padroes_de_servico.py`, e nenhum é ausência de demanda.

**Enquanto isso, a ordem da ONDA A é:** `encanador 14 · eletricista 12 · eletrodoméstico 9
(inclui máquina de lavar) · chaveiro 5 · desentupimento 1 · ar_condicionado 2 ·
limpeza_caixa_dagua 2` — 🔴 **e a máquina de lavar vai PRIMEIRO de todas**, porque é a rota
de referência e o executor precisa dela fechada para ter contra o que comparar.

### 6.2 🔴 Tudo ou quase nada

📊 **Os dois números estão certos — e só fecham por uma leitura que a v1 não declarava.**

O item é uma **escada de quatro degraus** (`rubrica.py:263`), não tudo-ou-nada:

```
pts = 20 if n == 0 else 10 if n == 1 else 4 if n == 2 else 0
```

🔴 **E a rota tem 4 OCORRÊNCIAS em 3 TELAS distintas** — o `*RESUMO*` aparece **duas
vezes**, e as duas cópias diferem só nos valores do agendamento (📊 similaridade 0,947).
**Uma âncora casa as duas.**

```
escrever a âncora do RESUMO   →  n = 2  →   4 pts  →  64/96   ← paga em dobro
escrever as três telas        →  n = 0  →  20 pts  →  80/96
```

🔴 **E o modo de falha que precisa estar escrito:** um executor que consertar **uma órfã
qualquer que NÃO seja o RESUMO** mede `60/96` — **ganho zero**, porque o penhasco `≥3 → 0`
engole o conserto. Ele vai achar que a régua está quebrada, e ela não está.

⚠️ **Esta SPEC usa "órfã" para duas grandezas, e nomeá-las é obrigatório:**

```
4  OCORRÊNCIAS       o que a rubrica conta
4  TEXTOS DISTINTOS  os dois RESUMOs diferem (terça/13h-18h vs sexta/9h-13h,
                     primeira diferença no char 124)
3  CLASSES DE ÂNCORA o que o executor escreve  ← 🔴 esta é a unidade do trabalho
```

🔴 **"3 telas distintas" seria o nome que mente** — e o `CLAUDE.md` §12.1 manda consertar o
nome, não o texto. São **3 classes de âncora**, e uma delas casa dois textos.

**Toda vez que esta SPEC disser "órfã", ela diz qual das três.**

> **O protocolo exige o GALHO INTEIRO.** Rota que passa por 8 das 14 estações não é
> 66% pronta — é uma rota com furo coberto, que é o que esta SPEC existe para não produzir.

### 6.3 O paralelismo

🔴 **A justificativa da v1 estava errada, e a medição a derruba:** ela dizia *"nunca duas
rotas do mesmo corredor, tocam o mesmo arquivo"*. 📊 `wc -l corridor_playbooks.py` →
**7.219 linhas**, e **os 14 playbooks das 10 seguradoras moram nesse arquivo único**. A
justificativa vale para **todo par**, não só para o mesmo corredor.

📊 Pior: `_auto_playbook()` (l.1367) é **fábrica compartilhada por 10 seguradoras**, e
`_PLAYBOOKS_AUTO_COM_PNEU` (l.4942) é montado a partir de 10 playbooks. Dois subagentes em
`allianz × auto` e `hdi × auto` são puxados para **a mesma fábrica**.

```
✅  um SUBAGENTE por rota, até 4 em paralelo — 🔴 CADA UM NO SEU WORKTREE
    (`isolation: "worktree"`), porque as 73 rotas moram num arquivo só
🔴  a INTEGRAÇÃO É SERIAL: um merge por vez, e `--comparar-com` DEPOIS DE CADA
    MERGE — nunca só depois da rota
🔴  NUNCA dois subagentes na mesma FÁBRICA (`_auto_playbook`, `_PLAYBOOKS_*`),
    mesmo de seguradoras diferentes
```

---

## 7. 🔴 OS JUÍZES

**O executor não libera o próprio trabalho.**

### 7.0 🔴 JUIZ 0 · O CÉTICO DA RÉGUA — para a FASE 0 e a FASE 1

**A Fase 0 mexe no instrumento de medida, e a v1 desta SPEC não dava juiz a ela.** O
executor trocaria a régua e se autoliberaria — e a proibição da §2.2 (*"afrouxar limiar,
remover item, renormalizar"*) seria **só uma frase, sem teste que a detecte**.

```
🔬 JUIZ 0 · O CÉTICO DA RÉGUA
   📊 rode as 73 com a régua VELHA e com a NOVA, lado a lado.
      Para cada rota que subiu: o ganho veio de qual item?
   🔴 alguma rota subiu SEM que nada nela mudasse por um motivo NOMEÁVEL?
      → é afrouxamento, e o conserto volta.
   algum limiar mudou? algum item saiu do denominador? alguma nota foi
      renormalizada?
   e o conserto tem MUTAÇÃO, executada e vermelha?
```

**Controle — e ele é POR CONSERTO, não por Fase 0.** 🔴 A v2 dizia *"reintroduz **um dos**
consertos"*: testa 1 e passa com 5 não verificados.

```
para CADA Cᵢ dos SEIS, um de cada vez:

  ① guarde a régua velha, executável:
     git show <commit-base>:backend/scripts/rubrica.py > /tmp/rubrica_v0.py
     🔴 sem isto o Juiz 0 não tem contra o que comparar — a Fase 0
        SUBSTITUI a régua num commit

  ② reverta SÓ o Cᵢ e rode as 73 com as duas réguas

  ③ 🔴 IDENTIDADE DE CONJUNTO — e é aqui que o teste global falha:
     o conjunto de rotas que muda tem de ser EXATAMENTE o que a §2.1
     declara para o Cᵢ.  📊 C1+C2 = 21 · C3 = 16 · C4 = 7 · C5 e C6 = o
     número medido de cada um.
     Uma rota a mais ou a menos REPROVA.
     ⚠️ Delta global ≠ 0 NÃO BASTA: um conserto que sobe 21 rotas e
        derruba 21 outras dá delta e está errado.

  ④ e a DIREÇÃO tem de bater. 🔴 O C4 SUBTRAI de propósito: 7 rotas caem
     −3 porque paravam de receber crédito indevido.
     Queda declarada é aprovação. Queda NÃO declarada é reprovação —
     e a v2 não tinha regra para rota que cai.

🔴 Um Cᵢ não testado é um Cᵢ REPROVADO. Não existe "amostra de conserto".
```

### 7.1 As três lentes, por rota

```
🔍 JUIZ 1 · O CÉTICO DA COBERTURA
   as 14 estações foram TODAS cumpridas, ou alguma foi pulada por ser "óbvia"?
   🔴 a E13 rodou? alguma tela virou `noop` sem `noop_justificado`?
   alguma âncora nova casa ZERO no corpus?
   o replay ainda acha órfã funcional?
   📊 e o número subiu por trabalho, ou por afrouxamento?

🛡️ JUIZ 2 · O CÉTICO DA SEGURANÇA
   alguma constante DECIDE algo em nome do segurado sem `constante_justificada`?
   o freio dispara no ensaio seco?
   o handoff casa tela real?
   🔴 e a pergunta da §3: se esta tecla estiver errada, o que acontece com o cliente?

🧍 JUIZ 3 · O CÉTICO DO SEGURADO
   o segurado é reconhecido pelo apelido que ele usaria?
   a atendente sabe o que avisar ANTES?
   o cliente recebe protocolo + dia + período?
   ele sabe que NÃO é hoje, quando não é hoje?
```

### 7.2 O laço

```
① o executor entrega a rota
② o juiz da lente julga, e ENTREGA A MEDIÇÃO junto
③ o executor conserta
④ 🔴 O MESMO JUIZ julga DE NOVO
⑤ repete até liberar

TETO: 3 voltas por rota. Bateu sem liberar → `PRECISA_DE_HUMANO` com dossiê.
🔴 NUNCA um verde forçado.
⚠️ Reprovação sem motivo acionável NÃO conta como volta — 🔴 **e quem decide se é
acionável é o JUIZ, não o executor**, que se beneficiaria da decisão.
```

### 7.3 A regra que vale para o juiz também

📊 Nas rodadas que produziram a SPEC-083, a SPEC-084 e esta, **CINCO prescrições de juiz foram
derrubadas pela query seguinte**.

> **Nenhuma regra entra sem a query que a produziu e o controle que pode reprová-la —
> inclusive as que o juiz escrever.**
>
> 🔴 **E a quinta derrubada registra POR QUE ele errou:** o juiz mediu com a âncora
> `\*resumo\*` e **o `_norm` remove o `*`**. Ele caiu na armadilha nº 2 da §E3 — *dentro da
> SPEC que a documenta*. **O juiz também roda o padrão na ferramenta que vai usá-lo.** Prescrição sem medição, o executor **reproduz antes de
> aplicar**; e se não reproduzir, devolve com o número.

---

## 8. O GATE FINAL

```
· FASE 0 fechada, em commit separado, sem tocar playbook
· FASE 0.5 fechada — **ou** a E8 declarada `SEM_ESPELHO` nas 73, nunca omitida
· FASE 1 devolve ZERO, e a ferramenta fica VERMELHA com um defeito reintroduzido
· toda rota trabalhada passou pelas **14** estações — 🔴 **E13 e E14 inclusas** —
  e pelas **3 lentes por rota** (§7.1). 🔴 São **4 lentes ao todo**: o JUIZ 0
  governa a FASE 0, a 0.5 e a FASE 1, que também estão neste gate.
· 🔴 FASE 0 e FASE 1 liberadas pelo **JUIZ 0** (§7.0), nunca pelo executor
· a LINHA DE BASE do E13 gravada, com a ONDA que paga cada tela declarada
· `--comparar-com` verde em TODAS: nenhuma rota perdeu respondidas
· o INVENTARIO regenerado, com carimbo de commit e hora
· 🔴 e o relatório diz, por rota: a nota ANTES, a nota DEPOIS, e QUAL ESTAÇÃO
     produziu cada ganho
```

⚠️ **A nota final de cada rota não é o gate.** 📊 O gate é: **as 14 estações cumpridas, e o
que ficou de fora nomeado com o que destrava.**

> **Uma rota em 51 com o bloqueio nomeado é ENTREGA. Uma rota em 95 com furo invisível não é.**

---

## 9. O QUE FICA DE FORA

| item | por quê | vai para |
|---|---|---|
| a senha que chega 1 s tarde | é do motor de acionamento, não da rota | SPEC-085 |
| o `_norm` sem `strip()` e sem U+00AD | é do motor, e esta SPEC não muda motor sem mutação própria | PENDENCIAS |
| mascarar nome no `templatize` do Atlas (hdi/yelum) | precisa re-tecer os mapas | PENDENCIAS 🔴 antes da ONDA C/D |
| as **32** rotas `SEM_CORPUS` — 📊 **26 fora de A–E + 6 dentro** (§6.1) | precisam de acionamento real | LISTA-DE-COLETA |
| mapa do Atlas por ramo | hoje os 10 são `ramo='todos'` | PENDENCIAS |
| 🔴 o acesso ao Espelho, se a FASE 0.5 não for feita | sem `--com-espelho` a E8 fica `SEM_ESPELHO` nas 73 e os 4 pts dos apelidos são inalcançáveis | PENDENCIAS 🧑 |
| `maquina_de_lavar` e `vidro`/`vidros` sem chave em `DEMANDA_MEDIDA` | defeito de chave, não ausência de demanda (§6.1) | PENDENCIAS 🤖 |

---

## 10. RELATÓRIO FINAL

Além do template padrão:

⚠️ 📊 **Esta seção era byte-idêntica à v1 até a v4** — três versões de correção, e a
seção que **registra** o trabalho nunca se moveu. É a mesma família de defeito que os dois
blockers da v3: *a cura entra e não sobe para onde é cobrada.*

```
· a tabela das 73: nota ANTES · nota DEPOIS · estação que produziu o ganho

· 🔴 o DELTA DA FASE 0 — COM SINAL e POR CONSERTO, nunca "quanto subiu":
     C1+C2 · C3 · C4 (📊 NEGATIVO: −3 em 7 rotas) · C5 · FASE 0.5 (C6)
     ⚠️ "quanto subiu" era um nome que mente sobre o que guarda — a Fase 0
        tem um conserto que SUBTRAI de propósito (CLAUDE.md §12.1)

· 🔴 o veredito do JUIZ 0, POR CONSERTO, com a IDENTIDADE DE CONJUNTO:
     para cada Cᵢ, as rotas que mudaram × as que a §2.1 declara.
     Conjunto diferente reprova, mesmo com o delta global certo.

· 🔴 a LINHA DE BASE do E13: quantas das 122 telas distintas foram pagas,
     por qual onda, e quantas restam    📊 63 em A–E · 59 na ONDA F

· 🔴 o inventário das TRÊS justificativas: quantos `constante_justificada`,
     `noop_justificado` e `handoff_justificado` a execução criou, e quantas
     telas cada um cobre

· quantas constantes viraram coleta ou derivação na FASE 1
· as rotas que bateram o teto de 3 voltas, com o dossiê
· 📊 e a lista do que trava cada rota de chegar a 96, com o que destrava
```
