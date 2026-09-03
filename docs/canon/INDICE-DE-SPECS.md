# ÍNDICE DE SPECS — a fila, em ordem, sem nada para trás

> **Uma folha. Toda SPEC do projeto, o estado dela, e qual é a próxima.**
> 🔴 **Este arquivo é a autoridade da ORDEM.** Se a pasta e ele discordarem,
> ele vence — e quem discordou conserta a pasta.
>
> 30/08/2026 · atualizado a cada conversão e a cada execução

---

## 🔴 03/09/2026 — o processo mudou: UM orquestrador, e a independência mora nos subagentes

```
🎯 Fable 5.1 orquestra: converte E executa, uma SPEC por vez, na ordem deste índice
🌐 PESQUISADOR (Opus)   reabre o research-pack → §7.3 da SPEC        (conversão)
🔨 AQUECIMENTO (Opus)   refuta a SPEC contra código e banco           (conversão)
🔧 BUILDER (Opus)       escreve, um por unidade                       (execução)
⚖️ PAINEL (Opus)        3–5 lentes cegas, sobre o CÓDIGO             (execução)
```

📊 Por quê: 133 URLs de pesquisa em 10 research-packs, **zero** em qualquer SPEC
convertida. E "ninguém audita a própria escrita" continua valendo — só que quem
audita agora é um subagente de contexto limpo, não um segundo chat.
Protocolo **v11**: [`PROTOCOLO-AUTOBROKERS-AAA.md`](PROTOCOLO-AUTOBROKERS-AAA.md) ·
pacotes em [`pacotes/`](pacotes/).

```
✅ SPEC-091  ABSORVIDA pela v11 do protocolo em 03/09/2026. O que sobrava dela era
   um bloco de guarda sobre os PACOTES — é o bloco [9] do
   `backend/tests/test_o_protocolo_tem_policia.py`. A Protocol Factory da proposta
   continua adiada com o mesmo gatilho (três protocolos escritos à mão).
✅ SPEC-088  REFEITA (v2, 7 referências externas reabertas) e EXECUTADA em 02–03/09/2026 sob a v11.
   Relatório: reports/SPEC-088-EXECUTION-REPORT.md. A 088-B (runtime de delegação) fica
   adiada com gatilho medido: agent_delegations = 0.
```

## ⛔ O PROCESSO ANTERIOR, em três caixas (histórico, até 02/09/2026)

```
①  A PROPOSTA                    você + GPT
    docs/canon/specs-propostas/          ← ela mora aqui, e só aqui

②  A CONVERSÃO                   CHAT CONVERSOR · usa o PROTOCOLO AAA v10
    audita · mede contra o CÓDIGO e o BANCO · corta o que não executa
    docs/canon/specs/SPEC-NNN-*.md       ← sai daqui pronta

③  A EXECUÇÃO                    CHAT EXECUTOR · uma a uma, EM ORDEM
    docs/canon/reports/SPEC-NNN-EXECUTION-REPORT.md
```

### 🔴 Por que DOIS chats, e não um

📊 **Medido:** o executor **derrubou 9 afirmações** das quatro SPECs que outro
escreveu — inclusive um orçamento de *"5 horas"* que eram **9m59**.

> **Se ele tivesse escrito as SPECs, teria derrubado zero.** Ninguém audita a
> própria escrita.

E o protocolo mede: o **juiz retomado** — o mesmo agente julgando de novo —
tirou **05/100** no placar de mecanismos. É o pior de todos.

### ⚠️ E os dois trabalham em LOTE

📊 O executor fez `087 → 090 → 086 → 089` **numa sessão só, 8h04, sem reaquecer
entre elas**. Um chat por SPEC joga fora esse ganho.

---

# 📋 A FILA — em ordem numérica

## ✅ FEITAS

| | o que é | quando |
|---|---|---|
| **081** | Raio-X Comercial e Radar por vendedor | 18/08 |
| **083** | A régua do corredor | 21/08 |
| **084** · **084.1** · **084.2** | A fábrica de rotas · O ensaio · O contrato | 22–24/08 |
| **085** | O destravamento não trava em silêncio | 25/08 |
| **086** | O atendimento termina, e o produto sabe | 26/08 |
| **087** | A tela que o corredor não conhece | 26/08 |
| **089** | A régua não sobe quando deixa de medir | 26/08 |
| **090** | O atendimento de ontem vira conserto de hoje | 26/08 |
| **092** | O formulário dentro do WhatsApp | 25/08 |
| **093** | O atendimento real liga e funciona | 25/08 |
| **088** | A Central de Agentes diz a verdade (v2, protocolo v11) | 03/09 |
| **093-B** | O sinistro deixa rastro (protocolo v11 · nível CRÍTICO · zero migration) | 03/09 |
| **094** | O Pulso 360 não pertence à InfoCap (v11.1→v11.2 · CRÍTICO · censo + CBIM + registry + canário vivo) | 03/09 |

## ⬜ OS BURACOS — e nenhum precisa de ação

```
079    nunca existiu
082    nunca existiu
```

⚠️ **Numeração não é contagem.** Um buraco não é trabalho perdido — é um número
que nunca foi usado. **Não invente SPEC para preencher.**

## ⚠️ A 080 — escrita, nunca executada, e ABSORVIDA

📊 `ESTADO-DAS-SPECS.md:51`: *"é a auto-atualização. Escrita, nunca executada.
**Vira a base da SPEC-087**"* — e a **087 foi executada em 26/08**.

> ✅ **A 080 está FECHADA por absorção.** O arquivo dela fica como histórico.
> ⛔ **Não executar.** Executá-la refaria o que a 087 já fez.

---

# 🔴 A FILA DE VERDADE — o que falta, em ordem

## ✅ LEVA 1 — CONVERTIDA em 02/09/2026. A sequência `081 → 093` está inteira.

| ordem | SPEC pronta, por caminho | 💭 execução |
|:---:|---|:---:|
| ✅ | [`SPEC-088 · A Central de Agentes diz a verdade`](specs/SPEC-088-a-central-de-agentes-para-de-mentir-de-verde.md) — EXECUTADA 03/09 · 📊 relógio 22:40→02:00 | feita |
| ✅ | [`SPEC-091`](specs/SPEC-091-o-pacote-carrega-o-que-a-secao-1-manda.md) — ABSORVIDA pela v11 do protocolo em 03/09 | feita |

🔴 **As duas entraram na fila adiadas com gatilho (nota 50 e 45), e a conversão
REMEDIU os dois gatilhos.** Nenhum disparou — e as duas SPECs dizem isso com
número, em vez de repetirem a proposta:

```
📊 088  o gatilho era "agentes ou auxiliares > ~20".  Hoje: 8 agentes
        (2 por corretora × 4) e 9 auxiliares instalados.  NÃO disparou.
        🔴 Mas a medição achou OUTRA coisa, e ela muda o produto:
        a Central dá VERDE quando o LAÇO roda, não quando o TRABALHO acontece.
        📊 `intelligence.garimpo`: 9 execuções `completed` em 3 dias,
           e `broker_insights` sem uma linha nova há 7 dias. Card verde.
        📊 E morto há 8 dias vira ⚪ AGUARDANDO, mais brando que 🔴 PARADO
           às 2h — o estado MELHORA conforme a morte envelhece.

📊 091  o gatilho era "TRÊS protocolos escritos à mão".  Hoje: UM.
        NÃO disparou, e a Factory inteira (2.815 linhas) fica adiada.
        🔴 Mas 4 de 10 pacotes de execução não carregam o protocolo — e o
        guarda criado em 02/09 (`9dddb7f`) confere o DOCUMENTO, não o PACOTE.
        Sobrou 1 bloco de ~1–2h, e a conta do §3 dele deu RISCO 1.
```

> ⚠️ **Adiada com data e número é diferente de esquecida.** O que saiu de cada
> proposta está na seção `O QUE SAIU` da SPEC correspondente, **com o gatilho
> medível que a faz voltar** (`CLAUDE.md` §11 — recorte registrado, nunca
> silencioso).

## LEVA 2 — as que já têm número livre

| ordem | vira | de qual proposta |
|:---:|---|---|
| 3º | **SPEC-093-B** | `7 - SPEC-093-claims-learning-shadow` |
| 4º | **SPEC-094** | `8 - SPEC-094-executive-intelligence-360` |
| 5º | **SPEC-095** | `9 - SPEC-095-artifact-delivery-hub` |
| 6º | **SPEC-096** | `10 - SPEC-096-chat-runtime-…` |

✅ **Estas mantêm o próprio número** — 094, 095 e 096 estão livres.

## LEVA 3+ — as que você ainda vai criar

`097` até `114`, na ordem em que forem chegando. ✅ **Todas mantêm o número da
proposta**, porque a partir da 094 não há mais colisão.

## 🔴 A ÚNICA COLISÃO — e ela fica no lugar dela

| proposta | problema | 🔴 vira |
|---|---|---|
| `7 - SPEC-093-claims-learning-shadow` | **093 já existe e foi executada** | **SPEC-093-B** |

🧑 **Decisão do Founder, 30/08:** *"se ela está no início da sequência, não quero
colocar para o final."*

✅ **E o projeto já tem o precedente:** `SPEC-084`, `084.1` e `084.2` — três SPECs
no mesmo número, executadas em ordem. **A letra é o desempate deste projeto, e
ela já funcionou três vezes.**

**A ordem de execução dela** fica onde o número manda: depois da `093` (feita) e
antes da `094`. ⚠️ Ou seja, **na LEVA 2, como primeira.**

---

# 🔴 A REGRA DA NUMERAÇÃO — para nunca mais colidir

```
o número da proposta está LIVRE   →  mantém           094 · 095 · 096 · 097+
o número está OCUPADO             →  ganha LETRA       093 → 093-B
                                      e fica na posição do número
```

⛔ **Nenhuma SPEC muda de número depois de convertida.** O de-para fica **aqui**,
para sempre.

⚠️ **E a letra não é "menos importante".** 📊 A `084.1` foi a SPEC que levou 19
corredores a AAA — a mais transformadora do bloco inteiro.

---

# ⚠️ QUANDO CONVERTER — e por que não tudo de uma vez

> 🔴 **A conversão MEDE contra o código.** Converter 20 propostas hoje e
> executá-las em três semanas produz SPECs com medição vencida — que é
> **exatamente o defeito das propostas atuais.**

📊 A proposta da 087 afirmava `structural escalated = 4`. No dia da conversão o
medido era **14 + 2**. **Números de 18/08 citados como se fossem de hoje.**

```
✅ converta 2 a 4  →  execute essas 2 a 4  →  repita
⛔ nunca converta o que não vai executar em seguida
```

---

# 📌 A PRÓXIMA COISA A FAZER

> ✅ **LEVA 1 fechada em 03/09/2026:** 088 executada (relatório em `reports/`), 091 absorvida pela v11.

> ✅ **093-B executada em 03/09/2026** (relatório em `reports/`, auditoria externa incluída). A **094 foi
> convertida no mesmo dia** — `specs/SPEC-094-o-pulso-360-nao-pertence-a-infocap.md` — e está em execução.

```
✅  SPEC-094 executada em 03/09 (nota 84). ⏸️ PROTOCOLO PAUSADO até a decisão do Founder sobre o ritmo (DECISAO-DO-RITMO-03-09-2026.md)
1º  SPEC-094.1 · A fábrica de relatórios (convertida; executa depois da decisão)
2º  SPEC-095  →  3º SPEC-096  →  4º SPEC-097 (proposta + research pack na pasta)  →  5º SPEC-098 (idem)  →  depois, o MASTERPLAN
    ⚠️ converta e execute em seguida, uma por vez. Número medido hoje vence número da proposta.
```

⚠️ **Antes de ligar o atendimento (terça, 08/09):** nada desta fila bloqueia o piloto. O que só o
Founder pode fazer está em `O-QUE-FALTA-PARA-LIGAR-O-ATENDIMENTO.md`.
