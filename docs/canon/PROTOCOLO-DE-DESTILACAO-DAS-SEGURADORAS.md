---
> **Estado:** vivo · roteiro de execução, para o Founder rodar no console do EasyPanel
> **Escrito em:** 18/09/2026 · **Autoridade:** SPEC-070 (o acervo) · SPEC-072 (listas) · SPEC-EXTRA-001.5 (planos)
> **Todos os números marcados 📊 foram medidos em 18/09/2026** por `SELECT` direto na base de produção.
---

# PROTOCOLO DE DESTILAÇÃO DAS SEGURADORAS

> Como transformar o PDF de condições gerais de uma seguradora em respostas que
> o agente dá em português, com a página do contrato do lado.

---

## 1. O que é a destilação, em cinco linhas

1. A seguradora registra o contrato na SUSEP. É um PDF de 100 a 200 páginas, escrito para advogado.
2. Nós baixamos esse PDF **na versão vigente**, cortamos em pedaços e guardamos o original.
3. Um leitor (um subagente Opus 5) lê os pedaços e escreve **cartas**: uma ideia por carta, em português de WhatsApp, cada uma apontando para o trecho exato que a sustenta.
4. As cartas entram no cérebro global (`autobrokers_global`) — **toda corretora da plataforma lê as mesmas cartas**. Não é conhecimento de uma corretora; é conhecimento do produto.
5. O contrato continua lá do lado. A carta responde rápido; o contrato prova.

```
PDF vigente da SUSEP
     ├─→ pedaços do contrato  → o que a apólice diz, na linguagem da apólice
     └─→ CARTAS destiladas    → a mesma regra em português, com endereço de origem
```

⚠️ **Isto não é o destilador de conversas.** Existem dois motores com nomes
parecidos e finalidades opostas. Veja §7.

---

## 2. O que já está feito e o que falta

📊 **O acervo hoje:** 194 documentos cadastrados · 42.091 pedaços · 5.561 cartas
publicadas, de 31 documentos, de 4 seguradoras. Todas as cartas nasceram entre
**09 e 16/08/2026** — a máquina rodou quatro vezes e parou.

| # | seguradora | documentos vigentes (no índice) | pedaços no índice | cartas | estado |
|---|---|---:|---:|---:|---|
| 1 | **Allianz** | 9 | 2.286 | **2.021** | ✅ destilada |
| 2 | **Yelum** | 8 | 2.825 | **1.361** | ✅ destilada |
| 3 | **Porto** | 6 | 1.686 | **1.203** | ✅ destilada |
| 4 | **HDI** | 8 | 1.642 | **976** | ✅ destilada |
| 5 | **Bradesco** | 18 | **6.845** | 0 | 🔴 **falta** |
| 6 | **Mapfre** | 23 | **4.288** | 0 | 🔴 **falta** |
| 7 | **Tokio Marine** | 14 | **3.576** | 0 | 🔴 **falta** |
| 8 | **Azul** | 3 | **1.091** | 0 | 🔴 **falta** |
| — | *normas da SUSEP* | 5 | 142 | 0 | 🔴 falta (por último) |
| | **falta ao todo** | **63** | **15.942** | **0** | |

📊 **A boa notícia que muda o tamanho do trabalho:** os PDFs das quatro que
faltam **já foram baixados, conferidos na SUSEP, cortados e indexados** — isso
aconteceu em 11/08/2026. O passo caro (§4, passos 1 a 3) **está feito**. O que
falta é a leitura: alguém precisa ler os 15.942 pedaços e escrever as cartas.

### 2.1 Onde os números do painel enganam

📊 A tabela `normative_documents` tem 77 linhas de Bradesco, 50 de Mapfre, 25 de
Tokio e 4 de Azul — 156 linhas, não 63. A diferença **não é trabalho parado**:

* **98 dessas linhas são versões já aposentadas**, guardadas de propósito (PDF no
  arquivo, linha no banco, fora da busca). É a regra D-Acervo-02: documento fora
  da busca vai para o arquivo morto, nunca para o lixo.
* 📊 **91 delas são de VIDA e foram retiradas de propósito em 11/08/2026.** Um
  comando rodou sem filtro de ramo e trouxe 89 documentos de vida, 17.710
  pedaços — mais do que o acervo conferido inteiro tinha. No mesmo dia mediu-se
  que, de 132 conversas reais do Bradesco, **3 falavam de vida**. Foram
  retiradas com o `retirar_do_acervo.py`. **Vida não é buraco; é decisão.**

### 2.2 O gatilho da destilação é humano — e a marca do banco não serve para achá-lo

📊 31 documentos têm `approved_at` preenchido e 31 documentos geraram carta.
**Não são os mesmos 31.** A sobreposição é de **10**. Há 21 documentos aprovados
sem nenhuma carta (Bradesco 7, Mapfre 5, SUSEP 5, Tokio 2, Azul 2) e 21
documentos com carta que nunca foram aprovados (HDI 8, Yelum 8, Allianz 5).

🔴 **Consequência prática:** não existe hoje nenhuma marca no banco que responda
*"este documento já foi destilado?"*. A resposta confiável é uma só —
**existe carta com `source_document_id` apontando para ele?** É essa a pergunta
do passo 7.

---

## 3. As peças, e o que cada uma faz

Todas vivem em `backend/scripts/acervo/`. ⚠️ **Dentro do contêiner o caminho
não tem `backend/`** — a imagem é construída a partir de `backend/`, que **vira**
o `/app`. Um comando com `backend/` no meio devolve `No such file or directory`,
que parece deploy faltando e não é.

| peça | o que faz | o que exige | o que grava |
|---|---|---|---|
| `coletar_seguradora.py` | pergunta à SUSEP quais produtos a seguradora vende, acha a **versão vigente** de cada um, baixa o PDF, corta, indexa e **exporta os pedaços em `.jsonl`** | Qdrant + OpenAI + MinIO (só com `--aplicar`) | banco, índice, MinIO e os `.jsonl` em `scripts/acervo/lotes/<seguradora>/` |
| `publicar_cartas.py` | pega as cartas prontas, confere uma a uma e publica no banco e no índice | banco + Qdrant + OpenAI | `knowledge_cards` + vetores no Qdrant |
| `conferir_ancoragem.py` | confere se cada carta aponta para o trecho que a sustenta | nada — roda fora do servidor | um `AUDITORIA.json` para leitura humana |
| `retirar_do_acervo.py` | **desfaz**: tira do índice, fecha a versão, marca o documento. Nada é apagado | banco + Qdrant | banco e índice |
| `extrair_listas_de_documentos.py` | caso especial: listas de documentos exigidos saem **inteiras**, sem passar por modelo nenhum | só leitura do acervo | `.jsonl` de cartas |
| `onde_pegar_documentos.py` | caso especial: "onde tiro o BO?" não está em contrato nenhum — é autoria | só leitura | `.jsonl` de cartas |
| `medir_o_rag.py` | pergunta a mesma coisa quatro vezes, variando um fator, para medir se o RAG está ajudando | OpenAI | um relatório |

### 3.1 Os argumentos que importam

```
coletar_seguradora.py
  --seguradora <chave>   obrigatório. porto allianz yelum hdi bradesco tokio
                         mapfre azul zurich alfa sura suhai
  --diagnostico          só mostra o levantamento. Não baixa, não grava.
  --aplicar              baixa, indexa e exporta. Só funciona no contêiner.
  --so-exportar          NÃO indexa. Só refaz os `.jsonl` do que já está no acervo.
  --ramo <ramo>          só um ramo (auto, residencial, condominio, empresarial,
                         equipamentos, garantia, vida)
  --sim                  não pergunta antes de gastar
  --pacote 150           quantos pedaços por arquivo `.jsonl`

publicar_cartas.py
  --seguradora <chave>   obrigatório
  --seco                 confere tudo e NÃO grava nada. Rode sempre isto antes.

retirar_do_acervo.py
  --seguradora <chave>   obrigatório
  --ramo <ramo>          só este ramo
  --aplicar              sem isto, é só ensaio
```

### 3.2 O formato exato de uma carta

Um arquivo `.jsonl` é **uma carta por linha**, sem vírgula entre linhas e sem
colchete em volta. Quatro campos, e só:

```json
{"texto": "A cobertura básica compreensiva do Porto Auto cobre colisão, choque, abalroamento e capotagem acidental, queda em precipício ou de ponte, incêndio, explosão acidental, queda de raio e roubo ou furto do veículo, total ou parcial.", "faceta": "escopo", "unit_id_origem": "norm-d24fa589-e261-48c6-bfee-983097b15873-v2#0031", "caminho": "4.1. AUTOMÓVEL — COBERTURA BÁSICA COMPREENSIVA > 4.1.2. Riscos cobertos"}
```

| campo | o que é | regra |
|---|---|---|
| `texto` | a carta em si | 📊 entre 15 e 400 caracteres é o alvo; o teto físico é o de uma mensagem. Média medida das 5.561: **492 caracteres** |
| `faceta` | em que balde a pergunta procura | **oito valores, nenhum outro:** `escopo` `exclusao` `limite` `franquia` `prazo` `documento` `definicao` `carencia` |
| `unit_id_origem` | o endereço do trecho do contrato | `norm-<id do documento>-v<versão>#<número do pedaço>` — copiado do campo `unit_id` do pedaço lido |
| `caminho` | a trilha de títulos até o trecho | serve para a pessoa conferir sem abrir o PDF |

📊 **Distribuição das 5.561 cartas publicadas, por faceta:** exclusão 1.734 ·
escopo 1.725 · limite 787 · prazo 566 · documento 450 · definição 193 ·
franquia 105 · **carência 1**.

⚠️ A carência quase não existe — e é a pergunta *"já posso usar?"*, que hoje cai
quase toda no balde `prazo` (*"quanto tempo tenho para avisar?"*). São perguntas
diferentes. A rodada de planos e coberturas (§5) é a chance de consertar isso.

### 3.3 Onde a carta é recusada, e por quê

O `publicar_cartas.py` recusa antes de gravar. Os motivos, na ordem em que ele confere:

```
sem texto                             a linha não tem o campo
curta demais                          abaixo do mínimo — não afirma nada
sem nenhum acento em 200+ caracteres  🔴 o arquivo foi gravado com codificação
                                      quebrada. "condominio" sem acento NÃO casa
                                      com "condomínio" digitado pelo corretor.
                                      Grave o arquivo em UTF-8, nunca por
                                      heredoc de terminal.
faceta desconhecida                   não é uma das oito
longa demais                          acima do limite de uma mensagem; se for
                                      lista taxativa, quebre em duas cartas
sem unit_id_origem                    a carta não sabe voltar ao contrato
unit_id_origem não aponta para a       ou o endereço foi inventado, ou a versão
versão VIGENTE                        foi substituída desde a destilação
a verificação de dado pessoal          a mesma rede do destilador de conversa
recusou o texto
```

📊 **Por que a cifra passa aqui e não passa na conversa:** este caminho só lê PDF
público da SUSEP, onde o número descreve o produto. Sem essa distinção, 36 das
716 cartas da Porto (5,0%) seriam recusadas — justamente as de `limite`, que são
as mais consultadas.

---

## 4. O passo a passo para destilar UMA seguradora

> Os comandos vão colados no **console do EasyPanel, serviço `smith-api`**.
> Troque `<seguradora>` pela chave: `bradesco`, `mapfre`, `tokio` ou `azul`.

### Passo 0 — Ver o que já existe, sem mexer em nada

```bash
cd /app && python scripts/acervo/coletar_seguradora.py --seguradora <seguradora> --diagnostico
```

**O que conferir:** a lista de produtos e, para cada um, a ficha de vigência. A
tela também mostra quais estão em dia com o que a SUSEP diz hoje.

**Se der errado:** `--diagnostico` só lê. Se ele falhar, o problema é de rede ou
de porta fechada, não de dado. A saída diz qual porta.

⏱️ 💭 1 a 3 minutos · 💰 zero.

---

### Passo 1 — Coletar o que ainda não está no acervo

🔴 **Para Bradesco, Mapfre, Tokio e Azul, este passo já foi feito em 11/08/2026.**
Rode-o mesmo assim: ele **pula sozinho** o que já está coletado na versão atual —
o progresso é um fato do banco, não um arquivo (um arquivo de progresso já
morreu num deploy e custou 109 minutos de retrabalho).

```bash
cd /app && python scripts/acervo/coletar_seguradora.py --seguradora <seguradora> --aplicar --sim
```

**O que conferir na saída:**

```
✅ v2 · 484 pedacos · vigencia 01/07/2026 (susep_rep2) · original guardado
↷  ja coletado nesta versao (v2)      ← isto é o esperado hoje
⛔ <motivo>                            ← LEIA. Documento pulado não é documento em dia.
```

E a última linha: `indexados N · exportados N · falhos N`.

**Se der errado:**

| o que aparece | o que significa | o que fazer |
|---|---|---|
| `RECUSADO: QDRANT_HOST/QDRANT_URL nao existe` | você não está no contêiner certo | rode no `smith-api` ou `smith-worker` |
| `RECUSADO: OPENAI_API_KEY nao existe` | idem | idem |
| `2_versoes_em_aberto` | a SUSEP publicou duas versões sem data de fim | **não escolha.** É defeito da fonte. Registre e siga |
| `falhos` maior que zero | parte não entrou | leia cada motivo antes de marcar o lote como pronto |

⏱️ 📊 40 segundos para os 6 documentos da Porto. 💭 2 a 5 minutos para Bradesco.
💰 📊 US$ 0,003 por documento (medido no CG144 da Porto: 484 pedaços, 137 mil
tokens de embedding). Para as quatro que faltam, se fosse do zero: 💭 **menos de
US$ 0,50 ao todo.** Como já está feito, hoje é **zero**.

---

### Passo 2 — Exportar os pedaços para leitura

É este passo que produz o material que o leitor recebe. Ele **não indexa nada** e
pode ser repetido à vontade.

```bash
cd /app && python scripts/acervo/coletar_seguradora.py --seguradora <seguradora> --so-exportar
```

**O que conferir:** para cada documento,

```
📦 2418 pedacos em 17 pacote(s) → /app/scripts/acervo/lotes/bradesco
     bradesco_residencial_v2_..._pacote_01.jsonl  150 linhas (203 KB)
```

📊 **Por que 150 por pacote:** a linha tem 1.365 bytes em média. Com 150 linhas o
arquivo fica em 190–240 KB — cabe numa leitura só do subagente e ainda sobra
janela para ele escrever as cartas. O arquivo inteiro não caberia.

**Se der errado:** `o texto nao voltou do MinIO` significa que o arquivamento
falhou. Rode de novo quando o MinIO estiver de pé. O texto sai do arquivo, não de
um download novo — de propósito: é o **mesmo** texto que foi indexado, então o
endereço da linha N do `.jsonl` é o endereço do pedaço N no índice, e não uma
aproximação.

🔴 **E agora o único passo manual do processo.** Os `.jsonl` nascem **dentro do
contêiner**, e o contêiner é recriado a cada deploy. O leitor roda **fora** dele,
na sua sessão. Copie os arquivos para fora **antes** de qualquer novo deploy, e
guarde a cópia versionada em `backend/scripts/acervo/pedacos/<seguradora>_pedacos.jsonl.gz`.

📊 Até 11/08/2026 esses arquivos existiam **só em pasta temporária**. Toda medição
publicada sobre o acervo saiu deles; uma limpeza apagaria a única cópia e nenhuma
medição poderia ser refeita nem contestada. Hoje estão versionados — mas só os da
Allianz, Porto e Yelum. **Os da HDI nunca foram guardados.**

> **Número medido sem base de prova preservada vira folclore no lote seguinte.**

⏱️ 💭 1 a 4 minutos · 💰 zero.

---

### Passo 3 — Ler e escrever as cartas (o trabalho de verdade)

Aqui não há comando. É leitura.

**Como se dispara:** 4 a 6 subagentes Opus 5 em paralelo, **um por ramo**. Cada
um recebe os pacotes de um ramo e devolve um arquivo de cartas. Nenhum deles toca
banco, índice ou script — recebe um arquivo e devolve outro.

📊 Acima de 6 em paralelo não acelera; o limite é a janela do plano.

**Onde o arquivo de saída tem de ficar:**

```
backend/scripts/acervo/cartas/<seguradora>/<ramo>_CARTAS.jsonl
```

🔴 **O prompt do leitor não existe como arquivo versionado — e isto é um defeito.**
As regras estão em prosa na SPEC-070 §10.3 e §10.3.1, e cada rodada reconstruiu o
prompt de novo, à mão. 📊 Foi assim que o alerta sobre "básica ou opcional"
produziu, sozinho, **129 cartas que afirmavam a natureza da cobertura sem que a
palavra existisse no trecho citado** — 72 tiveram de ser reescritas por auditores.

**Proposta, para fechar essa porta:** criar
`docs/canon/PROMPT-DESTILADOR-DO-ACERVO.md`, com as oito regras da §10.3, os três
alertas da §10.3.1 e a seção de planos e coberturas do §5 deste documento, e
passar a citá-lo pelo caminho em vez de reescrevê-lo. **Um prompt que se
reescreve a cada rodada perde a lição da rodada anterior.**

**As oito regras que o prompt precisa conter, em uma linha cada:**

1. Destile o que é verdade sobre o **produto**, nunca o que depende da apólice. Teste: *"duas apólices do mesmo produto podem responder diferente?"* Se sim, a carta ensina **onde verificar**.
2. Não destile o que é igual entre seguradoras (foro, prescrição, sanções). Isso é norma e entra uma vez só.
3. Toda carta cita a fonte: documento, cláusula e vigência.
4. Nenhum dado pessoal, em campo nenhum.
5. A carta é **uma ideia completa**. Se precisa de outra para fazer sentido, a busca trará metade da resposta.
6. Prefira zero a encher. Documento que não ensina nada devolve lista vazia.
7. **O teste da cauda.** Leia a última oração de cada frase e pergunte *qual trecho diz isto?* Se for "nenhum, mas faz sentido", apague a oração. O defeito que mais machuca não é a frase errada inteira — é o corpo fiel com a cauda inventada.
8. Não afirme cobertura sem o trecho. Você tem o contrato na mão; use-o.

**E os três alertas, que vão em TODO prompt:**

* **A.** 📊 O limite mora no pedaço **seguinte** ao título do serviço. No residencial da Porto, *"limite de até 3 itens"* do encanador ficou no mesmo pedaço que as exclusões do eletricista. Sempre confira o pedaço anterior e o seguinte antes de fixar um número.
* **B.** Tabela quebrada pela leitura do PDF: **não chute coluna.** Escreva a carta que ensina o eixo da resposta e manda conferir a apólice. 📊 Isso salvou quatro tabelas de virarem carta errada no primeiro lote.
* **C.** 🔴 Diga se a cobertura é **básica ou opcional — e só se o trecho disser.** A palavra (`básica`, `complementar`, `adicional`, `opcional`, `acessória`) tem de estar no corpo **ou** no caminho da unidade citada, referida àquela cobertura. Não vale de uma vizinha, não vale da seção seguinte. Sem isso: descreva o escopo **sem** o rótulo e feche com *"confira no demonstrativo de coberturas da apólice se ela foi contratada"*.

⏱️ 📊 O primeiro lote (Porto, 1.686 pedaços, 6 ramos) levou 💭 2 a 3 horas.
💭 Bradesco (6.845 pedaços, 6 ramos) leva **4 a 6 horas**; Mapfre 3 a 5; Tokio 3
a 4; Azul 1 a 2.

💰 **Custo:** no plano Max isto consome cota, não dinheiro. Se fosse pela API:
📊 15.942 pedaços × 1.365 bytes ≈ 21,8 MB de leitura ≈ 💭 6,1 milhões de tokens de
entrada, e 💭 1,4 milhão de saída. A US$ 5 por milhão de entrada e US$ 25 por
milhão de saída do Opus 5, isso é 💭 **da ordem de US$ 60 a 100 para as quatro
seguradoras inteiras** — incluindo releituras e a auditoria de ancoragem.

---

### Passo 4 — Conferir a ancoragem (obrigatório, não pule)

Roda **na sua máquina**, apontando para a pasta dos pacotes. Não toca em banco,
índice nem rede.

```bash
python backend/scripts/acervo/conferir_ancoragem.py --pasta <pasta dos pacotes> --auditoria
```

**O que ele confere:** se cada carta aponta para o trecho que realmente a
sustenta. Um endereço errado é **pior que endereço nenhum** — a carta continua
parecendo certa, o agente cita com confiança, e quem for conferir não acha nada
no lugar indicado.

**O que ele NÃO faz:** ele não reprova por "ancoragem fraca", de propósito. Uma
carta boa é o contrato reescrito, e a semelhança de palavras cai justamente
porque o trabalho foi bem feito. Ele reprova por **órfã** — endereço que não
existe.

📊 **Por que este passo existe:** no primeiro lote, um leitor rodou essa medição
por conta própria e achou **20 das suas 203 cartas** citando o pedaço vizinho. Na
rodada completa: 57 de 1.121 sinalizadas, 17 com um vizinho ancorando melhor.
**E o alerta no prompt não bastou** — os seis leitores receberam o aviso e o
defeito apareceu mesmo assim. O que acha é medir, não avisar.

O `--auditoria` grava um `AUDITORIA.json`. Mande subagentes julgarem caso a caso
em `ok` · `mover` (com o endereço certo) · `sem_lastro`. A decisão é de leitura,
não do script.

⏱️ 💭 10 a 20 minutos de script + 💭 30 a 60 minutos de julgamento.

---

### Passo 5 — Ensaio seco da publicação

```bash
cd /app && python scripts/acervo/publicar_cartas.py --seguradora <seguradora> --seco
```

**O que conferir:**

```
versões vigentes no banco: 18
cartas lidas: 1850
aprovadas: 1790   repetidas descartadas: 12
recusadas por motivo:
    31  longa demais
    17  unit_id_origem não aponta para versão VIGENTE
aproveitamento: 96.8%
ENSAIO SECO — nada foi gravado.
```

📊 **Régua de aproveitamento:** a Allianz fechou em 2.021 de 2.046 lidas (98,8%);
a Porto em 1.203. Se o aproveitamento cair abaixo de 💭 90%, **não publique** —
leia os motivos. Um monte de `longa demais` costuma ser lista taxativa que
precisa virar duas cartas; um monte de `unit_id_origem não aponta` significa que
alguém inventou endereço.

**Se der errado:** `nenhuma versão VIGENTE de <seguradora> no banco` quer dizer
que o passo 1 não rodou para ela.

⏱️ 💭 1 a 2 minutos · 💰 zero.

---

### Passo 6 — Ler vinte cartas com os olhos

Não é contagem. É leitura. Abra vinte, ao acaso, e para cada uma pergunte:

```
1. isto é verdade do PRODUTO, ou depende da apólice?
2. a última oração da frase está escrita em algum trecho, ou foi deduzida?
3. se ela diz "básica" ou "opcional", a palavra está no trecho citado?
4. se ela dá um número, o número está no MESMO pedaço que o serviço?
```

**Uma reprovação aqui volta ao passo 3.** É mais barato reescrever do que
despublicar.

---

### Passo 7 — Publicar

```bash
cd /app && python scripts/acervo/publicar_cartas.py --seguradora <seguradora>
```

**O que conferir:** a contagem final de `banco` e `índice`. Os dois números têm
de ser iguais. Uma carta que entrou no banco e não no índice fica marcada
`qdrant_pendente` — o script faz isso de propósito, para que o banco não minta
dizendo `published` sobre algo que a busca não enxerga.

**E a conferência que fecha o lote**, que não é o número da tela e sim o banco:

```sql
select count(*) from knowledge_cards
where insurer_key = '<seguradora>' and pii_check->>'origem' = 'acervo';
```

**Se der errado:** `índice recusou` em várias linhas costuma ser Qdrant fora do
ar. Rode de novo — o script é seguro para repetir (ele reconhece a carta pelo
texto e atualiza em vez de duplicar).

⏱️ 💭 5 a 15 minutos · 💰 📊 o embedding das cartas custa US$ 0,02 por milhão de
tokens: para 💭 10.500 cartas, **menos de US$ 0,10**.

---

### Passo 8 — Deixar escrito onde estamos

Atualize a tabela do §7 da SPEC-070 e o `PLACAR-DO-ACERVO.md`: quantos
documentos, quantos pedaços, quantas cartas, e o que ficou de fora e por quê.

🔴 **Sem isso, o próximo chat não sabe onde estamos.** 📊 Hoje a tabela da SPEC-070
diz que a HDI tem "ZERO documentos" — e a HDI tem 8 documentos vigentes e 976
cartas publicadas desde 14/08. A tabela está quatro lotes atrasada.

---

### 4.1 O relógio e a conta, em ordem de grandeza

| | Bradesco | Mapfre | Tokio | Azul | SUSEP |
|---|---:|---:|---:|---:|---:|
| documentos vigentes | 18 | 23 | 14 | 3 | 5 |
| pedaços a ler | 6.845 | 4.288 | 3.576 | 1.091 | 142 |
| pacotes de 150 | 46 | 29 | 24 | 8 | 1 |
| ramos (= subagentes) | 6 | 6 | 6 | 1 | 3 |
| 💭 cartas esperadas | ~4.500 | ~2.800 | ~2.400 | ~700 | ~90 |
| 💭 tempo de ponta a ponta | 5–7 h | 4–6 h | 3–5 h | 1–2 h | <1 h |

💭 A previsão de cartas usa a taxa medida das quatro prontas: 📊 8.439 pedaços
produziram 5.561 cartas — **0,66 carta por pedaço**.

**Total: 💭 13 a 20 horas de operação, 💭 US$ 60 a 100 se fosse por API, e menos
de US$ 1 de infraestrutura.** O custo real é atenção humana, não dinheiro.

---

## 5. 🔴 A destilação focada em PLANOS E COBERTURAS

> A próxima rodada tem um alvo declarado: fazer o agente responder bem
> *"tem carro reserva?"*, *"qual o limite do guincho?"*, *"cobre granizo?"*.

### 5.1 Por que a rodada anterior responde mal a essas três perguntas

📊 Das 5.561 cartas publicadas, **787 são de `limite`** — 14%. E 1.734 são de
exclusão. O acervo hoje é muito bom em dizer **o que não é coberto** e fraco em
dizer **quanto** e **em qual plano**.

E há uma razão de desenho por trás disso: a **regra 1** do prompt manda não
afirmar o que varia por apólice, e limite de assistência varia por plano. O
resultado foi uma coleção de cartas honestas e inúteis para a pergunta do
segurado:

```
✅ correta e útil    "Na cobertura de vidros da Porto Auto, risco, mancha e
                     arranhão não são cobertos — só quebra ou trinca."
⚠️ correta e vazia   "O limite de carro reserva da Porto depende da cláusula 26
                     contratada, do porte do veículo e da situação do sinistro."
```

A segunda não está errada. Ela simplesmente **não responde**. E o segurado, no
WhatsApp, às 23h, com o carro na guincho, perguntou *"quantos dias de carro
reserva eu tenho?"*.

### 5.2 A correção: a carta passa a carregar o PLANO

A regra 1 continua valendo — **o que muda é que o plano deixa de ser uma variável
escondida e vira parte da afirmação.** Onde o contrato diz o limite **por plano**,
a carta diz o plano.

```
❌ proibido      "O limite de guincho da HDI é 300 km."
                 (mente por omissão: depende do plano)

⚠️ o que temos   "O limite de guincho da HDI depende do plano contratado."
                 (verdadeiro, inútil)

✅ o alvo        "No plano Essencial do HDI Auto Básico, o guincho cobre até
                 300 km por evento, ou até R$ 120 por acionamento e R$ 360 na
                 vigência, em sinistro e em pane. Confira na apólice qual plano
                 foi contratado."
```

**A diferença é uma frase: nomear o plano e fechar mandando conferir qual plano
está na apólice.** A carta deixa de escolher pelo cliente e passa a dar a
resposta completa de cada caminho.

### 5.3 As perguntas que a rodada tem de responder

Cada uma destas é uma pergunta real de segurado. A rodada está pronta quando o
agente responde as doze com o plano, o número e a página:

```
ASSISTÊNCIA        tem carro reserva? por quantos dias?
                   qual o limite do guincho, em km e em reais?
                   guincho por pane conta igual a guincho por batida?
                   tem chaveiro? faz chave codificada?
                   pane seca leva combustível ou reboca?
                   tem táxi? hotel? por quantas diárias?
                   tem eletricista e encanador em casa? qual o teto por evento?

COBERTURA          cobre granizo?
                   cobre alagamento e enchente?
                   cobre vidro? só quebra, ou arranhão também?
                   quantos acionamentos de vidro eu tenho na vigência?
                   tem carência? de quantos dias?
```

### 5.4 Os campos que a carta precisa trazer

Não são campos novos no arquivo — o `.jsonl` continua com os mesmos quatro. São
**os elementos que precisam estar no texto da carta**, e cada um responde a uma
pergunta que o corretor faria em seguida:

| elemento | por que sem ele a carta trava | exemplo |
|---|---|---|
| **seguradora** | a resposta da HDI não vale para a Tokio | *HDI* |
| **ramo** | guincho de auto e encanador de casa não se misturam | *auto* |
| **produto** | a mesma seguradora vende vários | *HDI Auto Básico* |
| **plano / nível** | 🔴 **é o que falta hoje** | *Essencial* |
| **serviço** | o nome pelo qual o segurado pergunta | *guincho* |
| **limite com unidade** | "300" não é resposta; "300 km" é | *300 km por evento* |
| **carência** | *"já posso usar?"* é outra pergunta | *sem carência* |
| **condição** | o que precisa acontecer para valer | *em sinistro e em pane* |
| **documento e página** | é o que separa "acho" de "a página 93 diz" | *CG HDI Produtos Auto, p. 93* |

⚠️ **A página é o item novo.** A carta de hoje guarda o endereço interno
(`unit_id_origem`), que é preciso mas ilegível para uma pessoa. O número da
página é o que permite ao corretor abrir o PDF e conferir em cinco segundos.

### 5.5 As duas camadas, e por que as duas precisam existir

O AutoBrokers já tem uma segunda peça para esse mesmo problema: a base
estruturada da **SPEC-EXTRA-001.5**, em `insurer_assistance_plans` e
`insurer_assistance_services`.

```
CAMADA 1 — a CARTA                    CAMADA 2 — a BASE ESTRUTURADA
knowledge_cards                       insurer_assistance_plans + _services

responde em prosa                     responde com veredito
é barata: um leitor e um script       é cara: extração, verificação e
                                      aprovação humana linha a linha
cobre QUALQUER pergunta               cobre 12 serviços, um por vez
não sabe dizer "não"                  sabe dizer SIM, NÃO e COM CONDIÇÃO
não tem página legível                tem página, limite com unidade e carência
📊 5.561 linhas, publicadas           📊 81 linhas, NENHUMA publicada
```

**Elas não competem. Uma alimenta a outra.**

```
o segurado pergunta "tem carro reserva?"
   │
   ├─ a BASE tem linha publicada para (seguradora, ramo, plano, serviço)?
   │     SIM → responde o veredito, com o limite e a página.  ← o melhor caso
   │
   └─ não tem → a CARTA responde em prosa o que o contrato diz,
                 e manda conferir o plano na apólice.          ← nunca fica mudo
```

🔴 **E a regra que protege o segurado:** enquanto ninguém aprovar a linha da base,
o agente responde *"ainda não sei, vou confirmar"* — **nunca inventa um "não"**.
Um "não" errado manda o segurado dormir na estrada.

**Como uma alimenta a outra, na prática:** os nove elementos do §5.4 são
exatamente as colunas da base. Uma carta escrita com eles é uma linha da base
pronta para ser conferida — e é assim que a rodada de destilação passa a
**encher a fila de curadoria** em vez de correr ao lado dela.

📊 Hoje a fila tem 81 linhas de 17 pares seguradora × ramo, e **26 pares que têm
PDF no acervo não produziram nenhuma linha** — `empresarial`, `equipamentos`,
`garantia` e `vida` estão em zero em todas as seguradoras que têm o documento. O
inventário completo está em
[`reports/SPEC-EXTRA-001.5-INVENTARIO-DA-FILA.md`](reports/SPEC-EXTRA-001.5-INVENTARIO-DA-FILA.md).

### 5.6 O que acrescentar ao prompt do leitor nesta rodada

Além das oito regras e dos três alertas do §4 passo 3:

```
9.  Quando o contrato der o limite POR PLANO, escreva uma carta por plano, com
    o nome do plano na primeira frase. Nunca junte planos numa carta só.

10. Todo número vem com unidade e com janela: "300 km por evento", "R$ 360 na
    vigência", "2 diárias". Número solto não é resposta.

11. Feche toda carta de limite com "confira na apólice qual plano foi
    contratado". É o que impede que ela decida pelo cliente.

12. Se a tabela de planos estiver quebrada na leitura do PDF, NÃO chute a
    coluna. Escreva a carta do eixo ("o limite do guincho varia por plano e
    está na cláusula X") e registre a tabela como pendente de leitura manual.

13. Registre a PÁGINA do PDF ao lado do caminho, quando ela existir. É o que
    permite conferir sem abrir o índice.
```

---

## 6. A ordem recomendada

📊 A ordem é por tamanho do que falta, que é também a ordem da carteira.

| ordem | quem | por quê |
|---|---|---|
| **1º** | **Bradesco** | 📊 6.845 pedaços, 18 documentos — a maior massa parada, e a única com auto, residencial, condomínio, empresarial, equipamentos e garantia ao mesmo tempo |
| **2º** | **Mapfre** | 📊 4.288 pedaços, 23 documentos — o maior número de documentos vigentes do acervo inteiro |
| **3º** | **Tokio Marine** | 📊 3.576 pedaços, 14 documentos |
| **4º** | **Azul** | 📊 1.091 pedaços, 3 documentos, um ramo só. É a rodada curta — boa para calibrar o prompt novo antes de gastar o Bradesco |
| **5º** | **normas da SUSEP** | 📊 142 pedaços. São regra de regulador, iguais para todas as seguradoras. Entram **uma vez, sem seguradora** — a regra 2 do prompt |

💭 **Sugestão contrária, e a razão dela:** se o prompt de planos e coberturas
(§5) for novo e ainda não tiver sido testado, **comece pela Azul**. Ela custa 1 a
2 horas, tem um ramo só, e um prompt errado descoberto ali custa uma tarde — o
mesmo erro descoberto no Bradesco custa dois dias e 4.500 cartas para revisar.

**Depois das cinco:** as seguradoras que não têm nenhum documento no acervo. A
fila está medida e ordenada pela carteira real em
`docs/canon/providers/susep/fila-onda-3.json` — 📊 19 itens, sendo 12 siglas do
sistema de gestão que ainda precisam ser conciliadas com uma seguradora
canônica, e 7 seguradoras já conhecidas sem nenhum PDF (Alfa, Sompo, Suhai,
SulAmérica, Sura, Unimed, Zurich).

---

## 7. O que NÃO fazer

### 7.1 Não confundir os dois destiladores

| | **este documento** | **o outro** |
|---|---|---|
| **lê** | PDF de condições gerais da SUSEP | conversas reais de WhatsApp |
| **onde mora** | `backend/scripts/acervo/` | `backend/scripts/destilacao_max/` e `app/services/attendance_distiller.py` |
| **quem dispara** | você, pelo console | nunca; 📊 `DESTILADOR_TETO_POR_RODADA=0` significa "não destile nada" |
| **runbook** | este | [`RUNBOOK-A-NOITE-DA-DESTILACAO.md`](RUNBOOK-A-NOITE-DA-DESTILACAO.md) |

📊 O `RUNBOOK-A-NOITE-DA-DESTILACAO.md` cobre a destilação de **conversas de
atendimento** — decidir quais viram conhecimento e quais são papo pessoal que não
pode entrar no RAG. **Não é este processo**, e o material dele tem prazo (o
purge apaga o cru 90 dias depois da captura).

### 7.2 Não rodar a coleta sem `--ramo` quando o alvo é um ramo

📊 11/08/2026: o comando rodou sem filtro em quatro seguradoras e trouxe **89
documentos de vida, 17.710 pedaços** — mais do que o acervo conferido inteiro
tinha. No mesmo dia: das 132 cartas de conversa reais do Bradesco, **3 falavam
de vida**. Foram 91 versões para desfazer.

### 7.3 Não publicar sem o ensaio seco, e não publicar sem ler vinte cartas

O ensaio seco custa dois minutos. Uma carta errada publicada entra no cérebro de
**todas** as corretoras e é citada com a autoridade de um documento oficial.

### 7.4 Não gravar o arquivo de cartas por colagem no terminal

📊 Lote 2, Allianz: quatro leitores gravaram o arquivo por colagem de terminal. O
terminal usa outra codificação e o texto chegou como *"No Allianz Condominio a
cobertura Basica de Incendio e obrigatoria"*. Ninguém percebe lendo rápido — mas
a busca percebe: `condomínio` digitado pelo corretor **não casa** com `condominio`
gravado na carta, e a resposta certa some sem que nada acuse. **Grave sempre em
UTF-8, por escrita de arquivo.**

### 7.5 Não confiar no `approved_at` como marca de "já destilado"

📊 Ver §2.2: 31 aprovados, 31 com carta, **10 em comum**. A marca não mede o que
parece medir.

### 7.6 Não apagar versão antiga

Documento fora da busca vai para o arquivo morto, não para o lixo. É a D-Acervo-02,
e é o que permite voltar atrás. O `retirar_do_acervo.py` tira do índice, fecha a
versão e marca o documento — **o PDF continua no arquivo e a linha continua no
banco**. Na ordem certa: Qdrant primeiro, porque o contrário deixaria o banco
dizendo "retirado" com os pedaços ainda respondendo — o pior estado possível,
porque é invisível.

### 7.7 Não chutar coluna de tabela quebrada

📊 No primeiro lote, isso salvou quatro tabelas de virarem carta errada: diárias
de carro reserva, matriz da assistência 24h, depreciação e reajuste por idade. Um
número que não se pode afirmar é pior que nenhum número — ele **parece** uma
resposta.

### 7.8 Não deixar os `.jsonl` só dentro do contêiner

📊 Um arquivo de progresso morreu num deploy e custou 109 minutos. O contêiner é
apagado por desenho. Copie para fora e versione (§4 passo 2).

---

## 8. Para começar hoje, em três comandos

```bash
# 1. ver o que existe, sem mexer em nada
cd /app && python scripts/acervo/coletar_seguradora.py --seguradora azul --diagnostico

# 2. exportar os pedaços para leitura (não indexa nada)
cd /app && python scripts/acervo/coletar_seguradora.py --seguradora azul --so-exportar

# 3. e, quando as cartas estiverem escritas, o ensaio seco
cd /app && python scripts/acervo/publicar_cartas.py --seguradora azul --seco
```

Nenhum dos três grava carta. O primeiro e o segundo são seguros para repetir
quantas vezes quiser.
