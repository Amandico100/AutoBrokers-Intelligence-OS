# Bancada · portal_decisao — corpus v1

> SPEC-116 U12 · gerado em 23/09/2026 · 16 casos (16 N1 · 0 N2) · 16 críticos ·
> 1 com falha injetada · 0 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
portal_worker/adaptive.py:decide_next_action(chamar_modelo=) — o pedido que o PRODUTO monta (rota portal_decisao) vai ao braço (bancada.chamador_do_braco); o ledger do portal não é escrito

## De onde veio o texto
portal_jobs.evidence (debug_dom.text + adaptive_steps, SELECT 23/09) + as telas dos testes test_o_protocolo_volta_para_o_segurado / test_o_portal_deixa_prova_do_sucesso; mascarado

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
o caso falha-500 sai BLOCKED_BY_INFRA: desde a F3b erro do provedor vira ask_human (needs_human), sem trocar de modelo — falha de infra, fora do pass@1. O mesmo caso sem a falha é a linha de controle (test_controle_o_mesmo_caso_sem_a_falha_passa).

## Como rodar
```
cd backend
python scripts/bancada.py --papel portal_decisao --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
