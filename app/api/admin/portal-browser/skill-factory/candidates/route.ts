import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { getGlobalPortalCatalogSeed } from '@/lib/attendance/portal-global-catalog';
import { generatePortalSkillCandidatesFromCatalog } from '@/lib/attendance/portal-skill-factory';

export const dynamic = 'force-dynamic';

/** GET — candidatos a Portal Skill gerados do catálogo global (sem ação real). */
export async function GET(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });

    const { searchParams } = new URL(request.url);
    const candidates = generatePortalSkillCandidatesFromCatalog(getGlobalPortalCatalogSeed(), {
      audience: searchParams.get('audience'),
      status: searchParams.get('status'),
      confidence: searchParams.get('confidence'),
      exclude_mfa_captcha: searchParams.get('exclude_mfa_captcha') === 'true',
    });
    const limit = Math.min(Number(searchParams.get('limit') ?? '60') || 60, 200);
    return NextResponse.json({ ok: true, count: candidates.length, candidates: candidates.slice(0, limit), real_action_allowed: false });
  } catch (error: any) {
    console.error('[SKILL FACTORY CANDIDATES]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
