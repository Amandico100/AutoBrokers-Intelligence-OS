import { NextRequest, NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { filterGlobalCatalog, sanitizeGlobalCatalogEntry, getGlobalCatalogStats } from '@/lib/attendance/portal-global-catalog';

export const dynamic = 'force-dynamic';

/**
 * GET /api/admin/portal-browser/global-catalog?owner_key=&journey=&audience=&status=&confidence=
 * Catálogo GLOBAL de portais (intake oficial), sanitizado. Sem credencial; nenhum portal real acessado.
 */
export async function GET(request: NextRequest) {
  const supabase = getPortalSupabaseAdmin();
  try {
    const { userId } = await getPortalAdminContext(supabase);
    if (!userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });

    const { searchParams } = new URL(request.url);
    const entries = filterGlobalCatalog({
      owner_key: searchParams.get('owner_key'),
      journey: searchParams.get('journey'),
      audience: searchParams.get('audience'),
      status: searchParams.get('status'),
      confidence: searchParams.get('confidence'),
    });
    return NextResponse.json({
      ok: true,
      stats: getGlobalCatalogStats(),
      count: entries.length,
      catalog: entries.map(sanitizeGlobalCatalogEntry),
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[PORTAL GLOBAL-CATALOG GET]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
