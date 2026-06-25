# R1B.2 - Policy Query Contract and Smith Output Guard

> Data: 2026-06-25  
> Status: implementado para validacao apos deploy  
> Escopo: fechar consulta por numero humano e resposta operacional do Chat Principal.

## 1. Problema corrigido

Os testes reais mostraram que o Chat Principal acessava a InfoCap, mas falhava em duas bordas:

- numero humano de apolice era tratado como `policy_ref` tecnico e recusado por falta de `codfil + nosnum`;
- respostas operacionais da tool podiam ser reescritas pela LLM, apagando opcoes de ambiguidade ou transformando ausencia estruturada em "erro tecnico".

## 2. Implementacao

### Consulta por numero humano

`InfocapPolicyLookupTool` agora aceita:

- `document`;
- `name`;
- `policy_number`;
- `policy_ref`.

Fluxo canonico:

```text
policy_number
-> /documentos?codfil&texto=<numero>
-> match exato por numapo ou nosnum normalizado
-> PolicyLocator(provider=infocap, codfil, nosnum)
-> /documento?codfil=<codfil>&nosnum=<nosnum>
-> evidence pack existente
```

Se a LLM ainda enviar numero humano em `policy_ref`, a tool trata como `policy_number` quando o valor nao tem `codfil` tecnico.

### Output guard no Smith

O guard ficou em `backend/app/agents/nodes.py`:

- `_guard_infocap_policy_final_response`;
- `should_continue_after_tools`.

O `tool_node` captura `policy_response_contract` da InfoCap e grava `final_response`. O grafo passa a rotear `tools -> end/log` quando existe contrato operacional de InfoCap, evitando reescrita livre pela LLM.

Isso nao e runtime paralelo. E uma regra deterministica dentro do LangGraph existente.

## 3. Segurança de apresentacao

- numero `0`, vazio, nulo ou placeholder nao e exibido como numero valido;
- opcoes de ambiguidade usam numero humano, seguradora, produto/ramo, vigencia e status;
- `policy_locator_ref` fica interno/debug, nao requisito operacional do corretor;
- `structured_coverage_absent` vira ausencia honesta, nao erro tecnico;
- `document_evidence_required` pode mencionar futura fonte documental oficial, sem dizer que PDF foi lido.

## 4. R1C nao executada

Nao houve:

- download de PDF;
- acesso ou validacao de documento oficial;
- Docling/OCR;
- MinIO/Qdrant/SearchService;
- schema/migration;
- endpoint, conector, runtime, RAG, parser, storage, agente ou ferramenta paralela.

## 5. Testes

Coberto por:

- `backend/tests/test_infocap_contract_capture.py`
- `backend/tests/test_infocap_policy_output_guard.py`

Os testes validam `policy_number`, ambiguidade, numero invalido, opcoes deterministicas, output guard e ausencia honesta.

## 6. Aceite apos deploy

Testes manuais do Founder:

1. "Quais sao as apolices ativas do Rafael Lacau da Silveira?"
2. "Detalhe a apolice 202623140269972."
3. "Quais sao as coberturas dessa apolice?"
4. "Ela tem eletricista?"
5. "Ela tem assistencia residencial?"
6. "Ela tem franquia?"
7. "Ela tem premio ou parcelas?"
8. "Detalhe as coberturas do Rafael" sem apontar apolice.

Esperado:

- o Chat pede escolha quando houver varias apolices;
- entende numero humano da apolice;
- nao mostra "Numero: 0";
- nao transforma ausencia estruturada em erro tecnico;
- nao inventa cobertura;
- informa que a fonte documental oficial fica para R1C quando a InfoCap nao traz cobertura estruturada.
