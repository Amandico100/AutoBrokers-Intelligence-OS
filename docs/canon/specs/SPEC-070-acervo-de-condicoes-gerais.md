---
> **Status:** canônica · executável lote a lote
> **Versão:** 1.0 · **Criada em:** 08/08/2026
> **Substitui:** SPEC-066 v1 e v2 (o método mudou; o objetivo é o mesmo)
> **Autoridade:** CLAUDE.md · D-Acervo-01 · D-Acervo-02
> **Branch:** `feat/spec070-acervo-condicoes-gerais`
---

# SPEC-070 — O acervo de condições gerais

> **O objetivo, em uma frase:** que o AutoBrokers responda qualquer pergunta
> sobre qualquer cobertura de qualquer seguradora, com o texto **oficial e
> vigente**, e saiba dizer quando não sabe.

---

## COMO USAR ESTA SPEC

O Founder abre um chat e escreve **uma frase**:

```
Execute o LOTE N da SPEC-070.
```

O chat lê esta SPEC inteira, executa o lote, e **atualiza o placar da §7**.
Nenhum lote depende do seguinte. Um lote leva 💭 2-3 horas e fecha sozinho.

**Custo: zero.** Nada aqui usa API paga além do embedding (💭 ~US$ 0,002 por
documento). A destilação é feita por subagentes Opus 5 do Plano Max.

---

## 1. O ESTADO — medido em 08/08/2026

```
ÍNDICE (Qdrant, autobrokers_global)         23.478 pontos
   cards ..... 12.063  cartas destiladas de conversas reais
   normative . 11.409  trechos de condições gerais
   canon ..... 6

ACERVO DE DOCUMENTOS                        29 ingeridos, 6 parados
   seguradoras com algum documento .......  6 de 15+ que importam
   📊 documentos na versão VIGENTE .......  1 de 13 conferidos
```

**📊 O número que justifica esta SPEC: 12 de 13 documentos indexados são
versões revogadas.** O condomínio da Porto é de dezembro/2012 e o vigente é de
dezembro/2025. O auto da Porto está 4 revisões atrás.

📊 E 375 de 379 respostas reais do agente saíram com **zero** trechos do RAG.

---

## 2. AS DECISÕES JÁ TOMADAS — não reabrir

| # | decisão | onde |
|---|---|---|
| 1 | **Conhecimento destilado não tem dono.** É global, a serviço de todas as corretoras. | D-Acervo-01 |
| 2 | **Documento revogado sai da busca e vai para o arquivo.** Fica endereçável por (produto, data). | D-Acervo-02 |
| 3 | **A fonte é o registro oficial da SUSEP**, não o site da seguradora. | §3 |
| 4 | **Trecho cru e carta destilada coexistem.** Contrato manda no *que é*; carta manda no *como se faz*. | §6 |
| 5 | **Atualização = opção A**: automático até o RAG, o Founder dispara as cartas. | §9 |
| 6 | **Fato sobre pessoa nunca vira carta.** A decisão 1 não abre exceção. | D-Acervo-01 |

---

## 3. DE ONDE VEM O CONTEÚDO

### 3.1 O catálogo — para descobrir o que existe

```
GET https://dados.susep.gov.br/olinda/servico/produtos/versao/v1/odata/DadosProdutos?$format=text/csv
```
📊 200 · 4,5 MB · 2 segundos · sem chave. Devolve **31.871 produtos** com
`tipoproduto, entnome, cnpj, numeroprocesso, ramo, subramo`.

⚠️ `$top`, `$filter` e `$skip` devolvem **HTTP 500**. Só o dump inteiro funciona.
⚠️ Validar a **contagem**, não o status: 200 com 12 linhas é falha silenciosa.
Piso: 30.000 registros.

### 3.2 O registro do produto — para saber qual versão vale

```
POST https://www2.susep.gov.br/safe/menumercado/REP2/Produto.aspx/Consultar
     multipart/form-data · campo único: numeroProcesso
```
📊 200 · ~1,5 s · sem autenticação. Devolve sociedade, ramo oficial, **Situação
do Produto**, e a tabela de **Versões** com arquivo, Data de Início e Data de
Fim de Comercialização.

> **A regra da vigência, sem inferência:**
> **VIGENTE = produto "Passível de comercialização" + versão com Data de Fim VAZIA.**

Download: `GET .../REP2/Produto.aspx/DownloadConsultaPublica/{id}` → PDF.

### 3.2.1 🔴 A REGRA QUE NÃO SE NEGOCIA — só entra o VIGENTE

> **Nenhum documento revogado entra no acervo. Nunca. Por nenhum motivo.**

📊 É a razão de esta SPEC existir: hoje **12 de 13 documentos indexados são
versões revogadas**, e o agente responde a partir delas com a autoridade de um
documento oficial.

**O erro é invisível.** Um contrato revogado não parece revogado — tem o
logotipo certo, a linguagem certa e o número de processo certo. O segurado age
sobre a resposta e ninguém percebe.

#### O que o executor TEM de fazer, em toda consulta

```
1. A situação do produto é "Passível de comercialização"?
   NÃO → produto morto. NÃO baixe. Registre e siga.

2. Na tabela de Versões, qual linha tem Data de Fim de Comercialização VAZIA?
   ESSA é a vigente. É a única que se baixa.

3. DUAS linhas com fim vazio → NÃO ESCOLHA. Pare e registre `indeterminado`.
   Duas vigentes é defeito da fonte, não escolha sua.

4. NENHUMA com fim vazio → o produto não tem versão em comercialização.
   NÃO baixe.

5. A tabela não veio → `indeterminado`. NUNCA "sem alteração".
```

#### O que é PROIBIDO

| ⛔ | por quê |
|---|---|
| Baixar do site da seguradora "porque é mais fácil" | 📊 O site publica o que quer. A Porto mantém a CG140 revogada no ar desde janeiro; a vigente é a CG144 |
| Escolher a versão **mais recente** da lista | Recente ≠ vigente. 📊 A vigente do Bradesco Vida é de **2014** e está correta |
| Escolher pelo nome do arquivo ou pela data no título | 📊 O CG140 tem "010126" no nome e foi substituído em julho |
| Assumir "não achei versão nova" = "está atualizado" | 📊 8 de 28 consultas devolveram 200 com página vazia |
| Reaproveitar documento do acervo sem reconferir | 📊 Foi assim que os 12 revogados chegaram lá |

#### A conferência obrigatória, antes de indexar

O executor escreve no relatório do lote, para **cada** documento:

```
produto ........... <nome> (processo NNNNN.NNNNNN/AAAA-DD)
situação .......... Passível de comercialização
versão baixada .... <arquivo>
início ............ DD/MM/AAAA
fim ............... (vazio)   ← se não estiver vazio, PARE
total de versões .. N
o que tínhamos .... <versão antiga ou "nada">
```

**Se qualquer linha não puder ser preenchida com o que veio do registro oficial,
o documento não entra.** Um lote incompleto e honesto vale mais que um acervo
que mente com confiança.

#### E a carta herda a data

Toda carta destilada carrega a **vigência do documento de origem** (§10.4).
Carta sem vigência não é publicada — no dia em que o contrato mudar, ela seria
indistinguível das que continuam valendo.

### 3.3 As três armadilhas medidas

| armadilha | 📊 evidência | o que fazer |
|---|---|---|
| **200 com página vazia** | 8 de 28 consultas | Nunca ler só o status. Se a tabela de versões não vier, é `indeterminado`, **nunca** "não mudou" |
| **Número de processo malformado** | 3 de 31 no banco. `15414.100.233/2004-59` tem um ponto a mais | Normalizar para 17 dígitos antes de consultar |
| **Circular do regulador não está no REP2** | 5 de 5 deram vazio | Circular/Resolução vem por URL direta (`bnmapi.exe?router=upload/NNNNN`) |

### 3.4 O site da seguradora vira só conferência

📊 Testado: HDI **500** · Allianz **403** (bloqueia robô) · Tokio **200 com 1 KB**
(página de erro fingindo sucesso). O site é marketing; o REP2 é registro legal.

---

## 4. COMO O DOCUMENTO É PARTIDO — a parte mais delicada

📊 Medido sobre 5 condições gerais reais de 5 seguradoras. **Eram quatro
defeitos, não um.**

### 4.1 O extrator: PyMuPDF, nunca PyPDF2

📊 No mesmo PDF (Porto CG140), no mesmo dia:

| | PyPDF2 (o que usamos) | **PyMuPDF (fitz)** |
|---|---|---|
| linhas | 519 | **11.064** |
| `CLÁUSULA N` em início de linha | **3** | **74** |
| `N.N` em início de linha | **15** | **509** |
| alíneas `a)` | 22 | **946** |
| tempo | 15,6 s | **1,3 s** |

**PyPDF2 colapsa a página inteira numa linha.** É por isso que uma auditoria
anterior concluiu, errado, que "cortar por seção é impossível".

**Regra:** `PyMuPDF` (`page.get_text("text")`) para o texto corrido +
`pdfplumber.extract_tables()` **só nas regiões de tabela**. 📊 O CG140 tem 104
tabelas em 69 das 167 páginas.

### 4.2 A limpeza — nesta ordem exata

1. **Juntar número órfão:** linha com só `4.2.` + a seguinte curta e maiúscula
   viram `4.2. CONSERTO LINHA MARROM`. 📊 O Bradesco quebra assim.
2. **Remover sumário:** linha que casa `[.\-–—_·]{4,}\s*\d{1,4}$`.
3. **Remover mobília de página:** linha repetida ≥5×.
   ⚠️ **Excluir da mobília linha puramente numérica.** 📊 Sem isso, os valores
   `630` e `882` da tabela de carro reserva somem do documento.
4. **Remover número de página:** só quando anda de 1 em 1 ao longo do arquivo.

### 4.3 O corte

**Detectar título e montar a hierarquia:**

| nível | padrão |
|---|---|
| 1 | `CLÁUSULA \d+[A-Z]?` · `ANEXO` · `CAPÍTULO` · `SEÇÃO` |
| 2 | linha CAIXA-ALTA começando por `ASSISTÊNCIA` |
| 3 | linha CAIXA-ALTA solta |
| 4-7 | `N.` / `N.N` / `N.N.N` / `N.N.N.N` |
| 8 | título de faceta (lista da §5.1) |

⚠️ **Duas linhas de CAIXA-ALTA seguidas são parágrafo, não título.** 📊 Sem essa
guarda, um aviso em maiúsculas virou título e apagou `4.2. CONSERTO LINHA
MARROM` do caminho.

⚠️ **Número de cláusula tem de ser monotônico.** Candidato que retrocede é
descartado. 📊 O Allianz escreve `Cláusula 9 – …` no meio de frase e o detector
mordia a isca.

**Cortar:**
- Seção ≤ 2.200 caracteres → **um pedaço só**
- Acima → empacotar **blocos** (parágrafo, alínea, ou tabela inteira) até
  ~1.400 c, teto 2.200 c. **Bloco nunca é dividido.**
- Corpo < 180 c → funde com o vizinho
- **Pedaço só-título nunca é indexado**
- **Sumário: descartar.** 📊 A `CLÁUSULA 76R` aparece 2× no CG140 — uma no
  índice, uma no corpo. Indexar as duas põe uma linha de sumário competindo
  com a cláusula de verdade.

### 4.4 O cabeçalho — duas linhas em TODO pedaço

```
[<Seguradora> · <ramo> · <título do documento> · vigência <data> · SUSEP <processo>]
<Raiz> > <nível 2> > … > <folha>
<corpo>
```

Exemplo real:
```
[Porto Seguro · auto · Condições Gerais CG140 · vigência 01/07/2026 · SUSEP 15414.100233/2004-59]
CLÁUSULA 76R – DANOS A VIDROS E RETROVISORES, LANTERNAS E FARÓIS > 6. Solicitação de reembolso
```

🔴 **O cabeçalho é montado DEPOIS de picar, pedaço a pedaço — nunca antes.**
📊 Hoje o código concatena antes e pica depois; por isso só 29 de 11.409
pedaços têm etiqueta.

⚠️ Teto de 400 c no caminho: estourou, mantém **raiz + folha** e substitui o
meio por ` > … > `.

📊 Custo: ~19% do índice. E se paga — leva a pergunta do vidro de #98 para #2.

### 4.5 Tabelas

**Nenhuma tabela deste corpus é decorativa.** A resposta de carro reserva está
só em tabela.

- **A tabela é bloco atômico:** grade + título + notas de rodapé `(1)`, `*` num
  pedaço só. 📊 Sem a nota, `630` é número sem unidade.
- **Linearizar em frases** — grade em texto plano não é recuperável.
- **Corrigir célula girada:** 📊 pdfplumber devolve `odarugeS` invertido; pegar
  essas do fitz.
- **Anexo é raiz de nível 1** e nunca sai do caminho. 📊 A numeração reinicia em
  cada anexo — existem dois `4.1.1` no mesmo arquivo.

### 4.6 O resultado medido

| | hoje | com esta regra |
|---|---|---|
| frase cortada no fim | 57% | **22%** |
| começa no meio da frase | 46% | **0%** |
| não sabe de que seção veio | 69% | **10%** |
| não sabe de que seguradora é | 76% | **0%** |
| **o pedaço basta sozinho para responder** | **3/5** | **5/5** |

---

## 5. COMO O CONTEÚDO É CATEGORIZADO

### 5.1 A faceta — 8 valores, ancorados na Circular SUSEP 621/2021

A lei obriga toda condição geral a ter estas seções. **Não invente outras.**

| faceta | o que é | responde |
|---|---|---|
| `escopo` | riscos cobertos, objetivo | "cobre X?" |
| `exclusao` | riscos excluídos, bens não compreendidos | "por que negaram?" |
| `limite` | teto em reais, nº de acionamentos, diárias | "quanto? quantas vezes?" |
| `franquia` | franquia, participação obrigatória | "quanto sai do meu bolso?" |
| `carencia` | prazo até a garantia valer | "já posso usar?" |
| `prazo` | comunicação, liquidação, vigência, renovação | "quanto tempo?" |
| `documento` | o que mandar, por cobertura | "o que preciso enviar?" |
| `definicao` | o glossário obrigatório | "o que quer dizer…?" |

**Não casou nenhuma → `faceta = null`. E `null` passa em todo filtro, nunca
elimina.** Rótulo dá cota e prioridade; só fato verificável (seguradora,
vigência, documento) elimina candidato.

### 5.2 O ramo vem da SUSEP, não da nossa lista

📊 O REP2 devolve o ramo oficial numerado (`05 | AUTOMÓVEL - CASCO`,
`01 | COMPREENSIVO CONDOMÍNIO`). **Grave o código e o nome oficiais.** Criar
vocabulário paralelo ao do regulador é divergência de graça.

### 5.3 O que vai no payload de cada pedaço

**Na raiz** (é onde o filtro procura):
```
namespace: "normative"   insurer_key   product_line   doc_kind
susep_process            vigente: true                effective_from
faceta                   unit_id      parent_id       scope   curation_status
```
Dentro de `metadata` fica o resto — mas **o que filtra tem de estar na raiz**.

---

## 6. COMO TRECHO E CARTA CONVIVEM

| | **trecho** (contrato) | **carta** (conversa destilada) |
|---|---|---|
| vem de | condição geral oficial | atendimentos reais |
| responde | *o que está escrito* | *como funciona na prática* |
| autoridade | **maior** | menor |
| namespace | `normative` | `cards` |

**A regra:** se as duas discordarem sobre um fato, **o contrato ganha** e a
carta vira *"na prática, o atendimento costuma…"*. A carta nunca é apagada —
às vezes ela descreve o comportamento real da seguradora, que é o que o
corretor precisa saber.

🔴 **E elas não podem competir pelas mesmas vagas.** 📊 Hoje competem: o campo
`namespace` já existe no payload e **não é usado no filtro**. Cada um tem de ter
orçamento próprio:

```
busca 1  namespace=normative  ∧ (insurer_key=X ∨ ausente) ∧ vigente
busca 2  namespace=cards      ∧ (insurer_key=X ∨ ausente)
```

⚠️ **O filtro de vigência é de dois braços** (`vigente=true` OU chave ausente),
senão apaga as 12.063 cartas, que não têm essa chave.

---

## 7. OS LOTES — o placar

**Critério de ordem:** cartas de cobertura no acervo (sinistro + assistência +
apólice) × corredor ativo × estado do que temos. Cobrança não conta — boleto
não está no contrato.

| # | seguradora | cartas cob. | corredor | estado hoje | status | executado em |
|---|---|---:|---|---|---|---|
| **1** | **Porto** | 196 | auto+resid | 6 docs vigentes · 1.686 pedaços · cartas destiladas | ✅ | 08/08/2026 |
| **2** | **Allianz** | 356 | auto+resid | 4 docs, **todos vencidos**, sem condomínio | ⬜ | — |
| **3** | **Yelum** | 174 | auto+resid | 🔴 **ZERO documentos** | ⬜ | — |
| **4** | **HDI** | 128 | auto+resid | 🔴 **ZERO documentos** | ⬜ | — |
| **5** | **Bradesco** | 66 | auto | 5 docs, 🔴 **auto não existe** | ⬜ | — |
| **6** | **Tokio** | 65 | auto | 2 docs, processo **truncado** no banco | ⬜ | — |
| **7** | **Mapfre** | 25 | auto | 4 docs, **todos vencidos** | ⬜ | — |
| **8** | **Azul** | 19 | auto | 2 docs, só auto | ⬜ | — |
| **9** | **Zurich** | 21 | auto | 🔴 ZERO | ⬜ | — |
| **10** | **Alfa** | 17 | auto | 🔴 ZERO | ⬜ | — |
| **11** | **Sura + Suhai + Youse** | 36 | — | 🔴 ZERO | ⬜ | — |
| **12** | **Bancárias** (Caixa, Santander, BB) | — | — | 🔴 ZERO | ⬜ | — |
| **13** | **Normas do regulador** | — | — | 5 circulares | ⬜ | — |
| **14** | **Varredura final** | — | — | — | ⬜ | — |

**Legenda:** ⬜ não feito · 🔄 em execução · ✅ concluído

> **🔴 O chat que executar um lote DEVE atualizar esta tabela** — marcar ✅, a
> data, e preencher a §8 com o que entrou. Sem isso o próximo chat não sabe
> onde estamos.

---

## 8. REGISTRO DE EXECUÇÃO

*(cada lote acrescenta seu bloco aqui)*

```
LOTE 0 — Fundação (consertos)          ✅ 08/08/2026
LOTE 1 — Porto                          ✅ 08/08/2026
```

### LOTE 1 — Porto · 08/08/2026

**Coleta** (`coletar_seguradora.py --seguradora porto --aplicar`), 40 s, 0 falhos:

| ramo | pedaços | vigência oficial | o que saiu do ar |
|---|---:|---|---|
| auto | 484 | 01/07/2026 | CG140 (janeiro) → **CG144** |
| condomínio | 277 | 11/12/2025 | **o de 2012** |
| empresarial | 349 | 31/07/2026 | abril/2025 |
| residencial | 325 | 05/12/2025 | dezembro/2025 |
| fiança | 96 | 08/08/2026 | versão sem data |
| vida | 155 | 27/11/2025 | 2022 |

📊 **1.686 pedaços.** As 6 versões antigas ficaram fechadas e guardadas
(`superseded_at` + PDF no MinIO), conforme **D-Acervo-02**.

**Reprodução independente do corte.** Os pedaços foram gerados de novo fora do
servidor, a partir dos mesmos `susep_version_id`, e comparados um a um:
**idênticos nos 6 ramos** (484/277/349/96/325/155). É o que autoriza a carta a
citar `unit_id` — o endereço que ela guarda aponta mesmo para o trecho indexado.

**Destilação** — 6 subagentes Opus 5, um por ramo, com as 8 regras da §10.3.

Três alertas foram acrescentados aos prompts **durante** o lote, cada um vindo
de uma medição do subagente anterior. Eles pertencem à §10.3 daqui para a
frente:

1. **O limite mora no pedaço SEGUINTE ao título do serviço.** No residencial,
   "limite de até 3 itens" do encanador ficou no mesmo pedaço que as exclusões
   do eletricista. 📊 O destilador corrigiu 14 citações por causa disso, numa
   segunda passada. Sem o alerta, a carta gruda o limite no serviço errado.
2. **Tabela quebrada pelo OCR: não chute coluna.** Onde o cabeçalho se separou
   dos números, a instrução é escrever a carta que ensina o EIXO da resposta e
   manda conferir a apólice — nunca um número que não se pode afirmar.
3. **Diga sempre se a cobertura é básica ou opcional.** Sem isso o agente
   promete cobertura que o cliente não contratou.

**O que os destiladores recusaram destilar** — e é a parte mais valiosa do
relatório deles, porque é o que impede a carta convincente e errada:

- a tabela de diárias de carro reserva e a matriz de serviços da Assistência
  24h (auto): colunas perdidas no OCR;
- os 54 pares de percentual de reajuste por idade (vida): não dá para afirmar
  qual coluna é feminino linha a linha;
- os percentuais de depreciação (residencial): três colunas embaralhadas;
- **o regresso contra o inquilino (fiança): não existe neste contrato.** O
  destilador registrou que a afirmação "a Porto paga e depois cobra do
  inquilino" não está escrita ali, e ancorou a carta no que está — que o seguro
  não isenta o locatário. É a regra 8 funcionando.

---

---

## 9. O PASSO A PASSO DE UM LOTE

**Isto é o que o chat executa. Siga na ordem.**

### Passo 1 — Descobrir os produtos da seguradora

Consultar o catálogo (§3.1), filtrar por `entnome`, listar todos os produtos
de ramos de varejo: auto, residencial, condomínio, empresarial, vida, fiança,
equipamentos.

**Saída:** lista de `(numeroprocesso, ramo, subramo)`.

### Passo 2 — Descobrir a versão vigente de cada um

Para cada processo, consultar o REP2 (§3.2).

- Situação ≠ "Passível de comercialização" → **produto morto, pular**
- Versão com Data de Fim **vazia** → **é esta**
- Resposta vazia → registrar `indeterminado`, **nunca** "não mudou"

**Saída:** lista de `(processo, versão vigente, data de início, id de download)`.

### Passo 3 — Baixar e guardar

Baixar o PDF. **Guardar o arquivo** (MinIO) e o texto extraído.
📊 Hoje o PDF é lido e jogado fora — e a URL da HDI já morreu. Guardar é o que
permite reprocessar sem depender da rede.

### Passo 4 — Extrair e partir

Aplicar a §4 inteira: PyMuPDF → limpeza na ordem → detectar títulos → cortar
por seção → cabeçalho em cada pedaço.

**Conferência obrigatória antes de indexar** — abrir 10 pedaços ao acaso e
verificar:
- [ ] nenhum começa no meio de frase
- [ ] todos têm o cabeçalho de duas linhas
- [ ] nenhum é só título
- [ ] as tabelas estão inteiras, com as notas de rodapé

**Se falhar, pare e conserte antes de continuar.**

### Passo 5 — Indexar

Gravar em `autobrokers_global`, `namespace: normative`, com o payload da §5.3.

🔴 **A versão anterior do MESMO produto sai do índice** (D-Acervo-02) — e fica
no banco e no MinIO, endereçável por (produto, data).

### Passo 6 — Destilar cartas (subagentes Opus 5)

Ver §10.

### Passo 7 — Conferir e publicar

- Rodar o validador (vocabulário, PII, cobertura)
- **Ler 20 cartas com os olhos**, não a contagem
- Publicar

### Passo 8 — Atualizar esta SPEC

Marcar ✅ na §7 e escrever o bloco na §8: quantos produtos, quantos documentos,
quantos pedaços, quantas cartas, e o que ficou pendente.

---

## 10. OS SUBAGENTES QUE DESTILAM

### 10.1 Modelo e disparo

**Opus 5, plano Max.** 4 a 6 subagentes em paralelo — 📊 acima disso não
acelera, o limite é a janela do plano.

**Cada subagente lê um arquivo e escreve outro.** Não toca banco, não roda
script. 📊 Em 29/07 um subagente gastou 250 mil tokens para 90 conversas, dos
quais só 85 mil eram trabalho real — o resto era transporte.

### 10.2 O que o subagente recebe

Um arquivo `.jsonl` com os pedaços de UM documento, cada linha:
```json
{"unit_id": "...", "caminho": "CLÁUSULA 76R > 2. Exclusões",
 "faceta": "exclusao", "seguradora": "porto", "ramo": "auto",
 "documento": "CG140", "vigencia": "01/07/2026", "texto": "..."}
```

### 10.3 As regras que o prompt do subagente DEVE conter

**1. Destila o que é verdade sobre o PRODUTO. Não destila o que depende da
APÓLICE.**
Teste: *"duas apólices do mesmo produto podem responder diferente?"* Se sim, a
carta **ensina onde verificar** em vez de dar o número.

✅ *"Na cobertura de vidros da Porto Auto, risco, mancha e arranhão não são
cobertos — só quebra ou trinca."*
❌ *"O limite de carro reserva da Porto é R$ 630."* → varia por cláusula
contratada, porte e situação.
✅ *"O limite de carro reserva da Porto depende da cláusula 26 contratada (A a
X), do porte do veículo e da situação do sinistro — confira a cláusula na
apólice."*

**2. Não destila o que é idêntico entre seguradoras.**
Foro, prescrição, encargos de tradução, embargos e sanções são iguais em 5 de
7 documentos. Isso é `norma`, entra **uma vez**, sem seguradora.

**3. Toda carta cita a fonte.** Documento, cláusula e vigência.

**4. Nenhum dado pessoal, em campo nenhum.**

**5. A carta é uma ideia completa.** Se precisa de outra para fazer sentido, a
busca vai trazer metade da resposta.

**6. Prefira zero a encher.** Documento que não ensina nada devolve lista vazia.

**7. O teste da cauda.** Leia a última oração de cada frase e pergunte: *qual
trecho diz isto?* Se for "nenhum, mas faz sentido", **apague a oração**. O
defeito que mais machuca não é a frase errada de ponta a ponta — é o corpo
fiel com a cauda inventada.

**8. Não afirme cobertura sem o trecho.** Você tem o contrato na mão; use-o.

### 10.3.1 🔴 Os três alertas — medidos no LOTE 1, obrigatórios daqui pra frente

Cada um destes nasceu de uma medição de um destilador do LOTE 1 e foi
acrescentado ao prompt do subagente seguinte. **Vão em todo prompt.**

**A. O limite mora no pedaço SEGUINTE ao título do serviço.**
📊 No residencial da Porto, *"limite de até 3 itens"* do encanador ficou no
mesmo pedaço que as exclusões do eletricista. Uma carta montada de um pedaço só
**gruda o limite no serviço errado** — e sai convincente. O destilador que
recebeu o alerta corrigiu **14 citações** numa segunda passada; o que não
recebeu não tinha como saber que precisava conferir.

> *"Sempre confira o pedaço anterior e o seguinte antes de fixar um número."*

**B. Tabela quebrada pelo OCR: não chute coluna.**
Onde o cabeçalho se separou dos números, escreva a carta que ensina **o eixo da
resposta** e manda conferir a apólice. Nunca um número que não se pode afirmar.
📊 No LOTE 1 isso salvou quatro tabelas de virarem carta errada: diárias de
carro reserva, matriz da Assistência 24h, depreciação e reajuste por idade.

**C. Diga sempre se a cobertura é BÁSICA ou OPCIONAL.**
Sem isso o agente afirma que algo é coberto quando o cliente nunca contratou. É
o erro mais caro do atendimento porque cria expectativa — e em vida ele cai
sobre uma família em luto.

### 10.4 O formato de saída

JSONL puro. Sem vírgula entre linhas, sem array externo, sem cerca de código.
Uma linha por carta:
```json
{"texto": "...", "faceta": "exclusao", "unit_id_origem": "...",
 "seguradora": "porto", "ramo": "auto", "documento": "CG140",
 "vigencia": "01/07/2026"}
```

---

## 11. LOTE 0 — A FUNDAÇÃO

**Este vem antes de tudo.** São os consertos, num bloco só.

| # | conserto | por quê |
|---|---|---|
| 1 | **Trocar PyPDF2 por PyMuPDF** na extração | 📊 32× mais estrutura preservada |
| 2 | **Cabeçalho montado por pedaço, depois de picar** | 📊 hoje 29 de 11.409 têm etiqueta |
| 3 | **Corte por seção** (§4.3) | 📊 57% → 22% de frases cortadas |
| 4 | **Guardar PDF e texto no MinIO** | 📊 `storage_ref` vazio em 29 de 29; a URL da HDI morreu |
| 5 | **`namespace` no filtro de busca** | 📊 existe no payload e não é usado — contrato e carta competem |
| 6 | **Escritor de vigência** (`effective_from`, `effective_until`) | 📊 NULL em 35 de 35 |
| 7 | **`doc_id` versionado no Qdrant** | 📊 hoje a versão nova apaga a anterior |
| 8 | **`document_id` e `document_version` em `knowledge_cards`** | 📊 12.063 cartas não sabem de que documento vieram |
| 9 | **Parser do REP2** | é a fonte |
| 10 | **Índices de payload:** `insurer_key`, `namespace`, `vigente`, `faceta` | 📊 hoje só existem 3, e nenhum é desses |
| 11 | **Corrigir os 3 processos malformados** | 📊 devolvem 200 vazio |
| 12 | **Manifesto de migration** para `normative_documents` e `..._versions` | 📊 são tabelas órfãs; o CLAUDE.md §8 exige |
| 13 | **Ligar o reranker Cohere** | 📊 não é trabalho: é uma variável de ambiente. Sem ela, `rerank()` vira `docs[:3]` — trunca sem reordenar, pegando os 3 primeiros de uma fusão que não mede relevância |

⚠️ **O item 12 vem antes de qualquer SQL.**

**Pronto quando:** um documento novo entra pelo REP2, é partido pela §4, indexado
com cabeçalho em todos os pedaços, e a versão anterior sai do índice e continua
no banco.

---

## 12. O CHECKLIST

```
⬜ LOTE 0   fundação (consertos)                    1 bloco
⬜ LOTE 1   Porto                                   💭 2-3 h
⬜ LOTE 2   Allianz                                 💭 2-3 h
⬜ LOTE 3   Yelum                                   💭 2-3 h
⬜ LOTE 4   HDI                                     💭 2-3 h
⬜ LOTE 5   Bradesco                                💭 2-3 h
⬜ LOTE 6   Tokio                                   💭 2 h
⬜ LOTE 7   Mapfre                                  💭 2 h
⬜ LOTE 8   Azul                                    💭 1-2 h
⬜ LOTE 9   Zurich                                  💭 1-2 h
⬜ LOTE 10  Alfa                                    💭 1-2 h
⬜ LOTE 11  Sura + Suhai + Youse                    💭 2 h
⬜ LOTE 12  Bancárias                               💭 2-3 h
⬜ LOTE 13  Normas do regulador                     💭 1 h
⬜ LOTE 14  Varredura final — "acabou?" com número  💭 2 h
```

💭 **Total: 25 a 35 horas, em 15 disparos.**

### O critério de PRONTO

```
para cada seguradora que uma corretora nossa pode vender:
  para cada ramo que ela vende:
    existe o documento VIGENTE, indexado, partido por seção,
    com cabeçalho em todos os pedaços, e cartas destiladas dele
```

O LOTE 14 confirma isso **por contagem**, não por impressão.

---

## 13. O QUE FICA PARA DEPOIS

| item | por quê |
|---|---|
| **Agente de auto-atualização** | Decisão do Founder: não é prioridade. O ciclo manual funciona — basta pedir a um chat que confira. |
| **Matriz de assistência serviço × plano** | Exige leitura de layout. É o item mais caro e o que não termina. |
| **Ficha de produto completa** | Fica com 2 campos: `coberturas_de_outro_ramo` e o mapa cláusula → unidade. |
| **Comparação entre seguradoras** (fan-out) | Depois que houver acervo de duas seguradoras completas para comparar. |
