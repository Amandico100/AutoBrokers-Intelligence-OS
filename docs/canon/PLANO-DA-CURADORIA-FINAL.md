# Plano da curadoria final — o que ainda vira conhecimento

> **Criado em 08/08/2026** · commit base `94bd4b2` · autoridade: CLAUDE.md ·
> SPEC-052 (cérebro) · SPEC-056 (Skills) · [`D-Playbook-01`](FOUNDER-DECISIONS.md)
>
> **A frase que resume:** o acervo já é grande; o que falta não é volume, é
> **fechar as torneiras que pingam para fora** e **transformar em conduta o que
> já foi destilado e nunca virou playbook**.

---

## 0. O estado, medido — 08/08/2026

Tudo abaixo saiu de `SELECT` no banco de produção ou do `conferir_indice.py`
rodado no contêiner. Nada é estimativa.

```
ÍNDICE (Qdrant, autobrokers_global)      23.478 pontos
   cards ................................ 12.063   = as 12.063 published
   normative ............................ 11.409   = condições gerais
   canon ................................      6
   com `insurer_key` na raiz ............     25   ← reindexação em curso

BANCO
   attendance_sessions .................. 11.109   destiladas 9.196
   observed_sessions (seguradora) .........  553   destiladas   319
   knowledge_cards ...................... 12.933   published 12.063
   normative_documents ..................     35   ingested    29
   conduct_playbooks .................... 18 (12 ativos, 6 rascunhos)
```

**As três campanhas que já rodaram**, e o que cada uma custou:

| quando | material | conversas | cartas | custo |
|---|---|---:|---:|---|
| 28-30/07 | atendimento, por API | 8.872 | 9.699 | US$ 11,59 |
| 04/08 | atendimento, plano Max | 1.784 | 1.499 | **US$ 0,00** |
| 06/08 | seguradora, plano Max | 319 | 1.253 | **US$ 0,00** |

📊 O plano Max já provou que destilar não custa API: 27 subagentes Opus 5,
pacotes de 70 conversas, zero reprovados pelo validador.

---

## 1. A descoberta que reordena tudo

**O maior ganho disponível hoje não precisa de destilação nenhuma.**

📊 Os 18 playbooks existentes foram todos escritos com **30 conversas**, e
existem milhares. `auto/sinistro` usa 2,1% do material que tem. E há grupos
grandes sem playbook nenhum:

| grupo | atendimentos úteis | nota | playbook |
|---|---:|---:|---|
| **auto/cobranca** | **1.904** | **76,2** | 🔴 **nenhum** |
| **outro/cobranca** | **986** | 72,7 | 🔴 **nenhum** |
| residencial/cobranca | 25 | 76,6 | 🔴 nenhum |
| outro/renovacao | 17 | 68,8 | 🔴 nenhum |

📊 E a cobrança é **24% do acervo do RAG** (2.915 de 12.063 cartas) — o maior
bloco de trabalho da corretora, sem uma linha de conduta escrita.

**Por que isso é possível sem destilar:** as 9.196 sessões **já estão
destiladas**. A síntese do playbook lê 30 resumos prontos, não relê transcript
nenhum. 📊 Referência do próprio repositório: 11 chamadas ao Opus 5 na síntese
custaram US$ 0,45 — **~US$ 0,04 por playbook**.

📊 E a contradição que parecia existir entre dois relatórios se resolveu: a
campanha de 28/07 destilou 3.343 conversas de cobrança (50% dela); a de 04/08
destilou 5. As duas medidas estavam certas — a cobrança já estava no acervo, e
o lote de 04/08 pegou o que sobrou.

---

## 2. O que bloqueia, e sai primeiro

### 🔴 B1 — O filtro de valor não existe

`PENDENCIAS.md` P-67 e `RUNBOOK-A-NOITE-DA-DESTILACAO.md:65`:

> *"conversa doméstica → transcrição → carta → RAG. **Nada nesse caminho
> pergunta 'isto é sobre seguro?'**"*

O filtro de PII existe e funciona (📊 310 cartas rejeitadas). Este é outro: uma
conversa pode estar **perfeitamente anônima** e continuar não valendo nada. E
`pending_review → published` acontece **sem aprovação humana**.

Precedente real: em 03/08 o Observador capturou 630 contatos pessoais, 2.556
transcrições e 745 sessões. Foi contido e revertido, zero cartas geradas — mas
por sorte. *"Da próxima vez pode ser o telefone pessoal de um corretor de
verdade — e aí não é reversível com um DELETE nosso."*

### 🔴 B2 — A marca da campanha está congelada

`aplicar.py:51` — `MARCA = "destilacao_max_29_07_2026"`, constante nunca
trocada. 📊 As 1.941 cartas de 04/08 foram gravadas com a marca de 29/07: são
indistinguíveis pelo marcador, e a conferência que o checklist manda fazer
devolve as duas campanhas juntas.

### 🔴 B3 — `aplicar.py` marca a sessão antes de gravar as cartas

`aplicar.py:146` grava o "não volte mais" dentro do laço; o `upsert` das cartas
só acontece no fim do arquivo. Não é transação. P-109: *"as sessões já marcadas
ficam declaradas destiladas sem uma carta no acervo... a perda não deixa rastro
nenhum."* `aplicar_seguradoras.py:94-100` inverteu de propósito; este não.

---

## 3. O que será destilado — a lista fechada

Ordenada por **valor entregue ÷ esforço**, não por tamanho.

### Setor A — Conduta (não destila; sintetiza o que já existe)

| # | O que | Volume | Custo | Como |
|---|---|---|---|---|
| A1 | Playbooks dos 4 grupos sem nenhum | 4 | 💭 ~US$0,16 | síntese sobre resumos prontos |
| A2 | Versão 2 dos 14 existentes | 14 | 💭 ~US$0,56 | idem — hoje usam 30 conversas de milhares |

**Por que primeiro:** é o único item que muda o atendimento **amanhã**, custa
centavos e não depende de nada externo.

### Setor B — Atendimento (destilação nova)

| # | O que | Volume | Como |
|---|---|---|---|
| B1 | Sessões capturadas depois de 29/07 | **146** | 2 pacotes de 70, subagentes Opus 5 |
| B2 | Falsas-prontas com material real | **555** | investigar amostra antes; podem ser robô legítimo |
| B3 | Transcrições órfãs de sessão | **3.743 linhas** | ⚠️ precisa de correlação antes — não é destilação |

📊 **O que NÃO entra:** as 1.767 "sessões brutas" têm teto de **80 caracteres**
e 5 mensagens; 483 têm zero texto. São *"ok"*, *"obrigado"*, figurinha.
Destilá-las seriam 1.767 chamadas de modelo para colher 29 mil caracteres — o
pior retorno do inventário inteiro. **Ficam de fora, e isto é decisão
registrada, não esquecimento.**

### Setor C — Seguradora (o acervo que ensina o outro lado)

| # | O que | Volume | Ressalva |
|---|---|---|---|
| C1 | Sessões observadas novas | **13** | posteriores a 06/08, densas |
| C2 | Sessões magras descartadas | **221** | 📊 média de 2,1 eventos contra 62,3 das aproveitadas. Foram cortadas **de propósito** — 📊 sessão com ≤48 eventos deu 1 carta boa em 9 (11%). Reprocessar é provavelmente desperdício; medir 20 antes de decidir. |
| C3 | Eventos órfãos de sessão | **838** | mesma investigação de B3 |

### Setor D — Normativo (não destila; conserta e liga)

| # | O que | Custo | Nota |
|---|---|---|---|
| D1 | Destravar os 6 documentos parados | zero | 2 com erro de origem (HTTP 408/500) |
| D2 | Instalar o Radar de mercado | zero | 📊 código completo, **nunca chamado uma vez** |
| D3 | Varredor de estado órfão | zero | `vencidos()` não enxerga `fetching` — na próxima falta de crédito, repete |

---

## 4. A SUSEP — o que fica de fora, e por quê

📊 **A SPEC-066 existe** (746 linhas, 01/08/2026) e **nunca foi executada**: o
commit que a criou tocou só o `.md`, a branch não existe, nenhuma das 5
migrations foi escrita.

O achado dela foi **verificado à mão** em 30/07: o repositório da SUSEP é
público, sem senha e sem captcha, e devolve **todas as versões** de um produto
com data. Uma consulta real trouxe 72 versões de um produto Allianz.

**Ela não entra nesta campanha**, por três motivos medidos:

1. 📊 O **Bloco 0 dela é declarado obrigatório** e depende de uma coluna do SES
   (`sinistro_ocorrido`) que **não foi confirmada** — quem tentou reconferir
   levou 404 (P-22). *"A SPEC-066 inteira assenta nisso."*
2. 📊 O sistema **já tem** 29 documentos e 11.409 trechos de condições gerais.
   O que falta não é texto — é **vigência**: zero documentos com data de fim,
   uma única versão por documento. Isso é código novo, não curadoria.
3. É trabalho de engenharia (cliente HTTP, modelo temporal, ingestão do SES),
   não de destilação. Misturar as duas coisas atrasa as duas.

**O que cabe agora, de graça:** D1, D2 e D3 acima.

---

## 5. Como será executado

### O princípio, herdado da campanha que funcionou

> **"O modelo pensa, o script carrega."**

📊 Em 29/07 cada subagente gastou ~250 mil tokens para ~90 conversas, dos quais
só ~85 mil eram trabalho real — o resto era transporte. Desde então o subagente
**só lê um arquivo e escreve outro**: não toca banco, não roda script.

### O pipeline

```
1. EXPORTAR    script, custo zero, o texto não passa pelo contexto de ninguém
2. DESTILAR    N subagentes Opus 5 em paralelo, 4-6 por vez, plano Max
3. VALIDAR     validar.py — JSONL puro, vocabulário, PII, cobertura
4. APLICAR     aplicar.py (com B2 e B3 consertados)
5. PUBLICAR    automático: dedup 0,47 + contradição + Qdrant
```

### A regra de ouro antes da leva

Do runbook, e não se negocia:

> **Amostra de 20 antes da leva, com um papo pessoal incluído como linha de
> controle. Ele TEM de ser recusado. Se passar, a noite não começa.**

E as 20 cartas se leem **com os olhos**, não pela contagem.

### Quem faz o quê

| papel | quem |
|---|---|
| montar lotes, disparar, revisar, decidir | a liderança (contexto preservado para julgar) |
| ler conversa e escrever fato | subagentes Opus 5, um por lote |
| conferir antes do banco | `validar.py` |
| ler as 20 da amostra | 🧑 Founder + liderança |

---

## 6. As armadilhas conhecidas — todas com evidência

| # | Armadilha | Evidência |
|---|---|---|
| 1 | Reaplicar `templatize` em transcript montado **apaga a fala do cliente** | 📊 aconteceu 3× em 29/07, 278 sessões |
| 2 | A mesma sessão cobrada rodada após rodada | 📊 US$ 15 de US$ 22 compraram o mesmo erro |
| 3 | `hash()` de string é aleatório por processo | 📊 acervo dobrado: 2,66× e 1,99× |
| 4 | Corte silencioso em 7.000 caracteres | 📊 5 de 1.784 hoje; 47 sessões já perdidas assim |
| 5 | PostgREST corta em 1.000 linhas sem avisar | 📊 mapa da Allianz construído sobre 40% do material |
| 6 | Rótulo de seguradora que mente | 📊 só 32,3% citavam a própria; 2.582 rebaixados |
| 7 | Banco limpo, índice sujo | P-101 — *"a auditoria no banco diz que está resolvido"* |
| 8 | A fila mente: "pendente" que guarda "impossível" | 📊 1.775 de 1.779 tinham < 80 caracteres |
| 9 | Carta errada ≠ carta desatualizada | 📊 6 famílias no RAG; **5 são regra que MUDOU**, e nenhum teste pega |

---

## 7. O que fica registrado e não se executa agora

- **Mídia e áudio** — decisão do Founder em 08/08: ficam para depois da
  destilação. 📊 São 15.656 mídias, das quais 6.390 áudios, e 15 dos 27
  destiladores relataram que *"quanto mais resolutivo o atendimento, mais ele
  acontece em áudio"*. É o maior sumidouro conhecido do acervo.
- **Ramos novos** (condomínio, empresarial, RC, fiança) — [P-127](PENDENCIAS.md).
- **SUSEP / SPEC-066** — §4 acima.
- **Aprovação humana por lote** antes de `published` — recomendada no runbook,
  decisão do Founder pendente.

---

## 8. O relógio que ninguém pode ignorar

📊 `ATTENDANCE_RETENTION_DAYS=90`, contado da **ingestão**, não da conversa:

```
ingerido 28/07/2026  →  expira 26/10/2026  →  58.865 linhas
ingerido 29/07/2026  →  expira 27/10/2026  →  10.284 linhas
ingerido 04/08/2026  →  expira 02/11/2026  →  31.758 linhas
```

O destilado é permanente; **o cru não**. O que não virar conhecimento até lá
deixa de existir. `observed_events` não tem retenção nenhuma — nunca expira.
