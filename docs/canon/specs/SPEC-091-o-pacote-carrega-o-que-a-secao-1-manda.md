# SPEC-091 · O PACOTE CARREGA O QUE A §1 MANDA — e alguém confere

> **O que ela entrega:** nenhum pacote de execução chega ao executor sem o
> protocolo dentro — e existe um teste que fica **vermelho** quando isso acontece.
> 📊 Hoje, **4 de 10** pacotes escritos à mão não o carregam.
>
> **v1** · 02/09/2026 · commit base `862dd1c` · repo `AutoBrokers-FIX`
> Proposta de origem: `specs-propostas/6 - SPEC-091-protocol-process-factory.md`

---

## 🔴 ANTES DE TUDO: a proposta original continua ADIADA, e agora com número

📊 A proposta pede uma **Protocol & Process Factory** — *"todo processo importante
vira um protocolo executável, versionado, portátil e ensinável a qualquer LLM"*.
**2.815 linhas · 📊=0 marcas · 💭=0 marcas** (`CLAUDE.md` §12.1).

**O gatilho escrito na auditoria de 26/08 foi:** *"volta quando existirem TRÊS
protocolos escritos à mão e o terceiro doer."*

### 📊 A remedição de hoje, 02/09/2026 — o gatilho NÃO disparou

```bash
# quantos documentos deste projeto se declaram PROTOCOLO?
for f in docs/canon/*.md; do head -1 "$f" | grep -qi "protocolo" && echo "$f"; done
```
```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md      ← o único
docs/canon/PROTOCOLO-AAA-EVIDENCIAS.md       ← o apêndice de evidências DELE
```

> 🔴 **Um protocolo. Não dois, não três.** ⛔ **Uma fábrica de protocolos antes do
> segundo protocolo existir é construir a fábrica antes do produto.**

### 📊 E o plano de produto que a proposta queria preparar JÁ EXISTE

A própria proposta declara (§0.1) que a autoridade de runtime continua sendo o
Skill Registry da SPEC-056. 📊 **Ele está construído e povoado:**

```sql
SELECT count(*) FROM skills;  -- → 20, todas is_active = true
-- e as 20 têm release e binding: nenhuma é casca
```

⚠️ **Então o que a 091 acrescentaria é o plano de ENGENHARIA** — como este
projeto constrói a si mesmo. ⛔ **Isso não muda um byte do que chega ao segurado,
à corretora ou ao banco** (protocolo §2), e o §9.1 é explícito: *"documentação que
ninguém precisa para executar"* é **não material**.

### 🔴 E o risco que a auditoria de 26/08 apontou continua de pé

> *"O valor do protocolo atual está no que ele **RECUSA** — o juiz retomado, o
> painel sobre documento, a lista que envelhece. Uma fábrica que gera protocolos
> a partir de template gera os que não recusam nada."*

⚠️ **Nada nas 2.815 linhas mede como se gera uma recusa.** Uma fábrica que
produzisse o `PROTOCOLO-AAA` teria produzido a §5.1 (*"o juiz julga código"*)? 📊
Aquela regra nasceu de uma medição — **1.008 linhas de conserto contra 610 de
documento** — não de um template.

---

## 🔴 MAS a remedição achou uma dor REAL, medida hoje, e ela é pequena

📊 **02/09/2026 — os 10 pacotes de execução e aquecimento do repositório:**

```bash
for f in docs/canon/PROMPT-DE-AQUECIMENTO-* docs/canon/PROMPT-DE-EXECUCAO-*; do
  printf "%-50s %s\n" "$(basename $f)" "$(grep -ci 'PROTOCOLO-AUTOBROKERS-AAA' $f)"
done
```

```
✅ CARREGAM (6)   AQUECIMENTO-DO-EXECUTOR · SPEC-085 · SPEC-092
                  SPEC-093 (.md) · SPEC-093 (.TXT) · EXECUCAO-SPEC-085

🔴 NÃO CARREGAM (4)
                  PROMPT-DE-EXECUCAO-087-090-086.md      ← 0 ocorrências
                  PROMPT-DE-EXECUCAO-087-090-086.TXT     ← 0
                  PROMPT-DE-EXECUCAO-DA-LEVA.md          ← 0
                  PROMPT-DE-AQUECIMENTO-BLOCO-0.TXT      ← 0
```

🔴 **E o custo dessas quatro está medido — pelo próprio protocolo, §0.1:**

```
📊 092 e 093       o prompt mandava LER o protocolo  →  o painel RODOU   2 de 2
📊 087·090·086·089 o prompt NÃO mandava              →  não rodou        0 de 4

COM PAINEL    47 achados · 22 defeitos de PRODUTO
SEM PAINEL    19 achados ·  0 defeitos de produto        3,7× menos
```

> ⚠️ **O arquivo `PROMPT-DE-EXECUCAO-087-090-086.md`, com zero ocorrências, é o
> artefato daquela perda — e continua no repositório, do jeito que estava.**

### 🔴 A v10 consertou a REGRA. E o guarda de hoje confere o DOCUMENTO, não o PACOTE

📊 Em 02/09 às 10:12, o commit `9dddb7f` criou
`backend/tests/test_o_protocolo_tem_policia.py` — 196 linhas, 17 asserções. **É um
bom guarda.** Mas os alvos dele, nas linhas 51–53, são três:

```python
PROTO    = docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md
CLAUDE   = CLAUDE.md
TEMPLATE = docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md
```

> 🔴 **Ele prova que a §1 do protocolo lista a si mesma. Não prova que o pacote
> que você COLA no executor carrega alguma coisa.** 📊 E 4 de 10 não carregam.

⚠️ **É o mesmo defeito da v9 com o alvo deslocado um passo:** a regra existe, o
texto está certo, e **nada confere o objeto real**. O protocolo §4 já escreveu
essa lição para migrations — *"o ledger MENTE; o VERIFY confere o OBJETO no
banco"*. Aqui o ledger é o protocolo, e o objeto é o pacote.

---

## 0. O TESTE DO PRODUTO — 🔴 e ele é INDIRETO, declarado, não escondido

> **A próxima SPEC é entregue com um pacote sem o protocolo. O painel não roda.
> Os 22 defeitos de produto que ele acharia — vazamento entre corretoras,
> resposta em dobro ao segurado, `RecursionError` derrubando o webhook — sobem.**

⚠️ **A cadeia até o segurado tem DOIS passos, e os dois estão medidos** (§0.1 do
protocolo). ⛔ **Não é um passo.** 🧑 Se o Founder achar que dois passos é longe
demais, **esta SPEC inteira vira pendência numa linha** — e a §3 abaixo diz por
que isso custaria quase nada.

---

## 1. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal.
⛔ ZERO código de produto. ZERO migration. ZERO variável de ambiente.
⛔ Só um arquivo de teste e os arquivos de PACOTE em docs/canon/.
⛔ NUNCA `git add -A` (P-247).
```

---

## 2. 🔴 A CONTA DO §3 — e ela é o argumento desta SPEC

```
ALCANCE ........... 0   um teste e arquivos .md. Ninguém vê hoje
REVERSIBILIDADE ... 0   revert e não sobra nada: sem tabela, sem estado
FREQUÊNCIA ........ 1   um pacote por SPEC — toda semana
                   ──
RISCO ............. 1
SUPERFÍCIE ........ 1   um comportamento, em lugares que EU SEI LISTAR
PISO .............. nenhum (§3.2, por efeito): não envia · sem migration ·
                    não toca auth nem `company_id` · não cruza corretora
TIME .............. builder + juiz          (§3.1, RISCO 0–1 × SUPERFÍCIE 1–2)
```

> 🔴 **Um degrau acima da célula "NINGUÉM — faz e pronto".** ⚠️ **E é essa a
> prova de que a proposta errou o tamanho:** o que sobra da 091, depois de medido,
> **quase não precisa de SPEC** — e a proposta pedia 2.815 linhas e uma fábrica.

---

# BLOCO ÚNICO · O guarda confere o PACOTE

## O conserto

⛔ **Não é um arquivo novo de teste.** 🔴 **É um bloco `[5]` dentro do
`test_o_protocolo_tem_policia.py` que já existe** — porque um segundo guarda do
protocolo, num segundo arquivo, é a lista dupla que a SPEC-088 §1.5 mediu
envelhecendo em silêncio.

```
alvo:   docs/canon/PROMPT-DE-EXECUCAO-*   e   docs/canon/PROMPT-DE-AQUECIMENTO-*
regra:  todo pacote cita `PROTOCOLO-AUTOBROKERS-AAA` E o EXECUTION CARD
```

🔴 **E a regra tem DUAS metades. A conversão contou uma. As duas, medidas
em 02/09 com `grep -c` nos 10 arquivos:**

```
PROTOCOLO ......  4 de 10 não citam
EXECUTION CARD .  9 de 10 não citam    🔴 nunca foi contado
```

⚠️ **E as duas metades são quase anticorrelacionadas:** o único arquivo que
carrega o EXECUTION CARD (`PROMPT-DE-EXECUCAO-DA-LEVA.md`, 3×) **é um dos quatro
que não carrega o protocolo.**

> 🔴 **Por isso o conserto é de 10 arquivos, não de 4.** Consertar só os 4 e
> ligar o guarda deixaria **nove reprovando** — e o executor cairia numa de duas:
> estourar a faixa editando o que ninguém planejou, ou **derrubar em silêncio a
> cláusula do card**, que é o defeito que esta SPEC existe para consertar.

**E os 10 pacotes são consertados** — a linha do protocolo entra nos 4, a do
EXECUTION CARD nos 9. ⚠️ **A faixa sobe de 1–2h para 2–3h por causa disto**, e
a §9.2 manda declarar a mudança em vez de estourar em silêncio. ⚠️ 🔴 **Consertar sem o guarda seria inútil:** o defeito não foi falta de
texto, foi falta de portão. É o que o commit `9dddb7f` escreveu sobre si mesmo:
*"escrever pela quarta vez não faria diferença"*.

## O gate

```
① 🔴 os 10 pacotes de hoje passam — os 4 consertados junto
② 🔴 UM PACOTE NOVO sem a linha do protocolo → VERMELHO
   ⚠️ é a asserção que existe; sem ela isto é um `grep` decorativo
③ 🔴 LINHA DE CONTROLE: um pacote COM a linha → VERDE
   ⚠️ sem ela, um guarda que reprova tudo passaria em ②
④ o guarda encontra pacote por PADRÃO DE NOME, nunca por lista fixa
   🔴 um `PROMPT-DE-EXECUCAO-097.md` criado amanhã já nasce coberto
⑤ as 17 asserções que já existem continuam verdes
⑥ `.md` e `.TXT` — 📊 os dois formatos existem no repositório hoje
   ⚠️ **e a comparação é SEM CAIXA:** 📊 `PROMPT-DE-AQUECIMENTO-SPEC-085.MD`
   tem extensão maiúscula, e um `glob('*.md')` acha 7 no Windows e 6 no Linux
⑦ 🔴 **nenhum pacote manda "leia o protocolo INTEIRO".**
   📊 O protocolo tem **919 linhas**, e a §1 manda carregar §0, §1, §2, §3 e §5.
   📊 Hoje **3 dos 6 pacotes conformes dizem "INTEIRO"** — e um guarda que
   só faz `grep` da string **carimbaria os três como aprovados**, cimentando a
   leitura mais pesada exatamente na seção que É a dieta.
   ⚠️ **O gate que só conta a presença da string piora a dieta enquanto
   conserta o portao.** Este é o gate que impede isso
```

🔴 **A mutação obrigatória, e são duas — a segunda é a que quase todo mundo
esquece:**

```
1. tire a linha do protocolo de UM pacote  →  ② tem de ficar VERMELHO
2. 🔴 **crie** `PROMPT-DE-EXECUCAO-097.md` — um nome que NÃO existe hoje,
   DENTRO do padrão  →  o guarda tem de achá-lo sem ninguém listá-lo
   ⛔ um guarda que só acha o que já conhece guarda o passado
3. 🔴 **LINHA DE CONTROLE DO ALCANCE:** `PROMPT-COBRADOR.TXT` — que está
   FORA do padrão  →  o guarda **NÃO** pode reclamar dele
   📊 Existem **10 arquivos `PROMPT*` fora de `PROMPT-DE-*`**, e **9 têm zero
   citações**. Um guarda alargado demais **nasce vermelho em 9 arquivos que
   nem são pacotes de execução** — e guarda que acusa inocente ensina a
   ignorá-lo

⚠️ **A mutação 2 dizia o contrário disto até 02/09** (*"renomeie para um nome
FORA do padrão → tem de continuar achando"*) — e **contradizia o próprio gate
④**, que exige casamento por padrão. Um casador por padrão não pode, por
construção, achar o que está fora dele.
```

⛔ Restaurar **por cópia**, nunca `git checkout` (protocolo §10 · P-231).

💭 **~1–2h.** ⚠️ **E se passar de 2h, pare e leia a §9.2:** *"por que
continuar?"*. 🔴 Esta SPEC não vale uma terceira hora — o que ela fecha vale
uma, e o §9.1 diz que a execução não ganha crédito por lapidação.

---

## 3. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

📊 Saíram **2.815 de 2.815 linhas.** O que ficou não é um recorte dela: é a única
dor que a medição de hoje encontrou.

| peça | 📊 medido em 02/09 | **volta quando** |
|---|---|---|
| Protocol Factory · authoring · validação | **1** protocolo escrito à mão | existirem **3**, e o terceiro doer |
| Protocol Package (`SKILL.md` + `protocol.yaml` + `references/` + `scripts/`) | `skills` = **20**, todas com release e binding — a SPEC-056 já é isso | um processo do plano de ENGENHARIA precisar rodar dentro do produto |
| Immutable Release · content hash · progressive disclosure | ✅ **já existe** no Skill Registry | ⛔ nunca: refazer é motor paralelo (`CLAUDE.md` §5) |
| Clean-room execution de protocolo | — | 🔴 depois de existirem 3 protocolos |
| Protocol Execution Record → sinal de aprendizagem (090) → Dreams (106) | 📊 a 106 **não existe**; a 090 foi executada em 26/08 | a 106 existir |
| exportar protocolo para Codex / Copilot / outro harness | 💭 nenhum outro harness em uso hoje | 🧑 o Founder adotar um segundo harness |

> ⚠️ **Nada foi julgado ruim. Foi julgado cedo** — e cada linha tem gatilho
> medível. 🔴 **`CLAUDE.md` §11: isto é proposta de recorte REGISTRADA, nunca
> corte silencioso.** O Founder derruba qualquer linha desta tabela.

---

## 4. A REFERÊNCIA — §7.1, por caminho

| dimensão | referência | como comparar |
|---|---|---|
| **um guarda serve?** | `backend/tests/test_o_protocolo_tem_policia.py` | 📊 **205 linhas** · 17 asserções · a mutação escrita no commit `9dddb7f`. 🔴 **O bloco `[7]` entra NELE** — ⚠️ `bloco_1` a `bloco_5` já existem e o `bloco_6_CONTROLE` **fica por último** — o juiz abre o arquivo e vê se o novo bloco tem a mesma dureza dos quatro |
| **linha de controle** | `CLAUDE.md` §9.3 | prove que o guarda **CONSEGUE** ficar vermelho |
| **o número é medido?** | `CLAUDE.md` §12.1 | 📊 tem consulta e data · 💭 nunca é citável |

---

## 5. O que fica pendente

```
P-091-01  📊 6 pacotes de aquecimento (984 linhas) escrevem o MESMO processo
          da §5.2 à mão. Não dói ainda — 💭 dói quando divergirem em CONTEÚDO,
          não em volume. 🔴 O sinal de que doeu: dois pacotes com regras
          DIFERENTES para o mesmo passo. Hoje não há nenhum.
P-091-02  ⚠️ `PROMPT-DE-EXECUCAO-087-090-086` e `PROMPT-DE-AQUECIMENTO-SPEC-093`
          existem em `.md` E `.TXT`. 📊 Duplicata de formato, com conteúdo que
          pode divergir. O gate ⑥ cobre os dois; ⛔ não resolve a duplicata.
P-091-03  🔴 `PROMPT-DO-CHAT-CONVERSOR.md` foi APAGADO e virou `.TXT`
          (`git status`: ` D `). O pacote do conversor está fora do padrão
          `PROMPT-DE-*` e por isso fora do gate ④ como escrito.
          🔎 O executor decide: amplia o padrão, ou declara por quê não.
```

---

## 6. 🧑 A CAIXA DO FOUNDER

```
F-091-01  A proposta original continua ADIADA, com gatilho medido:
          TRÊS protocolos escritos à mão, e o terceiro doer. 📊 Hoje: um.
          ⛔ Não bloqueia nada. O número volta a ser medido na próxima leva.

F-091-02  🔴 Esta SPEC passa no teste do produto por uma cadeia de DOIS passos.
          Se o senhor achar longe demais, ela vira pendência numa linha e
          nada se perde — 📊 a conta do §3 deu RISCO 1 / SUPERFÍCIE 1, um
          degrau acima de "faz e pronto".
          ⚠️ O que se perde é o portão: 4 de 10 pacotes hoje não carregam o
          protocolo, e o custo medido disso foi 3,7× menos defeito achado.
```
