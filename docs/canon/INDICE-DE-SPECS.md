# ÍNDICE DE SPECS — a fila, em ordem, sem nada para trás

> **Uma folha. Toda SPEC do projeto, o estado dela, e qual é a próxima.**
> 🔴 **Este arquivo é a autoridade da ORDEM.** Se a pasta e ele discordarem,
> ele vence — e quem discordou conserta a pasta.
>
> 30/08/2026 · atualizado a cada conversão e a cada execução

---

## ⛔ O PROCESSO, em três caixas

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

## LEVA 1 — fechar a sequência

| ordem | vira | de qual proposta | 💭 |
|:---:|---|---|:---:|
| 1º | **SPEC-088** | `4 - SPEC-088-central-de-agentes-…` | conversão ~1h |
| 2º | **SPEC-091** | `6 - SPEC-091-protocol-process-factory` | conversão ~1h |

🔴 **Estas duas vêm primeiro porque são os ÚNICOS buracos na sequência.**
Depois delas, `081` a `093` fica inteira, sem falha.

⚠️ **E as duas foram auditadas e adiadas com gatilho** (nota **50** e **45**).
**Isso não as tira da fila** — significa que a conversão precisa **primeiro
reconferir se o gatilho já disparou**, e o resultado honesto pode ser
*"continua adiada, e aqui está a medição de hoje"*. 🔴 **Adiada com data e
motivo é diferente de esquecida.**

## LEVA 2 — as que já têm número livre

| ordem | vira | de qual proposta |
|:---:|---|---|
| 3º | **SPEC-094** | `8 - SPEC-094-executive-intelligence-360` |
| 4º | **SPEC-095** | `9 - SPEC-095-artifact-delivery-hub` |
| 5º | **SPEC-096** | `10 - SPEC-096-chat-runtime-…` |

✅ **Estas mantêm o próprio número** — 094, 095 e 096 estão livres.

## LEVA 3+ — as que você ainda vai criar

`097` até `114`, na ordem em que forem chegando. ✅ **Todas mantêm o número da
proposta**, porque a partir da 094 não há mais colisão.

## 🔴 A ÚNICA ÓRFÃ — e ela vai para o fim

| proposta | problema | vira |
|---|---|---|
| `7 - SPEC-093-claims-learning-shadow` | 🔴 **093 já existe e foi executada** | **SPEC-115** |

**Por que o fim, e não um número no meio:** ela é *shadow mode* — observa
sinistro sem agir. 📊 **Ela melhora com mais dado**, e hoje há **4 acionamentos**
na história do produto. **Colocá-la por último é a ordem tecnicamente certa, não
só a numericamente conveniente.**

---

# 🔴 A REGRA DA NUMERAÇÃO — para nunca mais colidir

```
o número da proposta está LIVRE   →  mantém
o número está OCUPADO             →  vai para o FIM da fila, e o de-para
                                      é registrado nesta folha
```

⛔ **Nenhuma SPEC muda de número depois de convertida.** Se a proposta tinha
outro número, o de-para fica **aqui**, para sempre.

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

```
🔴 CONVERTER a SPEC-088 e a SPEC-091      chat CONVERSOR · ~2h
   depois EXECUTAR as duas                chat EXECUTOR
   depois converter 094, 095, 096         e assim por diante
```

⚠️ **E antes de tudo isso:** o piloto com a Regina e a Saionara está esperando
elas voltarem do treinamento. **Ele não depende de SPEC nenhuma desta fila.**
