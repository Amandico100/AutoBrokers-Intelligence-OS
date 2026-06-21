// Dados Globais — leitura dos contatos globais de sinistro/assistência das
// seguradoras (ativos por padrão). Surface para o dashboard (edição/override por
// tenant vem depois). Read-only; admin autenticado. Não são segredos.
import { NextResponse } from 'next/server';
import { getPortalSupabaseAdmin, getPortalAdminContext } from '@/lib/attendance/portal-admin-context';
import { getInsurerContactsGlobal, getSharedServiceProviderPortals, INSURER_CONTACTS_SOURCE } from '@/lib/attendance/insurer-contacts-global-seed';

export const dynamic = 'force-dynamic';

export async function GET() {
  const supabase = getPortalSupabaseAdmin();
  try {
    const ctx = await getPortalAdminContext(supabase);
    if (!ctx.userId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });

    const contacts = getInsurerContactsGlobal();
    return NextResponse.json({
      ok: true,
      source: INSURER_CONTACTS_SOURCE,
      scope: 'global',
      editable_in_dashboard: false, // edição/override por tenant = próximo passo
      count: contacts.length,
      contacts,
      shared_service_provider_portals: getSharedServiceProviderPortals(),
      real_action_allowed: false,
    });
  } catch (error: any) {
    console.error('[INSURER CONTACTS]', error?.message);
    return NextResponse.json({ ok: false, error: 'Erro interno' }, { status: 500 });
  }
}
