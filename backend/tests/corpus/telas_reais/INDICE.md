# Corpus de telas reais — ÍNDICE

> Gerado em **2026-08-23T15:19:04+00:00** · commit `f156c8c`
> 📊 `marcas_de_corretora()` = **8** (o CONTROLE da SPEC-084 §2.5.1.3 — se fosse 0, a geração teria rodado sem banco e o corpus **não estaria mascarado**)

🔴 Este arquivo existe porque a SPEC-083 §7 proíbe pular em silêncio: *"truncar calado lê-se como 'cobrimos tudo'"*.

## Os arquivos

| arquivo | linhas | KB | sessões no corpus | candidatas | teto | subserviços | c/ desfecho |
|---|---:|---:|---|---:|---:|---:|---:|
| `bradesco-auto.jsonl` | 159 | 56 | 72af1ae1 2c05415b bc2cfead 0d5284f3 a10d095d 8f7f1d68 d557d3c7 9daeeccb b4e4ef95 100ef852 | 12 | 5 | 4 | 4 |

## Por que cada sessão entrou

**`bradesco-auto.jsonl`**
- [acidente] COM DESFECHO -> 72af1ae1
- [bateria] diversidade (jaccard 0.00) -> 2c05415b
- [guincho] COM DESFECHO -> bc2cfead
- [guincho] COM DESFECHO -> 0d5284f3
- [guincho] COM DESFECHO -> a10d095d
- [(tronco)] diversidade (jaccard 0.00) -> 8f7f1d68
- [(tronco)] diversidade (jaccard 0.09) -> d557d3c7
- [(tronco)] diversidade (jaccard 0.17) -> 9daeeccb
- [(tronco)] diversidade (jaccard 0.33) -> b4e4ef95
- [(tronco)] diversidade (jaccard 0.33) -> 100ef852
- [(tronco)] AVISO: 2 sessao(oes) FORA do corpus pelo teto de 5 por rota

## Linhas RECUSADAS — sujeira que sobrou depois da máscara

_nenhuma_

## Contagens por seguradora

| seguradora | dedup | nivel:- | nivel:nivel-2-texto | ramo:auto | ramo:indefinido | servico:indefinido | servico:nivel | zona:URA |
|---|---|---|---|---|---|---|---|---|
| bradesco | 12 | 10 | 12 | 12 | 10 | 7 | 5 | 182 |

## Vocativos

📊 esqueletos com ≥3 cabeças distintas (= DADO, mascarado): **7** · com exatamente 2 (= `NOME_DUVIDOSO`, **não** mascarado automaticamente, fica para leitura humana): **8**

