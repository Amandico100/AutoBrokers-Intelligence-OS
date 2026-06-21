// TA2-B — seguradoras disponíveis (contatos globais em leitura) + estado de
// corredores da corretora. Read-only: a corretora não edita contatos globais.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { getInsurerContactsGlobal } from '@/lib/attendance/insurer-contacts-global-seed';
import { listTenantCorridors } from '@/lib/admin/tenant-corridor-store';
import { buildInsurerView } from '@/lib/admin/tenant-insurers-view';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const corridors = await listTenantCorridors(auth.supabase, auth.ctx.companyId);
  const items = buildInsurerView(getInsurerContactsGlobal(), corridors.items);
  return NextResponse.json({ ok: true, items, read_only: true });
}
