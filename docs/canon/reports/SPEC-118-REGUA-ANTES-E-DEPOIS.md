# SPEC-118 · a régua das 73 rotas antes e depois, e a mutação dos guardas novos

> Companheiro do `SPEC-118-EXECUTION-REPORT.md` (o relatório tem teto de 15 KB).
> 📊 As duas rodadas são `python scripts/medir_rota.py --todas --formato tabela`,
> de dentro de `backend/`, com o **mesmo corpus** (o de 16/09/2026) e a árvore
> **sozinha** — nada mais rodando (P-118-14).

| | ANTES | DEPOIS |
|---|---|---|
| commit | `b897ac7` (HEAD limpo) | a árvore que virou `125a024` |
| ⚠️ | — | a rodada começou **antes** do commit: o que ela mediu é o conteúdo que `125a024` fixou |
| relógio | 18 min 24 s (20:38:25 → 20:56:49) | 16 min 45 s (20:58:35 → 21:15:20) |
| rotas medidas | 73 | 73 |

## As faixas — antes e depois

| patamar | ANTES | DEPOIS |
|---|---:|---:|
| 🔴 **AAA — atende do começo ao fim** | **0** | **0** |
| quase | 26 | 26 |
| parcial | 15 | 15 |
| esqueleto | 2 | 2 |
| SEM_CORPUS | 30 | 30 |
| **com portão aberto** | **18** | **18** |

## 🔴 O RESULTADO, E ELE É MAIS FORTE DO QUE "NENHUMA CAIU"

📊 As duas saídas são **idênticas byte a byte**:

```
$ diff regua_ANTES_F5.txt regua_DEPOIS_F5.txt     (sem saída)
$ md5sum regua_ANTES_F5.txt regua_DEPOIS_F5.txt
af4d7a2bed6fd0a152b71cf3527913fa *regua_ANTES_F5.txt
af4d7a2bed6fd0a152b71cf3527913fa *regua_DEPOIS_F5.txt
```

**FATO:** o conserto de `_STREET_RE` **não moveu nenhuma das 73 notas** — nem para cima, nem para
baixo. Nenhuma rota caiu, que era a condição da SPEC; e nenhuma subiu.

🔴 **INFERÊNCIA, e é a parte que importa:** a régua **não vê** este defeito. O corpus versionado não
tem nenhuma tela em que um endereço com `R.` e um ponto de referência atravesse o parser — as telas
são da URA da seguradora, e o endereço com nome de lugar chega pelo **pin do segurado**, que é o
outro lado da conversa. Uma nota estável aqui **não é** prova de que nada mudou no produto: é prova
de que **a régua mediu outra coisa**.

⚠️ É por isso que o conserto tem um guarda **próprio**
(`backend/tests/test_o_endereco_do_pin_reconhece_a_abreviacao.py`, 6 asserções, 4 delas de controle),
que nasceu **vermelho** com o defeito presente. Sem ele, a única evidência seria um número que não
mexeu — e um número que não mexe é compatível com *"consertou"* e com *"não fez nada"*.

## 🔴 O que a SPEC exigia: NENHUMA rota pode CAIR

```
SUBIRAM ................ 0
CAIRAM ................. 0      <- a regra: se > 0, reverter o conserto
mudaram de ESTADO ...... 0      (medida <-> sem medida)
mesma nota, PATAMAR ≠ .. 0
IDÊNTICAS .............. 73
```

### As que subiram
*(nenhuma)*


### 🔴 As que caíram
*(nenhuma)*


### As que mudaram de estado
*(nenhuma)*


### Mesma nota, patamar diferente
*(nenhuma)*


## ⚠️ Por que estes números NÃO se comparam com os de 24/08/2026

O denominador da régua saiu de **106** para **76 / 70 / 64** desde a SPEC-089: item que não se
aplica a uma rota sai da conta em vez de ser perdoado. `72/76` de hoje e `102/106` de então são
frações de réguas diferentes — e a página do painel diz isso, em vez de esconder (D-118-04).

## O limite honesto desta medição

📊 O corpus lido pelas duas rodadas é o de **16/09/2026**. Existem ~51 sessões mais novas que a
régua nunca viu, e regerar o corpus **move as 73 notas** — ficou fora desta SPEC de propósito
(**P-118-08**, **D-118-03**): misturar "a régua mudou" com "o produto mudou" no mesmo commit tira
o direito à conclusão (CLAUDE.md §9.2).

🔴 E a comparação só vale porque o comparador **consegue** acusar queda. Provado com linha de
controle: duas cópias do mesmo arquivo → `IDENTICAS: 73`, `CAIRAM: 0`; a mesma comparação com uma
nota rebaixada à mão (`alfa/auto/guincho 72/76 → 60/76`) → `CAIRAM: 1`, nominalmente.


---

# A MUTAÇÃO DOS GUARDAS NOVOS — protocolo §5 ③

> 🔴 **Um guarda que não tem como falhar não guarda nada** (CLAUDE.md §9.3). Cada guarda novo desta
> fatia foi exercitado com o defeito **reintroduzido**, e as saídas estão coladas.

## 1 · `test_o_endereco_do_pin_reconhece_a_abreviacao.py` — nasceu VERMELHO

📊 No HEAD `b897ac7`, com `_STREET_RE` na forma histórica:

```
FAILED ...::test_a_abreviacao_R_ponto_e_reconhecida_como_logradouro
FAILED ...::test_o_MOTOR_que_a_producao_usa_leva_a_rua_certa_ao_corredor
2 failed, 11 passed in 8.65s

AssertionError: o ponto de referencia do pin virou a rua:
  {'cep': '88015-530', 'uf': 'SC', 'rua': 'Posto Shell',
   'bairro': 'R. Rafael Bandeira', 'cidade': 'Florianopolis'}
```

📊 Depois do conserto: `6 passed in 4.53s`. As **4 linhas de controle** (a mesma via por extenso ·
`Dr.`/`Sr.` que **não** são logradouro · endereço sem ponto de referência · a rodovia com caminho
próprio) ficaram **verdes nas duas rodadas** — o mérito é do fator que mudou, e de mais nada.

## 2 · `test_a_lista_de_finalizacao_nao_tem_fantasma.py` — e a asserção que nasceu FROUXA

🔴 **Esta é a parte que vale registrar, porque o defeito era do próprio guarda.**

A 1ª versão de `test_o_health_publica_o_sinal` perguntava se a **chave**
`sinais["finalize_refs_fantasma"]` aparecia em `main.py`. 📊 Apagando a linha do caminho de sucesso —
a que **calcula** o sinal — o guarda continuou **VERDE**:

```
# mutação: `sinais["finalize_refs_fantasma"] = refs_de_finalizacao_sem_corredor(_PLAYBOOKS)`
#          vira `pass`
.......                                                                  [100%]
7 passed in 4.66s      ← 🔴 VERDE COM O DEFEITO PRESENTE
```

A causa: o **caminho de erro**, trinta linhas abaixo, escreve a mesma chave (`= None`). A asserção
passou a ser sobre a **atribuição que chama o motor**. Com a **mesma** mutação:

```
FAILED tests/test_a_lista_de_finalizacao_nao_tem_fantasma.py::test_o_health_publica_o_sinal
1 failed, 6 passed in 4.91s
AssertionError: o /health nao CALCULA os refs fantasma — a trava existe e ninguem a ve.
                ⚠️ a chave sozinha nao basta: o caminho de erro tambem a escreve
```

E depois de restaurar `main.py`: `7 passed in 4.40s`.

⚠️ A restauração foi `git checkout --` **porque a mudança estava commitada**. Num arquivo com
trabalho não commitado isso apagaria o trabalho — e é exatamente por isso que
`backend/scripts/verificar_mutacoes.py` restaura de uma **cópia**, nunca do git.

## 3 · Os vermelhos PRÉ-EXISTENTES, reconferidos para não serem confundidos com estes

📊 Rodados nesta árvore, depois do conserto, e **idênticos ao que a linha de base declarava**:

```
test_o_acionamento_nao_pede_o_impossivel .......... VERMELHO — 12 falha(s)   (por `local_seguro`)
test_golden_do_eletricista ........................ 2 PROBLEMA(S)
test_o_corredor_conhece_a_tela_que_esta_na_frente . VERMELHO — 2 falha(s)
```

E os consumidores do parser de endereço, que o conserto do §A poderia ter movido, continuam verdes:

```
$ python -m pytest tests/test_a_confirmacao_confere_antes_de_abrir.py     tests/test_o_segurado_nao_fica_no_escuro.py tests/test_spec031_yelum_v3.py     tests/test_o_pin_do_segurado_chega.py tests/test_o_acionamento_nao_trava.py -q
23 passed in 21.58s
```
