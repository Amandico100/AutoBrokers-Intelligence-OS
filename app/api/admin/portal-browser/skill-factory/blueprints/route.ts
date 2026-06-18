import { NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { getPortalSkillBlueprints } from '@/lib/attendance/portal-skill-factory';

export const dynamic = 'force-dynamic';

/** GET — lista os blueprints de skill reutilizáveis (genéricos, dry-run). */
export async function GET() {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
    return NextResponse.json({ ok: true, blueprints: getPortalSkillBlueprints(), real_action_allowed: false });
  } catch (error: any) {
    console.error('[SKILL FACTORY BLUEPRINTS]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
