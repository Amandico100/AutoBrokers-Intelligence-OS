# R1C.0.1 - Security and Admin Audit UX

> Data: 2026-06-25  
> Status: pronto para commit/deploy controlado  
> Escopo: hardening do diagnostico `official_document_source_audit` e UX no Portal Admin existente.

## 1. Objetivo

Finalizar o R1C.0 para uma unica execucao real controlada, sem iniciar R1C produtivo.

Esta etapa nao baixa PDF no Chat Principal, nao chama Docling, nao persiste documento, nao cria cache e nao altera o runtime Smith/LangGraph.

## 2. Arquivos alterados

- `backend/app/api/infocap_connector.py`
- `app/api/attendance/connectors/infocap/probe/route.ts`
- `app/admin/companies/[companyId]/agents/page.tsx`
- `backend/tests/test_infocap_official_document_source_audit.py`
- `docs/canon/PROGRAM-RECOVERY-F0-F2.md`
- `docs/canon/SPEC-015A-canonical-infocap-policy-read-adapter.md`
- `docs/canon/GOLDEN-TEST-MATRIX-INFOCAP.md`
- `docs/canon/design/2026-06-codex/R1C.0-official-document-source-audit-report.md`
- `docs/canon/design/2026-06-codex/R1C.0.1-security-and-admin-audit-report.md`

## 3. Segurança adicionada

- Backend exige marcador master-only para `policy_chain_contract` e `official_document_source_audit` antes de resolver conexao ou chamar provider.
- Rota Next continua validando `assertSameOrigin` e `requireMasterAdmin`.
- Rota Next envia `X-AutoBrokers-Master-Admin: true` ao backend somente depois da validacao master.
- URLs oficiais aceitas somente em HTTPS.
- URLs com usuario/senha embutidos sao bloqueadas.
- SSRF bloqueia localhost, loopback, `0.0.0.0`, `::1`, redes privadas, link-local, reserved/multicast/unspecified e endpoint de metadata.
- DNS que resolve para IP interno e bloqueado.
- Redirecionamentos sao manuais, maximo 3.
- Redirect para HTTP e bloqueado.
- Authorization/cookies so seguem para o mesmo origin original.
- Redirect externo HTTPS e tentado sem credenciais.
- Fetch usa Range e limite de tamanho por header e streaming.
- Resultado nao retorna URL, host integral, token, cookie, Authorization, CPF, nome, numero de apolice, `codfil`, `nosnum`, payload ou texto do PDF.

## 4. UX adicionada

No card existente "Diagnosticar contrato InfoCap", foi adicionado seletor de modo:

- Diagnosticar contrato InfoCap;
- Auditar fonte oficial da apolice.

Quando a auditoria documental e selecionada, o card reutiliza:

- metodo CPF/Nome;
- termo de teste;
- referencia da apolice.

O `company_id` vem da rota da pagina, nao de input manual do Founder. A tela exibe apenas o JSON estrutural seguro retornado pelo backend.

## 5. Como o Founder deve testar depois do deploy

1. Portal Admin -> Empresas -> Resulta Seguros -> Agentes.
2. Abrir "Diagnostico & manutencao".
3. Abrir "Diagnosticar contrato InfoCap".
4. Em Modo, selecionar "Auditar fonte oficial da apolice".
5. Selecionar CPF.
6. Informar o CPF de teste.
7. Informar o numero humano da apolice de teste.
8. Clicar em Executar.
9. Copiar de volta somente o bloco `source_audit`.

## 6. Campos seguros a trazer de volta

- `retrieval_status`
- `auth_mode_required`
- `final_origin_class`
- `content_type`
- `content_disposition_present`
- `content_length_bucket`
- `file_magic`
- `pdf_encrypted`
- `pdf_page_count`
- `text_layer_status`
- `document_anchor_detection`
- `content_hash_present`
- `source_fetch_safe_for_r1c`
- `source_fetch_blocker`
- `recommended_r1c_transport`

## 7. O que continua proibido

- R1C produtivo.
- Download de documento pelo Chat Principal.
- Docling/OCR.
- MinIO/Qdrant/Supabase/DocumentService.
- Cache documental.
- HTTP Tool ou MCP para InfoCap.
- Novo runtime, conector, parser, storage, migration, agente ou ferramenta paralela.

## 8. Proxima decisao

O JSON real definira o transporte da R1C:

- `direct_authenticated_fetch`;
- `signed_url_fetch`;
- `session_cookie_fetch`;
- `portal_required`;
- `unavailable`.
