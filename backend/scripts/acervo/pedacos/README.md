# Os pedaços do contrato — a base de prova do acervo

📊 6.797 pedaços de 23 documentos, das três seguradoras conferidas na SUSEP.
2,0 MB comprimidos (37 MB abertos).

## Por que isto está versionado

Até 11/08/2026 estes arquivos existiam **só em `%TEMP%`**. Todas as medições
publicadas sobre o acervo — a taxa de erro de ancoragem, a contagem de cartas
sem lastro, a comparação de corte entre lotes, os 45 erros confirmados por
auditores — saíram deles.

Um `git clean` ou uma limpeza de temporários apagaria a única cópia, e nenhuma
das medições poderia ser refeita nem contestada por outra pessoa. Só as cartas
de saída estavam commitadas — o que é o mesmo que guardar a resposta e jogar
fora a prova.

> **Número medido sem base de prova preservada vira folclore no lote seguinte.**

## O que tem dentro

Uma linha por pedaço, JSON:

| campo | o que é |
|---|---|
| `unit_id` | `norm-<document_id>-v<n>#<indice>` — o endereço do trecho |
| `caminho` | a trilha de títulos até ele (`CONDIÇÕES GERAIS > 11. FORMA…`) |
| `corpo` | o texto do contrato, como o destilador leu |
| `faceta` | a classificação do trecho |

O `unit_id` é a mesma chave que a carta guarda em `source_unit_id`, então dá
para cruzar carta ↔ contrato sem consultar banco nenhum.

## Como usar

```python
import gzip, json

with gzip.open("backend/scripts/acervo/pedacos/porto_pedacos.jsonl.gz",
               "rt", encoding="utf-8") as f:
    pedacos = {j["unit_id"]: j for j in map(json.loads, f)}

# a carta diz de onde veio; aqui se confere o que ela diz
print(pedacos["norm-....-v2#0013"]["corpo"])
```

⚠️ **Leia o `corpo` INTEIRO.** Já quase corrigimos uma carta correta por ter
lido só os primeiros 800 caracteres — a prova que faltava estava no fim.

## Como regerar, se um dia precisar

Não é para editar. Sai do coletor, a partir do PDF vigente:

```
cd /app && python scripts/acervo/coletar_seguradora.py --seguradora porto --so-exportar
```

Se o PDF na SUSEP mudou, o novo pacote **não** vai bater com este — e é isso
que se quer: este arquivo é o retrato do que foi lido quando as cartas foram
escritas, não o texto de hoje.
