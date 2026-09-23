# Bancada · cobranca — corpus v3

> SPEC-116 U12 · gerado em 23/09/2026 · 10 casos (10 N1 · 0 N2) · 5 críticos ·
> 0 com falha injetada · 0 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
create_agent_graph (papel attendance) → agent_node, com a mensagem de cobrança no histórico

## De onde veio o texto
retornos_de_cobranca.json (frases SINTÉTICAS por declaração do próprio arquivo) + cobranca_acervo anonimizado; o classificador de retorno do produto é REGEX (billing_replies.classificar_retorno) — o LLM só entra na conversa que segue

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
N2 (cobrança → 2ª via → pagamento) fica para a v2.

## Como rodar
```
cd backend
python scripts/bancada.py --papel cobranca --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
