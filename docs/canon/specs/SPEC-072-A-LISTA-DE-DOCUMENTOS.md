# SPEC-072 · A lista de documentos que o agente entrega

> **Estado:** proposta · **Aberta em:** 15/08/2026 · **Branch sugerida:** `feat/spec072-lista-de-documentos`
> **Depende de:** LEVA 5 fechada (feito) · corte de 400 removido (feito, commit `0a8282a`)

---

## 0. A correção que encolheu esta SPEC pela metade

A primeira versão desta proposta criava **duas tabelas novas** (`document_checklists`,
`document_checklist_items`) e uma **ferramenta** para o agente consultar.

O Founder recusou, e tinha razão:

> *"Devemos ter essa lista de documentos para as situações, mas não é pra virar
> uma nova estrutura só por causa disso."*

**E o motivo técnico que sustentava a tabela deixou de existir no mesmo dia.**

📊 A tabela existia porque uma lista completa **não cabia numa carta**: quatro
pontos de ingestão descartavam qualquer texto acima de **400 caracteres**, em
silêncio. Uma lista de documentos é longa *porque* é completa — era o que a
tornava útil e o que a matava.

Em 15/08/2026 esse corte foi substituído por uma constante única de **40 a 1.800
caracteres** — a mesma régua que o caminho do acervo já usava. 📊 Uma lista de 12
documentos com "onde pegar" tem ~1.100 caracteres. **Cabe com folga.**

> **Lição de método:** eu continuei propondo a tabela depois que o motivo dela
> desapareceu. A estrutura sobreviveu ao problema que a justificava. Quando um
> obstáculo é removido, as decisões tomadas por causa dele têm de ser reabertas
> — não herdadas.

**Esta SPEC não cria tabela nova, não cria ferramenta nova e não cria motor
paralelo.** Ela usa `knowledge_cards`, que já existe, com uma coluna a mais que
já é produzida e hoje é jogada fora.

---

## 1. O que o Founder pediu, na letra

> *"Quando acontecer um sinistro, o agente deve saber de todas as listas de
> documentos que precisa enviar para o cliente dependendo da situação — e de
> todas as seguradoras."*
>
> *"Alguns documentos que podem ser mais difíceis de conseguir, precisamos
> facilitar. Por exemplo, boletim de ocorrência. O agente deve enviar na lista o
> link do boletim de ocorrência online pra fazer na hora, igual a Regina sempre
> faz. E aí explicar mais ou menos o que fazer, um resumo."*

São **duas** coisas, e a segunda é menor do que eu fiz parecer:

| | o que é | tamanho real |
|---|---|---|
| **A lista** | quais documentos, por seguradora e por situação | o trabalho principal |
| **Onde pegar** | só para os **difíceis** — B.O., CRLV-e, ATPV-e, certidões | ~10 documentos, texto curto |

⚠️ **Eu tratei "onde pegar" como se fosse metade da SPEC e dei nota 3/100 a
ela.** Não é metade: são dez parágrafos curtos para dez documentos. O que
justifica atenção é que ela **não existe em fonte nenhuma** — condição geral não
ensina onde tirar documento, e 📊 só ~1% das conversas traz essa instrução. É
autoria, mas é autoria pequena.

---

## 2. Por que isto importa para o produto

O Founder definiu o desenho do atendimento:

```
assistência COM corredor .... ponta a ponta, sem humano
assistência SEM corredor .... primeira parte, depois handoff
SINISTRO .................... primeira parte, depois handoff
```

**A lista de documentos É a primeira parte do sinistro.** É literalmente o que o
agente faz antes de entregar ao humano. Se ela sai errada ou incompleta:

- o segurado vai ao órgão e volta sem o papel certo — 📊 o próprio acervo
  registra: *"sem isso o segurado vai ao órgão, volta sem o papel certo e o
  processo perde dias a cada ida"*
- o humano recebe um handoff pela metade e refaz o trabalho
- e o pior: **ninguém percebe que faltou item.** Uma lista incompleta parece
  uma lista.

---

## 3. O estado medido — o que existe hoje

> **🔴 Esta seção foi REESCRITA em 15/08/2026.** A versão anterior trazia seis
> números que não sobreviveram à medição, e um deles errava por **4×**. Todo
> número aqui vem com o comando que o produziu (CLAUDE.md §12.1) — e o que não
> for reprodutível está marcado como não citável, não corrigido por chute.
>
> **A lição do erro:** os números velhos saíram de amostras que ninguém
> perguntou se eram a população. `range(0,999)` do PostgREST não é amostra: é o
> **começo da tabela**. E `superseded` (653 cartas) não está no índice — contá-lo
> como RAG inflou três medições. **Toda contagem daqui em diante declara o
> filtro de status.**

📊 Fonte: `knowledge_cards` em `dcajcvlzcjbmyapmklil.supabase.co`, população
paginada até o fim, e `backend/scripts/acervo/`. Data: 15/08/2026.

### 3.1 O universo — e por que o total não é o RAG

```
GET /rest/v1/knowledge_cards?select=id&status=eq.<X>   Prefer: count=exact

TOTAL na tabela ......  18.621     ← NÃO é o RAG
published (o RAG) ....  17.928
superseded ...........     653     ← fora do índice
pending_review .......       0
rejected_* ...........      40
```

⚠️ `pending_review = 0` fecha **P-173** sozinha: as 343 cartas que a pendência
dizia merecerem "uma passada de olho antes" foram publicadas pelo job automático
do Destilador. Entraram no RAG sem a revisão que a pendência pedia.

### 3.2 O que já temos — só `published`

| | medido | comando |
|---|---|---|
| do **acervo** (`source_unit_id` não nulo) | **5.394** | `&status=eq.published&source_unit_id=not.is.null` |
| de **conversa** | **12.534** | `&source_unit_id=is.null` |
| tema `documentacao` | **2.786** | `&temas=cs.{"documentacao"}` |
| **sem** `insurer_key` | **10.183** (56,8%) | `&insurer_key=is.null` |
| **sem** `temas` | **4.083** (22,8%) | `&temas=is.null` |
| cartas do acervo com `faceta='documento'` | **380**, em 32 pares seg×ramo | contagem dos 32 `cartas/*/*_CARTAS.jsonl` |
| seções de documento no **bruto** | **253 seções · 307.729 caracteres** | `faceta=='documento'` nos 3 `pedacos/*.jsonl.gz`, somando `corpo` |

⚠️ **O número antigo era "63 seções · 73.749 caracteres". Errava por 4×** — e o
erro era a favor: **há quatro vezes mais matéria-prima** do que a SPEC prometia.
Nenhum de oito filtros testados reproduz 63 nem 73.749; o instrumento que os
produziu não ficou registrado. Nota: somar `texto` em vez de `corpo` dá 377.697
— a medição correta é sobre `corpo`.

⬜ **"187 cartas citam ≥3 documentos (1,07%)" e "102 sem `insurer_key`" não são
citáveis.** Medindo sobre 774 candidatas do banco com um vocabulário de 15
documentos: **108 cartas, 67 (62,0%) sem seguradora**. Mesma ordem de grandeza,
instrumento diferente — e nenhum dos dois é o teto, porque regex de documento
nomeado é piso por construção. Trate como piso, sem citar o número.

### 3.3 A cobertura — e o que "ter acervo" quer dizer

```
seguradora   published   do acervo   bruto preservado em pedacos/
allianz          2.546       1.937   SIM
yelum            1.708       1.360   SIM
porto            1.476       1.121   SIM
hdi              1.230         976   NÃO   ← tem cartas, não tem bruto
```

🔴 **São 3 seguradoras com bruto, não 4.** `backend/scripts/acervo/pedacos/`
tem `allianz`, `porto` e `yelum` — 6.797 pedaços de 23 documentos, e o
[README](../../../backend/scripts/acervo/pedacos/README.md) diz "das **três**
seguradoras conferidas na SUSEP". **O Bloco 2 não pode entregar HDI**, e o Gate
final #2 foi corrigido para 3. A HDI depende da URL nova das condições gerais
(`PENDENCIAS.md:1782`).

📊 E **16** seguradoras têm carta publicada e **zero** acervo, somando 785
cartas: alfa, axa, azul, bradesco, chubb, essor, itau, mapfre, metlife, sompo,
suhai, sura, tokio, unimed, youse, zurich. ⚠️ **SulAmérica não está na lista
porque tem zero carta publicada** — a lista antiga, de 11 nomes, a incluía por
engano e omitia seis.

⬜ **A matriz "colisão 3/2/2/0 · incêndio 0/0/0/0" não é citável.** Não foi
reproduzida: com critério de banco declarado (`insurer_key` + `ilike` + tema
`documentacao`) os números são outros, e "incêndio zero em todas" não se
sustenta. O instrumento original não ficou registrado. **A matriz volta quando
tiver comando.**

### 3.4 Os três defeitos de origem

**① O rótulo é produzido, e nenhum leitor o alcança.**

`faceta='documento'` classifica 380 cartas. O diagnóstico exato é pior do que
"o banco descarta":

```
publicar_cartas.py:332   grava a faceta DENTRO do jsonb `pii_check`
publicar_cartas.py:364   faz `pop("_faceta")` — a chave de topo sai
publicar_cartas.py:366   upsert em knowledge_cards SEM coluna `faceta`
publicar_cartas.py:385   passa a faceta ao Qdrant, que TEM índice para ela
                         (qdrant_service.py:96, KEYWORD)
```

E aí param os dois lados:

- **No Postgres** ela existe só dentro de `pii_check`, e **nenhum leitor do
  repositório consulta `pii_check->>faceta`**.
- **No Qdrant** ela tem índice e **nenhum filtro**: não há `_filtro_de_faceta`,
  não há parâmetro em `search_similar` (`qdrant_service.py:528`), não há kwarg
  em `build_global_search_kwargs` (`knowledge_scope.py:163`) e não há
  `faceta_da_pergunta()` ao lado de `seguradora_da_pergunta()`. **É P-142**, e é
  o que faz a SPEC entregar o que promete.
- **E a republicação apagava o que existia.** `insert_embeddings` faz `upsert`
  de **ponto inteiro** (`qdrant_service.py:355`), não `set_payload` — reescrever
  com menos payload substitui. 📊 Corrigido em 15/08/2026 (ver §5, Bloco 0).

⚠️ Consequência de desenho: **a coluna no Postgres, sozinha, não muda nenhuma
resposta do agente**, porque a busca em runtime nunca lê `knowledge_cards`. Ela
serve à durabilidade e à curadoria. O leitor é que serve ao agente.

**② A tabela de documentos morreu na extração — em DUAS seguradoras.**

```
yelum   · GLOSSÁRIO > TABELA DE DOCUMENTOS NECESSÁRIOS À REGULAÇÃO DE SINISTROS
          corpo: "Documentos necessários PP"                        ← 25 chars
allianz · CONDIÇÕES GERAIS DO SEGURO DE AUTOMÓVEL > ALLIANZ AUTO >
          25.9 Documentos Necessários para a Liquidação…
          corpo: "Casco (veículo segurado)\n\nDanos Materiais"      ← 41 chars
          (o mesmo corpo aparece 3× — são os CABEÇALHOS DE COLUNA da matriz)
allianz · ALLIANZ CONDOMÍNIO > 5. Documentos do Seguro
          corpo: "23"                                                ← 2 chars
```

A matriz seguradora × tipo-de-sinistro virou cabeçalho sem linhas. **O sistema
sabe ler a legenda e não tem as células.** ⚠️ A versão anterior atribuía o
defeito a Yelum + HDI; o da HDI **não é verificável neste repositório**, porque
não há bruto da HDI. O confirmado é **Yelum + Allianz AUTO** — e a Allianz AUTO
é a seguradora com mais cartas de acervo.

📊 **São 13 seções de documento truncadas** (corpo < 150 caracteres), não 5.

**③ A carta de acervo já é longa — e é por isso que o teto importava.**

📊 População inteira, `status='published'`:

```
                    n        p50    p90     max    >400    >1000
todas          17.928        212    535   1.630   3.213      150
do acervo       5.394        443    777   1.630   3.190      150
de conversa    12.534        185    262     497      23        0
faceta=documento  380        489    754   1.413     262       11
tema documentacao 2.786      225    618   1.413     654       51
```

⚠️ **59% das cartas de acervo passam de 400 caracteres.** O corte de 400, que
valeu até 15/08, matava justamente essa faixa — e é onde a lista completa mora.
A régua de 40–1.800 (`curadoria_cartas.py:85-86`) não é folga: **é o que
permite a lista existir.**

⬜ **"núcleo comum 5/16 destilado vs 12/16 bruto" e "dados bancários 0/4 → 3/3"
não são citáveis.** Com vocabulário declarado de 16 documentos a direção se
confirma (o bruto tem mais que o destilado), mas a magnitude não reproduz.
O que **está** medido e sustenta a mesma conclusão é o §3.4③ acima.

**Corolário operacional, e é a chave desta SPEC: não destile a lista. Extraia a
seção inteira.**

---

## 4. O que esta SPEC entrega

Uma **carta completa por (seguradora × situação)**, dentro de
`knowledge_cards`, achável por `faceta='documento'` + `insurer_key` + `temas`,
com a lista inteira e o "onde pegar" dos difíceis embutido.

Nada mais. Sem tabela, sem tool, sem motor.

### Exemplo do produto final — o formato de uma carta

```
(allianz / auto / colisão com terceiro · faceta=documento)

Documentos para abrir sinistro de colisão com terceiro na Allianz:
CNH do condutor no momento do acidente; documento do veículo (CRLV do ano
vigente); comprovante de residência dos últimos 3 meses; 4 fotos do veículo
(frente, traseira e as duas laterais, com a placa visível em ao menos uma);
nome e telefone do terceiro. Boletim de ocorrência NÃO é obrigatório nesta
situação — passa a ser quando houver vítima com lesão ou colisão de grande
monta. Se a CNH estiver vencida ou suspensa, não há recusa automática: a
Allianz analisa após regularização no Detran. Sem CNH e sem documento do
veículo o aviso não abre — nem o do segurado, nem o do terceiro.
Onde pegar: CRLV-e no app Carteira Digital de Trânsito > Veículos > baixar,
ou no gov.br. B.O. na delegacia virtual do estado do acidente.
```

📊 **1.087 caracteres.** Cabe no teto de 1.800. Não caberia no de 400 — e é
exatamente por isso que a lista completa não existia.

📊 E a medição de população confirma que a faixa é a certa, não folgada: a carta
de acervo tem **p50 = 443** caracteres, **3.190 das 5.394 passam de 400**, e a
maior legítima tem **1.630**. O alvo de 1.087 fica no meio da distribuição real,
não na cauda.

---

## 5. Os blocos

### BLOCO 0 · Republicar deixa de apagar o lastro — ✅ FEITO em 15/08/2026

**Por que vem antes de tudo:** enquanto não estivesse feito, qualquer
republicação desmontaria o que os Blocos 2 e 3 produzissem. Não adianta gerar a
carta certa se a próxima rodada a reescreve sem rótulo.

**O defeito:** `insert_embeddings` faz `upsert` de **ponto inteiro**
(`qdrant_service.py:355`), não `set_payload`. O `select` de quem republica é,
portanto, **a lista do que sobrevive** — e duas colunas não estavam nela.

📊 Medido sobre as 5.394 cartas de acervo publicadas, antes do conserto:

```
5.337  seriam reescritas SEM `unit_id` e SEM `faceta`
   57  seriam RECUSADAS — contadas como `falhou`, sem nada avisar
       todas da HDI, todas por `{CNPJ}` — e o `{CNPJ}` é o número de
       PROCESSO SUSEP (15414.900228/2017-63), que só parece CNPJ para
       quem não sabe que o documento é público
```

A causa das 57: `publish_card_sync:571` decide
`documento_publico=bool(card.get("source_unit_id"))`, e o `select` não pedia a
coluna — logo a resposta era sempre `False`, e a rede de PII rodava apertada
numa condição geral pública. O nome do erro no relatório seria `rejected_pii`,
que **mente sobre o que aconteceu**: não vazou dado de ninguém.

**Entregue:**
- `attendance_distiller.publish_card_sync` resolve a faceta de `card["faceta"]`
  **ou** de `card["pii_check"]["faceta"]` — um lugar conserta os três
  republicadores (CLAUDE.md §5)
- `reindexar_acervo.py` e `curadoria_cartas.publicar_lote_sync` (que **roda
  sozinho** a cada rodada) passam a pedir `source_unit_id, pii_check`
- `backend/tests/test_a_republicacao_nao_apaga_o_lastro.py` — comportamental,
  com linha de controle em cada caso e prova de mutação

**Gate — saída real:** suíte **201 verdes / 18 vermelhos**, contra baseline
medido em worktree isolado de **197 / 21**. **Zero regressões**; um vermelho
herdado consertado. Mutação na fonte (`source_unit_id` fora do select):
`EXIT=1`; restaurado: `EXIT=0`.

**Registro:** CHANGE-ADDENDA **CA-039** (BLOCKER, executada).

---

### BLOCO 1 · O LEITOR — faceta e temas passam a filtrar — ✅ FEITO em 15/08/2026

> **🔴 Este bloco trocou de lugar com a coluna do Postgres, e o motivo é o
> achado que mais mudou esta SPEC.**
>
> A versão anterior entregava `ALTER TABLE … ADD COLUMN faceta` e prometia que
> *"o agente passa a poder pedir só as cartas de documento desta seguradora"*.
> **Isso era falso, e continuaria falso depois da migration:** a busca em runtime
> **nunca lê `knowledge_cards` no Postgres**. Ela lê o Qdrant
> (`search_service.py:466` → `knowledge_scope.py:163` → `qdrant_service.py:528`).
> Todos os `.table("knowledge_cards")` de `backend/app/` são administração.
>
> A coluna sozinha não muda **nenhuma** resposta do agente. O leitor muda.

**Problema:** o índice de payload `faceta` existe (`qdrant_service.py:96`,
KEYWORD) e **não tem filtro**. É **P-142**, aberta, dono 🤖.

**Entrega — 4 pontos, espelhando `_filtro_de_namespace`:**

```
qdrant_service.py ~:470   _filtro_de_faceta(faceta)      ⚠️ DOIS BRAÇOS
qdrant_service.py  :546   parâmetro `faceta` em search_similar
knowledge_scope.py :211   kwarg em build_global_search_kwargs
knowledge_scope.py :118   faceta_da_pergunta(), ao lado de seguradora_da_pergunta()
```

🔴 **O aviso que P-142 já escreveu, e que vale igual aqui:** o filtro tem de ser
de **dois braços** — *"desta faceta **OU** sem faceta"*. Um braço só apagaria
📊 **12.534 cartas published** de conversa (que nunca terão faceta) **e 1.139
trechos de contrato** (16,8% dos 6.797 pedaços têm `faceta=None`, e
`insurance_corpus.py:1167` omite a chave de propósito nesse caso).

🔴 **E `temas` entra neste bloco, não no 6 — é P-177.** A §4 promete que a
entrega é *"achável por `faceta` + `insurer_key` + `temas`"*, e **o terceiro
termo não existe do lado que a busca enxerga**: 14.264 cartas foram rotuladas,
a coluna e o índice GIN existem no Postgres, e 📊 `grep temas search_service.py
qdrant_service.py` devolve **zero linhas**. `temas` não está em
`knowledge_extras`, não está em select de republicador nenhum, e não tem índice
de payload no Qdrant. Sem isto, **o AND da §4 não tem como rodar.**

⚠️ Mesmo cuidado dos dois braços: `temas` é nulo em 📊 **4.083 das 17.928
publicadas (22,8%)**.

**Gate — saída real, `test_o_filtro_de_faceta_tem_dois_bracos.py`:**

```
só o filtro de FACETA salva ... 12.534 cartas + 1.139 trechos de contrato
só o filtro de TEMA   salva ...  4.083 cartas + 6.797 trechos de contrato
CONTROLE: sem pedido .......... nenhum ponto some (24.725 de 24.725)

MUTAÇÃO — tirar o braço "OU ausente":
    dois braços  11.252 pontos
    um braço só   1.798 pontos
    APAGADOS      9.454      ← e o teste FALHA, como tem de falhar
```

O teste não olha a forma do filtro: ele **executa** o `Filter` que
`search_similar` monta de verdade contra um acervo de mentira com as proporções
medidas. ⚠️ Monkeypatchar `IsEmptyCondition = None` **não** serviria de mutação —
produz `None` (filtro abandonado, degradação segura), não um braço só.

**E uma decisão de projeto que o gate congela:** 📊 `faceta_da_pergunta`
reconhece **1 das 8 facetas**, e `temas_da_pergunta` **1 dos 24 temas**. O motivo
está escrito no código e é o seguinte: **`escopo` e `exclusao` são um PAR.**
Filtrar *"a apólice cobre vidro?"* por `faceta='escopo'` esconderia a cláusula de
exclusão que a anula — usar o rótulo para **estreitar** quando ele existe para
**equilibrar**, e o defeito seria invisível (a busca devolve resultado, só que
meio). `documento` entra porque é a única pergunta fechada: não existe cláusula
que anule uma lista de documentos.

As outras sete "provavelmente" servem — e "provavelmente" é o que a **P-145**
proíbe: lá, um sinal por faceta foi implementado, medido contra 19 erros
confirmados e **recusado** (3 acertos, 19 falsos alarmes). *"Um sinal que grita
mais do que acerta ensina o próximo a ignorar sinal."* Sem dados novos, elas
devolvem `None` — que é o comportamento de hoje e não esconde nada.

**Registro:** CHANGE-ADDENDA **CA-040**. Fecha **P-142** e **P-177**.

**Esforço real:** ~4h.

---

### BLOCO 2 · Recuperar as 253 seções do bruto — ✅ FEITO em 16/08/2026

> **🔴 Cinco fatos do bruto invalidaram premissas desta seção.** Medidos antes de
> escrever uma linha do extrator, e cada um mudava o desenho:
>
> | | a SPEC supunha | o bruto é |
> |---|---|---|
> | ramo | vem do `caminho` | vem do cabeçalho de `texto` — **100%** de cobertura; pelo caminho seriam 19% |
> | unidade | o pedaço | o chunker **parte listas ao meio**; a unidade é a **corrida** `(doc, caminho, índice consecutivo)`. 253 pedaços → 127 corridas |
> | censo | `faceta='documento'` | **incompleto**: +58 pedaços ao costurar vizinhos. A matriz da Allianz Auto está em `faceta=None` |
> | situação | o `caminho` | **na Yelum ele mente**: 0 concordâncias, 12 discordâncias. Diz `DESMORONAMENTO` onde o corpo diz `QUEBRA DE VIDROS` |
> | itens | dá para contar | **128 das 139 seções Yelum têm zero marcador**. A heurística de maiúscula erra **107%** na mediana |
>
> E o corolário do último: o gate de contagem vale onde há marcador (23% das
> seções). Onde não há, o invariante é outro e mais forte — **o texto limpo da
> origem é reconstruível a partir das cartas**. Inventar um contador para as
> outras 77% seria fabricar o gate.

**Problema:** 📊 **307.729 caracteres em 253 seções** de listas alfabéticas
completas (`a)` … `hh)`), organizadas por cobertura e por evento, estão em
`backend/scripts/acervo/pedacos/*.jsonl.gz` — e a destilação em prosa perdeu
item de lista no caminho.

**Escopo: 3 seguradoras — allianz, porto, yelum.** A HDI não tem bruto
preservado (§3.3); entra quando a condição geral aparecer.

**Entrega:**
- extrator que lê as seções de documentos do bruto e produz **uma carta por
  (seguradora × situação)**, preservando `unit_id` para rastreabilidade
- **não destilar em prosa** — a lista sai como lista
- preservar o `caminho` como campo **citável**. ⚠️ Ele já é *buscável* (entra no
  texto do chunk, `insurance_corpus.py:909`), mas não é payload nem coluna — e é
  ele que nomeia a situação ("CLÁUSULA 4. DOCUMENTOS NECESSÁRIOS…"). Poder citar
  a cláusula é o que separa "acho que precisa" de "a cláusula 4 exige"
- ⚠️ **13 seções estão truncadas na origem** (§3.4②): registrar quais, **não
  completar por dedução**
- 📊 **dedupar os 812 corpos repetidos** (11,9% dos 6.797 pedaços são duplicata
  literal; o campeão aparece **77×**). É o mesmo defeito de secionamento que
  produz as 13 truncadas, na outra ponta: boilerplate virando seção. 77 chunks
  quase idênticos disputando BM25 é ruído puro

**Gate — saída real, 16/08/2026:**

```
                       cartas    p50    >1.000   >1.800
GERADAS ..........       147   1.397     74%       0
base: do acervo ..              443
base: tema doc ...              225
```

📊 **p50 = 1.397 contra 443** — 3,2× a mediana da carta de acervo de hoje e 6,2×
a do tema `documentacao`. O alvo desta SPEC era ~1.100; a **mediana** passou
dele. Das 380 cartas com `faceta='documento'` que já existem, **onze** passam de
1.000 caracteres; destas 147, passam **109**.

`test_a_lista_de_documentos_nao_perde_item.py`:

```
itens: bloco de origem × cartas dele ....  0 de 32 divergem
texto limpo perdido ..................... 0 de 76 blocos (>3%)
MUTAÇÃO: regex de item com UMA letra .... 8 itens viram 3, e o teste FALHA
```

⚠️ **E o teste pegou dois defeitos reais** — é para isso que ele existe:
`blocos_de_cobertura` **descartava** trecho abaixo de 40 caracteres (um bloco
perdia 88% do texto), e `itens_de` exigia ≥2 marcadores, o que fazia a última
parte com um item só contar zero. Os dois consertados; a régua do próprio teste
também estava errada e passou a comparar **por bloco**, que é a unidade honesta
— o portão de pertinência descarta bloco de propósito.

**Escopo real: 3 seguradoras.** A HDI fica fora, declaradamente — não há bruto.

**O que ficou registrado e NÃO publicado:**
- 📊 **8 corridas, 106.984 caracteres**, que exigiriam de 5 a 18 cartas cada.
  *"Parte 17 de 18"* não é entregável: P-170 manda partir em vez de encurtar e
  está certa, mas 26.000 caracteres em 18 cartas entregam um capítulo fatiado,
  não uma lista. Ficam com os `unit_id`, para seccionamento manual.
- 📊 **74 blocos barrados** por não nomear ≥2 documentos distintos.

**Esforço real:** ~1 dia.

---

### BLOCO 3 · "Onde pegar" — os dez difíceis

**Problema:** 📊 aparece em ~1% das conversas e **em nenhuma condição geral** —
por construção: a seguradora diz o que exige, não onde se obtém.

**Entrega:** um parágrafo curto por documento difícil, embutido na carta da
situação (não em carta separada):

| documento | onde pegar |
|---|---|
| **B.O.** | delegacia virtual **do estado do fato** — link por UF |
| CRLV-e | app Carteira Digital de Trânsito → Veículos → baixar; ou gov.br |
| ATPV-e | Detran do estado, com firma reconhecida quando for indenização integral |
| certidão de óbito | cartório; registrar prazo |
| laudo do IC | Instituto de Criminalística — só em incêndio |
| contrato social | Junta Comercial / e-CNPJ |
| comprovante de residência | conta de consumo dos últimos 3 meses; se em outro nome, dizer de quem |
| dados bancários | do **titular da apólice**; se de terceiro, avisar antes |
| nota fiscal de acessório | a original; foto legível serve |
| boletim meteorológico | INMET — só em granizo/vendaval |

⚠️ **O B.O. é o caso que o Founder nomeou e o que mais aparece como objeção no
acervo** (*"precisa de BO mesmo assim?"*, *"nem dão andamento"*). A conduta
medida da Regina é a certa: **ela não argumenta, ela manda o link do estado
certo.** O agente faz igual.

**Gate:** os 10 documentos têm texto autoral, e o link do B.O. é resolvido por
UF (não um link genérico). Teste: pedir a lista para um sinistro em SC e em SP
devolve links diferentes.

**Esforço:** 1 dia.

---

### BLOCO 4 · O agente entrega no formato que funciona

**Problema medido**, sobre 468 mensagens de atendente que citam documento:

| | hoje |
|---|---|
| pedido em **rajada única** | **82,7%** — a Regina já faz certo |
| traz "onde pegar" | ~1% |
| traz "o que trava se faltar" | **13 de 468 (2,8%)** |
| numerado | 0,2% · com bullets 1,5% |

📊 E **167 de 361 fatos destilados** têm a regra de bloqueio. **O conhecimento
existe no acervo e não chega ao segurado.** É exatamente o valor que o agente
adiciona.

⚠️ **Conflito com o prompt em produção:** `backend/app/core/prompts.py:95-100`
manda *"peça num bloco de até 4 itens, numerados… máximo 4 itens… pergunta
delicada (documento pessoal) NUNCA entra em bloco"*. A medição diz que o pedido
padrão tem **5 itens** e o segurado responde, e que a CNH entra em bloco em
**100%** dos casos observados. **A regra é defensável em geral e errada para o
caso documental.**

**Entrega:**
- exceção documental nomeada em `prompts.py` — não revogação da regra
- atualizar os testes que afirmam "máximo 4 itens" (§9.3 do CLAUDE.md: teste que
  guarda verdade vencida é pior que teste nenhum)
- **eco de recebimento**: ao chegar documento, confirmar qual chegou e o que
  falta. 📊 "já mandei / não recebeu?" é o **segundo maior travamento** (20 casos)
  e é o único que se resolve por UX, não por conhecimento

**Gate:** um atendimento de teste com 5 documentos entrega os 5 numa mensagem,
com "onde pegar" nos difíceis e "o que trava" no fim. E ao receber 2 dos 5, o
agente diz quais faltam.

**Esforço:** 1 dia.

---

### BLOCO 5 · As 16 seguradoras sem acervo — 🧑 depende do Founder

📊 **São 16, não 11**, e somam **785 cartas publicadas**: alfa, axa, azul,
bradesco, chubb, essor, itau, mapfre, metlife, sompo, suhai, sura, tokio,
unimed, youse, zurich. ⚠️ A lista anterior incluía **SulAmérica, que tem zero
carta publicada**, e omitia axa, chubb, essor, itau, metlife e unimed.

**O que destrava:** o PDF das condições gerais, ou credencial do portal.

**Enquanto não vier — e a correção que muda o desenho deste bloco:** "zero
condição geral" **não** é "zero conhecimento". 📊 Tokio tem 173 cartas
publicadas, Bradesco 134, Youse 133, Mapfre 101, Zurich 75 — vindas de
atendimento real, não de contrato.

A carta dessas companhias combina **duas** fontes, **marcadas por procedência**:

```
source_unit_id NÃO nulo  → veio de CONTRATO      → é regra da companhia
source_unit_id     nulo  → veio de ATENDIMENTO   → "é o que costuma acontecer"
núcleo comum de mercado  → nem uma coisa nem outra → dizer isso na carta
```

⚠️ **Conhecimento de conversa NUNCA é apresentado como regra contratual da
companhia.** A carta diz de onde veio: *"esta é a lista padrão de mercado, e o
que vi nos atendimentos desta companhia; confirmo com ela o que é específico."*

Usar só o núcleo comum genérico seria **pior** do que o que já existe para essas
16 — e o dado já está no banco.

---

### BLOCO 6 · A coluna `faceta` no Postgres — *por último, e o motivo mudou*

> Ela era o Bloco 1 e virou o último. Não porque deixou de valer: porque o
> argumento que a justificava estava errado.

**O argumento antigo, e falso:** *"o agente passa a poder filtrar"*. Não passa —
o runtime não lê o Postgres (Bloco 1).

**O argumento verdadeiro, e é mais forte:** a faceta hoje só existe de forma
utilizável **dentro do payload do Qdrant**, que é índice **derivado e
reconstruível** (CLAUDE.md §6). Um dado de primeira classe não pode morar só num
índice. A coluna é o que dá a ele **um lugar durável** — e é o que permite
curadoria, admin e auditoria perguntarem "quais cartas respondem 'documento'?"
sem depender do índice.

**Entrega:**
- migration expand-first, espelhando `20260815_02_a_carta_ganha_tema.sql`:
  `ADD COLUMN IF NOT EXISTS faceta text` + índice parcial
  `WHERE faceta IS NOT NULL` + `COMMENT` distinguindo de `temas` e `category`
- atualizar `MANIFEST.md`, que está **3 migrations atrasado** (`20260813_01`,
  `20260815_01`, `20260815_02`)
- `publicar_cartas.py:364` deixa de fazer `pop` — o valor vai ao `upsert`
- backfill das 380 por `source_unit_id`, **em lotes de 200 com recuo**, e
  conferência **lida do banco**, não do print

⚠️ **Antes do backfill, reconciliar `faceta` × `temas`.** 📊 Das 380 cartas com
`faceta='documento'`, só **201 (53%)** têm o tema `documentacao` — e **673**
cartas de acervo têm o tema sem ter a faceta. A §4 promete "achável por `faceta`
+ `insurer_key` + `temas`": **esse AND acha 53% delas.** Rotular antes de
indexar, senão a coluna nasce mentindo.

🔴 **E a quarta edição nas mesmas três linhas — prevista aqui para não ser
esquecida.** No dia em que a coluna existir, `card["faceta"]` passa a ser a
fonte autoritativa, e **nenhum dos três selects a pede** (eles pedem `pii_check`,
que é o portador provisório do Bloco 0). Ou os selects ganham `faceta`, ou toda
carta cujo `pii_check` não carregue o valor perde a faceta no primeiro
republish — e 📊 **673 cartas de acervo já têm o tema `documentacao` sem ter a
faceta**, exatamente a população em risco. **A ordem certa é: reconciliar →
backfill → selects → só então confiar na coluna.**

⚠️ DDL não passa por PostgREST. O SQL vai escrito, com APPLY/VERIFY/ROLLBACK,
para o Founder colar no SQL Editor.

**Gate:** 📊 `select=id&faceta=eq.documento` devolve ≥ 380 (hoje devolve
`42703: column does not exist`). **Mutação:** reverter o `pop` faz o teste falhar.

**Esforço:** 3h.

---

## 6. O que esta SPEC NÃO faz

- **Não cria tabela nova.** A carta com teto de 1.800 comporta a lista.
- **Não cria ferramenta nova, nem motor paralelo.** Nenhum segundo RAG, segundo
  publicador, segundo destilador ou segundo índice.
- **Não completa por dedução** nenhuma seção truncada nem nenhuma tabela perdida.
  As 13 truncadas e as duas tabelas perdidas ficam registradas como perda.
- **Não resolve P-171** (as três respostas do link de vistoria expirado) — depende
  de confirmação da prestadora.

⚠️ **Duas linhas desta seção foram REMOVIDAS em 15/08/2026 porque mentiam:**

- ~~*"a busca existente, com `faceta` + `insurer_key` + `temas`, acha"*~~ — **a
  busca existente não filtra por faceta.** Não há `_filtro_de_faceta`, nem
  parâmetro em `search_similar`, nem kwarg em `build_global_search_kwargs`. É
  precisamente o Bloco 1.
- ~~*"não mexe no motor de RAG, no publicador nem no destilador"*~~ — **mexe nos
  dois primeiros, e tem de mexer.** O Bloco 0 já alterou
  `publish_card_sync` e dois republicadores; o Bloco 1 altera o caminho de busca.
  O que a SPEC não faz é criar um **paralelo** a eles — que é a proibição real da
  CLAUDE.md §5. Consolidar dentro do motor existente é o oposto de duplicá-lo.

---

## 7. Riscos

| risco | mitigação |
|---|---|
| 🔴 filtro de faceta de **um braço só** apaga 12.534 cartas e 1.139 trechos | dois braços ("desta faceta OU sem faceta"), com **mutação que prova** que o teste falha sem o segundo |
| a lista extraída do bruto reflete condição geral **vencida** | conferir vigência antes do backfill; a carta cita `unit_id` |
| conhecimento de conversa das 16 sem acervo virar "regra da companhia" | marcar por procedência (`source_unit_id`), e a carta diz de onde veio |
| a métrica "3+ documentos nomeados" é regex — **é piso, não teto** | tratar como piso, e **não citar o número** enquanto o instrumento não for registrado |
| carta de 1.800 caracteres cortada por um limite não achado | o teste do Bloco 2 conta itens na origem e no destino |
| 🟡 `faceta` e `temas` discordam em 47% | reconciliar **antes** do backfill do Bloco 6, senão a coluna nasce mentindo |
| 🟡 P-172 (o mascarador come `0800` e número de 4+ dígitos) atinge o Bloco 3 | medir as 10 cartas contra o `templatize` **antes** de gravar, com linha de controle |

---

## 8. Gate final da SPEC

1. ✅ republicar não apaga mais `faceta` nem `unit_id`, e a carta de documento
   público não é recusada por `{CNPJ}` — com prova de mutação **(Bloco 0, feito)**
2. 📊 o filtro de faceta é de **dois braços**, e a mutação que remove o segundo
   braço **derruba o teste**
3. 📊 uma carta completa por (seguradora × situação) para as **3 seguradoras com
   bruto preservado** — allianz, porto, yelum — com contagem de itens conferida
   contra a origem em 5 amostras. ⚠️ **A HDI fica declaradamente fora**: não há
   bruto no repositório, e nada é completado por dedução
4. 📊 os 10 documentos difíceis têm "onde pegar", e o B.O. resolve por UF
5. um atendimento de teste entrega a lista completa, em rajada única, com "o que
   trava" — e ecoa o que já recebeu
6. 📊 `faceta='documento'` responde no Postgres para ≥ 380 cartas
7. relatório com FATO / INFERÊNCIA / RECOMENDAÇÃO separados, e o que ficou fora
8. nenhum motor paralelo criado — declaração explícita
9. **todo número do relatório com o comando que o produziu, e o filtro de
   `status` declarado** (a lição da §3)

---

## 9. Ordem de execução

> **🔴 A ordem foi INVERTIDA.** A versão anterior punha a coluna do Postgres
> primeiro e o leitor no meio, como sub-item. É ao contrário: **o leitor é a
> única peça que faz a SPEC entregar o que promete**, e a coluna é a que pode
> esperar. E o Bloco 0 não existia — sem ele, o Bloco 2 produziria cartas que a
> rodada seguinte desmontaria.

```
Bloco 0  ✅ FEITO     republicar deixa de apagar o lastro
   +     ✅ FEITO     o teste vermelho herdado
      ↓
Bloco 1  (4h)         O LEITOR — filtro de faceta, dois braços
      ↓
Bloco 2  (1,5-2 dias) as 253 seções — o único que adiciona conhecimento novo
      ↓
Bloco 4  (1 dia)      exceção documental + CA-038 + eco de recebimento
      ↓
Bloco 3  (1 dia)      "onde pegar" — depois do formato, porque é o formato
                      que decide onde o parágrafo entra
      ↓
Bloco 6  (3h)         a coluna no Postgres — e a reconciliação faceta × temas

Bloco 5  🧑 Founder — em paralelo, a qualquer momento
```

**Total restante: 3,5 a 4,5 dias.**

---

## 10. Registro das correções desta SPEC

📊 15/08/2026, depois de auditoria + juiz crítico independente. Seis números não
sobreviveram à medição:

| onde | dizia | mede |
|---|---|---|
| §3.2 | 63 seções · 73.749 chars | **253 seções · 307.729 chars** |
| §3.3 | 4 seguradoras com acervo | **3 com bruto** (HDI não tem) |
| §3.4② | tabela vazia em Yelum + HDI | **Yelum + Allianz AUTO** (HDI não verificável) |
| §3.4② | 5 seções truncadas | **13** |
| §5 B5 | 11 seguradoras sem acervo | **16**, e sem SulAmérica (que tem zero carta) |
| §5 B1 | a coluna faz o agente filtrar | **não faz** — o runtime não lê o Postgres |

E três que a auditoria propôs e **também** não sobreviveram, registrados para
não voltarem:

- ⬜ *"a régua de 1.800 não está em produção"* — **falso.** `origin/main` é
  idêntico ao HEAD (`git ls-remote origin main` → `0ffcbed`). O erro nasceu de
  ler o ref `main` **local**, que estava velho porque os pushes da semana foram
  `git push origin HEAD:main` sem checkout. **`main` local ≠ `origin/main`.**
- ⬜ *"a carta de documento tem 182 caracteres de mediana"* — **viés das
  primeiras 1.000 linhas.** Na população: **225**, e a de acervo **443**. A
  conclusão era o oposto da verdade.
- ⬜ *"`publicar_cartas.py` é o único script sem `com_retry`"* — são **20 de 23**.
  Script offline, uma rodada: se cair, roda de novo. Não é para consertar.
