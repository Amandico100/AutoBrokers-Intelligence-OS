# Relatório de execução — SPEC-089: a régua não sobe quando deixa de medir

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-089-a-regua-nao-sobe-quando-deixa-de-medir.md` (v1)
**Branch:** `feat/spec089-a-regua-nao-sobe-quando-deixa-de-medir`
**Executor:** Opus 5 (1M) · 26/08/2026
**Commit inicial:** `73e3e3b` · **Commit final:** `d696e5b` + este relatório
**Estado final:** CONCLUÍDA

---

## 🧑 PARA O FOUNDER — uma página

### O que muda

A régua deixa de dar nota melhor para quem mede menos, e os pontos que ela dá
passam a separar rota boa de rota ruim.

### 🔴 Cinco coisas que você precisa saber

**1. 📊 27 de 43 rotas tiravam nota MAIOR quando o instrumento não media.**

```
sem `--com-espelho` .... 30 AAA · mediana 97,8% · 17 rotas em 100,0%
com `--com-espelho` .... 20 AAA · mediana 94,3% ·  9 rotas em 100,0%
```

**Dez rotas eram AAA só por isso.** E o caminho que inflava era o **padrão** da
ferramenta — `--todas` sem a flag. `AAA(102)` deixou de existir: **a única AAA
possível é a que mediu.**

**2. 📊 44 dos 106 pontos — 41,5% de cada nota — eram PRESENÇA, não qualidade.**

Nove itens nunca reprovaram nenhuma das 43 rotas. Oito deles têm a mesma forma:
conferem que **uma má prática está ausente**. Dar ponto por não ter defeito é
dar ponto por nada — e 43 de 43 ganhavam idêntico.

🔴 Eles viraram **portão**: continuam guardando, param de inflar, e uma rota que
abrir qualquer um **não chega a AAA**.

**3. 🔴 A régua passou a ver o travamento — e já reprova uma rota hoje.**

📊 `allianz/residencial/eletricista` travou (os 2 `needs_human` do banco são
dela) e perde 6 pontos. `allianz/auto/guincho` não travou e faz 76/76 AAA.

> **É o TESTE DO PRODUTO da SPEC cumprido HOJE, não na segunda-feira.**

**4. ⚠️ A SPEC estava errada em quatro afirmações, e uma delas orçava 5 horas.**

| a SPEC dizia | 📊 eu medi |
|---|---|
| *"as 73 custariam ~5h; meça uma amostra"* | 🔴 **9m59.** O custo é FIXO, não por rota |
| *"o eixo E = 9 tem seis hipóteses"* | 🔴 **uma linha:** o teste passava `(3,3)` e o repo declara 12 |
| *"8 itens não reprovam (40 pts)"* | **9 itens, 44 pts** |
| `work_events travamento.assumido` | 🔴 **não existe** — nenhum evento `travamento.*` no banco |

**5. ✅ E a quarentena esvaziou — nenhuma saiu trocando o número esperado.**

📊 `44 xfailed` → **`39 xfailed`** na bateria. As cinco saíram pela causa.

---

## 0. Declaração de integridade

- [x] 🔴 **Árvore EXCLUSIVA em toda medição** (P-261) — a régua muta
      `corridor_playbooks.py` para se medir.
- [x] Nenhum motor paralelo. O eixo F entrou na `Nota` que já existe; o leitor
      entrou no `regua_motor` que já lê o banco, com a **exclusão nomeada da
      Amandus** herdada.
- [x] ⛔ Nenhuma migration — esta SPEC não toca no banco.
- [x] ⛔ **Nenhuma mensagem saiu** · 📊 `platform_sends` 24h: **0**.
- [x] ⛔ **Nenhum agente ligado** · 📊 `attendance` com `is_active`: **0 de 4**.
- [x] ⛔ `git add -A` **não foi usado** (P-247).
- [x] ⚠️ `PYTHONIOENCODING=utf-8` em toda chamada da CLI (P-089-03).

---

## 1. BLOCO 0 — a medição refeita, as 73 rotas, os dois modos

| a SPEC afirma | 📊 medido em 26/08 | |
|---|---|---|
| `sem: 102/102 = 100,00% AAA(102)` | **exato** (allianz/auto/bateria) | ✅ |
| `com: 102/106 = 96,23%` | **exato** | ✅ |
| 43 rotas medidas de 73 | **43 de 73** | ✅ |
| 30 SEM_CORPUS | **30** | ✅ |
| 30 rotas AAA | **30** (sem espelho) | ✅ |
| mediana 97,6 | **97,8** | ~ |
| 19 itens distintos | **19** | ✅ |
| 8 itens que nunca reprovam = 40 pts | 🔴 **9 = 44 pts** | ✗ |
| *"as 73 custariam ~5h"* | 🔴 **9m59** | ✗ |
| `travamento.assumido` | 🔴 **não existe** | ✗ |
| `retomado_pelo_robo` | 🔴 **zero linhas** | ✗ |
| `work_steps needs_human` = 2 | **2** | ✅ |

🔴 **E o número que a SPEC não tem, e que é o mais forte:**

```
27 de 43 rotas tiram nota MAIOR quando o item não é medido.
DEZ delas eram AAA só por isso.
```

---

## 2. O que cada bloco entregou

### BLOCO A — não conseguir medir vale ZERO · `7f785c4`

`SEM_ESPELHO` deixou de sair do denominador. ⛔ **`AAA(102)` deixou de existir.**

⚠️ **E o diagnóstico da SPEC estava um passo ao lado** — o que dispara
`SEM_ESPELHO` é a **ausência da flag**, não uma falha do banco (essa já era um
erro de saída, `medir_rota.py:461`). **A conclusão dela continua certa**: a nota
subia por medir menos, e isso não podia continuar.

🔴 **E a régua já conhecia a regra, num lugar só.** O item da mutação (eixo E)
diz, quando não consegue ler o `MUTACOES` do repo: *"zero medido nao e zero nao
medido"* — e vale 0 **dentro** do denominador. Agora os dois dizem a mesma coisa.

### BLOCO D — as cinco da quarentena, pela causa · `7f785c4`

⛔ **Nenhuma saiu trocando um número esperado por outro.**

| a assertion | 📊 a causa |
|---|---|
| `denominador == 96` | **102 nunca foi a NOTA** — é o DENOMINADOR. O enunciado do P-226 estava errado |
| `orfas_funcionais` | 🔴 **exigia que o produto continuasse imperfeito.** Virou o inverso: *"se existir, é NOMEADA"* |
| `not guardado_sub` | 📊 o subserviço **ganhou** regra própria. A precondição venceu, e nunca foi necessária |
| eixo E `== 15` | 📊 **uma linha:** `(3,3)` contra 12 declaradas. **A régua estava CERTA** |
| `item excluido` | 🔴 o BLOCO A **desta SPEC** o quebrou, e ele estava certo. A lição migrou |

### BLOCO B — os itens que não conseguem reprovar · `0a6d6f4`

📊 **9 itens · 44 pontos · 41,5% de cada nota.** Oito viraram portão; o nono
(`>=85% determinístico`) teve o corte subido para **100%** e passou a reprovar
uma rota nomeável.

📊 A distribuição do determinismo mostra que **não era o corte que estava
frouxo — era a população que não varia**: mínimo 95,6%, 42 de 43 em 100,0%.
Qualquer corte entre 96% e 100% reprova exatamente uma.

### BLOCO C — a régua passa a ver o travamento · `d696e5b`

O eixo **F**, lendo o banco:

```
a rota anda sozinha .................... 6 pontos (placar)
🔴 a rota nao depende de gente ......... 4 pontos (PORTÃO)
```

⛔ **E a trava que a SPEC manda conferir** — *"o executor tem de conferir que
não repetiu o defeito que acabou de consertar"*. **Três** estados, não dois:

```
travamentos is None  →  🔴 NÃO MEDI          →  ZERO, dentro do denominador
travamentos == {}    →  ✅ medi, nada travou →  CHEIO
rota fora do mapa    →  ✅ medi, nada travou →  CHEIO
```

Há guarda para isso **e um CONTROLE** que prova que os dois estados conseguem
dar notas diferentes.

---

## 3. Os três gates do BLOCO B, medidos com o eixo F dentro

### 🔴 ① Cada item do placar reprova ao menos UMA rota — **NOMEADA**

```
20  zero orfas funcionais ................ hdi/residencial/eletricista
12  a ROTA percorrida ate o fim .......... allianz/residencial/desentupimento
 8  100% deterministico .................. hdi/residencial/eletricista
 8  o freio casa >=1 tela REAL ........... allianz/residencial/desentupimento
 6  a rota anda sozinha .................. allianz/residencial/eletricista
 5  protocolo + dia + periodo ............ allianz/residencial/desentupimento
 4  apelidos do jeito que o cliente fala .. alfa/auto/pneu
 3  o handoff casa >=1 tela REAL ......... allianz/residencial/ar_condicionado
 3  expectativa_do_desfecho existe ....... porto/residencial/eletrodomesticos
 3  regras_para_o_cliente casam o corpus .. porto/residencial/eletrodomesticos
 2  >=2 sessoes distintas ................ alfa/auto/pneu
 2  a mais recente tem <180 dias ......... allianz/residencial/consulta_veterinaria

=> itens que NÃO reprovam ninguém: NENHUM ✅
```

### ② A distribuição ABRE

```
antes    AAA 20 · quase 13 · parcial  9 · esqueleto 1              amplitude 46,2
depois   AAA 12 · quase 18 · parcial 12 · esqueleto 1              amplitude 69,7
```

### 🔴 ③ As rotas perfeitas continuam AAA — separar não é rebaixar todo mundo

```
alfa/auto/guincho · allianz/auto/guincho · allianz/residencial/encanador
azul/auto/guincho · hdi/auto/guincho · porto/auto/guincho
yelum/auto/guincho · yelum/residencial/encanador     →  76/76 AAA(76)
yelum/auto/socorro_mecanico                          →  58/58 AAA(58)
```

⚠️ **E SEM espelho nenhuma delas é AAA** — o BLOCO A funcionando. **Os dois
blocos se costuram: o topo da régua exige medir.**

---

## 4. Testes — saída real

```
test_a_rubrica_e_honesta.py        13 passed   (era 5 failed, 8 passed)
test_a_regua_ve_o_travamento.py    15 passed   (novo)
                                   ──────────
                                   28 passed em 581,75 s
```

### 🔴 A quarentena esvaziou, e a bateria prova

```
antes:  44 xfailed
depois: 39 xfailed
```

⚠️ **O `xfail(strict=True)` é o que dá valor a esse número:** com ele, uma das
cinco que voltasse a passar **quebraria a suíte**. As cinco passam, e a marca
fica declarada e vazia.

### 📊 A BATERIA INTEIRA

```
915 passed · 2 failed · 39 xfailed · 1 xpassed   em 957,79 s (15:57)
```

⚠️ **As 2 falhas não são desta SPEC:**

```
test_a_arvore_ficou_limpa_no_fim   o vazamento de mutação da P-246
                                   (agora em `higiene_do_corpus.py`)
test_a_politica_de_autorizacao     🔴 o node CRASHANDO, não um teste reprovando:
                                   exit 3221226505 (STATUS_STACK_BUFFER_OVERRUN)
                                   Assertion failed: !(handle->flags &
                                   UV_HANDLE_CLOSING), src\win\async.c:76
```

---

## 5. 🔴 Os defeitos — e um foi meu, pego pelo guarda

**`Nota.fora` passou a contar PORTÃO como *"excluído por um motivo"*.**

O laço era `if not i.conta`, e `conta` passou a devolver `False` também para os
portões. Resultado: `fora` virou `{None: 36, "SEM_FABRICA": 7}` — **uma chave
`None`** que não é motivo de nada, somando 36 pontos numa tabela que quem lê
interpreta como *"itens que não se aplicam a esta rota"*.

> ⛔ **Sair do denominador e ser portão são coisas diferentes.**

E o marco do denominador mudou **três vezes** nesta SPEC — cada uma com a causa
escrita ao lado, que é o que o próprio teste passou a exigir:

```
102  →  106   BLOCO A: `SEM_ESPELHO` parou de sair
106  →   70   BLOCO B: 36 pontos viraram PORTÃO
 70  →   76   BLOCO C: o eixo F entrou com 6 de placar
```

⚠️ E ganhou uma soma que fecha — `placar + portões + fora == 116` — **senão um
item SUMIU** em vez de ter sido movido.

---

## 6. Pendências abertas

`P-089-A` 🔴 a régua ainda não vê o **corpo** do atendimento (o corpus não tem
`direction`) · `P-089-B` o eixo F cobre 4 acionamentos, não 43 rotas — destrava
sozinha na segunda · `P-089-C` o rótulo `>=85%` sobrevive em relatórios antigos ·
`P-089-D` 📊 a P-089-04 errou por 30× · `P-089-E` `travamentos_por_rota` lê 2.000
sem paginar, e o teto real do PostgREST é 1.000.

E as que a SPEC já listava (`P-089-01`, `02`, `03`, `05`) continuam de pé.

---

## 7. O que saiu, e por quê

⛔ **Nada foi cortado do escopo.** As quatro peças que a SPEC v1 já tinha tirado
da proposta (`RouteAssessment`, G5, G0–G6, fingerprint de selo) continuam fora,
com o gatilho de cada uma escrito lá.

⚠️ **E uma coisa que a SPEC pedia foi feita de outro jeito:** a §E manda *"medir
uma amostra e dizer qual"*. 📊 Medi **as 73**, quatro vezes, porque o custo real
é 9m59 e não 5h. **Dizer "medi uma amostra de 10" seria medir menos por causa de
um número errado** — que é literalmente o defeito que esta SPEC conserta.

---

## 8. Separando FATO de INFERÊNCIA

**📊 FATO:** os números da §1 e da §3; 9 itens/44 pontos; determinismo mínimo
95,6% com 42 de 43 em 100%; `travamento.assumido` inexistente; as 73 em 9m59;
28 passed; 44→39 xfailed; 915 passed na bateria.

**💭 INFERÊNCIA:**

- 💭 Que o corte de determinismo deve ser **100%** e não 96%. Os dois reprovam a
  mesma rota hoje; escolhi 100% porque *"determinístico é determinístico"*.
  **Se aparecer uma rota legítima em 99%, o número muda — e a causa se escreve.**
- 💭 Que a nota do eixo F (6 + 4) é a proporção certa. Não há referência: são os
  primeiros pontos que a régua dá por comportamento em produção.

**🔴 RECOMENDAÇÃO:**

1. Rodar `medir_rota.py --todas --com-espelho` **de dentro de `backend/`** e com
   `PYTHONIOENCODING=utf-8`. Sem a flag, nenhuma rota é AAA — **e isso é o
   projeto, não um defeito.**
2. Depois da primeira semana de piloto, reler o eixo F: ele é o único que mede
   comportamento real, e hoje tem dado de 4 acionamentos (P-089-B).
3. Regerar `INVENTARIO-DE-ROTAS.md` — o denominador mudou três vezes, e as notas
   antigas **não são comparáveis** com as novas (P-089-C).
