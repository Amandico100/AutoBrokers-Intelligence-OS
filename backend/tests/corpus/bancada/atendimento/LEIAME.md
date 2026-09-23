# Bancada · atendimento — corpus v3

> SPEC-116 U12 · gerado em 23/09/2026 · 40 casos (30 N1 · 10 N2) · 36 críticos ·
> 4 com falha injetada · 2 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
app/agents/graph.py:create_agent_graph (papel attendance) → nodes.agent_node (N1: UMA volta, interrupt_before=tools) · N2: grafo inteiro com tool_node REAL sobre dublês

## De onde veio o texto
falas REAIS de segurado (messages, canal whatsapp, 23/09/2026) mascaradas à mão; 2 casos de risco SINTÉTICOS (o acervo não tem fala de risco do segurado) — marcados no campo origem

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
N2 com rajadas reais: o corpus rajadas_reais.jsonl guarda só TRAÇOS (sem texto); as trajetórias usam falas reais de outras conversas. Retomada/handoff com conversa real inteira fica para a v2.

## Como rodar
```
cd backend
python scripts/bancada.py --papel atendimento --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
