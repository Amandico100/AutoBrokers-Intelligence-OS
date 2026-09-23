# Bancada · memoria — corpus v2

> SPEC-116 U12 · gerado em 23/09/2026 · 15 casos (15 N1 · 0 N2) · 0 críticos ·
> 0 com falha injetada · 0 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
app/services/memory_service.py:MemoryService.extract_user_facts_async(llm=)

## De onde veio o texto
falas REAIS do chat web e do WhatsApp (23/09/2026), mascaradas

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
resumo de sessão (generate_session_summary_async) e consolidação ainda sem casos.

## Como rodar
```
cd backend
python scripts/bancada.py --papel memoria --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
