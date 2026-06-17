// Media Evidence Pipeline (42M0) — normalização/roteamento PURO + transcrição via
// AudioService do Smith (reuso, sem motor paralelo).
//
// Regras: mídia NUNCA confirma cobertura; mídia vira EVIDÊNCIA auxiliar com
// provenance. Nunca expõe URL bruta/base64/PII no response público nem em logs.
// Áudio reusa o AudioService do Smith via endpoint interno; imagem/documento têm
// interface segura (future-ready) com ack humano; localização vira resumo sanitizado.

import { createHash } from 'crypto';

export type AttendanceMediaKind = 'audio' | 'image' | 'document' | 'location' | 'text' | 'unknown';

export interface NormalizedAttendanceMedia {
  media_kind: AttendanceMediaKind;
  safe_ref: string | null; // hash/máscara — NUNCA url/base64 crus
  mime_type: string | null;
  size_hint: string | null; // 'small'|'medium'|'large'|null
  source_channel: string;
  provider: string;
  has_payload: boolean;
  redaction: string[];
  warnings: string[];
}

export interface AttendanceMediaInput {
  media_kind?: string | null;
  media_url?: string | null;
  media_base64?: string | null;
  mime_type?: string | null;
  source_channel?: string | null;
  provider?: string | null;
  location?: { lat?: number; lng?: number; address_hint?: string | null } | null;
}

function shortHash(s: string): string {
  return createHash('sha256').update(s).digest('hex').slice(0, 12);
}

function inferKindFromMime(mime: string | null): AttendanceMediaKind {
  const m = (mime || '').toLowerCase();
  if (m.startsWith('audio/')) return 'audio';
  if (m.startsWith('image/')) return 'image';
  if (m.includes('pdf') || m.includes('msword') || m.includes('officedocument') || m.startsWith('application/')) return 'document';
  return 'unknown';
}

function sizeBucket(base64?: string | null): string | null {
  if (!base64) return null;
  const bytes = Math.floor((base64.length * 3) / 4);
  if (bytes < 200_000) return 'small';
  if (bytes < 2_000_000) return 'medium';
  return 'large';
}

/** Normaliza a mídia do inbound. PURO. NUNCA retorna url/base64 crus. */
export function normalizeAttendanceMedia(input: AttendanceMediaInput): NormalizedAttendanceMedia {
  const declared = (input.media_kind || '').toLowerCase();
  let kind: AttendanceMediaKind =
    declared === 'audio' || declared === 'image' || declared === 'document' || declared === 'location' || declared === 'text'
      ? (declared as AttendanceMediaKind)
      : 'unknown';
  if (kind === 'unknown' || kind === 'text') {
    if (input.location || (input.location && typeof input.location === 'object')) kind = 'location';
    else if (input.media_url || input.media_base64) kind = inferKindFromMime(input.mime_type ?? null);
  }
  const payloadRef = input.media_url || input.media_base64 || null;
  const warnings: string[] = [];
  if (kind === 'unknown' && (input.media_url || input.media_base64)) warnings.push('unknown_media_type');
  return {
    media_kind: kind,
    safe_ref: payloadRef ? `${kind}:${shortHash(payloadRef)}` : input.location ? `location:${shortHash(JSON.stringify(input.location))}` : null,
    mime_type: input.mime_type || null,
    size_hint: sizeBucket(input.media_base64),
    source_channel: input.source_channel || 'whatsapp',
    provider: input.provider || 'z-api',
    has_payload: Boolean(input.media_url || input.media_base64 || input.location),
    redaction: ['url_omitida', 'base64_omitido', 'coordenadas_omitidas'],
    warnings,
  };
}

export interface MediaProcessResult {
  status: 'processed' | 'pending' | 'unsupported' | 'failed';
  media_kind: AttendanceMediaKind;
  extracted_text: string | null;
  visual_summary: string | null;
  document_summary: string | null;
  location_summary: string | null;
  possible_slots: Record<string, unknown>;
  evidence_notes: string[];
  provenance: string;
  confidence: 'low' | 'medium' | 'high';
  limitations: string[];
  safe_customer_reply: string;
  processing_route: 'backend_transcribe' | 'vision_future' | 'document_future' | 'location_inline' | 'none';
}

/**
 * Decide o tratamento da mídia (PURO, sem I/O). A transcrição de áudio em si é
 * feita pelo caller via transcribeAttendanceAudio (reuso do AudioService).
 */
export function processAttendanceMedia(
  normalized: NormalizedAttendanceMedia,
  opts: { pendingSlotHint?: string | null; location?: { address_hint?: string | null } | null } = {},
): MediaProcessResult {
  const base = {
    media_kind: normalized.media_kind,
    extracted_text: null,
    visual_summary: null,
    document_summary: null,
    location_summary: null,
    possible_slots: {},
    confidence: 'low' as const,
    limitations: ['Mídia é evidência auxiliar; não confirma cobertura.'],
  };
  switch (normalized.media_kind) {
    case 'audio':
      return {
        ...base,
        status: 'pending',
        evidence_notes: ['audio_recebido'],
        provenance: 'whatsapp_audio',
        processing_route: 'backend_transcribe',
        safe_customer_reply: 'Recebi seu áudio. Vou ouvir; se preferir, pode também me contar por escrito em uma frase o que está acontecendo.',
      };
    case 'image':
      return {
        ...base,
        status: 'pending',
        evidence_notes: ['imagem_recebida'],
        provenance: 'whatsapp_image',
        processing_route: 'vision_future',
        safe_customer_reply: `Recebi a imagem e ela fica registrada como evidência. ${opts.pendingSlotHint ? `Para eu continuar: ${opts.pendingSlotHint}` : 'Pode me descrever rapidamente o problema?'}`,
      };
    case 'document':
      return {
        ...base,
        status: 'pending',
        evidence_notes: ['documento_recebido'],
        provenance: 'whatsapp_document',
        processing_route: 'document_future',
        safe_customer_reply:
          'Recebi o documento. Ele fica registrado para análise, mas ainda não consigo validar automaticamente todo o conteúdo neste atendimento. Pode me adiantar, em uma frase, qual é a situação?',
      };
    case 'location': {
      const hint = opts.location?.address_hint ? ` (${String(opts.location.address_hint).slice(0, 60)})` : '';
      return {
        ...base,
        status: 'processed',
        location_summary: `Localização recebida${hint}`,
        possible_slots: { property_location_provided: true },
        evidence_notes: ['localizacao_recebida'],
        provenance: 'whatsapp_location',
        confidence: 'medium',
        processing_route: 'location_inline',
        safe_customer_reply: 'Recebi a localização. Ela é o endereço do imóvel segurado? Se sim, me confirma; se não, me passa o endereço correto.',
      };
    }
    default:
      return {
        ...base,
        status: 'unsupported',
        evidence_notes: ['midia_nao_suportada'],
        provenance: 'whatsapp_unknown',
        processing_route: 'none',
        safe_customer_reply: 'Recebi seu anexo, mas não consegui processá-lo neste formato. Pode me contar por texto o que está acontecendo?',
      };
  }
}

/** Registro sanitizado de evidência de mídia (metadata.media_evidence[]). Sem payload bruto. */
export function buildMediaEvidenceRecord(normalized: NormalizedAttendanceMedia, result: MediaProcessResult): Record<string, unknown> {
  return {
    media_kind: normalized.media_kind,
    safe_ref: normalized.safe_ref,
    mime_type: normalized.mime_type,
    size_hint: normalized.size_hint,
    source_channel: normalized.source_channel,
    provider: normalized.provider,
    status: result.status,
    summary: result.location_summary || result.visual_summary || result.document_summary || (result.extracted_text ? 'audio_transcrito' : null),
    confidence: result.confidence,
    provenance: result.provenance,
    limitations: result.limitations,
    processed_at: new Date().toISOString(),
  };
}

// --- Visão/Documento (42M1) -------------------------------------------------

const VIS_ELECTRICIAN = /\b(disjuntor|quadro|tomada|fio|fia[çc]|l[âa]mpada|el[ée]tric|curto|energia)\b/i;
const VIS_PLUMBER = /\b(vazament|cano|torneira|chuveiro|[áa]gua|encanad|esgoto|infiltra|goteira)\b/i;
const VIS_LOCKSMITH = /\b(fechadura|chave|tranca|porta|cadeado)\b/i;
const VIS_DOCUMENT = /\b(documento|ap[óo]lice|comprovante|nota|contrato|cnh|rg)\b/i;
const VIS_RISK = /\b(fogo|fuma[çc]a|fa[íi]sca|queimad|derret|incend|chama|brasa)\b/i;
const VIS_AREA = /\b(cozinha|sala|quarto|banheiro|garagem|varanda|quintal|[áa]rea externa|telhado)\b/i;

export interface VisualEvidence {
  possible_issue_type: string | null; // electrician|plumber|locksmith|document|null
  possible_slots: Record<string, unknown>;
  risk_hint: boolean;
  detected: string[];
}

/** Deriva evidência estruturada do resumo visual (PURO). Sugestões, NUNCA cobertura. */
export function deriveVisualEvidence(visualSummary: string): VisualEvidence {
  const s = (visualSummary || '').toLowerCase();
  const detected: string[] = [];
  let issue: string | null = null;
  if (VIS_ELECTRICIAN.test(s)) { issue = 'electrician'; detected.push('electrical'); }
  else if (VIS_PLUMBER.test(s)) { issue = 'plumber'; detected.push('plumbing'); }
  else if (VIS_LOCKSMITH.test(s)) { issue = 'locksmith'; detected.push('lock'); }
  else if (VIS_DOCUMENT.test(s)) { issue = 'document'; detected.push('document'); }
  const risk_hint = VIS_RISK.test(s);
  if (risk_hint) detected.push('risk');
  const areaMatch = s.match(VIS_AREA);
  // Sugestões (não auto-preenchem slots sensíveis nem cobertura).
  const possible_slots: Record<string, unknown> = {};
  if (issue && issue !== 'document') possible_slots.suggested_issue_type = issue;
  if (areaMatch) possible_slots.suggested_affected_area = areaMatch[0];
  return { possible_issue_type: issue, possible_slots, risk_hint, detected };
}

/** Resposta humana CONTROLADA para imagem (não ecoa o resumo cru do LLM). */
export function buildVisionCustomerReply(ev: VisualEvidence, pendingHint?: string | null): string {
  const typeLabel: Record<string, string> = {
    electrician: 'um problema elétrico',
    plumber: 'um problema hidráulico',
    locksmith: 'algo relacionado a fechadura/porta',
    document: 'um documento',
  };
  let reply = 'Recebi e analisei a imagem.';
  if (ev.possible_issue_type && typeLabel[ev.possible_issue_type]) {
    reply += ` Ela parece mostrar ${typeLabel[ev.possible_issue_type]}.`;
  }
  if (ev.risk_hint) {
    reply += ' ⚠️ Se houver fumaça, faísca ou cheiro de queimado, desligue o disjuntor e aguarde orientação da nossa equipe.';
  }
  reply += ' Isso ajuda como evidência, mas a cobertura ainda depende da apólice e da validação.';
  if (pendingHint) reply += ` Para eu continuar: ${pendingHint}`;
  return reply;
}

function backendUrl(): string {
  return (
    process.env.ATTENDANCE_BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.BACKEND_URL ||
    'http://localhost:8000'
  );
}

/**
 * Transcreve áudio reusando o AudioService do Smith (endpoint interno).
 * Gated por ATTENDANCE_MEDIA_ENABLED (default off → fail-safe). NUNCA loga url/base64.
 */
export async function transcribeAttendanceAudio(input: {
  companyId: string;
  agentId?: string | null;
  audioUrl?: string | null;
  audioBase64?: string | null;
}): Promise<{ ok: boolean; text?: string; reason?: string }> {
  if (process.env.ATTENDANCE_MEDIA_ENABLED !== 'true') return { ok: false, reason: 'media_disabled' };
  if (!input.audioUrl && !input.audioBase64) return { ok: false, reason: 'no_audio' };
  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) return { ok: false, reason: 'internal_key_missing' };
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45_000);
    const res = await fetch(`${backendUrl()}/attendance/media/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify({
        company_id: input.companyId,
        agent_id: input.agentId || undefined,
        audio_url: input.audioUrl || undefined,
        audio_base64: input.audioBase64 || undefined,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!res.ok) return { ok: false, reason: `backend_${res.status}` };
    const data = (await res.json()) as { ok?: boolean; text?: string };
    if (data?.ok && typeof data.text === 'string' && data.text.trim()) return { ok: true, text: data.text.trim() };
    return { ok: false, reason: 'empty_transcription' };
  } catch (e: any) {
    return { ok: false, reason: e?.name === 'AbortError' ? 'timeout' : 'fetch_error' };
  }
}

async function callMediaBackend(path: string, body: Record<string, unknown>, timeoutMs = 35_000): Promise<any> {
  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  if (!internalKey) return { ok: false, status: 'failed', reason: 'internal_key_missing' };
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${backendUrl()}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-AutoBrokers-Internal-Key': internalKey },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (!res.ok) return { ok: false, status: 'failed', reason: `backend_${res.status}` };
    return await res.json();
  } catch (e: any) {
    clearTimeout(timeout);
    return { ok: false, status: 'failed', reason: e?.name === 'AbortError' ? 'timeout' : 'fetch_error' };
  }
}

/** Analisa imagem (reuso da visão do Smith). Gated por ATTENDANCE_VISION_ENABLED. */
export async function analyzeAttendanceImage(input: {
  companyId: string;
  agentId?: string | null;
  caseId?: string | null;
  imageUrl?: string | null;
  imageBase64?: string | null;
  mimeType?: string | null;
}): Promise<{ ok: boolean; status?: string; visual_summary?: string; confidence?: string; reason?: string }> {
  if (process.env.ATTENDANCE_VISION_ENABLED !== 'true') return { ok: false, status: 'unsupported', reason: 'vision_disabled' };
  if (!input.imageUrl && !input.imageBase64) return { ok: false, status: 'unsupported', reason: 'no_image' };
  const data = await callMediaBackend('/attendance/media/vision-analyze', {
    company_id: input.companyId,
    agent_id: input.agentId || undefined,
    case_id: input.caseId || undefined,
    image_url: input.imageUrl || undefined,
    image_base64: input.imageBase64 || undefined,
    mime_type: input.mimeType || undefined,
    purpose: 'attendance_evidence',
  });
  if (data?.ok && typeof data.visual_summary === 'string' && data.visual_summary.trim()) {
    return { ok: true, status: 'processed', visual_summary: data.visual_summary.trim(), confidence: data.confidence || 'medium' };
  }
  return { ok: false, status: data?.status || 'unsupported', reason: data?.error || data?.reason || 'no_summary' };
}

/** Extrai/registra documento. Gated por ATTENDANCE_DOCUMENT_EXTRACTION_ENABLED. */
export async function extractAttendanceDocument(input: {
  companyId: string;
  agentId?: string | null;
  caseId?: string | null;
  documentUrl?: string | null;
  documentBase64?: string | null;
  mimeType?: string | null;
}): Promise<{ ok: boolean; status?: string; summary?: string; document_type?: string | null; reason?: string }> {
  if (process.env.ATTENDANCE_DOCUMENT_EXTRACTION_ENABLED !== 'true') return { ok: false, status: 'unsupported', reason: 'document_extraction_disabled' };
  if (!input.documentUrl && !input.documentBase64) return { ok: false, status: 'unsupported', reason: 'no_document' };
  const data = await callMediaBackend('/attendance/media/document-extract', {
    company_id: input.companyId,
    agent_id: input.agentId || undefined,
    case_id: input.caseId || undefined,
    document_url: input.documentUrl || undefined,
    document_base64: input.documentBase64 || undefined,
    mime_type: input.mimeType || undefined,
    purpose: 'attendance_evidence',
  });
  if (data?.ok && typeof data.extracted_text_summary === 'string' && data.extracted_text_summary.trim()) {
    return { ok: true, status: 'processed', summary: data.extracted_text_summary.trim(), document_type: data.document_type || null };
  }
  return { ok: false, status: data?.status || 'unsupported', reason: data?.error || data?.reason || 'no_summary' };
}
