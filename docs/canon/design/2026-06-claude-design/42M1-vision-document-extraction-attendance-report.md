# 42M1 — Vision & Document Extraction for Attendance Media Evidence using Smith Tools Report

> **Status:** concluído · testes offline **336 verdes** (21 vision/doc + 36 media + 22 knowledge + 37 policy-qa + 39 intent + 32 selection + 44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `py_compile` OK · `typecheck` EXIT=0 · build verde · **sem schema** · **reusa visão do Smith** · **mídia não confirma cobertura** · **sem envio externo** · **sem URL/base64/PII**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 0. Validação do 42M0
Smoke test do Founder passou: imagem (ack evidência, sem URL), documento (sem cobertura), localização (sem coordenadas, pergunta se é o endereço do imóvel). O "posso mandar foto?" como **primeira** mensagem foi para intake (citou "disjuntor" → problema) — comportamento razoável; o Q&A de mídia funciona mid-flow (coberto por teste).

## 1. Inventário Vision/Document Smith
| Capacidade | Onde | Reuso 42M1 |
|---|---|---|
| Visão multimodal (image_url → LLM) | `chat.py` (`agent.vision_model` + ChatOpenAI/ChatAnthropic, mensagem multimodal) | **reusado** (mesmo padrão) |
| Modelos de visão | `gpt-4o`/`gpt-*` (OPENAI_API_KEY), `claude*` (ANTHROPIC_API_KEY) | **reusado** |
| Extração de documento/PDF | `ingestion_service` (assíncrono/Qdrant) + Docling microservice | **placeholder** (extração inline madura → 42M2) |
| Cost callback de visão | `CostCallbackHandler(service_type='vision')` | referência (endpoint dedicado mantém simples) |

**Reusado:** padrão de visão do Smith (vision_model do agente). **Placeholder:** documento (sem parser inline frágil; ingestion é assíncrono/pesado). **Não recriei** OCR/vision engine.

## 2. Arquivos alterados/criados
- `backend/app/api/attendance_media.py` (**alterado**) — `POST /attendance/media/vision-analyze` (reusa visão do Smith; prompt de atendimento; saída sanitizada; nunca confirma cobertura) + `POST /attendance/media/document-extract` (placeholder seguro `unsupported` → 42M2).
- `lib/attendance/attendance-media.ts` (**alterado**) — `deriveVisualEvidence` (PURO: issue/risco/área), `buildVisionCustomerReply` (resposta controlada, não ecoa resumo cru), `analyzeAttendanceImage`/`extractAttendanceDocument` (gated; reuso backend).
- `app/api/attendance/whatsapp/inbound/route.ts` (**alterado**) — imagem→visão (flag on) com evidência+segurança; documento→extração (flag on) ou pending; `metadata.media_evidence` enriquecido.
- `lib/attendance/policy-qa.ts` (**alterado**) — Q&A de mídia ampliado ("a foto ajuda?", "enviei a apólice").
- `scripts/attendance-media-vision-document.test.mjs` (**novo**) + `package.json` (`test:media-vision`).
- `docs/canon/design/2026-06-claude-design/42M1-...md` (este).

## 3. Backend Vision (`/attendance/media/vision-analyze`)
Reusa o padrão do `chat.py`: lê `agent.vision_model`, monta `ChatOpenAI`/`ChatAnthropic`, envia mensagem multimodal (system de atendimento + `image_url`). Prompt: descrever objetivamente só o visível/relevante (quadro/disjuntor/tomada/fiação/vazamento/dano/documento), apontar risco, **não confirmar cobertura, não ler dados pessoais**. Saída sanitizada (`_mask_pii`, 800 chars): `visual_summary`, `confidence`, `limitations`, `provenance: vision:<model>`. Sem `vision_model`/provider → `unsupported`. Nunca retorna URL/base64.

## 4. Backend Document (`/attendance/media/document-extract`)
Sem extrator inline maduro, retorna `unsupported` com limitações claras ("extração automática ainda não disponível (42M2)"; "documento do cliente NÃO substitui validação oficial via InfoCap"). Contrato pronto para o 42M2 plugar Docling/ingestion. Não cria parser frágil, não confirma cobertura.

## 5. Como a imagem vira evidência (sem decidir cobertura)
Bridge (imagem, `ATTENDANCE_VISION_ENABLED=true`): `analyzeAttendanceImage` → `visual_summary` → `deriveVisualEvidence` (PURO): `possible_issue_type` (electrician/plumber/locksmith/document), `possible_slots` (sugestões `suggested_issue_type`/`suggested_affected_area` — **não** auto-preenchem o corredor), `risk_hint`. Resposta **controlada** (`buildVisionCustomerReply`): não ecoa o resumo cru do LLM; cita o tipo de problema; **se risco visual → orientação de segurança** ("desligue o disjuntor e aguarde a equipe"); sempre "a cobertura ainda depende da apólice e da validação". Evidência salva em `metadata.media_evidence[]` (com `visual_summary`, sem URL/base64). Flag off → ack seguro do 42M0.

## 6. Documento/apólice do cliente
Hoje `unsupported`/pending (registra para análise). **Nunca** "cobertura confirmada" por PDF enviado; documento do cliente **não substitui** o lookup InfoCap. Conflito documento×InfoCap (quando houver extração em 42M2) → handoff. Resposta segura mantida.

## 7. possible_slots — segurança
As sugestões da visão ficam **registradas como evidência** (`suggested_*`), **não** mudam o estado do corredor automaticamente (sem auto-fill de slot sensível, sem baixar risco, sem cobertura). Auto-preenchimento com alta confiança fica para 42M2 (com validação). Risco visual nunca é ignorado: vira orientação de segurança.

## 8. Q&A de mídia
"posso te mandar uma foto?", "a foto ajuda?", "o documento serve?", "enviei a apólice" → `media_offer_question` → *"Pode sim! …ajudam como evidência… a cobertura ainda depende da apólice e da validação."*

## 9. Flags/envs (default seguro)
- `ATTENDANCE_VISION_ENABLED` = false (liga a visão; reusa `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` + `agent.vision_model`).
- `ATTENDANCE_DOCUMENT_EXTRACTION_ENABLED` = false (extração → 42M2).
- `ATTENDANCE_MEDIA_ENABLED` = false (áudio, do 42M0).
Off → ack/evidência seguros, **sem custo inesperado**, produção inalterada.

## 10. Testes que rodei (offline)
- `node scripts/attendance-media-vision-document.test.mjs` → **21/21**: `deriveVisualEvidence` (elétrico/hidráulico/fechadura/documento/risco/área); `buildVisionCustomerReply` (não confirma cobertura, não ecoa cru, orientação de risco); vision/document **gated off → unsupported** (sem rede); Q&A de mídia ampliado.
- Regressão: media **36**, knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **336/336**.
- `python -m py_compile` (attendance_media) OK · `npx tsc --noEmit` EXIT=0 · `npm run build` verde. Goldens/Q&A/dispatch preservados.

## 11. Reteste (console, logado)
```js
// vision real exige ATTENDANCE_VISION_ENABLED=true + agent.vision_model + key.
const P='5544'+Math.floor(100000+Math.random()*899999);
const sim=async(b)=>(await (await fetch('/api/attendance/whatsapp/simulate-inbound',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from_phone:P,from_name:'M1',...b})})).json());
console.log((await sim({media_kind:'image',media_url:'<url da foto do disjuntor>',mime_type:'image/jpeg'})).auto_reply);
console.log((await sim({text:'a foto ajuda?'})).auto_reply);
```
**Esperado (flag on):** "Recebi e analisei a imagem. Ela parece mostrar um problema elétrico. … cobertura ainda depende da apólice e da validação." (+ orientação de segurança se risco). Flag off → ack do 42M0. Nunca vaza URL/base64; nunca confirma cobertura.

## 12. Critério de pronto
| Critério | Status |
|---|---|
| imagem interpretada ou falha com segurança | ✅ (visão reusada + fallback) |
| documento resumido ou pending seguro | ✅ (placeholder 42M2) |
| mídia melhora contexto/slots sem confirmar cobertura | ✅ (sugestões + safety) |
| sem vazamento URL/base64/PII | ✅ (testes) |
| Smith tools reutilizados | ✅ (visão) |
| goldens verdes | ✅ |

## 13. Próximos
- **42M2 — Document extraction real** (Docling/ingestion do Smith) + auto-fill de slots com validação + conflito documento×InfoCap.
- **42R1 — Ingestão real de KB** (Qdrant).
- **42X0 — Action Engine dry-run** · **42W2 — webhook real Z-API** (pausado).

## 14. Checks
| Check | Resultado |
|---|---|
| `node scripts/attendance-media-vision-document.test.mjs` | ✅ 21/21 |
| media/knowledge/policy-qa/intent/selection/whatsapp-inbound/dispatch/coverage/evidence | ✅ 36/22/37/39/32/44/35/33/37 |
| `python -m py_compile` | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · vision engine paralelo · mídia confirma cobertura · envio externo · URL/base64/PII · quebra goldens | ✅ nenhum |
