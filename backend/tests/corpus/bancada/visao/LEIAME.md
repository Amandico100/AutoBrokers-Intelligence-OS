# Bancada · visao — corpus v2

> SPEC-116 U12 · gerado em 23/09/2026 · 10 casos (10 N1 · 0 N2) · 2 críticos ·
> 0 com falha injetada · 0 com segundo tenant. 📊 contagem medida no arquivo `casos.jsonl`.

## O motor que estes casos rodam
app/services/vision_service.py:describe_image(llm=) — o braço entra pelo ponto de injeção da F3a

## De onde veio o texto
10 imagens SINTÉTICAS geradas por PIL (texto legível, nenhum dado real) em visao/imagens/

⛔ Sem PII: CPF, CNPJ, telefone, placa, e-mail, apólice, nome de pessoa e de corretora entram como
MARCADOR (`{{CPF:A1}}`, `{{NOME:N1}}`, `{{CORRETORA:A}}`…) e o carregador
(`app/services/evals/dubles.py:materializar`) gera valores SINTÉTICOS determinísticos na hora.
O guarda `tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
fotos reais mascaradas e PDFs: o acervo não tem imagem de segurado sem PII.

## Como rodar
```
cd backend
python scripts/bancada.py --papel visao --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
```
Formato de cada linha: `chave, versao, papel, nivel, critico, tenant, entrada, ferramentas_disponiveis,
efeitos_permitidos, efeitos_proibidos, oraculo, falhas_injetadas, orcamento_turnos, origem`.
Mudou um caso? Suba `versao` no `MANIFESTO.json` — versão congelada na Eval Fabric não recebe caso novo.
