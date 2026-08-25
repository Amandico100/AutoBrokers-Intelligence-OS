# SPEC-092 · Relatório de execução — o formulário dentro do WhatsApp

> Branch `feat/spec092-o-formulario-dentro-do-whatsapp`
> · início `8b49fdb` · **final `88d2f31`**
>
> ```
> 30eaada  A        o convite deixa de virar linha em branco
> 74dfbbb  B        o convite passa a ser LIDO — e não era o rótulo
> 34f0a93  C        o flow_id ecoado é o da seguradora
> 807e276  D.3 + E  o version medido, o format honesto
> 73d6e9c  D.2+F.2  a tela decide antes do passo; a prova não sai de casa
> 00b1a89  F.3+F.4  o ensaio exercita o formulário
> dec2a74  painel   cinco lentes, dezessete achados
> 88d2f31  juiz     três blockers — e dois eram consertos que não consertavam
> ```
> Escrita sob o `PROTOCOLO-AUTOBROKERS-AAA.md` **v9**
>
> 📊 medido · 💭 ilustrativo (`CLAUDE.md` §12.1). Número sem marca, aqui, é defeito.

---

## 0.1 TELEMETRIA — 🔴 §11 do protocolo

| | |
|---|---|
| branch criada | `08:46:23` |
| **primeira linha de código de produto** | **`08:53:08` — 6 min 45 s depois** |
| último commit de construção | `10:05:47` |
| construção (A→F) | **1 h 07 min**, 6 commits |
| **pedágio de leitura** | 📊 **87.855 bytes** — protocolo 28.121 · SPEC 27.724 · `CLAUDE.md` 21.491 · `O-FORMULARIO` 10.519 |
| o que a §1 da v9 **proibiu** ler | 📊 **421.146 bytes** (`PENDENCIAS.md`) — **83% do pedágio evitado** |
| painel (5 lentes, em paralelo) | 📊 **~32 min** de relógio · 5 lentes · **17 achados**, zero sobreposição total |
| juiz de confirmação | 📊 **~20 min** · **3 blockers**, dois deles consertos do painel |
| **rodadas de painel** | **1** (o teto do protocolo é 3) |
| **defeitos que o painel NÃO pegou** | 📊 **3** — todos pegos pelo juiz de confirmação, e 2 eram consertos do próprio painel |
| **razão docs/código na execução** | 📊 **0,000** — 2.378 linhas de código, **zero** de `.md` |

🔴 **A v9 mediu a si mesma e acertou.** 📊 O número que a motivou era *"9h25 até
a primeira linha de código da SPEC-085"* e *"razão docs/código 0,74"*. Aqui:
**6min45** e **0,000**. As duas causas que ela nomeou — o pedágio de entrada e o
juiz comprando documento — não se repetiram.

⚠️ **O que NÃO medi:** o relógio entre a mensagem do Founder e a criação da
branch (o aquecimento das quatro perguntas aconteceu ali e não tem carimbo).
Então o `6min45` é *branch → código*, não *pedido → código*.

---

## 🔴 O AQUECIMENTO (§5.2) — e ele achou o que mudaria a SPEC

As quatro perguntas foram respondidas **medindo**, antes de ler a SPEC.

### 1 · 📊 Quantas vezes o formulário foi respondido, por seguradora

```
observed_events · msg_type='flow_reply' · direction='out'
   porto  27  (9 sessões)  até 28/05/2026   100% history_sync
   yelum  14  (8 sessões)  até 19/08/2026   7 history + 7 LIVE
   hdi    11  (6 sessões)  até 18/07/2026   10 history + 1 LIVE
   azul   10  (4 sessões)  até 29/05/2026   100% history_sync
   ─────  62 · 27 sessões · 4 seguradoras
attendance_transcripts (155.624 linhas) ............ ZERO
```

Bate com a SPEC §2.2 número a número. **Mas 62 é o número que engana:** só **8**
são `live`, e só nessas sobrou conteúdo. As 54 de `history_sync` guardaram
`sorted(m.keys())` — 📊 zero `flow_id`, zero `flow_token`, zero payload. **Porto
e Azul são 37 dessas 54.**

### 2 · 📊 O convite está no acervo?

**Zero. Nos dois acervos.** E medi o que ficou no lugar dele: nas 12 respostas
mais recentes, **o convite foi gravado como `buttons` com `options: []`** — de
13 a 20 segundos antes da resposta, `source=live`, inclusive a de 19/08.

### 3 · 🔴 "O caminho de ENVIO está provado e correto" — **REFUTADO**

| campo | o código manda | as capturas reais |
|---|---|---|
| `version` | `1` | **`3`** — 📊 4 de 4 |
| `body.format` | `"EXTENSIONS"` | **`1`** — 📊 4 de 4 |
| `wa_flow_response_params` | `{flow_id, flow_name}` | **`{flow_id, flow_name, response_message, title}`** |

E o erro maior é estrutural: **o envio exige `flow_token`, que só vem do convite,
que nunca era reconhecido.** O cano provado em 03/08 nunca recebeu água.

### 4 · 🔴 O que eu NÃO entendia (e o que disso ficou de pé)

1. **Qual o rótulo real do botão de ENTRADA** — ✅ **resolvido por medição**: é
   `galaxy_message`, lido no `quotedMessage` de 4 capturas.
2. **Se `response_message` é exigido** — ⏳ continua sem medição possível offline.
3. **Se `native_form.{answers,fields}` é formato de fio ou derivado nosso** — ⏳.
4. **Por que `attendance_transcripts` tem 4× mais linhas e zero formulário** —
   ✅ **resolvido**: dois normalizadores; só `observed_events` tem `native_form`
   e `raw_out`.
5. **O que Porto e Azul pedem** — ⏳ 37 respostas, zero schema, sem recuperação.
6. **Se o embrulho `DocumentWithCaption` é do protocolo ou do nosso remetente**
   — 📊 medido que as 4 capturas reais **não o têm**; segue sem explicação.

---

## 🔴 AS CORREÇÕES À SPEC — e as três primeiras mudam o trabalho

### C1 · O BLOCO B **não era o rótulo**, e o rótulo sozinho não consertaria nada

A §B.1 manda *"reconhecer o rótulo `galaxy_message`"*, e a §BLOCO B avisa que
isso é **uma aposta** até o BLOCO A produzir uma captura de entrada.

📊 **Não é aposta — e não é o rótulo.** O convite sobrevive inteiro dentro de
`contextInfo.quotedMessage` das 4 respostas `live` da Yelum, e o caminho real é:

```
quotedMessage
  .interactiveMessage
    .InteractiveMessage        ← NÍVEL EXTRA, com I maiúsculo
      .NativeFlowMessage       ← N maiúsculo
        .buttons[0].name              = "galaxy_message"
        .buttons[0].buttonParamsJSON  ← JSON todo em maiúscula
```

O parser procurava `interactiveMessage.nativeFlowMessage` e `buttonParamsJson`.
**Nunca chegava aos botões** — caía no ramo final com `options` vazio e `body`
preenchido, devolvendo `{"kind":"buttons","options":[]}`, que é 📊 exatamente o
que o acervo mostra 50 vezes de 62.

> **São três divergências, e o rótulo é a terceira** — a única que já estava
> escrita em algum lugar.

### C2 · O `format` do BLOCO D.3 **não chega ao fio**

📊 Segui o campo até o fim:

```
1. montar_nfm_reply põe  body.format = "EXTENSIONS"  no dicionário waE2E
2. send_native_flow_response ACHATA e manda ao GO só
      {number, name, paramsJSON, wrapInDocumentWithCaption, version?, body?}
   ← `format` fica para trás AQUI
3. e o patch 0005 do GO fixa em código
      Format: waE2E.InteractiveResponseMessage_Body_DEFAULT.Enum()
```

**Trocar `"EXTENSIONS"` por `"1"` não muda um byte do que sai — e o teste ficaria
verde.** É a classe de defeito que esta SPEC existe para matar, aparecendo dentro
do próprio conserto dela.

📊 E o nome estava certo o tempo todo: a captura traz `body.format = 1`, que **é**
`EXTENSIONS` no enum do protobuf. **Quem manda o valor errado é o GO.**

### C3 · O BLOCO E é mais barato de achar e **mais caro de fazer** do que a SPEC supõe

📊 O quarto formulário da Yelum (`1579547063352571`) **está no acervo**, dentro de
`interactive.raw_out` — uma **terceira** forma de armazenamento que nenhum leitor
conhece. Mas:

```
📊 a definição ESTÁ no payload      `data-source` aparece nos 4 formulários
📊 e NÃO é alcançável por JSON      viaja como repr de PYTHON dentro de string
                                    escapada; nenhum caminhante de JSON a acha
📊 `data-source` tem DUAS formas    inline   [{'id':'1','title':'Sim'}]   (HDI)
                                    ligação  '${data.dt_TiposEndereco}'   (Yelum)
📊 recuperei                        6 telas · 18 campos · nome e rótulo · 0 PII
🔴 NÃO recuperei                    os `id` das opções
```

**Um componente sem os `id` das opções não pode ser respondido** — e este é o
formulário cuja resposta é *para onde o guincho vai*. Entregar meio schema seria
pior que nenhum.

### C4 · Números da SPEC que a medição corrige

| a SPEC diz | 📊 medido |
|---|---|
| §2.6 *"4.715 opções com `id` vazio"* | **15.273** — a SPEC contou **um** acervo |
| §3.2 *"`response_message` (~6 KB)"* | **4.854 caracteres**; os ~6 KB são o `paramsJSON` inteiro (5.874) |
| Gate D *"byte a byte igual ao exemplar de ouro"* | 🔴 **inalcançável**: o fixture do repositório tem `response_message` com **46** caracteres contra **4.854** da linha real. **O exemplar de ouro do repositório é uma cópia truncada da captura** |

---

## O QUE FOI ENTREGUE, POR BLOCO

### BLOCO A — o convite deixa de virar linha em branco · `30eaada`

```
observed_events         list     6.726 opções   id preenchido: 0
observed_events         buttons  3.832          0
attendance_transcripts  list     3.318          0
attendance_transcripts  buttons  1.397          0
──────────────────────────────────────────────────────────────
                                15.273 opções, e NENHUMA com id
```

🔴 **A causa, lida no cru:** o fio manda **`buttonID`** e **`rowID`**, com **D
maiúsculo**. É a mesma família da P-56 (*"lia `selectedButtonId`, d minúsculo"*,
98,9% dos cliques apagados), curada no lado da RESPOSTA e **nunca aplicada ao
lado do CONVITE**.

Mais: **o cru da TELA passa a ser guardado** — e só a tela, com `contextInfo`
fora, porque ele cita a mensagem anterior e pode trazer dado de segurado para uma
tabela durável sem ninguém decidir isso. E **o que não se reconhece passa a ser
guardado** com `kind='desconhecido'`, em vez de virar quatro nulos.

**A.3, decidido e registrado:** os dois acervos e o corredor ao vivo importam
**o mesmo parser**. Consertar ali é a consolidação que o `CLAUDE.md` §5 pede; um
terceiro caminho reprovaria. E o limitador de cru voltou a ter **uma**
implementação.

### BLOCO B — o convite passa a ser LIDO · `74dfbbb`

`_sub` acha o sub-dicionário por grafia normalizada e atravessa um nível de
invólucro homônimo. Mais leitura tolerante do nome do botão, dos params e dos
campos do flow, e o rótulo legado na allowlist.

📊 **O CONTROLE da §B.2, sobre payload CRU REAL** — 82 convites do acervo, parser
de `8b49fdb` contra o da árvore:

```
kind ANTES     kind DEPOIS       n
buttons        buttons          50      intacto
list           list             28      intacto
buttons        flow              4      <== os quatro formulários

opções          330 → 330    nenhuma opção inventada
ids               0 → 330    100% dos identificadores recuperados
flow_id           0 →   4
flow_token        0 →   4
```

**78 de 82 classificações idênticas.** Só os quatro convites de formulário se
moveram, e do errado para o certo.

### BLOCO C — o `flow_id` é por seguradora · `34f0a93`

📊 A hipótese da §2.3 **se confirma, campo a campo**: HDI `857030507196739` e
Yelum `3206000179602236` têm os **cinco mesmos nomes**. Um mapeamento serve às
duas — e é por isso mesmo que o defeito existia: um registro só, apontado pelos
dois playbooks, faz `montar_resposta_de_flow` devolver **sempre o id da HDI**.

E a moldura leva o `title`, a quarta chave que a captura tem e o produto não
mandava. `response_message` continua fora, de propósito.

### BLOCO D — responder · `807e276` + `73d6e9c`

- **D.2:** a tela de formulário decide **antes** do passo. 📊 Medido pelo
  investigador: **zero colisões em 4.220 telas reais**; **uma tela em 4.279**
  muda de comportamento, e ela muda de resposta errada para `needs_human` com
  motivo. A guarda tem **duas** condições porque `ura_simulator` e `replay`
  chamam sem `interactive`.
- 🔴 **E o que precisava estar escrito:** sob essa guarda,
  `_responder_formulario_nativo` **nunca devolve `None`**. Não é *"formulário
  primeiro, passo depois"*; é *"para mensagem de formulário, o passo não roda"*.
- **D.3:** `version` 1 → **3**, medido. `format` documentado como inerte, com o
  guarda que fixa a **lista fechada** de chaves do fio.
- **A trava do §D:** com o freio fechado o transcript dizia *"FORMULÁRIO NATIVO
  respondido"* para um formulário que ninguém enviou. Mesmo defeito da SPEC-085,
  noutro arquivo: a flag foi consertada e o texto ao lado dela não.

### BLOCO E — a 4ª tela da Yelum · `807e276` (parcial, com a medição inteira)

O que entra é o **controle**: tela sem schema vira `needs_human` com motivo, e
`id` de opção **nunca** é inventado a partir do título. A transcrição vai para a
pendência com tudo o que foi medido.

⚠️ **E isso fecha de passagem a §3.1.2:** `formulario_nativo_desconhecido` era
**inalcançável** porque o parser nunca emitia `flow`. Com o BLOCO B ele é
alcançável, e o guarda prova percorrendo o caminho.

### BLOCO F — a prova · `73d6e9c` + `00b1a89`

- **F.2:** a rota de prova manda **de verdade** e não passa por freio nenhum. Até
  aqui, o único motivo de ela ser segura era **a docstring dizer** que o destino
  é nosso.

  > **Uma premissa de segurança que existe só na docstring não é uma trava: é uma
  > esperança.**

  Agora o código confere, por lista de **permissão**, com equivalência de grafia,
  e **falha fechado** em três caminhos.
- **F.3/F.4:** o `interactive` e o `flow_sender` atravessam o simulador — que é a
  régua que decide se um playbook pode ir a produção, e para a qual o caminho mais
  novo do produto era invisível. Com a linha de controle da §F.4.

---

## O QUE FICOU FORA, E POR QUÊ

| | |
|---|---|
| a transcrição da 4ª tela | 📊 falta o `id` das opções; ver C3. **Não bloqueia** — o controle protege |
| `format` no fio | exige patch 0007 do GO + rebuild de imagem 🧑 |
| Porto e Azul | 📊 sem schema recuperável; só um acionamento ao vivo produz um 🧑 |
| o desfecho | provamos que o WhatsApp aceita; **não** que a seguradora aceita |

---

# 🔴 O PAINEL — cinco lentes, cinco reprovações

> §7 da SPEC e §5 do protocolo: as lentes rodam **de uma vez, cegas entre si**,
> sobre o CÓDIGO. Nenhuma recebeu a narrativa de quem construiu.
>
> **As cinco reprovaram.** E o padrão que atravessa quase todos os achados é o
> mesmo: **os fixtures tinham a forma errada — deduzida em vez de medida.**

## O que cada lente achou, e o que o TESTE DO PRODUTO decidiu

| # | achado | lente | teste do produto |
|---|---|---|:--:|
| 1 | `_destino_e_nosso` **sem filtro de `company_id`** — a lista de permissão era GLOBAL | isolamento · red | SEGURANÇA |
| 2 | a mesma trava virava **oráculo de pertencimento**: 400 = "não é de ninguém" | isolamento | SEGURANÇA |
| 3 | **comparava normalizado e enviava o cru** | isolamento | SEGURANÇA |
| 4 | `_chave_de_telefone` colidia móvel×fixo e BR×internacional | isolamento · medida | SEGURANÇA |
| 5 | a guarda D.2 era por **JANELA**, não por bolha → **resposta em dobro** | segurado | SEGURADO |
| 6 | e a bolha *"você está na fila"* **matava o acionamento** | segurado | SEGURADO |
| 7 | o transcript dizia `respondido` quando o **envio falhava** | segurado | CORRETORA |
| 8 | `_sub` descia demais e **o corpo da tela sumia** → 3 de 3 âncoras morriam | acervo · medida | SEGURADO |
| 9 | o ramo `unknown` **derrubava os dois portões de descarte** | isolamento · acervo · red | SEGURANÇA |
| 10 | o corte de `contextInfo` era **exato e raso** | acervo · red | SEGURANÇA |
| 11 | a moldura ecoava um **`flow_id` nunca conferido** | red | SEGURADO |
| 12 | o **`flow_cta` da seguradora escolhia o schema** | red | SEGURADO |
| 13 | **21 telas** de azul/porto virariam `needs_human` | medida | SEGURADO |
| 14 | `RecursionError` **derrubava a rota do webhook** | red | SEGURADO |
| 15 | `Buttons` com B maiúsculo reabria a P-084-68 **por uma letra** | red | SEGURADO |
| 16 | os **fixtures** tinham a forma errada, e escondiam 8, 10 e 12 | acervo · red | (guarda) |
| 17 | o guarda de dois tenants **não conseguia falhar** | isolamento | (gate) |

**Dezessete achados, todos consertados na mesma rodada.**

## 🔴 Os três que mais ensinam

### O conserto que era ele mesmo o vazamento

A trava do F.2 nasceu para impedir que a rota de prova mandasse mensagem para
fora de casa. 📊 A lente do isolamento mediu que ela **consultava `integrations`
sem filtro de `company_id`**:

```
um usuário logado da Corretora A posta {"para": "<pareado da B>"}
a lista aceita, porque o número é "nosso"
o backend carrega a integração DE A e dispara de verdade
→ mensagem real saindo do aparelho de A para o aparelho de B
```

E o meu guarda não podia ver: 📊 a lente apagou `.eq("is_active", True)` do
fonte e **todos os assertos continuaram verdes**, porque o banco falso tinha
`def eq(self,*a,**k): return self`.

> **Um guarda que não tem como falhar não guarda nada** — e eu escrevi um, no
> mesmo diff em que citei essa regra três vezes.

### A resposta que saía duas vezes, por uma peça que eu não olhei

📊 Medido pela lente do segurado, com linha de controle contra o motor de
`8b49fdb`:

```
rajada [FORMULÁRIO, "você está na fila"] com o MESMO interactive
ANTES  8b49fdb          RESPOSTAS ENVIADAS = 1
DEPOIS (com a D.2)                         = 2
```

`message_buffer_service.py:111` **preserva o `interactive` pela janela de
debounce inteira, de propósito** — e o comentário dele explica por quê: *"a URA
da família HDI manda rajadas — o formulário e, logo atrás, um aviso de fila"*.

**O `interactive` é por JANELA; o marcador é por BOLHA.** A guarda passou a
exigir o marcador, que `evolution_inbound` anexa só à bolha que **é** o
formulário.

### O fixture inventado, e os três defeitos que ele escondeu

📊 A lente do acervo mediu, com controle:

```
fixture do teste     corpo_no_texto=True    _sub devolveu ['NativeFlowMessage','body']
forma REAL do fio    corpo_no_texto=False   _sub devolveu ['NativeFlowMessage']
controle (ANTES)     corpo_no_texto=True
```

O meu `convite()` copiava o miolo para dentro, **dando `body` aos dois níveis**.
O fio não dá. E o red team achou a contradição de frente: **os meus dois
arquivos de teste descreviam o mesmo payload de jeitos diferentes** — um com
dois níveis e maiúsculas, o outro com um nível todo minúsculo.

Com o fixture certo, três defeitos apareceram de uma vez: o corpo perdido, o
`contextInfo` escapando pelo nível de dentro, e a `prompt_anchor` morta.

> É o `CLAUDE.md` §9.2 contra quem o citou: **forma deduzida em vez de medida.**

## O que as lentes disseram que está CERTO

Vale registrar, porque um painel que só acha defeito não mede nada:

- 📊 **30 payloads torcidos, zero exceções** — `buttonParamsJson` quebrado, `null`,
  lista, `bytes`; `buttons` vazio, `None`, string, 50 botões; `interactiveMessage`
  string, lista, int. Todos devolvem, nenhum levanta.
- 📊 **Injeção de JSON pelo `title` não funciona** — `json.dumps` fecha a porta, e
  `flow_cta` tem teto de 120 na sessão.
- 📊 **`flow_token` morre no snapshot durável**, como deve: depois de um restart o
  caminho cai em `formulario_pronto_sem_flow_token` → `needs_human`.
- 📊 **A inversão D.2 é estreita**: bateria diferencial BASE×HEAD, 8 cenas, **só 1
  difere**, e a linha de controle (a tela de BOTÕES com a mesma âncora) continua
  sendo respondida por texto nas duas versões.
- 📊 **`formulario_envio_falhou` continua `DIRETO_AO_HUMANO`** nas duas versões. A
  trava §D.4 está intacta.
- 📊 **Nenhum motor paralelo**: `_raw_capped` **mudou de casa** em vez de virar
  cópia, e `_CHAVES_DE_ID_DE_OPCAO` é derivada de `_CHAVES_DE_ID`.
- 📊 **O cru não alcança log, RAG, artifact nem o checkpoint durável** — conferido
  nos quatro.

## 🔴 Onde eu discordei de uma lente, com número

A lente da medida afirmou que o formulário `3206000179602236` da Yelum tem
**quatro** campos, e que a identidade com a HDI (cinco) era falsa.

📊 Reproduzi antes de aplicar, como o §6 do protocolo manda:

```
3206000179602236   fields  = 5   ckb_SituacoesVeiculo | rb_EmGaragemOuEstacionamento
                                 | rb_InformacoesLocal | rb_NivelDaRua | rb_Ocupantes
                   answers = 4   (sem rb_NivelDaRua)
```

Ela leu `answers` — **o que a pessoa preencheu** —, eu li `fields` — **o que o
formulário tem**. E `rb_NivelDaRua` é justamente o campo de visibilidade
condicional: ele só aparece se a resposta da garagem mandar.

⚠️ **Mas a crítica ESTRUTURAL dela é certa e foi aceita:** `nf['857…'] is
nf['3206…']` é `True`, então o meu teste comparou **o mesmo objeto Python
consigo mesmo**. A conclusão está certa; **o teste não a provava**. A prova real
é a consulta ao acervo, e ela está escrita no lugar do teste tautológico.

---

# 🔴 O JUIZ DE CONFIRMAÇÃO — e dois dos consertos do painel não consertavam

> §5 ⑥ do protocolo: **um juiz novo confirma, porque conserto cria defeito.**
> Ele **NÃO CONFIRMOU**. E dois dos três blockers dele eram consertos do painel
> que pareciam fechados e não estavam.

## B1 · A resposta em dobro — só o caso medido tinha sido fechado

📊 Medido pelo juiz, com linha de controle contra três versões do motor:

```
bolha 2                                BASE 8b49fdb  PRÉ-PAINEL  HEAD(defeito)
"você está na fila…"                        1            2            1
"Estamos verificando as informações…"       2            2            2
CONTROLE — a mesma rajada SEM interactive   1            1            1
```

A guarda `a_tela_e_formulario` protege a **primeira** chamada de
`_responder_formulario_nativo`. A **segunda** roda para toda bolha que não casa
passo, recebe o mesmo `interactive` de janela, e o *fallback* do `flow_id`
reconstrói o schema.

🔴 **E a bolha que o painel escolheu para medir casa um passo `noop` e retorna
ANTES de chegar lá.** Por isso ela deu 1. Qualquer outra bolha da mesma janela
manda duas vezes.

**O conserto é `interactive=None` na segunda chamada** — que é o que ela sempre
significou: *aqui não se olha metadado de janela nenhum*. O `flow_token`
continua vindo da sessão, gravado no começo do turno.

## B2 · O corte não alcançava o segredo que ele mesmo nomeia

📊 Medido pelo juiz, no acervo de produção:

```sql
www_proxy_secret dentro de string JSON ....... 4
www_proxy_secret como chave jsonb ............ 0
```

No fio, `flow_metadata` — com `www_proxy_secret` e `flow_token_signature` —
viaja **dentro** do `buttonParamsJSON`, que é **texto**. Um corte que anda só
por dicionário passa ao largo.

⚠️ **E o meu guarda punha a chave num `header`** — uma forma que não ocorre no
fio. É o mesmo defeito de *fixture deduzido em vez de medido* que o painel
diagnosticou, **repetido dentro do conserto disso**.

O corte agora entra na string. Re-serializar ali é seguro e está escrito por
quê: **o `cru` existe para ser lido por gente, nunca para ser ecoado à
seguradora** — quem ecoa byte a byte é o `paramsJSON` do envio, que não passa
por essa função.

## B3 · A frase mentia num ramo

O `raise ValueError("envelope_do_flow ausente")` morava **dentro do mesmo
`try`** cujo `except` grava `formulario_envio_falhou`. 📊 Medido:

```
envelope ausente → [FORMULÁRIO NATIVO montado e o envio FALHOU: 4 campos
                    — pode ter chegado, não dá para saber]
                   flow_envio_erro=ValueError
```

**Nada saiu — nem uma tentativa houve.** E quem tria decide diferente nos dois
casos: com *"pode ter chegado"* se evita reenviar; com *"não saiu"* se clica em
segundos.

Agora tem motivo próprio, `formulario_sem_envelope`, com veredito de retomada
escrito.

## 🔴 E o achado que mais ensina não é de produto

**Os três guardas da frase eram estáticos e não conseguiam falhar.** O juiz
mutou o produto trocando os dois ramos de lugar — passando a dizer *"respondido"*
quando o envio **falha** — e **8 de 8 asserções continuaram verdes**.

📊 Reproduzi a mesma mutação:

```
guardas ESTÁTICOS ..........  1 passed    ← verdes com a mentira de pé
guardas COMPORTAMENTAIS ....  2 failed    ← pegam
restauração POR CÓPIA, sha256 eefaa5d89ecabb74 idêntico
verde de novo ..............  41 passed
```

Os estáticos ficaram, com a **promessa rebaixada ao que eles de fato medem**:
uma frase apagada por engano é defeito real e eles o pegam; quem prova a
**escolha** chama o motor.

> **Três vezes nesta sessão a mesma lição pegou, em formas diferentes:** fixture
> inventado, guarda que lê comentário, guarda que lê fonte. Escrever *"um guarda
> que não tem como falhar não guarda nada"* não é o mesmo que obedecê-la.

## Os dois residuais que o juiz mediu, e por que eles importam

- 📊 **O veto do `flow_id` mandaria 21 telas de azul/porto para `needs_human`.**
  Elas dizem *"Ou, se preferir, preencha o formulário abaixo"* — têm botão
  clicável **e** formulário — e Porto e Azul são justamente as duas **sem schema
  nenhum**. Trocaria 21 acionamentos que funcionam por 21 que param. **A saída
  pelo botão vem antes do veto.**
- 📊 **`_sub` só olhava as pontas da cadeia.** Com três níveis e o
  `NativeFlowMessage` no do meio, voltava a `buttons` — o sintoma exato da
  P-084-68. O fio tem dois níveis; o laço não depende disso.

## 🔴 A décima sétima família — e um guarda de outra SPEC fez o trabalho dele

`formulario_sem_envelope` quebrou **dois guardas da SPEC-085**:

```
assert 17 == 16
assert not {'formulario_sem_envelope'}
```

📊 É exatamente o que eles foram escritos para fazer, e está no texto deles:
*"família nova no código e sem veredito **quebra aqui**, que é o ponto"*. A
suíte inteira ficou vermelha até a família ser classificada.

⚠️ **O nome do arquivo continua dizendo DEZESSEIS, de propósito**: ele nomeia o
achado que o criou (📊 *uma* de dezesseis retomava). Renomear apagaria a
história; o número vive dentro, medido do fonte.

---

# 📋 PARA O FOUNDER

> **Nada nesta caixa bloqueia a execução.** Ela é entregue inteira, uma vez, no
> fim. Cada linha diz o que é, o que você faz, o que custa esquecer, e se trava.

| # | o que é | o que você faz | custa se esquecer | trava? |
|---|---|---|:--:|:--:|
| **F-1** | 🔴 **O `version` mudou de `1` para `3`, e ele CHEGA AO FIO.** 📊 As quatro capturas `live` da Yelum trazem `3`, e o `1` era hipótese declarada. ⚠️ **Mas a prova de 03/08 que deu `200` foi feita com `version=1`.** A rodada 1 daquele dia mostrou que `version` não muda o resultado (cinco formas, cinco `479`), então 💭 não deve mudar o `200` — **não medido.** | refazer a prova `POST /prova-de-formulario` com `version=3` **antes** de abrir `INSURER_DISPATCH_LIVE` | um campo novo no fio sem a prova refeita | **NÃO** |
| **F-2** | 📊 **O `format` do envio exige patch 0007 do GO e rebuild de imagem.** O patch 0005 fixa `Body_DEFAULT` (0) em código; a captura real traz `1` = `EXTENSIONS`. O Python não controla isso — o campo nem sai do achatador. | decidir se o patch 0007 entra | se a seguradora validar o campo, a resposta é descartada em silêncio | **NÃO** |
| **F-3** | 🔴 **Porto e Azul não têm schema de formulário nenhum.** 📊 37 respostas delas vieram por `history_sync`, que guardou só `sorted(m.keys())`. **Não são recuperáveis** — só um acionamento **ao vivo** produz um. | decidir se vale um acionamento de teste em cada | 37 formulários por seguradora continuam sem resposta automática | **NÃO** |
| **F-4** | 🔴 **Quatro linhas de `observed_events` JÁ guardam `www_proxy_secret` e `flow_token_signature` hoje** — numa chave `raw_out` que **não vem** do parser que esta SPEC consertou. 📊 Achado pelo juiz, fora do escopo: é vazamento durável **anterior** a esta SPEC, e continua aberto. | decidir se as quatro linhas são purgadas ou mascaradas | segredo de terceiro parado numa tabela durável | **NÃO** |
| **F-5** | 🔴 **O desfecho continua sem prova.** Provamos que o WhatsApp **aceita** a mensagem. **Não** provamos que a seguradora aceita a resposta no meio de um atendimento real. São coisas diferentes, e só um acionamento real fecha. | decidir quando fazer esse acionamento, e em qual seguradora | o produto pode estar mandando uma resposta bem formada que a seguradora descarta — e o sintoma é indistinguível de tudo o mais | **NÃO** |
| **F-6** | 📊 **`app/services/__init__.py` importa `fastembed`, e o `gate.yml` não roda `pip install`.** Qualquer caminho que faça `from app.services import X` fica irrodável em CI — inclusive o ensaio. Todo guarda desta SPEC teve de montar o pacote à mão. | nada agora — é 🤖, está na P-092-05 | um dia alguém não vai montar, e o guarda vai passar por ignorância | **NÃO** |

---

## 🔴 A LIÇÃO QUE ATRAVESSOU A SESSÃO INTEIRA

Três vezes, em formas diferentes, o mesmo defeito:

```
1. o FIXTURE inventado      `convite()` dava `body` aos dois níveis; o fio não dá
                            → escondeu a perda do corpo, o contextInfo escapando
                              e a prompt_anchor morta

2. o guarda que lê COMENTÁRIO   `fonte.index("[FORMULÁRIO NATIVO respondido")`
                                achou a frase dentro do comentário que a explica

3. o guarda que lê FONTE     as três asserções da frase ficaram verdes com os
                             dois ramos TROCADOS de lugar no produto
```

E os três foram achados por **outra pessoa** — nunca por releitura minha.

> **Escrever *"um guarda que não tem como falhar não guarda nada"* não é o mesmo
> que obedecê-la.** A defesa não é ler com atenção. A defesa é mutar o produto e
> ver o guarda ficar vermelho.
