// 42X4 — Provider Adapter Homologation Harness. PURO, self-contained
// (sem imports cross-module em runtime, p/ testes Node .mjs).
//
// Adapters realistas por provider (Z-API, Evolution Go, Meta Cloud, manual),
// baseados em documentação oficial/atual. canSendReal=false SEMPRE: este harness
// só valida payload, simula (mockSend) e parseia respostas — NUNCA chama API real.
//
// Fontes oficiais consultadas (2026-06):
// - Z-API:       https://developer.z-api.io/  (send-text; header Client-Token; resp zaapId/messageId/id)
// - Meta Cloud:  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
// - Evolution:   https://docs.evolutionfoundation.com.br/ + https://doc.evolution-api.com/
//                (Evolution API /message/sendText/{instance}; Evolution Go gateway endpoint NÃO confirmado oficialmente → partial)

export type ProviderResearchStatus = 'verified' | 'partial' | 'research_required';

// Erros provider-neutros.
export type ProviderErrorCode =
  | 'invalid_destination'
  | 'auth_missing'
  | 'auth_failed_future'
  | 'provider_unavailable'
  | 'rate_limited'
  | 'instance_disconnected'
  | 'message_rejected'
  | 'webhook_signature_invalid'
  | 'unknown_provider_error';

export const PROVIDER_ERROR_CODES: ProviderErrorCode[] = [
  'invalid_destination',
  'auth_missing',
  'auth_failed_future',
  'provider_unavailable',
  'rate_limited',
  'instance_disconnected',
  'message_rejected',
  'webhook_signature_invalid',
  'unknown_provider_error',
];

export interface ProviderValidationResult {
  valid: boolean;
  errors: ProviderErrorCode[];
  warnings: string[];
}

export interface ProviderPayload {
  provider_key: string;
  endpoint_method: string;
  endpoint_template: string; // template com placeholders — NUNCA segredo
  headers_required: string[]; // só NOMES de header, nunca valores
  body: Record<string, unknown>; // mascarado
  dry_run: true;
}

export interface ProviderMockSendResult {
  sent: false; // SEMPRE false
  mock: true;
  status: string;
  provider_message_id: string | null;
  raw_mock: Record<string, unknown>;
  reason: string;
}

export interface ProviderParsedResponse {
  provider_message_id: string | null;
  status: string;
  error_code: ProviderErrorCode | null;
}

export interface ProviderParsedWebhook {
  event: string;
  provider_message_id: string | null;
  status: string;
  error_code: ProviderErrorCode | null;
}

export interface AdapterContext {
  destination_ref_masked?: string | null;
  message_text?: string | null;
  credential_present?: boolean;
  phone_number_id_present?: boolean; // meta
  within_24h_window?: boolean; // meta (template fora da janela)
}

export interface OutboxLike {
  destination_ref_masked?: string | null;
  message_text?: string | null;
}

export interface InsurerMessagingProviderAdapter {
  provider_key: string;
  label: string;
  canSendReal: false;
  research_status: ProviderResearchStatus;
  docs_url: string;
  validateConfig(ctx: AdapterContext): ProviderValidationResult;
  validatePayload(payload: ProviderPayload): ProviderValidationResult;
  buildTextPayload(outbox: OutboxLike, ctx: AdapterContext): ProviderPayload;
  mockSend(payload: ProviderPayload, ctx?: AdapterContext): ProviderMockSendResult;
  parseSendResponse(response: Record<string, any>, ctx?: AdapterContext): ProviderParsedResponse;
  parseWebhook?(payload: Record<string, any>, ctx?: AdapterContext): ProviderParsedWebhook;
}

const _LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
function maskBody(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).replace(_LONG_DIGITS, '[omitido]').slice(0, 1024);
}
function mockId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// --- Z-API ------------------------------------------------------------------
const zapiAdapter: InsurerMessagingProviderAdapter = {
  provider_key: 'zapi',
  label: 'Z-API (WhatsApp)',
  canSendReal: false,
  research_status: 'verified',
  docs_url: 'https://developer.z-api.io/',
  validateConfig(ctx) {
    const errors: ProviderErrorCode[] = [];
    const warnings: string[] = [];
    if (!ctx.destination_ref_masked) errors.push('invalid_destination');
    if (!ctx.credential_present) warnings.push('auth_missing_future'); // instance_id+token+Client-Token virão do Vault
    return { valid: errors.length === 0, errors, warnings };
  },
  validatePayload(payload) {
    const errors: ProviderErrorCode[] = [];
    if (!payload.body || !payload.body.phone) errors.push('invalid_destination');
    if (!payload.headers_required.includes('Client-Token')) errors.push('auth_missing');
    return { valid: errors.length === 0, errors, warnings: [] };
  },
  buildTextPayload(outbox) {
    return {
      provider_key: 'zapi',
      endpoint_method: 'POST',
      // Endpoint oficial: instance id + token na URL; Client-Token no header.
      endpoint_template: 'https://api.z-api.io/instances/{instanceId}/token/{token}/send-text',
      headers_required: ['Content-Type', 'Client-Token'],
      body: { phone: outbox.destination_ref_masked ?? null, message: maskBody(outbox.message_text) },
      dry_run: true,
    };
  },
  mockSend(_payload) {
    const id = mockId('zaap');
    return {
      sent: false,
      mock: true,
      status: 'mock_accepted',
      provider_message_id: id,
      raw_mock: { zaapId: id, messageId: mockId('msg'), id },
      reason: 'mock — canSendReal=false (Z-API não chamada)',
    };
  },
  parseSendResponse(response) {
    const pid = response?.zaapId ?? response?.messageId ?? response?.id ?? null;
    return { provider_message_id: pid ?? null, status: pid ? 'accepted' : 'unknown', error_code: pid ? null : 'unknown_provider_error' };
  },
  parseWebhook(payload) {
    const status = String(payload?.status ?? payload?.type ?? 'unknown').toLowerCase();
    const map: Record<string, string> = { sent: 'sent', received: 'delivered', delivered: 'delivered', read: 'read', 'message-status': status };
    return { event: 'zapi_status', provider_message_id: payload?.messageId ?? payload?.zaapId ?? null, status: map[status] ?? status, error_code: null };
  },
};

// --- Meta Cloud -------------------------------------------------------------
const metaCloudAdapter: InsurerMessagingProviderAdapter = {
  provider_key: 'meta_cloud',
  label: 'Meta WhatsApp Cloud API (oficial)',
  canSendReal: false,
  research_status: 'verified',
  docs_url: 'https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages',
  validateConfig(ctx) {
    const errors: ProviderErrorCode[] = [];
    const warnings: string[] = [];
    if (!ctx.destination_ref_masked) errors.push('invalid_destination');
    if (!ctx.phone_number_id_present) warnings.push('phone_number_id_missing_future');
    if (!ctx.credential_present) warnings.push('auth_missing_future'); // system_user_token via Vault
    if (ctx.within_24h_window === false) warnings.push('template_required_outside_24h_window');
    return { valid: errors.length === 0, errors, warnings };
  },
  validatePayload(payload) {
    const errors: ProviderErrorCode[] = [];
    const b = payload.body || {};
    if (b.messaging_product !== 'whatsapp') errors.push('message_rejected');
    if (!b.to) errors.push('invalid_destination');
    if (!payload.headers_required.includes('Authorization')) errors.push('auth_missing');
    return { valid: errors.length === 0, errors, warnings: [] };
  },
  buildTextPayload(outbox) {
    return {
      provider_key: 'meta_cloud',
      endpoint_method: 'POST',
      endpoint_template: 'https://graph.facebook.com/{version}/{phoneNumberId}/messages',
      headers_required: ['Authorization', 'Content-Type'],
      body: {
        messaging_product: 'whatsapp',
        recipient_type: 'individual',
        to: outbox.destination_ref_masked ?? null,
        type: 'text',
        text: { body: maskBody(outbox.message_text), preview_url: false },
      },
      dry_run: true,
    };
  },
  mockSend(_payload) {
    const id = mockId('wamid');
    return {
      sent: false,
      mock: true,
      status: 'mock_accepted',
      provider_message_id: id,
      raw_mock: { messaging_product: 'whatsapp', contacts: [{ wa_id: '****' }], messages: [{ id, message_status: 'accepted' }] },
      reason: 'mock — canSendReal=false (Meta Cloud não chamada)',
    };
  },
  parseSendResponse(response) {
    const pid = response?.messages?.[0]?.id ?? null;
    const st = response?.messages?.[0]?.message_status ?? (pid ? 'accepted' : 'unknown');
    return { provider_message_id: pid, status: st, error_code: pid ? null : 'unknown_provider_error' };
  },
  parseWebhook(payload) {
    const st = payload?.entry?.[0]?.changes?.[0]?.value?.statuses?.[0];
    return {
      event: 'meta_status',
      provider_message_id: st?.id ?? null,
      status: String(st?.status ?? 'unknown').toLowerCase(),
      error_code: st?.errors ? 'message_rejected' : null,
    };
  },
};

// --- Evolution Go (partial — endpoint do gateway Go NÃO confirmado oficialmente) ---
const evolutionGoAdapter: InsurerMessagingProviderAdapter = {
  provider_key: 'evolution_go',
  label: 'Evolution Go / Evolution API',
  canSendReal: false,
  research_status: 'partial',
  docs_url: 'https://docs.evolutionfoundation.com.br/',
  validateConfig(ctx) {
    const errors: ProviderErrorCode[] = [];
    const warnings: string[] = ['evolution_go_endpoint_unverified_research_required'];
    if (!ctx.destination_ref_masked) errors.push('invalid_destination');
    if (!ctx.credential_present) warnings.push('auth_missing_future'); // apikey via Vault
    return { valid: errors.length === 0, errors, warnings };
  },
  validatePayload(payload) {
    const errors: ProviderErrorCode[] = [];
    if (!payload.body || !payload.body.number) errors.push('invalid_destination');
    if (!payload.headers_required.includes('apikey')) errors.push('auth_missing');
    return { valid: errors.length === 0, errors, warnings: ['evolution_go_endpoint_unverified_research_required'] };
  },
  buildTextPayload(outbox) {
    return {
      provider_key: 'evolution_go',
      endpoint_method: 'POST',
      // Shape conhecido da Evolution API (v2). Endpoint exato do gateway Evolution Go: A CONFIRMAR.
      endpoint_template: '{serverUrl}/message/sendText/{instance}',
      headers_required: ['Content-Type', 'apikey'],
      body: { number: outbox.destination_ref_masked ?? null, text: maskBody(outbox.message_text) },
      dry_run: true,
    };
  },
  mockSend(_payload) {
    const id = mockId('evo');
    return {
      sent: false,
      mock: true,
      status: 'mock_accepted',
      provider_message_id: id,
      raw_mock: { key: { id }, status: 'PENDING' },
      reason: 'mock — canSendReal=false; endpoint Evolution Go ainda research_required',
    };
  },
  parseSendResponse(response) {
    const pid = response?.key?.id ?? response?.id ?? null;
    return { provider_message_id: pid, status: response?.status ?? (pid ? 'pending' : 'unknown'), error_code: pid ? null : 'unknown_provider_error' };
  },
};

// --- Manual (handoff humano — nunca envia) ----------------------------------
const manualAdapter: InsurerMessagingProviderAdapter = {
  provider_key: 'manual',
  label: 'Manual / handoff humano',
  canSendReal: false,
  research_status: 'verified',
  docs_url: 'n/a',
  validateConfig() {
    return { valid: true, errors: [], warnings: ['manual_no_automatic_send'] };
  },
  validatePayload() {
    return { valid: true, errors: [], warnings: ['manual_no_automatic_send'] };
  },
  buildTextPayload(outbox) {
    return {
      provider_key: 'manual',
      endpoint_method: 'NONE',
      endpoint_template: 'human_handoff',
      headers_required: [],
      body: { handoff: true, to_masked: outbox.destination_ref_masked ?? null, body: maskBody(outbox.message_text) },
      dry_run: true,
    };
  },
  mockSend() {
    return { sent: false, mock: true, status: 'manual_handoff', provider_message_id: null, raw_mock: { handoff: true }, reason: 'sem envio automático — tratativa humana' };
  },
  parseSendResponse() {
    return { provider_message_id: null, status: 'manual_handoff', error_code: null };
  },
};

const ADAPTERS: Record<string, InsurerMessagingProviderAdapter> = {
  zapi: zapiAdapter,
  meta_cloud: metaCloudAdapter,
  evolution_go: evolutionGoAdapter,
  manual: manualAdapter,
};

export function getProviderAdapter(provider_key: string | null | undefined): InsurerMessagingProviderAdapter | null {
  return (provider_key && ADAPTERS[provider_key]) || null;
}

export function getProviderAdapterRegistry(): InsurerMessagingProviderAdapter[] {
  return Object.values(ADAPTERS);
}

// --- Homologation checklist -------------------------------------------------
export interface HomologationChecklistItem {
  item: string;
  done: boolean;
  blocker: boolean;
}

export interface HomologationChecklist {
  provider_key: string;
  research_status: ProviderResearchStatus;
  can_send_real: false;
  items: HomologationChecklistItem[];
  blockers: string[];
  ready_for_real_future: boolean; // SEMPRE false neste batch
}

/**
 * Checklist de homologação por provider. Sempre ready_for_real_future=false no
 * 42X4. Itens dependentes de credencial/aprovação/real ficam pendentes (blocker).
 */
export function buildProviderHomologationChecklist(
  provider_key: string,
  ctx: AdapterContext = {},
): HomologationChecklist {
  const adapter = getProviderAdapter(provider_key);
  if (!adapter) {
    return { provider_key: String(provider_key ?? ''), research_status: 'research_required', can_send_real: false, items: [], blockers: ['unknown_provider'], ready_for_real_future: false };
  }
  const cfgVal = adapter.validateConfig(ctx);
  const payload = adapter.buildTextPayload({ destination_ref_masked: ctx.destination_ref_masked ?? '****0000', message_text: ctx.message_text ?? 'homologação' }, ctx);
  const payloadVal = adapter.validatePayload(payload);
  const mock = adapter.mockSend(payload, ctx);
  const verified = adapter.research_status === 'verified';

  const items: HomologationChecklistItem[] = [
    { item: 'official_docs_reviewed', done: adapter.research_status !== 'research_required', blocker: adapter.research_status === 'research_required' },
    { item: 'endpoint_documented', done: verified, blocker: !verified },
    { item: 'auth_model_documented', done: verified, blocker: false },
    { item: 'destination_format_validated', done: cfgVal.errors.indexOf('invalid_destination') < 0, blocker: cfgVal.errors.indexOf('invalid_destination') >= 0 },
    { item: 'payload_shape_validated', done: payloadVal.valid, blocker: !payloadVal.valid },
    { item: 'webhook_status_handling_documented', done: typeof adapter.parseWebhook === 'function', blocker: false },
    { item: 'error_mapping_implemented', done: true, blocker: false },
    { item: 'mock_send_passing', done: mock.mock === true && mock.sent === false, blocker: false },
    { item: 'real_credentials_in_vault', done: false, blocker: true },
    { item: 'kill_switch_tested', done: false, blocker: true },
    { item: 'approval_flow_tested', done: false, blocker: true },
    { item: 'canary_send_planned', done: false, blocker: true },
    { item: 'rollback_plan', done: false, blocker: true },
  ];
  const blockers = items.filter((i) => i.blocker).map((i) => i.item);
  return {
    provider_key,
    research_status: adapter.research_status,
    can_send_real: false,
    items,
    blockers: [...blockers, ...cfgVal.warnings.filter((w) => w.includes('research_required'))],
    ready_for_real_future: false,
  };
}

/** Validação + mock que o outbox anexa (sanitizado). */
export interface ProviderHarnessSummary {
  provider_research_status: ProviderResearchStatus;
  provider_validation_status: 'valid' | 'invalid' | 'unknown_provider';
  provider_validation_errors: ProviderErrorCode[];
  homologation_blockers: string[];
  provider_mock_capable: boolean;
  can_send_real: false;
}

export function summarizeProviderHarness(provider_key: string | null, ctx: AdapterContext = {}): ProviderHarnessSummary {
  const adapter = getProviderAdapter(provider_key);
  if (!adapter) {
    return { provider_research_status: 'research_required', provider_validation_status: 'unknown_provider', provider_validation_errors: ['unknown_provider_error'], homologation_blockers: ['unknown_provider'], provider_mock_capable: false, can_send_real: false };
  }
  const cfgVal = adapter.validateConfig(ctx);
  const payload = adapter.buildTextPayload({ destination_ref_masked: ctx.destination_ref_masked ?? null, message_text: ctx.message_text ?? null }, ctx);
  const payloadVal = adapter.validatePayload(payload);
  const checklist = buildProviderHomologationChecklist(provider_key as string, ctx);
  const valid = cfgVal.valid && payloadVal.valid;
  return {
    provider_research_status: adapter.research_status,
    provider_validation_status: valid ? 'valid' : 'invalid',
    provider_validation_errors: [...cfgVal.errors, ...payloadVal.errors],
    homologation_blockers: checklist.blockers,
    provider_mock_capable: adapter.research_status !== 'research_required',
    can_send_real: false,
  };
}
