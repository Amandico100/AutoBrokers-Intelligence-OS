// SPEC-013 B1 — galeria de Auxiliares da corretora (templates globais + status do tenant).
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';
import { listTenantAuxiliaries } from '@/lib/admin/tenant-auxiliary-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest) {
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const out = await listTenantAuxiliaries(auth.supabase, auth.ctx.companyId);
  return NextResponse.json(out);
}
