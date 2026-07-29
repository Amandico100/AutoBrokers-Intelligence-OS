# CURADORIA POR SUBAGENTES — o braço operacional do conhecimento

> **Como usar:** abra um chat novo no Claude Code (VS Code) e envie:
>
> ```
> Leia docs/canon/CURADORIA-POR-SUBAGENTES.md e execute uma CAMPANHA de
> curadoria. Objetivo: <o que você quer>. Fonte: <de onde vem o material>.
> ```
>
> O chat lê este arquivo e sabe o resto. Não precisa explicar o método de novo.

**v1.0** · 29/07/2026 · nasceu quando US$ 6 de API viraram 457 conversas e
faltavam 6.118.

---

## 1. Para que serve — e para que NÃO serve

| | Quem faz | Quando |
|---|---|---|
| **Conversa que chega hoje** | Central de Agentes (API, automático) | sempre |
| **Base grande, uma vez só** | **Subagentes (plano Max)** | pareamento, acervo, migração |

A Saionara e a Regina continuam atendendo, e o que elas fizerem hoje será
destilado pela Central automaticamente. Isso não muda.

O que muda é o **trabalho de fundação**: o histórico inteiro de uma corretora
recém-pareada, as condições gerais de uma seguradora, um acervo de manuais. São
volumes que chegam de uma vez, custam caro por API e **não têm pressa de
minutos**. Esses passam por aqui.

**Regra de decisão:** se o material já existe e ninguém está esperando a
resposta agora, é campanha de subagentes. Se está chegando em tempo real, é
Central de Agentes.

---

## 2. O princípio que não se negocia

> **Nenhuma peça deste caminho pode ser um segundo motor.**

Os scripts em `backend/scripts/destilacao_max/` não implementam regra nenhuma:

- `mascarar.py` **importa** `templatize` e `sem_copias` de produção
- `aplicar_sql.py` **espelha** `_store_card_sync` (md5, 15–400 chars, status)
- quem publica no Qdrant continua sendo o publicador de `distill_once`

A carta escrita por um subagente entra pela mesma porta, com a mesma checagem
de PII, e é indistinguível de uma escrita pela Central. É isso que permite
voltar ao normal sem migração nenhuma. CLAUDE.md §5.

---

## 3. As quatro fases

### Fase 1 — EXPORTAR (custo zero, sem contexto)

```bash
cd backend
python scripts/destilacao_max/exportar.py --lotes 60 --por-lote 100 \
       --saida ../lotes_resulta [--empresa <company_id>]
```

Sai do banco já **mascarado** e cai no disco. Nenhum texto de cliente passa
pelo contexto de ninguém — nem do chat, nem do subagente, antes do portão.

> **Por que existe:** na prova de 29/07 o gargalo não foi ler nem escrever, foi
> **transportar** o texto pelo canal de ferramentas — três passagens pelo
> contexto por conversa. A 6.118 conversas isso não escala.

### Fase 2 — DESTILAR (subagentes, plano Max)

Um subagente por lote, **em paralelo**. Cada um recebe:

1. o caminho do `lote_NNN.jsonl` (já mascarado)
2. o briefing de qualidade da §4
3. onde gravar o `lote_NNN.destilado.jsonl`

**Paralelismo:** 4 a 6 subagentes simultâneos. Mais que isso não acelera —
o limite é a janela de uso do plano, não a máquina.

**Modelo:** Opus 5 para escrever conhecimento. É a decisão do Founder de
19/07 aplicada aqui: o estrutural merece o modelo mais forte. Só use Sonnet 5
se o material for mecânico (transcrição, classificação de formulário).

### Fase 3 — APLICAR

```bash
python scripts/destilacao_max/aplicar_sql.py lote_001.destilado.jsonl > lote_001.sql
```

SQL idempotente com aspas em dólar. Rodar duas vezes não duplica nada:
`WHERE summary->'distilled' IS NULL` e `ON CONFLICT (card_hash) DO NOTHING`.

### Fase 4 — PUBLICAR

Não faça nada. O publicador automático de `distill_once` cura as quase-cópias
e manda para o Qdrant com vetor denso e esparso. **Funciona mesmo com o teto de
gasto em zero** — publicar não chama modelo de linguagem, só o embedding, que
custa centavos.

---

## 4. Briefing de qualidade — o que separa carta boa de lixo no RAG

Todo subagente recebe estas regras. Elas não são estilo, são o produto.

**A carta tem de fazer sentido para quem não leu a conversa.**

```
Ruim   "Precisa do documento."
Ruim   "A seguradora pede o boletim."
Bom    "A HDI exige boletim de ocorrência para abrir sinistro de roubo de
        veículo; sem ele o processo não é protocolado."
```

**Prefira zero a encher.** Se a conversa não ensina processo, devolva
`fatos_reutilizaveis: []`. Fato inventado ou genérico demais **envenena o RAG**:
ele disputa espaço de contexto com a carta que resolveria o caso.

**Nunca:** nome, telefone, placa, CPF, valor, endereço, número de apólice — em
nenhum campo. A conversa já chega mascarada; o que você escrever também tem de
estar.

**Seguradora só quando ela aparecer.** Inferir a seguradora pelo assunto é o
erro mais caro possível: uma regra da Porto atribuída à Allianz faz o agente
mentir para o segurado com confiança.

---

## 5. Regra por seguradora × regra de consenso

Este é o ponto mais delicado do acervo, e a estrutura já existe para resolvê-lo:
o campo `insurer_key` da carta.

| `insurer_key` | Significa | Exemplo |
|---|---|---|
| `hdi`, `porto`, `allianz`… | **regra daquela seguradora** | "A Porto exige B.O. para roubo" |
| `NULL` | **consenso de mercado** | "Franquia é o valor que o segurado paga em caso de sinistro parcial" |

**Como decidir, em uma pergunta:** *outra seguradora poderia fazer diferente?*
Se sim, a carta é da seguradora. Se não — se é definição, lei ou prática
universal — é consenso, e `seguradora` fica vazio.

Na dúvida, **marque a seguradora**. Uma regra específica marcada como consenso
espalha o erro por todas; uma regra geral marcada como específica só deixa de
aparecer em uma busca.

A curadoria já respeita isso: quase-cópias **só são unidas dentro da mesma
seguradora**. "A HDI gera boleto" e "a seguradora gera boleto" continuam sendo
duas cartas, porque a primeira é o que dá confiança ao agente quando o segurado
é da HDI.

---

## 6. Campanha de ACERVO (condições gerais, manuais, regras)

Quando o material não é conversa, mas documento — condições gerais, circulares,
manuais de sinistro — muda a fase 1 e o briefing ganha uma etapa.

### 6.1 Fonte: verificar antes de destilar

**Ordem de confiança, da maior para a menor:**

1. **Site oficial da seguradora** — condições gerais em PDF, processo SUSEP
2. **SUSEP** — normas, circulares, consulta de produto registrado
3. **Portal do corretor** da própria seguradora (exige login — o Founder fornece)
4. Material de treinamento da seguradora, datado
5. ~~Blog, portal de notícias, resumo de terceiro~~ — **nunca como fonte única**

**Toda carta de acervo carrega a origem.** Se o subagente não consegue apontar
de onde veio, a carta não entra. Conhecimento sem procedência é passivo: no dia
em que o agente errar, ninguém saberá se a regra mudou ou se foi inventada.

**Verificar antes de aceitar:** confira o número do processo SUSEP e a vigência.
Condição geral de 2019 substituída em 2024 é informação errada com cara de
certa — o pior tipo.

### 6.2 Organização obrigatória

Toda carta de acervo é classificada em quatro eixos:

```
seguradora  →  hdi | porto | allianz | yelum | tokio | zurich | (vazio = consenso)
ramo        →  auto | residencial | vida | empresarial
assunto     →  sinistro | assistencia | cobranca | cancelamento |
               apolice | vistoria | documentos | processo
tipo        →  cobertura | exclusao | prazo | documento | franquia | procedimento
```

**Exclusão é tão valiosa quanto cobertura.** "A Porto não cobre chaveiro em
sinistro de roubo" evita uma promessa que a corretora não pode cumprir — e é
justamente o que não aparece em conversa nenhuma, porque ninguém liga para
perguntar o que não existe.

### 6.3 Granularidade

Uma carta = **uma ideia completa**. Não corte uma regra em três nem junte cinco
numa só. A carta É o chunk do RAG: se ela precisa de outra para fazer sentido,
a busca vai trazer metade da resposta.

---

## 7. O que o agente faz com isso — e o que ele NUNCA faz

> Founder, 28/07/2026: *"O agente precisa ver as cartas como referência, mas
> precisa ser inteligente na hora de responder. Não dá pra responder cópias de
> cartas. Precisa ser idêntico a um humano respondendo, com perfeição."*

A carta é **fonte**, não resposta. O agente lê três cartas e escreve uma frase
sua, no tom de quem conhece o assunto. Copiar e colar a carta entrega o
constrangimento de um robô e não resolve o caso do segurado.

Por isso o `resumo_conduta` e as `perguntas_na_ordem` existem e não são
descartados: eles alimentam os **playbooks de conduta**, que ensinam *como* a
melhor atendente conduz — a diferença entre saber a informação e saber atender.

---

## 8. Checklist de campanha

Antes:

- [ ] `DESTILADOR_TETO_POR_RODADA=0` — a Central não gasta enquanto a campanha roda
- [ ] `.env` de `scripts/destilacao_max/` presente (fora do git)
- [ ] escopo definido: qual corretora / qual acervo / quantos lotes

Durante:

- [ ] 4–6 subagentes em paralelo, um por lote
- [ ] conferir o primeiro lote **antes** de disparar os outros 60
- [ ] nenhum subagente inventa fato para preencher

Depois:

- [ ] `select count(*) from knowledge_cards where pii_check->>'por' = '<marca>'`
- [ ] ler 10 cartas ao acaso — elas fazem sentido isoladas?
- [ ] rodar o publicador (o teto em zero não impede)
- [ ] religar a Central: `DESTILADOR_TETO_POR_RODADA=<n>`

---

## 9. Quando isto acaba

Quando a Resulta e a AutoFleet estiverem com a inteligência montada, a Central
volta a fazer o trabalho corrente — com **Batch API a 50% de desconto**, que é
o formato certo para destilação (ninguém está esperando).

Este caminho **não é descartado**: ele fica de pé para as próximas 20 ou 30
corretoras e para todo acervo novo. É a diferença entre pagar API por uma
fundação que se constrói uma vez, e pagar API pelo que chega todo dia.
