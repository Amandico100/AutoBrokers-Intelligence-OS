// SEC-001 — Production Gates & Kill Switches. PURO, self-contained.
// Regra mestra: FALHA FECHADO. Env ausente ⇒ BLOQUEADO. Nada real é liberado
// neste batch. Gates de portal/ação/RAG/memória retornam allowed=false por
// padrão; real_action_allowed é literal false.

export interface ProductionFlags {
  global_kill_switch: boolean; // true = bloqueando (default ATIVO)
  portal_real_action_enabled: boolean;
  portal_login_real_enabled: boolean;
  portal_session_capture_enabled: boolean;
  external_action_real_enabled: boolean;
  insurer_whatsapp_real_send_enabled: boolean;
  rag_publish_to_attendance_enabled: boolean;
  memory_long_term_enabled: boolean;
  web_search_core_enabled: boolean;
  web_search_attendance_enabled: boolean; // SEMPRE false no MVP
  media_public_urls_enabled: boolean;
}

type EnvLike = Record<string, string | undefined>;

/** Lê as flags com default SEGURO (ausente ⇒ bloqueado; kill switch ⇒ ativo). */
export function getProductionFlags(env: EnvLike = (typeof process !== 'undefined' ? process.env : {})): ProductionFlags {
  const on = (k: string) => env[k] === 'true';
  return {
    global_kill_switch: env.GLOBAL_KILL_SWITCH !== 'false', // ativo a menos que explicitamente desligado
    portal_real_action_enabled: on('PORTAL_REAL_ACTION_ENABLED'),
    portal_login_real_enabled: on('PORTAL_LOGIN_REAL_ENABLED'),
    portal_session_capture_enabled: on('PORTAL_SESSION_CAPTURE_ENABLED'),
    external_action_real_enabled: on('EXTERNAL_ACTION_REAL_ENABLED'),
    insurer_whatsapp_real_send_enabled: on('INSURER_WHATSAPP_REAL_SEND_ENABLED'),
    rag_publish_to_attendance_enabled: on('RAG_PUBLISH_TO_ATTENDANCE_ENABLED'),
    memory_long_term_enabled: on('MEMORY_LONG_TERM_ENABLED'),
    web_search_core_enabled: on('WEB_SEARCH_CORE_ENABLED'),
    web_search_attendance_enabled: false, // travado no MVP, ignora env
    media_public_urls_enabled: on('MEDIA_PUBLIC_URLS_ENABLED'),
  };
}

export interface GateResult {
  gate_name: string;
  allowed: boolean;
  blockers: string[];
  flags_snapshot: Record<string, boolean>;
  real_action_allowed: false;
}

export function evaluateGlobalKillSwitch(flags: ProductionFlags = getProductionFlags()): { active: boolean; reason: string } {
  return { active: flags.global_kill_switch === true, reason: flags.global_kill_switch ? 'global_kill_switch_active' : 'kill_switch_off' };
}

function snapshot(flags: ProductionFlags, keys: (keyof ProductionFlags)[]): Record<string, boolean> {
  const o: Record<string, boolean> = {};
  for (const k of keys) o[k] = flags[k];
  return o;
}

export interface PortalGateContext {
  flags?: ProductionFlags;
  portal_status?: string | null;
  skill_promotion?: string | null;
  dry_run_passed?: boolean;
  trace_available?: boolean;
  replay_available?: boolean;
  approval_exists?: boolean;
  session_capture?: boolean; // login setup
}

/** Gate de ação REAL de portal. SEC-001: sempre allowed=false. */
export function evaluatePortalRealActionGate(ctx: PortalGateContext = {}): GateResult {
  const flags = ctx.flags ?? getProductionFlags();
  const blockers: string[] = [];
  if (flags.global_kill_switch) blockers.push('global_kill_switch_active');
  if (!flags.portal_real_action_enabled) blockers.push('portal_real_action_disabled');
  if (ctx.session_capture && !flags.portal_login_real_enabled) blockers.push('portal_login_real_disabled');
  if (ctx.session_capture && !flags.portal_session_capture_enabled) blockers.push('portal_session_capture_disabled');
  if (ctx.portal_status === 'approved_future' ? false : ctx.portal_status !== undefined) blockers.push('portal_not_approved');
  if (!ctx.dry_run_passed) blockers.push('no_dry_run_passed');
  if (!ctx.trace_available) blockers.push('no_trace');
  if (!ctx.replay_available) blockers.push('no_replay');
  if (!ctx.approval_exists) blockers.push('no_human_approval');
  return {
    gate_name: 'portal_real_action',
    allowed: false, // travado no SEC-001
    blockers,
    flags_snapshot: snapshot(flags, ['global_kill_switch', 'portal_real_action_enabled', 'portal_login_real_enabled', 'portal_session_capture_enabled']),
    real_action_allowed: false,
  };
}

export interface ExternalActionGateContext {
  flags?: ProductionFlags;
  channel?: string | null; // insurer_whatsapp...
  adapter_can_send_real?: boolean;
  approval_exists?: boolean;
  coverage_human_approved?: boolean;
}

/** Gate de envio REAL externo (WhatsApp/seguradora). SEC-001: sempre allowed=false. */
export function evaluateExternalActionRealSendGate(ctx: ExternalActionGateContext = {}): GateResult {
  const flags = ctx.flags ?? getProductionFlags();
  const blockers: string[] = [];
  if (flags.global_kill_switch) blockers.push('global_kill_switch_active');
  if (!flags.external_action_real_enabled) blockers.push('external_action_real_disabled');
  if (ctx.channel === 'insurer_whatsapp' && !flags.insurer_whatsapp_real_send_enabled) blockers.push('insurer_whatsapp_real_send_disabled');
  if (ctx.adapter_can_send_real !== true) blockers.push('adapter_cannot_send_real');
  if (!ctx.approval_exists) blockers.push('no_human_approval');
  if (ctx.coverage_human_approved === false) blockers.push('coverage_not_human_approved');
  return {
    gate_name: 'external_action_real_send',
    allowed: false,
    blockers,
    flags_snapshot: snapshot(flags, ['global_kill_switch', 'external_action_real_enabled', 'insurer_whatsapp_real_send_enabled']),
    real_action_allowed: false,
  };
}

export interface RagPublishContext {
  flags?: ProductionFlags;
  target?: 'attendance' | 'core' | 'auxiliary' | string | null;
  audience?: string | null; // insured_external | broker_internal | confidential | restricted
  sensitivity?: string | null;
  status?: string | null; // draft | published | quarantined
  source_kind?: string | null; // raw_intake | conversation_bruta | curated | official
  approval_exists?: boolean;
  has_provenance?: boolean;
}

const ATTENDANCE_FORBIDDEN_AUDIENCE = ['broker_internal', 'confidential', 'restricted', 'internal'];

/** Gate de publicação/uso de conhecimento no Attendance. Falha fechado. */
export function evaluateRagKnowledgePublishGate(ctx: RagPublishContext = {}): GateResult {
  const flags = ctx.flags ?? getProductionFlags();
  const blockers: string[] = [];
  const target = ctx.target ?? 'attendance';
  if (!ctx.audience) blockers.push('missing_audience');
  if (!ctx.sensitivity) blockers.push('missing_sensitivity');
  if ((ctx.source_kind === 'raw_intake' || ctx.source_kind === 'conversation_bruta')) blockers.push('raw_intake_must_be_quarantined');
  if (target === 'attendance') {
    if (!flags.rag_publish_to_attendance_enabled) blockers.push('rag_publish_to_attendance_disabled');
    if (ctx.audience && ATTENDANCE_FORBIDDEN_AUDIENCE.includes(String(ctx.audience).toLowerCase())) blockers.push('audience_not_allowed_for_attendance');
    if (ctx.audience && String(ctx.audience).toLowerCase() !== 'insured_external') blockers.push('attendance_requires_insured_external');
    if (ctx.status !== 'published') blockers.push('not_published');
    if (!ctx.has_provenance) blockers.push('missing_provenance');
    if (!ctx.approval_exists) blockers.push('missing_approval');
  }
  return {
    gate_name: 'rag_knowledge_publish',
    allowed: false, // travado no SEC-001 (RAG real depende de RAG1A/1B/1C)
    blockers,
    flags_snapshot: snapshot(flags, ['global_kill_switch', 'rag_publish_to_attendance_enabled']),
    real_action_allowed: false,
  };
}

export interface MemoryAccessContext {
  flags?: ProductionFlags;
  actor?: 'core' | 'attendance' | 'auxiliary' | string | null;
  audience?: string | null;
  same_tenant?: boolean;
  same_case_or_session?: boolean;
  company_match?: boolean;
}

/** Gate de acesso a memória. Attendance isolado em insured_external + próprio caso. */
export function evaluateMemoryAccessGate(ctx: MemoryAccessContext = {}): GateResult {
  const flags = ctx.flags ?? getProductionFlags();
  const blockers: string[] = [];
  if (ctx.company_match === false) blockers.push('company_mismatch');
  if (ctx.same_tenant === false) blockers.push('cross_tenant_blocked');
  const actor = ctx.actor ?? 'attendance';
  let allowed = false;
  if (actor === 'attendance') {
    if (String(ctx.audience ?? '').toLowerCase() !== 'insured_external') blockers.push('attendance_only_insured_external');
    if (ctx.same_case_or_session === false) blockers.push('attendance_out_of_case_scope');
    allowed = blockers.length === 0;
  } else if (actor === 'core') {
    // Core pode broker_internal dentro do tenant.
    allowed = ctx.same_tenant !== false && ctx.company_match !== false;
    if (!allowed && blockers.length === 0) blockers.push('core_tenant_scope_required');
  } else {
    // Auxiliar: por escopo; conservador → bloqueia sem escopo confirmado.
    blockers.push('auxiliary_scope_unconfirmed');
    allowed = false;
  }
  // long-term memory exige flag.
  if (!flags.memory_long_term_enabled) blockers.push('memory_long_term_disabled');
  return {
    gate_name: 'memory_access',
    allowed: allowed && !blockers.includes('memory_long_term_disabled') ? allowed : false,
    blockers,
    flags_snapshot: snapshot(flags, ['global_kill_switch', 'memory_long_term_enabled']),
    real_action_allowed: false,
  };
}

export function explainGateBlockers(blockers: string[]): string[] {
  const human: Record<string, string> = {
    global_kill_switch_active: 'Kill switch global ativo — nada real é executado.',
    portal_real_action_disabled: 'Flag PORTAL_REAL_ACTION_ENABLED desligada.',
    portal_login_real_disabled: 'Flag PORTAL_LOGIN_REAL_ENABLED desligada.',
    portal_session_capture_disabled: 'Flag PORTAL_SESSION_CAPTURE_ENABLED desligada.',
    external_action_real_disabled: 'Flag EXTERNAL_ACTION_REAL_ENABLED desligada.',
    insurer_whatsapp_real_send_disabled: 'Flag INSURER_WHATSAPP_REAL_SEND_ENABLED desligada.',
    rag_publish_to_attendance_disabled: 'Publicação RAG→Attendance desligada.',
    audience_not_allowed_for_attendance: 'Audiência não permitida no Attendance (broker_internal/confidential/restricted).',
    attendance_requires_insured_external: 'Attendance só pode usar conhecimento insured_external.',
    no_human_approval: 'Falta aprovação humana.',
    no_dry_run_passed: 'Falta dry-run aprovado.',
    no_trace: 'Falta trace.',
    no_replay: 'Falta replay.',
    memory_long_term_disabled: 'Memória de longo prazo desligada (sem policy segura).',
  };
  return blockers.map((b) => human[b] ?? b);
}

// --- helpers de segredo/PII (inline; self-contained) ------------------------
const INLINE_SECRET_KEYS = [
  'password', 'senha', 'token', 'client_token', 'cookie', 'cookies', 'storage_state', 'storagestate',
  'otp', 'mfa_code', 'secret', 'apikey', 'api_key', 'authorization', 'bearer', 'private_key',
  'vault_ref', 'storage_ref', 'destination_ref', 'encrypted_secret_ref',
];

export function assertNoRawSecrets(payload: unknown): { ok: boolean; hits: string[] } {
  const hits: string[] = [];
  const walk = (v: unknown, path: string) => {
    if (!v || typeof v !== 'object') return;
    for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
      if (INLINE_SECRET_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
      if (val && typeof val === 'object') walk(val, path ? `${path}.${k}` : k);
    }
  };
  walk(payload, '');
  return { ok: hits.length === 0, hits };
}

const _CPF = /\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/;
const _PHONE = /\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b/;

export function assertNoPIIInLogPayload(payload: unknown): { ok: boolean; reason: string | null } {
  const raw = typeof payload === 'string' ? payload : JSON.stringify(payload ?? '');
  if (_CPF.test(raw)) return { ok: false, reason: 'cpf' };
  if (_PHONE.test(raw)) return { ok: false, reason: 'phone' };
  if (assertNoRawSecrets(payload).ok === false) return { ok: false, reason: 'secret_key' };
  return { ok: true, reason: null };
}

/** Sanitiza payload de auditoria: remove chaves-segredo e mascara dígitos longos/OTP. */
export function sanitizeAuditPayload(payload: unknown): unknown {
  const mask = (s: string) => s.replace(/\d[\d.\-/\s]{9,}\d/g, '[num]').replace(/\b\d{4,8}\b/g, '[otp]').slice(0, 600);
  const walk = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === 'object') {
      const o: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (INLINE_SECRET_KEYS.includes(k.toLowerCase())) { o[k] = '[redacted]'; continue; }
        o[k] = walk(val);
      }
      return o;
    }
    if (typeof v === 'string') return mask(v);
    return v;
  };
  return walk(payload);
}
