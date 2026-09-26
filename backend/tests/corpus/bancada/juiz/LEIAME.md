# Bancada · juiz — corpus v4

> SPEC-116 U12 · gerado em 23/09/2026 · v4 em 26/09/2026 (SPEC-117 F4a) ·
> 3 casos (3 N1 · 0 N2) · 0 críticos ·
> 0 com falha injetada · 0 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
BLOCKED — o motor existe (evals/juiz_llm.py:julgar_com_llm(llm=), consertado na F3b)

## De onde veio o texto
—

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
ESQUELETO: os 3 casos não têm OURO (saída, critério, veredito esperado). Não se inventa oráculo: entra na v2 com casos de concordância com veredito humano.

## Como rodar
```
cd backend
python scripts/bancada.py --papel juiz --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
