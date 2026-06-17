# 42M2 — Real Document Extraction for Attendance using Smith Docling/Ingestion Report

> **Status:** concluído · testes offline **351 verdes** (15 document + 21 vision/doc + 36 media + 22 knowledge + 37 policy-qa + 39 intent + 32 selection + 44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `py_compile` OK · `typecheck` EXIT=0 · build verde · **sem schema** · **reusa DocumentService do Smith** · **documento não confirma cobertura** · **conflito documento×InfoCap detectado** · **sem URL/base64/texto bruto/PII**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Inventário de documentos no Smith
| Pergunta | Resposta |
|---|---|
| Docling service? | **Sim** — `sanitization_service` + microserviço (`DOCLING_SERVICE_URL`, async/polling, OCR/layout). Pesado; ideal para ingestão de KB, não para extração inline rápida. |
| Extração síncrona? | **Sim** — `DocumentService.extract_text_internal(BytesIO, file_type)` (PyPDF2 p/ PDF, python-docx p/ DOCX, plain p/ TXT/MD/CSV). **É o que reusei.** |
| MIME suportado | pdf, docx/doc, txt, md, csv. |
| ingestion_service | chunking + embeddings + Qdrant (async/RAG). **Não** usado aqui (atendimento não indexa). |
| Storage/MinIO, Qdrant | existem (ingestão de KB). Não necessários para evidência inline. |
| Redaction/provenance | adicionei no endpoint de atendimento (mask PII, provenance). |
| Custo/limite | extração síncrona é local (sem custo de API); adicionei limite de tamanho. |
| Reutilizável agora | **`DocumentService.extract_text_internal`** (síncrono, leve). |

**Reusado:** `DocumentService` (extração síncrona). **Não usei** Docling microservice (async/pesado) nem ingestion/Qdrant — ficam para ingestão de KB (42R1). **Não criei** parser paralelo frágil.

## 2. Arquivos alterados/criados
- `backend/app/api/attendance_media.py` (**alterado**) — `/attendance/media/document-extract` **real**: baixa bytes (base64/URL, limite de tamanho), reusa `DocumentService.extract_text_internal`, detecta tipo, extrai `possible_policy_info`/`key_facts`, devolve **resumo sanitizado** (sem texto bruto/URL/base64).
- `backend/app/core/config.py` (**alterado**) — `ATTENDANCE_MEDIA_MAX_SIZE_MB` (default 10).
- `lib/attendance/attendance-media.ts` (**alterado**) — `extractAttendanceDocument` enriquecido + `detectDocumentInfocapConflict` (PURO) + `buildDocumentCustomerReply` (controlado).
- `app/api/attendance/whatsapp/inbound/route.ts` (**alterado**) — documento → extração (flag on), conflito × InfoCap → `metadata.document_infocap_conflict` + resposta de validação humana; `media_evidence` enriquecido (document_type/key_facts/possible_policy_info/conflicts).
- `scripts/attendance-document-extraction.test.mjs` (**novo**) + `package.json` (`test:media-document`).
- `docs/canon/design/2026-06-claude-design/42M2-...md` (este).

## 3. Backend extraction (`/attendance/media/document-extract`)
Gated por `ATTENDANCE_DOCUMENT_EXTRACTION_ENABLED`. Fluxo: resolve `file_type` (mime/filename) → baixa bytes (base64 decode ou httpx GET, **limite `ATTENDANCE_MEDIA_MAX_SIZE_MB`**) → `DocumentService.extract_text_internal` → detecta `document_type`, `possible_policy_info` (insurer/product/datas/nº mascarado/menção a assistência elétrica), `key_facts`, `extracted_text_summary` (**masked + truncado ≤800**, nunca texto bruto completo). MIME não suportado → `unsupported`; falha → `failed`. **Nunca** retorna URL/base64/texto bruto.

## 4. Tipos detectados
`policy_document`, `invoice_or_receipt`, `claim_report`, `identity_document`, `property_document`, `general_attachment` (heurística por palavras-chave no texto extraído).

## 5. Apólice enviada pelo cliente (não substitui InfoCap)
`possible_policy_info` (insurer/product/vigência/nº mascarado) é **evidência auxiliar** (`customer_uploaded_policy_evidence`). **Não** muda `policy_source` nem confirma cobertura. `detectDocumentInfocapConflict` compara (conservador) seguradora e nº de apólice contra `policy_snapshot`: divergência forte → `conflict=true` → grava `metadata.document_infocap_conflict` + resposta de **validação humana**.

## 6. Condições gerais / menção a cobertura
Se o documento menciona assistência elétrica → `document_mentions_assistance_electrician=true` na evidência, mas a resposta é: *"Ele menciona assistência elétrica em termos gerais, mas preciso validar se essa condição se aplica à sua apólice específica."* **Não** muda `coverage_readiness` para confirmado.

## 7. Resposta controlada (bridge)
Documento processado → *"Recebi e consegui ler um resumo do documento. Ele será usado como evidência auxiliar, mas a cobertura continua dependendo da validação da apólice."* Conflito → validação humana. Menção elétrica → termos gerais + validar. Flag off / não suportado → ack do 42M1.

## 8. Q&A sobre documento
- "posso mandar o PDF?" → `media_offer_question` (pode mandar; ajuda como evidência; cobertura depende de validação).
- "o PDF diz que cobre, então posso acionar?" → `policy_coverage_question` → **NÃO confirma** ("…preciso validar…"). Documento mencionando cobertura **não** autoriza acionamento.

## 9. Evidência/metadata
`metadata.media_evidence[]` (documento): `document_type`, `extracted_text_summary` (masked/truncado), `key_facts`, `possible_policy_info` (nº mascarado), `conflicts`, `confidence`, `limitations`, `provenance` (`document_service:<type>`), `redaction`. **Sem texto bruto completo, sem URL/base64.**

## 10. Flags/envs (default seguro)
- `ATTENDANCE_DOCUMENT_EXTRACTION_ENABLED` = false (liga a extração real; reuso local do DocumentService, sem custo de API).
- `ATTENDANCE_MEDIA_MAX_SIZE_MB` = 10 (limite).
- (`ATTENDANCE_VISION_ENABLED`, `ATTENDANCE_MEDIA_ENABLED` dos 42M0/42M1.)
Off → pending/ack seguros; produção inalterada.

## 11. Testes que rodei (offline)
- `node scripts/attendance-document-extraction.test.mjs` → **15/15**: gated off → fail-safe; **conflito documento×InfoCap** (insurer/nº); respostas controladas **não confirmam cobertura**; menção elétrica → validar; Q&A documento (PDF "cobre" → coverage não confirma; "posso mandar PDF" → media_offer).
- Regressão: vision/doc **21**, media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **351/351**.
- `python -m py_compile` (attendance_media + config) OK · `npx tsc --noEmit` EXIT=0 · `npm run build` verde. Goldens/Q&A/dispatch preservados.

## 12. Reteste (console, logado)
```js
// requer ATTENDANCE_DOCUMENT_EXTRACTION_ENABLED=true (extração local, sem custo de API).
const P='5544'+Math.floor(100000+Math.random()*899999);
const sim=async(b)=>(await (await fetch('/api/attendance/whatsapp/simulate-inbound',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from_phone:P,from_name:'M2',...b})})).json());
console.log((await sim({media_kind:'document',media_url:'<url do PDF/apólice>',mime_type:'application/pdf'})).auto_reply);
console.log((await sim({text:'o PDF diz que cobre, então posso acionar?'})).auto_reply); // não confirma
```
**Esperado (flag on):** "Recebi e consegui ler um resumo do documento… evidência auxiliar… cobertura depende da validação." Se divergir da apólice → validação humana. Nunca confirma cobertura; nunca vaza texto bruto/URL.

## 13. Critério de pronto
| Critério | Status |
|---|---|
| documento/PDF extraído ou pending seguro | ✅ (DocumentService; flag/fail-safe) |
| documento vira evidência auxiliar | ✅ (`media_evidence[]`) |
| documento não confirma cobertura sozinho | ✅ (testes [3][4]) |
| conflito com InfoCap detectável | ✅ (`detectDocumentInfocapConflict` + handoff flag) |
| sem vazamento | ✅ (masked/truncado, sem URL/base64) |
| goldens verdes | ✅ 351/351 |

## 14. Decisão: seguir para 42X0?
**Sim — pode seguir para 42X0 (Action Engine externo dry-run).** O bloco de mídia (áudio→texto, imagem→visão, documento→extração) está completo e seguro: tudo vira **evidência auxiliar**, nada confirma cobertura, conflitos vão para validação humana, e nada é enviado externamente. O atendente agora ouve, enxerga e lê — base sólida para o 42X0 preparar acionamento (dry-run/HITL) lendo `coverage_readiness`/`dispatch_readiness`, sempre com `external_action_sent=false` até homologação. Extração de layout/OCR avançada (Docling) e ingestão de KB (Qdrant) ficam para 42M3/42R1 conforme necessidade.

## 15. Checks
| Check | Resultado |
|---|---|
| `node scripts/attendance-document-extraction.test.mjs` | ✅ 15/15 |
| vision/media/knowledge/policy-qa/intent/selection/whatsapp/dispatch/coverage/evidence | ✅ 21/36/22/37/39/32/44/35/33/37 |
| `python -m py_compile` | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · parser paralelo · documento confirma cobertura · envio externo · texto bruto/URL/base64/PII · quebra goldens | ✅ nenhum |
