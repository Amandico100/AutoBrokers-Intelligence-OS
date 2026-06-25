# R1B - Canonical InfoCap Policy Read Adapter

> Data: 2026-06-24  
> Status: implementado para revisao/deploy  
> Escopo: corrigir leitura canonica InfoCap dentro do conector e da tool existentes.

## 1. Resumo

R1B substitui o caminho normal de leitura InfoCap por um contrato canonico dentro de `backend/app/api/infocap_connector.py`, sem criar runtime, endpoint, conector, RAG, parser, storage, tabela ou migration paralela.

O Chat Principal continua usando Smith/LangGraph e `InfocapPolicyLookupTool`. A diferenca e que a tool agora recebe DTO canonico do adapter existente.

## 2. Arquivos alterados

- `backend/app/api/infocap_connector.py`
- `backend/app/agents/tools/infocap_tool.py`
- `backend/tests/test_infocap_contract_capture.py`
- `docs/canon/SPEC-015A-canonical-infocap-policy-read-adapter.md`
- `docs/canon/PROGRAM-RECOVERY-F0-F2.md`
- `docs/canon/GOLDEN-TEST-MATRIX-INFOCAP.md`
- `docs/canon/design/2026-06-codex/R1B-canonical-infocap-policy-read-report.md`

## 3. Componentes reutilizados

- `tenant_connections`
- Vault / `encrypted_secret_ref`
- endpoint existente `POST /attendance/connectors/infocap/lookup`
- endpoint existente `POST /attendance/connectors/infocap/policy-detail`
- endpoint existente `POST /attendance/connectors/infocap/probe`
- `InfocapPolicyLookupTool`
- Capability existente `operational.infocap.policy_lookup.read`

## 4. Fluxo canonico aplicado

```text
CPF ou nome
-> /cliente_cpf ou /lista_clientes
-> /cliente?codfil&codigo
-> cpf_cnpj canonico
-> /cliente_ligacoes?codigo
-> documentos.documentos[]
-> PolicyLocator(provider=infocap, codfil, nosnum)
-> /documento?codfil&nosnum
-> Evidence Pack canonico
```

## 5. Correcoes principais

- Busca por CPF e nome chama `/cliente` antes de usar identidade final.
- CPF canonico vem de `cpf_cnpj` do detalhe do cliente.
- `codigo` e `codcli` nao viram `policy_ref`.
- `numapo` e pesquisavel/exibivel e pode resolver para `nosnum`.
- Detalhe usa `codfil + nosnum`.
- Multiplas apolices retornam `ambiguous_policy`, sem selecao silenciosa.
- Envelope de `/documento` nao e reduzido prematuramente para `documento[0]`.
- `documento`, `historico`, `acompanhamento`, `parcelas` e `prod_docs` entram como metadados estruturais seguros.
- `parcelas` sao normalizadas com `source_fields`.
- Campos financeiros do provider ficam com `provider_field` e `semantic_status=provider_field_unclassified`.
- `tabela_itens` e campo desconhecido/classificavel, nao cobertura.
- Codigos curtos como `P`, `A` e `C` nao viram cobertura.
- Ausencia de itens estruturados retorna `structured_coverage_absent`.
- `url_apolice` vira somente `official_document_source_available=true`; a URL nao e retornada.

## 6. Nao executado nesta fase

- R1C nao foi executada.
- Nenhum PDF/documento oficial foi baixado.
- Nenhum Docling/OCR foi chamado.
- Nenhum MinIO/Qdrant/SearchService foi alterado.
- Nenhum prompt, `graph.py` ou Capability Registry foi alterado.
- Nenhum provider real foi chamado durante o desenvolvimento.

## 7. Feature flag

Feature flag temporaria:

```text
INFOCAP_CANONICAL_POLICY_READ
```

Valor padrao planejado: `true`.

Para rollback temporario, usar valor equivalente a off:

```text
false
0
off
legacy
```

A flag fica dentro do adapter existente. Ela nao cria segundo conector, segunda rota, segunda tool ou runtime paralelo.

## 8. Testes executados nesta fase

- `python backend/tests/test_infocap_contract_capture.py`
- `python -m py_compile backend/app/api/infocap_connector.py backend/app/agents/tools/infocap_tool.py`

O harness offline cobre os casos R1B criticos: CPF canonico, `PolicyLocator`, `numapo -> nosnum`, `P` nao cobertura, envelope seguro, parcelas, financeiros, ausencia estruturada e fonte oficial como flag.

## 9. Build local

O build local Next em Windows ja estava registrado como pendencia de ambiente por travar em `compile/minify-js`. R1B nao alterou essa frente. A validacao de build produtivo deve continuar sendo feita pelo EasyPanel/ambiente de deploy.

## 10. Testes do Founder apos deploy

1. No Chat Principal, buscar o segurado de teste por CPF.
2. Confirmar que o CPF retornado corresponde ao `cpf_cnpj` canonico do detalhe do cliente.
3. Buscar o mesmo segurado por nome.
4. Confirmar que retorna a mesma pessoa e as mesmas apolices.
5. Pedir detalhes de uma apolice especifica usando o `policy_ref` retornado.
6. Conferir seguradora, ramo/produto, vigencia, status, numero e parcelas.
7. Perguntar sobre cobertura.
8. Confirmar que o Core nao inventa cobertura: deve informar ausencia estruturada na InfoCap e registrar que existe fonte documental oficial quando disponivel.

## 11. Bloqueio da proxima etapa

R1C so deve comecar apos validar R1B em deploy.

R1C deve implementar:

- fetch do documento oficial somente quando necessario;
- cache por `company_id + PolicyLocator + hash/ETag/versionamento`;
- DocumentService + MinIO existentes;
- Docling/OCR apenas quando necessario;
- evidencia por pagina/trecho;
- nenhuma leitura repetida do mesmo documento;
- nenhum RAG/parser/storage paralelo.
