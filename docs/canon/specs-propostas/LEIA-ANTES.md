# ⚠️ Propostas — todas passaram pelo protocolo

**26/08/2026.** As seis foram avaliadas com o `PROTOCOLO-AUTOBROKERS-AAA` em
MODO INVESTIGAÇÃO, contra o **código e o banco** — não por leitura.

> 🔴 **Quatro viraram SPEC de verdade, em `docs/canon/specs/`. Duas ficaram, com
> gatilho escrito.**

---

## ✅ AS QUATRO QUE VIRARAM SPEC

| proposta | nota | virou | 💭 |
|---|:---:|---|:---:|
| **087** route self-healing | 58 | **`SPEC-087 · A tela que o corredor não conhece`** | ~5h |
| **086** continuidade / posse | 62 · 68 | **`SPEC-086 · O atendimento termina e o produto sabe`** | ~3h |
| **089** a régua AAA | 68 | **`SPEC-089 · A régua não sobe quando deixa de medir`** | ~6h |
| **090** fábrica de inteligência | 58 | **`SPEC-090 · O atendimento de ontem vira conserto de hoje`** | ~4h |

### 🔴 O que cada medição achou, e mudou a SPEC inteira

```
087   📊 35,6% das telas reais que a seguradora manda, o corredor NÃO CONHECE
      (269 de 755, e 66 delas são MENU). E o detector de hoje vê 6% disso.
      🔴 O Bloco A da proposta desarma uma arma DESCARREGADA: `simulate()`
         levanta KeyError em 10 de 10 mapas, por uma chave errada.

086   📊 ZERO conversas marcadas como resolvidas, em 671. O produto não sabe
      distinguir "acabou" de "o cliente foi embora". E 5 `work_runs` presos
      em `queued`, o mais velho há 28 dias.
      🔴 Mais da metade da proposta era trava de posse, que o Founder cortou.

089   📊 A régua SOBE de nota quando deixa de medir: 100,00% sem espelho contra
      96,23% com. E 40 dos 102 pontos vêm de itens que NUNCA reprovam.

090   📊 As três fontes de dado NÃO SE JUNTAM: 152.300 transcripts com
      `session_id` que casam com ZERO conversas. E não existe porta para a
      anotação da Regina e da Saionara entrar no produto.
```

⚠️ **E as quatro tinham o mesmo defeito de forma:** 📊 **zero marcas 📊/💭** em
2.707 · 2.844 · 2.250 · e as linhas da 090. `CLAUDE.md` §12.1 — número sem marca,
em documento novo, é defeito de revisão.

---

## ⏸️ AS DUAS QUE FICARAM — com gatilho, não com "depois"

### **088** · A Central de Agentes vira uma organização operacional — **nota 50**

📊 3.718 linhas · zero marcas · grupos, papéis, contratos de delegação,
especialistas, juízes e execução governada.

🔴 **Ela responde uma pergunta de arquitetura que o Founder não fez.** A queixa
dele, registrada no `RASCUNHO-SPECS-FUTURAS.md:195`, foi:

> *"Está muito confuso para mim."*

⚠️ **Isso é navegação, não ontologia.** 📊 Existem **8 agentes** (4 de
atendimento + 4 core) e 12 tabelas de auxiliar/rotina. **Agrupar 8 coisas em
telas não precisa de contratos de delegação nem de juízes.**

**Volta quando:** o número de agentes ou auxiliares passar de ~20, **ou** o
Founder disser que a confusão continua depois de um agrupamento simples.

💭 **O que resolveria a queixa dele hoje:** a mesma coisa que a SPEC-093 fez com
os corredores — agrupar por propósito, com um resumo por grupo. **~2h**, e não
precisa de SPEC.

### **091** · Protocol & Process Factory — **nota 45**

📊 2.815 linhas · zero marcas · *"todo processo importante vira um protocolo
executável, versionado, portátil e ensinável a qualquer LLM"*.

🔴 **A ideia está certa e a hora está errada.** 📊 Existe **um** protocolo neste
projeto — o `PROTOCOLO-AUTOBROKERS-AAA.md` — e ele foi construído por **medição
ao longo de dias**, com o placar de mecanismos, os erros registrados e as regras
que custaram um dia cada.

> ⛔ **Uma fábrica de protocolos antes do segundo protocolo existir é construir a
> fábrica antes do produto.**

⚠️ **E há um risco concreto:** o valor do protocolo atual está no que ele
**recusa** — o juiz retomado, o painel sobre documento, a lista que envelhece.
Uma fábrica que gera protocolos a partir de template **gera os que não recusam
nada**.

**Volta quando:** existirem **três** protocolos escritos à mão e o terceiro doer.
🔴 **A dor é o requisito, e ela ainda não veio.**

---

## 📋 A ORDEM DE EXECUÇÃO

```
087  →  090  →  086  →  089
```

`docs/canon/PROMPT-DE-EXECUCAO-087-090-086.md` — pronto para colar.

🔴 **E antes de tudo:** `docs/canon/O-QUE-FALTA-PARA-LIGAR-O-ATENDIMENTO.md`,
que é a folha do que só o Founder pode fazer.
