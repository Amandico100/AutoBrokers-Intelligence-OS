# SPEC-084.1 — O ENSAIO

> **O protocolo que leva cada uma das 73 rotas ao nível da máquina de lavar — não o de 19/08, mas o de depois do que aprendemos com ela.**
>
> Autor: execução · **v1, 22/08/2026** · base `10abc94` · branch da SPEC-084
> Precondição: SPEC-083 ✅ · SPEC-084 blocos 0–5 ✅

---

## 0. PREFLIGHT

```bash
git rev-parse --show-toplevel        # AutoBrokers-FIX
git status --short                   # limpo
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial \
       --servico maquina_de_lavar
# tem de responder 60/96 e listar o que falta. Se não responder, PARE.
```

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
o corredor fala com a URA .............. 41 de 73    média 47,8/96
a atendente sabe conduzir o cliente ....  2 de 73    regras_para_o_cliente
o cliente recebe protocolo+dia+período .  0 de 73    client_summary
alguém provou ponta a ponta ............  1 de 73

apelidos: maquina_de_lavar 11 · guincho 6 · vidros 5 · encanador 2
          🔴 chaveiro 0 · bateria 0 · pneu 0
```

🔴 **Zero apelidos significa que o acionamento morre antes de começar.** Comentário no
próprio código: *"Sem estes apelidos, `canonical_subservice` devolve o próprio texto,
`subservices` não acha, e o acionamento morre antes de começar."*

### 1.2 O teto é 96/96, e nada falta de evidência

📊 Simulado em memória com a rubrica real, na rota de referência:

```
dos 36 pontos que faltam:
   36  são TRABALHO      a evidência JÁ ESTÁ no corpus
    0  são COLETA
    0  são ARQUITETURA

60/96  hoje
83/96  só com trabalho de ROTA        (+23)
96/96  + consertos da RÉGUA           (+13)
```

---

## 2. 🔴 FASE 0 — A RÉGUA PRIMEIRO, EM COMMIT SEPARADO

**Antes de tocar em qualquer rota.** 📊 Dois itens da rubrica falham em **73 de 73** — não porque ninguém fez, mas porque **a ferramenta não consegue passar**. São o defeito que a SPEC-083 §3.3 nomeia, dentro da própria régua.

### 2.1 Os quatro consertos

| # | onde | o defeito | 📊 |
|---|---|---|---|
| **R1** | `rubrica.py:289` | monta a chave `"capture"`; `client_summary_from_capture` lê `"captured"` → devolve `None` **sempre** | 0/73 |
| **R2** | `insurer_dispatch_service.py:2384-2390` | lê `schedule["from"/"to"/"at"/"day"]` e **nunca** `schedule["periodo"]`. A captura tem `'periodo': 'tarde das 13:00 as 18:00'` e ele é descartado | 0/73 |
| **R3** | `rubrica.py:325` | o denominador das `notes` reconta contra o acervo inteiro, não contra o corpus da rota | 0/73 |
| **R4** | `rubrica.py:365` | não filtra `only_subservices` ao cobrar origem de tecla — cobra teclas de outra rota | 5 teclas |

🔴 **R2 é o furo nº 3 da Clarissa, ainda aberto.** É por ele que ela recebeu *"Prontinho! ✅ Sua assistência foi aberta"* **sem data e sem período** — e depois ficou escondido atrás de um item que não sabia medi-lo.

### 2.2 Por que separado, e é regra da SPEC-083

> *"Medir a coisa e mudar a coisa no mesmo commit é como se perde a régua. Se a nota
> subir, ninguém sabe se foi a rota que melhorou ou a medida que afrouxou."*

```
GATE DA FASE 0
· os 4 consertos em UM commit que não toca nenhum playbook
    🔴 `git status backend/app/services/corridor_playbooks.py` LIMPO
    ⚠️ exceção: R2 é em insurer_dispatch_service.py — é motor, não corredor.
       Commit próprio, com mutação.
· `--todas` roda e a tabela das 73 é regravada  →  é a LINHA DE BASE
· 📊 e o relatório diz, rota a rota, quanto subiu SÓ pelo conserto da régua
    (esperado: até +7 por rota; 7 × 73 = 511 pontos de leitura)
· mutação em cada conserto, EXECUTADA e vermelha
```

⚠️ **E o que NÃO é permitido na Fase 0:** afrouxar limiar, remover item, renormalizar
nota. Os quatro são bugs de leitura — se algum exigir mudar a régua para passar, **não é
Fase 0**, é mudança de rubrica e vai para o juiz.

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

```
1. `conferir_respostas.py --todas` roda e devolve ZERO
2. 🔴 e um RELATÓRIO nomeando, para cada constante que decide algo em nome do
   cliente, a `constante_justificada` que a autoriza — ou o passo que a substituiu
   por coleta
3. GATE: reintroduza um dos 8 defeitos históricos. Se a ferramenta ficar VERDE,
   ela está cega e a fase não fecha.
```

🔴 **Nenhuma rota vai a teste ao vivo antes desta fase fechar.**

---

## 4. 🔴 O PROTOCOLO — as 12 estações, uma rota por vez

**Toda rota passa pelas 12. Sem exceção, sem "esta é simples".**

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

🔴 **A armadilha:** a contagem tem de **reconter contra o corpus da rota**, não contra o
acervo inteiro. 📊 `menu_tipo_servico` declarava 64 e o acervo Allianz tem 147.

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

🔴 **A armadilha nº 5 — âncora com máscara.** 📊 **41% dos nós do Atlas** contêm `{ENDERECO}`,
`###`. **Uma âncora com máscara nunca casa tráfego vivo.**

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

**Controle:** o relatório lista **toda** constante da rota e, ao lado, a
`constante_justificada` ou a fonte que a substituiu. **Constante sem uma das duas reprova.**

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
Regra escrita de cabeça reprova.

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

---

## 5. 🔴 O ATLAS — como usar, e as quatro travas

📊 Auditado em 22/08. **O Atlas é confiável como registro do que a URA disse.**

```
nós no Atlas (allianz) ............ 1.244
nós recalculados do acervo cru .... 1.244
nós INVENTADOS .................... 0
âncoras do corredor sem lastro .... 0 de 48
```

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

**E o que o Atlas entrega de melhor:** 📊 a lacuna residencial real da Allianz é de **133 nós**
— e é dominada por **variantes de redação** de telas já cobertas.

```
casa:      "informe o complemento do endereço (se houver), e/ou referência do local"  n=91
NÃO casa:  "informe uma referência do local e/ou o complemento do endereço, se houver" n=24
```

> **O ganho é ALARGAR âncora, não escrever passo novo.** E alargar é seguro (E3).

⚠️ **Antes de usar o Atlas de hdi e yelum:** 📊 **38 nós `fase='ura'`** trazem primeiro nome
sem máscara, e o nome **entra no hash e parte a mesma tela em dois nós** — hdi: 17 nós para 13
telas reais. **Mascarar no `templatize` e re-tecer.** A allianz não é afetada.

⚠️ **E os 10 mapas são `ramo='todos'`.** Não existe mapa residencial: 📊 59 dos 194 nós URA sem
resposta da allianz são de **auto**.

---

## 6. A ORDEM DE EXECUÇÃO

### 6.1 As ondas

```
FASE 0    a régua                                      ~70 min   ← antes de tudo
FASE 1    a varredura de segurança nas 73              ~2 h      ← antes de qualquer rota
ONDA A    allianz × residencial   (6 rotas)            a maior demanda residencial
ONDA B    allianz × auto          (4)      ─┐
ONDA C    hdi × auto              (4)       │  as 31 prioritárias
ONDA D    yelum × auto            (4)       │  📊 hoje 4 chegam a 60
ONDA E    porto × auto            (5+4)    ─┘
ONDA F    o resto que pontua               (~14)
ONDA G    as 32 SEM_CORPUS                            só lista de coleta
```

🔴 **Dentro de cada onda, por demanda medida** (escolha real, nunca cardápio):

```
guincho 65 · socorro mecânico 24 · bateria 18 · encanador 18 · carro reserva 16
eletricista 13 · chaveiro 12 · pneu 10 · eletrodoméstico 5 · vidros 2
```

### 6.2 🔴 Tudo ou quase nada

📊 Medido na rota de referência: só a órfã mais fácil → `64/96`. **As três juntas → `80/96`.**

> **O protocolo exige o GALHO INTEIRO.** Rota que passa por 8 das 12 estações não é
> 66% pronta — é uma rota com furo coberto, que é o que esta SPEC existe para não produzir.

### 6.3 O paralelismo

```
✅  um SUBAGENTE por rota, até 4 em paralelo — rotas de seguradoras diferentes
🔴  NUNCA duas rotas do mesmo corredor em paralelo: tocam o mesmo arquivo
🔴  E depois de CADA rota: `--comparar-com` a linha de base.
    Nenhuma outra rota daquela seguradora pode ter perdido respondidas.
```

---

## 7. 🔴 OS JUÍZES

**O executor não libera o próprio trabalho.**

### 7.1 As três lentes, por rota

```
🔍 JUIZ 1 · O CÉTICO DA COBERTURA
   as 12 estações foram TODAS cumpridas, ou alguma foi pulada por ser "óbvia"?
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
⚠️ Reprovação sem motivo acionável NÃO conta como volta.
```

### 7.3 A regra que vale para o juiz também

📊 Nas quinze rodadas que produziram a SPEC-083 e a 084, **quatro prescrições de juiz foram
derrubadas pela query seguinte**.

> **Nenhuma regra entra sem a query que a produziu e o controle que pode reprová-la —
> inclusive as que o juiz escrever.** Prescrição sem medição, o executor **reproduz antes de
> aplicar**; e se não reproduzir, devolve com o número.

---

## 8. O GATE FINAL

```
· FASE 0 fechada, em commit separado, sem tocar playbook
· FASE 1 devolve ZERO, e a ferramenta fica VERMELHA com um defeito reintroduzido
· toda rota trabalhada passou pelas 12 estações e pelos 3 juízes
· `--comparar-com` verde em TODAS: nenhuma rota perdeu respondidas
· o INVENTARIO regenerado, com carimbo de commit e hora
· 🔴 e o relatório diz, por rota: a nota ANTES, a nota DEPOIS, e QUAL ESTAÇÃO
     produziu cada ganho
```

⚠️ **A nota final de cada rota não é o gate.** 📊 O gate é: **as 12 estações cumpridas, e o
que ficou de fora nomeado com o que destrava.**

> **Uma rota em 51 com o bloqueio nomeado é ENTREGA. Uma rota em 95 com furo invisível não é.**

---

## 9. O QUE FICA DE FORA

| item | por quê | vai para |
|---|---|---|
| a senha que chega 1 s tarde | é do motor de acionamento, não da rota | SPEC-085 |
| o `_norm` sem `strip()` e sem U+00AD | é do motor, e esta SPEC não muda motor sem mutação própria | PENDENCIAS |
| mascarar nome no `templatize` do Atlas (hdi/yelum) | precisa re-tecer os mapas | PENDENCIAS 🔴 antes da ONDA C/D |
| as 32 rotas `SEM_CORPUS` | precisam de acionamento real | LISTA-DE-COLETA |
| mapa do Atlas por ramo | hoje os 10 são `ramo='todos'` | PENDENCIAS |

---

## 10. RELATÓRIO FINAL

Além do template padrão:

```
· a tabela das 73: nota ANTES · nota DEPOIS · estação que produziu o ganho
· quanto subiu SÓ pela FASE 0 (o conserto da régua), separado do resto
· quantas constantes viraram coleta ou derivação na FASE 1
· as rotas que bateram o teto de 3 voltas, com o dossiê
· 📊 e a lista do que trava cada rota de chegar a 96, com o que destrava
```
