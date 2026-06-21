// TA2-B — catálogo de corredores da corretora (status real por tenant).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { listTenantCorridors } from '@/lib/admin/tenant-corridor-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await listTenantCorridors(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out);
}
