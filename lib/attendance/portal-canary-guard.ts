// 43P-FINAL-2 — guard compartilhado dos endpoints de canary (server-only).
// Resolve conta + flags + readiness + autorização tenant/approval num só lugar.
import type { SupabaseClient } from '@supabase/supabase-js';
import { listPortalAccounts, listPortalDefinitions, listCanaryApprovals } from '@/lib/attendance/portal-admin-context';
import { getProductionFlags } from '@/lib/security/production-gates';
import { evaluateBrowserbaseReadiness } from '@/lib/attendance/browserbase-real-adapter';
import { evaluateTenantCanaryAuthorization } from '@/lib/attendance/portal-tenant-canary-authorization';

export interface CanaryGuardCtx { companyId: string; userId: string; isMaster: boolean }

export interface CanaryGuardResult {
  acc: any | null;
  flags: ReturnType<typeof getProductionFlags>;
  readiness: ReturnType<typeof evaluateBrowserbaseReadiness>;
  authz: ReturnType<typeof evaluateTenantCanaryAuthorization>;
  hostAllowlist: string[];
  env: { BROWSERBASE_API_KEY?: string; BROWSERBASE_PROJECT_ID?: string };
}

function hostOf(url: string | null | undefined): string | null {
  if (!url) return null;
  try { return new URL(url).host; } catch { return null; }
}

export async function guardCanary(supabase: SupabaseClient, ctx: CanaryGuardCtx, portalAccountId: string, journey = 'login'): Promise<CanaryGuardResult> {
  const accounts = await listPortalAccounts(supabase, ctx.companyId);
  const acc = accounts.find((a: any) => a.portal_account_id === portalAccountId) ?? null;

  let hostAllowlist: string[] = [];
  if (acc?.portal_id) {
    try {
      const defs = await listPortalDefinitions(supabase, ctx.companyId);
      const def = defs.find((d: any) => d.portal_id === acc.portal_id);
      const h = hostOf(def?.base_url);
      if (h) hostAllowlist = [h];
    } catch { /* segue sem allowlist */ }
  }

  const flags = getProductionFlags();
  const readiness = evaluateBrowserbaseReadiness({
    flags: {
      global_kill_switch: flags.global_kill_switch,
      portal_real_action_enabled: flags.portal_real_action_enabled,
      portal_login_real_enabled: flags.portal_login_real_enabled,
      portal_session_capture_enabled: flags.portal_session_capture_enabled,
      browserbase_real_browser_enabled: flags.browserbase_real_browser_enabled,
    },
    approval_exists: true,
  });

  const approvals = await listCanaryApprovals(supabase, ctx.companyId);
  const approval = approvals.find((a: any) => a.portal_account_id === portalAccountId && a.journey === journey) ?? null;

  const authz = evaluateTenantCanaryAuthorization({
    company_id: ctx.companyId, portal_id: acc?.portal_id ?? null, portal_account_id: portalAccountId, journey,
    is_master: ctx.isMaster, operator_company_id: ctx.companyId,
    global_kill_switch: flags.global_kill_switch,
    global_flag_enabled: flags.portal_login_real_enabled && flags.browserbase_real_browser_enabled,
    readiness_can_open: readiness.can_open_real_browser,
    approval,
  });

  return {
    acc, flags, readiness, authz, hostAllowlist,
    env: { BROWSERBASE_API_KEY: process.env.BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID: process.env.BROWSERBASE_PROJECT_ID },
  };
}

// Seletores genéricos (o portal map fornece os específicos na expansão).
export const DEFAULT_CHALLENGE_SELECTORS = [
  { kind: 'captcha', selector: 'iframe[src*="recaptcha"], iframe[title*="captcha" i], div.g-recaptcha, [data-hcaptcha-widget-id]' },
  { kind: 'otp', selector: 'input[autocomplete="one-time-code"], input[name*="otp" i], input[name*="token" i]' },
];
