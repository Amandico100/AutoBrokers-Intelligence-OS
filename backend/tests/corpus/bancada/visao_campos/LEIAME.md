# Bancada · visao_campos — corpus v4 (papel novo)

> SPEC-124 F2 · gerado em 01/10/2026 · 10 casos (10 N1 · 0 N2) · 7 críticos.
> 📊 contagem medida no arquivo `casos.jsonl` (`python -c "import json;print(sum(1 for l in open('casos.jsonl',encoding='utf-8') if l.strip()))"`).

## O que mede
A leitura de documento por CAMPO — "parece bom" não vale. Cada caso tem o gabarito dos 12 campos do
esquema (`app/services/evals/bancada.py:CAMPOS_DA_VISAO`; `null` = o documento não tem) e o juiz
(`veredito_dos_campos`) compara normalizado: CPF/apólice só dígitos, placa sem traço, datas ISO,
valores em centavos, nome sem acento/caixa, coberturas por nome compatível E LMI igual. Campo que o
documento não tem e o modelo preencheu é **inventou** — erro.

## O motor
`app/services/evals/bancada.py:motor_visao_campos` — o braço da ROTA `visao` (resolvedor + fábrica do
produto, ledger `service_type='bancada'`, `details.papel='visao'`) recebe a imagem no MESMO formato de
`vision_service.describe_image` e a instrução FIXA `INSTRUCAO_DE_CAMPOS`, igual para todo braço (o
produto só descreve; não há prompt de extração a reusar).

## De onde vieram os documentos
10 imagens SINTÉTICAS (`gerar_imagens.py`, PIL): apólice auto (2 layouts), apólice residencial, CNH,
CRLV, orçamento de oficina, boleto, foto de para-brisa trincado com a placa visível, apólice auto
DEGRADADA (62 % da resolução, inclinada 3,5°, ruído, JPEG q38) e CNH FOTOGRAFADA (inclinada −7°, fundo
escuro, desfoque). Distratores de propósito: prêmio por cobertura ao lado do LMI, prêmio líquido e IOF
ao lado do total, franquia de vidros ao lado da básica, subtotal e desconto no orçamento, data do
documento ao lado do vencimento no boleto.

⛔ Sem PII: o texto deste diretório guarda só MARCADORES (`{{CPF:VA}}`, `{{NOME:VA}}`, `{{PLACA:VA}}`,
`{{APOLICE:VA}}`); `dubles.materializar` gera valores FICTÍCIOS DETERMINÍSTICOS (CPF com dígito
verificador, placa Mercosul) — os MESMOS que o gerador desenhou. O guarda
`tests/test_spec116_bancada_corpus.py::test_corpus_sem_pii` varre este diretório.

## O que falta (medido, não prometido)
Documento REAL mascarado: o acervo não tem imagem de apólice/CNH/CRLV sem PII e não há mascarador de
imagem. Sintético limpo é mais fácil que foto de celular de verdade — o número desta bancada é TETO.

## Como rodar
```
cd backend
python tests/corpus/bancada/visao_campos/gerar_imagens.py        # só se mudar um documento
python scripts/bancada.py --papel visao_campos --braco dublê:perfeito --braco dublê:burro --k 1 --saida <arq>.json
python scripts/bancada.py --papel visao_campos --braco openai:gpt-6-luna:medium --k 1 \
    --teto-provedor 0.45 --ledger-desde 2026-10-01T00:00:00+00:00 --ledger-papel visao --saida <arq>.json
python scripts/bancada.py --resumo-visao "<pasta>/visao_*.json"
```
