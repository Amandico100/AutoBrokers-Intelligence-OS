# A noite da destilação — o runbook que espera a sua palavra

> **Estado:** pronto e **parado de propósito**. Nada aqui roda sozinho.
> **Gatilho:** o Founder avisar. Palavras dele: *"Quando eu avisar, nós faremos
> a destilação. Eu quero fazer isso de madrugada, com você autorizando
> subagentes para fazerem as cartas."*
> **Escrito em:** 04/08/2026 · **Autoridade:** [D-Observador-02](FOUNDER-DECISIONS.md)

---

## 1. Por que existe uma noite, e não um botão

A destilação lê conversa real, decide o que virou conhecimento e escreve carta
no cérebro global — o que **todas** as corretoras vão ler depois. Errar aqui não
quebra uma tela: envenena a memória do produto.

E ela custa. Por isso não é uma rotina que acorda sozinha: é uma operação com
hora marcada, teto de gasto declarado e alguém olhando.

---

## 2. O material que está esperando

📊 Medido em 04/08/2026 (Supabase `dcajcvlzcjbmyapmklil`):

```
attendance_transcripts     69.150 linhas    AutoFleet 9.982 · Resulta 59.168
attendance_sessions          8.872 fechadas  8.865 com resumo
knowledge_cards              8.916 published · 468 superseded
                               310 rejected_pii · 5 rejected_absoluto
```

🔴 **Todas as 9.699 cartas nasceram entre 28 e 30/07.** A máquina rodou uma vez
e parou. 📊 `DESTILADOR_TETO_POR_RODADA` tem padrão **`0`**, e `0` significa
"não destile nada".

⏳ **E o material tem prazo.** O purge de retenção apaga o cru 90 dias depois da
captura — por volta de **27/10/2026**. Depois disso não há o que destilar.

---

## 3. O que MUDOU no critério, e é a parte nova

Decisão do Founder de 04/08 ([D-Observador-02](FOUNDER-DECISIONS.md)):

> *"Não precisamos ter milhões de cartas. Precisamos ter um cérebro
> inteligentíssimo que entende tudo de seguros, de atendimento. E precisamos que
> conversas pessoais que não vão aumentar a inteligência do nosso cérebro não
> sejam colocadas no RAG."*

Isso separa duas coisas que estavam grudadas:

```
CAPTURAR    amplo. Telefone pareado por corretora é oficial de atendimento.
            Perder conversa é irreversível; guardar não é.

DESTILAR    seletivo. "Isto aumenta a inteligência do cérebro?"
            Papo pessoal, agendamento de almoço, corrente de bom-dia: NÃO.
```

> **O filtro de valor não é um filtro de PII.** O de PII já existe e funciona
> (📊 310 cartas rejeitadas por isso). Este é outro: uma conversa pode estar
> perfeitamente anônima **e continuar não valendo nada** para o cérebro.

⚠️ **Esta peça ainda não existe.** É o primeiro item da lista de execução.

---

## 4. Antes da noite — o que tem de estar verdadeiro

| # | Condição | Por quê |
|---|---|---|
| 1 | Os WhatsApps das corretoras **pareados** e capturando | 🧑 o Founder quer conversa nova, não só o acervo velho |
| 2 | **Zero duplicação** no repareamento | 📊 o `history_sync` reentrega tudo; sem dedupe o acervo dobra |
| 3 | O **filtro de valor** implementado e testado | senão a noite produz milhares de cartas sem valor |
| 4 | **Teto de gasto** declarado e visível | destilar 8.872 sessões sem teto é cheque em branco |
| 5 | Uma **leva pequena** rodada e conferida à mão | ninguém aprova 9 mil cartas que não viu |

---

## 5. A noite, passo a passo

**Passo 0 — a amostra.** Rodar em **20 sessões** escolhidas a dedo (uma de cada
tipo: acionamento, dúvida de cobertura, cobrança, papo pessoal, grupo).
🔴 **O caso do papo pessoal é o controle:** ele TEM de ser recusado. Se passar,
a noite não começa.

**Passo 1 — ler as 20 cartas com os olhos.** Não a contagem: o texto. Uma carta
ruim publicada é lida por todas as corretoras.

**Passo 2 — a leva.** Subagentes em paralelo, cada um com um lote, teto por
rodada declarado. Cada carta nasce com: a sessão de origem, a corretora, a data
e a força da evidência.

**Passo 3 — a curadoria.** O que já existe: dedupe contra o acervo (`superseded`),
recusa por PII (`rejected_pii`), recusa absoluta (`rejected_absoluto`). Some-se
o filtro de valor novo.

**Passo 4 — publicar.** 🔴 **Hoje a publicação acontece sem aprovação humana**
(📊 8.916 cartas `published`). Para uma noite grande isso é muito poder sem
freio. **Recomendo um portão de aprovação por lote** — decisão do Founder.

**Passo 5 — o relatório.** Quantas nasceram, quantas foram recusadas e **por
quê**, com exemplos das recusadas. É o que prova que o filtro funcionou.

---

## 6. Depois da destilação: as condições gerais (SUSEP)

Palavras do Founder: *"É importante que tenhamos as condições gerais das
seguradoras dos últimos 12 meses ou até mais."*

📊 Estado hoje: `normative_documents` tem **8 ingeridos** (Bradesco, Mapfre),
**23 parados em `fetching`** e **4 `discovered`**. Os 23 pararam em **HTTP 402**
— crédito do Firecrawl esgotado ([D18](FOUNDER-DECISIONS.md)).

**Destrava com dinheiro, não com trabalho.** Um plano pago do Firecrawl (ou
outro extrator) e a fila anda.

**Minha recomendação de ordem:** conversas primeiro, condições gerais depois. As
conversas são material que **expira em outubro** e já está pago; as condições
gerais não expiram e esperam uma assinatura.

E uma observação sobre o "12 meses": condição geral muda com **circular da
SUSEP**, não com o calendário. O corte certo é *"a versão vigente de cada produto
+ as anteriores que ainda têm apólice viva"* — uma apólice de 2025 é regida pela
condição de 2025, e é sobre ela que o segurado vai perguntar.

---

## 7. O que NÃO fazer

1. **Rodar a leva grande antes da amostra de 20.** Custa dinheiro e envenena o RAG.
2. **Destilar antes de o dedupe estar provado.** Cartas em dobro de conversas em dobro.
3. **Publicar sem ler.** 9 mil cartas que ninguém viu são 9 mil apostas.
4. **Confundir o filtro de PII com o filtro de valor.** São perguntas diferentes.
5. **Deixar passar de outubro.** É a única coisa aqui com data de validade.
