# SPEC-089 · A RÉGUA NÃO SOBE QUANDO DEIXA DE MEDIR

> **O que ela entrega:** uma nota em que **não conseguir medir vale zero, não
> vale nada** — e itens que conseguem reprovar de verdade.
>
> **v1** · 26/08/2026 · commit base `0c59fe5` · repo `AutoBrokers-FIX`

---

## 🔴 A razão desta SPEC existir, em quatro linhas

📊 Medido em 26/08/2026, rodando a régua:

```
sem --com-espelho :  102/102 = 100,00%   AAA(102)    ← o comportamento PADRÃO
com  --com-espelho:  102/106 =  96,23%   AAA(106)
```

> **A rota tira nota MAIOR quando o instrumento falha.**

O item dos apelidos sai do denominador com o motivo `SEM_ESPELHO` — que quer
dizer **"não consegui alcançar o banco"**. 📊 E é o único `N/A` que a régua
produz na prática: **43 de 43 rotas.**

⚠️ **E o `--todas` é o comando sem a flag.** Ou seja: o caminho padrão da
ferramenta é o que infla.

🔴 **A proposta escreve a regra que isso viola** — §8.4: *"detector quebrado ≠
N/A; falha do instrumento não pode melhorar a rota"* — e **nunca liga a regra ao
`SEM_ESPELHO`.** A "lavagem de N/A" que o red team dela deve caçar **já está
ligada, por omissão, no caminho padrão.**

## 1.1 · 📊 E 40 dos 102 pontos não conseguem reprovar

```
itens distintos ............................. 19
🔴 itens que NUNCA reprovam nas 43 rotas .... 8      = 40 pontos
🔴 item que nunca CONTA (sempre N/A) ........ 1      = +4 pontos
```

Os oito: `B ≥85% determinístico` (+8) · `B notes que RECONTA` (+2) · `C âncora
sem *` (+3) · `C nenhuma constante decide` (+6) · `C tecla tem origem` (+6) · **e
o eixo E inteiro** (+15).

⚠️ **Dois deles têm causa nomeável:**

```
o corte de determinismo exige ≥85%
   📊 o MÍNIMO medido nas 43 rotas é 95,6%
   📊 e 42 das 43 estão em 100,0%
   → o corte está 10,6 pontos abaixo do pior aluno

o eixo E (15 pts) mede o REPOSITÓRIO, não a rota
   📊 a tupla de mutação é calculada UMA vez para as 73 (`medir_rota.py:469`)
   → 15 pontos idênticos em 43 rotas = 14,7% de cada nota sem separar nada
```

> **`CLAUDE.md` §9.3, aplicado à régua: um item que não tem como reprovar não
> mede nada.** Quarenta pontos de cada nota são decoração.

## 1.2 · 🔴 E ela não vê nada do que o produto passou a saber

📊 Zero ocorrências de `needs_human`, `work_steps`, clique humano ou religamento
nos **quatro** arquivos da régua (`rubrica.py`, `regua_motor.py`, `replay.py`,
`medir_rota.py`).

⚠️ **E não é omissão que um item novo conserta:** o corpus
(`backend/tests/corpus/telas_reais/*.jsonl`, 16 arquivos, 4.279 linhas, 195
sessões) **não tem campo `direction`** — só tem tela de seguradora. **Não existe
ali o turno do agente, nem o do atendente, nem o do segurado.**

📊 E o dado existe, do outro lado: `work_steps` tem `needs_human` 2 ·
`human_phase` 4 · `ura` 4.

## 1.3 · O que a proposta afirma e não reproduz

| a proposta diz | 📊 medido em 26/08 |
|---|---|
| o inventário mostra `102/106 → AAA(106)` | `--todas` de hoje: **`102/102 → AAA(102)`** |
| **19 rotas AAA** | **30** |
| máximo bruto **106** | 106 é a soma bruta; **o denominador aplicado é 102** em 33 rotas |
| eixo E = 9, e lista **seis hipóteses** para a causa | 📊 a causa é **uma linha**: o teste passa `mutacoes_ok=(3,3)` e o repo declara **12** |

---

## 0. O TESTE DO PRODUTO

> **Duas rotas: uma que o robô percorre sozinho até o fim, e outra em que o
> corredor trava e uma pessoa termina. A régua tem de dar notas DIFERENTES — e
> a que precisou de gente tem de tirar menos.**

⛔ **Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal.
⛔ NÃO mexer em variável de ambiente de produção.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NUNCA `git add -A` (P-247).
🔴 A RÉGUA MUTA `corridor_playbooks.py` PARA MEDIR.
   Tome a trava (`verificar_mutacoes.py:_tomar_a_trava`) e rode com a árvore
   EXCLUSIVA. É a P-261, e ela foi violada ontem por quem escreve isto.
⚠️ E no Windows a CLI quebra sem `PYTHONIOENCODING=utf-8`
   (`UnicodeEncodeError` cp1252, `medir_rota.py:488`).
```

---

# BLOCO A · 🔴 Não conseguir medir vale ZERO

## O problema

📊 `SEM_ESPELHO` sai do denominador, e a nota sobe de 96,23% para 100,00%.

## O conserto

**Três motivos de N/A, e só um deles é honesto:**

```
NÃO SE APLICA à rota          → sai do denominador       ✅ legítimo
não medi porque não quis      → sai do denominador       ✅ legítimo
🔴 não CONSEGUI medir          → FICA no denominador, valendo ZERO
```

⚠️ **`SEM_ESPELHO` é o terceiro.** Ele significa *"o banco não respondeu"* — e a
resposta certa a isso é **perder os pontos**, não ganhá-los de graça.

## 🔴 E a nota passa a carregar como foi tirada

```
AAA(102) sem espelho     ⛔ deixa de existir
AAA(106) com espelho     ✅ a única nota AAA possível
102/106 sem espelho      = 96,23%, e o motivo aparece do lado
```

> **Duas notas com o mesmo número e denominadores diferentes são duas coisas
> diferentes.** Hoje elas se parecem.

## O gate

```
① banco inalcançável → o item vale ZERO e a nota CAI
② 🔴 LINHA DE CONTROLE: banco alcançável → o item conta, e a nota é a mesma de hoje
③ item que NÃO SE APLICA à rota → continua saindo do denominador
④ a nota traz o denominador, e duas notas com denominadores diferentes
   nunca são comparadas como iguais
```

🔴 **A mutação:** faça o espelho falhar e ① tem de ficar **vermelho** se a nota
subir.

---

# BLOCO B · Os itens que não conseguem reprovar

## O problema

📊 8 de 19 itens nunca reprovaram em nenhuma das 43 rotas. **40 pontos de cada
nota.**

## O conserto — e a decisão é item a item, com o número na mão

```
o corte de determinismo (+8)     📊 exige ≥85%, o pior aluno tem 95,6%
                                 → SOBE para onde separe, ou o item SAI
o eixo E inteiro (+15)           📊 mede o REPOSITÓRIO, não a rota
                                 → SAI da nota da rota. Vira gate do repo.
os outros seis (+17)             → cada um: qual rota reprovaria? se nenhuma,
                                    ou o corte muda, ou o item sai
```

⚠️ **Tirar um item não é baixar a régua** — é parar de dar pontos por nada.
📊 Uma nota em que 40% é presença não distingue rota boa de rota ruim, **e é
exatamente por isso que 30 das 43 estão em AAA.**

## 🔴 O gate — e ele é o mais duro desta SPEC

```
① 🔴 CADA item restante reprova PELO MENOS UMA rota real das 73
   ⚠️ e o teste NOMEIA a rota. "Deve reprovar alguma" não conta.
② a distribuição das notas ABRE: hoje 📊 mediana 97,6 e 30 de 43 em AAA
③ 🔴 LINHA DE CONTROLE: uma rota que era AAA e continua perfeita
   permanece AAA — o objetivo é separar, não rebaixar todo mundo
```

---

# BLOCO C · 🔴 A régua passa a ver o travamento

## O problema

📊 A régua não sabe dizer se a rota travou, se uma mão humana terminou, nem se a
saudação saiu. **O corpus não tem `direction`** — só tela de seguradora.

## O conserto — o menor que responde a pergunta

⛔ **Não é reconstruir o corpus.** É um eixo novo que lê o **banco**, não o
corpus:

```
por rota, nos últimos N dias:
   quantas vezes travou              work_steps step_key='needs_human'
   quantas um HUMANO destravou       work_events travamento.assumido
   quantas o robô destravou sozinho  unblock_state='retomado_pelo_robo'
```

🔴 **E é o item que separa de verdade:** uma rota que só anda com gente **não é
AAA**, por mais bonito que seja o replay dela.

⚠️ **Enquanto o piloto não rodar, esse eixo mede ZERO em todas** — 📊 hoje há 2
`needs_human` no banco inteiro. **Ele nasce inerte e ganha poder na segunda-feira.**

> ⛔ **E inerte não pode virar N/A.** Rota sem travamento registrado **conta como
> "não travou"** — que é a nota boa. ⚠️ É o BLOCO A outra vez, e o executor tem
> de conferir que não repetiu o defeito que acabou de consertar.

## O gate

```
① rota com travamento registrado tira MENOS que rota sem
② 🔴 rota que só andou com humano NÃO é AAA
③ 🔴 rota sem nenhum registro conta como "não travou", NÃO como N/A
④ dois tenants: o travamento de A não conta na rota de B
```

---

# BLOCO D · As cinco da quarentena, pela causa

📊 `pytest tests/test_a_rubrica_e_honesta.py --runxfail` → **5 failed, 8 passed
em 8m03**.

⛔ **Nenhuma sai trocando o número esperado.** Cada uma diz o que era e o que é:

| a asserção | 📊 a causa medida |
|---|---|
| `assert 102 == 96` (`:72`) | é o **denominador**, não a nota. O enunciado do defeito estava errado |
| `assert 102 == (100-4)` (`:408`) | idem |
| `assert r.orfas_funcionais` (`:133`) | 📊 são **zero** — e o guarda **exige que o produto continue imperfeito** |
| eixo E = 9 | 📊 **uma linha**: o teste passa `mutacoes_ok=(3,3)`, o repo declara **12**, e `rubrica.py:1004` zera por divergência |

🔴 **A terceira é a mais interessante e a mais perigosa:** um teste que só passa
enquanto houver defeito. **Ele tem de virar o inverso** — *"se aparecer órfã, ela
é NOMEADA"* — e passar quando não houver nenhuma.

---

# BLOCO E · A prova

```
① os gates de A, B, C, D passam
② 🔴 as 5 da quarentena saem, e o `xfail(strict=True)` prova que saíram
③ a régua roda nas 73 e a distribuição ABRE
④ 🔴 rodado com árvore EXCLUSIVA — a régua muta o corredor (P-261)
⑤ a bateria inteira, com o número de rodadas do diário
```

⚠️ 📊 **Custo de medir:** uma rota = **4m14**. As 73 não cabem num laço ingênuo —
o executor mede uma amostra e diz **qual**.

---

## 3. 🔴 O QUE SAIU DA PROPOSTA

📊 2.250 linhas de SPEC para 2.700 de código medido.

| peça | por que saiu | **volta quando** |
|---|---|---|
| `RouteAssessment` ao lado de `Nota` | ⛔ duas classes de nota é remendo ao lado (`CLAUDE.md` §5) | ⛔ nunca. Estenda a `Nota` |
| G5 "contrato da ferramenta" | 📊 `acionamento_pelo_contrato.py` **já existe** e faz isso — e 📊 **43 de 43 acionam**: o portão bloqueia zero | quando bloquear alguma |
| G0–G6 como camada nova | a régua já tem patamar e itens | quando os itens do BLOCO B separarem |
| fingerprint + registry de selo | 💭 selo que morre com a rota é bom, e é para depois de a nota valer | o BLOCO B terminar |

---

## 4. O que fica pendente

```
P-089-01  📊 `regua_motor.eventos_observados()` SELECIONA `company_id` e NÃO
          FILTRA por ele — contra o comentário duas linhas acima. É leitura
          global por desenho (o Atlas é um só), mas não está registrado.
P-089-02  📊 a exclusão da Amandus é por UUID EM CÓDIGO, não por configuração.
P-089-03  📊 a CLI quebra no Windows sem `PYTHONIOENCODING=utf-8`.
P-089-04  📊 medir uma rota custa 4m14; as 73 custariam ~5h.
P-089-05  📊 30 rotas em SEM_CORPUS de 73 — a régua mede 43.
```

---

## 5. A ordem de execução

```
A  →  D  →  B  →  C  →  E
```

💭 **~6h.** O BLOCO B domina (decidir item a item, com medição por item).

🔴 **A antes de tudo:** enquanto "não consegui medir" valer nota, **toda
calibração do BLOCO B mede o instrumento quebrado.**
🔴 **D antes de B:** três das cinco asserções em quarentena são sobre os números
que o BLOCO B vai mudar. Consertar B primeiro faz a quarentena mentir duas vezes.
