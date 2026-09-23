# Bancada · chat_principal — corpus v2

> SPEC-116 U12 · gerado em 23/09/2026 · 38 casos (30 N1 · 8 N2) · 23 críticos ·
> 3 com falha injetada · 2 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
create_agent_graph (papel core) → agent_node · N2 com tool_node REAL sobre dublês

## De onde veio o texto
falas REAIS do corretor no chat web (296 no acervo) + perguntas_do_chat/2026-09-09_10.json; pedido de rotina SINTÉTICO (o acervo não tem um completo)

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
casos de relatório executivo/propor_metrica/avaliar_automacao ainda não cobertos.

## Como rodar
```
cd backend
python scripts/bancada.py --papel chat_principal --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
