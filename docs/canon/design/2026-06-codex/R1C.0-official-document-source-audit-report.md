# R1C.0 - Official Policy Document Source Audit

> Data: 2026-06-25  
> Status: implementado para revisao antes de commit/deploy  
> Escopo: auditoria viva read-only da fonte oficial da apolice InfoCap.

## 1. Problema investigado

Os testes reais confirmaram que a cadeia InfoCap localiza cliente, catalogo e detalhe de apolice, mas o JSON de `/documento` nao trouxe `itens`, `coberturas`, `franquias`, `clausulas` ou `assistencias` para a apolice testada.

O mesmo envelope trouxe `acompanhamento.emissao.url_apolice`, indicando que a cobertura completa provavelmente esta no documento oficial da apolice. R1C.0 existe para descobrir se essa fonte e recuperavel e processavel sem iniciar a R1C produtiva.

## 2. Arquivos alterados

- `backend/app/api/infocap_connector.py`
- `app/api/attendance/connectors/infocap/probe/route.ts`
- `backend/tests/test_infocap_official_document_source_audit.py`
- `docs/canon/PROGRAM-RECOVERY-F0-F2.md`
- `docs/canon/SPEC-015A-canonical-infocap-policy-read-adapter.md`
- `docs/canon/GOLDEN-TEST-MATRIX-INFOCAP.md`
- `docs/canon/design/2026-06-codex/R1C.0-official-document-source-audit-report.md`

## 3. Componentes reutilizados

- Endpoint existente `POST /attendance/connectors/infocap/probe`.
- Resolucao canonica de conexao InfoCap via `tenant_connections + Vault`.
- Login InfoCap existente.
- Cadeia canonica de apolice ate `/documento`.
- `PolicyLocator(provider=infocap, codfil, nosnum)` interno.

Nenhum conector, runtime, endpoint, RAG, parser, storage, tabela, migration, agente ou ferramenta paralela foi criado.

## 4. Modo novo do probe

Modo:

```text
official_document_source_audit
```

Fluxo:

```text
tenant_connections + Vault
-> login InfoCap
-> cliente / catalogo / detalhe canonico
-> /documento por codfil + nosnum
-> acompanhamento.emissao.url_apolice
-> tentativa read-only controlada da fonte oficial
-> classificacao segura
```

O modo tambem aceita `policy_ref` tecnico interno quando necessario, mas a recomendacao operacional e informar CPF/nome no termo e o numero humano da apolice no campo de referencia.

## 5. Dados proibidos

O output nao pode conter:

- URL integral, query string ou hostname identificador;
- token, cookie, header Authorization, senha ou segredo;
- CPF/CNPJ, nome, endereco, telefone ou numero de apolice;
- `PolicyLocator`, `codfil`, `nosnum`, `codigo` ou `codcli`;
- conteudo do PDF, texto extraido, payload bruto ou preview.

O retorno pode conter apenas classes, booleanos, contagens, buckets, magic file, status HTTP seguro, nomes de chaves, hashes estruturais e blockers genericos.

## 6. Como rodar o diagnostico seguro

Atualizado em R1C.0.1: a execucao deve acontecer pelo card existente no Portal Admin, sem DevTools/Console.

1. Abrir Portal Admin -> Empresas -> corretora piloto -> Agentes.
2. Abrir Diagnostico & manutencao.
3. Abrir "Diagnosticar contrato InfoCap".
4. Em Modo, selecionar "Auditar fonte oficial da apolice".
5. Selecionar CPF ou Nome.
6. Informar o termo de teste.
7. Informar o numero humano da apolice no campo "Referencia da apolice".
8. Clicar em Executar.
9. Copiar de volta somente o bloco `source_audit` retornado.

## 7. Formato seguro esperado

```json
{
  "ok": true,
  "provider": "infocap",
  "mode": "official_document_source_audit",
  "status": "found",
  "candidate_count": 1,
  "document_count": 1,
  "detected_policy_fields": {
    "history_present": true,
    "installments_present": true
  },
  "source_audit": {
    "official_document_url_present": true,
    "official_document_source_kind": "policy_pdf",
    "retrieval_status": "retrieved",
    "auth_mode_required": "authorization_header",
    "redirect_count": 0,
    "final_origin_class": "infocap_same_origin",
    "content_type": "application/pdf",
    "content_disposition_present": true,
    "content_length_bucket": "1_to_10mb",
    "file_magic": "pdf",
    "pdf_encrypted": false,
    "pdf_page_count": 12,
    "text_layer_status": "present",
    "document_anchor_detection": {
      "coverage_anchor_present": true,
      "assistance_anchor_present": true,
      "deductible_anchor_present": true,
      "premium_anchor_present": true,
      "lmi_anchor_present": true,
      "policy_number_anchor_present": true
    },
    "content_hash_present": true,
    "source_fetch_safe_for_r1c": true,
    "source_fetch_blocker": [],
    "recommended_r1c_transport": "direct_authenticated_fetch"
  }
}
```

O exemplo acima e sintetico. O retorno real nao deve conter URL, nomes, CPF, numero de apolice, `codfil` ou `nosnum`.

## 8. Campos a confirmar no resultado real

- `retrieval_status`
- `auth_mode_required`
- `final_origin_class`
- `content_type`
- `file_magic`
- `pdf_encrypted`
- `pdf_page_count`
- `text_layer_status`
- `document_anchor_detection`
- `source_fetch_safe_for_r1c`
- `source_fetch_blocker`
- `recommended_r1c_transport`

## 9. R1C continua bloqueada

R1C produtiva ainda nao foi iniciada. Esta rodada nao baixa documento no Chat Principal, nao persiste arquivo, nao chama Docling, nao envia nada para MinIO/Qdrant/Supabase e nao cria cache.

R1C so deve comecar depois que o Founder trouxer o JSON estrutural real e a equipe decidir o transporte correto:

- `direct_authenticated_fetch`;
- `signed_url_fetch`;
- `session_cookie_fetch`;
- `portal_required`;
- `unavailable`.
