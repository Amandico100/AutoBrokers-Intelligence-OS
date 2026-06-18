import { NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { getPortalSkills } from '@/lib/attendance/portal-skills';
import { getPortalMaps } from '@/lib/attendance/portal-maps';

export const dynamic = 'force-dynamic';

/** GET — lista Portal Skills + Portal Maps disponíveis (dry-run only). */
export async function GET() {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    return NextResponse.json({
      ok: true,
      skills: getPortalSkills(),
      maps: getPortalMaps().map((m) => ({ portal_map_id: m.portal_map_id, portal_id: m.portal_id, version: m.version, label: m.label, status: m.status, journeys: m.journeys.map((j) => j.journey) })),
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[PORTAL SKILLS GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
