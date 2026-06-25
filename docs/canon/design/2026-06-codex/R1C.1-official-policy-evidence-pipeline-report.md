# R1C.1 - Official Policy Evidence Pipeline

> Data: 2026-06-25
> Status: implementado para validacao controlada apos deploy.
> Regra: sem runtime, conector, RAG, parser, storage, Vault, migration, endpoint ou agente paralelo.

## 1. Contexto validado

O R1C.0.1 foi executado em producao controlada pelo Portal Admin. O resultado informado pelo Founder comprovou:

- duas apolices com `url_apolice` retornando PDF oficial recuperavel por `signed_url_fetch`;
- PDF real, pequeno, nao criptografado, com camada de texto presente;
- nenhuma autenticacao adicional necessaria para essas URLs;
- uma apolice sem `url_apolice`/fonte documental automatica;
- o JSON `/documento` continua sem cobertura/franquia/assistencia estruturada para as apolices testadas.

Conclusao: a leitura de coberturas deve usar documento oficial sob demanda, com cache, quando a InfoCap estruturada for insuficiente.

## 2. Arquivos alterados

- `backend/app/api/infocap_connector.py`
- `backend/app/agents/tools/infocap_tool.py`
- `backend/app/agents/nodes.py`
- `backend/app/services/policy_document_evidence_service.py`
- `backend/app/services/document_service.py`
- `backend/app/services/ingestion_service.py`
- `backend/app/services/qdrant_service.py`
- `backend/app/services/search_service.py`
- `backend/app/services/langchain_service.py`
- `backend/tests/test_infocap_official_policy_evidence_pipeline.py`
- `backend/tests/test_infocap_official_document_source_audit.py`
- `backend/tests/test_infocap_policy_output_guard.py`
- `docs/canon/SPEC-015A-canonical-infocap-policy-read-adapter.md`
- `docs/canon/PROGRAM-RECOVERY-F0-F2.md`
- `docs/canon/GOLDEN-TEST-MATRIX-INFOCAP.md`

## 3. Estruturas reutilizadas

- Adapter InfoCap canonico existente.
- Resolucao de conexao por `tenant_connections + Vault`.
- Fetch seguro R1C.0.1, com SSRF/redirect/size guard.
- `DocumentService` existente.
- MinIO privado existente.
- Extracao direta de PDF ja existente no `DocumentService`.
- `SanitizationService`/Docling existente como fallback quando configurado.
- `IngestionService` existente.
- Qdrant existente.
- `SearchService` e `KnowledgeBaseTool` existentes, com filtro para impedir busca ampla de documento oficial.
- Policy Response Contract / output guard do Smith existente.

## 4. Sem schema novo

Nao foi criada migration.

O cache usa a tabela `documents` existente e o caminho privado MinIO existente. A vinculacao com a apolice usa metadata e nomes seguros derivados de:

```text
provider=infocap
policy_locator_hash
content_hash
document_type=official_policy_document
```

`codfil`, `nosnum`, URL assinada, token, cookie, Authorization e payload bruto nao sao persistidos.

## 5. Fluxo implementado

```text
Pergunta sobre cobertura/franquia/assistencia/clausula/LMI
        |
        v
InfoCap canonical adapter localiza PolicyLocator
        |
        v
/documento confirma dados operacionais e url_apolice
        |
        v
Cache por policy_locator_hash + content_hash
        |
        +-- hit  -> usa evidencia ja extraida
        |
        +-- miss -> signed_url_fetch seguro
                    -> DocumentService/MinIO privado
                    -> extracao direta por pagina
                    -> Docling existente somente se necessario
                    -> IngestionService/Qdrant
                    -> evidencia curta por pagina/trecho
```

## 6. Transporte e seguranca

- `signed_url_fetch` e tentado primeiro, sem Authorization/cookie.
- Authorization/cookie so podem ser enviados se o destino estiver no origin InfoCap validado.
- Redirect externo HTTPS remove credenciais.
- HTTP, localhost, loopback, rede privada, link-local, metadata endpoint e arquivo grande continuam bloqueados pelo fetch seguro.
- A URL oficial nunca e retornada ao chat, frontend, logs ou metadata persistida.

## 7. Evidencia gerada

Cada item de evidencia contem:

- `document_id`;
- `policy_locator_hash`;
- `page_number`;
- `chunk_id`;
- `evidence_type`;
- `evidence_text` curto;
- `source_document=official_policy_document`;
- `extraction_method`;
- `confidence`;
- `content_hash`;
- `conflict_status`.

O Core recebe evidencia completa permitida. Even so recebe DTO minimo quando houver `case_id`. Auxiliares continuam bloqueados sem capability propria.

## 8. Estados

Estados suportados:

```text
source_available
fetching
fetched
direct_extracting
docling_pending
parsed
evidence_ready
source_unavailable
source_fetch_failed
document_not_policy_evidence
low_confidence
conflict_requires_human
```

## 9. Limites assumidos

- Nao houve chamada real a InfoCap durante desenvolvimento local.
- Nao houve download real de apolice durante desenvolvimento local.
- O primeiro fetch real deve acontecer somente apos deploy, por pergunta do Chat Principal ou acao explicita futura.
- Docling fallback existe, mas so sera usado quando a extracao direta nao produzir evidencia e `DOCLING_SERVICE_URL` estiver configurado.
- Documentos oficiais ficam excluidos de busca ampla de conhecimento; devem ser recuperados por filtro de apolice.

## 10. Teste real apos deploy

Usar uma das apolices cujo R1C.0.1 retornou `retrieval_status=retrieved` e `file_magic=pdf`.

Perguntas:

```text
Detalhe todas as coberturas da apolice [numero humano].
Ela possui assistencia residencial?
Ela cobre eletricista?
Qual e a franquia?
Qual e o limite de cada cobertura?
Quais sao as exclusoes relevantes?
```

Resultado esperado:

- se houver evidencia no documento: resposta com cobertura/limite/franquia e fonte `Apolice oficial, pagina X`;
- se o documento nao trouxer evidencia suficiente: resposta honesta com `document_not_policy_evidence` ou `low_confidence`, sem cobertura inventada;
- segunda consulta da mesma apolice deve usar cache, sem novo fetch do PDF.
