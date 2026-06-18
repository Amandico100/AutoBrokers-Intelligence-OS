// 43P3 — Portal Skill Runner (dry-run). PURO, self-contained. Orquestra uma
// PortalSkill sobre o Browser Relay Sandbox via INJEÇÃO DE DEPENDÊNCIA (recebe
// adapter + funções do relay), evitando cross-import em runtime. NUNCA acessa
// portal/URL/credencial real. real_action_allowed sempre false.

import type { PortalSkillRecord } from '@/lib/attendance/portal-skills';
import type { PortalMapRecord } from '@/lib/attendance/portal-maps';
import type { BrowserRelayProviderAdapter, RelayProviderKey } from '@/lib/attendance/browser-relay-adapters';
import type { RelayRuntimeSession, StartRelayInput, RelayStepInput } from '@/lib/attendance/browser-relay-runtime';

export type PortalSkillRunStatus =
  | 'planned' | 'running_sandbox' | 'waiting_human' | 'sandbox_passed' | 'sandbox_failed' | 'cancelled';

export interface PortalSkillEval {
  passed: boolean;
  score: number; // 0..1
  required_outputs_found: string[];
  forbidden_actions_detected: string[];
  challenge_detected: boolean;
  trace_available: boolean;
  replay_available: boolean;
  safe_to_promote_to_sandbox_validated: boolean;
  real_action_allowed: false;
}

export interface PortalSkillRun {
  run_id: string;
  portal_id: string;
  portal_account_id: string | null;
  portal_skill_id: string;
  portal_map_id: string;
  skill_key: string;
  journey: string;
  provider: RelayProviderKey;
  status: PortalSkillRunStatus;
  next_step: string;
  outputs: string[];
  forbidden_actions_detected: string[];
  challenge_detected: boolean;
  relay_session: RelayRuntimeSession | null;
  eval: PortalSkillEval | null;
  real_action_allowed: false;
}

export interface SkillRunnerDeps {
  adapter: BrowserRelayProviderAdapter;
  startRelay: (input: StartRelayInput, adapter: BrowserRelayProviderAdapter) => RelayRuntimeSession;
  applyStep: (session: RelayRuntimeSession, step: RelayStepInput, adapter: BrowserRelayProviderAdapter) => RelayRuntimeSession;
}

export interface RunSkillInput {
  skill: PortalSkillRecord;
  map: PortalMapRecord | null;
  portal_id: string;
  portal_account_id: string | null;
  account_present: boolean;
  credential_present: boolean;
  session_status: string | null; // healthy|expired|challenge_required|unknown
  provider: RelayProviderKey;
  inject_challenge?: string | null; // só para validação/eval do caminho de challenge
}

function runId(): string {
  return `skillrun-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function baseRun(input: RunSkillInput): PortalSkillRun {
  return {
    run_id: runId(),
    portal_id: input.portal_id,
    portal_account_id: input.portal_account_id ?? null,
    portal_skill_id: input.skill.portal_skill_id,
    portal_map_id: input.skill.portal_map_id,
    skill_key: input.skill.skill_key,
    journey: input.skill.journey,
    provider: input.provider,
    status: 'planned',
    next_step: 'init',
    outputs: [],
    forbidden_actions_detected: [],
    challenge_detected: false,
    relay_session: null,
    eval: null,
    real_action_allowed: false,
  };
}

/** Avalia o run produzindo o eval (passed/score/safe_to_promote). PURO. */
export function evaluatePortalSkillRun(run: PortalSkillRun, skill: PortalSkillRecord): PortalSkillEval {
  const required = skill.expected_outputs || [];
  const found = required.filter((o) => run.outputs.includes(o));
  const traceAvailable = Boolean(run.relay_session && run.relay_session.events.length > 0);
  const replayAvailable = traceAvailable;
  const passed = run.status === 'sandbox_passed'
    && found.length === required.length
    && run.forbidden_actions_detected.length === 0
    && run.challenge_detected === false;
  const score = required.length === 0 ? 0 : Math.round((found.length / required.length) * 100) / 100;
  const safe = passed && traceAvailable && replayAvailable && run.forbidden_actions_detected.length === 0 && !run.challenge_detected;
  return {
    passed,
    score,
    required_outputs_found: found,
    forbidden_actions_detected: run.forbidden_actions_detected,
    challenge_detected: run.challenge_detected,
    trace_available: traceAvailable,
    replay_available: replayAvailable,
    safe_to_promote_to_sandbox_validated: safe,
    real_action_allowed: false,
  };
}

export function buildPortalSkillEval(run: PortalSkillRun, skill: PortalSkillRecord): PortalSkillEval {
  return evaluatePortalSkillRun(run, skill);
}

/** Executa a skill em dry-run sobre o relay sandbox (adapter+relay via DI). PURO. */
export function runPortalSkillDryRun(input: RunSkillInput, deps: SkillRunnerDeps): PortalSkillRun {
  const run = baseRun(input);

  // --- Gates ---
  if (!input.map) {
    run.status = 'sandbox_failed'; run.next_step = 'no_map';
    run.eval = evaluatePortalSkillRun(run, input.skill);
    return run;
  }
  if (!input.account_present) {
    run.status = 'planned'; run.next_step = 'create_portal_account';
    run.eval = evaluatePortalSkillRun(run, input.skill);
    return run;
  }
  if (!input.credential_present) {
    run.status = 'planned'; run.next_step = 'credential_required';
    run.eval = evaluatePortalSkillRun(run, input.skill);
    return run;
  }
  if (input.session_status === 'expired' || input.session_status === 'challenge_required') {
    run.status = 'waiting_human'; run.next_step = 'human_challenge_required';
    run.challenge_detected = true;
    run.eval = evaluatePortalSkillRun(run, input.skill);
    return run;
  }

  // --- Run sandbox ---
  let relay = deps.startRelay({
    portal_id: input.portal_id, portal_account_id: input.portal_account_id, journey: input.skill.journey,
    provider: input.provider, portal_available: true, account_present: true, session_status: 'healthy', session_ref_masked: null,
  }, deps.adapter);

  if (relay.status !== 'running_sandbox') {
    run.relay_session = relay; run.status = 'waiting_human'; run.next_step = 'human_challenge_required';
    run.eval = evaluatePortalSkillRun(run, input.skill);
    return run;
  }
  run.status = 'running_sandbox';

  // observe → detecta login form + auth_required
  relay = deps.applyStep(relay, { type: 'observe', instruction: 'observe landing/login do corretor' }, deps.adapter);
  run.outputs.push('login_form_detected', 'auth_required');

  // extract → campos visíveis (mock)
  relay = deps.applyStep(relay, { type: 'extract', query: 'campos de autenticação visíveis' }, deps.adapter);

  if (input.inject_challenge) {
    relay = deps.applyStep(relay, { type: 'challenge', challenge_signal: input.inject_challenge }, deps.adapter);
    run.challenge_detected = true;
    run.outputs.push('challenge_required');
    run.status = 'waiting_human'; run.next_step = 'human_challenge_required';
  } else {
    relay = deps.applyStep(relay, { type: 'complete' }, deps.adapter);
    run.outputs.push('post_login_home_detected');
    run.status = 'sandbox_passed'; run.next_step = 'evaluate';
  }

  run.relay_session = relay;
  run.eval = evaluatePortalSkillRun(run, input.skill);
  return run;
}

/** Aplica um passo manual extra ao run; bloqueia ações fora do allowed/forbidden. PURO. */
export function applyPortalSkillStep(
  run: PortalSkillRun,
  step: { action: string; relay_step?: RelayStepInput },
  skill: PortalSkillRecord,
  deps: SkillRunnerDeps,
): PortalSkillRun {
  const s: PortalSkillRun = { ...run, outputs: [...run.outputs], forbidden_actions_detected: [...run.forbidden_actions_detected], real_action_allowed: false };
  const action = (step.action || '').toLowerCase();
  const isForbidden = (skill.forbidden_actions || []).some((f) => action.includes(f.toLowerCase()) || f.toLowerCase().includes(action))
    || /real|submit|login_real|bypass|download|upload/.test(action);
  if (isForbidden) {
    // NÃO executa; registra bloqueio (mas não conta como "detected/performed").
    if (s.relay_session) {
      s.relay_session = { ...s.relay_session, events: [...s.relay_session.events, { at: new Date().toISOString(), type: 'forbidden_action_blocked', note: action }] };
    }
    s.next_step = 'forbidden_action_blocked';
    s.eval = evaluatePortalSkillRun(s, skill);
    return s;
  }
  if (s.relay_session && step.relay_step) {
    s.relay_session = deps.applyStep(s.relay_session, step.relay_step, deps.adapter);
  }
  s.eval = evaluatePortalSkillRun(s, skill);
  return s;
}

const FORBIDDEN_KEYS = ['password', 'senha', 'token', 'client_token', 'cookie', 'cookies', 'storage_state', 'storagestate', 'otp', 'secret', 'apikey', 'authorization', 'bearer', 'private_key'];

export function findSkillRunSecrets(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (FORBIDDEN_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findSkillRunSecrets(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

/** Saída sanitizada do run (remove chaves de segredo recursivamente). */
export function sanitizePortalSkillRun(run: PortalSkillRun): Record<string, unknown> {
  const walk = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === 'object') {
      const o: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (FORBIDDEN_KEYS.includes(k.toLowerCase())) continue;
        o[k] = walk(val);
      }
      return o;
    }
    return v;
  };
  return walk(run) as Record<string, unknown>;
}
