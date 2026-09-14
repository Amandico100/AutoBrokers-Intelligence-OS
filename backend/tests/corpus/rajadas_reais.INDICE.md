# Corpus de rajadas reais — ÍNDICE

> Gerado em **14/09/2026** por `backend/scripts/gerar_corpus_de_rajadas.py --de-arquivo <export>`
> Fonte: **400 rajadas reais** (≥ 2 mensagens de entrada do segurado em ≤ 60 s) desde 01/08/2026,
> lidas pelo relógio certo — `attendance_transcripts.wa_timestamp`, ⛔ **nunca** `messages.created_at`
> (📊 o segundo é o relógio do espelho e infla as rajadas em **+39,2%**: SPEC-EXTRA-001.2 §0.3).
> SPEC-EXTRA-001.2 §13 · guarda que o consome: `backend/tests/test_uma_rajada_um_turno.py`

🔴 **Este arquivo NÃO tem uma palavra de conversa de segurado, e o `.jsonl` também não.**
O que está versionado são **traços**: quantos caracteres, se terminou em pontuação final, se
terminou em conectivo, se é dado curto, o tipo e o intervalo até a mensagem anterior.
⛔ Nenhum texto · nenhum telefone · nenhum hash · nenhuma data absoluta · nenhum UUID de corretora
(`company` é `"A"`/`"B"`, pela ordem de aparição).

## Como ele resolve a tensão "medir no acervo" × "não carregar texto"

```
tracos_da_mensagem(texto) ──► Tracos ──► janela_de_espera(Tracos) ──► segundos
      ↑ roda no acervo, por script             ↑ roda no CI, sobre ESTE corpus
      ↑ imprime só CONTAGENS                   ↑ o corpus guarda só os Tracos
```

O texto real vive **fora do repositório**, no scratchpad da sessão que gerou o corpus, e
alimenta apenas `--de-arquivo`.

## O arquivo

| arquivo | rajadas | itens | itens de texto |
|---|---:|---:|---:|
| `rajadas_reais.jsonl` | **20** | 62 | 49 |

## Critérios de aceite do corpus (§13) — cada um, e o que se mediu

| critério | exigido | medido | |
|---|---|---:|---|
| rajadas | ≥ 20 | **20** | ✅ |
| tamanhos 2 · 3 · 4 · 5+ | todos | 12 · 3 · 2 · 3 | ✅ |
| faixas de intervalo 0–3 · 3–8 · 8–18 · 18–25 · > 25 s | todas | 18 · 16 · 4 · 1 · 3 | ✅ |
| rajadas com mídia | ≥ 3 | **6** (7 imagens · 4 áudios · 1 documento · 1 vídeo) | ✅ |
| as duas corretoras | A e B | A **11** · B **9** | ✅ |
| rajadas que HOJE viram 2+ respostas | a régua | **19 de 20** | ✅ |
| rajadas que a janela une em UM turno | a régua | **12 de 20** (era 17 antes de J1) | ⚠️ |

## Por que cada rajada entrou

A escolha é **estratificada**, não aleatória, e roda nesta ordem:

1. as que **fragmentaram hoje** (`turnos_hoje` ≥ 2) e que a janela **une em uma** —
   📊 **12 das 20** (recontado em 14/09 depois de J1; eram 16). São a régua do outcome: o mesmo pedido, uma resposta só.
2. as que faltavam para cobrir tamanho, faixa de intervalo, mídia, dado curto e corretora.
3. 🔴 **3 rajadas que a janela NÃO une** (`turnos_esperados` 2 ou 3), porque um intervalo
   interno passa de 25 s. ⛔ Elas entram de propósito: o teto de 25 s é a constante da Meta
   (§20 E02), e esconder o limite do corpus seria prometer o que a janela não faz.

## 🔴 RECONTAGEM de 14/09/2026 — o achado J1 mudou `turnos_esperados`

Os 18 s deixaram de ser o padrão da janela: eles agora exigem **`termina_em_conectivo`**, e
tudo que não termina em pontuação nem em conectivo é **frase completa, 8 s** (o defeito era
cobrar 18 s de "oi", "SOCORRO" e "bateu meu carro"). O `turnos_esperados` de cada linha foi
**recomputado pelo motor** sobre este mesmo corpus.

```
📊 itens que pediam 18 s     37 de 61 (60,7%)  ->  1 de 61 (1,6%)
📊 espera do ULTIMO item     11,0 s media      ->  7,0 s media
📊 rajadas que viram 1 turno 17 de 20          ->  12 de 20
```

⚠️ **O preço está declarado:** 5 rajadas a mais fragmentam. É a troca escolhida — 4 s a menos
de espera em **toda** conversa contra a agregação de 5 rajadas em 20. ⛔ E a linha de CONTROLE
do guarda mudou de alvo junto: comparar com uma fixa de 8 s deixou de conseguir falhar
(P-E0012-J1); o controle agora é o estado de **antes** de J1.

## Os campos de cada linha

```json
{"id":"r01","company":"A",
 "itens":[{"tipo":"text","n_chars":42,"pont_final":false,"conectivo":true,
           "dado_curto":false,"intervalo_ms":0}, …],
 "turnos_hoje":2,"turnos_esperados":1}
```

- `intervalo_ms` — milissegundos desde a mensagem **anterior da mesma rajada**. O primeiro
  item é sempre `0`: o intervalo dele seria a distância até **outra** conversa.
- `turnos_hoje` — quantos **blocos de resposta** a rajada recebeu no acervo. Dois blocos são
  separados por mais de **15 s** (📊 o produto manda balões da mesma resposta com 0,7 s entre
  eles, e a demora mediana entre rajada e resposta é 67 s — 15 s separa os dois mundos).
- `turnos_esperados` — quantos turnos a janela desta SPEC prevê. ⚠️ É **expectativa**: quem a
  prova é o guarda, rodando `should_process` de verdade com o relógio dublado.

## 📊 CONTAGENS do corpus (as que o relatório cola)

```
terminam em pontuação final:  7 / 49 itens de texto
terminam em conectivo:        1 / 49
dado curto:                   5 / 49
turnos esperados pela janela: {1: 17, 2: 2, 3: 1}
hoje 2+ turnos E a janela une em 1: 16
```

### 📊 CLASSE DO ITEM × FAIXA DO INTERVALO SEGUINTE — no ACERVO INTEIRO (400 rajadas)

É esta tabela que calibra **3 · 8 · 18**, e ela é o item 6 do BLOCO 0.

| classe | 0–3 s | 3–8 s | 8–18 s | 18–25 s | > 25 s | n |
|---|---:|---:|---:|---:|---:|---:|
| dado curto | 12,2% | 34,1% | 19,5% | 17,1% | 17,1% | 41 |
| frase completa | 12,7% | 26,4% | 34,5% | 11,8% | 14,5% | 110 |
| frase inacabada | 15,8% | 36,0% | 30,0% | 9,6% | 8,6% | 417 |
| mídia sem legenda | 29,7% | 20,9% | 26,4% | 13,2% | 9,9% | 91 |

## 🔴 As duas LINHAS DE CONTROLE (CLAUDE.md §9.2)

| # | o que afirma | medido |
|---|---|---|
| **1** | `Σ n_chars > 0` — se fosse 0, a extração não rodou e **todos** os traços seriam falsos | **1.195** no corpus · **29.612** no acervo |
| **2** | a janela adaptativa e uma janela fixa de 8 s **conseguem** dar números diferentes | no corpus: **3** × **7** rajadas fragmentando · no acervo: **203** × **273** |

⚠️ Sem a linha 2, um corpus fácil "passaria" por acaso e o mérito iria para o lugar errado.

## Linhas RECUSADAS

_nenhuma_ — o gerador só escreve traços; não há máscara a falhar.

⚠️ **380 rajadas do acervo ficaram FORA do corpus versionado.** Não é truncar em silêncio: o
corpus é uma amostra estratificada de 20, e o gerador imprime as contagens do **acervo inteiro**
ao lado das do corpus, toda vez que roda.
