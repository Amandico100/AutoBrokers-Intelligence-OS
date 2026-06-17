# 42M0 — Media Evidence Pipeline using Smith Existing Audio, Image & Document Tools Report

> **Status:** concluído · testes offline **315 verdes** (36 media + 22 knowledge + 37 policy-qa + 39 intent + 32 selection + 44 whatsapp-inbound + 35 dispatch + 33 coverage + 37 evidence) · `py_compile` OK · `typecheck` EXIT=0 · build verde · **sem schema** · **reusa AudioService do Smith** · **mídia não confirma cobertura** · **sem envio externo** · **sem URL/base64/PII em respostas/logs**.
> **Data:** 2026-06-17 · **Modelo:** Claude Opus 4.8 · **Branch:** main

## 1. Inventário de mídia no Smith
| Capacidade | Onde | Reuso 42M0 |
|---|---|---|
| Áudio base64 → texto (Whisper) | `AudioService.transcribe_audio` | **reusado** |
| Áudio por URL → texto (WhatsApp) | `AudioService.transcribe_audio_from_url` | **reusado** |
| Chat multimodal (audioData/imageUrl) | `backend/app/api/chat.py` | referência (não acoplado ao atendimento) |
| Imagem (vision) no LangChain | `chat.py` (image_url → LLM vision) | **placeholder future-ready** (não acoplei vision ao runtime ainda) |
| Documento/PDF (ingestion/docling) | `ingestion_service`, document tooling | **placeholder future-ready** |
| Webhook WhatsApp (já transcrevia áudio/processava imagem) | `webhook.py` | referência (atendimento usa o bridge) |

**Reusado:** AudioService (áudio). **Placeholder seguro:** imagem (vision) e documento (extração) — interface pronta, com ack humano, sem motor paralelo. **Não recriei** OCR/vision/transcrição.

## 2. Arquivos alterados/criados
- `lib/attendance/attendance-media.ts` (**novo**) — `normalizeAttendanceMedia`, `processAttendanceMedia`, `buildMediaEvidenceRecord`, `transcribeAttendanceAudio` (reuso AudioService via endpoint interno).
- `backend/app/api/attendance_media.py` (**novo**) — `POST /attendance/media/transcribe` (chave interna; reusa AudioService; stateless; logs sanitizados) + registro no `main.py`.
- `app/api/attendance/whatsapp/inbound/route.ts` (**alterado**) — pipeline de mídia (áudio→transcrição→runtime; imagem/doc/local→evidência+ack); `metadata.media_evidence[]` sem payload bruto.
- `app/api/attendance/whatsapp/simulate-inbound/route.ts` (**alterado**) — aceita `media_url`/`media_base64`/`mime_type`/`location`.
- `lib/attendance/policy-qa.ts` (**alterado**) — categoria `media_offer_question` ("posso mandar foto/áudio?").
- `app/api/attendance/cases/[caseId]/runtime/reply/route.ts` (**alterado**) — de-dup da retomada reforçado (corrige a duplicação suave do teste do 42R0).
- `scripts/attendance-media.test.mjs` (**novo**) + `package.json` (`test:media`).
- `docs/canon/design/2026-06-claude-design/42M0-...md` (este).

## 3. Bug do teste 42R0 corrigido
No teste do Founder, com LLM ligado, a resposta de status já re-perguntava no meio do texto (terminando em ".") e o código ainda anexava "Para eu continuar: …" → **a pergunta da área aparecia 2×**. Fix: se o LLM foi usado e a resposta contém **qualquer** "?", não anexa a retomada (o LLM já conduziu de volta). Sem LLM, a retomada continua (determinístico não pergunta).

## 4. Contrato normalizado (`normalizeAttendanceMedia`)
Saída: `media_kind` (audio/image/document/location/text/unknown), `safe_ref` (hash sha256-12, **nunca** URL/base64), `mime_type`, `size_hint`, `source_channel`, `provider`, `has_payload`, `redaction[]`, `warnings[]`. Testado: não vaza URL/base64/coordenadas/endereço.

## 5. Adapter (`processAttendanceMedia`)
- **Áudio** → `pending` + `backend_transcribe` (transcrição feita por `transcribeAttendanceAudio`); se transcrever, o texto vira **mensagem normal** do runtime.
- **Imagem** → `pending` + `vision_future` (evidência + ack; vision real depois).
- **Documento** → `pending` + `document_future` (registra para análise; **nunca** confirma cobertura por PDF).
- **Localização** → `processed` + `possible_slots.property_location_provided` + resumo **sem coordenadas** + pergunta "é o endereço do imóvel segurado?".
- Todos: `limitations` incluem "mídia não confirma cobertura" e `safe_customer_reply` humano.

## 6. Áudio (reuso AudioService)
`transcribeAttendanceAudio` (gated por `ATTENDANCE_MEDIA_ENABLED`, default off) chama `POST /attendance/media/transcribe`, que reusa `AudioService.transcribe_audio_from_url` (URL) ou `transcribe_audio` (base64). Sucesso → o texto transcrito entra no `runtime/reply` (provenance `whatsapp_audio`/`audio_transcribed`). Falha/flag off → ack seguro ("Recebi seu áudio… pode me contar por texto?"). **Nunca** loga áudio/URL/base64.

## 7. Imagem / Documento / Localização
- **Imagem/Documento**: hoje **evidência + ack** (placeholder future-ready). Não mandam mídia bruta ao LLM nem confirmam cobertura. Vision/extração reais ficam para **42M1**.
- **Localização**: vira `location_summary` sanitizado + sinaliza `property_location_provided`; pergunta se é o endereço do imóvel segurado. Coordenadas nunca expostas.

## 8. Evidência (sem schema novo)
`attendance_cases.metadata.media_evidence[]` (append, máx 10) com: media_kind, safe_ref, mime_type, size_hint, source_channel, provider, status, summary, confidence, provenance, limitations, processed_at. **Sem payload bruto.** Diagnóstico do run registra eventos `media_*`/`audio_transcribed`.

## 9. WhatsApp simulate-inbound com mídia
Aceita `{ media_kind, media_url?, media_base64?, mime_type?, location?, text? }` e delega ao bridge in-process. Áudio (flag on) → transcreve → runtime; mídia+texto → registra evidência e o texto segue; só mídia → evidência + ack. WhatsApp real (42W2) herdará o mesmo caminho.

## 10. Q&A de mídia
"posso te mandar uma foto do disjuntor?" → `media_offer_question` → *"Pode sim! Você pode me mandar foto, áudio, documento ou a localização — eles ajudam como evidência… a cobertura ainda depende da apólice e da validação."*

## 11. Testes que rodei (offline)
- `node scripts/attendance-media.test.mjs` → **36/36**: normalização/classificação por mime; **sem PII/URL/base64/coordenadas**; roteamento por tipo; **mídia não confirma cobertura**; evidence record sanitizado; áudio fail-safe (flag off → `media_disabled`, sem rede); Q&A de oferta de mídia.
- Regressão: knowledge **22**, policy-qa **37**, intent **39**, selection **32**, whatsapp-inbound **44**, dispatch **35**, coverage **33**, evidence **37** = **315/315**.
- `python -m py_compile` (attendance_media + main) OK · `npx tsc --noEmit` EXIT=0 · `npm run build` verde. Goldens/Q&A preservados.

## 12. Flags/envs
- `ATTENDANCE_MEDIA_ENABLED` (default off) — liga a transcrição de áudio (reuso AudioService). Off → ack seguro (produção inalterada).
- Reusa `OPENAI_API_KEY` (backend, Whisper), `BACKEND_INTERNAL_API_KEY`, `ATTENDANCE_BACKEND_URL`.

## 13. Reteste (console, logado)
```js
const P='5544'+Math.floor(100000+Math.random()*899999);
const sim=async(b)=>(await (await fetch('/api/attendance/whatsapp/simulate-inbound',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from_phone:P,from_name:'Teste M0',...b})})).json());
console.log((await sim({media_kind:'image',media_url:'https://exemplo/foto.jpg',mime_type:'image/jpeg'})).auto_reply); // ack evidência, sem vazar URL
console.log((await sim({location:{lat:-23.5,lng:-46.6}})).auto_reply); // pergunta se é o endereço do imóvel
console.log((await sim({text:'posso te mandar uma foto?'})).auto_reply); // pode sim + limite de cobertura
// áudio: com ATTENDANCE_MEDIA_ENABLED=true + AudioService, sim({media_kind:'audio',media_url:'<url>'}) transcreve e segue o runtime
```
**Esperado:** mídia não trava; ack humano; sem URL/base64/coords; áudio (flag on) vira texto e conduz o atendimento.

## 14. Critério de pronto
| Critério | Status |
|---|---|
| áudio transcrito ou falha com resposta segura | ✅ (reuso AudioService; gated) |
| imagem/documento/localização não quebram | ✅ |
| mídia vira evidência segura | ✅ (`media_evidence[]`) |
| mídia não decide cobertura | ✅ (teste [3]) |
| WhatsApp simulate-inbound aceita mídia | ✅ |
| sem vazamento de URL/base64/PII | ✅ (testes [2][4]) |
| Smith tools auditados/reusados | ✅ (AudioService) |
| goldens continuam verdes | ✅ |

## 15. Próximos (42M1 / 42R1)
- **42M1 — Vision & Document extraction**: ligar a visão (LangChain vision do Smith) para resumo de imagem (quadro/disjuntor/dano) e extração de documento/PDF (ingestion/docling) como evidência — **sem** confirmar cobertura. A interface (`vision_future`/`document_future`) já está pronta.
- **42R1 — Ingestão real de KB** (Qdrant) por seguradora/corredor/corretora.
- **42X0 — Action Engine externo dry-run**; **42W2 — webhook real Z-API** (pausado).

## 16. Checks
| Check | Resultado |
|---|---|
| `node scripts/attendance-media.test.mjs` | ✅ 36/36 |
| knowledge/policy-qa/intent/selection/whatsapp-inbound/dispatch/coverage/evidence | ✅ 22/37/39/32/44/35/33/37 |
| `python -m py_compile` | ✅ OK |
| `npx tsc --noEmit` | ✅ EXIT=0 |
| `npm run build` | ✅ verde |
| `git diff --check` | ✅ limpo |
| schema · provider/OCR paralelo · mídia confirma cobertura · envio externo · URL/base64/PII · quebra goldens | ✅ nenhum |
