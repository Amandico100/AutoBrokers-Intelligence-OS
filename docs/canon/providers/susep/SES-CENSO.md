# SUSEP SES — CENSO MEDIDO da BaseCompleta

> **A primeira fonte EXTERNA do AutoBrokers.** Estatística oficial do mercado segurador
> brasileiro: prêmio e sinistro por **entidade × competência × ramo**, desde 1995.
> **Sem login, sem chave, sem contrato.**
>
> BLOCO 0 da **SPEC-094.1** · medido em **03/09/2026** · escrito pelo INVESTIGADOR.
> ⛔ Nenhum dado de pessoa existe nesta base: a granularidade mínima é a **seguradora**.
> Nome de seguradora é nome de empresa, e aparece cru neste documento de propósito.

---

## EXECUTION CARD

```
OUTCOME ..............  o BLOCO B da 094.1 sabe, por MEDIÇÃO, quais arquivos ler, com
                        que encoding, com que chave, e quanto vale a sinistralidade de
                        mercado que ele vai comparar com a carteira da corretora
FONTE ................  https://www2.susep.gov.br/download/estatisticas/BaseCompleta.zip
MÉTODO ...............  1 HEAD + 1 GET. Download UMA vez para o scratchpad. Nenhuma
                        gravação no MinIO nesta rodada (o BLOCO B faz isso pela Rotina)
DOWNLOAD .............  571.756.724 bytes (571,8 MB) · HTTP 200 · sem redirect · sem auth
LAST-MODIFIED ........  Mon, 31 Aug 2026 03:47:22 GMT
SHA256 ...............  7810ea3362f6166a345b923c25b3d8e7a30631d6fd7a3f9482b77129ec5c5a46
COMPETÊNCIA FINAL ....  202606  (📊 lido de Ses_diversos.csv, não inferido)
SAÍDA ................  este arquivo + seguradora-coenti.json + ses-schema.json
```

---

## 1. O ZIP — 40 arquivos, e só 5 interessam

📊 `python -c "import zipfile; …"` sobre o ZIP baixado:

| arquivo | bytes | papel |
|---|---:|---|
| `SES_Balanco.csv` | 743.235.096 | balanço contábil — **não usamos** |
| `SES_ValoresMovRamos.csv` | 554.205.516 | movimento detalhado — não usamos |
| `SES_UF2.csv` | 466.504.669 | por UF — 💭 candidato futuro (mercado local) |
| `Ses_rmovram.csv` | 294.475.215 | resseguro — não usamos |
| **`Ses_seguros.csv`** | **136.068.656** | 🔴 **O FATO**: prêmio e sinistro por mês × entidade × ramo |
| **`Ses_cias.csv`** | 40.683 | domínio de ENTIDADE (`Coenti` → `Noenti`) |
| **`Ses_ramos.csv`** | 7.126 | domínio de RAMO (`coramo` → `noramo`) |
| **`ses_gruposramos.csv`** | 563 | domínio de GRUPO de ramo (22 grupos; `05` = Automóvel) |
| **`Ses_diversos.csv`** | 76 | uma linha: `Data_Final;202606` |

🔴 **O ZIP inteiro é 571 MB; o que o produto precisa são 136 MB + 48 KB.** É por isso
que a Rotina do BLOCO B extrai por nome, e o adapter nunca abre o ZIP.

## 2. As convenções — e as três que quebram quem copiar exemplo de internet

```
separador ................  ;
encoding .................  latin-1 (cp1252)   🔴 utf-8 estoura em "PREVIDÊNCIA"
decimal ..................  VÍRGULA            🔴 "350407,58" — float() cru dá ValueError
quebra de linha ..........  CRLF
padding ..................  🔴 os CÓDIGOS das tabelas de domínio vêm com espaços à
                            direita, largura fixa: "04600     ". No FATO vêm sem.
                            Casar chave sem .strip() devolve ZERO linhas, em silêncio
negativos ................  `sinistro_ocorrido` pode ser NEGATIVO (estorno de provisão).
                            📊 Porto, ramo 0520, 202605: −53.790,44. Truncar em zero
                            inventa sinistro que não houve
```

## 3. `Ses_seguros.csv` — o MarketFact

```
damesano · coenti · cogrupo · coramo
premio_direto · premio_de_seguros · premio_retido · premio_ganho · premio_emitido2 · premio_emitido_cap
sinistro_direto · sinistro_retido · sinistro_ocorrido · sinistros_ocorridos_cap · recuperacao_sinistros_ocorridos_cap
desp_com · despesa_resseguros · receita_resseguro · rvne · conveniodpvat · consorciosefundos
```

| medido | valor |
|---|---|
| linhas | **1.801.731** |
| granularidade | **`damesano` × `coenti` × `cogrupo` × `coramo`** |
| período | **199501 → 202606** · 378 competências |
| entidades distintas | 275 |
| ramos distintos | 217 |
| competências com auto (grupo 05) | 200009 → 202606 · 310 |
| seguradoras com auto nos últimos 12 meses | **105** |

🔴 **`damesano` é COMPETÊNCIA, não data.** `202606` é junho de 2026 inteiro. Uma métrica
que compare com a carteira tem de comparar **mês fechado com mês fechado** — e a base só
existe até `202606`, três meses atrás. **A defasagem é da fonte, e tem de aparecer no
ponteiro do Evidence Pack.**

### 3.1 A sinistralidade, e por que só um par de campos serve

```
sinistralidade = sinistro_ocorrido / premio_ganho
```

As duas pontas do **mesmo regime de competência**: o prêmio já *ganho* no mês contra o
sinistro *ocorrido* no mês. ⛔ `premio_direto` é emissão e `sinistro_direto` é pago —
**misturar regimes é o erro clássico**, e ele não trava: devolve um número plausível e
errado (CLAUDE.md §9.5).

### 3.2 O grupo de ramo sai dos DOIS PRIMEIROS dígitos de `coramo`

📊 Os 13 ramos do grupo **05 — Automóvel** presentes na base:

```
0531 Automóvel-Casco          0553 RC Facultativa Veículos-RCFV      0542 Assistência e Outras-Auto
0520 Acid. Pessoais Passag.   0525 Carta Verde                       0588 DPVAT (+0583/0589 extintos)
0523 · 0524 · 0526 · 0527 · 0544  (RUN OFF ou residuais)
```

⚠️ 📊 **Errar o corte custa a tabela inteira:** a primeira medição usou `coramo[1:3]` e
devolveu **zero** ramos de auto — silenciosamente. É `coramo[:2]`.

## 4. 📊 O exemplo de sinistralidade — Porto Seguro × auto × 3 meses

`coenti 05886 · PORTO SEGURO COMPANHIA DE SEGUROS GERAIS · grupo de ramo 05 · 202604–202606`

| competência | prêmio ganho (R$) | sinistro ocorrido (R$) | sinistralidade |
|---|---:|---:|---:|
| 202604 | 1.315.555.466,70 | 810.464.672,38 | **61,61 %** |
| 202605 | 1.363.390.236,46 | 752.732.317,52 | **55,21 %** |
| 202606 | 1.329.045.965,49 | 726.322.791,58 | **54,65 %** |
| **3 meses** | **4.007.991.668,65** | **2.289.519.781,48** | **57,12 %** |

Só o ramo `0531` (Casco): 59,75 % → 55,92 % → **50,47 %** — três meses de queda.

📊 O trimestre, nas outras seguradoras com auto ativo:

```
MAPFRE 48,46%  ·  PORTO 57,12%  ·  TOKIO MARINE 60,56%  ·  BRADESCO AUTO/RE 60,85%
YELUM 61,50%   ·  SUHAI 62,46%  ·  ALLIANZ 65,06%       ·  HDI 67,44%
ZURICH MINAS 72,80%  ·  SURA 75,60%  ·  ALFA 45,63%     ·  AZUL 2,44% ⚠️
```

⚠️ **Os 2,44 % da Azul não são eficiência** — são o sinal de uma carteira em
transferência ou run-off. É exatamente o tipo de número que o produto **não pode
publicar sozinho**: ele responde, parece ótimo, e diz outra coisa.

## 5. O casamento com as 15 seguradoras do repositório

📊 Fonte da lista: `SELECT DISTINCT insurer_key FROM portals` → **17 portais, 15
seguradoras** (2 portais de vidros, um sem `insurer_key`).

```
CASARAM com um coenti .................  14 / 15
COM AUTO ATIVO em 202606 ..............  12 / 15
CASAM mas SEM auto recente ............   2   sompo (último 202303) · seguros_unimed (200901)
UNKNOWN ...............................   1   sulamerica
```

| chave | coenti | entidade no SES | auto em 202606 |
|---|---|---|---|
| porto | 05886 | PORTO SEGURO COMPANHIA DE SEGUROS GERAIS | ✅ |
| allianz | 05177 | ALLIANZ SEGUROS S.A. | ✅ |
| tokio_marine | 06190 | TOKIO MARINE SEGURADORA S.A. | ✅ |
| bradesco | 05312 | BRADESCO AUTO/RE COMPANHIA DE SEGUROS | ✅ |
| yelum | 05185 | YELUM SEGUROS S.A. | ✅ |
| hdi | 06572 | HDI SEGUROS S.A. | ✅ |
| mapfre | 06238 | MAPFRE SEGUROS GERAIS S.A. | ✅ |
| suhai | 04952 | SUHAI SEGURADORA S.A. | ✅ |
| zurich | 05495 | ZURICH MINAS BRASIL SEGUROS S.A. | ✅ |
| azul | 05355 | AZUL COMPANHIA DE SEGUROS GERAIS | ✅ |
| sura | 06751 | SEGUROS SURA S.A. | ✅ |
| alfa | 06467 | ALFA SEGURADORA S.A. | ✅ |
| sompo | 05720 | SOMPO SEGUROS S.A. | ❌ último 202303 |
| seguros_unimed | 06947 | UNIMED SEGURADORA S.A. | ❌ último 200901 |
| **sulamerica** | **UNKNOWN** | — | ❌ |

🔴 **Por que `sulamerica` fica UNKNOWN e não recebe um palpite:** há **11 entidades**
"SUL AMERICA" em `Ses_cias.csv`, e **nenhuma** das candidatas tem prêmio de auto no
trimestre medido — a histórica do ramo é `05240 SUL AMERICA TERRESTRES, MARÍTIMOS E
ACIDENTES`. Escolher pelo nome seria **adivinhar**, e a métrica sairia com o número de
outra empresa. **UNKNOWN é a resposta correta, e ela nunca vira zero** (M2).

🔴 **E o casamento por nome tem armadilha medida:** buscar o token `SEGUROS` para
`seguros_unimed` devolveu **284 candidatos** e `SURA` devolveu **130** (casa dentro de
"asSURAnt", "ASSURANCE"). O desempate que funcionou foi **prêmio de auto > 0 no
trimestre**. 🔴 **Nome não é chave.** O mapa é versionado em
`seguradora-coenti.json` e revisado por gente — nunca recalculado em runtime.

## 6. O que este censo NÃO mediu

| não medido | por quê |
|---|---|
| `SES_UF2.csv` (mercado por UF) | 466 MB; fora do escopo do BLOCO B. 💭 é o próximo cruzamento |
| entidade × grupo econômico (`Cogrupo`) | a corretora vende pela entidade, não pelo grupo |
| ramos fora do grupo 05 | o BLOCO B começa por auto; o schema serve para todos |
| a série histórica completa por seguradora | 1,8 M de linhas; o conector recorta por `coenti` + competência |
| gravação no MinIO | é do BLOCO B, por Rotina (`tick.py`), não do censo |
| cadência real de atualização | 📊 um `Last-Modified` (31/08/2026) não prova "semanal". Duas medições em datas diferentes provam |

## 7. Os arquivos

| arquivo | o que é |
|---|---|
| `SES-CENSO.md` | este documento |
| `seguradora-coenti.json` | o mapa nome canônico → `coenti`, com `UNKNOWN` e os candidatos avaliados |
| `ses-schema.json` | colunas, tipos, convenções, período e o `MarketFact` sugerido |

📊 Scripts da medição: `scratchpad/bloco0_0941/{ses_censo,ses_auto,ses_map,ses_build_docs}.py`
