// Dados Globais — leitura dos contatos globais de sinistro/assistência das
// seguradoras (ativos por padrão). Surface para o dashboard (edição/override por
// tenant vem depois). Read-only; admin autenticado. Não são segredos.
// SPEC-064 Bloco H — a autenticação passou a vir de `admin-auth.ts`.
//
// Esta rota importava `getPortalAdminContext` de `portal-admin-context.ts`,
// que era parte do Portal Browser. Os dois helpers que ela usava —
// cliente service-role e resolução de sessão de admin — não têm nada a ver
// com portal: só moravam ali por acidente de histórico.
//
// Era a única coisa viva presa no módulo do simulador, e mantê-la significava
// manter 332 linhas de um sistema que nunca acessou nada. Agora ela usa o
// caminho canônico, o mesmo que a Fábrica passou a usar no Bloco I.1.
import { NextResponse } from 'next/server';
import { getAdminContext } from '@/lib/admin/admin-auth';
import { getInsurerContactsGlobal, getSharedServiceProviderPortals, INSURER_CONTACTS_SOURCE } from '@/lib/attendance/insurer-contacts-global-seed';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const ctx = await getAdminContext();
    if (!ctx?.adminId) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });

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
