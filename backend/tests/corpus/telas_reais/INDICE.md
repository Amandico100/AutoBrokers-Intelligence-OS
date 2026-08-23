# Corpus de telas reais — ÍNDICE

> Gerado em **2026-08-23T12:58:48+00:00** · commit `7064183`
> 📊 `marcas_de_corretora()` = **8** (o CONTROLE da SPEC-084 §2.5.1.3 — se fosse 0, a geração teria rodado sem banco e o corpus **não estaria mascarado**)

🔴 Este arquivo existe porque a SPEC-083 §7 proíbe pular em silêncio: *"truncar calado lê-se como 'cobrimos tudo'"*.

## Os arquivos

| arquivo | linhas | KB | sessões no corpus | candidatas | teto | subserviços | c/ desfecho |
|---|---:|---:|---|---:|---:|---:|---:|
| `porto-auto.jsonl` | 521 | 154 | 4830574a e3b1561f f4838bb3 c470d13d 67296ad9 d0d64bfc d6f1f8d3 697561ab d801cbd8 ca755794 c5cafa8b e5318468 b1ff65f2 0c1e8e3e 1f2582fc 90a47771 cdcc7125 8c490e96 e17f4b74 | 61 | 5 | 8 | 17 |
| `porto-residencial.jsonl` | 210 | 66 | 565cb39a 3854b4a2 5bcf0792 84187509 0fe42179 897c42ff 0e97bfa8 e3b9dfd6 4631b3ed | 9 | 5 | 5 | 4 |

## Por que cada sessão entrou

**`porto-auto.jsonl`**
- [?4145720 - 26] diversidade (jaccard 0.00) -> 4830574a
- [bateria] COM DESFECHO -> e3b1561f
- [bateria] COM DESFECHO -> f4838bb3
- [bateria] COM DESFECHO -> c470d13d
- [bateria] COM DESFECHO -> 67296ad9
- [chaveiro] COM DESFECHO -> d0d64bfc
- [guincho] COM DESFECHO -> d6f1f8d3
- [guincho] COM DESFECHO -> 697561ab
- [guincho] COM DESFECHO -> d801cbd8
- [guincho] COM DESFECHO -> ca755794
- [guincho] COM DESFECHO -> c5cafa8b
- [guincho] AVISO: 17 sessao(oes) FORA do corpus pelo teto de 5 por rota
- [tecnico] COM DESFECHO -> e5318468
- [tecnico] COM DESFECHO -> b1ff65f2
- [vidros] diversidade (jaccard 0.00) -> 0c1e8e3e
- [(tronco)] diversidade (jaccard 0.00) -> 1f2582fc
- [(tronco)] diversidade (jaccard 0.00) -> 90a47771
- [(tronco)] diversidade (jaccard 0.00) -> cdcc7125
- [(tronco)] diversidade (jaccard 0.00) -> 8c490e96
- [(tronco)] diversidade (jaccard 0.00) -> e17f4b74
- [(tronco)] AVISO: 25 sessao(oes) FORA do corpus pelo teto de 5 por rota

**`porto-residencial.jsonl`**
- [chaveiro] COM DESFECHO -> 565cb39a
- [eletrodomesticos] diversidade (jaccard 0.00) -> 3854b4a2
- [encanador] COM DESFECHO -> 5bcf0792
- [encanador] COM DESFECHO -> 84187509
- [encanador] COM DESFECHO -> 0fe42179
- [(tronco)] diversidade (jaccard 0.00) -> 897c42ff
- [(tronco)] diversidade (jaccard 0.05) -> 0e97bfa8
- [(tronco)] diversidade (jaccard 0.15) -> e3b9dfd6
- [(tronco)] diversidade (jaccard 0.45) -> 4631b3ed

## Linhas RECUSADAS — sujeira que sobrou depois da máscara

_nenhuma_

## Contagens por seguradora

| seguradora | ORFAO_sessao | dedup | nivel:- | nivel:nivel-1-resposta | nivel:nivel-2-texto | nivel:sem-escolha-de-ramo | ramo:auto | ramo:indefinido | ramo:residencial | ramo:sem_escolha | senha_preservada | servico:indefinido | servico:nivel | vocativo_mascarado | zona:HUMANO | zona:URA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| porto | 1 | 520 | 52 | 29 | 41 | 15 | 61 | 52 | 9 | 15 | 21 | 34 | 36 | 39 | 384 | 1764 |

## Vocativos

📊 esqueletos com ≥3 cabeças distintas (= DADO, mascarado): **7** · com exatamente 2 (= `NOME_DUVIDOSO`, **não** mascarado automaticamente, fica para leitura humana): **8**

