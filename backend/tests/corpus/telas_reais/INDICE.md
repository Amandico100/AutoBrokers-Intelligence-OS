# Corpus de telas reais — ÍNDICE

> Gerado em **2026-08-21T23:35:29+00:00** · commit `608db03`
> 📊 `marcas_de_corretora()` = **8** (o CONTROLE da SPEC-084 §2.5.1.3 — se fosse 0, a geração teria rodado sem banco e o corpus **não estaria mascarado**)

🔴 Este arquivo existe porque a SPEC-083 §7 proíbe pular em silêncio: *"truncar calado lê-se como 'cobrimos tudo'"*.

## Os arquivos

| arquivo | linhas | KB | sessões no corpus | candidatas | teto | subserviços | c/ desfecho |
|---|---:|---:|---|---:|---:|---:|---:|
| `alfa-auto.jsonl` | 72 | 22 | 1b13140b f25d07b1 5872a774 0c085fc5 fa39ff38 | 8 | 5 | 4 | 3 |
| `allianz-auto.jsonl` | 133 | 40 | d2edf0dd 4971b50b cea36de4 d6b1d83f b60d9359 | 40 | 5 | 4 | 14 |
| `allianz-residencial.jsonl` | 141 | 48 | 7ac3c101 0b244572 987572a4 bb6e16d4 bb97ea04 c58a171a | 81 | 6 | 6 | 17 |
| `azul-auto.jsonl` | 160 | 47 | b012d3cd 4c821851 d70ced75 2f0cd86a fdec3edf | 11 | 5 | 5 | 10 |
| `bradesco-auto.jsonl` | 79 | 27 | bc2cfead 72af1ae1 9daeeccb d557d3c7 8f7f1d68 | 12 | 5 | 4 | 5 |
| `hdi-auto.jsonl` | 153 | 51 | 3dc92fcf 697abd09 71caf82f e476dc68 886066e5 | 28 | 5 | 4 | 15 |
| `hdi-residencial.jsonl` | 93 | 31 | 26c0546f 13379965 0a7c24ef a1ba53b9 1c8d0849 | 8 | 5 | 5 | 1 |
| `mapfre-auto.jsonl` | 58 | 19 | a68aa770 9fae42e2 f6f2ec11 1684d4a8 d857d4de | 7 | 5 | 4 | 0 |
| `porto-auto.jsonl` | 155 | 46 | d6f1f8d3 e3b1561f d0d64bfc e5318468 0c1e8e3e | 60 | 5 | 5 | 17 |
| `porto-residencial.jsonl` | 116 | 36 | 3854b4a2 5bcf0792 565cb39a 897c42ff 0e97bfa8 | 9 | 5 | 3 | 0 |
| `tokio-auto.jsonl` | 48 | 17 | c1a67b4a d99a47a1 641420c8 fa8127ef ca52ff75 | 7 | 5 | 4 | 7 |
| `tokio-condominio.jsonl` | 16 | 5 | cd4b5ba7 c99dd4bb | 2 | 5 | 0 | 0 |
| `tokio-residencial.jsonl` | 43 | 15 | 66c9dd9b 8d9b8672 f8b83a35 e0383feb | 4 | 5 | 0 | 0 |
| `yelum-auto.jsonl` | 162 | 53 | a1c18e1c 935c4076 e6a07317 8a6040a7 e8efabc0 | 56 | 5 | 4 | 24 |
| `yelum-residencial.jsonl` | 92 | 32 | 6376f868 9cb09e20 bb573c0a 70571f37 81c8ba13 | 9 | 5 | 5 | 4 |
| `zurich-auto.jsonl` | 206 | 68 | 8e5fb8c0 963f4097 e1349860 4118ba36 d5ce1862 | 10 | 5 | 5 | 3 |

## Por que cada sessão entrou

**`alfa-auto.jsonl`**
- COM DESFECHO + servico pneu -> 1b13140b
- COM DESFECHO + servico guincho -> f25d07b1
- diversidade (jaccard max 0.08) -> 5872a774
- diversidade (jaccard max 0.30) -> 0c085fc5
- diversidade (jaccard max 0.36) -> fa39ff38

**`allianz-auto.jsonl`**
- COM DESFECHO + servico eletricista -> d2edf0dd
- COM DESFECHO + servico guincho -> 4971b50b
- COM DESFECHO + servico bateria -> cea36de4
- COM DESFECHO + servico pneu -> d6b1d83f
- cobertura de servico (sem desfecho): encanador -> b60d9359

**`allianz-residencial.jsonl`**
- COM DESFECHO + servico maquina_de_lavar -> 7ac3c101
- COM DESFECHO + servico encanador -> 0b244572
- COM DESFECHO + servico ?limpeza -> 987572a4
- COM DESFECHO + servico ?limpeza de caixa d'agua -> bb6e16d4
- COM DESFECHO + servico ?pet assistance -> bb97ea04
- COM DESFECHO + servico ?consulta veterinaria -> c58a171a

**`azul-auto.jsonl`**
- COM DESFECHO + servico guincho -> b012d3cd
- COM DESFECHO + servico bateria -> 4c821851
- COM DESFECHO + servico ?tecnico -> d70ced75
- diversidade (jaccard max 0.31) -> 2f0cd86a
- diversidade (jaccard max 0.47) -> fdec3edf

**`bradesco-auto.jsonl`**
- COM DESFECHO + servico (tronco) -> bc2cfead
- COM DESFECHO + servico acidente -> 72af1ae1
- diversidade (jaccard max 0.03) -> 9daeeccb
- diversidade (jaccard max 0.09) -> d557d3c7
- diversidade (jaccard max 0.17) -> 8f7f1d68

**`hdi-auto.jsonl`**
- COM DESFECHO + servico guincho -> 3dc92fcf
- COM DESFECHO + servico chaveiro -> 697abd09
- COM DESFECHO + servico socorro_mecanico -> 71caf82f
- COM DESFECHO + servico (tronco) -> e476dc68
- COM DESFECHO + servico pneu -> 886066e5

**`hdi-residencial.jsonl`**
- COM DESFECHO + servico encanador -> 26c0546f
- cobertura de servico (sem desfecho): eletricista -> 13379965
- cobertura de servico (sem desfecho): chaveiro -> 0a7c24ef
- diversidade (jaccard max 0.06) -> a1ba53b9
- diversidade (jaccard max 0.39) -> 1c8d0849

**`mapfre-auto.jsonl`**
- cobertura de servico (sem desfecho): carro_reserva -> a68aa770
- diversidade (jaccard max 0.00) -> 9fae42e2
- diversidade (jaccard max 0.00) -> f6f2ec11
- diversidade (jaccard max 0.22) -> 1684d4a8
- diversidade (jaccard max 0.35) -> d857d4de

**`porto-auto.jsonl`**
- COM DESFECHO + servico guincho -> d6f1f8d3
- COM DESFECHO + servico bateria -> e3b1561f
- COM DESFECHO + servico chaveiro -> d0d64bfc
- COM DESFECHO + servico ?tecnico -> e5318468
- cobertura de servico (sem desfecho): vidros -> 0c1e8e3e

**`porto-residencial.jsonl`**
- cobertura de servico (sem desfecho): eletrodomesticos -> 3854b4a2
- cobertura de servico (sem desfecho): encanador -> 5bcf0792
- cobertura de servico (sem desfecho): chaveiro -> 565cb39a
- diversidade (jaccard max 0.06) -> 897c42ff
- diversidade (jaccard max 0.09) -> 0e97bfa8

**`tokio-auto.jsonl`**
- COM DESFECHO + servico carro_reserva -> c1a67b4a
- COM DESFECHO + servico guincho -> d99a47a1
- COM DESFECHO + servico (tronco) -> 641420c8
- diversidade (jaccard max 0.36) -> fa8127ef
- diversidade (jaccard max 0.55) -> ca52ff75

**`tokio-condominio.jsonl`**
- diversidade (jaccard max 0.00) -> cd4b5ba7
- diversidade (jaccard max 0.14) -> c99dd4bb

**`tokio-residencial.jsonl`**
- diversidade (jaccard max 0.00) -> 66c9dd9b
- diversidade (jaccard max 0.69) -> 8d9b8672
- diversidade (jaccard max 0.73) -> f8b83a35
- diversidade (jaccard max 0.82) -> e0383feb

**`yelum-auto.jsonl`**
- COM DESFECHO + servico guincho -> a1c18e1c
- COM DESFECHO + servico socorro_mecanico -> 935c4076
- COM DESFECHO + servico (tronco) -> e6a07317
- COM DESFECHO + servico pneu -> 8a6040a7
- cobertura de servico (sem desfecho): carro_reserva -> e8efabc0

**`yelum-residencial.jsonl`**
- COM DESFECHO + servico encanador -> 6376f868
- COM DESFECHO + servico eletricista -> 9cb09e20
- cobertura de servico (sem desfecho): eletrodomesticos -> bb573c0a
- diversidade (jaccard max 0.00) -> 70571f37
- diversidade (jaccard max 0.13) -> 81c8ba13

**`zurich-auto.jsonl`**
- COM DESFECHO + servico guincho -> 8e5fb8c0
- COM DESFECHO + servico (tronco) -> 963f4097
- diversidade (jaccard max 0.03) -> e1349860
- diversidade (jaccard max 0.04) -> 4118ba36
- diversidade (jaccard max 0.08) -> d5ce1862

## Linhas RECUSADAS — sujeira que sobrou depois da máscara

_nenhuma_

## Contagens por seguradora

| seguradora | ORFAO_sessao | SESSAO_TODA_HUMANA | dedup | nivel:- | nivel:colisao | nivel:nivel-1-resposta | nivel:nivel-2-texto | nivel:sem-escolha-de-ramo | ramo:ambos | ramo:auto | ramo:condominio | ramo:indefinido | ramo:residencial | ramo:sem_escolha | senha_preservada | servico:indefinido | servico:nivel | vocativo_mascarado | zona:HUMANO | zona:URA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alfa | 0 | 0 | 30 | 1 | 0 | 0 | 8 | 0 | 0 | 8 | 0 | 1 | 0 | 0 | 3 | 3 | 5 | 0 | 0 | 151 |
| allianz | 1 | 5 | 1382 | 13 | 1 | 114 | 7 | 0 | 1 | 40 | 0 | 13 | 81 | 0 | 43 | 41 | 80 | 0 | 3791 | 3317 |
| azul | 0 | 0 | 68 | 3 | 0 | 0 | 11 | 5 | 0 | 11 | 0 | 3 | 0 | 5 | 0 | 0 | 11 | 10 | 22 | 450 |
| bradesco | 0 | 0 | 12 | 10 | 0 | 0 | 12 | 0 | 0 | 12 | 0 | 10 | 0 | 0 | 1 | 11 | 1 | 0 | 0 | 182 |
| hdi | 1 | 0 | 229 | 6 | 1 | 8 | 28 | 0 | 1 | 28 | 0 | 6 | 8 | 0 | 29 | 13 | 23 | 22 | 405 | 1165 |
| mapfre | 1 | 0 | 19 | 6 | 0 | 0 | 7 | 0 | 0 | 7 | 0 | 6 | 0 | 0 | 0 | 6 | 1 | 0 | 38 | 101 |
| porto | 1 | 1 | 520 | 52 | 0 | 29 | 40 | 15 | 0 | 60 | 0 | 52 | 9 | 15 | 0 | 34 | 35 | 39 | 368 | 1755 |
| tokio | 1 | 0 | 94 | 33 | 0 | 0 | 13 | 0 | 0 | 7 | 2 | 33 | 4 | 0 | 7 | 8 | 5 | 0 | 0 | 223 |
| yelum | 0 | 0 | 441 | 34 | 0 | 32 | 33 | 1 | 0 | 56 | 0 | 34 | 9 | 1 | 49 | 19 | 46 | 30 | 403 | 2014 |
| zurich | 1 | 0 | 70 | 4 | 0 | 0 | 10 | 0 | 0 | 10 | 0 | 4 | 0 | 0 | 4 | 9 | 1 | 0 | 39 | 384 |

## Avisos

- SESSAO_TODA_HUMANA allianz/44ff2017: 'ajudo em algo mais'
- SESSAO_TODA_HUMANA allianz/d2e3174b: 'ajudo em algo mais'
- SESSAO_TODA_HUMANA allianz/efa74707: 'assistencia 24 horas, permanece a disposicao'
- SESSAO_TODA_HUMANA allianz/b6e9961b: 'assistencia 24 horas, permanece a disposicao'
- PADRAO_DE_CARDAPIO allianz/b8df5a82: colisao:auto+residencial
- SESSAO_TODA_HUMANA allianz/309e1e5c: 'assistencia 24 horas, permanece a disposicao'
- PADRAO_DE_CARDAPIO hdi/e0b0c73d: colisao:auto+residencial
- SESSAO_TODA_HUMANA porto/4830574a: 'consultora de relacionamento'

## Vocativos

📊 esqueletos com ≥3 cabeças distintas (= DADO, mascarado): **7** · com exatamente 2 (= `NOME_DUVIDOSO`, **não** mascarado automaticamente, fica para leitura humana): **8**

