# R1B.1 - Canonical Runtime Hardening and Evidence Safety

> Data: 2026-06-24  
> Status: implementado para validacao apos deploy  
> Escopo: endurecer R1B sem iniciar R1C.

## 1. Objetivo

Consolidar o R1B antes do aceite produtivo, removendo duplicacao de codigo, unificando a resolucao de conexao InfoCap no backend e impedindo que classificacao de produto/ramo gere falsa evidencia de cobertura.

## 2. Arquivos alterados

- `backend/app/api/infocap_connector.py`
- `backend/app/agents/tools/infocap_tool.py`
- `backend/tests/test_infocap_contract_capture.py`
- `app/api/attendance/connectors/infocap/probe/route.ts`
- `package.json`
- `docs/canon/SPEC-015A-canonical-infocap-policy-read-adapter.md`
- `docs/canon/PROGRAM-RECOVERY-F0-F2.md`
- `docs/canon/GOLDEN-TEST-MATRIX-INFOCAP.md`
- `docs/canon/design/2026-06-codex/R1B.1-runtime-hardening-report.md`

Removidos por duplicacao de autoridade:

- `lib/attendance/connectors/infocap-connection-resolution.ts`
- `scripts/infocap-connection-resolution.test.mjs`

## 3. Componentes reutilizados

- `tenant_connections`
- Vault / `encrypted_secret_ref`
- endpoint Python existente `POST /attendance/connectors/infocap/probe`
- endpoints Python existentes `infocap_lookup` e `infocap_policy_detail`
- tool existente `InfocapPolicyLookupTool`
- Contract Capture Gate existente no Portal Admin

Nenhum endpoint, conector, runtime, RAG, parser, storage, tabela ou migration paralelo foi criado.

## 4. Resolucao canonica de conexao

A resolucao canonica ficou em `backend/app/api/infocap_connector.py`:

- `_resolve_infocap_connection_candidates`
- `_resolve_infocap_connection`
- `_connection_block_response`

Regra aplicada:

- pertence a empresa;
- template InfoCap;
- nao arquivada/inativa;
- status/saude operacional;
- Vault presente;
- base URL efetiva;
- uma elegivel = usa;
- zero elegiveis = `blocked_missing_credentials`;
- duas ou mais elegiveis = `ambiguous_connection`.

Consumidores:

- `infocap_lookup`
- `infocap_policy_detail`
- `infocap_probe`
- `InfocapPolicyLookupTool`, que nao escolhe mais conexao localmente.

A rota Next do probe agora autentica, resolve a empresa e delega a decisao de conexao ao backend.

## 5. Duplicacoes consolidadas

Restou uma unica definicao canonica de:

- `_build_evidence_pack`
- `_coverage_sections`
- `InfocapPolicyLookupTool._summarize`
- `InfocapPolicyLookupTool._summarize_detail`

O helper local `_find_conn_id` foi removido da tool.

## 6. Seguranca de evidencia

Produto, ramo, `ramo_abrev`, descricao geral e tipo de documento nao geram:

- `coverage_sections`;
- assistencia positiva;
- eletricista;
- conclusao de cobertura.

Cobertura/assistencia so pode ser positiva quando vier de item, cobertura, clausula ou assistencia estruturada com label humano comprovado.

`tabela_itens` permanece campo desconhecido/classificavel.

## 7. PolicyLocator

Referencia tecnica preferencial:

```text
infocap:<codfil>:<nosnum>
```

Detalhe direto por `nosnum` simples sem `codfil` validado retorna limite de fonte e pede o locator retornado pela listagem. Isso evita chamada a `/documento` com `codfil` padrao.

## 8. R1C nao executada

Nao foi baixado, acessado, validado ou processado documento oficial. `official_document_source_available` continua apenas uma flag segura para a futura R1C.

## 9. Validacao executada

- `python backend/tests/test_infocap_contract_capture.py`
- `python -m py_compile backend/app/api/infocap_connector.py backend/app/agents/tools/infocap_tool.py backend/tests/test_infocap_contract_capture.py`

Validacoes adicionais de Node/typecheck devem ser registradas no fechamento do batch.

## 10. Aceite apos deploy

R1B so sera aceita depois de teste real no Chat Principal:

1. Buscar segurado por CPF e validar CPF canonico de `/cliente`.
2. Buscar o mesmo segurado por nome e validar mesma pessoa/apolices.
3. Pedir detalhe sem referencia quando houver varias apolices e confirmar lista de opcoes.
4. Detalhar usando `policy_locator_ref`.
5. Perguntar cobertura e confirmar ausencia honesta quando nao houver item estruturado.
6. Confirmar que produto/ramo nao gera assistencia ou cobertura.

Somente depois desse aceite a R1C.0 pode validar a fonte oficial do documento.
