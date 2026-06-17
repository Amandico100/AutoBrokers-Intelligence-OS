// 42X3 — Provider-Agnostic Insurer Channel Registry. PURO, self-contained
// (sem imports cross-module em runtime, p/ testes Node .mjs).
//
// Modela providers de mensageria de seguradora (Z-API, Evolution Go, Meta
// Cloud, manual), suas capabilities, a configuração de canal por
// tenant/seguradora/corredor e os payloads por provider — TUDO em sandbox.
// NUNCA envia: send_real_allowed/canSendReal são sempre false neste estágio.

export type InsurerActionChannel = 'insurer_whatsapp' | 'manual';
export type ProviderStatus = 'available' | 'future' | 'manual';

export interface InsurerMessagingProvider {
  provider_key: string;
  label: string;
  channel: InsurerActionChannel;
  supports_text: boolean;
  supports_media: boolean;
  supports_template: boolean;
  supports_threading: boolean;
  supports_webhook: boolean;
  supports_group: boolean;
  auth_model: string;
  destination_format: string;
  status: ProviderStatus;
  real_send_supported_future: boolean;
  notes: string;
}

const PROVIDERS: InsurerMessagingProvider[] = [
  {
    provider_key: 'zapi',
    label: 'Z-API (WhatsApp)',
    channel: 'insurer_whatsapp',
    supports_text: true,
    supports_media: true,
    supports_template: false,
    supports_threading: false,
    supports_webhook: true,
    supports_group: true,
    auth_model: 'instance_id+token+client_token',
    destination_format: 'phone_e164_or_group_id',
    status: 'available',
    real_send_supported_future: true,
    notes: 'Provider de WhatsApp atualmente integrado ao app (não oficial).',
  },
  {
    provider_key: 'evolution_go',
    label: 'Evolution Go / Evolution API',
    channel: 'insurer_whatsapp',
    supports_text: true,
    supports_media: true,
    supports_template: false,
    supports_threading: false,
    supports_webhook: true,
    supports_group: true,
    auth_model: 'api_key+instance',
    destination_format: 'phone_e164_or_group_id',
    status: 'future',
    real_send_supported_future: true,
    notes: 'Alternativa à Z-API; previsto, ainda não homologado.',
  },
  {
    provider_key: 'meta_cloud',
    label: 'Meta WhatsApp Cloud API (oficial)',
    channel: 'insurer_whatsapp',
    supports_text: true,
    supports_media: true,
    supports_template: true,
    supports_threading: false,
    supports_webhook: true,
    supports_group: false,
    auth_model: 'system_user_token+phone_number_id',
    destination_format: 'phone_e164',
    status: 'future',
    real_send_supported_future: true,
    notes: 'Oficial; fora da janela de 24h exige template aprovado. Sem grupos.',
  },
  {
    provider_key: 'manual',
    label: 'Manual / handoff humano',
    channel: 'manual',
    supports_text: false,
    supports_media: false,
    supports_template: false,
    supports_threading: false,
    supports_webhook: false,
    supports_group: false,
    auth_model: 'none',
    destination_format: 'none',
    status: 'manual',
    real_send_supported_future: false,
    notes: 'Sem envio automático; corretor humano executa o acionamento.',
  },
  {
    provider_key: 'future_custom',
    label: 'Provider futuro (genérico)',
    channel: 'insurer_whatsapp',
    supports_text: true,
    supports_media: false,
    supports_template: false,
    supports_threading: false,
    supports_webhook: false,
    supports_group: false,
    auth_model: 'tbd',
    destination_format: 'tbd',
    status: 'future',
    real_send_supported_future: true,
    notes: 'Placeholder para futuros providers conectáveis.',
  },
];

export function getInsurerMessagingProviderRegistry(): InsurerMessagingProvider[] {
  return PROVIDERS.map((p) => ({ ...p }));
}

export function getInsurerMessagingProvider(provider_key: string | null | undefined): InsurerMessagingProvider | null {
  return PROVIDERS.find((p) => p.provider_key === provider_key) ?? null;
}

export function validateProviderKey(provider_key: string | null | undefined): boolean {
  return PROVIDERS.some((p) => p.provider_key === provider_key);
}

export interface ProviderCapabilities {
  provider_key: string;
  found: boolean;
  channel: InsurerActionChannel | null;
  status: ProviderStatus | null;
  supports_text: boolean;
  supports_media: boolean;
  supports_template: boolean;
  supports_threading: boolean;
  supports_webhook: boolean;
  supports_group: boolean;
  real_send_supported_future: boolean;
}

export function resolveProviderCapabilities(provider_key: string | null | undefined): ProviderCapabilities {
  const p = getInsurerMessagingProvider(provider_key);
  if (!p) {
    return {
      provider_key: String(provider_key ?? ''),
      found: false,
      channel: null,
      status: null,
      supports_text: false,
      supports_media: false,
      supports_template: false,
      supports_threading: false,
      supports_webhook: false,
      supports_group: false,
      real_send_supported_future: false,
    };
  }
  return {
    provider_key: p.provider_key,
    found: true,
    channel: p.channel,
    status: p.status,
    supports_text: p.supports_text,
    supports_media: p.supports_media,
    supports_template: p.supports_template,
    supports_threading: p.supports_threading,
    supports_webhook: p.supports_webhook,
    supports_group: p.supports_group,
    real_send_supported_future: p.real_send_supported_future,
  };
}

// --- Insurer Channel Config -------------------------------------------------

export type HomologationStatus =
  | 'not_started'
  | 'sandbox_ready'
  | 'awaiting_credentials'
  | 'awaiting_approval'
  | 'homologated_future';

export type DestinationKind = 'phone' | 'group' | 'portal' | 'email' | 'manual';
export type ChannelConfigMode = 'sandbox' | 'dry_run' | 'future_real_disabled';

export interface InsurerActionChannelConfig {
  config_id: string;
  company_id: string | null;
  insurer_key: string;
  corridor_key: string | null;
  subcorridor_key: string | null;
  channel: InsurerActionChannel;
  provider_key: string;
  mode: ChannelConfigMode;
  destination_ref_masked: string | null; // NUNCA o destino cru
  destination_kind: DestinationKind;
  homologation_status: HomologationStatus;
  capabilities: ProviderCapabilities;
  playbook_id: string | null;
  priority: number;
  is_active: boolean;
  send_real_allowed: false; // SEMPRE false neste estágio
  notes: string | null;
  created_at: string;
  updated_at: string;
}

function maskDestination(ref: string | null | undefined): string | null {
  if (!ref) return null;
  const s = String(ref).trim();
  if (s.length <= 4) return '****';
  return `****${s.slice(-4)}`;
}

export interface BuildChannelConfigInput {
  config_id?: string;
  company_id: string | null;
  insurer_key: string;
  corridor_key?: string | null;
  subcorridor_key?: string | null;
  provider_key: string;
  destination_ref?: string | null; // cru — será mascarado e NUNCA armazenado cru
  destination_ref_masked?: string | null;
  destination_kind?: DestinationKind;
  homologation_status?: HomologationStatus;
  playbook_id?: string | null;
  priority?: number;
  is_active?: boolean;
  notes?: string | null;
  mode?: ChannelConfigMode;
  created_at?: string;
}

function configId(): string {
  return `iacc-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Cria/normaliza um InsurerActionChannelConfig. O destino cru é mascarado
 * imediatamente e NUNCA armazenado. send_real_allowed é sempre false.
 */
export function buildInsurerChannelConfig(input: BuildChannelConfigInput): InsurerActionChannelConfig {
  const now = new Date().toISOString();
  const provider = getInsurerMessagingProvider(input.provider_key);
  const capabilities = resolveProviderCapabilities(input.provider_key);
  const channel: InsurerActionChannel = provider?.channel ?? 'manual';
  const masked = input.destination_ref_masked ?? maskDestination(input.destination_ref);
  const destination_kind: DestinationKind =
    input.destination_kind ?? (channel === 'manual' ? 'manual' : 'phone');
  return {
    config_id: input.config_id ?? configId(),
    company_id: input.company_id ?? null,
    insurer_key: input.insurer_key,
    corridor_key: input.corridor_key ?? null,
    subcorridor_key: input.subcorridor_key ?? null,
    channel,
    provider_key: input.provider_key,
    mode: input.mode ?? 'sandbox',
    destination_ref_masked: masked,
    destination_kind,
    homologation_status: input.homologation_status ?? 'not_started',
    capabilities,
    playbook_id: input.playbook_id ?? null,
    priority: typeof input.priority === 'number' ? input.priority : 100,
    is_active: input.is_active !== false,
    send_real_allowed: false,
    notes: input.notes ?? null,
    created_at: input.created_at ?? now,
    updated_at: now,
  };
}

/** Versão pública/sanitizada (garante ausência de destino cru/token). */
export function sanitizeInsurerChannelConfig(config: InsurerActionChannelConfig): Record<string, unknown> {
  const { destination_ref_masked, ...rest } = config;
  return {
    ...rest,
    destination_ref_masked: destination_ref_masked ?? null,
    send_real_allowed: false,
  };
}

export interface ResolveConfigContext {
  insurer_key: string | null;
  corridor_key?: string | null;
  subcorridor_key?: string | null;
}

/**
 * Resolve a config ativa mais específica para o contexto:
 * subcorredor > corredor > seguradora. Desempata por priority (menor vence)
 * e depois pela mais recente. Sem match → null (cai em manual no chamador).
 */
export function resolveActiveInsurerChannelConfig(
  configs: InsurerActionChannelConfig[],
  ctx: ResolveConfigContext,
): InsurerActionChannelConfig | null {
  const active = (configs || []).filter(
    (c) => c.is_active && c.insurer_key === ctx.insurer_key,
  );
  if (active.length === 0) return null;

  const score = (c: InsurerActionChannelConfig): number => {
    let s = 0;
    if (c.subcorridor_key && c.subcorridor_key === ctx.subcorridor_key) s += 4;
    else if (c.subcorridor_key) return -1; // pede subcorredor diferente → não serve
    if (c.corridor_key && c.corridor_key === ctx.corridor_key) s += 2;
    else if (c.corridor_key) return -1; // pede corredor diferente → não serve
    return s;
  };

  let best: InsurerActionChannelConfig | null = null;
  let bestScore = -1;
  for (const c of active) {
    const s = score(c);
    if (s < 0) continue;
    if (
      s > bestScore ||
      (s === bestScore && best && (c.priority < best.priority ||
        (c.priority === best.priority && c.updated_at > best.updated_at)))
    ) {
      best = c;
      bestScore = s;
    }
  }
  return best;
}

// --- Homologation -----------------------------------------------------------

export type HomologationEvalState =
  | 'not_started'
  | 'missing_credentials'
  | 'destination_missing'
  | 'sandbox_ready'
  | 'blocked_real_send_disabled'
  | 'future_homologated_pending';

export interface HomologationEvaluation {
  state: HomologationEvalState;
  send_real_allowed: false; // SEMPRE false no 42X3
  blockers: string[];
  provider_status: ProviderStatus | null;
}

/**
 * Avalia o estado de homologação do canal. Nenhum estado libera envio real no
 * 42X3 (send_real_allowed sempre false).
 */
export function evaluateInsurerChannelHomologation(
  config: InsurerActionChannelConfig,
  ctx: { credentialPresent?: boolean } = {},
): HomologationEvaluation {
  const provider = getInsurerMessagingProvider(config.provider_key);
  const blockers: string[] = ['real_send_disabled_42x3'];
  if (!provider) {
    return { state: 'not_started', send_real_allowed: false, blockers: [...blockers, 'unknown_provider'], provider_status: null };
  }
  // Manual: handoff humano não precisa de credencial/destino → sandbox_ready.
  if (provider.channel === 'manual') {
    return { state: 'sandbox_ready', send_real_allowed: false, blockers, provider_status: provider.status };
  }
  if (!config.destination_ref_masked) {
    return { state: 'destination_missing', send_real_allowed: false, blockers: [...blockers, 'destination_missing'], provider_status: provider.status };
  }
  if (!ctx.credentialPresent) {
    return { state: 'missing_credentials', send_real_allowed: false, blockers: [...blockers, 'missing_credentials'], provider_status: provider.status };
  }
  // Tudo presente no sandbox, mas envio real continua desabilitado.
  return { state: 'sandbox_ready', send_real_allowed: false, blockers, provider_status: provider.status };
}

// --- Provider Payload Builders (sandbox; nunca chamam API; sem token) -------

export interface PayloadContext {
  destination_ref_masked?: string | null;
  message_text?: string | null;
  media?: boolean;
}

const _LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
function maskBody(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).replace(_LONG_DIGITS, '[omitido]').slice(0, 480);
}

/**
 * Monta o payload sanitizado por provider. SEMPRE dry_run; NUNCA inclui token
 * nem destino cru; NUNCA chama API.
 */
export function buildProviderPayload(
  provider_key: string,
  ctx: PayloadContext,
): Record<string, unknown> {
  const to = ctx.destination_ref_masked ?? null;
  const body = maskBody(ctx.message_text);
  switch (provider_key) {
    case 'zapi':
      return { provider: 'zapi', endpoint_kind: ctx.media ? 'send-image' : 'send-text', to_masked: to, body, dry_run: true, sent: false };
    case 'evolution_go':
      return { provider: 'evolution_go', endpoint_kind: ctx.media ? 'sendMedia' : 'sendText', to_masked: to, body, dry_run: true, sent: false };
    case 'meta_cloud':
      return { provider: 'meta_cloud', messaging_product: 'whatsapp', to_masked: to, type: 'text', text: { body }, dry_run: true, sent: false };
    case 'manual':
      return { provider: 'manual', handoff: true, to_masked: to, body, dry_run: true, sent: false };
    default:
      return { provider: 'unknown', supported: false, to_masked: to, body, dry_run: true, sent: false };
  }
}

/** Resumo seguro de uma lista de configs (sem destino cru/token). */
export function safeChannelConfigSummary(configs: InsurerActionChannelConfig[]): Record<string, unknown> {
  return {
    count: configs.length,
    providers: Array.from(new Set(configs.map((c) => c.provider_key))),
    insurers: Array.from(new Set(configs.map((c) => c.insurer_key))),
    any_send_real_allowed: false,
    active_count: configs.filter((c) => c.is_active).length,
  };
}
