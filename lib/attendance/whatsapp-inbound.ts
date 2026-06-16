// WhatsApp Inbound — normalização/segurança PURA (42W0).
//
// Helpers sem I/O para o canal WhatsApp do Attendance Runtime. NÃO é um runtime
// paralelo: apenas normaliza/sanitiza o payload do provider (Z-API), consolida
// buffer, classifica evento e decide a política de outbound (dry-run seguro).
//
// REGRAS: nunca expor telefone cru/nome completo/token/payload bruto. Telefone
// vai mascarado + hash pseudônimo. O cérebro do atendimento continua no
// Attendance Runtime (corridor-runtime/reply); aqui é só a borda do canal.

import { createHash } from 'crypto';

export type WhatsAppProviderName = 'z-api';

export type WhatsAppMediaKind = 'text' | 'audio' | 'image' | 'document' | 'location' | 'status' | 'empty';

export interface NormalizedWhatsAppInbound {
  provider: WhatsAppProviderName;
  message_id: string | null;
  connected_phone_masked: string | null;
  from_phone_masked: string | null;
  from_phone_hash: string | null;
  from_name_safe: string | null;
  text: string | null;
  media: { kind: WhatsAppMediaKind; has_media: boolean };
  timestamp: number | null;
  company_id: string | null;
  agent_id: string | null;
  raw_ref: string | null;
}

export interface NormalizedWhatsAppOutbound {
  provider: WhatsAppProviderName;
  to_phone_ref: string | null; // mascarado
  text: string;
  company_id: string | null;
  agent_id: string | null;
  conversation_id: string | null;
  case_id?: string | null;
  dry_run: boolean;
  external_send_allowed: boolean;
}

/** Mascara telefone: mantém 4 primeiros + **** + 2 últimos dígitos. Nunca cru. */
export function maskPhone(value?: string | null): string | null {
  const r = (value || '').toString().trim();
  if (!r) return null;
  const digits = r.replace(/\D/g, '');
  if (digits.length < 6) return '****';
  return `${digits.slice(0, 4)}****${digits.slice(-2)}`;
}

/** Hash pseudônimo determinístico do telefone (sha256 dos dígitos, 16 hex). Sem PII crua. */
export function phoneHash(value?: string | null): string | null {
  const digits = (value || '').toString().replace(/\D/g, '');
  if (!digits) return null;
  return createHash('sha256').update(digits).digest('hex').slice(0, 16);
}

/** Nome seguro: só o primeiro nome (sem sobrenome completo). */
export function safeName(name?: string | null): string | null {
  const v = (name || '').toString().trim();
  if (!v) return null;
  const first = v.split(/\s+/)[0];
  return first ? first.slice(0, 40) : null;
}

/** Classifica o tipo de evento do payload Z-API (ignora status/vazio). */
export function classifyInboundEvent(payload: Record<string, any>): WhatsAppMediaKind {
  if (!payload || typeof payload !== 'object') return 'empty';
  if (payload.isGroup === true || payload.fromMe === true) return 'status';
  if (payload.text && typeof payload.text.message === 'string' && payload.text.message.trim()) return 'text';
  if (payload.audio && (payload.audio.audioUrl || payload.audio.url)) return 'audio';
  if (payload.image && (payload.image.imageUrl || payload.image.url)) return 'image';
  if (payload.document || payload.file) return 'document';
  if (payload.location) return 'location';
  return 'empty';
}

/** Mensagem humana segura por tipo de mídia (sem vazar URL/payload). */
export function mediaAckMessage(kind: WhatsAppMediaKind): string {
  switch (kind) {
    case 'audio':
      return 'Recebi seu áudio. Pode me contar por escrito, em uma frase, o que está acontecendo?';
    case 'image':
      return 'Recebi sua imagem e vou analisar. Enquanto isso, pode me descrever rapidamente o problema?';
    case 'document':
      return 'Recebi seu documento e vou analisar. Pode me adiantar, em uma frase, qual é a situação?';
    case 'location':
      return 'Recebi sua localização. Pode confirmar, por favor, o endereço onde o atendimento é necessário?';
    default:
      return 'Recebi sua mensagem. Pode me contar rapidamente o que está acontecendo?';
  }
}

/** Normaliza o payload Z-API para o contrato interno seguro. */
export function normalizeZapiInbound(
  payload: Record<string, any>,
  ctx: { companyId?: string | null; agentId?: string | null } = {},
): NormalizedWhatsAppInbound {
  const p = payload && typeof payload === 'object' ? payload : {};
  const kind = classifyInboundEvent(p);
  const text =
    kind === 'text' && p.text && typeof p.text.message === 'string' ? p.text.message.trim().slice(0, 4000) : null;
  return {
    provider: 'z-api',
    message_id: typeof p.messageId === 'string' && p.messageId ? p.messageId : null,
    connected_phone_masked: maskPhone(p.connectedPhone),
    from_phone_masked: maskPhone(p.phone),
    from_phone_hash: phoneHash(p.phone),
    from_name_safe: safeName(p.senderName),
    text,
    media: { kind, has_media: kind === 'audio' || kind === 'image' || kind === 'document' || kind === 'location' },
    timestamp: typeof p.momment === 'number' ? p.momment : null,
    company_id: ctx.companyId ?? null,
    agent_id: ctx.agentId ?? null,
    raw_ref: typeof p.messageId === 'string' && p.messageId ? `zapi:${p.messageId}` : null,
  };
}

/** Há identificador mínimo para processar? (precisa de phone + connectedPhone). */
export function hasMinimalIdentifiers(payload: Record<string, any>): boolean {
  if (!payload || typeof payload !== 'object') return false;
  return Boolean(payload.phone) && Boolean(payload.connectedPhone);
}

/** Consolida mensagens do buffer numa única entrada (ordem temporal preservada). */
export function consolidateBufferedMessages(messages: unknown[]): string {
  if (!Array.isArray(messages)) return '';
  return messages
    .map((m) => (typeof m === 'string' ? m.trim() : ''))
    .filter((m) => m.length > 0)
    .join('\n')
    .slice(0, 6000);
}

// ---------------------------------------------------------------------------
// Webhook auth mode (segurança do endpoint inbound)
// ---------------------------------------------------------------------------

export type WebhookAuthMode = 'disabled' | 'shared_secret' | 'provider_signature';

export function resolveWebhookAuthMode(raw?: string | null): WebhookAuthMode {
  const v = (raw || '').toLowerCase().trim();
  if (v === 'shared_secret' || v === 'provider_signature') return v;
  return 'disabled';
}

/** Valida o acesso ao webhook conforme o modo. Nunca loga o segredo. */
export function checkWebhookAuth(input: {
  mode: WebhookAuthMode;
  providedSecret?: string | null;
  expectedSecret?: string | null;
  hasProviderSignature?: boolean;
}): { ok: boolean; reason: string } {
  if (input.mode === 'disabled') return { ok: true, reason: 'auth_disabled' };
  if (input.mode === 'shared_secret') {
    if (!input.expectedSecret) return { ok: false, reason: 'secret_not_configured' };
    if (!input.providedSecret) return { ok: false, reason: 'missing_secret' };
    return input.providedSecret === input.expectedSecret
      ? { ok: true, reason: 'shared_secret_ok' }
      : { ok: false, reason: 'secret_mismatch' };
  }
  // provider_signature
  return input.hasProviderSignature ? { ok: true, reason: 'signature_ok' } : { ok: false, reason: 'missing_signature' };
}

// ---------------------------------------------------------------------------
// Outbound policy (dry-run seguro por conexão)
// ---------------------------------------------------------------------------

export interface OutboundPolicyInput {
  globalDryRun?: boolean; // settings.DRY_RUN global
  integrationDryRun?: boolean; // integration.metadata.whatsapp_dry_run
  environment?: string | null; // tenant_connection.environment: sandbox|production
  externalSendAuthorized?: boolean; // explicitamente autorizado a enviar de verdade
}

/** Decide se o envio é real ou dry-run. Conservador: dry-run a menos que tudo libere. */
export function resolveOutboundPolicy(input: OutboundPolicyInput): { dry_run: boolean; external_send_allowed: boolean } {
  const sandbox = (input.environment || '').toLowerCase() === 'sandbox';
  const dryRun = input.globalDryRun === true || input.integrationDryRun === true || sandbox || input.externalSendAuthorized !== true;
  return { dry_run: dryRun, external_send_allowed: !dryRun };
}
