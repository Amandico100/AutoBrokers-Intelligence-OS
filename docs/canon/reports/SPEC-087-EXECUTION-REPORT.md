# Relatório de execução — SPEC-087: a tela que o corredor não conhece

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-087-a-tela-que-o-corredor-nao-conhece.md` (v1)
**Branch:** `feat/spec087-a-tela-que-o-corredor-nao-conhece`
**Executor:** Opus 5 (1M) · 26/08/2026
**Commit inicial:** `56b1b02` · **Commit final:** `04ded4c` + este relatório
**Estado final:** CONCLUÍDA COM RESSALVAS

---

## 🧑 PARA O FOUNDER — uma página

### O que muda

Quando a seguradora manda uma tela que o corredor não sabe responder, **o
produto passa a saber disso**. Hoje o segurado espera e ninguém fica sabendo;
depois desta SPEC a tela cai numa fila com o texto, a rota e a data — e o
contador ordena a fila pela dor.

### 🔴 Três coisas que você precisa saber

1. **Refiz a medição da SPEC e ela estava errada em três pontos.** Não é
   detalhe: muda para onde apontar o trabalho.

   | a SPEC dizia | 📊 eu medi |
   |---|---|
   | 269 de 755 telas cegas = **35,6%** | **378 de 1.696 = 22,3%** |
   | **66** menus cegos | **27** |
   | 🔴 *"tokio 13/13 — CEM POR CENTO cego"* | **tokio 18/54 = 33%** |
   | — | 🔴 **a pior é a zurich auto: 65,2%** |

   A P-087-01 diz que a tokio é *"a rota mais quebrada medida"*. **É a zurich.**

2. **A SPEC mandou escolher entre dois mascaradores, e os dois estavam
   errados.** 📊 Existe um terceiro na árvore — `atlas/templater` — que pega
   **6 de 8** telas onde o escolhido pega **1**: endereço, data de nascimento,
   chassi, CEP solto, placa em minúscula e CPF com espaços passavam batido. Foi
   um painel de revisão que achou; eu tinha aceitado a lista da SPEC sem medir.

3. **O Alfaiate voltou a existir — e está DESCARREGADO.** A chave dele nunca
   casou o registry (📊 10 de 10 devolviam `None`), e isso explicava três zeros
   de uma vez. Consertada, ele volta a **poder escrever no corredor**. Então o
   auto-apply nasce **desligado por variável** (`ALFAIATE_AUTO_APPLY`), e o
   gatilho é seu — P-263 diz onde e o que medir antes.

### ⚠️ E uma coisa que eu quebrei e conserto não desfaz

📊 Uma linha de `route_drift` está com a `signature` corrompida (58 caracteres
em vez de 64). Foi o backfill desta SPEC: o padrão de telefone não tem `\b` e
comeu dígitos dentro de um sha256. **Se você receber um alerta de deriva
repetido, é essa linha** — ela vai duplicar uma vez e depois normalizar. P-262.

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo. 🔴 Ao contrário: o BLOCO C **compôs** dois
      mascaradores que já existiam em vez de criar o terceiro.
- [x] Uma migration nova, aditiva, idempotente, expand-first, não destrutiva.
- [x] ⛔ **Nenhuma mensagem saiu** · 📊 `platform_sends` 24h: **0**.
- [x] ⛔ **Nenhum agente ligado** · 📊 `attendance` com `is_active=true`: **0**.
- [x] ⛔ `playbook_overlays` continua com **0 linhas** (gate ④ do BLOCO D).
- [x] ⛔ Nenhum portal, nenhuma variável de ambiente tocada, nenhum dado pessoal
      impresso.
- [x] ⛔ `git add -A` **não foi usado** — arquivos por nome (P-247).

---

## 1. BLOCO 0 — a medição refeita

Rodando `match_ura_step` sobre `backend/tests/corpus/telas_reais/` (o corpus
versionado e auditado por PII da SPEC-083), com o casamento **mais generoso
possível** — 14 playbooks × 76 subserviços — então o número é **piso**:

```
seguradora ramo         distintas  CEGAS      %  menus m.cegos
zurich     auto               207    135  65,2%     20       2  🔴
yelum      auto               195     55  28,2%      6       5
allianz    residencial        195     45  23,1%    108       8
porto      auto               215     31  14,4%     11       0
allianz    auto               119     21  17,6%     70      10
…
TOTAL                        1.696    378  22,3%    286      27
```

⚠️ **A SPEC mediu o banco em 45 dias; eu medi o corpus versionado.** O corpus
roda sem rede, já foi auditado por PII e é a mesma fonte dos guardas de
corredor. **A direção é a mesma; o alvo mudou.**

---

## 2. O que cada bloco entregou

### BLOCO C — a máscara antes da tabela global · `4668843` + `4c7af1d`

📊 `route_drift` e `playbook_overlays` são **globais, sem `company_id`** — e a
coluna nem existe. ✅ **A chave global está certa** (o Atlas é um só, decisão
registrada). ⛔ **O vazamento era a CARGA.**

🔴 **E o gate ② mudou o desenho duas vezes.** Mascarar é fácil; mascarar sem
matar o casamento é o problema — e o próprio gate mostrou que a âncora
mascarada **sequestrava tela alheia** quando a identidade da tela *era* a PII.

> ⛔ **Mascarar pode custar a âncora — e quando custa, não se cria âncora.**

### BLOCO A — a tela cega vira fila · `11ae898` + `4c7af1d`

Fila de **trabalho**, não log. A dedupe é o que a torna útil, e o contador é o
que ordena. `company_id` existe aqui, e a diferença para `route_drift` é o
produto: aquilo é **mapa** (um só para todas); isto é **fila de trabalho de uma
corretora**.

### BLOCO B — a chave quebrada · `e2c1848` + `4c7af1d`

📊 Com linha de controle, mesmo registry, só a chave muda: **10 de 10 devolviam
`None`**; a ref real devolve o playbook em 10 de 10. Uma causa explicava
`simulator_passed` NULL em 16/16, `auto_applied` false em 16/16 e
`playbook_overlays` = 0.

> ⛔ Ler esses zeros como *"o auto-publish é um risco vivo"* é ler ao contrário:
> **eles são o atestado de óbito do Alfaiate.**

---

## 3. Migration

`20260826_01_spec087_blocoA_tela_cega.sql` — aplicada e verificada:

```
V1 tela_cega / rls=true / policies=0
V2 ck_tela_cega_status CHECK (status IN ('aberta','virou_passo','ignorada'))
   ck_tela_cega_vezes  CHECK (visto_quantas_vezes >= 1)
V3 🔴 CONTROLE (transação desfeita por `raise`):
   status recusado? t | vezes>=1 recusado? t | UNIQUE recusou? t
V4 uq_tela_cega_chave UNIQUE (company_id, insurer_key, ramo, hash_normalizado)
V5 FK company_id → companies ON DELETE CASCADE
```

---

## 4. O painel — 4 lentes cegas, e o que elas acharam

📊 **19 achados. Os mais graves, todos criados pelos meus consertos ou aceitos
da SPEC sem medir:**

| # | achado | quem |
|---|---|---|
| 1 | 🔴 a SPEC listou os **dois mascaradores errados** — o certo pega 6 de 8 onde o escolhido pega 1 | PII |
| 2 | 🔴 **o hash sobre texto cru matava a dedupe** — uma linha por *pessoa*, que é a razão da fila existir | PII + correção |
| 3 | 🔴 **a `signature` era destruída** pelo mascarador — 17,9% de 50 mil hashes, e **uma linha de produção já corrompida** | correção **e** red team, independentes |
| 4 | 🔴 o gancho registrava **prosa de analista humano** — 4.315 textos que nunca se repetem | correção |
| 5 | 🔴 o gancho disparava **dentro do simulador** com `company_id="sim"` | red team |
| 6 | 🔴 o corte em 60 **partia a marca** e matava a âncora | correção |
| 7 | 🔴 `ramo='todos'` media o **corredor errado** — 100% dos mapas ativos | red team |
| 8 | 🔴 backtracking catastrófico: 📊 **não terminou em 120 s** | correção |
| 9 | 🔴 quatro guardas **que não tinham como falhar** | guardas |

⚠️ **E dois dos meus próprios consertos do painel estavam errados** — pegos pela
bateria e pelo guarda novo, na primeira rodada: `templatize` deixa `{CPF}` e
`redigir` deixa `[CPF]`, e eu só ensinei uma família ao curinga; e o cortador só
olhava `[`.

---

## 5. Testes — saída real

```
test_a_mascara_vem_antes_da_tabela_global.py    21 passed
test_a_tela_cega_vira_fila.py                   24 passed
test_a_chave_quebrada_e_o_alfaiate.py           15 passed
                                                ──────────
                                                60 passed
```

### As mutações — 38 no total, todas vermelhas

```
BLOCO C  ....................... 10 vermelhas   (obrigatória: 8)
BLOCO A  .......................  9 vermelhas   (obrigatória: 1)
BLOCO B  .......................  9 vermelhas   (obrigatória: 2)
consertos do painel ............ 10 vermelhas
```

Toda restauração **por cópia**, sha256 conferido, controle verde dos dois lados.

⚠️ **Quatro ficaram verdes na primeira rodada** e foram consertadas antes de o
número valer: o `.*` sem prefixo, a âncora singular por inserção, o `ramo='auto'`
no caminho que não é o real, e o corte da marca.

---

## 6. 📊 A BATERIA

> Lido de `backend/.diario-da-bateria.jsonl`, que o `conftest.py` escreve.
> 🔴 **Commit não é rodada.**

| | |
|---|---|
| rodadas nesta SPEC | 📊 **131** |
| das quais **bateria inteira** | 📊 **2** (mais 2 rodadas parciais de alvo múltiplo) |
| relógio total esperando a suíte | 📊 **35,8 min** |
| só as inteiras | 📊 **28,6 min** — **80% do relógio** |

### As duas inteiras

```
05:50:29   867,8 s   764 coletados   4 falhas   ← 2 minhas + 2 da P-246
06:25:08   825,0 s   779 coletados   2 falhas   ← só a P-246
```

📊 **Os guardas cresceram 15** entre as duas (764 → 779), e os dois vermelhos
que eram meus sumiram:

- `test_spec034_onda4` — um guarda **pré-existente** que meu conserto quebrou
  (`anchor_from_text` ganhou um import e passou a poder levantar). A lição
  migrou: a âncora é regex segura nas duas saídas — existe e casa, ou é vazia e
  ninguém escreve overlay.
- `test_a_politica_de_autorizacao_passa` — 📊 passa sozinho (47/47). Foi
  instabilidade do `node` sob carga da bateria.

⚠️ **Os 2 vermelhos não são desta SPEC:** é o vazamento de mutação da P-246 (o
restaurador se reportando depois de limpar, e uma vítima dele). 📊 A bateria
anterior tinha `715 passed / 4 failed`; os dois vermelhos que eram meus sumiram,
e os guardas cresceram 17.

---

## 7. Pendências abertas

`P-262` 🔴 a `signature` corrompida em produção — **foi meu backfill** ·
`P-263` `ALFAIATE_AUTO_APPLY` sem documentação, e o que medir antes de ligar ·
`P-264` a fila `tela_cega` não tem leitor (📊 ~1.100 linhas/45 dias) ·
`P-265` o contador é read-modify-write ·
`P-266` nome próprio em saudação solta passa pelos dois mascaradores.

---

## 8. O que a SPEC previa e não foi feito

⛔ Nada foi cortado. Os itens que a própria SPEC v1 já tinha tirado da proposta
(drift v2, evidence/candidate/sandbox, approval `route_publish`, release +
canário) continuam fora, com o gatilho de cada um escrito na SPEC.

⚠️ **E o canário Amandus → Resulta → AutoFleet não foi executado**, pelo mesmo
motivo da SPEC-093: ele exige ligar o atendimento, e as travas proíbem. O que
deu para verificar sem ligar nada está na §0.
