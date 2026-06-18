import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext, getSkillRun } from '@/lib/attendance/portal-admin-context';
import { findRequestSecrets } from '@/lib/attendance/portal-admin-sanitizers';
import { getGlobalPortalCatalogSeed } from '@/lib/attendance/portal-global-catalog';
import { getPortalMapForPortal } from '@/lib/attendance/portal-maps';
import { getPortalSkill } from '@/lib/attendance/portal-skills';
import { buildPortalSkillEvidencePack, evaluatePortalSkillQuality, explainMissingEvidence } from '@/lib/attendance/portal-skill-factory';

export const dynamic = 'force-dynamic';

/** POST — avalia evidence pack + quality score de uma skill candidata. Sem ação real. */
export async function POST(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { companyId, userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    if (!companyId) return NextResponse.json({ ok: false, error: 'No company associated' }, { status: 403 });

    let body: Record<string, any> = {};
    try { body = await request.json(); } catch { body = {}; }
    if (findRequestSecrets(body).length > 0) return NextResponse.json({ ok: false, error: 'forbidden_secret_in_body' }, { status: 400 });
    if (!body.portal_id) return NextResponse.json({ ok: false, error: 'missing_portal_id' }, { status: 400 });

    const entry = getGlobalPortalCatalogSeed().find((e) => e.portal_id === body.portal_id);
    if (!entry) return NextResponse.json({ ok: false, error: 'portal_not_in_catalog' }, { status: 404 });

    const journey = body.journey ?? entry.supported_journeys?.[0] ?? null;
    const map = getPortalMapForPortal(body.portal_id, journey);
    const skill = body.skill_key ? getPortalSkill(body.portal_id, body.skill_key) : null;

    let lastRun: any = null;
    if (body.run_id) {
      try { lastRun = await getSkillRun(supabase, companyId, body.run_id); } catch { lastRun = null; }
    }
    const lastRunLite = lastRun
      ? { passed: lastRun.eval?.passed, trace_available: lastRun.eval?.trace_available, replay_available: lastRun.eval?.replay_available, status: lastRun.status, forbidden_actions_detected: lastRun.forbidden_actions_detected, challenge_detected: lastRun.challenge_detected }
      : null;

    const pack = buildPortalSkillEvidencePack({
      portalEntry: entry, journey, map,
      trace_id: lastRun?.relay_session?.relay_id ?? null,
      replay_id: lastRun?.relay_session?.relay_id ?? null,
      human_review_status: body.human_review_status ?? 'none',
    });
    const quality = evaluatePortalSkillQuality(skill, pack, lastRunLite);

    return NextResponse.json({
      ok: true,
      evidence_pack: pack,
      missing_evidence_explained: explainMissingEvidence(pack),
      quality,
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[SKILL FACTORY EVALUATE]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
