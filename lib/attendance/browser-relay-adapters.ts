// 43P2 — Browser Relay Provider Adapters (MOCK). PURO, self-contained.
// Adapters para Browserbase, Playwright local, Stagehand, Skyvern lab e mock.
// NENHUM abre browser real, acessa URL real ou usa credencial real:
// canOpenRealBrowser/canAccessRealUrl/canUseRealCredential são SEMPRE false e
// todo método retorna evento MOCK. Nenhuma chamada de rede.

export type RelayProviderKey = 'browserbase' | 'local_playwright' | 'stagehand' | 'skyvern_lab' | 'mock';
export type RelayAdapterMode = 'mock' | 'sandbox' | 'real_future';

export interface BrowserRelayAdapterResult {
  ok: boolean;
  mock: true; // SEMPRE
  provider: RelayProviderKey;
  kind: 'create_session' | 'observe' | 'act' | 'extract' | 'close';
  data?: Record<string, unknown>;
  reason: string;
  real_action_allowed: false;
}

export interface RelayAdapterSessionInput {
  relay_id: string;
  portal_id: string;
  journey?: string | null;
  // Apenas metadados/refs opacas — NUNCA segredo/cookie/storageState.
  session_ref_masked?: string | null;
}

export interface RelayAdapterStepInput {
  instruction?: string | null; // linguagem natural (stagehand-like) — sanitizada
  selector_hint?: string | null;
  query?: string | null;
}

export interface BrowserRelayProviderAdapter {
  provider_key: RelayProviderKey;
  label: string;
  mode: RelayAdapterMode;
  canOpenRealBrowser: false;
  canAccessRealUrl: false;
  canUseRealCredential: false;
  notes: string;
  createSession(input: RelayAdapterSessionInput): BrowserRelayAdapterResult;
  observe(session: RelayAdapterSessionInput, input: RelayAdapterStepInput): BrowserRelayAdapterResult;
  act(session: RelayAdapterSessionInput, input: RelayAdapterStepInput): BrowserRelayAdapterResult;
  extract(session: RelayAdapterSessionInput, input: RelayAdapterStepInput): BrowserRelayAdapterResult;
  close(session: RelayAdapterSessionInput): BrowserRelayAdapterResult;
}

const _LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
const _OTP = /\b\d{4,8}\b/g;
function maskText(s: string | null | undefined): string | null {
  if (!s) return null;
  return String(s).replace(_LONG_DIGITS, '[omitido]').replace(_OTP, '[otp]').slice(0, 240);
}

function mockResult(
  provider: RelayProviderKey,
  kind: BrowserRelayAdapterResult['kind'],
  reason: string,
  data?: Record<string, unknown>,
): BrowserRelayAdapterResult {
  return { ok: true, mock: true, provider, kind, data, reason, real_action_allowed: false };
}

function makeAdapter(
  provider_key: RelayProviderKey,
  label: string,
  notes: string,
): BrowserRelayProviderAdapter {
  return {
    provider_key,
    label,
    mode: 'mock',
    canOpenRealBrowser: false,
    canAccessRealUrl: false,
    canUseRealCredential: false,
    notes,
    createSession: (input) =>
      mockResult(provider_key, 'create_session', `mock session criada (${provider_key}); nenhum browser real aberto`, {
        relay_id: input.relay_id,
        portal_id: input.portal_id,
        session_ref_masked: input.session_ref_masked ?? null,
        opened_real_browser: false,
      }),
    observe: (_s, input) =>
      mockResult(provider_key, 'observe', 'mock observe; nenhuma URL real acessada', {
        instruction: maskText(input.instruction),
        observed_elements: [
          { role: 'textbox', label: 'usuário', actionable: true },
          { role: 'textbox', label: 'senha', actionable: true, sensitive: true },
          { role: 'button', label: 'entrar', actionable: true },
        ],
      }),
    act: (_s, input) =>
      mockResult(provider_key, 'act', 'mock act; nenhuma ação real executada', {
        instruction: maskText(input.instruction),
        selector_hint: maskText(input.selector_hint),
        performed: false,
        simulated: true,
      }),
    extract: (_s, input) =>
      mockResult(provider_key, 'extract', 'mock extract; dados sintéticos mascarados', {
        query: maskText(input.query),
        extracted: { policy_status: 'vigente', masked_policy_number: '****99', protocol: 'mock-proto', source: 'sandbox' },
      }),
    close: () => mockResult(provider_key, 'close', 'mock session encerrada', { closed: true }),
  };
}

const ADAPTERS: Record<RelayProviderKey, BrowserRelayProviderAdapter> = {
  browserbase: makeAdapter('browserbase', 'Browserbase (cloud browser)', 'Provider principal recomendado para sandbox/real futuro; real só após homologação + flags.'),
  local_playwright: makeAdapter('local_playwright', 'Playwright local', 'Apenas dev/sandbox; storageState/trace via SessionRef opaco no futuro.'),
  stagehand: makeAdapter('stagehand', 'Stagehand (act/extract/observe)', 'Camada agentic controlada sobre Playwright/Browserbase; fallback inteligente.'),
  skyvern_lab: makeAdapter('skyvern_lab', 'Skyvern (lab/fallback)', 'Laboratório para fluxos difíceis; não é dependência primária do MVP.'),
  mock: makeAdapter('mock', 'Mock (sem provider)', 'Adapter neutro de simulação pura.'),
};

export function getBrowserRelayAdapter(key: string | null | undefined): BrowserRelayProviderAdapter {
  return (key && ADAPTERS[key as RelayProviderKey]) || ADAPTERS.mock;
}

export function getBrowserRelayAdapterRegistry(): BrowserRelayProviderAdapter[] {
  return Object.values(ADAPTERS);
}

export function isKnownRelayProvider(key: string | null | undefined): boolean {
  return Boolean(key && (key as RelayProviderKey) in ADAPTERS);
}

export interface RelayEligibility {
  eligible: boolean;
  effective_mode: 'sandbox'; // SEMPRE sandbox neste estágio
  provider: RelayProviderKey;
  blockers: string[];
  real_action_allowed: false;
}

/**
 * 43P3 — gate de elegibilidade NOMEADO do relay. Recusa explicitamente
 * qualquer modo real/real_future (rebaixa para sandbox) e providers
 * desconhecidos. Prepara o caminho do 43P4 sem permitir real aqui.
 */
export function evaluateRelayEligibility(provider: string | null | undefined, requestedMode?: string | null): RelayEligibility {
  const known = isKnownRelayProvider(provider);
  const adapter = getBrowserRelayAdapter(provider);
  const blockers: string[] = [];
  if (!known) blockers.push('unknown_provider_downgraded_to_mock');
  if (requestedMode && requestedMode !== 'sandbox') blockers.push('real_mode_not_allowed_43p3');
  if (adapter.canOpenRealBrowser !== false) blockers.push('adapter_cannot_open_real_in_43p3'); // nunca ocorre
  return { eligible: true, effective_mode: 'sandbox', provider: adapter.provider_key, blockers, real_action_allowed: false };
}
