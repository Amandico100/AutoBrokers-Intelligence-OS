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

📊 Medições de 15/08/2026, fonte `knowledge_cards` (18.621 cartas) e
`backend/scripts/acervo/`.

### 3.1 O que já temos

| | medido |
|---|---|
| cartas com tema `documentacao` | **2.835** |
| cartas citando ≥1 documento nomeado | 2.230 |
| cartas citando ≥3 documentos — "é uma lista" | **187** (1,07%) |
| das 187, **sem `insurer_key`** | **102 (54,5%)** |
| seções de documentos no texto **bruto** das condições gerais | **63 seções · 73.749 caracteres** |
| cartas do acervo com `faceta='documento'` | **380**, em 32 pares seguradora×ramo |

### 3.2 O buraco, por situação — cartas de auto que citam documento

```
situação          allianz  hdi  porto  yelum
colisão              3      2     2      0     ← a mais comum, quase vazia
roubo/furto          5      6    10      6
perda total          4     18     4      8
vidros               1      1     2      0
terceiro            10      6     6      7
incêndio             0      0     0      0     ← zero em todas
PJ                   3      5     0      2
```

📊 E o buraco maior: **4 seguradoras com acervo, contra 15 com portal
cadastrado.** Cobertura **26,7%**.

### 3.3 Os três defeitos de origem

**① O rótulo existe e o banco o descarta.**
`faceta='documento'` classifica 380 cartas. Em `publicar_cartas.py` o valor é
validado, viaja até o payload do Qdrant e **nunca entra no Postgres** —
`knowledge_cards` não tem coluna `faceta`. O trabalho foi feito e jogado fora.

**② A tabela de documentos morreu na extração.**
O pedaço mais importante da Yelum:
```
caminho: GLOSSÁRIO > TABELA DE DOCUMENTOS NECESSÁRIOS À REGULAÇÃO DE SINISTROS
corpo:   "Documentos necessários PP"        ← 25 caracteres. É isso.
```
A matriz seguradora × tipo-de-sinistro virou um cabeçalho sem linhas. A HDI tem
a mesma tabela, também vazia. **O sistema sabe ler a legenda e não tem as
células** — e é isso que explica o buraco "colisão" acima: a lista por situação
morava na tabela, e tabela em PDF não sobrevive a extração de prosa.

**③ A destilação em prosa perde item de lista — e isso é medido.**

📊 Núcleo comum de documentos entre seguradoras:
```
medido nas cartas DESTILADAS ......  5 de 16
medido no texto BRUTO ............ 12 de 16
```
**"Dados bancários" saiu de 0/4 para 3/3.** As três seguradoras exigem; nenhuma
carta destilada de auto registrou.

> **A divergência aparente entre companhias é artefato da destilação, não
> diferença entre seguradoras.**

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

---

## 5. Os blocos

### BLOCO 1 · O rótulo que já existe volta a ser guardado

**Problema:** `faceta` é produzida, validada, mandada ao Qdrant e descartada
antes do Postgres.

**Entrega:**
- migration expand-first: `ALTER TABLE knowledge_cards ADD COLUMN faceta text`
  + índice parcial `WHERE faceta IS NOT NULL`
- `publicar_cartas.py` grava o valor que já carrega
- backfill das 380 cartas por `source_unit_id`

**Gate:** 📊 `SELECT count(*) FROM knowledge_cards WHERE faceta='documento'`
devolve ≥ 380. Uma busca filtrando `faceta='documento' AND insurer_key='hdi'`
devolve resultado.

**Ganho isolado:** mesmo que a SPEC pare aqui, o agente passa a poder pedir "só
as cartas de documento desta seguradora" em vez de torcer pela busca semântica.

**Esforço:** 2–3h.

---

### BLOCO 2 · Recuperar as 63 seções do bruto *(o coração)*

**Problema:** 📊 73.749 caracteres de listas alfabéticas completas (`a)` … `hh)`),
organizadas por cobertura e por evento, estão em
`backend/scripts/acervo/pedacos/*.jsonl.gz` — e a destilação em prosa perdeu 7
dos 16 tipos de documento no caminho.

**Entrega:**
- extrator que lê as seções de documentos do bruto e produz **uma carta por
  (seguradora × situação)**, preservando `unit_id` para rastreabilidade
- **não destilar em prosa** — a lista sai como lista
- ⚠️ 5 das 63 seções estão truncadas na origem: registrar quais, não completar
  por dedução

**Gate:** para cada par (seguradora × situação) coberto, a carta gerada contém
**todos** os documentos que a seção bruta lista. Teste: escolher 5 seções ao
acaso, contar os itens na origem e na carta. **Divergência = falha.**

**Ganho:** 📊 sai de 5/16 para 12/16 de vocabulário de documento. É a maior
recuperação da SPEC e **não depende de nenhuma fonte nova**.

**Esforço:** 1–2 dias.

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

### BLOCO 5 · As 11 seguradoras sem acervo — 🧑 depende do Founder

📊 Mapfre, Tokio, Bradesco, Zurich, Azul, SulAmérica, Sompo, Suhai, Sura, Alfa,
Seguros Unimed: **zero condição geral no repositório.**

**O que destrava:** o PDF das condições gerais, ou credencial do portal.

**Enquanto não vier:** as cartas dessas seguradoras usam o **núcleo comum**
(12/16 documentos), marcado como tal — *"esta é a lista padrão de mercado;
confirmo com a companhia o que é específico"*. **Marcado, nunca apresentado como
regra da companhia.**

⚠️ Sem este bloco a cobertura fica em **26,7%**. Ele é o único que não depende
de execução.

---

## 6. O que esta SPEC NÃO faz

- **Não cria tabela nova.** A carta com teto de 1.800 comporta a lista.
- **Não cria ferramenta nova.** A busca existente, com `faceta` + `insurer_key`
  + `temas`, acha.
- **Não mexe no motor de RAG, no publicador nem no destilador.**
- **Não completa por dedução** nenhuma seção truncada nem nenhuma tabela perdida.
- **Não resolve P-171** (as três respostas do link de vistoria expirado) — depende
  de confirmação da prestadora.

---

## 7. Riscos

| risco | mitigação |
|---|---|
| a lista extraída do bruto reflete condição geral **vencida** | conferir vigência antes do backfill; a carta cita `unit_id` |
| o núcleo comum (12/16) foi medido em **3 seguradoras** | marcar como núcleo, nunca como regra da companhia |
| a métrica "3+ documentos nomeados" é regex — **187 é piso, não teto** | tratar como piso em todo relatório |
| carta de 1.800 caracteres pode ser cortada por um limite que eu não achei | o teste do Bloco 2 conta itens na origem e no destino |

---

## 8. Gate final da SPEC

1. 📊 `faceta='documento'` responde no Postgres para ≥ 380 cartas
2. 📊 uma carta completa por (seguradora × situação) para as 4 seguradoras com
   acervo, com contagem de itens conferida contra a origem em 5 amostras
3. 📊 os 10 documentos difíceis têm "onde pegar", e o B.O. resolve por UF
4. um atendimento de teste entrega a lista completa, em rajada única, com "o que
   trava" — e ecoa o que já recebeu
5. relatório com FATO / INFERÊNCIA / RECOMENDAÇÃO separados, e o que ficou fora
6. nenhum motor paralelo criado — declaração explícita

---

## 9. Ordem de execução

```
Bloco 1  (2-3h)   ─┐ independentes, podem ir juntos
Bloco 3  (1 dia)  ─┘
      ↓
Bloco 2  (1-2 dias)   depende do Bloco 1 (precisa da coluna faceta)
      ↓
Bloco 4  (1 dia)      depende do Bloco 2 (precisa da carta completa existir)

Bloco 5  🧑 Founder — em paralelo, a qualquer momento
```

**Total de execução: 3 a 5 dias.**
