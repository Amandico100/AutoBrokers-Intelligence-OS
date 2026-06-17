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
